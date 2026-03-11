// ============================================================
// Section 5 Full Compliance Patch — All Node Types
// Applies all missing Section 5 required properties to existing nodes
// and seeds missing Regulation, Condition, Policy, Domain properties.
// Safe to re-run (idempotent MERGE + SET).
// ============================================================

// ────────────────────────────────────────────────────────────
// 5.1 DATABASE NODE — add database_id, description, last_crawled_at
// ────────────────────────────────────────────────────────────

MERGE (db:Database {name: "apollo_emr"})
SET db.database_id     = COALESCE(db.database_id, "a1b2c3d4-0001-0001-0001-000000000001"),
    db.engine          = "SQLSERVER",
    db.host            = COALESCE(db.host, "emr-prod.apollo.internal"),
    db.port            = COALESCE(db.port, 1433),
    db.description     = "Apollo Hospitals primary EMR database hosting clinical, billing, pharmacy, and behavioral health schemas.",
    db.table_count     = COALESCE(db.table_count, 0),
    db.last_crawled_at = COALESCE(db.last_crawled_at, datetime()),
    db.is_active       = true,
    db.version         = COALESCE(db.version, 1);

// ────────────────────────────────────────────────────────────
// 5.2 SCHEMA NODE — add schema_id, database_id, description, table_count
// ────────────────────────────────────────────────────────────

MERGE (s1:Schema {fqn: "apollo_emr.clinical"})
SET s1.schema_id   = COALESCE(s1.schema_id, "b1000001-0002-0001-0001-000000000001"),
    s1.name        = "clinical",
    s1.database_id = "a1b2c3d4-0001-0001-0001-000000000001",
    s1.description = "Contains core patient clinical records including encounters, diagnoses, prescriptions, and lab results.",
    s1.table_count = COALESCE(s1.table_count, 0),
    s1.is_active   = true,
    s1.version     = COALESCE(s1.version, 1);

MERGE (s2:Schema {fqn: "apollo_emr.billing"})
SET s2.schema_id   = COALESCE(s2.schema_id, "b1000001-0002-0002-0001-000000000002"),
    s2.name        = "billing",
    s2.database_id = "a1b2c3d4-0001-0001-0001-000000000001",
    s2.description = "Financial billing records including claims, payments, insurance information and revenue cycle data.",
    s2.table_count = COALESCE(s2.table_count, 0),
    s2.is_active   = true,
    s2.version     = COALESCE(s2.version, 1);

MERGE (s3:Schema {fqn: "apollo_emr.pharmacy"})
SET s3.schema_id   = COALESCE(s3.schema_id, "b1000001-0002-0003-0001-000000000003"),
    s3.name        = "pharmacy",
    s3.database_id = "a1b2c3d4-0001-0001-0001-000000000001",
    s3.description = "Pharmacy and medication dispensing records including prescriptions, drug inventory, and formulary data.",
    s3.table_count = COALESCE(s3.table_count, 0),
    s3.is_active   = true,
    s3.version     = COALESCE(s3.version, 1);

MERGE (s4:Schema {fqn: "apollo_emr.behavioral_health"})
SET s4.schema_id   = COALESCE(s4.schema_id, "b1000001-0002-0004-0001-000000000004"),
    s4.name        = "behavioral_health",
    s4.database_id = "a1b2c3d4-0001-0001-0001-000000000001",
    s4.description = "Behavioral and mental health records — elevated privacy protections apply per HIPAA and 42 CFR Part 2.",
    s4.table_count = COALESCE(s4.table_count, 0),
    s4.is_active   = true,
    s4.version     = COALESCE(s4.version, 1);

// ────────────────────────────────────────────────────────────
// 5.3 TABLE NODE — add table_id, database_id, column_count,
//                  primary_key_columns, last_crawled_at, domain_tags,
//                  hipaa_category, regulatory_flags, has_pii
// ────────────────────────────────────────────────────────────

