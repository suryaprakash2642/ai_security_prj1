// ============================================================
// apollo_analytics — Analytics Database (PostgreSQL)
// ============================================================

// --- Database & Schema ---
MERGE (db_an:Database {name: "apollo_analytics"})
SET db_an.engine = "postgresql", db_an.host = "pg-analytics",
    db_an.port = 5432, db_an.is_active = true,
    db_an.created_at = datetime(), db_an.version = 1;

MERGE (s_an:Schema {fqn: "apollo_analytics.analytics"})
SET s_an.name = "analytics", s_an.is_active = true, s_an.created_at = datetime(), s_an.version = 1;
MERGE (s_rpt:Schema {fqn: "apollo_analytics.reports"})
SET s_rpt.name = "reports", s_rpt.is_active = true, s_rpt.created_at = datetime(), s_rpt.version = 1;

MERGE (db_an)-[:HAS_SCHEMA]->(s_an);
MERGE (db_an)-[:HAS_SCHEMA]->(s_rpt);

// --- Domain ---
MERGE (d_analytics:Domain {name: "analytics"})
SET d_analytics.description = "Analytics, KPIs, and reporting data", d_analytics.created_at = datetime(), d_analytics.version = 1;

// --- Regulations ---
MERGE (r_hipaa:Regulation {code: "HIPAA"});
MERGE (r_dpdpa:Regulation {code: "DPDPA_2023"});

// --- Tables ---
MERGE (ta1:Table {fqn: "apollo_analytics.analytics.patient_metrics"})
SET ta1.name = "patient_metrics", ta1.description = "Aggregated patient outcome metrics and scores",
    ta1.sensitivity_level = 3, ta1.is_active = true, ta1.row_count_approx = 3500000,
    ta1.domain = "analytics", ta1.created_at = datetime(), ta1.version = 1;

MERGE (ta2:Table {fqn: "apollo_analytics.analytics.readmission_scores"})
SET ta2.name = "readmission_scores", ta2.description = "30-day readmission risk prediction scores",
    ta2.sensitivity_level = 3, ta2.is_active = true, ta2.row_count_approx = 1800000,
    ta2.domain = "analytics", ta2.created_at = datetime(), ta2.version = 1;

MERGE (ta3:Table {fqn: "apollo_analytics.analytics.clinical_outcomes"})
SET ta3.name = "clinical_outcomes", ta3.description = "Clinical quality outcome measurements",
    ta3.sensitivity_level = 3, ta3.is_active = true, ta3.row_count_approx = 5200000,
    ta3.domain = "analytics", ta3.created_at = datetime(), ta3.version = 1;

MERGE (ta4:Table {fqn: "apollo_analytics.reports.department_kpis"})
SET ta4.name = "department_kpis", ta4.description = "Department-level KPI dashboards — occupancy, wait times",
    ta4.sensitivity_level = 2, ta4.is_active = true, ta4.row_count_approx = 450000,
    ta4.domain = "analytics", ta4.created_at = datetime(), ta4.version = 1;

MERGE (ta5:Table {fqn: "apollo_analytics.reports.revenue_analytics"})
SET ta5.name = "revenue_analytics", ta5.description = "Revenue and billing cycle analytics per department",
    ta5.sensitivity_level = 3, ta5.is_active = true, ta5.row_count_approx = 780000,
    ta5.domain = "analytics", ta5.created_at = datetime(), ta5.version = 1;

MERGE (ta6:Table {fqn: "apollo_analytics.reports.quality_measures"})
SET ta6.name = "quality_measures", ta6.description = "NABH/JCI quality compliance measures and scores",
    ta6.sensitivity_level = 2, ta6.is_active = true, ta6.row_count_approx = 120000,
    ta6.domain = "analytics", ta6.created_at = datetime(), ta6.version = 1;

MERGE (ta7:Table {fqn: "apollo_analytics.analytics.patient_satisfaction"})
SET ta7.name = "patient_satisfaction", ta7.description = "Patient satisfaction survey scores and feedback",
    ta7.sensitivity_level = 3, ta7.is_active = true, ta7.row_count_approx = 950000,
    ta7.domain = "analytics", ta7.created_at = datetime(), ta7.version = 1;

// Schema-Table links
MERGE (s_an)-[:HAS_TABLE]->(ta1);
MERGE (s_an)-[:HAS_TABLE]->(ta2);
MERGE (s_an)-[:HAS_TABLE]->(ta3);
MERGE (s_rpt)-[:HAS_TABLE]->(ta4);
MERGE (s_rpt)-[:HAS_TABLE]->(ta5);
MERGE (s_rpt)-[:HAS_TABLE]->(ta6);
MERGE (s_an)-[:HAS_TABLE]->(ta7);

