// ============================================================
// tsdb — Audit Trail Database (Timescale Cloud)
// Auto-generated from live crawl at 2026-03-03 19:28:09
// ============================================================

// --- Database ---
MERGE (db:Database {name: "tsdb"})
SET db.engine = "timescale_postgresql", db.is_active = true,
    db.created_at = datetime(), db.source = "live_crawl";

// --- Schemas ---
MERGE (s0:Schema {fqn: "tsdb.ai"})
SET s0.name = "ai", s0.is_active = true;
MERGE (s1:Schema {fqn: "tsdb.public"})
SET s1.name = "public", s1.is_active = true;

MERGE (db)-[:HAS_SCHEMA]->(s0);
MERGE (db)-[:HAS_SCHEMA]->(s1);

// --- Tables ---
MERGE (t0:Table {fqn: "tsdb.ai._secret_permissions"})
SET t0.name = "_secret_permissions", t0.is_active = true,
    t0.row_count_approx = 0,
    t0.sensitivity_level = 0, t0.has_pii = false,
    t0.domain = "security", t0.source = "live_crawl";

MERGE (t1:Table {fqn: "tsdb.ai.feature_flag"})
SET t1.name = "feature_flag", t1.is_active = true,
    t1.row_count_approx = 0,
    t1.sensitivity_level = 0, t1.has_pii = false,
    t1.domain = "general", t1.source = "live_crawl";

MERGE (t2:Table {fqn: "tsdb.ai.migration"})
SET t2.name = "migration", t2.is_active = true,
    t2.row_count_approx = 0,
    t2.sensitivity_level = 0, t2.has_pii = false,
    t2.domain = "general", t2.source = "live_crawl";

MERGE (t3:Table {fqn: "tsdb.public.access_events"})
SET t3.name = "access_events", t3.is_active = true,
    t3.row_count_approx = 0,
    t3.sensitivity_level = 0, t3.has_pii = false,
    t3.domain = "general", t3.source = "live_crawl";

MERGE (t4:Table {fqn: "tsdb.public.alert_history"})
SET t4.name = "alert_history", t4.is_active = true,
    t4.row_count_approx = 0,
    t4.sensitivity_level = 0, t4.has_pii = false,
    t4.domain = "general", t4.source = "live_crawl";

MERGE (t5:Table {fqn: "tsdb.public.anomaly_scores"})
SET t5.name = "anomaly_scores", t5.is_active = true,
    t5.row_count_approx = 0,
    t5.sensitivity_level = 0, t5.has_pii = false,
    t5.domain = "general", t5.source = "live_crawl";

MERGE (t6:Table {fqn: "tsdb.public.api_access_log"})
SET t6.name = "api_access_log", t6.is_active = true,
    t6.row_count_approx = 0,
    t6.sensitivity_level = 0, t6.has_pii = false,
    t6.domain = "audit", t6.source = "live_crawl";

MERGE (t7:Table {fqn: "tsdb.public.audit_events"})
SET t7.name = "audit_events", t7.is_active = true,
    t7.row_count_approx = 0,
    t7.sensitivity_level = 0, t7.has_pii = false,
    t7.domain = "audit", t7.source = "live_crawl";

MERGE (t8:Table {fqn: "tsdb.public.btg_sessions"})
SET t8.name = "btg_sessions", t8.is_active = true,
    t8.row_count_approx = 0,
    t8.sensitivity_level = 0, t8.has_pii = false,
    t8.domain = "general", t8.source = "live_crawl";

MERGE (t9:Table {fqn: "tsdb.public.classification_review_queue"})
SET t9.name = "classification_review_queue", t9.is_active = true,
    t9.row_count_approx = 0,
    t9.sensitivity_level = 0, t9.has_pii = false,
    t9.domain = "general", t9.source = "live_crawl";

MERGE (t10:Table {fqn: "tsdb.public.compliance_reports"})
SET t10.name = "compliance_reports", t10.is_active = true,
    t10.row_count_approx = 0,
    t10.sensitivity_level = 0, t10.has_pii = false,
    t10.domain = "analytics", t10.source = "live_crawl";

MERGE (t11:Table {fqn: "tsdb.public.crawl_history"})
SET t11.name = "crawl_history", t11.is_active = true,
    t11.row_count_approx = 0,
    t11.sensitivity_level = 0, t11.has_pii = false,
    t11.domain = "general", t11.source = "live_crawl";

MERGE (t12:Table {fqn: "tsdb.public.embedding_metadata"})
SET t12.name = "embedding_metadata", t12.is_active = true,
    t12.row_count_approx = 0,
    t12.sensitivity_level = 0, t12.has_pii = false,
    t12.domain = "clinical", t12.source = "live_crawl";

MERGE (t13:Table {fqn: "tsdb.public.graph_change_log"})
SET t13.name = "graph_change_log", t13.is_active = true,
    t13.row_count_approx = 0,
    t13.sensitivity_level = 0, t13.has_pii = false,
    t13.domain = "audit", t13.source = "live_crawl";

MERGE (t14:Table {fqn: "tsdb.public.graph_version"})
SET t14.name = "graph_version", t14.is_active = true,
    t14.row_count_approx = 0,
    t14.sensitivity_level = 0, t14.has_pii = false,
    t14.domain = "audit", t14.source = "live_crawl";

MERGE (t15:Table {fqn: "tsdb.public.policy_versions"})
SET t15.name = "policy_versions", t15.is_active = true,
    t15.row_count_approx = 0,
    t15.sensitivity_level = 0, t15.has_pii = false,
    t15.domain = "audit", t15.source = "live_crawl";

// Schema-Table links
MERGE (s0)-[:HAS_TABLE]->(t0);
MERGE (s0)-[:HAS_TABLE]->(t1);
MERGE (s0)-[:HAS_TABLE]->(t2);
MERGE (s1)-[:HAS_TABLE]->(t3);
MERGE (s1)-[:HAS_TABLE]->(t4);
MERGE (s1)-[:HAS_TABLE]->(t5);
MERGE (s1)-[:HAS_TABLE]->(t6);
MERGE (s1)-[:HAS_TABLE]->(t7);
MERGE (s1)-[:HAS_TABLE]->(t8);
MERGE (s1)-[:HAS_TABLE]->(t9);
MERGE (s1)-[:HAS_TABLE]->(t10);
MERGE (s1)-[:HAS_TABLE]->(t11);
MERGE (s1)-[:HAS_TABLE]->(t12);
MERGE (s1)-[:HAS_TABLE]->(t13);
MERGE (s1)-[:HAS_TABLE]->(t14);
MERGE (s1)-[:HAS_TABLE]->(t15);

// --- Columns (_secret_permissions) ---
MERGE (c0:Column {fqn: "tsdb.ai._secret_permissions.name"})
SET c0.name = "name", c0.data_type = "text", c0.is_pk = true, c0.is_nullable = false, c0.ordinal_position = 1, c0.is_active = true;

MERGE (c1:Column {fqn: "tsdb.ai._secret_permissions.role"})
SET c1.name = "role", c1.data_type = "text", c1.is_pk = true, c1.is_nullable = false, c1.ordinal_position = 2, c1.is_active = true;

// Column-Table links (_secret_permissions)
MERGE (t0)-[:HAS_COLUMN]->(c0);
MERGE (t0)-[:HAS_COLUMN]->(c1);