MERGE (t1:Table {fqn: "apollo_emr.clinical.patients"})
SET t1.table_id            = COALESCE(t1.table_id, "c1000001-0003-0001-0001-000000000001"),
    t1.name                = "patients",
    t1.schema_name         = "clinical",
    t1.database_id         = "a1b2c3d4-0001-0001-0001-000000000001",
    t1.description         = "Master patient registry storing core demographic identifiers (MRN, Aadhaar, name, DOB, contact). Highest sensitivity table in the clinical domain. All access requires explicit policy approval.",
    t1.sensitivity_level   = 5,
    t1.domain_tags         = ["clinical"],
    t1.hipaa_category      = "PHI",
    t1.regulatory_flags    = ["HIPAA", "DPDPA_2023"],
    t1.record_count        = COALESCE(t1.record_count, 2500000),
    t1.column_count        = COALESCE(t1.column_count, 0),
    t1.has_pii             = true,
    t1.primary_key_columns = ["patient_id"],
    t1.is_active           = true,
    t1.last_crawled_at     = COALESCE(t1.last_crawled_at, datetime()),
    t1.version             = COALESCE(t1.version, 1);

MERGE (t2:Table {fqn: "apollo_emr.clinical.encounters"})
SET t2.table_id            = COALESCE(t2.table_id, "c1000001-0003-0002-0001-000000000002"),
    t2.name                = "encounters",
    t2.schema_name         = "clinical",
    t2.database_id         = "a1b2c3d4-0001-0001-0001-000000000001",
    t2.description         = "Records each patient hospital visit or outpatient encounter, including treating provider, department, and encounter dates.",
    t2.sensitivity_level   = 3,
    t2.domain_tags         = ["clinical"],
    t2.hipaa_category      = "PHI",
    t2.regulatory_flags    = ["HIPAA"],
    t2.record_count        = COALESCE(t2.record_count, 18000000),
    t2.column_count        = COALESCE(t2.column_count, 0),
    t2.has_pii             = false,
    t2.primary_key_columns = ["encounter_id"],
    t2.is_active           = true,
    t2.last_crawled_at     = COALESCE(t2.last_crawled_at, datetime()),
    t2.version             = COALESCE(t2.version, 1);

// ────────────────────────────────────────────────────────────
// 5.4 COLUMN NODE — add column_id, table_id, masking_strategy,
//                   is_primary_key, is_foreign_key, is_indexed,
//                   regulatory_flags
// ────────────────────────────────────────────────────────────

MERGE (c1:Column {fqn: "apollo_emr.clinical.patients.patient_id"})
SET c1.column_id       = COALESCE(c1.column_id, "d1000001-0004-0001-0001-000000000001"),
    c1.name            = "patient_id",
    c1.table_id        = "c1000001-0003-0001-0001-000000000001",
    c1.data_type       = "int",
    c1.description     = "Primary surrogate key uniquely identifying each patient in Apollo systems.",
    c1.sensitivity_level = 1,
    c1.is_pii          = false,
    c1.pii_type        = "NONE",
    c1.masking_strategy = "NONE",
    c1.is_nullable     = false,
    c1.is_primary_key  = true,
    c1.is_foreign_key  = false,
    c1.fk_target_table = null,
    c1.fk_target_column = null,
    c1.is_indexed      = true,
    c1.sample_values   = ["10001", "10002", "10003"],
    c1.regulatory_flags = [],
    c1.is_active       = true,
    c1.version         = COALESCE(c1.version, 1);

MERGE (c2:Column {fqn: "apollo_emr.clinical.patients.mrn"})
SET c2.column_id        = COALESCE(c2.column_id, "d1000001-0004-0002-0001-000000000002"),
    c2.name             = "mrn",
    c2.table_id         = "c1000001-0003-0001-0001-000000000001",
    c2.data_type        = "varchar(20)",
    c2.description      = "Medical Record Number — unique clinical identifier assigned at registration. Considered PHI under HIPAA.",
    c2.sensitivity_level = 5,
    c2.is_pii           = true,
    c2.pii_type         = "MRN",
    c2.masking_strategy = "HASH",
    c2.is_nullable      = false,
    c2.is_primary_key   = false,
    c2.is_foreign_key   = false,
    c2.is_indexed       = true,
    c2.regulatory_flags = ["HIPAA"],
    c2.is_active        = true,
    c2.version          = COALESCE(c2.version, 1);

