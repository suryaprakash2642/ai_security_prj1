"""Write-only graph repository — used exclusively by admin/batch services.

Every write operation:
1. Executes the parameterized Cypher mutation
2. Returns change details for audit logging
"""

from __future__ import annotations

import json
from typing import Any

import structlog

from app.models.graph import (
    ColumnNode,
    DatabaseNode,
    DomainNode,
    PolicyNode,
    RegulationNode,
    RoleNode,
    SchemaNode,
    TableNode,
)
from app.repositories.neo4j_manager import Neo4jManager

logger = structlog.get_logger(__name__)


class GraphWriteRepository:
    """Parameterized write operations for the Knowledge Graph."""

    def __init__(self, neo4j: Neo4jManager) -> None:
        self._neo4j = neo4j

    # ── Schema structure writes ──────────────────────────────

    async def upsert_database(self, db: DatabaseNode) -> dict[str, Any]:
        query = """
        MERGE (d:Database {name: $name})
        ON CREATE SET d.engine = $engine, d.host = $host, d.port = $port,
                      d.is_active = true, d.created_at = datetime(), d.version = 1
        ON MATCH SET d.engine = $engine, d.host = $host, d.port = $port,
                     d.is_active = true, d.version = d.version + 1
        RETURN d.version AS version, d.name AS name
        """
        params = {"name": db.name, "engine": db.engine.value, "host": db.host, "port": db.port}
        records = await self._neo4j.execute_write(query, params)
        return records[0] if records else {}

    async def upsert_schema(self, schema: SchemaNode, database_name: str) -> dict[str, Any]:
        query = """
        MATCH (db:Database {name: $db_name})
        MERGE (s:Schema {fqn: $fqn})
        ON CREATE SET s.name = $name, s.is_active = true,
                      s.created_at = datetime(), s.version = 1
        ON MATCH SET s.name = $name, s.is_active = true,
                     s.version = s.version + 1
        MERGE (db)-[:HAS_SCHEMA]->(s)
        RETURN s.version AS version, s.fqn AS fqn
        """
        params = {"db_name": database_name, "fqn": schema.fqn, "name": schema.name}
        records = await self._neo4j.execute_write(query, params)
        return records[0] if records else {}

    async def upsert_table(
        self, table: TableNode, schema_fqn: str, domain_name: str
    ) -> dict[str, Any]:
        query = """
        MATCH (s:Schema {fqn: $schema_fqn})
        MERGE (t:Table {fqn: $fqn})
        ON CREATE SET t.name = $name, t.description = $description,
                      t.sensitivity_level = $sensitivity_level,
                      t.is_active = true, t.hard_deny = $hard_deny,
                      t.domain = $domain, t.row_count_approx = $row_count,
                      t.created_at = datetime(), t.version = 1
        ON MATCH SET t.name = $name, t.description = $description,
                     t.sensitivity_level = $sensitivity_level,
                     t.is_active = true, t.hard_deny = $hard_deny,
                     t.domain = $domain, t.row_count_approx = $row_count,
                     t.version = t.version + 1
        MERGE (s)-[:HAS_TABLE]->(t)
        WITH t
        MERGE (d:Domain {name: $domain})
        ON CREATE SET d.description = '', d.created_at = datetime(), d.version = 1
        MERGE (t)-[:BELONGS_TO_DOMAIN]->(d)
        RETURN t.version AS version, t.fqn AS fqn
        """
        params = {
            "schema_fqn": schema_fqn,
            "fqn": table.fqn,
            "name": table.name,
            "description": table.description,
            "sensitivity_level": table.sensitivity_level,
            "hard_deny": table.hard_deny,
            "domain": domain_name,
            "row_count": table.row_count_approx,
        }
        records = await self._neo4j.execute_write(query, params)
        return records[0] if records else {}

    async def upsert_column(self, column: ColumnNode, table_fqn: str, ordinal_position: int = 0) -> dict[str, Any]:
        query = """
        MATCH (t:Table {fqn: $table_fqn})
        MERGE (c:Column {fqn: $fqn})
        ON CREATE SET c.name = $name, c.data_type = $data_type,
                      c.is_pk = $is_pk, c.is_nullable = $is_nullable,
                      c.is_pii = $is_pii, c.pii_type = $pii_type,
                      c.sensitivity_level = $sensitivity_level,
                      c.masking_strategy = $masking_strategy,
                      c.description = $description,
                      c.is_active = true, c.version = 1
        ON MATCH SET c.name = $name, c.data_type = $data_type,
                     c.is_pk = $is_pk, c.is_nullable = $is_nullable,
                     c.is_pii = $is_pii, c.pii_type = $pii_type,
                     c.sensitivity_level = $sensitivity_level,
                     c.masking_strategy = $masking_strategy,
                     c.description = $description,
                     c.is_active = true, c.version = c.version + 1
        MERGE (t)-[r:HAS_COLUMN]->(c)
        SET r.ordinal_position = $ordinal_position
        RETURN c.version AS version, c.fqn AS fqn
        """
        params = {
            "table_fqn": table_fqn,
            "fqn": column.fqn,
            "name": column.name,
            "data_type": column.data_type,
            "is_pk": column.is_pk,
            "is_nullable": column.is_nullable,
            "is_pii": column.is_pii,
            "pii_type": column.pii_type.value if column.pii_type else None,
            "sensitivity_level": column.sensitivity_level,
            "masking_strategy": column.masking_strategy.value if column.masking_strategy else None,
            "description": column.description,
            "ordinal_position": ordinal_position,
        }
        records = await self._neo4j.execute_write(query, params)
        return records[0] if records else {}

    async def add_foreign_key(
        self, source_col_fqn: str, target_col_fqn: str, constraint_name: str = ""
    ) -> None:
        query = """
        MATCH (src:Column {fqn: $source_fqn})
        MATCH (tgt:Column {fqn: $target_fqn})
        MERGE (src)-[:FOREIGN_KEY_TO {constraint_name: $constraint}]->(tgt)
        """
        await self._neo4j.execute_write(
            query,
            {"source_fqn": source_col_fqn, "target_fqn": target_col_fqn, "constraint": constraint_name},
        )

    async def deactivate_table(self, table_fqn: str) -> None:
        """Soft-delete: mark table and its columns as inactive. Never hard-delete."""
        query = """
        MATCH (t:Table {fqn: $fqn})
        SET t.is_active = false, t.deactivated_at = datetime(), t.version = t.version + 1
        WITH t
        MATCH (t)-[:HAS_COLUMN]->(c:Column)
        SET c.is_active = false, c.version = c.version + 1
        """
        await self._neo4j.execute_write(query, {"fqn": table_fqn})

    async def deactivate_column(self, column_fqn: str) -> None:
        query = """
        MATCH (c:Column {fqn: $fqn})
        SET c.is_active = false, c.version = c.version + 1
        """
        await self._neo4j.execute_write(query, {"fqn": column_fqn})

    # ── Classification writes ────────────────────────────────

    async def update_column_classification(
        self,
        column_fqn: str,
        sensitivity_level: int,
        is_pii: bool,
        pii_type: str | None,
        masking_strategy: str | None,
    ) -> dict[str, Any]:
        """Update column classification, returning both old and new values."""
        # Capture pre-mutation state for audit
        pre_query = """
        MATCH (c:Column {fqn: $fqn})
        RETURN c.sensitivity_level AS old_sensitivity,
               c.is_pii AS old_is_pii,
               c.pii_type AS old_pii_type,
               c.masking_strategy AS old_masking
        """
        old_records = await self._neo4j.execute_read(pre_query, {"fqn": column_fqn})
        old_values = old_records[0] if old_records else {}

        query = """
        MATCH (c:Column {fqn: $fqn})
        SET c.sensitivity_level = $sensitivity,
            c.is_pii = $is_pii,
            c.pii_type = $pii_type,
            c.masking_strategy = $masking,
            c.version = c.version + 1
        RETURN c.version AS version, c.fqn AS fqn
        """
        records = await self._neo4j.execute_write(
            query,
            {
                "fqn": column_fqn,
                "sensitivity": sensitivity_level,
                "is_pii": is_pii,
                "pii_type": pii_type,
                "masking": masking_strategy,
            },
        )
        result = records[0] if records else {}
        result["old_values"] = dict(old_values) if old_values else {}
        return result

    async def add_regulation_to_column(self, column_fqn: str, regulation_code: str) -> None:
        query = """
        MATCH (c:Column {fqn: $col_fqn})
        MATCH (reg:Regulation {code: $reg_code})
        MERGE (c)-[:COLUMN_REGULATED_BY]->(reg)
        """
        await self._neo4j.execute_write(
            query, {"col_fqn": column_fqn, "reg_code": regulation_code}
        )

    async def add_regulation_to_table(self, table_fqn: str, regulation_code: str) -> None:
        query = """
        MATCH (t:Table {fqn: $table_fqn})
        MATCH (reg:Regulation {code: $reg_code})
        MERGE (t)-[:REGULATED_BY]->(reg)
        """
        await self._neo4j.execute_write(
            query, {"table_fqn": table_fqn, "reg_code": regulation_code}
        )

    # ── Policy writes ────────────────────────────────────────

    async def upsert_policy(self, policy: PolicyNode) -> dict[str, Any]:
        query = """
        MERGE (p:Policy {policy_id: $policy_id})
        ON CREATE SET p.policy_type = $policy_type,
                      p.nl_description = $nl_description,
                      p.structured_rule = $structured_rule,
                      p.priority = $priority,
                      p.is_active = $is_active,
                      p.is_hard_deny = $is_hard_deny,
                      p.created_at = datetime(),
                      p.version = 1
        ON MATCH SET p.policy_type = $policy_type,
                     p.nl_description = $nl_description,
                     p.structured_rule = $structured_rule,
                     p.priority = $priority,
                     p.is_active = $is_active,
                     p.is_hard_deny = $is_hard_deny,
                     p.version = p.version + 1
        RETURN p.version AS version, p.policy_id AS policy_id
        """
        params = {
            "policy_id": policy.policy_id,
            "policy_type": policy.policy_type.value,
            "nl_description": policy.nl_description,
            "structured_rule": policy.structured_rule,
            "priority": policy.priority,
            "is_active": policy.is_active,
            "is_hard_deny": policy.is_hard_deny,
        }
        records = await self._neo4j.execute_write(query, params)
        return records[0] if records else {}

    async def bind_policy_to_role(self, policy_id: str, role_name: str) -> None:
        query = """
        MATCH (p:Policy {policy_id: $policy_id})
        MATCH (r:Role {name: $role_name})
        MERGE (p)-[:APPLIES_TO_ROLE]->(r)
        """
        await self._neo4j.execute_write(
            query, {"policy_id": policy_id, "role_name": role_name}
        )

    async def bind_policy_to_table(self, policy_id: str, table_fqn: str) -> None:
        query = """
        MATCH (p:Policy {policy_id: $policy_id})
        MATCH (t:Table {fqn: $table_fqn})
        MERGE (p)-[:GOVERNS_TABLE]->(t)
        """
        await self._neo4j.execute_write(
            query, {"policy_id": policy_id, "table_fqn": table_fqn}
        )

    async def bind_policy_to_domain(self, policy_id: str, domain_name: str) -> None:
        query = """
        MATCH (p:Policy {policy_id: $policy_id})
        MATCH (d:Domain {name: $domain_name})
        MERGE (p)-[:GOVERNS_DOMAIN]->(d)
        """
        await self._neo4j.execute_write(
            query, {"policy_id": policy_id, "domain_name": domain_name}
        )

    async def bind_policy_to_column(self, policy_id: str, column_fqn: str) -> None:
        """Bind a policy to a specific column via GOVERNS_COLUMN."""
        query = """
        MATCH (p:Policy {policy_id: $policy_id})
        MATCH (c:Column {fqn: $column_fqn})
        MERGE (p)-[:GOVERNS_COLUMN]->(c)
        """
        await self._neo4j.execute_write(
            query, {"policy_id": policy_id, "column_fqn": column_fqn}
        )

    async def deactivate_policy(self, policy_id: str) -> None:
        query = """
        MATCH (p:Policy {policy_id: $policy_id})
        SET p.is_active = false, p.version = p.version + 1
        """
        await self._neo4j.execute_write(query, {"policy_id": policy_id})

    # ── Role writes ──────────────────────────────────────────

    async def upsert_role(self, role: RoleNode) -> dict[str, Any]:
        query = """
        MERGE (r:Role {name: $name})
        ON CREATE SET r.description = $description, r.is_active = true, r.version = 1
        ON MATCH SET r.description = $description, r.is_active = true,
                     r.version = r.version + 1
        RETURN r.version AS version, r.name AS name
        """
        records = await self._neo4j.execute_write(
            query, {"name": role.name, "description": role.description}
        )
        return records[0] if records else {}

    async def add_role_inheritance(self, child_role: str, parent_role: str) -> None:
        """Add INHERITS_FROM relationship with cycle prevention.

        Before creating child→parent, checks whether parent already
        inherits from child (directly or transitively). If so, raises
        ValueError to prevent circular inheritance.
        """
        # Self-inheritance guard
        if child_role == parent_role:
            raise ValueError(f"Role '{child_role}' cannot inherit from itself")

        # Cycle detection: check if parent already reaches child via INHERITS_FROM
        cycle_check = """
        MATCH path = (parent:Role {name: $parent})-[:INHERITS_FROM*1..20]->(ancestor:Role {name: $child})
        RETURN count(path) AS cycle_count
        """
        records = await self._neo4j.execute_read(
            cycle_check, {"parent": parent_role, "child": child_role}
        )
        if records and records[0]["cycle_count"] > 0:
            raise ValueError(
                f"Adding {child_role}→{parent_role} inheritance would create a cycle: "
                f"'{parent_role}' already inherits from '{child_role}' (directly or transitively)"
            )

        query = """
        MATCH (child:Role {name: $child})
        MATCH (parent:Role {name: $parent})
        MERGE (child)-[:INHERITS_FROM]->(parent)
        """
        await self._neo4j.execute_write(
            query, {"child": child_role, "parent": parent_role}
        )

    async def add_role_domain_access(self, role_name: str, domain_name: str) -> None:
        query = """
        MATCH (r:Role {name: $role})
        MATCH (d:Domain {name: $domain})
        MERGE (r)-[:ACCESSES_DOMAIN]->(d)
        """
        await self._neo4j.execute_write(
            query, {"role": role_name, "domain": domain_name}
        )

    # ── Regulation writes ────────────────────────────────────

    async def upsert_regulation(self, reg: RegulationNode) -> dict[str, Any]:
        query = """
        MERGE (r:Regulation {code: $code})
        ON CREATE SET r.full_name = $full_name, r.description = $description,
                      r.jurisdiction = $jurisdiction, r.version = 1
        ON MATCH SET r.full_name = $full_name, r.description = $description,
                     r.jurisdiction = $jurisdiction, r.version = r.version + 1
        RETURN r.version AS version, r.code AS code
        """
        records = await self._neo4j.execute_write(
            query,
            {
                "code": reg.code,
                "full_name": reg.full_name,
                "description": reg.description,
                "jurisdiction": reg.jurisdiction,
            },
        )
        return records[0] if records else {}

    # ── Bulk helpers ─────────────────────────────────────────

    async def get_existing_table_fqns(self, database_name: str) -> set[str]:
        """Return all active table FQNs for a database."""
        query = """
        MATCH (db:Database {name: $db_name})-[:HAS_SCHEMA]->(s:Schema)-[:HAS_TABLE]->(t:Table)
        WHERE t.is_active = true
        RETURN t.fqn AS fqn
        """
        records = await self._neo4j.execute_read(query, {"db_name": database_name})
        return {r["fqn"] for r in records}

    async def get_existing_column_fqns(self, table_fqn: str) -> set[str]:
        """Return all active column FQNs for a table."""
        query = """
        MATCH (t:Table {fqn: $table_fqn})-[:HAS_COLUMN]->(c:Column)
        WHERE c.is_active = true
        RETURN c.fqn AS fqn
        """
        records = await self._neo4j.execute_read(query, {"table_fqn": table_fqn})
        return {r["fqn"] for r in records}

    # ── Init helpers ─────────────────────────────────────────

    async def run_cypher_file(self, cypher_text: str) -> None:
        """Execute a multi-statement Cypher script. Used for init only."""
        statements = [s.strip() for s in cypher_text.split(";") if s.strip() and not s.strip().startswith("//")]
        for stmt in statements:
            if stmt:
                try:
                    await self._neo4j.execute_write(stmt + ";")
                except Exception as exc:
                    logger.warning("cypher_statement_failed", statement=stmt[:100], error=str(exc))
