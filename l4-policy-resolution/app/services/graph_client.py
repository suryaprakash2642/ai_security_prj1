"""Neo4j graph client tailored for fetching policy and schema paths.

Implements Cypher queries needed by the Policy Collector to fetch
role hierarchies and applicable table/column policies.
"""

import structlog
from neo4j import AsyncGraphDatabase, AsyncDriver

from app.config import get_settings

logger = structlog.get_logger(__name__)


class GraphClient:
    """Manages asynchronous connections to Neo4j."""

    def __init__(self, uri: str, user: str, password: str):
        self._driver: AsyncDriver = AsyncGraphDatabase.driver(uri, auth=(user, password))

    async def close(self):
        await self._driver.close()

    async def get_effective_roles(self, initial_roles: list[str]) -> set[str]:
        """Traverse role hierarchy and return all roles the user inherits exactly."""
        query = """
        UNWIND $roles AS role_name
        MATCH (start:Role {name: role_name})-[:INHERITS_FROM*0..]->(inherited:Role)
        RETURN collect(DISTINCT inherited.name) AS effective_roles
        """
        async with self._driver.session() as session:
            result = await session.run(query, roles=initial_roles)
            record = await result.single()
            if not record:
                return set(initial_roles)
            return set(record["effective_roles"])

    async def get_table_policies(self, table_ids: list[str], roles: list[str]) -> list[dict]:
        """Fetch all policies governing the provided tables, filtering by effective roles.
        
        This fetches policies directly attached to the Table, via its Domain,
        or via global Regulatory/System policies.
        """
        query = """
        UNWIND $table_ids AS tid
        MATCH (t:Table {table_id: tid})
        OPTIONAL MATCH (t)-[:BELONGS_TO_DOMAIN]->(d:Domain)
        
        // 1. Table-level policies
        OPTIONAL MATCH (p1:Policy)-[:GOVERNS_TABLE]->(t)
        WHERE (p1)-[:APPLIES_TO_ROLE]->(:Role) // Ensure valid policy attachment
        
        // 2. Domain-level policies
        OPTIONAL MATCH (p2:Policy)-[:GOVERNS_DOMAIN]->(d)
        WHERE (p2)-[:APPLIES_TO_ROLE]->(:Role)
        
        // 3. Regulated/Universal policies (FED-001)
        // e.g. policies covering HIPAA rules if the table is tagged
        OPTIONAL MATCH (t)-[:REGULATED_BY]->(r:Regulation)<-[:ENFORCES_REGULATION]-(p3:Policy)
        
        WITH tid, t, collect(p1) + collect(p2) + collect(p3) AS all_policies
        UNWIND all_policies AS p
        WITH DISTINCT tid, p
        
        // Filter: policy must apply to the user's role OR be universal
        MATCH (p)-[:APPLIES_TO_ROLE]->(role:Role)
        WHERE role.name IN $roles OR role.name = 'ALL_ROLES'
        
        // Fetch nested conditions
        OPTIONAL MATCH (p)-[:HAS_CONDITION]->(c:Condition)
        WITH tid, p, collect(c {.*, condition_id: c.condition_id}) AS conditions
        
        RETURN tid, p {.*, policy_id: p.policy_id, conditions: conditions} AS policy
        """
        policies = []
        async with self._driver.session() as session:
            res = await session.run(query, table_ids=table_ids, roles=roles)
            async for record in res:
                policies.append({
                    "table_id": record["tid"],
                    "policy": record["policy"]
                })
        return policies

    async def get_column_policies(self, table_ids: list[str], roles: list[str]) -> list[dict]:
        """Fetch all policies governing columns within the matching tables."""
        query = """
        UNWIND $table_ids AS tid
        MATCH (t:Table {table_id: tid})-[:HAS_COLUMN]->(c:Column)

        // Column-level policies
        OPTIONAL MATCH (p:Policy)-[:GOVERNS_COLUMN]->(c)
        WITH tid, c, p
        WHERE p IS NOT NULL

        // Role check
        MATCH (p)-[:APPLIES_TO_ROLE]->(role:Role)
        WHERE role.name IN $roles OR role.name = 'ALL_ROLES'

        OPTIONAL MATCH (p)-[:HAS_CONDITION]->(cond:Condition)
        WITH tid, c, p, collect(cond {.*, condition_id: cond.condition_id}) AS conditions

        RETURN tid, c.name AS col_name, c.id AS col_id, p {.*, policy_id: p.policy_id, conditions: conditions} AS policy
        """
        policies = []
        async with self._driver.session() as session:
            res = await session.run(query, table_ids=table_ids, roles=roles)
            async for record in res:
                policies.append({
                    "table_id": record["tid"],
                    "column_name": record["col_name"],
                    "column_id": record["col_id"],
                    "policy": record["policy"]
                })
        return policies

    async def get_table_properties(self, table_ids: list[str]) -> dict[str, dict]:
        """Fetch table-level properties (sensitivity_level, domain, facility scope) for clearance gating."""
        query = """
        UNWIND $table_ids AS tid
        MATCH (t:Table {table_id: tid})
        OPTIONAL MATCH (t)-[:BELONGS_TO_DOMAIN]->(d:Domain)
        RETURN tid, t.sensitivity_level AS sensitivity_level, d.name AS domain
        """
        result: dict[str, dict] = {}
        async with self._driver.session() as session:
            res = await session.run(query, table_ids=table_ids)
            async for record in res:
                result[record["tid"]] = {
                    "sensitivity_level": record["sensitivity_level"] or 1,
                    "domain": record["domain"] or "",
                }
        return result

    async def get_all_table_columns(self, table_ids: list[str]) -> list[dict]:
        """Fetch all column definitions for the given tables regardless of attached policies.

        Used by the policy collector to ensure every column is registered in
        TableMetadata even when no Policy node is attached to it.  Columns
        without policies are then resolved as VISIBLE by the ConflictResolver's
        default-allow fallback.
        """
        query = """
        UNWIND $table_ids AS tid
        MATCH (t:Table {table_id: tid})-[:HAS_COLUMN]->(c:Column)
        RETURN tid, c.name AS col_name, c.id AS col_id
        """
        columns = []
        async with self._driver.session() as session:
            res = await session.run(query, table_ids=table_ids)
            async for record in res:
                columns.append({
                    "table_id": record["tid"],
                    "column_name": record["col_name"],
                    "column_id": record["col_id"],
                })
        return columns


# Global singleton instance (initialized on app startup)
graph_client: GraphClient | None = None

def get_graph_client() -> GraphClient:
    global graph_client
    if not graph_client:
        settings = get_settings()
        graph_client = GraphClient(
            settings.neo4j_uri,
            settings.neo4j_user,
            settings.neo4j_password
        )
    return graph_client