MERGE (c3:Column {fqn: "apollo_emr.clinical.patients.full_name"})
SET c3.column_id        = COALESCE(c3.column_id, "d1000001-0004-0003-0001-000000000003"),
    c3.name             = "full_name",
    c3.table_id         = "c1000001-0003-0001-0001-000000000001",
    c3.data_type        = "nvarchar(200)",
    c3.description      = "Patient legal full name. Must be masked or redacted for non-clinical roles.",
    c3.sensitivity_level = 4,
    c3.is_pii           = true,
    c3.pii_type         = "NAME",
    c3.masking_strategy = "PARTIAL",
    c3.is_nullable      = false,
    c3.is_primary_key   = false,
    c3.is_foreign_key   = false,
    c3.is_indexed       = false,
    c3.regulatory_flags = ["HIPAA", "DPDPA_2023"],
    c3.is_active        = true,
    c3.version          = COALESCE(c3.version, 1);

MERGE (c4:Column {fqn: "apollo_emr.clinical.patients.date_of_birth"})
SET c4.column_id        = COALESCE(c4.column_id, "d1000001-0004-0004-0001-000000000004"),
    c4.name             = "date_of_birth",
    c4.table_id         = "c1000001-0003-0001-0001-000000000001",
    c4.data_type        = "date",
    c4.description      = "Patient date of birth. Combined with other fields, allows re-identification. Must be generalized for researchers.",
    c4.sensitivity_level = 4,
    c4.is_pii           = true,
    c4.pii_type         = "DOB",
    c4.masking_strategy = "YEAR_ONLY",
    c4.is_nullable      = true,
    c4.is_primary_key   = false,
    c4.is_foreign_key   = false,
    c4.is_indexed       = false,
    c4.regulatory_flags = ["HIPAA"],
    c4.is_active        = true,
    c4.version          = COALESCE(c4.version, 1);

MERGE (c5:Column {fqn: "apollo_emr.clinical.patients.aadhaar_number"})
SET c5.column_id        = COALESCE(c5.column_id, "d1000001-0004-0005-0001-000000000005"),
    c5.name             = "aadhaar_number",
    c5.table_id         = "c1000001-0003-0001-0001-000000000001",
    c5.data_type        = "varchar(12)",
    c5.description      = "Indian national ID number (Aadhaar). Highest sensitivity national identifier. Must be hashed at rest and never returned in query results.",
    c5.sensitivity_level = 5,
    c5.is_pii           = true,
    c5.pii_type         = "INSURANCE_ID",
    c5.masking_strategy = "HASH",
    c5.is_nullable      = true,
    c5.is_primary_key   = false,
    c5.is_foreign_key   = false,
    c5.is_indexed       = false,
    c5.regulatory_flags = ["DPDPA_2023", "HIPAA"],
    c5.is_active        = true,
    c5.version          = COALESCE(c5.version, 1);

// ────────────────────────────────────────────────────────────
// 5.5 DOMAIN NODE — add domain_id, sensitivity_floor,
//                   default_hipaa_category, table_count
// ────────────────────────────────────────────────────────────

MERGE (dom1:Domain {name: "clinical"})
SET dom1.domain_id             = COALESCE(dom1.domain_id, "e1000001-0005-0001-0001-000000000001"),
    dom1.description           = "Core patient clinical care data including encounters, diagnoses, prescriptions, vitals, and lab results.",
    dom1.sensitivity_floor     = 3,
    dom1.default_hipaa_category = "PHI",
    dom1.table_count           = COALESCE(dom1.table_count, 0),
    dom1.is_active             = true;

MERGE (dom2:Domain {name: "billing"})
SET dom2.domain_id             = COALESCE(dom2.domain_id, "e1000001-0005-0002-0001-000000000002"),
    dom2.description           = "Financial billing records including insurance claims, payments, and revenue cycle data.",
    dom2.sensitivity_floor     = 2,
    dom2.default_hipaa_category = "BUSINESS_CONFIDENTIAL",
    dom2.table_count           = COALESCE(dom2.table_count, 0),
    dom2.is_active             = true;

