// ============================================================
// apollo_analytics — Analytics & Reporting Database (AWS RDS PostgreSQL)
// Auto-generated from live crawl at 2026-03-03 19:28:09
// ============================================================

// --- Database ---
MERGE (db:Database {name: "apollo_analytics"})
SET db.engine = "postgresql", db.is_active = true,
    db.created_at = datetime(), db.source = "live_crawl";

// --- Schemas ---
MERGE (s0:Schema {fqn: "apollo_analytics.public"})
SET s0.name = "public", s0.is_active = true;

MERGE (db)-[:HAS_SCHEMA]->(s0);

// --- Tables ---
MERGE (t0:Table {fqn: "apollo_analytics.public.encounter_summaries"})
SET t0.name = "encounter_summaries", t0.is_active = true,
    t0.row_count_approx = 2304,
    t0.sensitivity_level = 3, t0.has_pii = true,
    t0.domain = "clinical", t0.source = "live_crawl";

MERGE (t1:Table {fqn: "apollo_analytics.public.population_health"})
SET t1.name = "population_health", t1.is_active = true,
    t1.row_count_approx = 960,
    t1.sensitivity_level = 3, t1.has_pii = true,
    t1.domain = "general", t1.source = "live_crawl";

MERGE (t2:Table {fqn: "apollo_analytics.public.quality_metrics"})
SET t2.name = "quality_metrics", t2.is_active = true,
    t2.row_count_approx = 1344,
    t2.sensitivity_level = 0, t2.has_pii = false,
    t2.domain = "analytics", t2.source = "live_crawl";

MERGE (t3:Table {fqn: "apollo_analytics.public.research_cohorts"})
SET t3.name = "research_cohorts", t3.is_active = true,
    t3.row_count_approx = 0,
    t3.sensitivity_level = 0, t3.has_pii = false,
    t3.domain = "general", t3.source = "live_crawl";

MERGE (t4:Table {fqn: "apollo_analytics.public.table_embeddings"})
SET t4.name = "table_embeddings", t4.is_active = true,
    t4.row_count_approx = 0,
    t4.sensitivity_level = 0, t4.has_pii = false,
    t4.domain = "clinical", t4.source = "live_crawl";

// Schema-Table links
MERGE (s0)-[:HAS_TABLE]->(t0);
MERGE (s0)-[:HAS_TABLE]->(t1);
MERGE (s0)-[:HAS_TABLE]->(t2);
MERGE (s0)-[:HAS_TABLE]->(t3);
MERGE (s0)-[:HAS_TABLE]->(t4);

// --- Columns (encounter_summaries) ---
MERGE (c0:Column {fqn: "apollo_analytics.public.encounter_summaries.summary_id"})
SET c0.name = "summary_id", c0.data_type = "uuid", c0.is_pk = true, c0.is_nullable = false, c0.ordinal_position = 1, c0.sensitivity_level = 3, c0.is_pii = true, c0.pii_type = "CLINICAL_CONTEXT", c0.masking_strategy = "REVIEW", c0.is_active = true;

MERGE (c1:Column {fqn: "apollo_analytics.public.encounter_summaries.facility_id"})
SET c1.name = "facility_id", c1.data_type = "character varying", c1.is_nullable = false, c1.ordinal_position = 2, c1.sensitivity_level = 3, c1.is_pii = true, c1.pii_type = "CLINICAL_CONTEXT", c1.masking_strategy = "REVIEW", c1.is_active = true;

MERGE (c2:Column {fqn: "apollo_analytics.public.encounter_summaries.facility_name"})
SET c2.name = "facility_name", c2.data_type = "character varying", c2.is_nullable = true, c2.ordinal_position = 3, c2.sensitivity_level = 3, c2.is_pii = true, c2.pii_type = "CLINICAL_CONTEXT", c2.masking_strategy = "REVIEW", c2.is_active = true;

