// ============================================================
// L2 Knowledge Graph — Seed Data (Apollo Hospitals Example)
// ============================================================

// --- Domains ---
MERGE (d1:Domain {name: "clinical"})
SET d1.description = "Clinical and patient care data",
    d1.created_at = datetime(), d1.version = 1;

MERGE (d2:Domain {name: "billing"})
SET d2.description = "Financial and billing data",
    d2.created_at = datetime(), d2.version = 1;

MERGE (d3:Domain {name: "pharmacy"})
SET d3.description = "Pharmacy and medication data",
    d3.created_at = datetime(), d3.version = 1;

MERGE (d4:Domain {name: "hr"})
SET d4.description = "Human resources and employee data",
    d4.created_at = datetime(), d4.version = 1;

MERGE (d5:Domain {name: "admin"})
SET d5.description = "Administrative and operational data",
    d5.created_at = datetime(), d5.version = 1;

MERGE (d6:Domain {name: "behavioral_health"})
SET d6.description = "Behavioral and mental health data — elevated protections",
    d6.created_at = datetime(), d6.version = 1;

// --- Regulations ---
MERGE (r1:Regulation {code: "HIPAA"})
SET r1.full_name = "Health Insurance Portability and Accountability Act",
    r1.description = "US federal law protecting health information privacy",
    r1.jurisdiction = "US", r1.version = 1;

MERGE (r2:Regulation {code: "42_CFR_PART_2"})
SET r2.full_name = "42 CFR Part 2 — Substance Use Disorder Records",
    r2.description = "Federal regulation with stricter protections than HIPAA for SUD records",
    r2.jurisdiction = "US", r2.version = 1;

MERGE (r3:Regulation {code: "HIPAA_PSYCHOTHERAPY"})
SET r3.full_name = "HIPAA Psychotherapy Notes Protection",
    r3.description = "Elevated HIPAA protections for psychotherapy notes",
    r3.jurisdiction = "US", r3.version = 1;

MERGE (r4:Regulation {code: "DPDPA_2023"})
SET r4.full_name = "Digital Personal Data Protection Act 2023",
    r4.description = "India's data protection legislation",
    r4.jurisdiction = "IN", r4.version = 1;

MERGE (r5:Regulation {code: "STATE_MH_LAWS"})
SET r5.full_name = "State Mental Health Laws",
    r5.description = "State-level mental health data protections",
    r5.jurisdiction = "US_STATE", r5.version = 1;

MERGE (r6:Regulation {code: "GINA"})
SET r6.full_name = "Genetic Information Nondiscrimination Act",
    r6.description = "Prohibits use of genetic information in employment/insurance",
    r6.jurisdiction = "US", r6.version = 1;

// --- Database ---
MERGE (db:Database {name: "apollo_emr"})
SET db.engine = "sqlserver", db.host = "emr-prod.apollo.internal",
    db.port = 1433, db.is_active = true,
    db.created_at = datetime(), db.version = 1;

// --- Schema ---
MERGE (s1:Schema {fqn: "apollo_emr.clinical"})
SET s1.name = "clinical", s1.is_active = true,
    s1.created_at = datetime(), s1.version = 1;

MERGE (s2:Schema {fqn: "apollo_emr.billing"})
SET s2.name = "billing", s2.is_active = true,
    s2.created_at = datetime(), s2.version = 1;

MERGE (s3:Schema {fqn: "apollo_emr.pharmacy"})
SET s3.name = "pharmacy", s3.is_active = true,
    s3.created_at = datetime(), s3.version = 1;

MERGE (s4:Schema {fqn: "apollo_emr.behavioral_health"})
SET s4.name = "behavioral_health", s4.is_active = true,
    s4.created_at = datetime(), s4.version = 1;

MERGE (db)-[:HAS_SCHEMA]->(s1);
MERGE (db)-[:HAS_SCHEMA]->(s2);
MERGE (db)-[:HAS_SCHEMA]->(s3);
MERGE (db)-[:HAS_SCHEMA]->(s4);

// --- Tables ---
MERGE (t1:Table {fqn: "apollo_emr.clinical.patients"})
SET t1.name = "patients", t1.description = "Core patient demographics and identifiers",
    t1.sensitivity_level = 4, t1.is_active = true, t1.row_count_approx = 2500000,
    t1.domain = "clinical", t1.created_at = datetime(), t1.version = 1;

MERGE (t2:Table {fqn: "apollo_emr.clinical.encounters"})
SET t2.name = "encounters", t2.description = "Patient visit and encounter records",
    t2.sensitivity_level = 3, t2.is_active = true, t2.row_count_approx = 18000000,
    t2.domain = "clinical", t2.created_at = datetime(), t2.version = 1;

