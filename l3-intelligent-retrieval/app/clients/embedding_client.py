"""Embedding provider client — Azure OpenAI primary, Voyage fallback, OpenAI last-resort.

Handles:
- L2 normalization of embedding vectors
- Provider failover (Azure -> Voyage -> Standard OpenAI)
- Error handling with fail-secure semantics
"""

from __future__ import annotations

import math

import httpx
import structlog

from app.config import Settings

logger = structlog.get_logger(__name__)


def _l2_normalize(vec: list[float]) -> list[float]:
    """Apply L2 normalization to the embedding vector."""
    norm = math.sqrt(sum(x * x for x in vec))
    if norm < 1e-12:
        return vec
    return [x / norm for x in vec]


def _truncate_or_pad(vec: list[float], dim: int) -> list[float]:
    """Ensure the vector matches expected dimensions."""
    if len(vec) >= dim:
        return vec[:dim]
    return vec + [0.0] * (dim - len(vec))


class EmbeddingClient:
    """Async client for generating text embeddings."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._http: httpx.AsyncClient | None = None

    async def connect(self) -> None:
        self._http = httpx.AsyncClient(timeout=httpx.Timeout(15.0))

    async def close(self) -> None:
        if self._http:
            await self._http.aclose()

    async def embed(self, text: str) -> list[float]:
        """Generate embedding with Azure -> Voyage -> OpenAI failover.

        Returns L2-normalized vector of configured dimensions.
        Raises RuntimeError if all providers fail.
        """
        providers = []

        # Azure OpenAI takes priority if configured
        if self._settings.embedding_azure_api_key and self._settings.embedding_azure_endpoint:
            providers.append(("azure", self._embed_azure))

        # Then Voyage and standard OpenAI based on settings
        providers.append((self._settings.embedding_primary_provider, self._embed_primary))
        providers.append((self._settings.embedding_fallback_provider, self._embed_fallback))

        last_error: Exception | None = None
        for name, fn in providers:
            try:
                raw = await fn(text)
                vec = _truncate_or_pad(raw, self._settings.embedding_dimensions)
                return _l2_normalize(vec)
            except Exception as exc:
                logger.warning("embedding_provider_failed", provider=name, error=str(exc))
                last_error = exc

        raise RuntimeError(
            f"All embedding providers failed. Last error: {last_error}"
        )

    async def _embed_azure(self, text: str) -> list[float]:
        """Azure OpenAI embedding -- uses api-key header, deployment-based URL."""
        api_key = self._settings.embedding_azure_api_key
        endpoint = self._settings.embedding_azure_endpoint.rstrip("/")
        deployment = self._settings.embedding_azure_deployment
        api_version = self._settings.embedding_azure_api_version

        if not api_key or not endpoint:
            raise RuntimeError("Azure OpenAI API key or endpoint not configured")

        if not self._http:
            raise RuntimeError("HTTP client not initialized")

        url = f"{endpoint}/openai/deployments/{deployment}/embeddings?api-version={api_version}"
        resp = await self._http.post(
            url,
            json={"input": text},
            headers={
                "api-key": api_key,
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["data"][0]["embedding"]

    async def _embed_primary(self, text: str) -> list[float]:
        """Voyage AI embedding."""
        api_key = self._settings.embedding_voyage_api_key
        if not api_key:
            raise RuntimeError("Voyage API key not configured")

        if not self._http:
            raise RuntimeError("HTTP client not initialized")

        resp = await self._http.post(
            "https://api.voyageai.com/v1/embeddings",
            json={
                "input": [text],
                "model": self._settings.embedding_voyage_model,
            },
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["data"][0]["embedding"]

    async def _embed_fallback(self, text: str) -> list[float]:
        """Standard OpenAI embedding fallback."""
        api_key = self._settings.embedding_openai_api_key
        if not api_key:
            raise RuntimeError("OpenAI API key not configured")

        if not self._http:
            raise RuntimeError("HTTP client not initialized")

        resp = await self._http.post(
            "https://api.openai.com/v1/embeddings",
            json={
                "input": text,
                "model": self._settings.embedding_openai_model,
                "dimensions": self._settings.embedding_dimensions,
            },
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["data"][0]["embedding"]

    async def health_check(self) -> bool:
        """Quick health check -- verifies HTTP client is usable."""
        return self._http is not None and not self._http.is_closed
