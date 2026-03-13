"""Read-only graph repository — parameterized Cypher queries only.

No downstream layer ever executes raw Cypher. Every query is pre-approved,
parameterized, and goes through this repository.
"""

from __future__ import annotations

import json
import re
from typing import Any

import structlog

from app.models.api import (
    ColumnResponse,
    ConditionResponse,
    ForeignKeyResponse,
    JoinRestrictionResponse,
    MaskingRuleResponse,
    PIIColumnResponse,
    PolicyResponse,
    PolicySimulateResult,
    RegulatedTableResponse,
    TableResponse,
)
from app.models.enums import PolicyType
from app.repositories.neo4j_manager import Neo4jManager

logger = structlog.get_logger(__name__)


def _sanitize_fulltext_query(query: str, max_length: int = 200) -> str:
    """Strip Lucene special characters from a fulltext query.

    Neo4j's db.index.fulltext.queryNodes uses Lucene query syntax, so square
    brackets, colons, and other reserved chars cause ParseException when they
    appear in plain user text or injected metadata tags like [role:X dept:Y].
    """
    # Remove injected metadata tags: [department:Cardiology role:ATTENDING_PHYSICIAN]
    cleaned = re.sub(r'\[.*?\]', ' ', query)
    # Remove remaining Lucene reserved characters
    cleaned = re.sub(r'[+\-&|!(){}^"~*?:\\/]', ' ', cleaned)
    # Collapse whitespace and cap length
    cleaned = ' '.join(cleaned.split())[:max_length]
    return cleaned or '*'


