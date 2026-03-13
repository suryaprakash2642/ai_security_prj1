"""Retrieval Orchestrator — coordinates the full L3 pipeline.

Pipeline stages:
1. Validate SecurityContext
2. Embed question
3. Classify intent
4. Multi-strategy retrieval
5. Domain-aware ranking
6. RBAC domain pre-filter + L4 policy resolution
7. Column-level scoping
8. Join graph construction
9. Context assembly with token budget

Fail-secure at every stage.
"""

from __future__ import annotations

import time
import uuid

import structlog

from app.auth import validate_request_context
from app.config import Settings
from app.models.api import RetrievalRequest
from app.models.enums import RetrievalErrorCode
from app.models.retrieval import RetrievalMetadata, RetrievalResult
from app.services.audit_logger import (
    log_break_glass_access,
    log_retrieval_metrics,
    log_sensitivity5_attempt,
    validate_break_glass_ttl,
)
from app.services.column_scoper import ColumnScoper
from app.services.context_assembler import ContextAssembler
from app.services.dialect_detector import DialectDetector
from app.services.embedding_engine import EmbeddingEngine
from app.services.intent_classifier import IntentClassifier
from app.services.join_graph import JoinGraphBuilder
from app.services.query_enrichment import QueryEnrichmentService
from app.services.ranking_engine import RankingEngine
from app.services.rbac_filter import RBACFilter
from app.services.retrieval_pipeline import RetrievalPipeline

logger = structlog.get_logger(__name__)


class RetrievalError(Exception):
    """Structured retrieval error with error code."""

    def __init__(self, code: RetrievalErrorCode, message: str, status: int = 400) -> None:
        self.code = code
        self.message = message
        self.status = status
        super().__init__(message)


