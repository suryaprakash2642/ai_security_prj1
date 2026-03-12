"""Core retrieval pipeline models — internal representations and final output.

These models are used throughout the retrieval pipeline and ultimately
assembled into the RetrievalResult that L5 consumes.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    ColumnVisibility,
    DomainHint,
    QueryIntent,
    RetrievalStrategy,
    TableDecision,
)
from app.models.l4_models import PermissionEnvelope


# ── Intent classification output ────────────────────────────


class IntentResult(BaseModel):
    """Output of the intent classifier."""

    model_config = ConfigDict(frozen=True)

    intent: QueryIntent
    confidence: float = Field(ge=0.0, le=1.0)
    matched_keywords: list[str] = Field(default_factory=list)
    domain_hints: list[DomainHint] = Field(default_factory=list)
    used_fallback: bool = False
    # All intents that scored > 0, used by ranking for multi-signal boosts
    secondary_intents: list[str] = Field(default_factory=list)


# ── Candidate table (pre-policy) ────────────────────────────


class CandidateTable(BaseModel):
    """A table retrieved by the multi-strategy pipeline, pre-RBAC."""

    model_config = ConfigDict()

    table_id: str  # FQN
    table_name: str
    description: str = ""
    domain: str = ""
    sensitivity_level: int = 1
    hard_deny: bool = False

    # Scoring
    semantic_score: float = 0.0
    keyword_score: float = 0.0
    fk_score: float = 0.0
    domain_affinity_score: float = 0.0
    intent_score: float = 0.0
    multi_strategy_bonus: float = 0.0
    final_score: float = 0.0

    # Provenance
    contributing_strategies: list[RetrievalStrategy] = Field(default_factory=list)
    fk_path: list[str] = Field(default_factory=list)
    is_bridge_table: bool = False


# ── Scoped column (post-policy) ─────────────────────────────


class ScopedColumn(BaseModel):
    """A column after policy-level scoping."""

    model_config = ConfigDict()

    name: str
    data_type: str = ""
    visibility: ColumnVisibility = ColumnVisibility.VISIBLE
    masking_expression: str | None = None
    computed_expression: str | None = None
    is_pk: bool = False
    description: str = ""


# ── Filtered table (post-policy) ────────────────────────────


class FilteredTable(BaseModel):
    """A table that survived RBAC filtering and column scoping."""

    model_config = ConfigDict()

    table_id: str
    table_name: str
    description: str = ""
    relevance_score: float = 0.0
    domain_tags: list[str] = Field(default_factory=list)

    # Column-level scoping
    visible_columns: list[ScopedColumn] = Field(default_factory=list)
    masked_columns: list[ScopedColumn] = Field(default_factory=list)
    hidden_column_count: int = 0

    # Policy constraints
    row_filters: list[str] = Field(default_factory=list)
    aggregation_only: bool = False
    max_rows: int | None = None

    # DDL fragment for LLM consumption
    ddl_fragment: str = ""


# ── Join graph ──────────────────────────────────────────────


class JoinEdge(BaseModel):
    """A single FK join edge between two allowed tables."""

    model_config = ConfigDict()

    source_table: str
    source_column: str
    target_table: str
    target_column: str
    constraint_name: str = ""
    is_restricted: bool = False


class JoinGraph(BaseModel):
    """Filtered join graph — only includes edges between allowed tables."""

    model_config = ConfigDict()

    edges: list[JoinEdge] = Field(default_factory=list)
    restricted_joins: list[dict[str, str]] = Field(default_factory=list)


# ── Retrieval metadata ──────────────────────────────────────


class RetrievalMetadata(BaseModel):
    """Pipeline execution metadata for observability."""

    model_config = ConfigDict()

    total_candidates_found: int = 0
    candidates_after_rbac: int = 0
    candidates_after_policy: int = 0
    tables_in_result: int = 0
    semantic_search_ms: float = 0.0
    keyword_search_ms: float = 0.0
    fk_walk_ms: float = 0.0
    rbac_filter_ms: float = 0.0
    policy_resolution_ms: float = 0.0
    column_scoping_ms: float = 0.0
    total_latency_ms: float = 0.0
    embedding_cache_hit: bool = False
    schema_cache_hit: bool = False
    token_count: int = 0
    tables_truncated: int = 0


# ── Final retrieval result (output to L5) ───────────────────


class RetrievalResult(BaseModel):
    """The complete output of the L3 retrieval pipeline.

    This is the security-scoped schema package that L5 receives.
    The LLM must ONLY see what is in this result.
    """

    model_config = ConfigDict()

    request_id: str
    user_id: str
    original_question: str
    preprocessed_question: str
    intent: IntentResult

    # Filtered schema
    filtered_schema: list[FilteredTable] = Field(default_factory=list)
    join_graph: JoinGraph = Field(default_factory=JoinGraph)

    # Policy rules in natural language for LLM instruction
    nl_policy_rules: list[str] = Field(default_factory=list)

    # Signed permission envelope from L4, forwarded for L5/L6/L7 verification.
    permission_envelope: PermissionEnvelope | None = None

    # Security summary (no details about denied tables)
    denied_tables_count: int = 0

    # Pipeline metadata
    retrieval_metadata: RetrievalMetadata = Field(default_factory=RetrievalMetadata)

    # Timestamp
    resolved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