// --- Columns (feature_flag) ---
MERGE (c2:Column {fqn: "tsdb.ai.feature_flag.name"})
SET c2.name = "name", c2.data_type = "text", c2.is_pk = true, c2.is_nullable = false, c2.ordinal_position = 1, c2.is_active = true;

MERGE (c3:Column {fqn: "tsdb.ai.feature_flag.applied_at_version"})
SET c3.name = "applied_at_version", c3.data_type = "text", c3.is_nullable = false, c3.ordinal_position = 2, c3.is_active = true;

MERGE (c4:Column {fqn: "tsdb.ai.feature_flag.applied_at"})
SET c4.name = "applied_at", c4.data_type = "timestamp with time zone", c4.is_nullable = false, c4.ordinal_position = 3, c4.is_active = true;

// Column-Table links (feature_flag)
MERGE (t1)-[:HAS_COLUMN]->(c2);
MERGE (t1)-[:HAS_COLUMN]->(c3);
MERGE (t1)-[:HAS_COLUMN]->(c4);

// --- Columns (migration) ---
MERGE (c5:Column {fqn: "tsdb.ai.migration.name"})
SET c5.name = "name", c5.data_type = "text", c5.is_pk = true, c5.is_nullable = false, c5.ordinal_position = 1, c5.is_active = true;

MERGE (c6:Column {fqn: "tsdb.ai.migration.applied_at_version"})
SET c6.name = "applied_at_version", c6.data_type = "text", c6.is_nullable = false, c6.ordinal_position = 2, c6.is_active = true;

MERGE (c7:Column {fqn: "tsdb.ai.migration.applied_at"})
SET c7.name = "applied_at", c7.data_type = "timestamp with time zone", c7.is_nullable = false, c7.ordinal_position = 3, c7.is_active = true;

MERGE (c8:Column {fqn: "tsdb.ai.migration.body"})
SET c8.name = "body", c8.data_type = "text", c8.is_nullable = false, c8.ordinal_position = 4, c8.is_active = true;

// Column-Table links (migration)
MERGE (t2)-[:HAS_COLUMN]->(c5);
MERGE (t2)-[:HAS_COLUMN]->(c6);
MERGE (t2)-[:HAS_COLUMN]->(c7);
MERGE (t2)-[:HAS_COLUMN]->(c8);

// --- Columns (access_events) ---
MERGE (c9:Column {fqn: "tsdb.public.access_events.access_id"})
SET c9.name = "access_id", c9.data_type = "uuid", c9.is_pk = true, c9.is_nullable = false, c9.ordinal_position = 1, c9.is_active = true;

MERGE (c10:Column {fqn: "tsdb.public.access_events.timestamp"})
SET c10.name = "timestamp", c10.data_type = "timestamp with time zone", c10.is_pk = true, c10.is_nullable = false, c10.ordinal_position = 2, c10.is_active = true;

MERGE (c11:Column {fqn: "tsdb.public.access_events.user_id"})
SET c11.name = "user_id", c11.data_type = "character varying", c11.is_nullable = false, c11.ordinal_position = 3, c11.is_active = true;

MERGE (c12:Column {fqn: "tsdb.public.access_events.user_role"})
SET c12.name = "user_role", c12.data_type = "character varying", c12.is_nullable = true, c12.ordinal_position = 4, c12.is_active = true;

MERGE (c13:Column {fqn: "tsdb.public.access_events.facility_id"})
SET c13.name = "facility_id", c13.data_type = "character varying", c13.is_nullable = true, c13.ordinal_position = 5, c13.is_active = true;

MERGE (c14:Column {fqn: "tsdb.public.access_events.request_id"})
SET c14.name = "request_id", c14.data_type = "uuid", c14.is_nullable = true, c14.ordinal_position = 6, c14.is_active = true;

MERGE (c15:Column {fqn: "tsdb.public.access_events.action"})
SET c15.name = "action", c15.data_type = "character varying", c15.is_nullable = false, c15.ordinal_position = 7, c15.is_active = true;

MERGE (c16:Column {fqn: "tsdb.public.access_events.tables_accessed"})
SET c16.name = "tables_accessed", c16.data_type = "ARRAY", c16.is_nullable = true, c16.ordinal_position = 8, c16.is_active = true;

MERGE (c17:Column {fqn: "tsdb.public.access_events.columns_accessed"})
SET c17.name = "columns_accessed", c17.data_type = "ARRAY", c17.is_nullable = true, c17.ordinal_position = 9, c17.is_active = true;

MERGE (c18:Column {fqn: "tsdb.public.access_events.rows_returned"})
SET c18.name = "rows_returned", c18.data_type = "integer", c18.is_nullable = true, c18.ordinal_position = 10, c18.is_active = true;

MERGE (c19:Column {fqn: "tsdb.public.access_events.execution_time_ms"})
SET c19.name = "execution_time_ms", c19.data_type = "numeric", c19.is_nullable = true, c19.ordinal_position = 11, c19.is_active = true;

MERGE (c20:Column {fqn: "tsdb.public.access_events.database_used"})
SET c20.name = "database_used", c20.data_type = "character varying", c20.is_nullable = true, c20.ordinal_position = 12, c20.is_active = true;

MERGE (c21:Column {fqn: "tsdb.public.access_events.sql_hash"})
SET c21.name = "sql_hash", c21.data_type = "character varying", c21.is_nullable = true, c21.ordinal_position = 13, c21.is_active = true;

MERGE (c22:Column {fqn: "tsdb.public.access_events.validation_result"})
SET c22.name = "validation_result", c22.data_type = "character varying", c22.is_nullable = true, c22.ordinal_position = 14, c22.is_active = true;

MERGE (c23:Column {fqn: "tsdb.public.access_events.violations"})
SET c23.name = "violations", c23.data_type = "jsonb", c23.is_nullable = true, c23.ordinal_position = 15, c23.is_active = true;

MERGE (c24:Column {fqn: "tsdb.public.access_events.rewrites_applied"})
SET c24.name = "rewrites_applied", c24.data_type = "jsonb", c24.is_nullable = true, c24.ordinal_position = 16, c24.is_active = true;

MERGE (c25:Column {fqn: "tsdb.public.access_events.sanitization_events"})
SET c25.name = "sanitization_events", c25.data_type = "integer", c25.is_nullable = true, c25.ordinal_position = 17, c25.is_active = true;

// Column-Table links (access_events)
MERGE (t3)-[:HAS_COLUMN]->(c9);
MERGE (t3)-[:HAS_COLUMN]->(c10);
MERGE (t3)-[:HAS_COLUMN]->(c11);
MERGE (t3)-[:HAS_COLUMN]->(c12);
MERGE (t3)-[:HAS_COLUMN]->(c13);
MERGE (t3)-[:HAS_COLUMN]->(c14);
MERGE (t3)-[:HAS_COLUMN]->(c15);
MERGE (t3)-[:HAS_COLUMN]->(c16);
MERGE (t3)-[:HAS_COLUMN]->(c17);
MERGE (t3)-[:HAS_COLUMN]->(c18);
MERGE (t3)-[:HAS_COLUMN]->(c19);
MERGE (t3)-[:HAS_COLUMN]->(c20);
MERGE (t3)-[:HAS_COLUMN]->(c21);
MERGE (t3)-[:HAS_COLUMN]->(c22);
MERGE (t3)-[:HAS_COLUMN]->(c23);
MERGE (t3)-[:HAS_COLUMN]->(c24);
MERGE (t3)-[:HAS_COLUMN]->(c25);

