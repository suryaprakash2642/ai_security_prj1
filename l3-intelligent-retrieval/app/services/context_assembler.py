"""Context Assembler — constructs final RetrievalResult with token budget enforcement.

Token budget rules (priority order):
1. Policy rules — NEVER truncated
2. Row filters — NEVER truncated
3. Table definitions — low-ranked tables dropped first
4. Descriptions — truncated before definitions are dropped

Uses tiktoken for accurate token counting.
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog

from app.config import load_ranking_weights
from app.models.l4_models import PermissionEnvelope
from app.models.retrieval import (
    FilteredTable,
    IntentResult,
    JoinGraph,
    RetrievalMetadata,
    RetrievalResult,
)

logger = structlog.get_logger(__name__)

# Try to use tiktoken; fall back to word-count estimate
try:
    import tiktoken
    _ENCODER = tiktoken.get_encoding("cl100k_base")

    def _count_tokens(text: str) -> int:
        return len(_ENCODER.encode(text))
except ImportError:
    _ENCODER = None

    def _count_tokens(text: str) -> int:
        # Rough estimate: ~0.75 tokens per word
        return int(len(text.split()) * 1.3)


class ContextAssembler:
    """Assembles the final RetrievalResult with token budget management."""

    def __init__(self) -> None:
        self._config = load_ranking_weights()
        self._budget = self._config.get("token_budget", {})

    def assemble(
        self,
        request_id: str,
        user_id: str,
        original_question: str,
        preprocessed_question: str,
        intent: IntentResult,
        filtered_tables: list[FilteredTable],
        join_graph: JoinGraph,
        envelope: PermissionEnvelope,
        denied_count: int,
        metadata: RetrievalMetadata,
        max_tables: int = 10,
    ) -> RetrievalResult:
        """Assemble the complete retrieval result within token budget.

        Priority:
        1. Policy rules — never truncated
        2. Row filters — never truncated
        3. High-ranked tables first
        4. Descriptions truncated before definitions dropped
        """
        max_tokens = self._budget.get("max_tokens", 4096)
        policy_reserved = self._budget.get("policy_rules_reserved", 512)
        filter_reserved = self._budget.get("row_filters_reserved", 256)
        desc_max = self._budget.get("description_max_tokens", 100)

        # Collect NL policy rules
        nl_rules = list(envelope.global_nl_rules)
        for tp in envelope.table_permissions:
            nl_rules.extend(tp.nl_rules)
        nl_rules = list(dict.fromkeys(nl_rules))  # Deduplicate preserving order

        # Calculate fixed token costs
        rules_tokens = sum(_count_tokens(r) for r in nl_rules)
        filter_tokens = sum(
            sum(_count_tokens(rf) for rf in t.row_filters)
            for t in filtered_tables
        )
        overhead_tokens = _count_tokens(original_question) + _count_tokens(preprocessed_question) + 100

        available = max_tokens - rules_tokens - filter_tokens - overhead_tokens

        # Apply token budget to tables
        final_tables, truncated = self._apply_token_budget(
            filtered_tables[:max_tables], available, desc_max,
        )

        # Update metadata
        metadata.tables_in_result = len(final_tables)
        metadata.tables_truncated = truncated
        metadata.token_count = self._count_total_tokens(
            final_tables, nl_rules, original_question, preprocessed_question,
        )

        return RetrievalResult(
            request_id=request_id,
            user_id=user_id,
            original_question=original_question,
            preprocessed_question=preprocessed_question,
            intent=intent,
            filtered_schema=final_tables,
            join_graph=join_graph,
            nl_policy_rules=nl_rules,
            denied_tables_count=denied_count,
            retrieval_metadata=metadata,
            resolved_at=datetime.now(UTC),
        )

    def _apply_token_budget(
        self,
        tables: list[FilteredTable],
        available_tokens: int,
        desc_max_tokens: int,
    ) -> tuple[list[FilteredTable], int]:
        """Apply token budget: truncate descriptions, drop low-ranked tables.

        Returns (final_tables, tables_dropped).
        """
        if available_tokens <= 0:
            return [], len(tables)

        result: list[FilteredTable] = []
        used = 0
        dropped = 0

        for table in tables:
            table_tokens = _count_tokens(table.ddl_fragment)

            # Truncate description if too long
            if table.description:
                desc_tokens = _count_tokens(table.description)
                if desc_tokens > desc_max_tokens:
                    words = table.description.split()
                    truncated_desc = ""
                    for word in words:
                        test = truncated_desc + " " + word
                        if _count_tokens(test) > desc_max_tokens:
                            break
                        truncated_desc = test
                    table = table.model_copy(update={"description": truncated_desc.strip() + "..."})

            if used + table_tokens <= available_tokens:
                result.append(table)
                used += table_tokens
            else:
                dropped += 1

        return result, dropped

    def _count_total_tokens(
        self,
        tables: list[FilteredTable],
        nl_rules: list[str],
        question: str,
        preprocessed: str,
    ) -> int:
        total = _count_tokens(question) + _count_tokens(preprocessed)
        total += sum(_count_tokens(r) for r in nl_rules)
        total += sum(_count_tokens(t.ddl_fragment) for t in tables)
        return total
