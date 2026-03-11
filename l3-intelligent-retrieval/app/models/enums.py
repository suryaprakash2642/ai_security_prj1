"""Enumerated types for the L3 Intelligent Retrieval Layer."""

from __future__ import annotations

from enum import Enum


class QueryIntent(str, Enum):
    """Classified intent of the natural-language question."""
    DATA_LOOKUP = "DATA_LOOKUP"
    AGGREGATION = "AGGREGATION"
    COMPARISON = "COMPARISON"
    TREND = "TREND"
    JOIN_QUERY = "JOIN_QUERY"
    EXISTENCE_CHECK = "EXISTENCE_CHECK"
    DEFINITION = "DEFINITION"


class DomainHint(str, Enum):
    """Domain areas hinted by the question text."""
    CLINICAL = "clinical"
    BILLING = "billing"
    PHARMACY = "pharmacy"
    LABORATORY = "laboratory"
    HR = "hr"
    SCHEDULING = "scheduling"


class ColumnVisibility(str, Enum):
    """Column-level access classification after policy resolution."""
    VISIBLE = "VISIBLE"
    MASKED = "MASKED"
    HIDDEN = "HIDDEN"
    COMPUTED = "COMPUTED"


class TableDecision(str, Enum):
    """Per-table access decision from L4 policy resolution."""
    ALLOW = "ALLOW"
    DENY = "DENY"
    MASK = "MASK"
    FILTER = "FILTER"


class RetrievalStrategy(str, Enum):
    """Which retrieval strategy contributed a candidate table."""
    SEMANTIC = "SEMANTIC"
    KEYWORD = "KEYWORD"
    FK_WALK = "FK_WALK"


class RetrievalErrorCode(str, Enum):
    """Structured error codes for retrieval failures."""
    INVALID_QUESTION = "INVALID_QUESTION"
    INVALID_SECURITY_CONTEXT = "INVALID_SECURITY_CONTEXT"
    NO_RELEVANT_TABLES = "NO_RELEVANT_TABLES"
    RESTRICTED_DATA_REQUEST = "RESTRICTED_DATA_REQUEST"
    EMBEDDING_SERVICE_UNAVAILABLE = "EMBEDDING_SERVICE_UNAVAILABLE"
    KNOWLEDGE_GRAPH_UNAVAILABLE = "KNOWLEDGE_GRAPH_UNAVAILABLE"
    POLICY_SERVICE_UNAVAILABLE = "POLICY_SERVICE_UNAVAILABLE"
    TOKEN_BUDGET_EXCEEDED = "TOKEN_BUDGET_EXCEEDED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class EmbeddingProvider(str, Enum):
    """Supported embedding API providers."""
    VOYAGE = "voyage"
    OPENAI = "openai"


class ServiceRole(str, Enum):
    """Roles for inter-service authentication."""
    PIPELINE_READER = "pipeline_reader"
    POLICY_RESOLVER = "policy_resolver"
    ADMIN = "admin"