// --- Columns (alert_history) ---
MERGE (c26:Column {fqn: "tsdb.public.alert_history.alert_id"})
SET c26.name = "alert_id", c26.data_type = "uuid", c26.is_pk = true, c26.is_nullable = false, c26.ordinal_position = 1, c26.is_active = true;

MERGE (c27:Column {fqn: "tsdb.public.alert_history.created_at"})
SET c27.name = "created_at", c27.data_type = "timestamp with time zone", c27.is_nullable = false, c27.ordinal_position = 2, c27.is_active = true;

MERGE (c28:Column {fqn: "tsdb.public.alert_history.alert_type"})
SET c28.name = "alert_type", c28.data_type = "character varying", c28.is_nullable = false, c28.ordinal_position = 3, c28.is_active = true;

MERGE (c29:Column {fqn: "tsdb.public.alert_history.severity"})
SET c29.name = "severity", c29.data_type = "character varying", c29.is_nullable = false, c29.ordinal_position = 4, c29.is_active = true;

MERGE (c30:Column {fqn: "tsdb.public.alert_history.user_id"})
SET c30.name = "user_id", c30.data_type = "character varying", c30.is_nullable = true, c30.ordinal_position = 5, c30.is_active = true;

MERGE (c31:Column {fqn: "tsdb.public.alert_history.description"})
SET c31.name = "description", c31.data_type = "text", c31.is_nullable = true, c31.ordinal_position = 6, c31.is_active = true;

MERGE (c32:Column {fqn: "tsdb.public.alert_history.detection_source"})
SET c32.name = "detection_source", c32.data_type = "character varying", c32.is_nullable = true, c32.ordinal_position = 7, c32.is_active = true;

MERGE (c33:Column {fqn: "tsdb.public.alert_history.anomaly_score"})
SET c33.name = "anomaly_score", c33.data_type = "numeric", c33.is_nullable = true, c33.ordinal_position = 8, c33.is_active = true;

MERGE (c34:Column {fqn: "tsdb.public.alert_history.occurrence_count"})
SET c34.name = "occurrence_count", c34.data_type = "integer", c34.is_nullable = true, c34.ordinal_position = 9, c34.is_active = true;

MERGE (c35:Column {fqn: "tsdb.public.alert_history.status"})
SET c35.name = "status", c35.data_type = "character varying", c35.is_nullable = true, c35.ordinal_position = 10, c35.is_active = true;

MERGE (c36:Column {fqn: "tsdb.public.alert_history.acknowledged_by"})
SET c36.name = "acknowledged_by", c36.data_type = "character varying", c36.is_nullable = true, c36.ordinal_position = 11, c36.is_active = true;

MERGE (c37:Column {fqn: "tsdb.public.alert_history.acknowledged_at"})
SET c37.name = "acknowledged_at", c37.data_type = "timestamp with time zone", c37.is_nullable = true, c37.ordinal_position = 12, c37.is_active = true;

MERGE (c38:Column {fqn: "tsdb.public.alert_history.resolved_by"})
SET c38.name = "resolved_by", c38.data_type = "character varying", c38.is_nullable = true, c38.ordinal_position = 13, c38.is_active = true;

MERGE (c39:Column {fqn: "tsdb.public.alert_history.resolved_at"})
SET c39.name = "resolved_at", c39.data_type = "timestamp with time zone", c39.is_nullable = true, c39.ordinal_position = 14, c39.is_active = true;

MERGE (c40:Column {fqn: "tsdb.public.alert_history.resolution_notes"})
SET c40.name = "resolution_notes", c40.data_type = "text", c40.is_nullable = true, c40.ordinal_position = 15, c40.is_active = true;

MERGE (c41:Column {fqn: "tsdb.public.alert_history.related_request_ids"})
SET c41.name = "related_request_ids", c41.data_type = "ARRAY", c41.is_nullable = true, c41.ordinal_position = 16, c41.is_active = true;

MERGE (c42:Column {fqn: "tsdb.public.alert_history.escalated"})
SET c42.name = "escalated", c42.data_type = "boolean", c42.is_nullable = true, c42.ordinal_position = 17, c42.is_active = true;

MERGE (c43:Column {fqn: "tsdb.public.alert_history.escalation_level"})
SET c43.name = "escalation_level", c43.data_type = "integer", c43.is_nullable = true, c43.ordinal_position = 18, c43.is_active = true;

// Column-Table links (alert_history)
MERGE (t4)-[:HAS_COLUMN]->(c26);
MERGE (t4)-[:HAS_COLUMN]->(c27);
MERGE (t4)-[:HAS_COLUMN]->(c28);
MERGE (t4)-[:HAS_COLUMN]->(c29);
MERGE (t4)-[:HAS_COLUMN]->(c30);
MERGE (t4)-[:HAS_COLUMN]->(c31);
MERGE (t4)-[:HAS_COLUMN]->(c32);
MERGE (t4)-[:HAS_COLUMN]->(c33);
MERGE (t4)-[:HAS_COLUMN]->(c34);
MERGE (t4)-[:HAS_COLUMN]->(c35);
MERGE (t4)-[:HAS_COLUMN]->(c36);
MERGE (t4)-[:HAS_COLUMN]->(c37);
MERGE (t4)-[:HAS_COLUMN]->(c38);
MERGE (t4)-[:HAS_COLUMN]->(c39);
MERGE (t4)-[:HAS_COLUMN]->(c40);
MERGE (t4)-[:HAS_COLUMN]->(c41);
MERGE (t4)-[:HAS_COLUMN]->(c42);
MERGE (t4)-[:HAS_COLUMN]->(c43);

// --- Columns (anomaly_scores) ---
MERGE (c44:Column {fqn: "tsdb.public.anomaly_scores.score_id"})
SET c44.name = "score_id", c44.data_type = "uuid", c44.is_pk = true, c44.is_nullable = false, c44.ordinal_position = 1, c44.is_active = true;

MERGE (c45:Column {fqn: "tsdb.public.anomaly_scores.timestamp"})
SET c45.name = "timestamp", c45.data_type = "timestamp with time zone", c45.is_pk = true, c45.is_nullable = false, c45.ordinal_position = 2, c45.is_active = true;

MERGE (c46:Column {fqn: "tsdb.public.anomaly_scores.user_id"})
SET c46.name = "user_id", c46.data_type = "character varying", c46.is_nullable = false, c46.ordinal_position = 3, c46.is_active = true;

MERGE (c47:Column {fqn: "tsdb.public.anomaly_scores.model_name"})
SET c47.name = "model_name", c47.data_type = "character varying", c47.is_nullable = false, c47.ordinal_position = 4, c47.is_active = true;

MERGE (c48:Column {fqn: "tsdb.public.anomaly_scores.model_version"})
SET c48.name = "model_version", c48.data_type = "character varying", c48.is_nullable = true, c48.ordinal_position = 5, c48.is_active = true;

MERGE (c49:Column {fqn: "tsdb.public.anomaly_scores.anomaly_score"})
SET c49.name = "anomaly_score", c49.data_type = "numeric", c49.is_nullable = false, c49.ordinal_position = 6, c49.is_active = true;