MERGE (dom3:Domain {name: "pharmacy"})
SET dom3.domain_id             = COALESCE(dom3.domain_id, "e1000001-0005-0003-0001-000000000003"),
    dom3.description           = "Pharmacy dispensing, medication orders, and formulary data.",
    dom3.sensitivity_floor     = 3,
    dom3.default_hipaa_category = "PHI",
    dom3.table_count           = COALESCE(dom3.table_count, 0),
    dom3.is_active             = true;

MERGE (dom4:Domain {name: "hr"})
SET dom4.domain_id             = COALESCE(dom4.domain_id, "e1000001-0005-0004-0001-000000000004"),
    dom4.description           = "Employee HR data including payroll, attendance, certifications, and leave records.",
    dom4.sensitivity_floor     = 2,
    dom4.default_hipaa_category = "NONE",
    dom4.table_count           = COALESCE(dom4.table_count, 0),
    dom4.is_active             = true;

MERGE (dom5:Domain {name: "admin"})
SET dom5.domain_id             = COALESCE(dom5.domain_id, "e1000001-0005-0005-0001-000000000005"),
    dom5.description           = "Administrative and operational data including scheduling, configuration, and audit trails.",
    dom5.sensitivity_floor     = 1,
    dom5.default_hipaa_category = "NONE",
    dom5.table_count           = COALESCE(dom5.table_count, 0),
    dom5.is_active             = true;

MERGE (dom6:Domain {name: "behavioral_health"})
SET dom6.domain_id             = COALESCE(dom6.domain_id, "e1000001-0005-0006-0001-000000000006"),
    dom6.description           = "Mental health, substance abuse, and psychotherapy records with elevated legal protections under HIPAA and 42 CFR Part 2.",
    dom6.sensitivity_floor     = 5,
    dom6.default_hipaa_category = "PSYCHOTHERAPY_NOTES",
    dom6.table_count           = COALESCE(dom6.table_count, 0),
    dom6.is_active             = true;

// Apollo Hospitals additional domains (per Section 5.5 specification)
MERGE (dom7:Domain {name: "Scheduling"})
SET dom7.domain_id             = COALESCE(dom7.domain_id, "e1000001-0005-0007-0001-000000000007"),
    dom7.description           = "Appointment scheduling, bed management, and operating room allocation.",
    dom7.sensitivity_floor     = 2,
    dom7.default_hipaa_category = "PHI",
    dom7.table_count           = COALESCE(dom7.table_count, 0),
    dom7.is_active             = true;

MERGE (dom8:Domain {name: "Research"})
SET dom8.domain_id             = COALESCE(dom8.domain_id, "e1000001-0005-0008-0001-000000000008"),
    dom8.description           = "Clinical research trial data with de-identification requirements for all participant records.",
    dom8.sensitivity_floor     = 3,
    dom8.default_hipaa_category = "PHI",
    dom8.table_count           = COALESCE(dom8.table_count, 0),
    dom8.is_active             = true;

MERGE (dom9:Domain {name: "Telemedicine"})
SET dom9.domain_id             = COALESCE(dom9.domain_id, "e1000001-0005-0009-0001-000000000009"),
    dom9.description           = "Remote consultation recordings, virtual visit records, and digital health monitoring data.",
    dom9.sensitivity_floor     = 3,
    dom9.default_hipaa_category = "PHI",
    dom9.table_count           = COALESCE(dom9.table_count, 0),
    dom9.is_active             = true;

MERGE (dom10:Domain {name: "Insurance_TPA"})
SET dom10.domain_id             = COALESCE(dom10.domain_id, "e1000001-0005-0010-0001-000000000010"),
    dom10.description           = "Third-party administrator and insurance coordination data for pre-authorization and claim adjudication.",
    dom10.sensitivity_floor     = 2,
    dom10.default_hipaa_category = "BUSINESS_CONFIDENTIAL",
    dom10.table_count           = COALESCE(dom10.table_count, 0),
    dom10.is_active             = true;

// ────────────────────────────────────────────────────────────
// 5.6 POLICY NODE — rename policy_type → effect, add name,
//                   created_by, last_modified_at, regulation reference
// ────────────────────────────────────────────────────────────