MERGE (t3:Table {fqn: "apollo_emr.clinical.diagnoses"})
SET t3.name = "diagnoses", t3.description = "ICD-coded diagnosis records linked to encounters",
    t3.sensitivity_level = 4, t3.is_active = true, t3.row_count_approx = 45000000,
    t3.domain = "clinical", t3.created_at = datetime(), t3.version = 1;

MERGE (t4:Table {fqn: "apollo_emr.billing.claims"})
SET t4.name = "claims", t4.description = "Insurance claims and billing records",
    t4.sensitivity_level = 3, t4.is_active = true, t4.row_count_approx = 12000000,
    t4.domain = "billing", t4.created_at = datetime(), t4.version = 1;

MERGE (t5:Table {fqn: "apollo_emr.pharmacy.prescriptions"})
SET t5.name = "prescriptions", t5.description = "Medication prescriptions and dispensing records",
    t5.sensitivity_level = 4, t5.is_active = true, t5.row_count_approx = 30000000,
    t5.domain = "pharmacy", t5.created_at = datetime(), t5.version = 1;

// HARD DENY table — substance abuse records
MERGE (t6:Table {fqn: "apollo_emr.behavioral_health.substance_abuse_records"})
SET t6.name = "substance_abuse_records",
    t6.description = "Protected substance use disorder records — NO NL-to-SQL access permitted",
    t6.sensitivity_level = 5, t6.is_active = true, t6.hard_deny = true,
    t6.domain = "behavioral_health", t6.created_at = datetime(), t6.version = 1;

MERGE (t7:Table {fqn: "apollo_emr.clinical.therapy_notes"})
SET t7.name = "therapy_notes",
    t7.description = "Psychotherapy session notes — elevated HIPAA protection",
    t7.sensitivity_level = 5, t7.is_active = true,
    t7.domain = "behavioral_health", t7.created_at = datetime(), t7.version = 1;

// Link tables to schemas
MERGE (s1)-[:HAS_TABLE]->(t1);
MERGE (s1)-[:HAS_TABLE]->(t2);
MERGE (s1)-[:HAS_TABLE]->(t3);
MERGE (s2)-[:HAS_TABLE]->(t4);
MERGE (s3)-[:HAS_TABLE]->(t5);
MERGE (s4)-[:HAS_TABLE]->(t6);
MERGE (s4)-[:HAS_TABLE]->(t7);

// Link tables to domains
MERGE (t1)-[:BELONGS_TO_DOMAIN]->(d1);
MERGE (t2)-[:BELONGS_TO_DOMAIN]->(d1);
MERGE (t3)-[:BELONGS_TO_DOMAIN]->(d1);
MERGE (t4)-[:BELONGS_TO_DOMAIN]->(d2);
MERGE (t5)-[:BELONGS_TO_DOMAIN]->(d3);
MERGE (t6)-[:BELONGS_TO_DOMAIN]->(d6);
MERGE (t7)-[:BELONGS_TO_DOMAIN]->(d6);

// Regulatory links
MERGE (t1)-[:REGULATED_BY]->(r1);
MERGE (t1)-[:REGULATED_BY]->(r4);
MERGE (t3)-[:REGULATED_BY]->(r1);
MERGE (t5)-[:REGULATED_BY]->(r1);
MERGE (t6)-[:REGULATED_BY]->(r2);
MERGE (t7)-[:REGULATED_BY]->(r3);
MERGE (t7)-[:REGULATED_BY]->(r5);

// --- Columns (patients table) ---
MERGE (c1:Column {fqn: "apollo_emr.clinical.patients.patient_id"})
SET c1.name = "patient_id", c1.data_type = "int", c1.is_pk = true, c1.is_nullable = false,
    c1.sensitivity_level = 2, c1.is_pii = false,
    c1.description = "Unique patient identifier (surrogate key)",
    c1.is_active = true, c1.version = 1;

MERGE (c2:Column {fqn: "apollo_emr.clinical.patients.mrn"})
SET c2.name = "mrn", c2.data_type = "varchar(20)", c2.is_pk = false, c2.is_nullable = false,
    c2.sensitivity_level = 5, c2.is_pii = true,
    c2.pii_type = "MEDICAL_RECORD_NUMBER", c2.masking_strategy = "HASH",
    c2.description = "Medical record number — direct patient identifier",
    c2.is_active = true, c2.version = 1;