MERGE (c3:Column {fqn: "apollo_analytics.public.encounter_summaries.department_id"})
SET c3.name = "department_id", c3.data_type = "character varying", c3.is_nullable = true, c3.ordinal_position = 4, c3.sensitivity_level = 3, c3.is_pii = true, c3.pii_type = "CLINICAL_CONTEXT", c3.masking_strategy = "REVIEW", c3.is_active = true;

MERGE (c4:Column {fqn: "apollo_analytics.public.encounter_summaries.department_name"})
SET c4.name = "department_name", c4.data_type = "character varying", c4.is_nullable = true, c4.ordinal_position = 5, c4.sensitivity_level = 3, c4.is_pii = true, c4.pii_type = "CLINICAL_CONTEXT", c4.masking_strategy = "REVIEW", c4.is_active = true;

MERGE (c5:Column {fqn: "apollo_analytics.public.encounter_summaries.report_month"})
SET c5.name = "report_month", c5.data_type = "date", c5.is_nullable = false, c5.ordinal_position = 6, c5.sensitivity_level = 3, c5.is_pii = true, c5.pii_type = "CLINICAL_CONTEXT", c5.masking_strategy = "REVIEW", c5.is_active = true;

MERGE (c6:Column {fqn: "apollo_analytics.public.encounter_summaries.encounter_type"})
SET c6.name = "encounter_type", c6.data_type = "character varying", c6.is_nullable = true, c6.ordinal_position = 7, c6.sensitivity_level = 3, c6.is_pii = true, c6.pii_type = "CLINICAL_CONTEXT", c6.masking_strategy = "REVIEW", c6.is_active = true;

MERGE (c7:Column {fqn: "apollo_analytics.public.encounter_summaries.total_encounters"})
SET c7.name = "total_encounters", c7.data_type = "integer", c7.is_nullable = false, c7.ordinal_position = 8, c7.sensitivity_level = 3, c7.is_pii = true, c7.pii_type = "CLINICAL_CONTEXT", c7.masking_strategy = "REVIEW", c7.is_active = true;

MERGE (c8:Column {fqn: "apollo_analytics.public.encounter_summaries.total_admissions"})
SET c8.name = "total_admissions", c8.data_type = "integer", c8.is_nullable = true, c8.ordinal_position = 9, c8.sensitivity_level = 3, c8.is_pii = true, c8.pii_type = "CLINICAL_CONTEXT", c8.masking_strategy = "REVIEW", c8.is_active = true;

MERGE (c9:Column {fqn: "apollo_analytics.public.encounter_summaries.total_discharges"})
SET c9.name = "total_discharges", c9.data_type = "integer", c9.is_nullable = true, c9.ordinal_position = 10, c9.sensitivity_level = 3, c9.is_pii = true, c9.pii_type = "CLINICAL_CONTEXT", c9.masking_strategy = "REVIEW", c9.is_active = true;

MERGE (c10:Column {fqn: "apollo_analytics.public.encounter_summaries.avg_length_of_stay"})
SET c10.name = "avg_length_of_stay", c10.data_type = "numeric", c10.is_nullable = true, c10.ordinal_position = 11, c10.sensitivity_level = 3, c10.is_pii = true, c10.pii_type = "CLINICAL_CONTEXT", c10.masking_strategy = "REVIEW", c10.is_active = true;

MERGE (c11:Column {fqn: "apollo_analytics.public.encounter_summaries.readmission_count"})
SET c11.name = "readmission_count", c11.data_type = "integer", c11.is_nullable = true, c11.ordinal_position = 12, c11.sensitivity_level = 3, c11.is_pii = true, c11.pii_type = "CLINICAL_CONTEXT", c11.masking_strategy = "REVIEW", c11.is_active = true;