MERGE (c50:Column {fqn: "tsdb.public.anomaly_scores.feature_vector"})
SET c50.name = "feature_vector", c50.data_type = "jsonb", c50.is_nullable = true, c50.ordinal_position = 7, c50.is_active = true;

MERGE (c51:Column {fqn: "tsdb.public.anomaly_scores.is_anomaly"})
SET c51.name = "is_anomaly", c51.data_type = "boolean", c51.is_nullable = true, c51.ordinal_position = 8, c51.is_active = true;

MERGE (c52:Column {fqn: "tsdb.public.anomaly_scores.alert_generated"})
SET c52.name = "alert_generated", c52.data_type = "boolean", c52.is_nullable = true, c52.ordinal_position = 9, c52.is_active = true;

// Column-Table links (anomaly_scores)
MERGE (t5)-[:HAS_COLUMN]->(c44);
MERGE (t5)-[:HAS_COLUMN]->(c45);
MERGE (t5)-[:HAS_COLUMN]->(c46);
MERGE (t5)-[:HAS_COLUMN]->(c47);
MERGE (t5)-[:HAS_COLUMN]->(c48);
MERGE (t5)-[:HAS_COLUMN]->(c49);
MERGE (t5)-[:HAS_COLUMN]->(c50);
MERGE (t5)-[:HAS_COLUMN]->(c51);
MERGE (t5)-[:HAS_COLUMN]->(c52);

// --- Columns (api_access_log) ---
MERGE (c53:Column {fqn: "tsdb.public.api_access_log.id"})
SET c53.name = "id", c53.data_type = "bigint", c53.is_pk = true, c53.is_nullable = false, c53.ordinal_position = 1, c53.is_active = true;

MERGE (c54:Column {fqn: "tsdb.public.api_access_log.service_id"})
SET c54.name = "service_id", c54.data_type = "character varying", c54.is_nullable = false, c54.ordinal_position = 2, c54.is_active = true;

MERGE (c55:Column {fqn: "tsdb.public.api_access_log.endpoint"})
SET c55.name = "endpoint", c55.data_type = "character varying", c55.is_nullable = false, c55.ordinal_position = 3, c55.is_active = true;

MERGE (c56:Column {fqn: "tsdb.public.api_access_log.method"})
SET c56.name = "method", c56.data_type = "character varying", c56.is_nullable = false, c56.ordinal_position = 4, c56.is_active = true;

MERGE (c57:Column {fqn: "tsdb.public.api_access_log.status_code"})
SET c57.name = "status_code", c57.data_type = "integer", c57.is_nullable = false, c57.ordinal_position = 5, c57.is_active = true;

MERGE (c58:Column {fqn: "tsdb.public.api_access_log.latency_ms"})
SET c58.name = "latency_ms", c58.data_type = "double precision", c58.is_nullable = false, c58.ordinal_position = 6, c58.is_active = true;

MERGE (c59:Column {fqn: "tsdb.public.api_access_log.created_at"})
SET c59.name = "created_at", c59.data_type = "timestamp with time zone", c59.is_nullable = false, c59.ordinal_position = 7, c59.is_active = true;

// Column-Table links (api_access_log)
MERGE (t6)-[:HAS_COLUMN]->(c53);
MERGE (t6)-[:HAS_COLUMN]->(c54);
MERGE (t6)-[:HAS_COLUMN]->(c55);
MERGE (t6)-[:HAS_COLUMN]->(c56);
MERGE (t6)-[:HAS_COLUMN]->(c57);
MERGE (t6)-[:HAS_COLUMN]->(c58);
MERGE (t6)-[:HAS_COLUMN]->(c59);

// --- Columns (audit_events) ---
MERGE (c60:Column {fqn: "tsdb.public.audit_events.event_id"})
SET c60.name = "event_id", c60.data_type = "uuid", c60.is_pk = true, c60.is_nullable = false, c60.ordinal_position = 1, c60.is_active = true;

MERGE (c61:Column {fqn: "tsdb.public.audit_events.event_type"})
SET c61.name = "event_type", c61.data_type = "character varying", c61.is_nullable = false, c61.ordinal_position = 2, c61.is_active = true;

MERGE (c62:Column {fqn: "tsdb.public.audit_events.source_layer"})
SET c62.name = "source_layer", c62.data_type = "character varying", c62.is_nullable = false, c62.ordinal_position = 3, c62.is_active = true;

MERGE (c63:Column {fqn: "tsdb.public.audit_events.timestamp"})
SET c63.name = "timestamp", c63.data_type = "timestamp with time zone", c63.is_pk = true, c63.is_nullable = false, c63.ordinal_position = 4, c63.is_active = true;

MERGE (c64:Column {fqn: "tsdb.public.audit_events.request_id"})
SET c64.name = "request_id", c64.data_type = "uuid", c64.is_nullable = true, c64.ordinal_position = 5, c64.is_active = true;

MERGE (c65:Column {fqn: "tsdb.public.audit_events.user_id"})
SET c65.name = "user_id", c65.data_type = "character varying", c65.is_nullable = true, c65.ordinal_position = 6, c65.is_active = true;

MERGE (c66:Column {fqn: "tsdb.public.audit_events.session_id"})
SET c66.name = "session_id", c66.data_type = "character varying", c66.is_nullable = true, c66.ordinal_position = 7, c66.is_active = true;

MERGE (c67:Column {fqn: "tsdb.public.audit_events.severity"})
SET c67.name = "severity", c67.data_type = "character varying", c67.is_nullable = false, c67.ordinal_position = 8, c67.is_active = true;

MERGE (c68:Column {fqn: "tsdb.public.audit_events.btg_active"})
SET c68.name = "btg_active", c68.data_type = "boolean", c68.is_nullable = true, c68.ordinal_position = 9, c68.is_active = true;

MERGE (c69:Column {fqn: "tsdb.public.audit_events.payload"})
SET c69.name = "payload", c69.data_type = "jsonb", c69.is_nullable = false, c69.ordinal_position = 10, c69.is_active = true;

MERGE (c70:Column {fqn: "tsdb.public.audit_events.hmac_signature"})
SET c70.name = "hmac_signature", c70.data_type = "character varying", c70.is_nullable = true, c70.ordinal_position = 11, c70.is_active = true;

MERGE (c71:Column {fqn: "tsdb.public.audit_events.chain_hash"})
SET c71.name = "chain_hash", c71.data_type = "character varying", c71.is_nullable = true, c71.ordinal_position = 12, c71.is_active = true;

MERGE (c72:Column {fqn: "tsdb.public.audit_events.previous_chain_hash"})
SET c72.name = "previous_chain_hash", c72.data_type = "character varying", c72.is_nullable = true, c72.ordinal_position = 13, c72.is_active = true;

// Column-Table links (audit_events)
MERGE (t7)-[:HAS_COLUMN]->(c60);
MERGE (t7)-[:HAS_COLUMN]->(c61);
MERGE (t7)-[:HAS_COLUMN]->(c62);
MERGE (t7)-[:HAS_COLUMN]->(c63);
MERGE (t7)-[:HAS_COLUMN]->(c64);
MERGE (t7)-[:HAS_COLUMN]->(c65);
MERGE (t7)-[:HAS_COLUMN]->(c66);
MERGE (t7)-[:HAS_COLUMN]->(c67);
MERGE (t7)-[:HAS_COLUMN]->(c68);
MERGE (t7)-[:HAS_COLUMN]->(c69);
MERGE (t7)-[:HAS_COLUMN]->(c70);
MERGE (t7)-[:HAS_COLUMN]->(c71);
MERGE (t7)-[:HAS_COLUMN]->(c72);