MERGE (c3:Column {fqn: "apollo_emr.clinical.patients.full_name"})
SET c3.name = "full_name", c3.data_type = "nvarchar(200)", c3.is_nullable = false,
    c3.sensitivity_level = 4, c3.is_pii = true,
    c3.pii_type = "FULL_NAME", c3.masking_strategy = "REDACT",
    c3.description = "Patient full legal name",
    c3.is_active = true, c3.version = 1;

MERGE (c4:Column {fqn: "apollo_emr.clinical.patients.dob"})
SET c4.name = "dob", c4.data_type = "date", c4.is_nullable = false,
    c4.sensitivity_level = 4, c4.is_pii = true,
    c4.pii_type = "DATE_OF_BIRTH", c4.masking_strategy = "GENERALIZE_YEAR",
    c4.description = "Patient date of birth",
    c4.is_active = true, c4.version = 1;

MERGE (c5:Column {fqn: "apollo_emr.clinical.patients.aadhaar_number"})
SET c5.name = "aadhaar_number", c5.data_type = "varchar(12)", c5.is_nullable = true,
    c5.sensitivity_level = 5, c5.is_pii = true,
    c5.pii_type = "NATIONAL_ID", c5.masking_strategy = "HASH",
    c5.description = "Aadhaar unique identification number",
    c5.is_active = true, c5.version = 1;

MERGE (c6:Column {fqn: "apollo_emr.clinical.patients.email"})
SET c6.name = "email", c6.data_type = "varchar(255)", c6.is_nullable = true,
    c6.sensitivity_level = 3, c6.is_pii = true,
    c6.pii_type = "EMAIL", c6.masking_strategy = "PARTIAL_MASK",
    c6.description = "Patient email address",
    c6.is_active = true, c6.version = 1;

MERGE (c7:Column {fqn: "apollo_emr.clinical.patients.phone"})
SET c7.name = "phone", c7.data_type = "varchar(15)", c7.is_nullable = true,
    c7.sensitivity_level = 3, c7.is_pii = true,
    c7.pii_type = "PHONE", c7.masking_strategy = "PARTIAL_MASK",
    c7.description = "Patient contact phone number",
    c7.is_active = true, c7.version = 1;

// Link columns to table
MERGE (t1)-[:HAS_COLUMN]->(c1);
MERGE (t1)-[:HAS_COLUMN]->(c2);
MERGE (t1)-[:HAS_COLUMN]->(c3);
MERGE (t1)-[:HAS_COLUMN]->(c4);
MERGE (t1)-[:HAS_COLUMN]->(c5);
MERGE (t1)-[:HAS_COLUMN]->(c6);
MERGE (t1)-[:HAS_COLUMN]->(c7);

// Regulatory links for columns
MERGE (c2)-[:COLUMN_REGULATED_BY]->(r1);
MERGE (c5)-[:COLUMN_REGULATED_BY]->(r4);

// --- Columns (encounters table) ---
MERGE (c10:Column {fqn: "apollo_emr.clinical.encounters.encounter_id"})
SET c10.name = "encounter_id", c10.data_type = "bigint", c10.is_pk = true,
    c10.sensitivity_level = 1, c10.is_pii = false,
    c10.description = "Unique encounter identifier",
    c10.is_active = true, c10.version = 1;

MERGE (c11:Column {fqn: "apollo_emr.clinical.encounters.patient_id"})
SET c11.name = "patient_id", c11.data_type = "int", c11.is_pk = false,
    c11.sensitivity_level = 2, c11.is_pii = false,
    c11.description = "Foreign key to patients table",
    c11.is_active = true, c11.version = 1;

MERGE (c12:Column {fqn: "apollo_emr.clinical.encounters.encounter_date"})
SET c12.name = "encounter_date", c12.data_type = "datetime", c12.is_nullable = false,
    c12.sensitivity_level = 2, c12.is_pii = false,
    c12.description = "Date and time of patient encounter",
    c12.is_active = true, c12.version = 1;

MERGE (t2)-[:HAS_COLUMN]->(c10);
MERGE (t2)-[:HAS_COLUMN]->(c11);
MERGE (t2)-[:HAS_COLUMN]->(c12);

// FK relationship
MERGE (c11)-[:FOREIGN_KEY_TO]->(c1);

// --- Roles ---
MERGE (r_admin:Role {name: "hospital_admin"})
SET r_admin.description = "Hospital administrator with broad data access",
    r_admin.is_active = true, r_admin.version = 1;

MERGE (r_doctor:Role {name: "doctor"})
SET r_doctor.description = "Attending physician — clinical data access",
    r_doctor.is_active = true, r_doctor.version = 1;

MERGE (r_nurse:Role {name: "nurse"})
SET r_nurse.description = "Nursing staff — limited clinical access",
    r_nurse.is_active = true, r_nurse.version = 1;