MERGE (c12:Column {fqn: "apollo_analytics.public.encounter_summaries.readmission_rate"})
SET c12.name = "readmission_rate", c12.data_type = "numeric", c12.is_nullable = true, c12.ordinal_position = 13, c12.sensitivity_level = 3, c12.is_pii = true, c12.pii_type = "CLINICAL_CONTEXT", c12.masking_strategy = "REVIEW", c12.is_active = true;

MERGE (c13:Column {fqn: "apollo_analytics.public.encounter_summaries.total_revenue"})
SET c13.name = "total_revenue", c13.data_type = "numeric", c13.is_nullable = true, c13.ordinal_position = 14, c13.sensitivity_level = 3, c13.is_pii = true, c13.pii_type = "CLINICAL_CONTEXT", c13.masking_strategy = "REVIEW", c13.is_active = true;

MERGE (c14:Column {fqn: "apollo_analytics.public.encounter_summaries.avg_revenue_per_encounter"})
SET c14.name = "avg_revenue_per_encounter", c14.data_type = "numeric", c14.is_nullable = true, c14.ordinal_position = 15, c14.sensitivity_level = 3, c14.is_pii = true, c14.pii_type = "CLINICAL_CONTEXT", c14.masking_strategy = "REVIEW", c14.is_active = true;

MERGE (c15:Column {fqn: "apollo_analytics.public.encounter_summaries.bed_occupancy_rate"})
SET c15.name = "bed_occupancy_rate", c15.data_type = "numeric", c15.is_nullable = true, c15.ordinal_position = 16, c15.sensitivity_level = 3, c15.is_pii = true, c15.pii_type = "CLINICAL_CONTEXT", c15.masking_strategy = "REVIEW", c15.is_active = true;

MERGE (c16:Column {fqn: "apollo_analytics.public.encounter_summaries.mortality_count"})
SET c16.name = "mortality_count", c16.data_type = "integer", c16.is_nullable = true, c16.ordinal_position = 17, c16.sensitivity_level = 3, c16.is_pii = true, c16.pii_type = "CLINICAL_CONTEXT", c16.masking_strategy = "REVIEW", c16.is_active = true;

MERGE (c17:Column {fqn: "apollo_analytics.public.encounter_summaries.mortality_rate"})
SET c17.name = "mortality_rate", c17.data_type = "numeric", c17.is_nullable = true, c17.ordinal_position = 18, c17.sensitivity_level = 3, c17.is_pii = true, c17.pii_type = "CLINICAL_CONTEXT", c17.masking_strategy = "REVIEW", c17.is_active = true;

MERGE (c18:Column {fqn: "apollo_analytics.public.encounter_summaries.created_at"})
SET c18.name = "created_at", c18.data_type = "timestamp without time zone", c18.is_nullable = true, c18.ordinal_position = 19, c18.sensitivity_level = 3, c18.is_pii = true, c18.pii_type = "CLINICAL_CONTEXT", c18.masking_strategy = "REVIEW", c18.is_active = true;

// Column-Table links (encounter_summaries)
MERGE (t0)-[:HAS_COLUMN]->(c0);
MERGE (t0)-[:HAS_COLUMN]->(c1);
MERGE (t0)-[:HAS_COLUMN]->(c2);
MERGE (t0)-[:HAS_COLUMN]->(c3);
MERGE (t0)-[:HAS_COLUMN]->(c4);
MERGE (t0)-[:HAS_COLUMN]->(c5);
MERGE (t0)-[:HAS_COLUMN]->(c6);
MERGE (t0)-[:HAS_COLUMN]->(c7);
MERGE (t0)-[:HAS_COLUMN]->(c8);
MERGE (t0)-[:HAS_COLUMN]->(c9);
MERGE (t0)-[:HAS_COLUMN]->(c10);
MERGE (t0)-[:HAS_COLUMN]->(c11);
MERGE (t0)-[:HAS_COLUMN]->(c12);
MERGE (t0)-[:HAS_COLUMN]->(c13);
MERGE (t0)-[:HAS_COLUMN]->(c14);
MERGE (t0)-[:HAS_COLUMN]->(c15);
MERGE (t0)-[:HAS_COLUMN]->(c16);
MERGE (t0)-[:HAS_COLUMN]->(c17);
MERGE (t0)-[:HAS_COLUMN]->(c18);

