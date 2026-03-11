// ============================================================
// tsdb — Audit Database (Timescale PostgreSQL)
// ============================================================

// --- Database & Schema ---
MERGE (db_ts:Database {name: "tsdb"})
SET db_ts.engine = "timescale_postgresql", db_ts.host = "pg-audit",
    db_ts.port = 37990, db_ts.is_active = true,
    db_ts.created_at = datetime(), db_ts.version = 1;

MERGE (s_pub:Schema {fqn: "tsdb.public"})
SET s_pub.name = "public", s_pub.is_active = true, s_pub.created_at = datetime(), s_pub.version = 1;

MERGE (db_ts)-[:HAS_SCHEMA]->(s_pub);

// --- Domain ---
MERGE (d_audit:Domain {name: "audit"})
SET d_audit.description = "Audit trails, change logs, and compliance records",
    d_audit.created_at = datetime(), d_audit.version = 1;

// --- Regulations ---
MERGE (r_hipaa:Regulation {code: "HIPAA"});
MERGE (r_dpdpa:Regulation {code: "DPDPA_2023"});

// --- Tables (matching actual 001_audit_tables.sql migration) ---
MERGE (tt1:Table {fqn: "tsdb.public.graph_version"})
SET tt1.name = "graph_version", tt1.description = "Knowledge graph version tracking",
    tt1.sensitivity_level = 2, tt1.is_active = true, tt1.row_count_approx = 100,
    tt1.domain = "audit", tt1.created_at = datetime(), tt1.version = 1;

MERGE (tt2:Table {fqn: "tsdb.public.graph_change_log"})
SET tt2.name = "graph_change_log", tt2.description = "Immutable log of all graph modifications",
    tt2.sensitivity_level = 3, tt2.is_active = true, tt2.row_count_approx = 500000,
    tt2.domain = "audit", tt2.created_at = datetime(), tt2.version = 1;

MERGE (tt3:Table {fqn: "tsdb.public.policy_versions"})
SET tt3.name = "policy_versions", tt3.description = "Historical versions of security policies",
    tt3.sensitivity_level = 3, tt3.is_active = true, tt3.row_count_approx = 5000,
    tt3.domain = "audit", tt3.created_at = datetime(), tt3.version = 1;

MERGE (tt4:Table {fqn: "tsdb.public.classification_review_queue"})
SET tt4.name = "classification_review_queue", tt4.description = "PII classification reviews pending human approval",
    tt4.sensitivity_level = 2, tt4.is_active = true, tt4.row_count_approx = 1000,
    tt4.domain = "audit", tt4.created_at = datetime(), tt4.version = 1;

MERGE (tt5:Table {fqn: "tsdb.public.crawl_history"})
SET tt5.name = "crawl_history", tt5.description = "Schema crawl execution history and results",
    tt5.sensitivity_level = 2, tt5.is_active = true, tt5.row_count_approx = 500,
    tt5.domain = "audit", tt5.created_at = datetime(), tt5.version = 1;

MERGE (tt6:Table {fqn: "tsdb.public.embedding_metadata"})
SET tt6.name = "embedding_metadata", tt6.description = "Semantic embedding metadata and content hashes",
    tt6.sensitivity_level = 1, tt6.is_active = true, tt6.row_count_approx = 5000,
    tt6.domain = "audit", tt6.created_at = datetime(), tt6.version = 1;

MERGE (tt7:Table {fqn: "tsdb.public.api_access_log"})
SET tt7.name = "api_access_log", tt7.description = "API access audit trail — who queried what and when",
    tt7.sensitivity_level = 3, tt7.is_active = true, tt7.row_count_approx = 2000000,
    tt7.domain = "audit", tt7.created_at = datetime(), tt7.version = 1;

// Schema-Table links
MERGE (s_pub)-[:HAS_TABLE]->(tt1);
MERGE (s_pub)-[:HAS_TABLE]->(tt2);
MERGE (s_pub)-[:HAS_TABLE]->(tt3);
MERGE (s_pub)-[:HAS_TABLE]->(tt4);
MERGE (s_pub)-[:HAS_TABLE]->(tt5);
MERGE (s_pub)-[:HAS_TABLE]->(tt6);
MERGE (s_pub)-[:HAS_TABLE]->(tt7);