// Domain links
MERGE (ta1)-[:BELONGS_TO_DOMAIN]->(d_analytics);
MERGE (ta2)-[:BELONGS_TO_DOMAIN]->(d_analytics);
MERGE (ta3)-[:BELONGS_TO_DOMAIN]->(d_analytics);
MERGE (ta4)-[:BELONGS_TO_DOMAIN]->(d_analytics);
MERGE (ta5)-[:BELONGS_TO_DOMAIN]->(d_analytics);
MERGE (ta6)-[:BELONGS_TO_DOMAIN]->(d_analytics);
MERGE (ta7)-[:BELONGS_TO_DOMAIN]->(d_analytics);

// Regulatory links (aggregated data still falls under HIPAA)
MERGE (ta1)-[:REGULATED_BY]->(r_hipaa);
MERGE (ta2)-[:REGULATED_BY]->(r_hipaa);
MERGE (ta7)-[:REGULATED_BY]->(r_dpdpa);

// --- Columns (patient_metrics) ---
MERGE (cam1:Column {fqn: "apollo_analytics.analytics.patient_metrics.metric_id"})
SET cam1.name = "metric_id", cam1.data_type = "bigint", cam1.is_pk = true, cam1.is_nullable = false,
    cam1.sensitivity_level = 1, cam1.is_pii = false, cam1.is_active = true, cam1.version = 1;

MERGE (cam2:Column {fqn: "apollo_analytics.analytics.patient_metrics.patient_id"})
SET cam2.name = "patient_id", cam2.data_type = "integer", cam2.is_nullable = false,
    cam2.sensitivity_level = 2, cam2.is_pii = false, cam2.is_active = true, cam2.version = 1;

MERGE (cam3:Column {fqn: "apollo_analytics.analytics.patient_metrics.los_days"})
SET cam3.name = "los_days", cam3.data_type = "integer", cam3.is_nullable = true,
    cam3.sensitivity_level = 2, cam3.is_pii = false,
    cam3.description = "Length of stay in days",
    cam3.is_active = true, cam3.version = 1;

MERGE (cam4:Column {fqn: "apollo_analytics.analytics.patient_metrics.risk_score"})
SET cam4.name = "risk_score", cam4.data_type = "decimal(5,2)", cam4.is_nullable = true,
    cam4.sensitivity_level = 3, cam4.is_pii = false,
    cam4.description = "Clinical risk score",
    cam4.is_active = true, cam4.version = 1;

MERGE (ta1)-[:HAS_COLUMN]->(cam1);
MERGE (ta1)-[:HAS_COLUMN]->(cam2);
MERGE (ta1)-[:HAS_COLUMN]->(cam3);
MERGE (ta1)-[:HAS_COLUMN]->(cam4);

// --- Analytics Roles ---
MERGE (r_analyst:Role {name: "data_analyst"})
SET r_analyst.description = "Data analyst — read-only access to analytics and reports",
    r_analyst.is_active = true, r_analyst.version = 1;

MERGE (r_quality:Role {name: "quality_officer"})
SET r_quality.description = "Quality officer — quality measures and compliance data",
    r_quality.is_active = true, r_quality.version = 1;

MERGE (r_analyst)-[:ACCESSES_DOMAIN]->(d_analytics);
MERGE (r_quality)-[:ACCESSES_DOMAIN]->(d_analytics);

// --- Analytics Policies ---
MERGE (p_an1:Policy {policy_id: "POL-AN-001"})
SET p_an1.policy_type = "FILTER",
    p_an1.nl_description = "Data analysts see only aggregated metrics — no patient-level drill-down",
    p_an1.structured_rule = '{"effect":"FILTER","target":{"domain":"analytics"},"subject":{"role":"data_analyst"},"conditions":["AGGREGATION_ONLY"]}',
    p_an1.priority = 80, p_an1.is_active = true, p_an1.created_at = datetime(), p_an1.version = 1;
MERGE (p_an1)-[:APPLIES_TO_ROLE]->(r_analyst);
MERGE (p_an1)-[:GOVERNS_DOMAIN]->(d_analytics);

MERGE (p_an2:Policy {policy_id: "POL-AN-002"})
SET p_an2.policy_type = "DENY",
    p_an2.nl_description = "Analytics domain cannot be joined to HR salary data",
    p_an2.structured_rule = '{"effect":"DENY","type":"JOIN_RESTRICTION","source_domain":"analytics","target_domain":"hr","subject":{"role":"*"}}',
    p_an2.priority = 200, p_an2.is_active = true, p_an2.created_at = datetime(), p_an2.version = 1;
MERGE (d_hr:Domain {name: "hr"});
MERGE (p_an2)-[:RESTRICTS_JOIN {source_domain: "analytics", target_domain: "hr"}]->(d_hr);