// --- Columns (btg_sessions) ---
MERGE (c73:Column {fqn: "tsdb.public.btg_sessions.session_id"})
SET c73.name = "session_id", c73.data_type = "uuid", c73.is_pk = true, c73.is_nullable = false, c73.ordinal_position = 1, c73.is_active = true;

MERGE (c74:Column {fqn: "tsdb.public.btg_sessions.user_id"})
SET c74.name = "user_id", c74.data_type = "character varying", c74.is_nullable = false, c74.ordinal_position = 2, c74.is_active = true;

MERGE (c75:Column {fqn: "tsdb.public.btg_sessions.activated_at"})
SET c75.name = "activated_at", c75.data_type = "timestamp with time zone", c75.is_nullable = false, c75.ordinal_position = 3, c75.is_active = true;

MERGE (c76:Column {fqn: "tsdb.public.btg_sessions.expired_at"})
SET c76.name = "expired_at", c76.data_type = "timestamp with time zone", c76.is_nullable = true, c76.ordinal_position = 4, c76.is_active = true;

MERGE (c77:Column {fqn: "tsdb.public.btg_sessions.duration_minutes"})
SET c77.name = "duration_minutes", c77.data_type = "integer", c77.is_nullable = true, c77.ordinal_position = 5, c77.is_active = true;

MERGE (c78:Column {fqn: "tsdb.public.btg_sessions.justification"})
SET c78.name = "justification", c78.data_type = "text", c78.is_nullable = false, c78.ordinal_position = 6, c78.is_active = true;

MERGE (c79:Column {fqn: "tsdb.public.btg_sessions.emergency_type"})
SET c79.name = "emergency_type", c79.data_type = "character varying", c79.is_nullable = true, c79.ordinal_position = 7, c79.is_active = true;

MERGE (c80:Column {fqn: "tsdb.public.btg_sessions.patient_ids"})
SET c80.name = "patient_ids", c80.data_type = "ARRAY", c80.is_nullable = true, c80.ordinal_position = 8, c80.is_active = true;

MERGE (c81:Column {fqn: "tsdb.public.btg_sessions.tables_accessed"})
SET c81.name = "tables_accessed", c81.data_type = "ARRAY", c81.is_nullable = true, c81.ordinal_position = 9, c81.is_active = true;

MERGE (c82:Column {fqn: "tsdb.public.btg_sessions.queries_executed"})
SET c82.name = "queries_executed", c82.data_type = "integer", c82.is_nullable = true, c82.ordinal_position = 10, c82.is_active = true;

MERGE (c83:Column {fqn: "tsdb.public.btg_sessions.rows_accessed"})
SET c83.name = "rows_accessed", c83.data_type = "integer", c83.is_nullable = true, c83.ordinal_position = 11, c83.is_active = true;

MERGE (c84:Column {fqn: "tsdb.public.btg_sessions.review_status"})
SET c84.name = "review_status", c84.data_type = "character varying", c84.is_nullable = true, c84.ordinal_position = 12, c84.is_active = true;

MERGE (c85:Column {fqn: "tsdb.public.btg_sessions.reviewed_by"})
SET c85.name = "reviewed_by", c85.data_type = "character varying", c85.is_nullable = true, c85.ordinal_position = 13, c85.is_active = true;

MERGE (c86:Column {fqn: "tsdb.public.btg_sessions.reviewed_at"})
SET c86.name = "reviewed_at", c86.data_type = "timestamp with time zone", c86.is_nullable = true, c86.ordinal_position = 14, c86.is_active = true;

MERGE (c87:Column {fqn: "tsdb.public.btg_sessions.review_notes"})
SET c87.name = "review_notes", c87.data_type = "text", c87.is_nullable = true, c87.ordinal_position = 15, c87.is_active = true;

// Column-Table links (btg_sessions)
MERGE (t8)-[:HAS_COLUMN]->(c73);
MERGE (t8)-[:HAS_COLUMN]->(c74);
MERGE (t8)-[:HAS_COLUMN]->(c75);
MERGE (t8)-[:HAS_COLUMN]->(c76);
MERGE (t8)-[:HAS_COLUMN]->(c77);
MERGE (t8)-[:HAS_COLUMN]->(c78);
MERGE (t8)-[:HAS_COLUMN]->(c79);
MERGE (t8)-[:HAS_COLUMN]->(c80);
MERGE (t8)-[:HAS_COLUMN]->(c81);
MERGE (t8)-[:HAS_COLUMN]->(c82);
MERGE (t8)-[:HAS_COLUMN]->(c83);
MERGE (t8)-[:HAS_COLUMN]->(c84);
MERGE (t8)-[:HAS_COLUMN]->(c85);
MERGE (t8)-[:HAS_COLUMN]->(c86);
MERGE (t8)-[:HAS_COLUMN]->(c87);

// --- Columns (classification_review_queue) ---
MERGE (c88:Column {fqn: "tsdb.public.classification_review_queue.id"})
SET c88.name = "id", c88.data_type = "bigint", c88.is_pk = true, c88.is_nullable = false, c88.ordinal_position = 1, c88.is_active = true;

MERGE (c89:Column {fqn: "tsdb.public.classification_review_queue.column_fqn"})
SET c89.name = "column_fqn", c89.data_type = "character varying", c89.is_nullable = false, c89.ordinal_position = 2, c89.is_active = true;

MERGE (c90:Column {fqn: "tsdb.public.classification_review_queue.suggested_sensitivity"})
SET c90.name = "suggested_sensitivity", c90.data_type = "integer", c90.is_nullable = false, c90.ordinal_position = 3, c90.is_active = true;

MERGE (c91:Column {fqn: "tsdb.public.classification_review_queue.suggested_pii_type"})
SET c91.name = "suggested_pii_type", c91.data_type = "character varying", c91.is_nullable = true, c91.ordinal_position = 4, c91.is_active = true;

MERGE (c92:Column {fqn: "tsdb.public.classification_review_queue.suggested_masking"})
SET c92.name = "suggested_masking", c92.data_type = "character varying", c92.is_nullable = true, c92.ordinal_position = 5, c92.is_active = true;

MERGE (c93:Column {fqn: "tsdb.public.classification_review_queue.confidence"})
SET c93.name = "confidence", c93.data_type = "double precision", c93.is_nullable = false, c93.ordinal_position = 6, c93.is_active = true;

MERGE (c94:Column {fqn: "tsdb.public.classification_review_queue.reason"})
SET c94.name = "reason", c94.data_type = "text", c94.is_nullable = false, c94.ordinal_position = 7, c94.is_active = true;

MERGE (c95:Column {fqn: "tsdb.public.classification_review_queue.status"})
SET c95.name = "status", c95.data_type = "character varying", c95.is_nullable = false, c95.ordinal_position = 8, c95.is_active = true;

MERGE (c96:Column {fqn: "tsdb.public.classification_review_queue.reviewed_by"})
SET c96.name = "reviewed_by", c96.data_type = "character varying", c96.is_nullable = true, c96.ordinal_position = 9, c96.is_active = true;

