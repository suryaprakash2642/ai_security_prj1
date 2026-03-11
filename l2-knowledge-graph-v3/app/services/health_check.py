"""Health Check Service — automated graph integrity validations.

Checks for:
- Orphan policies (no role binding or target)
- Circular role inheritance
- Missing domain assignments
- PII consistency (PII columns must have sensitivity >= 3)
- Masking consistency (PII columns should have a masking strategy)
- substance_abuse_records deny-only enforcement
- Neo4j connectivity
- PostgreSQL audit connectivity
"""

from __future__ import annotations

from typing import Any

import structlog

from app.models.api import HealthCheckResult
from app.repositories.audit_repository import AuditRepository
from app.repositories.graph_read_repo import GraphReadRepository
from app.repositories.neo4j_manager import Neo4jManager
from app.services.cache import CacheService

logger = structlog.get_logger(__name__)


class HealthCheckService:
    """Runs automated graph integrity and consistency checks."""

    def __init__(
        self,
        graph_reader: GraphReadRepository,
        neo4j: Neo4jManager,
        audit_repo: AuditRepository,
        cache: CacheService | None = None,
    ) -> None:
        self._reader = graph_reader
        self._neo4j = neo4j
        self._audit = audit_repo
        self._cache = cache

    async def run_all(self) -> list[HealthCheckResult]:
        """Execute all health checks and return results."""
        checks: list[HealthCheckResult] = []
        checks.append(await self.check_neo4j_connectivity())
        checks.append(await self.check_pg_connectivity())
        checks.append(await self.check_redis_connectivity())
        checks.append(await self.check_orphan_policies())
        checks.append(await self.check_circular_inheritance())
        checks.append(await self.check_missing_domain_assignment())
        checks.append(await self.check_pii_consistency())
        checks.append(await self.check_masking_consistency())
        checks.append(await self.check_substance_abuse_deny())
        return checks

    async def check_neo4j_connectivity(self) -> HealthCheckResult:
        """Verify Neo4j is reachable."""
        try:
            ok = await self._neo4j.health_check()
            return HealthCheckResult(
                check_name="neo4j_connectivity",
                passed=ok,
                details="Neo4j read driver responsive" if ok else "Neo4j health check failed",
            )
        except Exception as exc:
            return HealthCheckResult(
                check_name="neo4j_connectivity",
                passed=False,
                details=f"Neo4j unreachable: {exc}",
            )

    async def check_pg_connectivity(self) -> HealthCheckResult:
        """Verify PostgreSQL audit DB is reachable."""
        try:
            ok = await self._audit.health_check()
            return HealthCheckResult(
                check_name="pg_audit_connectivity",
                passed=ok,
                details="PostgreSQL audit DB responsive" if ok else "PostgreSQL health check failed",
            )
        except Exception as exc:
            return HealthCheckResult(
                check_name="pg_audit_connectivity",
                passed=False,
                details=f"PostgreSQL unreachable: {exc}",
            )

    async def check_redis_connectivity(self) -> HealthCheckResult:
        """Verify Redis cache is reachable."""
        if not self._cache:
            return HealthCheckResult(
                check_name="redis_connectivity",
                passed=True,
                details="Redis cache not configured (graceful degradation)",
            )
        try:
            ok = await self._cache.health_check()
            return HealthCheckResult(
                check_name="redis_connectivity",
                passed=ok,
                details="Redis cache responsive" if ok else "Redis health check failed",
            )
        except Exception as exc:
            return HealthCheckResult(
                check_name="redis_connectivity",
                passed=False,
                details=f"Redis unreachable: {exc}",
            )

    async def check_orphan_policies(self) -> HealthCheckResult:
        """Find policies with no role binding AND no table/domain target."""
        query = """
            MATCH (p:Policy)
            WHERE p.is_active = true
              AND NOT (p)-[:APPLIES_TO_ROLE]->()
              AND NOT (p)-[:GOVERNS_TABLE]->()
              AND NOT (p)-[:GOVERNS_DOMAIN]->()
              AND NOT (p)-[:GOVERNS_COLUMN]->()
            RETURN p.policy_id AS pid
        """
        try:
            records = await self._neo4j.execute_read(query)
            orphans = [r["pid"] for r in records]
            return HealthCheckResult(
                check_name="orphan_policies",
                passed=len(orphans) == 0,
                details=f"{len(orphans)} orphan policies found" if orphans else "No orphan policies",
                items=orphans,
            )
        except Exception as exc:
            return HealthCheckResult(
                check_name="orphan_policies", passed=False, details=f"Check failed: {exc}"
            )

    async def check_circular_inheritance(self) -> HealthCheckResult:
        """Detect circular INHERITS_FROM relationships in the role hierarchy."""
        query = """
            MATCH path = (r:Role)-[:INHERITS_FROM*1..20]->(r)
            RETURN DISTINCT r.name AS role_name
            LIMIT 10
        """
        try:
            records = await self._neo4j.execute_read(query)
            cycles = [r["role_name"] for r in records]
            return HealthCheckResult(
                check_name="circular_role_inheritance",
                passed=len(cycles) == 0,
                details=f"{len(cycles)} circular inheritance paths found" if cycles else "No circular inheritance",
                items=cycles,
            )
        except Exception as exc:
            return HealthCheckResult(
                check_name="circular_role_inheritance", passed=False, details=f"Check failed: {exc}"
            )

    async def check_missing_domain_assignment(self) -> HealthCheckResult:
        """Find active tables with no BELONGS_TO_DOMAIN relationship."""
        query = """
            MATCH (t:Table)
            WHERE t.is_active = true
              AND NOT (t)-[:BELONGS_TO_DOMAIN]->()
            RETURN t.fqn AS fqn
        """
        try:
            records = await self._neo4j.execute_read(query)
            missing = [r["fqn"] for r in records]
            return HealthCheckResult(
                check_name="missing_domain_assignment",
                passed=len(missing) == 0,
                details=f"{len(missing)} tables without domain" if missing else "All tables have domains",
                items=missing[:20],
            )
        except Exception as exc:
            return HealthCheckResult(
                check_name="missing_domain_assignment", passed=False, details=f"Check failed: {exc}"
            )

    async def check_pii_consistency(self) -> HealthCheckResult:
        """PII columns must have sensitivity_level >= 3 (CONFIDENTIAL)."""
        query = """
            MATCH (c:Column)
            WHERE c.is_pii = true AND c.sensitivity_level < 3
            RETURN c.fqn AS fqn
        """
        try:
            records = await self._neo4j.execute_read(query)
            violations = [r["fqn"] for r in records]
            return HealthCheckResult(
                check_name="pii_sensitivity_consistency",
                passed=len(violations) == 0,
                details=(
                    f"{len(violations)} PII columns below CONFIDENTIAL sensitivity"
                    if violations
                    else "All PII columns meet minimum sensitivity"
                ),
                items=violations[:20],
            )
        except Exception as exc:
            return HealthCheckResult(
                check_name="pii_sensitivity_consistency", passed=False, details=f"Check failed: {exc}"
            )

    async def check_masking_consistency(self) -> HealthCheckResult:
        """PII columns should have a masking strategy defined."""
        query = """
            MATCH (c:Column)
            WHERE c.is_pii = true
              AND (c.masking_strategy IS NULL OR c.masking_strategy = '')
              AND c.is_active = true
            RETURN c.fqn AS fqn
        """
        try:
            records = await self._neo4j.execute_read(query)
            missing = [r["fqn"] for r in records]
            return HealthCheckResult(
                check_name="masking_consistency",
                passed=len(missing) == 0,
                details=(
                    f"{len(missing)} PII columns without masking strategy"
                    if missing
                    else "All PII columns have masking strategies"
                ),
                items=missing[:20],
            )
        except Exception as exc:
            return HealthCheckResult(
                check_name="masking_consistency", passed=False, details=f"Check failed: {exc}"
            )

    async def check_substance_abuse_deny(self) -> HealthCheckResult:
        """substance_abuse_records tables must have hard_deny = true
        and must NOT have any ALLOW policies.
        """
        query = """
            MATCH (t:Table)
            WHERE t.name CONTAINS 'substance_abuse'
            OPTIONAL MATCH (p:Policy)-[:GOVERNS_TABLE]->(t)
            WHERE p.policy_type = 'ALLOW' AND p.is_active = true
            RETURN t.fqn AS fqn, t.hard_deny AS hd,
                   collect(DISTINCT p.policy_id) AS allow_policies
        """
        try:
            records = await self._neo4j.execute_read(query)
            violations: list[str] = []
            for r in records:
                if not r.get("hd"):
                    violations.append(f"{r['fqn']}: hard_deny not set")
                if r.get("allow_policies"):
                    violations.append(
                        f"{r['fqn']}: has ALLOW policies {r['allow_policies']}"
                    )
            return HealthCheckResult(
                check_name="substance_abuse_deny_enforcement",
                passed=len(violations) == 0,
                details=(
                    f"{len(violations)} violations found"
                    if violations
                    else "All substance abuse tables properly protected"
                ),
                items=violations,
            )
        except Exception as exc:
            return HealthCheckResult(
                check_name="substance_abuse_deny_enforcement",
                passed=False,
                details=f"Check failed: {exc}",
            )