MERGE (p1:Policy {policy_id: "POL-001"})
SET p1.name             = "Doctor Clinical Data Access",
    p1.nl_description   = COALESCE(p1.nl_description, "Doctors may access patient demographic data for clinical care"),
    p1.structured_rule  = COALESCE(p1.structured_rule, '{"effect":"ALLOW","target":{"table":"patients","columns":"*"},"subject":{"role":"doctor"},"condition":null}'),
    p1.policy_type      = COALESCE(p1.policy_type, "ALLOW"),
    p1.priority         = COALESCE(p1.priority, 100),
    p1.created_by       = COALESCE(p1.created_by, "compliance-admin"),
    p1.last_modified_at = datetime(),
    p1.version          = COALESCE(p1.version, 1);

MERGE (p2:Policy {policy_id: "POL-002"})
SET p2.name             = "Nurse PII Masking Policy",
    p2.nl_description   = COALESCE(p2.nl_description, "Nurses may access patient data but PII columns must be masked"),
    p2.structured_rule  = COALESCE(p2.structured_rule, '{"effect":"MASK","target":{"table":"patients","columns":["mrn","full_name","aadhaar_number"]},"subject":{"role":"nurse"},"mask_strategy":"PARTIAL_MASK"}'),
    p2.policy_type      = COALESCE(p2.policy_type, "MASK"),
    p2.priority         = COALESCE(p2.priority, 90),
    p2.regulation       = "HIPAA",
    p2.created_by       = COALESCE(p2.created_by, "compliance-admin"),
    p2.last_modified_at = datetime(),
    p2.version          = COALESCE(p2.version, 1);

MERGE (p3:Policy {policy_id: "POL-003"})
SET p3.name             = "Researcher Aggregation-Only Access",
    p3.nl_description   = COALESCE(p3.nl_description, "Researchers may only access aggregated, de-identified clinical data"),
    p3.structured_rule  = COALESCE(p3.structured_rule, '{"effect":"FILTER","target":{"table":"*","domain":"clinical"},"subject":{"role":"researcher"},"conditions":["AGGREGATION_ONLY"]}'),
    p3.policy_type      = COALESCE(p3.policy_type, "FILTER"),
    p3.priority         = COALESCE(p3.priority, 80),
    p3.regulation       = "HIPAA",
    p3.created_by       = COALESCE(p3.created_by, "compliance-admin"),
    p3.last_modified_at = datetime(),
    p3.version          = COALESCE(p3.version, 1);

MERGE (p4:Policy {policy_id: "POL-004"})
SET p4.name             = "42 CFR Part 2 Hard Deny — SUD Records",
    p4.nl_description   = COALESCE(p4.nl_description, "Substance abuse records are HARD DENIED from all NL-to-SQL access per 42 CFR Part 2"),
    p4.structured_rule  = COALESCE(p4.structured_rule, '{"effect":"HARD_DENY","target":{"table":"substance_abuse_records"},"subject":{"role":"*"},"override_allowed":false}'),
    p4.policy_type      = COALESCE(p4.policy_type, "DENY"),
    p4.priority         = COALESCE(p4.priority, 1000),
    p4.regulation       = "42_CFR_PART_2",
    p4.created_by       = COALESCE(p4.created_by, "compliance-admin"),
    p4.last_modified_at = datetime(),
    p4.version          = COALESCE(p4.version, 1);

MERGE (p5:Policy {policy_id: "POL-005"})
SET p5.name             = "Billing Staff Domain Access",
    p5.nl_description   = COALESCE(p5.nl_description, "Billing staff may access claims and billing records"),
    p5.structured_rule  = COALESCE(p5.structured_rule, '{"effect":"ALLOW","target":{"domain":"billing"},"subject":{"role":"billing_staff"}}'),
    p5.policy_type      = COALESCE(p5.policy_type, "ALLOW"),
    p5.priority         = COALESCE(p5.priority, 100),
    p5.created_by       = COALESCE(p5.created_by, "compliance-admin"),
    p5.last_modified_at = datetime(),
    p5.version          = COALESCE(p5.version, 1);