MERGE (c97:Column {fqn: "tsdb.public.classification_review_queue.reviewed_at"})
SET c97.name = "reviewed_at", c97.data_type = "timestamp with time zone", c97.is_nullable = true, c97.ordinal_position = 10, c97.is_active = true;

MERGE (c98:Column {fqn: "tsdb.public.classification_review_queue.created_at"})
SET c98.name = "created_at", c98.data_type = "timestamp with time zone", c98.is_nullable = false, c98.ordinal_position = 11, c98.is_active = true;

// Column-Table links (classification_review_queue)
MERGE (t9)-[:HAS_COLUMN]->(c88);
MERGE (t9)-[:HAS_COLUMN]->(c89);
MERGE (t9)-[:HAS_COLUMN]->(c90);
MERGE (t9)-[:HAS_COLUMN]->(c91);
MERGE (t9)-[:HAS_COLUMN]->(c92);
MERGE (t9)-[:HAS_COLUMN]->(c93);
MERGE (t9)-[:HAS_COLUMN]->(c94);
MERGE (t9)-[:HAS_COLUMN]->(c95);
MERGE (t9)-[:HAS_COLUMN]->(c96);
MERGE (t9)-[:HAS_COLUMN]->(c97);
MERGE (t9)-[:HAS_COLUMN]->(c98);

// --- Columns (compliance_reports) ---
MERGE (c99:Column {fqn: "tsdb.public.compliance_reports.report_id"})
SET c99.name = "report_id", c99.data_type = "uuid", c99.is_pk = true, c99.is_nullable = false, c99.ordinal_position = 1, c99.is_active = true;

MERGE (c100:Column {fqn: "tsdb.public.compliance_reports.report_type"})
SET c100.name = "report_type", c100.data_type = "character varying", c100.is_nullable = false, c100.ordinal_position = 2, c100.is_active = true;

MERGE (c101:Column {fqn: "tsdb.public.compliance_reports.report_period_start"})
SET c101.name = "report_period_start", c101.data_type = "date", c101.is_nullable = false, c101.ordinal_position = 3, c101.is_active = true;

MERGE (c102:Column {fqn: "tsdb.public.compliance_reports.report_period_end"})
SET c102.name = "report_period_end", c102.data_type = "date", c102.is_nullable = false, c102.ordinal_position = 4, c102.is_active = true;

MERGE (c103:Column {fqn: "tsdb.public.compliance_reports.generated_at"})
SET c103.name = "generated_at", c103.data_type = "timestamp with time zone", c103.is_nullable = true, c103.ordinal_position = 5, c103.is_active = true;

MERGE (c104:Column {fqn: "tsdb.public.compliance_reports.generated_by"})
SET c104.name = "generated_by", c104.data_type = "character varying", c104.is_nullable = true, c104.ordinal_position = 6, c104.is_active = true;

MERGE (c105:Column {fqn: "tsdb.public.compliance_reports.report_data"})
SET c105.name = "report_data", c105.data_type = "jsonb", c105.is_nullable = false, c105.ordinal_position = 7, c105.is_active = true;

MERGE (c106:Column {fqn: "tsdb.public.compliance_reports.file_path"})
SET c106.name = "file_path", c106.data_type = "character varying", c106.is_nullable = true, c106.ordinal_position = 8, c106.is_active = true;

MERGE (c107:Column {fqn: "tsdb.public.compliance_reports.status"})
SET c107.name = "status", c107.data_type = "character varying", c107.is_nullable = true, c107.ordinal_position = 9, c107.is_active = true;

MERGE (c108:Column {fqn: "tsdb.public.compliance_reports.reviewed_by"})
SET c108.name = "reviewed_by", c108.data_type = "character varying", c108.is_nullable = true, c108.ordinal_position = 10, c108.is_active = true;

MERGE (c109:Column {fqn: "tsdb.public.compliance_reports.reviewed_at"})
SET c109.name = "reviewed_at", c109.data_type = "timestamp with time zone", c109.is_nullable = true, c109.ordinal_position = 11, c109.is_active = true;

// Column-Table links (compliance_reports)
MERGE (t10)-[:HAS_COLUMN]->(c99);
MERGE (t10)-[:HAS_COLUMN]->(c100);
MERGE (t10)-[:HAS_COLUMN]->(c101);
MERGE (t10)-[:HAS_COLUMN]->(c102);
MERGE (t10)-[:HAS_COLUMN]->(c103);
MERGE (t10)-[:HAS_COLUMN]->(c104);
MERGE (t10)-[:HAS_COLUMN]->(c105);
MERGE (t10)-[:HAS_COLUMN]->(c106);
MERGE (t10)-[:HAS_COLUMN]->(c107);
MERGE (t10)-[:HAS_COLUMN]->(c108);
MERGE (t10)-[:HAS_COLUMN]->(c109);

// --- Columns (crawl_history) ---
MERGE (c110:Column {fqn: "tsdb.public.crawl_history.id"})
SET c110.name = "id", c110.data_type = "bigint", c110.is_pk = true, c110.is_nullable = false, c110.ordinal_position = 1, c110.is_active = true;

MERGE (c111:Column {fqn: "tsdb.public.crawl_history.database_name"})
SET c111.name = "database_name", c111.data_type = "character varying", c111.is_nullable = false, c111.ordinal_position = 2, c111.is_active = true;

MERGE (c112:Column {fqn: "tsdb.public.crawl_history.status"})
SET c112.name = "status", c112.data_type = "character varying", c112.is_nullable = false, c112.ordinal_position = 3, c112.is_active = true;

MERGE (c113:Column {fqn: "tsdb.public.crawl_history.tables_found"})
SET c113.name = "tables_found", c113.data_type = "integer", c113.is_nullable = true, c113.ordinal_position = 4, c113.is_active = true;

MERGE (c114:Column {fqn: "tsdb.public.crawl_history.tables_added"})
SET c114.name = "tables_added", c114.data_type = "integer", c114.is_nullable = true, c114.ordinal_position = 5, c114.is_active = true;

MERGE (c115:Column {fqn: "tsdb.public.crawl_history.tables_updated"})
SET c115.name = "tables_updated", c115.data_type = "integer", c115.is_nullable = true, c115.ordinal_position = 6, c115.is_active = true;

MERGE (c116:Column {fqn: "tsdb.public.crawl_history.tables_deactivated"})
SET c116.name = "tables_deactivated", c116.data_type = "integer", c116.is_nullable = true, c116.ordinal_position = 7, c116.is_active = true;

MERGE (c117:Column {fqn: "tsdb.public.crawl_history.columns_found"})
SET c117.name = "columns_found", c117.data_type = "integer", c117.is_nullable = true, c117.ordinal_position = 8, c117.is_active = true;

MERGE (c118:Column {fqn: "tsdb.public.crawl_history.columns_added"})
SET c118.name = "columns_added", c118.data_type = "integer", c118.is_nullable = true, c118.ordinal_position = 9, c118.is_active = true;

MERGE (c119:Column {fqn: "tsdb.public.crawl_history.columns_updated"})
SET c119.name = "columns_updated", c119.data_type = "integer", c119.is_nullable = true, c119.ordinal_position = 10, c119.is_active = true;