// --- Columns (population_health) ---
MERGE (c19:Column {fqn: "apollo_analytics.public.population_health.record_id"})
SET c19.name = "record_id", c19.data_type = "uuid", c19.is_pk = true, c19.is_nullable = false, c19.ordinal_position = 1, c19.is_active = true;

MERGE (c20:Column {fqn: "apollo_analytics.public.population_health.facility_id"})
SET c20.name = "facility_id", c20.data_type = "character varying", c20.is_nullable = false, c20.ordinal_position = 2, c20.is_active = true;

MERGE (c21:Column {fqn: "apollo_analytics.public.population_health.report_quarter"})
SET c21.name = "report_quarter", c21.data_type = "date", c21.is_nullable = false, c21.ordinal_position = 3, c21.is_active = true;

MERGE (c22:Column {fqn: "apollo_analytics.public.population_health.age_group"})
SET c22.name = "age_group", c22.data_type = "character varying", c22.is_nullable = true, c22.ordinal_position = 4, c22.is_active = true;

MERGE (c23:Column {fqn: "apollo_analytics.public.population_health.gender"})
SET c23.name = "gender", c23.data_type = "character varying", c23.is_nullable = true, c23.ordinal_position = 5, c23.sensitivity_level = 3, c23.is_pii = true, c23.pii_type = "DEMOGRAPHIC", c23.masking_strategy = "GENERALIZE", c23.is_active = true;

MERGE (c24:Column {fqn: "apollo_analytics.public.population_health.disease_category"})
SET c24.name = "disease_category", c24.data_type = "character varying", c24.is_nullable = true, c24.ordinal_position = 6, c24.is_active = true;

MERGE (c25:Column {fqn: "apollo_analytics.public.population_health.icd_chapter"})
SET c25.name = "icd_chapter", c25.data_type = "character varying", c25.is_nullable = true, c25.ordinal_position = 7, c25.is_active = true;

MERGE (c26:Column {fqn: "apollo_analytics.public.population_health.patient_count"})
SET c26.name = "patient_count", c26.data_type = "integer", c26.is_nullable = true, c26.ordinal_position = 8, c26.is_active = true;

MERGE (c27:Column {fqn: "apollo_analytics.public.population_health.encounter_count"})
SET c27.name = "encounter_count", c27.data_type = "integer", c27.is_nullable = true, c27.ordinal_position = 9, c27.is_active = true;

MERGE (c28:Column {fqn: "apollo_analytics.public.population_health.avg_cost"})
SET c28.name = "avg_cost", c28.data_type = "numeric", c28.is_nullable = true, c28.ordinal_position = 10, c28.is_active = true;

MERGE (c29:Column {fqn: "apollo_analytics.public.population_health.avg_los"})
SET c29.name = "avg_los", c29.data_type = "numeric", c29.is_nullable = true, c29.ordinal_position = 11, c29.is_active = true;

MERGE (c30:Column {fqn: "apollo_analytics.public.population_health.complication_rate"})
SET c30.name = "complication_rate", c30.data_type = "numeric", c30.is_nullable = true, c30.ordinal_position = 12, c30.is_active = true;

MERGE (c31:Column {fqn: "apollo_analytics.public.population_health.created_at"})
SET c31.name = "created_at", c31.data_type = "timestamp without time zone", c31.is_nullable = true, c31.ordinal_position = 13, c31.is_active = true;