// Domain links
MERGE (tt1)-[:BELONGS_TO_DOMAIN]->(d_audit);
MERGE (tt2)-[:BELONGS_TO_DOMAIN]->(d_audit);
MERGE (tt3)-[:BELONGS_TO_DOMAIN]->(d_audit);
MERGE (tt4)-[:BELONGS_TO_DOMAIN]->(d_audit);
MERGE (tt5)-[:BELONGS_TO_DOMAIN]->(d_audit);
MERGE (tt6)-[:BELONGS_TO_DOMAIN]->(d_audit);
MERGE (tt7)-[:BELONGS_TO_DOMAIN]->(d_audit);

// Audit logs regulated under HIPAA (audit trail requirement)
MERGE (tt2)-[:REGULATED_BY]->(r_hipaa);
MERGE (tt7)-[:REGULATED_BY]->(r_hipaa);

// --- Key Columns (api_access_log — contains user identifiers) ---
MERGE (ca1:Column {fqn: "tsdb.public.api_access_log.log_id"})
SET ca1.name = "log_id", ca1.data_type = "bigint", ca1.is_pk = true, ca1.is_nullable = false,
    ca1.sensitivity_level = 1, ca1.is_pii = false, ca1.is_active = true, ca1.version = 1;

MERGE (ca2:Column {fqn: "tsdb.public.api_access_log.service_id"})
SET ca2.name = "service_id", ca2.data_type = "varchar(100)", ca2.is_nullable = false,
    ca2.sensitivity_level = 2, ca2.is_pii = false, ca2.is_active = true, ca2.version = 1;

MERGE (ca3:Column {fqn: "tsdb.public.api_access_log.query_text"})
SET ca3.name = "query_text", ca3.data_type = "text", ca3.is_nullable = true,
    ca3.sensitivity_level = 4, ca3.is_pii = true, ca3.pii_type = "QUERY_CONTENT",
    ca3.masking_strategy = "REDACT",
    ca3.description = "Raw NL query may contain patient names or identifiers",
    ca3.is_active = true, ca3.version = 1;

MERGE (ca4:Column {fqn: "tsdb.public.api_access_log.accessed_at"})
SET ca4.name = "accessed_at", ca4.data_type = "timestamptz", ca4.is_nullable = false,
    ca4.sensitivity_level = 1, ca4.is_pii = false, ca4.is_active = true, ca4.version = 1;

MERGE (tt7)-[:HAS_COLUMN]->(ca1);
MERGE (tt7)-[:HAS_COLUMN]->(ca2);
MERGE (tt7)-[:HAS_COLUMN]->(ca3);
MERGE (tt7)-[:HAS_COLUMN]->(ca4);

// Column regulatory
MERGE (ca3)-[:COLUMN_REGULATED_BY]->(r_hipaa);

// --- Audit Roles ---
MERGE (r_auditor:Role {name: "compliance_auditor"})
SET r_auditor.description = "Compliance auditor — read-only access to all audit trails",
    r_auditor.is_active = true, r_auditor.version = 1;

MERGE (r_sys_admin:Role {name: "system_admin"})
SET r_sys_admin.description = "System administrator — audit DB management",
    r_sys_admin.is_active = true, r_sys_admin.version = 1;

MERGE (r_auditor)-[:ACCESSES_DOMAIN]->(d_audit);
MERGE (r_sys_admin)-[:ACCESSES_DOMAIN]->(d_audit);

// --- Audit Policies ---
MERGE (p_aud1:Policy {policy_id: "POL-AUD-001"})
SET p_aud1.policy_type = "ALLOW",
    p_aud1.nl_description = "Compliance auditors have read-only access to all audit tables",
    p_aud1.structured_rule = '{"effect":"ALLOW","target":{"domain":"audit"},"subject":{"role":"compliance_auditor"},"access_type":"READ_ONLY"}',
    p_aud1.priority = 100, p_aud1.is_active = true, p_aud1.created_at = datetime(), p_aud1.version = 1;
MERGE (p_aud1)-[:APPLIES_TO_ROLE]->(r_auditor);
MERGE (p_aud1)-[:GOVERNS_DOMAIN]->(d_audit);

MERGE (p_aud2:Policy {policy_id: "POL-AUD-002"})
SET p_aud2.policy_type = "MASK",
    p_aud2.nl_description = "Query text in API access logs is redacted for non-admin roles",
    p_aud2.structured_rule = '{"effect":"MASK","target":{"table":"api_access_log","columns":["query_text"]},"subject":{"role":"*"},"exception":{"roles":["system_admin"]}}',
    p_aud2.priority = 150, p_aud2.is_active = true, p_aud2.created_at = datetime(), p_aud2.version = 1;
MERGE (p_aud2)-[:GOVERNS_TABLE]->(tt7);
MERGE (p_aud2)-[:GOVERNS_COLUMN]->(ca3);