MERGE (c120:Column {fqn: "tsdb.public.crawl_history.errors"})
SET c120.name = "errors", c120.data_type = "jsonb", c120.is_nullable = true, c120.ordinal_position = 11, c120.is_active = true;

MERGE (c121:Column {fqn: "tsdb.public.crawl_history.started_at"})
SET c121.name = "started_at", c121.data_type = "timestamp with time zone", c121.is_nullable = false, c121.ordinal_position = 12, c121.is_active = true;

MERGE (c122:Column {fqn: "tsdb.public.crawl_history.completed_at"})
SET c122.name = "completed_at", c122.data_type = "timestamp with time zone", c122.is_nullable = true, c122.ordinal_position = 13, c122.is_active = true;

MERGE (c123:Column {fqn: "tsdb.public.crawl_history.triggered_by"})
SET c123.name = "triggered_by", c123.data_type = "character varying", c123.is_nullable = false, c123.ordinal_position = 14, c123.is_active = true;

// Column-Table links (crawl_history)
MERGE (t11)-[:HAS_COLUMN]->(c110);
MERGE (t11)-[:HAS_COLUMN]->(c111);
MERGE (t11)-[:HAS_COLUMN]->(c112);
MERGE (t11)-[:HAS_COLUMN]->(c113);
MERGE (t11)-[:HAS_COLUMN]->(c114);
MERGE (t11)-[:HAS_COLUMN]->(c115);
MERGE (t11)-[:HAS_COLUMN]->(c116);
MERGE (t11)-[:HAS_COLUMN]->(c117);
MERGE (t11)-[:HAS_COLUMN]->(c118);
MERGE (t11)-[:HAS_COLUMN]->(c119);
MERGE (t11)-[:HAS_COLUMN]->(c120);
MERGE (t11)-[:HAS_COLUMN]->(c121);
MERGE (t11)-[:HAS_COLUMN]->(c122);
MERGE (t11)-[:HAS_COLUMN]->(c123);

// --- Columns (embedding_metadata) ---
MERGE (c124:Column {fqn: "tsdb.public.embedding_metadata.id"})
SET c124.name = "id", c124.data_type = "bigint", c124.is_pk = true, c124.is_nullable = false, c124.ordinal_position = 1, c124.is_active = true;

MERGE (c125:Column {fqn: "tsdb.public.embedding_metadata.entity_type"})
SET c125.name = "entity_type", c125.data_type = "character varying", c125.is_nullable = false, c125.ordinal_position = 2, c125.is_active = true;

MERGE (c126:Column {fqn: "tsdb.public.embedding_metadata.entity_fqn"})
SET c126.name = "entity_fqn", c126.data_type = "character varying", c126.is_nullable = false, c126.ordinal_position = 3, c126.is_active = true;

MERGE (c127:Column {fqn: "tsdb.public.embedding_metadata.model_name"})
SET c127.name = "model_name", c127.data_type = "character varying", c127.is_nullable = false, c127.ordinal_position = 4, c127.is_active = true;

MERGE (c128:Column {fqn: "tsdb.public.embedding_metadata.model_version"})
SET c128.name = "model_version", c128.data_type = "character varying", c128.is_nullable = false, c128.ordinal_position = 5, c128.is_active = true;

MERGE (c129:Column {fqn: "tsdb.public.embedding_metadata.source_text"})
SET c129.name = "source_text", c129.data_type = "text", c129.is_nullable = false, c129.ordinal_position = 6, c129.is_active = true;

MERGE (c130:Column {fqn: "tsdb.public.embedding_metadata.source_hash"})
SET c130.name = "source_hash", c130.data_type = "character varying", c130.is_nullable = false, c130.ordinal_position = 7, c130.is_active = true;

MERGE (c131:Column {fqn: "tsdb.public.embedding_metadata.embedding"})
SET c131.name = "embedding", c131.data_type = "USER-DEFINED", c131.is_nullable = true, c131.ordinal_position = 8, c131.is_active = true;

MERGE (c132:Column {fqn: "tsdb.public.embedding_metadata.created_at"})
SET c132.name = "created_at", c132.data_type = "timestamp with time zone", c132.is_nullable = false, c132.ordinal_position = 9, c132.is_active = true;

// Column-Table links (embedding_metadata)
MERGE (t12)-[:HAS_COLUMN]->(c124);
MERGE (t12)-[:HAS_COLUMN]->(c125);
MERGE (t12)-[:HAS_COLUMN]->(c126);
MERGE (t12)-[:HAS_COLUMN]->(c127);
MERGE (t12)-[:HAS_COLUMN]->(c128);
MERGE (t12)-[:HAS_COLUMN]->(c129);
MERGE (t12)-[:HAS_COLUMN]->(c130);
MERGE (t12)-[:HAS_COLUMN]->(c131);
MERGE (t12)-[:HAS_COLUMN]->(c132);

// --- Columns (graph_change_log) ---
MERGE (c133:Column {fqn: "tsdb.public.graph_change_log.id"})
SET c133.name = "id", c133.data_type = "bigint", c133.is_pk = true, c133.is_nullable = false, c133.ordinal_position = 1, c133.is_active = true;

MERGE (c134:Column {fqn: "tsdb.public.graph_change_log.graph_version"})
SET c134.name = "graph_version", c134.data_type = "bigint", c134.is_nullable = false, c134.ordinal_position = 2, c134.is_active = true;

MERGE (c135:Column {fqn: "tsdb.public.graph_change_log.node_type"})
SET c135.name = "node_type", c135.data_type = "character varying", c135.is_nullable = false, c135.ordinal_position = 3, c135.is_active = true;

MERGE (c136:Column {fqn: "tsdb.public.graph_change_log.node_id"})
SET c136.name = "node_id", c136.data_type = "character varying", c136.is_nullable = false, c136.ordinal_position = 4, c136.is_active = true;

MERGE (c137:Column {fqn: "tsdb.public.graph_change_log.action"})
SET c137.name = "action", c137.data_type = "character varying", c137.is_nullable = false, c137.ordinal_position = 5, c137.is_active = true;

MERGE (c138:Column {fqn: "tsdb.public.graph_change_log.changed_properties"})
SET c138.name = "changed_properties", c138.data_type = "jsonb", c138.is_nullable = true, c138.ordinal_position = 6, c138.is_active = true;

MERGE (c139:Column {fqn: "tsdb.public.graph_change_log.old_values"})
SET c139.name = "old_values", c139.data_type = "jsonb", c139.is_nullable = true, c139.ordinal_position = 7, c139.is_active = true;

MERGE (c140:Column {fqn: "tsdb.public.graph_change_log.new_values"})
SET c140.name = "new_values", c140.data_type = "jsonb", c140.is_nullable = true, c140.ordinal_position = 8, c140.is_active = true;

MERGE (c141:Column {fqn: "tsdb.public.graph_change_log.changed_by"})
SET c141.name = "changed_by", c141.data_type = "character varying", c141.is_nullable = false, c141.ordinal_position = 9, c141.is_active = true;

MERGE (c142:Column {fqn: "tsdb.public.graph_change_log.change_source"})
SET c142.name = "change_source", c142.data_type = "character varying", c142.is_nullable = false, c142.ordinal_position = 10, c142.is_active = true;