// Column-Table links (population_health)
MERGE (t1)-[:HAS_COLUMN]->(c19);
MERGE (t1)-[:HAS_COLUMN]->(c20);
MERGE (t1)-[:HAS_COLUMN]->(c21);
MERGE (t1)-[:HAS_COLUMN]->(c22);
MERGE (t1)-[:HAS_COLUMN]->(c23);
MERGE (t1)-[:HAS_COLUMN]->(c24);
MERGE (t1)-[:HAS_COLUMN]->(c25);
MERGE (t1)-[:HAS_COLUMN]->(c26);
MERGE (t1)-[:HAS_COLUMN]->(c27);
MERGE (t1)-[:HAS_COLUMN]->(c28);
MERGE (t1)-[:HAS_COLUMN]->(c29);
MERGE (t1)-[:HAS_COLUMN]->(c30);
MERGE (t1)-[:HAS_COLUMN]->(c31);

// --- Columns (quality_metrics) ---
MERGE (c32:Column {fqn: "apollo_analytics.public.quality_metrics.metric_id"})
SET c32.name = "metric_id", c32.data_type = "uuid", c32.is_pk = true, c32.is_nullable = false, c32.ordinal_position = 1, c32.is_active = true;

MERGE (c33:Column {fqn: "apollo_analytics.public.quality_metrics.facility_id"})
SET c33.name = "facility_id", c33.data_type = "character varying", c33.is_nullable = false, c33.ordinal_position = 2, c33.is_active = true;

MERGE (c34:Column {fqn: "apollo_analytics.public.quality_metrics.department_id"})
SET c34.name = "department_id", c34.data_type = "character varying", c34.is_nullable = true, c34.ordinal_position = 3, c34.is_active = true;

MERGE (c35:Column {fqn: "apollo_analytics.public.quality_metrics.metric_name"})
SET c35.name = "metric_name", c35.data_type = "character varying", c35.is_nullable = false, c35.ordinal_position = 4, c35.is_active = true;

MERGE (c36:Column {fqn: "apollo_analytics.public.quality_metrics.metric_category"})
SET c36.name = "metric_category", c36.data_type = "character varying", c36.is_nullable = true, c36.ordinal_position = 5, c36.is_active = true;

MERGE (c37:Column {fqn: "apollo_analytics.public.quality_metrics.report_month"})
SET c37.name = "report_month", c37.data_type = "date", c37.is_nullable = false, c37.ordinal_position = 6, c37.is_active = true;

MERGE (c38:Column {fqn: "apollo_analytics.public.quality_metrics.numerator"})
SET c38.name = "numerator", c38.data_type = "integer", c38.is_nullable = true, c38.ordinal_position = 7, c38.is_active = true;

MERGE (c39:Column {fqn: "apollo_analytics.public.quality_metrics.denominator"})
SET c39.name = "denominator", c39.data_type = "integer", c39.is_nullable = true, c39.ordinal_position = 8, c39.is_active = true;

MERGE (c40:Column {fqn: "apollo_analytics.public.quality_metrics.metric_value"})
SET c40.name = "metric_value", c40.data_type = "numeric", c40.is_nullable = true, c40.ordinal_position = 9, c40.is_active = true;

MERGE (c41:Column {fqn: "apollo_analytics.public.quality_metrics.target_value"})
SET c41.name = "target_value", c41.data_type = "numeric", c41.is_nullable = true, c41.ordinal_position = 10, c41.is_active = true;

MERGE (c42:Column {fqn: "apollo_analytics.public.quality_metrics.benchmark_value"})
SET c42.name = "benchmark_value", c42.data_type = "numeric", c42.is_nullable = true, c42.ordinal_position = 11, c42.is_active = true;

MERGE (c43:Column {fqn: "apollo_analytics.public.quality_metrics.performance_status"})
SET c43.name = "performance_status", c43.data_type = "character varying", c43.is_nullable = true, c43.ordinal_position = 12, c43.is_active = true;