class GraphReadRepository:
    """Pre-approved read queries against the Knowledge Graph."""

    def __init__(self, neo4j: Neo4jManager) -> None:
        self._neo4j = neo4j

    # ── Database discovery ─────────────────────────────────────

    async def get_all_databases(self) -> list[dict[str, Any]]:
        """Return all active databases with engine type and metadata."""
        query = """
        MATCH (db:Database)
        WHERE db.is_active = true
        OPTIONAL MATCH (db)-[:HAS_SCHEMA]->(s:Schema)-[:HAS_TABLE]->(t:Table)
        WHERE t.is_active = true
        OPTIONAL MATCH (t)-[:BELONGS_TO_DOMAIN]->(d:Domain)
        WITH db,
             count(DISTINCT t) AS table_count,
             collect(DISTINCT d.name) AS domains
        RETURN db.name AS name,
               db.engine AS engine,
               db.description AS description,
               db.host AS host,
               db.port AS port,
               table_count,
               domains
        ORDER BY db.name
        """
        records = await self._neo4j.execute_read(query, {})
        return [
            {
                "name": r["name"],
                "engine": r["engine"] or "postgresql",
                "description": r.get("description", ""),
                "host": r.get("host", ""),
                "port": r.get("port", 0),
                "table_count": r.get("table_count", 0),
                "domains": r.get("domains", []),
            }
            for r in records
        ]

    # ── Schema queries ───────────────────────────────────────

    async def get_tables_by_domain(
        self, domain: str, limit: int = 100, offset: int = 0
    ) -> list[TableResponse]:
        query = """
        MATCH (t:Table)-[:BELONGS_TO_DOMAIN]->(d:Domain {name: $domain})
        WHERE t.is_active = true
        OPTIONAL MATCH (t)-[:REGULATED_BY]->(reg:Regulation)
        WITH t, collect(DISTINCT reg.code) AS regulations
        OPTIONAL MATCH (s:Schema)-[:HAS_TABLE]->(t)
        OPTIONAL MATCH (db:Database)-[:HAS_SCHEMA]->(s)
        RETURN t, regulations, s.name AS schema_name, db.name AS database_name
        ORDER BY t.name
        SKIP $offset LIMIT $limit
        """
        records = await self._neo4j.execute_read(
            query, {"domain": domain, "limit": limit, "offset": offset}
        )
        return [self._map_table(r) for r in records]

    async def get_table_columns(self, table_fqn: str) -> list[ColumnResponse]:
        query = """
        MATCH (t:Table {fqn: $table_fqn})-[:HAS_COLUMN]->(c:Column)
        WHERE c.is_active = true
        OPTIONAL MATCH (c)-[:COLUMN_REGULATED_BY]->(reg:Regulation)
        RETURN c, collect(DISTINCT reg.code) AS regulations
        ORDER BY c.is_pk DESC, c.name
        """
        records = await self._neo4j.execute_read(query, {"table_fqn": table_fqn})
        return [self._map_column(r) for r in records]

    async def get_tables_by_sensitivity(
        self, min_level: int, limit: int = 100, offset: int = 0
    ) -> list[TableResponse]:
        query = """
        MATCH (t:Table)
        WHERE t.is_active = true AND t.sensitivity_level >= $min_level
        OPTIONAL MATCH (t)-[:REGULATED_BY]->(reg:Regulation)
        WITH t, collect(DISTINCT reg.code) AS regulations
        OPTIONAL MATCH (s:Schema)-[:HAS_TABLE]->(t)
        OPTIONAL MATCH (db:Database)-[:HAS_SCHEMA]->(s)
        RETURN t, regulations, s.name AS schema_name, db.name AS database_name
        ORDER BY t.sensitivity_level DESC, t.name
        SKIP $offset LIMIT $limit
        """
        records = await self._neo4j.execute_read(
            query, {"min_level": min_level, "limit": limit, "offset": offset}
        )
        return [self._map_table(r) for r in records]

    async def get_foreign_keys(self, table_fqn: str) -> list[ForeignKeyResponse]:
        query = """
        MATCH (t:Table {fqn: $table_fqn})-[:HAS_COLUMN]->(src:Column)-[:FOREIGN_KEY_TO]->(tgt:Column)
        MATCH (t2:Table)-[:HAS_COLUMN]->(tgt)
        RETURN src.fqn AS source_column_fqn, src.name AS source_column_name,
               tgt.fqn AS target_column_fqn, tgt.name AS target_column_name,
               t2.fqn AS target_table_fqn
        """
        records = await self._neo4j.execute_read(query, {"table_fqn": table_fqn})
        return [
            ForeignKeyResponse(
                source_column_fqn=r["source_column_fqn"],
                source_column_name=r["source_column_name"],
                target_column_fqn=r["target_column_fqn"],
                target_column_name=r["target_column_name"],
                target_table_fqn=r["target_table_fqn"],
            )
            for r in records
        ]

    async def search_tables(self, query_text: str, limit: int = 20) -> list[TableResponse]:
        """Full-text search over table names and descriptions."""
        query_text = _sanitize_fulltext_query(query_text)
        query = """
        CALL db.index.fulltext.queryNodes('table_search', $query_text)
        YIELD node, score
        WHERE node.is_active = true
        WITH node AS t, score
        ORDER BY score DESC
        LIMIT $limit
        OPTIONAL MATCH (t)-[:REGULATED_BY]->(reg:Regulation)
        WITH t, collect(DISTINCT reg.code) AS regulations
        OPTIONAL MATCH (s:Schema)-[:HAS_TABLE]->(t)
        OPTIONAL MATCH (db:Database)-[:HAS_SCHEMA]->(s)
        RETURN t, regulations, s.name AS schema_name, db.name AS database_name
        """
        records = await self._neo4j.execute_read(
            query, {"query_text": query_text, "limit": limit}
        )
        return [self._map_table(r) for r in records]

    async def get_all_active_tables(self) -> list[TableResponse]:
        query = """
        MATCH (t:Table)
        WHERE t.is_active = true
        OPTIONAL MATCH (t)-[:REGULATED_BY]->(reg:Regulation)
        WITH t, collect(DISTINCT reg.code) AS regulations
        OPTIONAL MATCH (s:Schema)-[:HAS_TABLE]->(t)
        OPTIONAL MATCH (db:Database)-[:HAS_SCHEMA]->(s)
        RETURN t, regulations, s.name AS schema_name, db.name AS database_name
        ORDER BY t.fqn
        """
        records = await self._neo4j.execute_read(query)
        return [self._map_table(r) for r in records]

    # ── Policy queries ───────────────────────────────────────

    async def get_policies_for_roles(
        self, roles: list[str], include_inherited: bool = True
    ) -> list[PolicyResponse]:
        """Get all active policies applicable to given roles, including inherited roles."""
        if include_inherited:
            query = """
            UNWIND $roles AS role_name
            MATCH (r:Role {name: role_name})
            OPTIONAL MATCH path = (r)-[:INHERITS_FROM*0..10]->(ancestor:Role)
            WITH collect(DISTINCT ancestor.name) + collect(DISTINCT r.name) AS all_roles
            UNWIND all_roles AS rn
            MATCH (role:Role {name: rn})<-[:APPLIES_TO_ROLE]-(p:Policy)
            WHERE p.is_active = true
            WITH DISTINCT p
            OPTIONAL MATCH (p)-[:GOVERNS_TABLE]->(t:Table)
            OPTIONAL MATCH (p)-[:GOVERNS_COLUMN]->(c:Column)
            OPTIONAL MATCH (p)-[:GOVERNS_DOMAIN]->(d:Domain)
            OPTIONAL MATCH (p)-[:APPLIES_TO_ROLE]->(br:Role)
            OPTIONAL MATCH (p)-[:HAS_CONDITION]->(cond:Condition)
            RETURN p,
                   collect(DISTINCT t.fqn) AS target_tables,
                   collect(DISTINCT c.fqn) AS target_columns,
                   collect(DISTINCT d.name) AS target_domains,
                   collect(DISTINCT br.name) AS bound_roles,
                   collect(DISTINCT {
                       condition_id: cond.condition_id,
                       condition_type: cond.condition_type,
                       parameters: cond.parameters,
                       description: cond.description
                   }) AS conditions
            ORDER BY p.priority DESC
            """
        else:
            query = """
            UNWIND $roles AS role_name
            MATCH (r:Role {name: role_name})<-[:APPLIES_TO_ROLE]-(p:Policy)
            WHERE p.is_active = true
            WITH DISTINCT p
            OPTIONAL MATCH (p)-[:GOVERNS_TABLE]->(t:Table)
            OPTIONAL MATCH (p)-[:GOVERNS_COLUMN]->(c:Column)
            OPTIONAL MATCH (p)-[:GOVERNS_DOMAIN]->(d:Domain)
            OPTIONAL MATCH (p)-[:APPLIES_TO_ROLE]->(br:Role)
            OPTIONAL MATCH (p)-[:HAS_CONDITION]->(cond:Condition)
            RETURN p,
                   collect(DISTINCT t.fqn) AS target_tables,
                   collect(DISTINCT c.fqn) AS target_columns,
                   collect(DISTINCT d.name) AS target_domains,
                   collect(DISTINCT br.name) AS bound_roles,
                   collect(DISTINCT {
                       condition_id: cond.condition_id,
                       condition_type: cond.condition_type,
                       parameters: cond.parameters,
                       description: cond.description
                   }) AS conditions
            ORDER BY p.priority DESC
            """
        records = await self._neo4j.execute_read(query, {"roles": roles})
        return [self._map_policy(r) for r in records]

    async def get_policies_for_table(self, table_fqn: str) -> list[PolicyResponse]:
        query = """
        MATCH (t:Table {fqn: $table_fqn})
        OPTIONAL MATCH (p:Policy)-[:GOVERNS_TABLE]->(t)
        WHERE p.is_active = true
        WITH p WHERE p IS NOT NULL
        // Also get domain-level policies
        UNION
        MATCH (t:Table {fqn: $table_fqn})-[:BELONGS_TO_DOMAIN]->(d:Domain)
        MATCH (p:Policy)-[:GOVERNS_DOMAIN]->(d)
        WHERE p.is_active = true
        WITH p
        // Collect bindings
        OPTIONAL MATCH (p)-[:GOVERNS_TABLE]->(gt:Table)
        OPTIONAL MATCH (p)-[:GOVERNS_COLUMN]->(gc:Column)
        OPTIONAL MATCH (p)-[:GOVERNS_DOMAIN]->(gd:Domain)
        OPTIONAL MATCH (p)-[:APPLIES_TO_ROLE]->(br:Role)
        OPTIONAL MATCH (p)-[:HAS_CONDITION]->(cond:Condition)
        RETURN DISTINCT p,
               collect(DISTINCT gt.fqn) AS target_tables,
               collect(DISTINCT gc.fqn) AS target_columns,
               collect(DISTINCT gd.name) AS target_domains,
               collect(DISTINCT br.name) AS bound_roles,
               collect(DISTINCT {
                   condition_id: cond.condition_id,
                   condition_type: cond.condition_type,
                   parameters: cond.parameters,
                   description: cond.description
               }) AS conditions
        ORDER BY p.priority DESC
        """
        records = await self._neo4j.execute_read(query, {"table_fqn": table_fqn})
        return [self._map_policy(r) for r in records]

    async def get_join_restrictions(self, roles: list[str]) -> list[JoinRestrictionResponse]:
        query = """
        UNWIND $roles AS role_name
        MATCH (r:Role {name: role_name})
        OPTIONAL MATCH path = (r)-[:INHERITS_FROM*0..10]->(ancestor:Role)
        WITH collect(DISTINCT ancestor.name) + collect(DISTINCT r.name) AS all_roles
        UNWIND all_roles AS rn
        MATCH (role:Role {name: rn})<-[:APPLIES_TO_ROLE]-(p:Policy)
        WHERE p.is_active = true
        MATCH (p)-[:HAS_CONDITION]->(cond:Condition {condition_type: 'JOIN_RESTRICTION'})
        OPTIONAL MATCH (p)-[:APPLIES_TO_ROLE]->(br:Role)
        RETURN DISTINCT p.policy_id AS policy_id,
               cond.parameters AS parameters,
               collect(DISTINCT br.name) AS bound_roles
        """
        records = await self._neo4j.execute_read(query, {"roles": roles})
        results = []
        for r in records:
            params = json.loads(r.get("parameters", "{}"))
            results.append(
                JoinRestrictionResponse(
                    policy_id=r["policy_id"],
                    source_domain=params.get("source_domain", ""),
                    target_domain=params.get("target_domain", ""),
                    bound_roles=r.get("bound_roles", []),
                )
            )
        return results

    async def get_role_domain_access(
        self, roles: list[str], include_inherited: bool = True
    ) -> dict[str, list[str]]:
        """Return domain access map keyed by input role name."""
        if not roles:
            return {}

        if include_inherited:
            query = """
            UNWIND $roles AS role_name
            MATCH (r:Role {name: role_name})
            OPTIONAL MATCH (r)-[:INHERITS_FROM*0..10]->(ancestor:Role)
            WITH role_name, collect(DISTINCT ancestor.name) + collect(DISTINCT r.name) AS all_roles
            UNWIND all_roles AS rn
            MATCH (role:Role {name: rn})<-[:APPLIES_TO_ROLE]-(p:Policy)
            WHERE p.is_active = true
            OPTIONAL MATCH (p)-[:GOVERNS_DOMAIN]->(d:Domain)
            RETURN role_name, collect(DISTINCT d.name) AS domains
            """
        else:
            query = """
            UNWIND $roles AS role_name
            MATCH (r:Role {name: role_name})<-[:APPLIES_TO_ROLE]-(p:Policy)
            WHERE p.is_active = true
            OPTIONAL MATCH (p)-[:GOVERNS_DOMAIN]->(d:Domain)
            RETURN role_name, collect(DISTINCT d.name) AS domains
            """

        records = await self._neo4j.execute_read(query, {"roles": roles})
        role_map: dict[str, list[str]] = {r: [] for r in roles}
        for row in records:
            domains = [d for d in row.get("domains", []) if d]
            role_map[row["role_name"]] = sorted(set(domains))
        return role_map

    async def get_hard_deny_tables(self) -> list[str]:
        """Return FQNs of all tables with hard_deny = true."""
        query = """
        MATCH (t:Table)
        WHERE t.hard_deny = true AND t.is_active = true
        RETURN t.fqn AS fqn
        """
        records = await self._neo4j.execute_read(query)
        return [r["fqn"] for r in records]

    async def check_substance_abuse_deny(self, table_fqn: str) -> bool:
        """Return True if the table is a hard-deny substance abuse table."""
        query = """
        MATCH (t:Table {fqn: $table_fqn})
        WHERE t.hard_deny = true
        RETURN count(t) > 0 AS is_denied
        """
        records = await self._neo4j.execute_read(query, {"table_fqn": table_fqn})
        return records[0].get("is_denied", False) if records else False

    # ── Classification queries ───────────────────────────────

    async def get_pii_columns(
        self,
        domain: str | None = None,
        table_fqn: str | None = None,
        pii_type: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[PIIColumnResponse]:
        params: dict[str, Any] = {
            "domain": domain,
            "table_fqn": table_fqn,
            "pii_type": pii_type,
            "limit": limit,
            "offset": offset,
        }

        query = """
        MATCH (t:Table)-[:HAS_COLUMN]->(c:Column)
        WHERE c.is_pii = true AND c.is_active = true
          AND ($domain IS NULL OR t.domain = $domain)
          AND ($table_fqn IS NULL OR t.fqn = $table_fqn)
          AND ($pii_type IS NULL OR c.pii_type = $pii_type)
        OPTIONAL MATCH (c)-[:COLUMN_REGULATED_BY]->(reg:Regulation)
        RETURN c.fqn AS column_fqn, c.name AS column_name,
               t.fqn AS table_fqn, t.name AS table_name,
               c.pii_type AS pii_type, c.sensitivity_level AS sensitivity_level,
               c.masking_strategy AS masking_strategy,
               collect(DISTINCT reg.code) AS regulations
        ORDER BY c.sensitivity_level DESC
        SKIP $offset LIMIT $limit
        """
        records = await self._neo4j.execute_read(query, params)
        return [
            PIIColumnResponse(
                column_fqn=r["column_fqn"],
                column_name=r["column_name"],
                table_fqn=r["table_fqn"],
                table_name=r["table_name"],
                pii_type=r.get("pii_type", ""),
                sensitivity_level=r.get("sensitivity_level", 1),
                masking_strategy=r.get("masking_strategy"),
                regulations=[x for x in r.get("regulations", []) if x],
            )
            for r in records
        ]

    async def get_tables_regulated_by(self, regulation_code: str) -> list[RegulatedTableResponse]:
        query = """
        MATCH (t:Table)-[:REGULATED_BY]->(reg:Regulation {code: $code})
        WHERE t.is_active = true
        RETURN t.fqn AS table_fqn, t.name AS table_name,
               reg.code AS regulation_code, reg.full_name AS regulation_name,
               t.sensitivity_level AS sensitivity_level,
               COALESCE(t.hard_deny, false) AS hard_deny
        ORDER BY t.sensitivity_level DESC
        """
        records = await self._neo4j.execute_read(query, {"code": regulation_code})
        return [RegulatedTableResponse(**r) for r in records]

    async def get_masking_rules(self, table_fqn: str) -> list[MaskingRuleResponse]:
        query = """
        MATCH (t:Table {fqn: $table_fqn})-[:HAS_COLUMN]->(c:Column)
        WHERE c.is_active = true AND c.masking_strategy IS NOT NULL
        OPTIONAL MATCH (p:Policy)-[:GOVERNS_COLUMN]->(c)
        WHERE p.is_active = true AND p.policy_type = 'MASK'
        RETURN c.fqn AS column_fqn, c.name AS column_name,
               c.masking_strategy AS masking_strategy,
               c.pii_type AS pii_type,
               c.sensitivity_level AS sensitivity_level,
               collect(DISTINCT p.policy_id) AS policy_ids
        ORDER BY c.sensitivity_level DESC
        """
        records = await self._neo4j.execute_read(query, {"table_fqn": table_fqn})
        return [
            MaskingRuleResponse(
                column_fqn=r["column_fqn"],
                column_name=r["column_name"],
                masking_strategy=r["masking_strategy"],
                pii_type=r.get("pii_type"),
                sensitivity_level=r.get("sensitivity_level", 1),
                policy_ids=[pid for pid in r.get("policy_ids", []) if pid],
            )
            for r in records
        ]

    # ── Role hierarchy ───────────────────────────────────────

    async def get_inherited_roles(self, role_name: str) -> list[str]:
        """Traverse INHERITS_FROM to get full role ancestry."""
        query = """
        MATCH (r:Role {name: $role_name})
        OPTIONAL MATCH path = (r)-[:INHERITS_FROM*1..10]->(ancestor:Role)
        RETURN collect(DISTINCT ancestor.name) AS inherited_roles
        """
        records = await self._neo4j.execute_read(query, {"role_name": role_name})
        if records:
            return records[0].get("inherited_roles", [])
        return []

    async def get_role_domains(self, role_name: str) -> list[str]:
        """Get domains a role can access (including inherited)."""
        query = """
        MATCH (r:Role {name: $role_name})
        OPTIONAL MATCH path = (r)-[:INHERITS_FROM*0..10]->(ancestor:Role)
        WITH collect(DISTINCT ancestor) + [r] AS all_roles
        UNWIND all_roles AS role
        MATCH (role)-[:ACCESSES_DOMAIN]->(d:Domain)
        RETURN collect(DISTINCT d.name) AS domains
        """
        records = await self._neo4j.execute_read(query, {"role_name": role_name})
        if records:
            return records[0].get("domains", [])
        return []

    # ── Graph stats ──────────────────────────────────────────

    async def get_node_counts(self) -> dict[str, int]:
        query = """
        CALL {
            MATCH (n:Database) RETURN 'Database' AS label, count(n) AS cnt
            UNION ALL
            MATCH (n:Schema) RETURN 'Schema' AS label, count(n) AS cnt
            UNION ALL
            MATCH (n:Table) WHERE n.is_active = true RETURN 'Table' AS label, count(n) AS cnt
            UNION ALL
            MATCH (n:Column) WHERE n.is_active = true RETURN 'Column' AS label, count(n) AS cnt
            UNION ALL
            MATCH (n:Domain) RETURN 'Domain' AS label, count(n) AS cnt
            UNION ALL
            MATCH (n:Role) RETURN 'Role' AS label, count(n) AS cnt
            UNION ALL
            MATCH (n:Policy) WHERE n.is_active = true RETURN 'Policy' AS label, count(n) AS cnt
            UNION ALL
            MATCH (n:Regulation) RETURN 'Regulation' AS label, count(n) AS cnt
        }
        RETURN label, cnt
        """
        records = await self._neo4j.execute_read(query)
        return {r["label"]: r["cnt"] for r in records}

    # ── Private mapping helpers ──────────────────────────────

    @staticmethod
    def _map_table(record: dict[str, Any]) -> TableResponse:
        t = record["t"]
        return TableResponse(
            fqn=t.get("fqn", ""),
            name=t.get("name", ""),
            description=t.get("description", ""),
            sensitivity_level=t.get("sensitivity_level", 1),
            domain=t.get("domain", ""),
            is_active=t.get("is_active", True),
            hard_deny=t.get("hard_deny", False),
            schema_name=record.get("schema_name") or "",
            database_name=record.get("database_name") or "",
            row_count_approx=t.get("row_count_approx", 0),
            version=t.get("version", 1),
            regulations=[x for x in record.get("regulations", []) if x],
        )

    @staticmethod
    def _map_column(record: dict[str, Any]) -> ColumnResponse:
        c = record["c"]
        return ColumnResponse(
            fqn=c.get("fqn", ""),
            name=c.get("name", ""),
            data_type=c.get("data_type", ""),
            is_pk=c.get("is_pk", False),
            is_nullable=c.get("is_nullable", True),
            is_pii=c.get("is_pii", False),
            pii_type=c.get("pii_type"),
            sensitivity_level=c.get("sensitivity_level", 1),
            masking_strategy=c.get("masking_strategy"),
            description=c.get("description", ""),
            is_active=c.get("is_active", True),
            regulations=[x for x in record.get("regulations", []) if x],
        )

    @staticmethod
    def _map_policy(record: dict[str, Any]) -> PolicyResponse:
        p = record["p"]
        structured = p.get("structured_rule", "{}")
        try:
            structured_dict = json.loads(structured) if isinstance(structured, str) else structured
        except (json.JSONDecodeError, TypeError):
            structured_dict = {"raw": structured}

        conditions_raw = record.get("conditions", [])
        conditions = []
        for c in conditions_raw:
            if c and c.get("condition_id"):
                params_str = c.get("parameters", "{}")
                try:
                    params_dict = json.loads(params_str) if isinstance(params_str, str) else params_str
                except (json.JSONDecodeError, TypeError):
                    params_dict = {}
                conditions.append(
                    ConditionResponse(
                        condition_id=c["condition_id"],
                        condition_type=c.get("condition_type", "ROW_FILTER"),
                        parameters=params_dict,
                        description=c.get("description", ""),
                    )
                )

        return PolicyResponse(
            policy_id=p.get("policy_id", ""),
            policy_type=p.get("policy_type", "DENY"),
            nl_description=p.get("nl_description", ""),
            structured_rule=structured_dict,
            priority=p.get("priority", 0),
            is_hard_deny=p.get("is_hard_deny", False),
            is_active=p.get("is_active", True),
            target_tables=[x for x in record.get("target_tables", []) if x],
            target_columns=[x for x in record.get("target_columns", []) if x],
            target_domains=[x for x in record.get("target_domains", []) if x],
            bound_roles=[x for x in record.get("bound_roles", []) if x],
            conditions=conditions,
            version=p.get("version", 1),
        )