MERGE (c143:Column {fqn: "tsdb.public.graph_change_log.created_at"})
SET c143.name = "created_at", c143.data_type = "timestamp with time zone", c143.is_nullable = false, c143.ordinal_position = 11, c143.is_active = true;

// Column-Table links (graph_change_log)
MERGE (t13)-[:HAS_COLUMN]->(c133);
MERGE (t13)-[:HAS_COLUMN]->(c134);
MERGE (t13)-[:HAS_COLUMN]->(c135);
MERGE (t13)-[:HAS_COLUMN]->(c136);
MERGE (t13)-[:HAS_COLUMN]->(c137);
MERGE (t13)-[:HAS_COLUMN]->(c138);
MERGE (t13)-[:HAS_COLUMN]->(c139);
MERGE (t13)-[:HAS_COLUMN]->(c140);
MERGE (t13)-[:HAS_COLUMN]->(c141);
MERGE (t13)-[:HAS_COLUMN]->(c142);
MERGE (t13)-[:HAS_COLUMN]->(c143);

// --- Columns (graph_version) ---
MERGE (c144:Column {fqn: "tsdb.public.graph_version.id"})
SET c144.name = "id", c144.data_type = "integer", c144.is_pk = true, c144.is_nullable = false, c144.ordinal_position = 1, c144.is_active = true;

MERGE (c145:Column {fqn: "tsdb.public.graph_version.version"})
SET c145.name = "version", c145.data_type = "bigint", c145.is_nullable = false, c145.ordinal_position = 2, c145.is_active = true;

MERGE (c146:Column {fqn: "tsdb.public.graph_version.updated_at"})
SET c146.name = "updated_at", c146.data_type = "timestamp with time zone", c146.is_nullable = false, c146.ordinal_position = 3, c146.is_active = true;

MERGE (c147:Column {fqn: "tsdb.public.graph_version.updated_by"})
SET c147.name = "updated_by", c147.data_type = "character varying", c147.is_nullable = false, c147.ordinal_position = 4, c147.is_active = true;

MERGE (c148:Column {fqn: "tsdb.public.graph_version.description"})
SET c148.name = "description", c148.data_type = "text", c148.is_nullable = true, c148.ordinal_position = 5, c148.is_active = true;

// Column-Table links (graph_version)
MERGE (t14)-[:HAS_COLUMN]->(c144);
MERGE (t14)-[:HAS_COLUMN]->(c145);
MERGE (t14)-[:HAS_COLUMN]->(c146);
MERGE (t14)-[:HAS_COLUMN]->(c147);
MERGE (t14)-[:HAS_COLUMN]->(c148);

// --- Columns (policy_versions) ---
MERGE (c149:Column {fqn: "tsdb.public.policy_versions.id"})
SET c149.name = "id", c149.data_type = "bigint", c149.is_pk = true, c149.is_nullable = false, c149.ordinal_position = 1, c149.is_active = true;

MERGE (c150:Column {fqn: "tsdb.public.policy_versions.policy_id"})
SET c150.name = "policy_id", c150.data_type = "character varying", c150.is_nullable = false, c150.ordinal_position = 2, c150.is_active = true;

MERGE (c151:Column {fqn: "tsdb.public.policy_versions.version"})
SET c151.name = "version", c151.data_type = "integer", c151.is_nullable = false, c151.ordinal_position = 3, c151.is_active = true;

MERGE (c152:Column {fqn: "tsdb.public.policy_versions.policy_type"})
SET c152.name = "policy_type", c152.data_type = "character varying", c152.is_nullable = false, c152.ordinal_position = 4, c152.is_active = true;

MERGE (c153:Column {fqn: "tsdb.public.policy_versions.nl_description"})
SET c153.name = "nl_description", c153.data_type = "text", c153.is_nullable = false, c153.ordinal_position = 5, c153.is_active = true;

MERGE (c154:Column {fqn: "tsdb.public.policy_versions.structured_rule"})
SET c154.name = "structured_rule", c154.data_type = "jsonb", c154.is_nullable = false, c154.ordinal_position = 6, c154.is_active = true;

MERGE (c155:Column {fqn: "tsdb.public.policy_versions.priority"})
SET c155.name = "priority", c155.data_type = "integer", c155.is_nullable = false, c155.ordinal_position = 7, c155.is_active = true;

MERGE (c156:Column {fqn: "tsdb.public.policy_versions.is_active"})
SET c156.name = "is_active", c156.data_type = "boolean", c156.is_nullable = false, c156.ordinal_position = 8, c156.is_active = true;

MERGE (c157:Column {fqn: "tsdb.public.policy_versions.created_by"})
SET c157.name = "created_by", c157.data_type = "character varying", c157.is_nullable = false, c157.ordinal_position = 9, c157.is_active = true;

MERGE (c158:Column {fqn: "tsdb.public.policy_versions.created_at"})
SET c158.name = "created_at", c158.data_type = "timestamp with time zone", c158.is_nullable = false, c158.ordinal_position = 10, c158.is_active = true;

// Column-Table links (policy_versions)
MERGE (t15)-[:HAS_COLUMN]->(c149);
MERGE (t15)-[:HAS_COLUMN]->(c150);
MERGE (t15)-[:HAS_COLUMN]->(c151);
MERGE (t15)-[:HAS_COLUMN]->(c152);
MERGE (t15)-[:HAS_COLUMN]->(c153);
MERGE (t15)-[:HAS_COLUMN]->(c154);
MERGE (t15)-[:HAS_COLUMN]->(c155);
MERGE (t15)-[:HAS_COLUMN]->(c156);
MERGE (t15)-[:HAS_COLUMN]->(c157);
MERGE (t15)-[:HAS_COLUMN]->(c158);

// --- Domains ---
MERGE (dom_analytics:Domain {name: "analytics"});
MERGE (dom_audit:Domain {name: "audit"});
MERGE (dom_clinical:Domain {name: "clinical"});
MERGE (dom_general:Domain {name: "general"});
MERGE (dom_security:Domain {name: "security"});

// Domain-Table links
MERGE (t0)-[:BELONGS_TO_DOMAIN]->(dom_security);
MERGE (t1)-[:BELONGS_TO_DOMAIN]->(dom_general);
MERGE (t2)-[:BELONGS_TO_DOMAIN]->(dom_general);
MERGE (t3)-[:BELONGS_TO_DOMAIN]->(dom_general);
MERGE (t4)-[:BELONGS_TO_DOMAIN]->(dom_general);
MERGE (t5)-[:BELONGS_TO_DOMAIN]->(dom_general);
MERGE (t6)-[:BELONGS_TO_DOMAIN]->(dom_audit);
MERGE (t7)-[:BELONGS_TO_DOMAIN]->(dom_audit);
MERGE (t8)-[:BELONGS_TO_DOMAIN]->(dom_general);
MERGE (t9)-[:BELONGS_TO_DOMAIN]->(dom_general);
MERGE (t10)-[:BELONGS_TO_DOMAIN]->(dom_analytics);
MERGE (t11)-[:BELONGS_TO_DOMAIN]->(dom_general);
MERGE (t12)-[:BELONGS_TO_DOMAIN]->(dom_clinical);
MERGE (t13)-[:BELONGS_TO_DOMAIN]->(dom_audit);
MERGE (t14)-[:BELONGS_TO_DOMAIN]->(dom_audit);
MERGE (t15)-[:BELONGS_TO_DOMAIN]->(dom_audit);