MERGE (c44:Column {fqn: "apollo_analytics.public.quality_metrics.created_at"})
SET c44.name = "created_at", c44.data_type = "timestamp without time zone", c44.is_nullable = true, c44.ordinal_position = 13, c44.is_active = true;

// Column-Table links (quality_metrics)
MERGE (t2)-[:HAS_COLUMN]->(c32);
MERGE (t2)-[:HAS_COLUMN]->(c33);
MERGE (t2)-[:HAS_COLUMN]->(c34);
MERGE (t2)-[:HAS_COLUMN]->(c35);
MERGE (t2)-[:HAS_COLUMN]->(c36);
MERGE (t2)-[:HAS_COLUMN]->(c37);
MERGE (t2)-[:HAS_COLUMN]->(c38);
MERGE (t2)-[:HAS_COLUMN]->(c39);
MERGE (t2)-[:HAS_COLUMN]->(c40);
MERGE (t2)-[:HAS_COLUMN]->(c41);
MERGE (t2)-[:HAS_COLUMN]->(c42);
MERGE (t2)-[:HAS_COLUMN]->(c43);
MERGE (t2)-[:HAS_COLUMN]->(c44);

// --- Columns (research_cohorts) ---
MERGE (c45:Column {fqn: "apollo_analytics.public.research_cohorts.cohort_id"})
SET c45.name = "cohort_id", c45.data_type = "uuid", c45.is_pk = true, c45.is_nullable = false, c45.ordinal_position = 1, c45.is_active = true;

MERGE (c46:Column {fqn: "apollo_analytics.public.research_cohorts.cohort_name"})
SET c46.name = "cohort_name", c46.data_type = "character varying", c46.is_nullable = false, c46.ordinal_position = 2, c46.is_active = true;

MERGE (c47:Column {fqn: "apollo_analytics.public.research_cohorts.study_id"})
SET c47.name = "study_id", c47.data_type = "character varying", c47.is_nullable = true, c47.ordinal_position = 3, c47.is_active = true;

MERGE (c48:Column {fqn: "apollo_analytics.public.research_cohorts.principal_investigator"})
SET c48.name = "principal_investigator", c48.data_type = "character varying", c48.is_nullable = true, c48.ordinal_position = 4, c48.is_active = true;

MERGE (c49:Column {fqn: "apollo_analytics.public.research_cohorts.department_id"})
SET c49.name = "department_id", c49.data_type = "character varying", c49.is_nullable = true, c49.ordinal_position = 5, c49.is_active = true;

MERGE (c50:Column {fqn: "apollo_analytics.public.research_cohorts.inclusion_criteria"})
SET c50.name = "inclusion_criteria", c50.data_type = "text", c50.is_nullable = true, c50.ordinal_position = 6, c50.is_active = true;

MERGE (c51:Column {fqn: "apollo_analytics.public.research_cohorts.exclusion_criteria"})
SET c51.name = "exclusion_criteria", c51.data_type = "text", c51.is_nullable = true, c51.ordinal_position = 7, c51.is_active = true;

MERGE (c52:Column {fqn: "apollo_analytics.public.research_cohorts.patient_count"})
SET c52.name = "patient_count", c52.data_type = "integer", c52.is_nullable = true, c52.ordinal_position = 8, c52.is_active = true;

MERGE (c53:Column {fqn: "apollo_analytics.public.research_cohorts.enrollment_start"})
SET c53.name = "enrollment_start", c53.data_type = "date", c53.is_nullable = true, c53.ordinal_position = 9, c53.is_active = true;

MERGE (c54:Column {fqn: "apollo_analytics.public.research_cohorts.enrollment_end"})
SET c54.name = "enrollment_end", c54.data_type = "date", c54.is_nullable = true, c54.ordinal_position = 10, c54.is_active = true;

MERGE (c55:Column {fqn: "apollo_analytics.public.research_cohorts.status"})
SET c55.name = "status", c55.data_type = "character varying", c55.is_nullable = true, c55.ordinal_position = 11, c55.is_active = true;

