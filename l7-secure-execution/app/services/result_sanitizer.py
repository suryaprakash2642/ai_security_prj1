"""Result Sanitizer — last-line-of-defense PII detection and masking.

Scans every returned value for PII patterns regardless of whether
SQL-level masking was applied. Catches edge cases that masking
expressions might miss (NULLs, dialect differences, data quality).
"""

from __future__ import annotations

import re
from typing import Any

import structlog

from app.models.api import ColumnMetadata, SanitizationEvent
from app.models.enums import PIIType

logger = structlog.get_logger(__name__)


# ── Pre-compiled PII patterns ──────────────────────────────────────────────

_PATTERNS: list[tuple[PIIType, re.Pattern]] = [
    (PIIType.SSN,    re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    (PIIType.AADHAAR, re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")),
    (PIIType.PHONE,  re.compile(r"\b(?:\+\d{1,3}[\s-]?)?\d{10,12}\b")),
    (PIIType.EMAIL,  re.compile(
        r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
        re.IGNORECASE,
    )),
]

# Columns that are known-safe for certain numeric patterns
_EXCLUDE_COLUMN_PATTERNS = re.compile(
    r"(mrn|encounter_id|claim_id|icd|procedure_code|diagnosis_code"
    r"|zipcode|zip_code|postal_code|npi|dea|tax_id)",
    re.IGNORECASE,
)

# ── Masking functions ──────────────────────────────────────────────────────

def _mask_ssn(value: str, match: re.Match) -> str:
    last4 = match.group(0)[-4:]
    return value[:match.start()] + f"***-**-{last4}" + value[match.end():]


def _mask_aadhaar(value: str, match: re.Match) -> str:
    raw = re.sub(r"\s", "", match.group(0))
    last4 = raw[-4:]
    return value[:match.start()] + f"XXXX XXXX {last4}" + value[match.end():]


def _mask_phone(value: str, match: re.Match) -> str:
    raw = re.sub(r"[\s\-+]", "", match.group(0))
    last4 = raw[-4:] if len(raw) >= 4 else raw
    return value[:match.start()] + f"***-***-{last4}" + value[match.end():]


def _mask_email(value: str, match: re.Match) -> str:
    email = match.group(0)
    at_idx = email.find("@")
    if at_idx < 0:
        return value
    first_char = email[0] if email else "*"
    domain = email[at_idx + 1:]
    masked = f"{first_char}***@{domain}"
    return value[:match.start()] + masked + value[match.end():]


_MASKERS = {
    PIIType.SSN: _mask_ssn,
    PIIType.AADHAAR: _mask_aadhaar,
    PIIType.PHONE: _mask_phone,
    PIIType.EMAIL: _mask_email,
}


# ── Column filter helpers ──────────────────────────────────────────────────

def _should_scan_column(col: ColumnMetadata) -> bool:
    """Return True if the column should be PII-scanned."""
    col_type = (col.type or "").upper()
    # Skip purely numeric/boolean/date columns (no string PII)
    if col_type in ("INT", "INTEGER", "BIGINT", "FLOAT", "DOUBLE",
                    "BOOLEAN", "BOOL", "DATE", "TIMESTAMP", "TIMESTAMPTZ"):
        return False
    return True


def _should_check_phone_for_column(col_name: str) -> bool:
    """Phone pattern has high false-positive rate on medical codes / IDs."""
    return not bool(_EXCLUDE_COLUMN_PATTERNS.search(col_name))


# ── Core sanitizer ─────────────────────────────────────────────────────────

class SanitizationResult:
    def __init__(self):
        self.events: list[SanitizationEvent] = []
        self.rows_scanned = 0
        self.columns_checked = 0

    @property
    def pii_detected(self) -> int:
        return len(self.events)


def sanitize(
    rows: list[list[Any]],
    columns: list[ColumnMetadata],
) -> tuple[list[list[Any]], SanitizationResult]:
    """Scan and redact PII from result rows.

    Returns (sanitized_rows, result) — modifies rows in-place for efficiency.
    """
    result = SanitizationResult()
    result.rows_scanned = len(rows)

    # Determine which columns to scan
    col_indices_to_scan = [
        (i, col) for i, col in enumerate(columns)
        if _should_scan_column(col)
    ]
    result.columns_checked = len(col_indices_to_scan)

    for row_idx, row in enumerate(rows):
        for col_idx, col in col_indices_to_scan:
            if col_idx >= len(row):
                continue
            cell = row[col_idx]
            if not isinstance(cell, str) or not cell:
                continue

            original = cell
            modified = cell

            for pii_type, pattern in _PATTERNS:
                # Skip phone checks for known-ID columns
                if pii_type == PIIType.PHONE and not _should_check_phone_for_column(col.name):
                    continue

                match = pattern.search(modified)
                if match:
                    masker = _MASKERS.get(pii_type)
                    if masker:
                        modified = masker(modified, match)
                        snippet = original[:6] + "..." if len(original) > 6 else original
                        result.events.append(SanitizationEvent(
                            row_index=row_idx,
                            column=col.name,
                            pii_type=pii_type,
                            original_snippet=snippet,
                            masked_value=modified,
                        ))
                        logger.warning(
                            "pii_detected",
                            row=row_idx,
                            column=col.name,
                            pii_type=pii_type.value,
                        )

            if modified != original:
                row[col_idx] = modified

    return rows, result