MERGE (r_billing:Role {name: "billing_staff"})
SET r_billing.description = "Billing department — financial data access",
    r_billing.is_active = true, r_billing.version = 1;

MERGE (r_researcher:Role {name: "researcher"})
SET r_researcher.description = "Clinical researcher — aggregated/de-identified access only",
    r_researcher.is_active = true, r_researcher.version = 1;

MERGE (r_pharmacist:Role {name: "pharmacist"})
SET r_pharmacist.description = "Pharmacy staff — medication data access",
    r_pharmacist.is_active = true, r_pharmacist.version = 1;

// Role hierarchy
MERGE (r_doctor)-[:INHERITS_FROM]->(r_nurse);
MERGE (r_admin)-[:INHERITS_FROM]->(r_doctor);

// Role-domain access
MERGE (r_doctor)-[:ACCESSES_DOMAIN]->(d1);
MERGE (r_doctor)-[:ACCESSES_DOMAIN]->(d3);
MERGE (r_nurse)-[:ACCESSES_DOMAIN]->(d1);
MERGE (r_billing)-[:ACCESSES_DOMAIN]->(d2);
MERGE (r_pharmacist)-[:ACCESSES_DOMAIN]->(d3);
MERGE (r_admin)-[:ACCESSES_DOMAIN]->(d1);
MERGE (r_admin)-[:ACCESSES_DOMAIN]->(d2);
MERGE (r_admin)-[:ACCESSES_DOMAIN]->(d3);
MERGE (r_admin)-[:ACCESSES_DOMAIN]->(d5);

// --- Policies ---

// P1: Doctors can access patient demographics
MERGE (p1:Policy {policy_id: "POL-001"})
SET p1.policy_type = "ALLOW",
    p1.nl_description = "Doctors may access patient demographic data for clinical care",
    p1.structured_rule = '{"effect":"ALLOW","target":{"table":"patients","columns":"*"},"subject":{"role":"doctor"},"condition":null}',
    p1.priority = 100, p1.is_active = true,
    p1.created_at = datetime(), p1.version = 1;
MERGE (p1)-[:APPLIES_TO_ROLE]->(r_doctor);
MERGE (p1)-[:GOVERNS_TABLE]->(t1);

// P2: Nurses see masked PII
MERGE (p2:Policy {policy_id: "POL-002"})
SET p2.policy_type = "MASK",
    p2.nl_description = "Nurses may access patient data but PII columns must be masked",
    p2.structured_rule = '{"effect":"MASK","target":{"table":"patients","columns":["mrn","full_name","aadhaar_number"]},"subject":{"role":"nurse"},"mask_strategy":"PARTIAL_MASK"}',
    p2.priority = 90, p2.is_active = true,
    p2.created_at = datetime(), p2.version = 1;
MERGE (p2)-[:APPLIES_TO_ROLE]->(r_nurse);
MERGE (p2)-[:GOVERNS_TABLE]->(t1);
MERGE (p2)-[:GOVERNS_COLUMN]->(c2);
MERGE (p2)-[:GOVERNS_COLUMN]->(c3);
MERGE (p2)-[:GOVERNS_COLUMN]->(c5);

// P3: Researchers get aggregation-only access
MERGE (p3:Policy {policy_id: "POL-003"})
SET p3.policy_type = "FILTER",
    p3.nl_description = "Researchers may only access aggregated, de-identified clinical data",
    p3.structured_rule = '{"effect":"FILTER","target":{"table":"*","domain":"clinical"},"subject":{"role":"researcher"},"conditions":["AGGREGATION_ONLY"]}',
    p3.priority = 80, p3.is_active = true,
    p3.created_at = datetime(), p3.version = 1;
MERGE (p3)-[:APPLIES_TO_ROLE]->(r_researcher);
MERGE (p3)-[:GOVERNS_DOMAIN]->(d1);

// Condition for P3
MERGE (cond1:Condition {condition_id: "COND-001"})
SET cond1.condition_type = "AGGREGATION_ONLY",
    cond1.parameters = '{"min_group_size":10}',
    cond1.description = "Results must be aggregated with minimum group size of 10";
MERGE (p3)-[:HAS_CONDITION]->(cond1);

// P4: HARD DENY on substance_abuse_records
MERGE (p4:Policy {policy_id: "POL-004"})
SET p4.policy_type = "DENY",
    p4.nl_description = "Substance abuse records are HARD DENIED from all NL-to-SQL access per 42 CFR Part 2",
    p4.structured_rule = '{"effect":"HARD_DENY","target":{"table":"substance_abuse_records"},"subject":{"role":"*"},"override_allowed":false}',
    p4.priority = 1000, p4.is_active = true, p4.is_hard_deny = true,
    p4.created_at = datetime(), p4.version = 1;