MERGE (c56:Column {fqn: "apollo_analytics.public.research_cohorts.irb_approval_number"})
SET c56.name = "irb_approval_number", c56.data_type = "character varying", c56.is_nullable = true, c56.ordinal_position = 12, c56.is_active = true;

MERGE (c57:Column {fqn: "apollo_analytics.public.research_cohorts.created_at"})
SET c57.name = "created_at", c57.data_type = "timestamp without time zone", c57.is_nullable = true, c57.ordinal_position = 13, c57.is_active = true;

// Column-Table links (research_cohorts)
MERGE (t3)-[:HAS_COLUMN]->(c45);
MERGE (t3)-[:HAS_COLUMN]->(c46);
MERGE (t3)-[:HAS_COLUMN]->(c47);
MERGE (t3)-[:HAS_COLUMN]->(c48);
MERGE (t3)-[:HAS_COLUMN]->(c49);
MERGE (t3)-[:HAS_COLUMN]->(c50);
MERGE (t3)-[:HAS_COLUMN]->(c51);
MERGE (t3)-[:HAS_COLUMN]->(c52);
MERGE (t3)-[:HAS_COLUMN]->(c53);
MERGE (t3)-[:HAS_COLUMN]->(c54);
MERGE (t3)-[:HAS_COLUMN]->(c55);
MERGE (t3)-[:HAS_COLUMN]->(c56);
MERGE (t3)-[:HAS_COLUMN]->(c57);

// --- Columns (table_embeddings) ---
MERGE (c58:Column {fqn: "apollo_analytics.public.table_embeddings.fqn"})
SET c58.name = "fqn", c58.data_type = "text", c58.is_pk = true, c58.is_nullable = false, c58.ordinal_position = 1, c58.is_active = true;

MERGE (c59:Column {fqn: "apollo_analytics.public.table_embeddings.description_hash"})
SET c59.name = "description_hash", c59.data_type = "text", c59.is_nullable = false, c59.ordinal_position = 2, c59.is_active = true;

MERGE (c60:Column {fqn: "apollo_analytics.public.table_embeddings.embedding"})
SET c60.name = "embedding", c60.data_type = "USER-DEFINED", c60.is_nullable = false, c60.ordinal_position = 3, c60.is_active = true;

MERGE (c61:Column {fqn: "apollo_analytics.public.table_embeddings.description"})
SET c61.name = "description", c61.data_type = "text", c61.is_nullable = true, c61.ordinal_position = 4, c61.is_active = true;

MERGE (c62:Column {fqn: "apollo_analytics.public.table_embeddings.updated_at"})
SET c62.name = "updated_at", c62.data_type = "timestamp with time zone", c62.is_nullable = true, c62.ordinal_position = 5, c62.is_active = true;

// Column-Table links (table_embeddings)
MERGE (t4)-[:HAS_COLUMN]->(c58);
MERGE (t4)-[:HAS_COLUMN]->(c59);
MERGE (t4)-[:HAS_COLUMN]->(c60);
MERGE (t4)-[:HAS_COLUMN]->(c61);
MERGE (t4)-[:HAS_COLUMN]->(c62);

// --- Domains ---
MERGE (dom_analytics:Domain {name: "analytics"});
MERGE (dom_clinical:Domain {name: "clinical"});
MERGE (dom_general:Domain {name: "general"});

// Domain-Table links
MERGE (t0)-[:BELONGS_TO_DOMAIN]->(dom_clinical);
MERGE (t1)-[:BELONGS_TO_DOMAIN]->(dom_general);
MERGE (t2)-[:BELONGS_TO_DOMAIN]->(dom_analytics);
MERGE (t3)-[:BELONGS_TO_DOMAIN]->(dom_general);
MERGE (t4)-[:BELONGS_TO_DOMAIN]->(dom_clinical);
