// ============================================================
// L2 Knowledge Graph — Constraints & Indexes
// Run once during graph initialization
// ============================================================

// --- Uniqueness constraints (also create indexes) ---

CREATE CONSTRAINT db_name_unique IF NOT EXISTS
FOR (d:Database) REQUIRE d.name IS UNIQUE;

CREATE CONSTRAINT schema_fqn_unique IF NOT EXISTS
FOR (s:Schema) REQUIRE s.fqn IS UNIQUE;

CREATE CONSTRAINT table_fqn_unique IF NOT EXISTS
FOR (t:Table) REQUIRE t.fqn IS UNIQUE;

CREATE CONSTRAINT column_fqn_unique IF NOT EXISTS
FOR (c:Column) REQUIRE c.fqn IS UNIQUE;

CREATE CONSTRAINT domain_name_unique IF NOT EXISTS
FOR (d:Domain) REQUIRE d.name IS UNIQUE;

CREATE CONSTRAINT role_name_unique IF NOT EXISTS
FOR (r:Role) REQUIRE r.name IS UNIQUE;

CREATE CONSTRAINT policy_id_unique IF NOT EXISTS
FOR (p:Policy) REQUIRE p.policy_id IS UNIQUE;

CREATE CONSTRAINT condition_id_unique IF NOT EXISTS
FOR (c:Condition) REQUIRE c.condition_id IS UNIQUE;

CREATE CONSTRAINT regulation_code_unique IF NOT EXISTS
FOR (r:Regulation) REQUIRE r.code IS UNIQUE;

// --- Composite indexes for hot query paths ---

CREATE INDEX table_domain_idx IF NOT EXISTS
FOR (t:Table) ON (t.domain);

CREATE INDEX table_sensitivity_idx IF NOT EXISTS
FOR (t:Table) ON (t.sensitivity_level);

CREATE INDEX table_active_idx IF NOT EXISTS
FOR (t:Table) ON (t.is_active);

CREATE INDEX column_pii_idx IF NOT EXISTS
FOR (c:Column) ON (c.is_pii);

CREATE INDEX column_sensitivity_idx IF NOT EXISTS
FOR (c:Column) ON (c.sensitivity_level);

CREATE INDEX column_active_idx IF NOT EXISTS
FOR (c:Column) ON (c.is_active);

CREATE INDEX policy_type_idx IF NOT EXISTS
FOR (p:Policy) ON (p.policy_type);

CREATE INDEX policy_active_idx IF NOT EXISTS
FOR (p:Policy) ON (p.is_active);

CREATE INDEX role_active_idx IF NOT EXISTS
FOR (r:Role) ON (r.is_active);

// --- Full-text search indexes ---

CREATE FULLTEXT INDEX table_search IF NOT EXISTS
FOR (t:Table) ON EACH [t.name, t.description, t.fqn];

CREATE FULLTEXT INDEX column_search IF NOT EXISTS
FOR (c:Column) ON EACH [c.name, c.description];

// --- Existence constraints (ensure critical properties) ---

CREATE CONSTRAINT table_name_exists IF NOT EXISTS
FOR (t:Table) REQUIRE t.name IS NOT NULL;

CREATE CONSTRAINT column_name_exists IF NOT EXISTS
FOR (c:Column) REQUIRE c.name IS NOT NULL;

CREATE CONSTRAINT policy_type_exists IF NOT EXISTS
FOR (p:Policy) REQUIRE p.policy_type IS NOT NULL;

CREATE CONSTRAINT policy_nl_exists IF NOT EXISTS
FOR (p:Policy) REQUIRE p.nl_description IS NOT NULL;

CREATE CONSTRAINT policy_rule_exists IF NOT EXISTS
FOR (p:Policy) REQUIRE p.structured_rule IS NOT NULL;
