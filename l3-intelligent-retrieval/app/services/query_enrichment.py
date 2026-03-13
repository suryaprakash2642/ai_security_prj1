"""Query Enrichment Service — extracts metadata from questions for better retrieval.

Uses an LLM call (Azure OpenAI) with structured JSON output to extract
table hints, database hints, synonyms, and suggested dialect.

The LLM prompt is dynamically built from the actual graph metadata
(databases, domains, table counts) fetched from L2 at startup — no
hardcoded database or table lists.

Falls back gracefully: if LLM is unavailable the pipeline continues
with unenriched retrieval (same behavior as before this feature).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os

import httpx
import structlog

from app.config import Settings
from app.models.l2_models import L2DatabaseInfo
from app.models.retrieval import EnrichedQuery

logger = structlog.get_logger(__name__)


class QueryEnrichmentService:
    """Enriches questions with metadata for better retrieval.

    All database/table knowledge is loaded dynamically from L2 at startup.
    Nothing is hardcoded.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._http_client: httpx.AsyncClient | None = None
        self._cache: dict[str, EnrichedQuery] = {}
        # Populated at startup from L2 graph metadata
        self._db_catalog: list[L2DatabaseInfo] = []
        self._system_prompt: str = ""

    async def connect(self) -> None:
        self._http_client = httpx.AsyncClient(timeout=5.0)

    async def close(self) -> None:
        if self._http_client:
            await self._http_client.aclose()

    async def load_catalog(self, databases: list[L2DatabaseInfo]) -> None:
        """Load database catalog from L2 and build a dynamic LLM prompt."""
        self._db_catalog = databases
        self._system_prompt = self._build_system_prompt(databases)
        logger.info(
            "enrichment_catalog_loaded",
            database_count=len(databases),
            databases=[d.name for d in databases],
        )

    def _build_system_prompt(self, databases: list[L2DatabaseInfo]) -> str:
        """Dynamically build the LLM system prompt from graph metadata."""
        db_descriptions = []
        for db in databases:
            domains_str = ", ".join(db.domains) if db.domains else "unknown"
            db_descriptions.append(
                f"- {db.name} ({db.engine}): {db.table_count} tables, "
                f"domains=[{domains_str}]"
            )
        db_section = "\n".join(db_descriptions) if db_descriptions else "- No databases discovered"

        return f"""\
You extract structured metadata from a user's natural language database question.
Return ONLY valid JSON with these fields:
{{
  "table_hints": ["exact_table_name", ...],
  "database_hints": ["database_name", ...],
  "synonyms": ["synonym_phrase", ...],
  "entity_references": {{"facility_id": "FAC-001", ...}},
  "suggested_dialect": "mysql" | "postgresql" | null,
  "rewritten_query": "optimized search query",
  "confidence": 0.0-1.0
}}

Known databases in this system:
{db_section}

Rules:
- table_hints: likely table names (snake_case) the question refers to
- database_hints: which database(s) the question targets — match from the list above
- synonyms: 3-5 alternative phrasings of core concepts for embedding search
- suggested_dialect: infer from target database engine (mysql for MySQL DBs, postgresql for PostgreSQL DBs)
- rewritten_query: rephrase for better embedding search (expand abbreviations, add context)
- confidence: your confidence in the extraction (0.0-1.0)
- If you cannot determine the database, leave database_hints empty and set confidence low
"""

    async def enrich(self, question: str, intent_value: str = "") -> EnrichedQuery:
        """Enrich a question with metadata via LLM.

        Returns an unenriched default if LLM is unavailable — the pipeline
        will proceed with standard vector search without pre-filtering.
        """
        cache_key = hashlib.sha256(question.encode()).hexdigest()[:16]
        if cache_key in self._cache:
            return self._cache[cache_key]

        result: EnrichedQuery | None = None
        if self._system_prompt:
            try:
                result = await asyncio.wait_for(
                    self._llm_enrich(question), timeout=2.0,
                )
            except (asyncio.TimeoutError, Exception) as exc:
                logger.debug("enrichment_llm_unavailable", error=str(exc))

        if result is None:
            result = EnrichedQuery(
                original_question=question,
                rewritten_query=question,
                confidence=0.0,
            )

        self._cache[cache_key] = result
        # Keep cache bounded
        if len(self._cache) > 500:
            oldest = next(iter(self._cache))
            del self._cache[oldest]

        logger.info(
            "query_enriched",
            database_hints=result.database_hints,
            table_hints=result.table_hints,
            suggested_dialect=result.suggested_dialect,
            confidence=result.confidence,
        )
        return result

    async def _llm_enrich(self, question: str) -> EnrichedQuery | None:
        """Call Azure OpenAI for structured enrichment."""
        azure_endpoint = (
            self._settings.embedding_azure_endpoint
            or os.getenv("AZURE_AI_ENDPOINT", "").rstrip("/")
        )
        azure_api_key = (
            self._settings.embedding_azure_api_key
            or os.getenv("AZURE_AI_API_KEY", "")
        )

        if not azure_endpoint or not azure_api_key or not self._http_client:
            return None

        url = (
            f"{azure_endpoint}/openai/deployments/"
            "gpt-4.1-mini/chat/completions?api-version=2024-02-01"
        )

        body = {
            "messages": [
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": question},
            ],
            "temperature": 0.0,
            "max_tokens": 500,
            "response_format": {"type": "json_object"},
        }

        resp = await self._http_client.post(
            url, headers={"api-key": azure_api_key}, json=body,
        )
        resp.raise_for_status()

        content = resp.json()["choices"][0]["message"]["content"]
        data = json.loads(content)

        return EnrichedQuery(
            original_question=question,
            rewritten_query=data.get("rewritten_query", ""),
            synonyms=data.get("synonyms", []),
            table_hints=data.get("table_hints", []),
            database_hints=data.get("database_hints", []),
            entity_references=data.get("entity_references", {}),
            suggested_dialect=data.get("suggested_dialect"),
            confidence=data.get("confidence", 0.5),
        )