MERGE (p4)-[:GOVERNS_TABLE]->(t6);

// P5: Billing staff access limited to billing domain
MERGE (p5:Policy {policy_id: "POL-005"})
SET p5.policy_type = "ALLOW",
    p5.nl_description = "Billing staff may access claims and billing records",
    p5.structured_rule = '{"effect":"ALLOW","target":{"domain":"billing"},"subject":{"role":"billing_staff"}}',
    p5.priority = 100, p5.is_active = true,
    p5.created_at = datetime(), p5.version = 1;
MERGE (p5)-[:APPLIES_TO_ROLE]->(r_billing);
MERGE (p5)-[:GOVERNS_DOMAIN]->(d2);

// P6: Billing staff DENIED clinical joins
MERGE (p6:Policy {policy_id: "POL-006"})
SET p6.policy_type = "DENY",
    p6.nl_description = "Billing staff may not join billing data with clinical patient data",
    p6.structured_rule = '{"effect":"DENY","type":"JOIN_RESTRICTION","source_domain":"billing","target_domain":"clinical","subject":{"role":"billing_staff"}}',
    p6.priority = 200, p6.is_active = true,
    p6.created_at = datetime(), p6.version = 1;
MERGE (p6)-[:APPLIES_TO_ROLE]->(r_billing);
MERGE (cond2:Condition {condition_id: "COND-002"})
SET cond2.condition_type = "JOIN_RESTRICTION",
    cond2.parameters = '{"source_domain":"billing","target_domain":"clinical"}',
    cond2.description = "Prohibits cross-domain joins between billing and clinical";
MERGE (p6)-[:HAS_CONDITION]->(cond2);
MERGE (p6)-[:RESTRICTS_JOIN {source_domain: "billing", target_domain: "clinical"}]->(d1);

// P7: Time-windowed access for night-shift nurses
MERGE (p7:Policy {policy_id: "POL-007"})
SET p7.policy_type = "FILTER",
    p7.nl_description = "Night-shift nurses may only access encounter data from current shift window",
    p7.structured_rule = '{"effect":"FILTER","target":{"table":"encounters"},"subject":{"role":"nurse","shift":"night"},"conditions":["TIME_WINDOW"]}',
    p7.priority = 85, p7.is_active = true,
    p7.created_at = datetime(), p7.version = 1;
MERGE (p7)-[:APPLIES_TO_ROLE]->(r_nurse);
MERGE (p7)-[:GOVERNS_TABLE]->(t2);
MERGE (cond3:Condition {condition_id: "COND-003"})
SET cond3.condition_type = "TIME_WINDOW",
    cond3.parameters = '{"window_hours":12,"field":"encounter_date"}',
    cond3.description = "Restricts access to encounters within the current 12-hour shift";
MERGE (p7)-[:HAS_CONDITION]->(cond3);

// P8: Max rows for researcher queries
MERGE (p8:Policy {policy_id: "POL-008"})
SET p8.policy_type = "FILTER",
    p8.nl_description = "Researcher queries are limited to 1000 rows per result set",
    p8.structured_rule = '{"effect":"FILTER","target":{"domain":"clinical"},"subject":{"role":"researcher"},"conditions":["MAX_ROWS"]}',
    p8.priority = 75, p8.is_active = true,
    p8.created_at = datetime(), p8.version = 1;
MERGE (p8)-[:APPLIES_TO_ROLE]->(r_researcher);
MERGE (cond4:Condition {condition_id: "COND-004"})
SET cond4.condition_type = "MAX_ROWS",
    cond4.parameters = '{"limit":1000}',
    cond4.description = "Limits result set to maximum 1000 rows";
MERGE (p8)-[:HAS_CONDITION]->(cond4);

// P9: Therapy notes — DENY all except treating psychiatrist
MERGE (p9:Policy {policy_id: "POL-009"})
SET p9.policy_type = "DENY",
    p9.nl_description = "Therapy notes are denied to all roles via NL-to-SQL except treating provider with explicit authorization",
    p9.structured_rule = '{"effect":"DENY","target":{"table":"therapy_notes"},"subject":{"role":"*"},"exception":{"role":"treating_psychiatrist","requires":"explicit_authorization"}}',
    p9.priority = 900, p9.is_active = true,
    p9.created_at = datetime(), p9.version = 1;
MERGE (p9)-[:GOVERNS_TABLE]->(t7);
