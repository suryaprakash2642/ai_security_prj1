"""Auto-Classification Engine — rules-based PII detection with human review queue.

Key rules:
- Ambiguous cases default to HIGHER sensitivity
- All suggestions enter a human review queue
- Approved classifications become enforced graph state
- substance_abuse_records → HARD DENY, no override
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import structlog

from app.models.api import ClassificationSummary
from app.models.audit import ChangeRecord
from app.models.enums import (
    ChangeAction,
    ChangeSource,
    MaskingStrategy,
    PIIType,
    SensitivityLevel,
)
from app.repositories.audit_repository import AuditRepository
from app.repositories.graph_read_repo import GraphReadRepository
from app.repositories.graph_write_repo import GraphWriteRepository
from app.services.cache import CacheService

logger = structlog.get_logger(__name__)


# ── Classification rule definitions ──────────────────────────


@dataclass(frozen=True)
class ClassificationRule:
    """A single pattern-match rule for column classification."""
    patterns: list[str]
    pii_type: PIIType
    sensitivity_level: SensitivityLevel
    masking_strategy: MaskingStrategy
    confidence: float  # 0.0 – 1.0
    description: str


# Master rule set — ordered by specificity (most specific first)
CLASSIFICATION_RULES: list[ClassificationRule] = [
    # Identity documents
    ClassificationRule(
        patterns=[r"ssn", r"social_security", r"social_sec"],
        pii_type=PIIType.SSN,
        sensitivity_level=SensitivityLevel.TOP_SECRET,
        masking_strategy=MaskingStrategy.HASH,
        confidence=0.95,
        description="Social Security Number — highest sensitivity",
    ),
    ClassificationRule(
        patterns=[r"aadhaar", r"aadhar", r"aadhar_num"],
        pii_type=PIIType.AADHAAR,
        sensitivity_level=SensitivityLevel.TOP_SECRET,
        masking_strategy=MaskingStrategy.HASH,
        confidence=0.95,
        description="Aadhaar identification number (India)",
    ),
    ClassificationRule(
        patterns=[r"pan_number", r"pan_card", r"pan_no"],
        pii_type=PIIType.PAN,
        sensitivity_level=SensitivityLevel.RESTRICTED,
        masking_strategy=MaskingStrategy.HASH,
        confidence=0.90,
        description="PAN card number (India tax ID)",
    ),
    # Medical identifiers
    ClassificationRule(
        patterns=[r"mrn", r"medical_record", r"med_rec_num", r"patient_mrn"],
        pii_type=PIIType.MEDICAL_RECORD_NUMBER,
        sensitivity_level=SensitivityLevel.TOP_SECRET,
        masking_strategy=MaskingStrategy.HASH,
        confidence=0.95,
        description="Medical Record Number — direct patient identifier",
    ),
    ClassificationRule(
        patterns=[r"insurance_id", r"ins_id", r"policy_number", r"member_id"],
        pii_type=PIIType.INSURANCE_ID,
        sensitivity_level=SensitivityLevel.RESTRICTED,
        masking_strategy=MaskingStrategy.HASH,
        confidence=0.85,
        description="Insurance/policy identifier",
    ),
    # Personal names
    ClassificationRule(
        patterns=[r"full_name", r"patient_name", r"emp_name", r"person_name"],
        pii_type=PIIType.FULL_NAME,
        sensitivity_level=SensitivityLevel.RESTRICTED,
        masking_strategy=MaskingStrategy.REDACT,
        confidence=0.90,
        description="Full person name",
    ),
    ClassificationRule(
        patterns=[r"first_name", r"fname", r"given_name"],
        pii_type=PIIType.FIRST_NAME,
        sensitivity_level=SensitivityLevel.CONFIDENTIAL,
        masking_strategy=MaskingStrategy.REDACT,
        confidence=0.85,
        description="First/given name",
    ),
    ClassificationRule(
        patterns=[r"last_name", r"lname", r"surname", r"family_name"],
        pii_type=PIIType.LAST_NAME,
        sensitivity_level=SensitivityLevel.CONFIDENTIAL,
        masking_strategy=MaskingStrategy.REDACT,
        confidence=0.85,
        description="Last/family name",
    ),
    # Dates
    ClassificationRule(
        patterns=[r"dob", r"date_of_birth", r"birth_date", r"birthdate"],
        pii_type=PIIType.DATE_OF_BIRTH,
        sensitivity_level=SensitivityLevel.RESTRICTED,
        masking_strategy=MaskingStrategy.GENERALIZE_YEAR,
        confidence=0.90,
        description="Date of birth — HIPAA identifier",
    ),
    # Contact information
    ClassificationRule(
        patterns=[r"email", r"e_mail", r"email_addr"],
        pii_type=PIIType.EMAIL,
        sensitivity_level=SensitivityLevel.CONFIDENTIAL,
        masking_strategy=MaskingStrategy.PARTIAL_MASK,
        confidence=0.90,
        description="Email address",
    ),
    ClassificationRule(
        patterns=[r"phone", r"tel", r"mobile", r"cell_num", r"contact_num"],
        pii_type=PIIType.PHONE,
        sensitivity_level=SensitivityLevel.CONFIDENTIAL,
        masking_strategy=MaskingStrategy.PARTIAL_MASK,
        confidence=0.85,
        description="Phone/mobile number",
    ),
    ClassificationRule(
        patterns=[r"address", r"street_addr", r"mailing_addr", r"home_addr", r"postal_addr"],
        pii_type=PIIType.ADDRESS,
        sensitivity_level=SensitivityLevel.CONFIDENTIAL,
        masking_strategy=MaskingStrategy.REDACT,
        confidence=0.80,
        description="Physical/mailing address",
    ),
    # Financial
    ClassificationRule(
        patterns=[r"salary", r"compensation", r"base_pay", r"gross_pay", r"net_pay"],
        pii_type=PIIType.SALARY,
        sensitivity_level=SensitivityLevel.RESTRICTED,
        masking_strategy=MaskingStrategy.GENERALIZE_RANGE,
        confidence=0.85,
        description="Salary/compensation data",
    ),
    ClassificationRule(
        patterns=[r"bank_account", r"account_num", r"routing_num", r"iban"],
        pii_type=PIIType.BANK_ACCOUNT,
        sensitivity_level=SensitivityLevel.TOP_SECRET,
        masking_strategy=MaskingStrategy.HASH,
        confidence=0.90,
        description="Bank account/routing number",
    ),
    # Clinical notes (elevated protections)
    ClassificationRule(
        patterns=[r"note_text", r"therapy_note", r"psych_note", r"clinical_note", r"progress_note"],
        pii_type=PIIType.THERAPY_NOTE,
        sensitivity_level=SensitivityLevel.TOP_SECRET,
        masking_strategy=MaskingStrategy.REDACT,
        confidence=0.80,
        description="Clinical/therapy note text — may contain embedded PII",
    ),
]

# Tables that must ALWAYS be HARD DENY
HARD_DENY_TABLE_PATTERNS = [
    r"substance_abuse",
    r"sud_record",
    r"substance_use_disorder",
]


class ClassificationEngine:
    """Rules-based classification with human review queue."""

    def __init__(
        self,
        graph_reader: GraphReadRepository,
        graph_writer: GraphWriteRepository,
        audit_repo: AuditRepository,
        cache: CacheService | None = None,
    ) -> None:
        self._reader = graph_reader
        self._writer = graph_writer
        self._audit = audit_repo
        self._cache = cache

    async def classify_columns(
        self,
        table_fqns: list[str] | None = None,
        force_reclassify: bool = False,
        auto_approve_threshold: float = 0.90,
        classifier_id: str = "classification_engine",
    ) -> ClassificationSummary:
        """Analyze columns and create classification suggestions.

        High-confidence matches (>= threshold) are auto-approved.
        Lower-confidence matches go to the human review queue.
        Ambiguous cases default to HIGHER sensitivity.
        """
        summary = ClassificationSummary()

        # Get tables to process
        if table_fqns:
            tables = []
            for fqn in table_fqns:
                cols = await self._reader.get_table_columns(fqn)
                for c in cols:
                    tables.append((fqn, c))
        else:
            all_tables = await self._reader.get_all_active_tables()
            tables = []
            for t in all_tables:
                cols = await self._reader.get_table_columns(t.fqn)
                for c in cols:
                    tables.append((t.fqn, c))

        audit_records: list[ChangeRecord] = []

        for table_fqn, col in tables:
            # Skip already-classified unless forcing
            if col.is_pii and not force_reclassify:
                continue

            summary.columns_analyzed += 1
            match = self._match_column(col.name, col.data_type)

            if not match:
                continue

            summary.pii_detected += 1
            rule, confidence = match

            # Ambiguity guard: if confidence < 0.7, bump sensitivity up one level
            effective_sensitivity = rule.sensitivity_level
            if confidence < 0.7:
                effective_sensitivity = min(rule.sensitivity_level + 1, SensitivityLevel.TOP_SECRET)
                logger.info(
                    "ambiguous_classification_elevated",
                    column=col.fqn,
                    original_level=rule.sensitivity_level,
                    elevated_level=effective_sensitivity,
                )

            if confidence >= auto_approve_threshold:
                # Auto-approve and apply to graph
                write_result = await self._writer.update_column_classification(
                    column_fqn=col.fqn,
                    sensitivity_level=effective_sensitivity,
                    is_pii=True,
                    pii_type=rule.pii_type.value,
                    masking_strategy=rule.masking_strategy.value,
                )
                summary.auto_approved += 1
                audit_records.append(
                    ChangeRecord(
                        node_type="Column",
                        node_id=col.fqn,
                        action=ChangeAction.UPDATE,
                        old_values=write_result.get("old_values", {}),
                        new_values={
                            "is_pii": True,
                            "pii_type": rule.pii_type.value,
                            "sensitivity_level": effective_sensitivity,
                            "masking_strategy": rule.masking_strategy.value,
                        },
                        changed_by=classifier_id,
                        change_source=ChangeSource.CLASSIFICATION_ENGINE,
                    )
                )
            else:
                # Send to human review queue
                await self._audit.add_review_item(
                    column_fqn=col.fqn,
                    suggested_sensitivity=effective_sensitivity,
                    suggested_pii_type=rule.pii_type.value,
                    suggested_masking=rule.masking_strategy.value,
                    confidence=confidence,
                    reason=rule.description,
                )
                summary.review_items_created += 1

        # Log audit records
        if audit_records:
            gv = await self._audit.increment_graph_version(
                classifier_id, "Auto-classification run"
            )
            await self._audit.log_changes_batch(audit_records, gv)

        # Invalidate caches affected by classification changes
        if self._cache and summary.auto_approved > 0:
            await self._cache.invalidate("columns:")
            await self._cache.invalidate("tables:")
            await self._cache.invalidate("masking:")

        logger.info(
            "classification_complete",
            analyzed=summary.columns_analyzed,
            pii_found=summary.pii_detected,
            auto_approved=summary.auto_approved,
            review_queue=summary.review_items_created,
        )
        return summary

    async def apply_approved_review(self, review_id: int, approver: str) -> None:
        """Apply an approved review item to the graph."""
        reviews = await self._audit.get_pending_reviews(limit=1000)
        target = next((r for r in reviews if r["id"] == review_id), None)
        if not target:
            raise ValueError(f"Review item {review_id} not found or not pending")

        await self._writer.update_column_classification(
            column_fqn=target["column_fqn"],
            sensitivity_level=target["suggested_sensitivity"],
            is_pii=True,
            pii_type=target["suggested_pii_type"],
            masking_strategy=target["suggested_masking"],
        )
        await self._audit.approve_review(review_id, approver)

        gv = await self._audit.increment_graph_version(
            approver, f"Classification approved for {target['column_fqn']}"
        )
        await self._audit.log_change(
            ChangeRecord(
                node_type="Column",
                node_id=target["column_fqn"],
                action=ChangeAction.UPDATE,
                new_values={
                    "is_pii": True,
                    "pii_type": target["suggested_pii_type"],
                    "sensitivity_level": target["suggested_sensitivity"],
                },
                changed_by=approver,
                change_source=ChangeSource.CLASSIFICATION_ENGINE,
            ),
            gv,
        )

        # Invalidate caches affected by classification change
        if self._cache:
            await self._cache.invalidate("columns:")
            await self._cache.invalidate("masking:")

    @staticmethod
    def is_hard_deny_table(table_name: str) -> bool:
        """Check if a table must be HARD DENY (e.g., substance_abuse_records)."""
        lower = table_name.lower()
        return any(re.search(p, lower) for p in HARD_DENY_TABLE_PATTERNS)

    @staticmethod
    def _match_column(
        column_name: str, data_type: str
    ) -> tuple[ClassificationRule, float] | None:
        """Match a column against classification rules. Returns (rule, confidence) or None."""
        lower_name = column_name.lower().strip()

        for rule in CLASSIFICATION_RULES:
            for pattern in rule.patterns:
                # Exact match → full confidence
                if lower_name == pattern:
                    return rule, rule.confidence

                # Contains match → slightly reduced confidence
                if re.search(rf"(^|_){pattern}($|_)", lower_name):
                    return rule, rule.confidence * 0.95

                # Fuzzy contains → reduced confidence
                if pattern in lower_name:
                    return rule, rule.confidence * 0.8

        # Data-type heuristics for edge cases
        if data_type and "date" in data_type.lower() and any(
            kw in lower_name for kw in ["birth", "dob", "born"]
        ):
            return CLASSIFICATION_RULES[8], 0.7  # DOB rule

        return None
