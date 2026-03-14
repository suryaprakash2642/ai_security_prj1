"""PostgreSQL audit repository — append-only change log, policy versions, crawl history."""

from __future__ import annotations

import json
import ssl
from pathlib import Path
from datetime import datetime
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.models.audit import ChangeRecord, CrawlRecord, PolicyVersionRecord

logger = structlog.get_logger(__name__)


class AuditRepository:
    """Append-only audit log in PostgreSQL."""

    def __init__(self, settings: Settings) -> None:
        self._engine: AsyncEngine | None = None
        self._session_factory: sessionmaker | None = None
        self._settings = settings
        self._api_access_log_ready: bool = False
        self._api_access_log_disabled: bool = False

    async def connect(self) -> None:
        dsn = self._settings.pg_audit_dsn
        # asyncpg does not accept `sslmode` as a URL query parameter.
        # For remote hosts (e.g. Timescale Cloud) strip it from the DSN and
        # pass a proper SSL context via connect_args instead.
        clean_dsn = dsn.split("?")[0] if "?" in dsn else dsn
        use_ssl = self._settings.pg_ssl and "localhost" not in clean_dsn and "127.0.0.1" not in clean_dsn
        if use_ssl:
            # For cloud-hosted PostgreSQL (Aiven, Timescale, etc.), use SSL.
            # Use pinned CA only when explicitly configured; otherwise fall back
            # to permissive SSL for environments with self-signed chains.
            ca_path = (self._settings.pg_audit_ca_cert_path or "").strip()
            if ca_path:
                ssl_ctx = ssl.create_default_context(cafile=ca_path)
            else:
                ssl_ctx = ssl.create_default_context()
                ssl_ctx.check_hostname = False
                ssl_ctx.verify_mode = ssl.CERT_NONE
            connect_args = {"ssl": ssl_ctx}
        else:
            connect_args = {}

        self._engine = create_async_engine(
            clean_dsn,
            pool_size=self._settings.pg_pool_min,
            max_overflow=self._settings.pg_pool_max - self._settings.pg_pool_min,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
        self._session_factory = sessionmaker(
            self._engine, class_=AsyncSession, expire_on_commit=False
        )
        await self._ensure_api_access_log_table()
        logger.info("audit_db_connected")

    async def close(self) -> None:
        if self._engine:
            await self._engine.dispose()
            logger.info("audit_db_disconnected")

    def _get_session(self) -> AsyncSession:
        if not self._session_factory:
            raise RuntimeError("Audit DB not connected")
        return self._session_factory()

    # ── Graph version ────────────────────────────────────────

    async def increment_graph_version(self, updated_by: str, description: str = "") -> int:
        async with self._get_session() as session:
            result = await session.execute(
                text("""
                    UPDATE graph_version
                    SET version = version + 1, updated_at = NOW(),
                        updated_by = :updated_by, description = :description
                    RETURNING version
                """),
                {"updated_by": updated_by, "description": description},
            )
            row = result.fetchone()
            await session.commit()
            return row[0] if row else 0

    async def get_graph_version(self) -> dict[str, Any]:
        async with self._get_session() as session:
            result = await session.execute(
                text("SELECT version, updated_at, updated_by FROM graph_version LIMIT 1")
            )
            row = result.fetchone()
            if row:
                return {"version": row[0], "updated_at": row[1], "updated_by": row[2]}
            return {"version": 0, "updated_at": None, "updated_by": "unknown"}

    # ── Change log ───────────────────────────────────────────

    async def log_change(self, record: ChangeRecord, graph_version: int) -> None:
        async with self._get_session() as session:
            await session.execute(
                text("""
                    INSERT INTO graph_change_log
                        (graph_version, node_type, node_id, action,
                         changed_properties, old_values, new_values,
                         changed_by, change_source)
                    VALUES
                        (:gv, :nt, :nid, :action, :cp, :ov, :nv, :cb, :cs)
                """),
                {
                    "gv": graph_version,
                    "nt": record.node_type,
                    "nid": record.node_id,
                    "action": record.action.value,
                    "cp": json.dumps(record.changed_properties),
                    "ov": json.dumps(record.old_values),
                    "nv": json.dumps(record.new_values),
                    "cb": record.changed_by,
                    "cs": record.change_source.value,
                },
            )
            await session.commit()

    async def log_changes_batch(
        self, records: list[ChangeRecord], graph_version: int
    ) -> None:
        if not records:
            return
        async with self._get_session() as session:
            for record in records:
                await session.execute(
                    text("""
                        INSERT INTO graph_change_log
                            (graph_version, node_type, node_id, action,
                             changed_properties, old_values, new_values,
                             changed_by, change_source)
                        VALUES
                            (:gv, :nt, :nid, :action, :cp, :ov, :nv, :cb, :cs)
                    """),
                    {
                        "gv": graph_version,
                        "nt": record.node_type,
                        "nid": record.node_id,
                        "action": record.action.value,
                        "cp": json.dumps(record.changed_properties),
                        "ov": json.dumps(record.old_values),
                        "nv": json.dumps(record.new_values),
                        "cb": record.changed_by,
                        "cs": record.change_source.value,
                    },
                )
            await session.commit()
            logger.info("audit_batch_logged", count=len(records))

    # ── Policy versions ──────────────────────────────────────

    async def save_policy_version(self, record: PolicyVersionRecord) -> None:
        async with self._get_session() as session:
            await session.execute(
                text("""
                    INSERT INTO policy_versions
                        (policy_id, version, policy_type, nl_description,
                         structured_rule, priority, is_active, created_by)
                    VALUES
                        (:pid, :ver, :pt, :nl, :sr, :pri, :active, :cb)
                """),
                {
                    "pid": record.policy_id,
                    "ver": record.version,
                    "pt": record.policy_type,
                    "nl": record.nl_description,
                    "sr": json.dumps(record.structured_rule),
                    "pri": record.priority,
                    "active": record.is_active,
                    "cb": record.created_by,
                },
            )
            await session.commit()

    async def get_policy_version(self, policy_id: str, version: int) -> dict[str, Any] | None:
        async with self._get_session() as session:
            result = await session.execute(
                text("""
                    SELECT policy_id, version, policy_type, nl_description,
                           structured_rule, priority, is_active, created_by, created_at
                    FROM policy_versions
                    WHERE policy_id = :pid AND version = :ver
                """),
                {"pid": policy_id, "ver": version},
            )
            row = result.fetchone()
            if row:
                return {
                    "policy_id": row[0], "version": row[1], "policy_type": row[2],
                    "nl_description": row[3], "structured_rule": row[4],
                    "priority": row[5], "is_active": row[6],
                    "created_by": row[7], "created_at": row[8],
                }
            return None

    async def get_policy_history(self, policy_id: str) -> list[dict[str, Any]]:
        async with self._get_session() as session:
            result = await session.execute(
                text("""
                    SELECT version, policy_type, is_active, created_by, created_at
                    FROM policy_versions
                    WHERE policy_id = :pid
                    ORDER BY version DESC
                """),
                {"pid": policy_id},
            )
            return [
                {"version": r[0], "policy_type": r[1], "is_active": r[2],
                 "created_by": r[3], "created_at": r[4]}
                for r in result.fetchall()
            ]

    # ── Crawl history ────────────────────────────────────────

    async def start_crawl(self, record: CrawlRecord) -> int:
        async with self._get_session() as session:
            result = await session.execute(
                text("""
                    INSERT INTO crawl_history (database_name, status, triggered_by)
                    VALUES (:db, 'running', :by)
                    RETURNING id
                """),
                {"db": record.database_name, "by": record.triggered_by},
            )
            row = result.fetchone()
            await session.commit()
            return row[0] if row else 0

    async def complete_crawl(
        self, crawl_id: int, record: CrawlRecord
    ) -> None:
        async with self._get_session() as session:
            await session.execute(
                text("""
                    UPDATE crawl_history
                    SET status = :status,
                        tables_found = :tf, tables_added = :ta,
                        tables_updated = :tu, tables_deactivated = :td,
                        columns_found = :cf, columns_added = :ca,
                        columns_updated = :cu, errors = :errors,
                        completed_at = NOW()
                    WHERE id = :id
                """),
                {
                    "id": crawl_id,
                    "status": record.status,
                    "tf": record.tables_found,
                    "ta": record.tables_added,
                    "tu": record.tables_updated,
                    "td": record.tables_deactivated,
                    "cf": record.columns_found,
                    "ca": record.columns_added,
                    "cu": record.columns_updated,
                    "errors": json.dumps(record.errors),
                },
            )
            await session.commit()

    # ── Classification review queue ──────────────────────────

    async def add_review_item(
        self,
        column_fqn: str,
        suggested_sensitivity: int,
        suggested_pii_type: str | None,
        suggested_masking: str | None,
        confidence: float,
        reason: str,
    ) -> int:
        async with self._get_session() as session:
            result = await session.execute(
                text("""
                    INSERT INTO classification_review_queue
                        (column_fqn, suggested_sensitivity, suggested_pii_type,
                         suggested_masking, confidence, reason)
                    VALUES (:fqn, :sens, :pii, :mask, :conf, :reason)
                    RETURNING id
                """),
                {
                    "fqn": column_fqn,
                    "sens": suggested_sensitivity,
                    "pii": suggested_pii_type,
                    "mask": suggested_masking,
                    "conf": confidence,
                    "reason": reason,
                },
            )
            row = result.fetchone()
            await session.commit()
            return row[0] if row else 0

    async def get_pending_reviews(self, limit: int = 50) -> list[dict[str, Any]]:
        async with self._get_session() as session:
            result = await session.execute(
                text("""
                    SELECT id, column_fqn, suggested_sensitivity, suggested_pii_type,
                           suggested_masking, confidence, reason, status, created_at
                    FROM classification_review_queue
                    WHERE status = 'pending'
                    ORDER BY confidence ASC, created_at ASC
                    LIMIT :limit
                """),
                {"limit": limit},
            )
            return [
                {
                    "id": r[0], "column_fqn": r[1], "suggested_sensitivity": r[2],
                    "suggested_pii_type": r[3], "suggested_masking": r[4],
                    "confidence": r[5], "reason": r[6], "status": r[7], "created_at": r[8],
                }
                for r in result.fetchall()
            ]

    async def approve_review(self, review_id: int, reviewer: str) -> None:
        async with self._get_session() as session:
            await session.execute(
                text("""
                    UPDATE classification_review_queue
                    SET status = 'approved', reviewed_by = :reviewer, reviewed_at = NOW()
                    WHERE id = :id
                """),
                {"id": review_id, "reviewer": reviewer},
            )
            await session.commit()

    async def reject_review(self, review_id: int, reviewer: str) -> None:
        async with self._get_session() as session:
            await session.execute(
                text("""
                    UPDATE classification_review_queue
                    SET status = 'rejected', reviewed_by = :reviewer, reviewed_at = NOW()
                    WHERE id = :id
                """),
                {"id": review_id, "reviewer": reviewer},
            )
            await session.commit()

    # ── Health check ─────────────────────────────────────────

    async def health_check(self) -> bool:
        try:
            async with self._get_session() as session:
                result = await session.execute(text("SELECT 1"))
                return result.fetchone() is not None
        except Exception:
            return False

    # ── Aliases for admin routes ──────────────────────────────

    async def get_current_version(self) -> dict[str, Any]:
        return await self.get_graph_version()

    async def get_changes(
        self,
        node_type: str | None = None,
        node_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit, "nt": node_type, "nid": node_id}
        async with self._get_session() as session:
            result = await session.execute(
                text("""
                    SELECT id, graph_version, node_type, node_id, action,
                           changed_properties, old_values, new_values,
                           changed_by, change_source, created_at
                    FROM graph_change_log
                    WHERE (:nt IS NULL OR node_type = :nt)
                      AND (:nid IS NULL OR node_id = :nid)
                    ORDER BY created_at DESC
                    LIMIT :limit
                """),
                params,
            )
            return [
                {
                    "id": r[0], "graph_version": r[1], "node_type": r[2],
                    "node_id": r[3], "action": r[4],
                    "changed_properties": r[5], "old_values": r[6],
                    "new_values": r[7], "changed_by": r[8],
                    "change_source": r[9], "created_at": r[10],
                }
                for r in result.fetchall()
            ]

    # ── API access logging ────────────────────────────────────

    async def log_api_access(
        self,
        service_id: str,
        endpoint: str,
        method: str,
        status_code: int,
        latency_ms: float,
    ) -> None:
        """Log an API access event to the api_access_log table."""
        if self._api_access_log_disabled:
            return

        async with self._get_session() as session:
            params = {
                "sid": service_id,
                "ep": endpoint,
                "method": method,
                "sc": status_code,
                "lat": latency_ms,
            }
            try:
                await session.execute(
                    text("""
                        INSERT INTO api_access_log
                            (service_id, endpoint, method, status_code, latency_ms)
                        VALUES (:sid, :ep, :method, :sc, :lat)
                    """),
                    params,
                )
                await session.commit()
            except ProgrammingError as exc:
                msg = str(exc).lower()
                if "api_access_log" in msg and "does not exist" in msg:
                    await session.rollback()
                    await self._ensure_api_access_log_table()
                    try:
                        await session.execute(
                            text("""
                                INSERT INTO api_access_log
                                    (service_id, endpoint, method, status_code, latency_ms)
                                VALUES (:sid, :ep, :method, :sc, :lat)
                            """),
                            params,
                        )
                        await session.commit()
                        return
                    except Exception as retry_exc:
                        await session.rollback()
                        self._api_access_log_disabled = True
                        logger.warning(
                            "api_access_log_disabled",
                            reason="create_or_retry_failed",
                            error=str(retry_exc),
                        )
                        return
                raise

    async def _ensure_api_access_log_table(self) -> None:
        """Ensure API access audit table exists in the connected audit DB."""
        if self._api_access_log_ready or self._api_access_log_disabled:
            return

        try:
            async with self._get_session() as session:
                await session.execute(
                    text("""
                        CREATE TABLE IF NOT EXISTS api_access_log (
                            id BIGSERIAL PRIMARY KEY,
                            service_id VARCHAR(100) NOT NULL,
                            endpoint VARCHAR(200) NOT NULL,
                            method VARCHAR(10) NOT NULL,
                            status_code INT NOT NULL,
                            latency_ms FLOAT NOT NULL,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )
                    """)
                )
                await session.execute(
                    text("CREATE INDEX IF NOT EXISTS idx_api_access_time ON api_access_log (created_at DESC)")
                )
                await session.execute(
                    text("CREATE INDEX IF NOT EXISTS idx_api_access_service ON api_access_log (service_id)")
                )
                await session.commit()
                self._api_access_log_ready = True
                logger.info("api_access_log_ready")
        except Exception as exc:
            self._api_access_log_disabled = True
            logger.warning("api_access_log_setup_failed", error=str(exc))
