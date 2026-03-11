"""Question Embedding Engine — preprocess, expand, hash, embed, cache.

Preprocessing pipeline:
1. Normalize whitespace
2. Expand healthcare abbreviations (additive, original preserved)
3. Append user department + primary role as context suffix
4. SHA-256 hash for cache keying
5. Generate embedding via provider client
6. Cache result in Redis
"""

from __future__ import annotations

import hashlib
import re
import time

import structlog

from app.cache.cache_service import CacheService
from app.clients.embedding_client import EmbeddingClient
from app.config import Settings, load_abbreviations
from app.models.security import SecurityContext

logger = structlog.get_logger(__name__)


class EmbeddingEngine:
    """Preprocesses questions and generates cached embeddings."""

    def __init__(
        self,
        settings: Settings,
        embedding_client: EmbeddingClient,
        cache: CacheService,
    ) -> None:
        self._settings = settings
        self._client = embedding_client
        self._cache = cache
        self._abbreviations = load_abbreviations()

    def preprocess(self, question: str, context: SecurityContext) -> str:
        """Full preprocessing pipeline.

        Returns the preprocessed question text ready for embedding.
        """
        text = question.strip()

        # 1. Normalize whitespace
        text = _normalize_whitespace(text)

        # 2. Expand abbreviations (additive)
        text = self._expand_abbreviations(text)

        # 3. Append context suffix
        suffix_parts = []
        if context.department:
            suffix_parts.append(f"department:{context.department}")
        if context.effective_roles:
            suffix_parts.append(f"role:{context.effective_roles[0]}")

        if suffix_parts:
            text = f"{text} [{' '.join(suffix_parts)}]"

        return text

    def compute_cache_key(self, preprocessed_text: str) -> str:
        """SHA-256 hash of preprocessed question + model version for cache key."""
        model = self._settings.embedding_voyage_model
        raw = f"{preprocessed_text}|{model}|v{self._settings.embedding_dimensions}"
        return hashlib.sha256(raw.encode()).hexdigest()

    async def embed_question(
        self,
        question: str,
        context: SecurityContext,
    ) -> tuple[str, list[float], bool]:
        """Full embedding pipeline: preprocess → cache check → embed → cache store.

        Returns:
            (preprocessed_question, embedding_vector, cache_hit)

        Raises:
            RuntimeError: if embedding fails and no cached result available
        """
        preprocessed = self.preprocess(question, context)
        cache_key = self.compute_cache_key(preprocessed)

        # Check cache
        cached = await self._cache.get_embedding(cache_key)
        if cached is not None:
            logger.debug("embedding_cache_hit", key=cache_key[:12])
            return preprocessed, cached, True

        # Generate embedding
        start = time.monotonic()
        try:
            embedding = await self._client.embed(preprocessed)
        except RuntimeError as exc:
            logger.error("embedding_failed", error=str(exc))
            raise

        elapsed_ms = (time.monotonic() - start) * 1000
        logger.info("embedding_generated", latency_ms=round(elapsed_ms, 2))

        # Store in cache
        await self._cache.set_embedding(cache_key, embedding)

        return preprocessed, embedding, False

    def _expand_abbreviations(self, text: str) -> str:
        """Additively expand healthcare abbreviations.

        The original term is kept; its expansion is appended.
        E.g., "BP readings" → "BP (blood pressure) readings"
        """
        if not self._abbreviations:
            return text

        words = text.split()
        result_parts: list[str] = []

        for word in words:
            # Clean punctuation for matching
            clean = re.sub(r"[^\w/&]", "", word)

            # Try exact match (case-insensitive for common abbreviations)
            expansion = self._abbreviations.get(clean)
            if not expansion:
                expansion = self._abbreviations.get(clean.upper())
            if not expansion:
                # Try without trailing 's' for plurals
                expansion = self._abbreviations.get(clean.rstrip("s"))

            if expansion:
                result_parts.append(f"{word} ({expansion})")
            else:
                result_parts.append(word)

        return " ".join(result_parts)


def _normalize_whitespace(text: str) -> str:
    """Collapse multiple whitespace characters into single spaces."""
    return re.sub(r"\s+", " ", text).strip()