class RetrievalOrchestrator:
    """Coordinates the full retrieval pipeline."""

    def __init__(
        self,
        settings: Settings,
        embedding_engine: EmbeddingEngine,
        intent_classifier: IntentClassifier,
        retrieval_pipeline: RetrievalPipeline,
        ranking_engine: RankingEngine,
        rbac_filter: RBACFilter,
        column_scoper: ColumnScoper,
        join_graph_builder: JoinGraphBuilder,
        context_assembler: ContextAssembler,
        enrichment_service: QueryEnrichmentService | None = None,
        dialect_detector: DialectDetector | None = None,
    ) -> None:
        self._settings = settings
        self._embedding = embedding_engine
        self._intent = intent_classifier
        self._retrieval = retrieval_pipeline
        self._ranking = ranking_engine
        self._rbac = rbac_filter
        self._scoper = column_scoper
        self._join = join_graph_builder
        self._assembler = context_assembler
        self._enrichment = enrichment_service
        self._dialect = dialect_detector or DialectDetector()

    async def resolve(self, request: RetrievalRequest) -> RetrievalResult:
        """Execute the full retrieval pipeline.

        Raises:
            RetrievalError: on any structured failure
        """
        start = time.monotonic()
        request_id = request.request_id or str(uuid.uuid4())
        metadata = RetrievalMetadata()

        logger.info(
            "retrieval_started",
            request_id=request_id,
            user_id=request.security_context.user_id,
        )

        # ── Stage 1: Validate SecurityContext ───────────────
        try:
            validate_request_context(request.security_context, self._settings)
        except Exception:
            raise RetrievalError(
                RetrievalErrorCode.INVALID_SECURITY_CONTEXT,
                "Invalid or expired security context",
                status=401,
            )

        ctx = request.security_context

        # ── Break-glass: emit dedicated audit event + TTL check (Fix 5 / §13.3) ──
        if ctx.break_glass:
            ttl_valid = validate_break_glass_ttl(
                context_expiry=ctx.context_expiry,
                request_id=request_id,
                user_id=ctx.user_id,
            )
            if not ttl_valid:
                raise RetrievalError(
                    RetrievalErrorCode.INVALID_SECURITY_CONTEXT,
                    "Break-glass session exceeds maximum 15-minute window",
                    status=401,
                )
            log_break_glass_access(
                request_id=request_id,
                user_id=ctx.user_id,
                provider_id=ctx.provider_id,
                facility_id=ctx.facility_id,
                department=ctx.department,
                unit_id=ctx.unit_id,
                session_id=ctx.session_id,
                purpose=ctx.purpose,
                context_expiry=ctx.context_expiry,
            )

        # ── Stage 2: Embed question ─────────────────────────
        try:
            preprocessed, embedding, cache_hit = await self._embedding.embed_question(
                request.question, ctx,
            )
            metadata.embedding_cache_hit = cache_hit
        except RuntimeError:
            raise RetrievalError(
                RetrievalErrorCode.EMBEDDING_SERVICE_UNAVAILABLE,
                "Embedding service unavailable",
                status=503,
            )

        # ── Stage 3: Classify intent ────────────────────────
        intent = self._intent.classify(preprocessed)
        logger.info(
            "intent_classified",
            intent=intent.intent.value,
            confidence=intent.confidence,
            domains=[d.value for d in intent.domain_hints],
        )

        # ── Stage 3.5: Query enrichment ────────────────────
        enriched = None
        if self._enrichment:
            try:
                enriched = await self._enrichment.enrich(preprocessed, intent.intent.value)
                logger.info(
                    "query_enriched",
                    request_id=request_id,
                    database_hints=enriched.database_hints,
                    table_hints=enriched.table_hints,
                    suggested_dialect=enriched.suggested_dialect,
                )
            except Exception as exc:
                logger.warning("enrichment_failed", error=str(exc))

        # ── Stage 4: Multi-strategy retrieval ───────────────
        try:
            candidates, retrieval_timing = await self._retrieval.retrieve_candidates(
                preprocessed, embedding, intent, request.max_tables,
                clearance_level=ctx.clearance_level,  # Fix 1: scope cache by clearance
                enriched=enriched,
            )
            metadata.semantic_search_ms = retrieval_timing.get("semantic_ms", 0)
            metadata.keyword_search_ms = retrieval_timing.get("keyword_ms", 0)
            metadata.fk_walk_ms = retrieval_timing.get("fk_walk_ms", 0)
            metadata.total_candidates_found = len(candidates)
        except Exception as exc:
            logger.error("retrieval_failed", error=str(exc))
            raise RetrievalError(
                RetrievalErrorCode.KNOWLEDGE_GRAPH_UNAVAILABLE,
                "Schema retrieval failed",
                status=503,
            )

        if not candidates:
            raise RetrievalError(
                RetrievalErrorCode.NO_RELEVANT_TABLES,
                "No relevant tables found for the question",
                status=404,
            )

        # ── Stage 5: Domain-aware ranking ───────────────────
        # Get accessible domains for ranking context
        accessible_domains: set[str] = set()
        try:
            role_map = await self._rbac._l2.get_role_domain_access(ctx.effective_roles)
            for domains in role_map.values():
                accessible_domains.update(domains)
        except Exception:
            pass

        ranked = self._ranking.rank(candidates, intent, accessible_domains, enriched=enriched)

        # ── Stage 6: RBAC filtering + L4 resolution ─────────
        try:
            surviving, envelope, rbac_timing = await self._rbac.filter_candidates(
                ranked, ctx, request_id,
            )
            # SECURITY: The PermissionEnvelope (envelope) MUST NEVER be cached.
            # It is a per-request, per-user policy decision. Caching it and
            # serving it to a different user or a subsequent request would be a
            # critical privilege escalation vulnerability — a user could receive
            # another user's column visibility, row filters, and masking rules.
            # Each call to filter_candidates() must resolve fresh from L4.
            metadata.rbac_filter_ms = sum(rbac_timing.values())
            metadata.candidates_after_rbac = len(surviving)
            metadata.candidates_after_policy = len(surviving)
        except RuntimeError as exc:
            if "unreachable" in str(exc).lower() or "failed" in str(exc).lower():
                raise RetrievalError(
                    RetrievalErrorCode.POLICY_SERVICE_UNAVAILABLE,
                    "Policy resolution service unavailable",
                    status=503,
                )
            raise

        denied_count = metadata.total_candidates_found - len(surviving)

        if not surviving:
            # Check if this looks like a restricted data attempt (§13.3)
            if any(c.sensitivity_level >= 5 for c in ranked):
                log_sensitivity5_attempt(
                    request_id=request_id,
                    user_id=ctx.user_id,
                    effective_roles=ctx.effective_roles,
                    candidate_table_ids=[c.table_id for c in ranked if c.sensitivity_level >= 5],
                )
                raise RetrievalError(
                    RetrievalErrorCode.RESTRICTED_DATA_REQUEST,
                    "Insufficient permissions for requested data",
                    status=403,
                )
            raise RetrievalError(
                RetrievalErrorCode.NO_RELEVANT_TABLES,
                "No accessible tables found for the question",
                status=404,
            )

        # ── Stage 7: Column-level scoping ───────────────────
        filtered_tables, scoping_ms = await self._scoper.scope_tables(
            surviving, envelope,
        )
        metadata.column_scoping_ms = scoping_ms

        # ── Stage 8: Join graph construction ────────────────
        join_graph = await self._join.build(filtered_tables, surviving, envelope)

        # ── Stage 9: Context assembly ───────────────────────
        result = self._assembler.assemble(
            request_id=request_id,
            user_id=ctx.user_id,
            original_question=request.question,
            preprocessed_question=preprocessed,
            intent=intent,
            filtered_tables=filtered_tables,
            join_graph=join_graph,
            envelope=envelope,
            denied_count=denied_count,
            metadata=metadata,
            max_tables=request.max_tables,
        )

        # ── Stage 9.5: Dialect detection ─────────────────────
        # Stamp each table with its dialect from its FQN, then pick the
        # global dialect from the top table for backward compatibility.
        detected_dialect, target_database = self._dialect.detect(
            filtered_tables, enriched,
        )
        # Also stamp the final assembled tables (may differ after budget trim)
        self._dialect.stamp_tables(result.filtered_schema)
        result.detected_dialect = detected_dialect
        result.target_database = target_database
        result.database_metadata = self._dialect.get_database_metadata(
            result.filtered_schema,
        )
        logger.info(
            "dialect_detected",
            request_id=request_id,
            detected_dialect=detected_dialect,
            target_database=target_database,
            database_metadata=result.database_metadata,
            per_table={t.table_id: t.dialect for t in result.filtered_schema},
        )

        metadata.total_latency_ms = (time.monotonic() - start) * 1000

        logger.info(
            "retrieval_completed",
            request_id=request_id,
            user_id=ctx.user_id,
            tables=len(filtered_tables),
            denied=denied_count,
            latency_ms=round(metadata.total_latency_ms, 2),
        )

        # Debug: log schema summary so downstream issues can be diagnosed
        logger.info(
            "retrieval_schema_debug",
            request_id=request_id,
            table_ids=[t.table_id for t in filtered_tables],
            tables_detail=[
                {
                    "table_id": t.table_id,
                    "columns": [c.name for c in (t.visible_columns or [])],
                    "row_filters": t.row_filters or [],
                    "relevance_score": round(getattr(t, "relevance_score", 0), 4),
                }
                for t in filtered_tables
            ],
            join_edges=[
                {
                    "from": f"{e.source_table}.{e.source_column}",
                    "to": f"{e.target_table}.{e.target_column}",
                }
                for e in (join_graph.edges if join_graph else [])
            ],
        )

        # Spec §16 step 12: log retrieval metrics to audit system (Fix 5)
        log_retrieval_metrics(
            request_id=request_id,
            user_id=ctx.user_id,
            tables_in_result=len(filtered_tables),
            denied_count=denied_count,
            total_latency_ms=metadata.total_latency_ms,
            strategies_used=[
                s.value for s in set(
                    strat
                    for t in (candidates if candidates else [])
                    for strat in getattr(t, "contributing_strategies", [])
                )
            ],
        )

        return result