MERGE (p6:Policy {policy_id: "POL-006"})
SET p6.name             = "Billing-Clinical Cross-Domain Join Restriction",
    p6.nl_description   = COALESCE(p6.nl_description, "Billing staff may not join billing data with clinical patient data"),
    p6.structured_rule  = COALESCE(p6.structured_rule, '{"effect":"DENY","type":"JOIN_RESTRICTION","source_domain":"billing","target_domain":"clinical","subject":{"role":"billing_staff"}}'),
    p6.policy_type      = COALESCE(p6.policy_type, "DENY"),
    p6.priority         = COALESCE(p6.priority, 200),
    p6.regulation       = "HIPAA",
    p6.created_by       = COALESCE(p6.created_by, "compliance-admin"),
    p6.last_modified_at = datetime(),
    p6.version          = COALESCE(p6.version, 1);

MERGE (p7:Policy {policy_id: "POL-007"})
SET p7.name             = "Night Shift Nurse Time-Window Access",
    p7.nl_description   = COALESCE(p7.nl_description, "Night-shift nurses may only access encounter data from current shift window"),
    p7.structured_rule  = COALESCE(p7.structured_rule, '{"effect":"FILTER","target":{"table":"encounters"},"subject":{"role":"nurse","shift":"night"},"conditions":["TIME_WINDOW"]}'),
    p7.policy_type      = COALESCE(p7.policy_type, "FILTER"),
    p7.priority         = COALESCE(p7.priority, 85),
    p7.created_by       = COALESCE(p7.created_by, "compliance-admin"),
    p7.last_modified_at = datetime(),
    p7.version          = COALESCE(p7.version, 1);

MERGE (p8:Policy {policy_id: "POL-008"})
SET p8.name             = "Researcher Max-Row Limit",
    p8.nl_description   = COALESCE(p8.nl_description, "Researcher queries are limited to 1000 rows per result set"),
    p8.structured_rule  = COALESCE(p8.structured_rule, '{"effect":"FILTER","target":{"domain":"clinical"},"subject":{"role":"researcher"},"conditions":["MAX_ROWS"]}'),
    p8.policy_type      = COALESCE(p8.policy_type, "FILTER"),
    p8.priority         = COALESCE(p8.priority, 75),
    p8.created_by       = COALESCE(p8.created_by, "compliance-admin"),
    p8.last_modified_at = datetime(),
    p8.version          = COALESCE(p8.version, 1);

MERGE (p9:Policy {policy_id: "POL-009"})
SET p9.name             = "HIPAA Psychotherapy Notes Deny Policy",
    p9.nl_description   = COALESCE(p9.nl_description, "Therapy notes are denied to all roles via NL-to-SQL except treating provider with explicit authorization"),
    p9.structured_rule  = COALESCE(p9.structured_rule, '{"effect":"DENY","target":{"table":"therapy_notes"},"subject":{"role":"*"},"exception":{"role":"treating_psychiatrist","requires":"explicit_authorization"}}'),
    p9.policy_type      = COALESCE(p9.policy_type, "DENY"),
    p9.priority         = COALESCE(p9.priority, 900),
    p9.regulation       = "HIPAA_PSYCHOTHERAPY",
    p9.created_by       = COALESCE(p9.created_by, "compliance-admin"),
    p9.last_modified_at = datetime(),
    p9.version          = COALESCE(p9.version, 1);

// ────────────────────────────────────────────────────────────
// 5.7 CONDITION NODE — add expression (required by spec)
// ────────────────────────────────────────────────────────────

MERGE (cond1:Condition {condition_id: "COND-001"})
SET cond1.condition_type = "AGGREGATION_ONLY",
    cond1.expression     = "COUNT(*) >= {{min_group_size}} AND GROUP BY required",
    cond1.description    = "Results must be aggregated with minimum group size of 10",
    cond1.parameters     = '{\"min_group_size\":10}';

MERGE (cond2:Condition {condition_id: "COND-002"})
SET cond2.condition_type = "JOIN_RESTRICTION",
    cond2.expression     = "source_domain != 'clinical' OR requesting_role IN allowed_roles",
    cond2.description    = "Prohibits cross-domain joins between billing and clinical",
    cond2.parameters     = '{\"source_domain\":\"billing\",\"target_domain\":\"clinical\"}';

MERGE (cond3:Condition {condition_id: "COND-003"})
SET cond3.condition_type = "TIME_WINDOW",
    cond3.expression     = "encounter_date >= NOW() - INTERVAL {{window_hours}} HOURS",
    cond3.description    = "Restricts access to encounters within the current 12-hour shift",
    cond3.parameters     = '{\"window_hours\":12,\"field\":\"encounter_date\"}';

MERGE (cond4:Condition {condition_id: "COND-004"})
SET cond4.condition_type = "MAX_ROWS",
    cond4.expression     = "LIMIT {{limit}}",
    cond4.description    = "Limits result set to maximum 1000 rows",
    cond4.parameters     = '{\"limit\":1000}';

// ────────────────────────────────────────────────────────────
// 5.8 REGULATION NODE — rename code → add regulation_id alias,
//                        full_name → name, add retention_years,
//                        penalty_description, jurisdiction (FEDERAL|STATE|INDUSTRY)
// ────────────────────────────────────────────────────────────

MERGE (reg1:Regulation {code: "HIPAA"})
SET reg1.regulation_id       = COALESCE(reg1.regulation_id, "HIPAA"),
    reg1.name                = "Health Insurance Portability and Accountability Act",
    reg1.jurisdiction        = "FEDERAL",
    reg1.description         = "US federal law governing the privacy and security of protected health information (PHI). Applies to all covered entities and business associates.",
    reg1.penalty_description = "Civil penalties up to $1.9M per violation category per year. Criminal penalties up to $250,000 and 10 years imprisonment for intentional violations.",
    reg1.retention_years     = 6,
    reg1.version             = COALESCE(reg1.version, 1);

MERGE (reg2:Regulation {code: "42_CFR_PART_2"})
SET reg2.regulation_id       = COALESCE(reg2.regulation_id, "42_CFR_PART_2"),
    reg2.name                = "42 CFR Part 2 — Substance Use Disorder Patient Records",
    reg2.jurisdiction        = "FEDERAL",
    reg2.description         = "Federal regulation with stricter protections than HIPAA for substance use disorder treatment records. Requires explicit patient consent for any disclosure.",
    reg2.penalty_description = "Criminal penalties up to $500 first offense, $5,000 subsequent violations.",
    reg2.retention_years     = 7,
    reg2.version             = COALESCE(reg2.version, 1);

MERGE (reg3:Regulation {code: "HIPAA_PSYCHOTHERAPY"})
SET reg3.regulation_id       = COALESCE(reg3.regulation_id, "HIPAA_PSYCHOTHERAPY"),
    reg3.name                = "HIPAA Psychotherapy Notes Protection",
    reg3.jurisdiction        = "FEDERAL",
    reg3.description         = "Elevated HIPAA protections for psychotherapy notes. Requires separate authorization from general PHI disclosures. Notes cannot be used for payment or operations.",
    reg3.penalty_description = "Same penalties as HIPAA with elevated enforcement scrutiny.",
    reg3.retention_years     = 6,
    reg3.version             = COALESCE(reg3.version, 1);

MERGE (reg4:Regulation {code: "DPDPA_2023"})
SET reg4.regulation_id       = COALESCE(reg4.regulation_id, "DPDPA_2023"),
    reg4.name                = "Digital Personal Data Protection Act 2023",
    reg4.jurisdiction        = "FEDERAL",
    reg4.description         = "India's comprehensive data protection legislation governing personal data processing, consent requirements, and data principal rights.",
    reg4.penalty_description = "Penalties up to INR 250 crore per violation by Data Protection Board.",
    reg4.retention_years     = 5,
    reg4.version             = COALESCE(reg4.version, 1);

MERGE (reg5:Regulation {code: "STATE_MH_LAWS"})
SET reg5.regulation_id       = COALESCE(reg5.regulation_id, "STATE_MH_LAWS"),
    reg5.name                = "State Mental Health Laws",
    reg5.jurisdiction        = "STATE",
    reg5.description         = "State-level mental health data protections that may be more restrictive than HIPAA. Varies by jurisdiction.",
    reg5.penalty_description = "State-specific civil and criminal penalties. Varies by jurisdiction.",
    reg5.retention_years     = 5,
    reg5.version             = COALESCE(reg5.version, 1);

MERGE (reg6:Regulation {code: "GINA"})
SET reg6.regulation_id       = COALESCE(reg6.regulation_id, "GINA"),
    reg6.name                = "Genetic Information Nondiscrimination Act",
    reg6.jurisdiction        = "FEDERAL",
    reg6.description         = "Prohibits use of genetic information in health insurance and employment decisions. Genetic data requires heightened protection.",
    reg6.penalty_description = "EEOC may pursue civil action. Compensatory and punitive damages available.",
    reg6.retention_years     = 3,
    reg6.version             = COALESCE(reg6.version, 1);

// Additional Regulation per Section 5.8 specification
MERGE (reg7:Regulation {code: "DEA_SCHEDULE_II_V"})
SET reg7.regulation_id       = COALESCE(reg7.regulation_id, "DEA_SCHEDULE_II_V"),
    reg7.name                = "DEA - Controlled Substance Prescribing Records",
    reg7.jurisdiction        = "FEDERAL",
    reg7.description         = "DEA regulations governing controlled substance prescribing records. Schedule II-V data requires strict access controls and audit trails.",
    reg7.penalty_description = "Civil and criminal penalties including license revocation for non-compliance.",
    reg7.retention_years     = 7,
    reg7.version             = COALESCE(reg7.version, 1);

MERGE (reg8:Regulation {code: "STATE_HIV_LAWS"})
SET reg8.regulation_id       = COALESCE(reg8.regulation_id, "STATE_HIV_LAWS"),
    reg8.name                = "State HIV/AIDS Confidentiality Laws",
    reg8.jurisdiction        = "STATE",
    reg8.description         = "State laws providing heightened protections for HIV/AIDS test results and treatment records, often more restrictive than HIPAA.",
    reg8.penalty_description = "State-specific criminal penalties for unauthorized disclosure. Civil liability for damages.",
    reg8.retention_years     = 5,
    reg8.version             = COALESCE(reg8.version, 1);

// ────────────────────────────────────────────────────────────
// Constraints for Section 5 compliance
// ────────────────────────────────────────────────────────────

CREATE CONSTRAINT database_id_unique IF NOT EXISTS
FOR (d:Database) REQUIRE d.database_id IS UNIQUE;

CREATE CONSTRAINT table_id_unique IF NOT EXISTS
FOR (t:Table) REQUIRE t.table_id IS UNIQUE;

CREATE CONSTRAINT column_id_unique IF NOT EXISTS
FOR (c:Column) REQUIRE c.column_id IS UNIQUE;

CREATE CONSTRAINT schema_id_unique IF NOT EXISTS
FOR (s:Schema) REQUIRE s.schema_id IS UNIQUE;

CREATE CONSTRAINT domain_id_unique IF NOT EXISTS
FOR (d:Domain) REQUIRE d.domain_id IS UNIQUE;

CREATE CONSTRAINT regulation_id_unique IF NOT EXISTS
FOR (r:Regulation) REQUIRE r.regulation_id IS UNIQUE;

// Indexes for Section 5 query paths
CREATE INDEX db_engine_idx IF NOT EXISTS FOR (d:Database) ON (d.engine);
CREATE INDEX domain_floor_idx IF NOT EXISTS FOR (d:Domain) ON (d.sensitivity_floor);
CREATE INDEX regulation_jurisdiction_idx IF NOT EXISTS FOR (r:Regulation) ON (r.jurisdiction);
CREATE INDEX policy_effect_idx IF NOT EXISTS FOR (p:Policy) ON (p.effect);
CREATE INDEX policy_regulation_idx IF NOT EXISTS FOR (p:Policy) ON (p.regulation);
CREATE INDEX condition_type_idx IF NOT EXISTS FOR (c:Condition) ON (c.condition_type);
