// ============================================================
// ApolloHIS — Hospital Information System (SQL Server)
// ============================================================

// --- Database & Schemas ---
MERGE (db_his:Database {name: "ApolloHIS"})
SET db_his.engine = "sqlserver", db_his.host = "sql-server-his",
    db_his.port = 1433, db_his.is_active = true,
    db_his.created_at = datetime(), db_his.version = 1;

MERGE (s_clin:Schema {fqn: "ApolloHIS.clinical"})
SET s_clin.name = "clinical", s_clin.is_active = true, s_clin.created_at = datetime(), s_clin.version = 1;
MERGE (s_lab:Schema {fqn: "ApolloHIS.laboratory"})
SET s_lab.name = "laboratory", s_lab.is_active = true, s_lab.created_at = datetime(), s_lab.version = 1;
MERGE (s_rad:Schema {fqn: "ApolloHIS.radiology"})
SET s_rad.name = "radiology", s_rad.is_active = true, s_rad.created_at = datetime(), s_rad.version = 1;
MERGE (s_nurs:Schema {fqn: "ApolloHIS.nursing"})
SET s_nurs.name = "nursing", s_nurs.is_active = true, s_nurs.created_at = datetime(), s_nurs.version = 1;

MERGE (db_his)-[:HAS_SCHEMA]->(s_clin);
MERGE (db_his)-[:HAS_SCHEMA]->(s_lab);
MERGE (db_his)-[:HAS_SCHEMA]->(s_rad);
MERGE (db_his)-[:HAS_SCHEMA]->(s_nurs);

// --- Domain references ---
MERGE (d_clinical:Domain {name: "clinical"});
MERGE (d_lab:Domain {name: "lab"});
MERGE (d_radiology:Domain {name: "radiology"});
MERGE (d_nursing:Domain {name: "nursing"});
MERGE (d_bhav:Domain {name: "behavioral_health"});

// Create new domains
MERGE (d_radiology)
SET d_radiology.description = "Radiology and imaging data", d_radiology.created_at = datetime(), d_radiology.version = 1;
MERGE (d_nursing)
SET d_nursing.description = "Nursing assessments and vital signs", d_nursing.created_at = datetime(), d_nursing.version = 1;

// --- Regulations ---
MERGE (r_hipaa:Regulation {code: "HIPAA"});
MERGE (r_dpdpa:Regulation {code: "DPDPA_2023"});

// --- Tables ---
MERGE (th1:Table {fqn: "ApolloHIS.clinical.patient_registry"})
SET th1.name = "patient_registry", th1.description = "Master patient index with demographics and identifiers",
    th1.sensitivity_level = 5, th1.is_active = true, th1.row_count_approx = 3500000,
    th1.domain = "clinical", th1.created_at = datetime(), th1.version = 1;

MERGE (th2:Table {fqn: "ApolloHIS.clinical.admissions"})
SET th2.name = "admissions", th2.description = "Inpatient admissions, transfers, and discharge records",
    th2.sensitivity_level = 3, th2.is_active = true, th2.row_count_approx = 8500000,
    th2.domain = "clinical", th2.created_at = datetime(), th2.version = 1;

MERGE (th3:Table {fqn: "ApolloHIS.clinical.procedures"})
SET th3.name = "procedures", th3.description = "Medical and surgical procedures performed",
    th3.sensitivity_level = 4, th3.is_active = true, th3.row_count_approx = 12000000,
    th3.domain = "clinical", th3.created_at = datetime(), th3.version = 1;

MERGE (th4:Table {fqn: "ApolloHIS.clinical.allergies"})
SET th4.name = "allergies", th4.description = "Patient allergy records — critical for safety",
    th4.sensitivity_level = 3, th4.is_active = true, th4.row_count_approx = 4200000,
    th4.domain = "clinical", th4.created_at = datetime(), th4.version = 1;

MERGE (th5:Table {fqn: "ApolloHIS.clinical.immunizations"})
SET th5.name = "immunizations", th5.description = "Vaccination and immunization history",
    th5.sensitivity_level = 3, th5.is_active = true, th5.row_count_approx = 6800000,
    th5.domain = "clinical", th5.created_at = datetime(), th5.version = 1;

MERGE (th6:Table {fqn: "ApolloHIS.laboratory.lab_results"})
SET th6.name = "lab_results", th6.description = "Laboratory test results — CBC, metabolic panels, etc.",
    th6.sensitivity_level = 4, th6.is_active = true, th6.row_count_approx = 52000000,
    th6.domain = "lab", th6.created_at = datetime(), th6.version = 1;

MERGE (th7:Table {fqn: "ApolloHIS.laboratory.lab_orders"})
SET th7.name = "lab_orders", th7.description = "Laboratory test orders by physicians",
    th7.sensitivity_level = 3, th7.is_active = true, th7.row_count_approx = 25000000,
    th7.domain = "lab", th7.created_at = datetime(), th7.version = 1;

MERGE (th8:Table {fqn: "ApolloHIS.radiology.imaging_orders"})
SET th8.name = "imaging_orders", th8.description = "Radiology imaging orders — X-ray, CT, MRI",
    th8.sensitivity_level = 3, th8.is_active = true, th8.row_count_approx = 9500000,
    th8.domain = "radiology", th8.created_at = datetime(), th8.version = 1;

MERGE (th9:Table {fqn: "ApolloHIS.radiology.imaging_reports"})
SET th9.name = "imaging_reports", th9.description = "Radiologist diagnostic reports and findings",
    th9.sensitivity_level = 4, th9.is_active = true, th9.row_count_approx = 9500000,
    th9.domain = "radiology", th9.created_at = datetime(), th9.version = 1;

MERGE (th10:Table {fqn: "ApolloHIS.nursing.vital_signs"})
SET th10.name = "vital_signs", th10.description = "Patient vital sign measurements — BP, HR, SpO2, temp",
    th10.sensitivity_level = 3, th10.is_active = true, th10.row_count_approx = 85000000,
    th10.domain = "nursing", th10.created_at = datetime(), th10.version = 1;

MERGE (th11:Table {fqn: "ApolloHIS.nursing.nursing_assessments"})
SET th11.name = "nursing_assessments", th11.description = "Nursing clinical assessments and care plans",
    th11.sensitivity_level = 3, th11.is_active = true, th11.row_count_approx = 16000000,
    th11.domain = "nursing", th11.created_at = datetime(), th11.version = 1;

MERGE (th12:Table {fqn: "ApolloHIS.clinical.operating_room_schedules"})
SET th12.name = "operating_room_schedules", th12.description = "OR scheduling and surgical case assignments",
    th12.sensitivity_level = 3, th12.is_active = true, th12.row_count_approx = 1200000,
    th12.domain = "clinical", th12.created_at = datetime(), th12.version = 1;

// Schema-Table links
MERGE (s_clin)-[:HAS_TABLE]->(th1);
MERGE (s_clin)-[:HAS_TABLE]->(th2);
MERGE (s_clin)-[:HAS_TABLE]->(th3);
MERGE (s_clin)-[:HAS_TABLE]->(th4);
MERGE (s_clin)-[:HAS_TABLE]->(th5);
MERGE (s_lab)-[:HAS_TABLE]->(th6);
MERGE (s_lab)-[:HAS_TABLE]->(th7);
MERGE (s_rad)-[:HAS_TABLE]->(th8);
MERGE (s_rad)-[:HAS_TABLE]->(th9);
MERGE (s_nurs)-[:HAS_TABLE]->(th10);
MERGE (s_nurs)-[:HAS_TABLE]->(th11);
MERGE (s_clin)-[:HAS_TABLE]->(th12);

// Domain links
MERGE (th1)-[:BELONGS_TO_DOMAIN]->(d_clinical);
MERGE (th2)-[:BELONGS_TO_DOMAIN]->(d_clinical);
MERGE (th3)-[:BELONGS_TO_DOMAIN]->(d_clinical);
MERGE (th4)-[:BELONGS_TO_DOMAIN]->(d_clinical);
MERGE (th5)-[:BELONGS_TO_DOMAIN]->(d_clinical);
MERGE (th6)-[:BELONGS_TO_DOMAIN]->(d_lab);
MERGE (th7)-[:BELONGS_TO_DOMAIN]->(d_lab);
MERGE (th8)-[:BELONGS_TO_DOMAIN]->(d_radiology);
MERGE (th9)-[:BELONGS_TO_DOMAIN]->(d_radiology);
MERGE (th10)-[:BELONGS_TO_DOMAIN]->(d_nursing);
MERGE (th11)-[:BELONGS_TO_DOMAIN]->(d_nursing);
MERGE (th12)-[:BELONGS_TO_DOMAIN]->(d_clinical);

// Regulatory links
MERGE (th1)-[:REGULATED_BY]->(r_hipaa);
MERGE (th1)-[:REGULATED_BY]->(r_dpdpa);
MERGE (th3)-[:REGULATED_BY]->(r_hipaa);
MERGE (th6)-[:REGULATED_BY]->(r_hipaa);

// --- Key Columns (patient_registry) ---
MERGE (ch1:Column {fqn: "ApolloHIS.clinical.patient_registry.patient_id"})
SET ch1.name = "patient_id", ch1.data_type = "int", ch1.is_pk = true, ch1.is_nullable = false,
    ch1.sensitivity_level = 2, ch1.is_pii = false, ch1.is_active = true, ch1.version = 1;

MERGE (ch2:Column {fqn: "ApolloHIS.clinical.patient_registry.uhid"})
SET ch2.name = "uhid", ch2.data_type = "varchar(20)", ch2.is_nullable = false,
    ch2.sensitivity_level = 5, ch2.is_pii = true, ch2.pii_type = "MEDICAL_RECORD_NUMBER",
    ch2.masking_strategy = "HASH", ch2.description = "Unique Hospital ID — direct patient identifier",
    ch2.is_active = true, ch2.version = 1;

MERGE (ch3:Column {fqn: "ApolloHIS.clinical.patient_registry.patient_name"})
SET ch3.name = "patient_name", ch3.data_type = "nvarchar(200)", ch3.is_nullable = false,
    ch3.sensitivity_level = 4, ch3.is_pii = true, ch3.pii_type = "FULL_NAME",
    ch3.masking_strategy = "REDACT", ch3.is_active = true, ch3.version = 1;

MERGE (ch4:Column {fqn: "ApolloHIS.clinical.patient_registry.gender"})
SET ch4.name = "gender", ch4.data_type = "char(1)", ch4.is_nullable = false,
    ch4.sensitivity_level = 2, ch4.is_pii = true, ch4.pii_type = "GENDER",
    ch4.masking_strategy = "GENERALIZE", ch4.is_active = true, ch4.version = 1;

MERGE (ch5:Column {fqn: "ApolloHIS.clinical.patient_registry.blood_group"})
SET ch5.name = "blood_group", ch5.data_type = "varchar(5)", ch5.is_nullable = true,
    ch5.sensitivity_level = 3, ch5.is_pii = true, ch5.pii_type = "MEDICAL",
    ch5.masking_strategy = "REDACT", ch5.is_active = true, ch5.version = 1;

MERGE (ch6:Column {fqn: "ApolloHIS.clinical.patient_registry.emergency_contact"})
SET ch6.name = "emergency_contact", ch6.data_type = "varchar(15)", ch6.is_nullable = true,
    ch6.sensitivity_level = 3, ch6.is_pii = true, ch6.pii_type = "PHONE",
    ch6.masking_strategy = "PARTIAL_MASK", ch6.is_active = true, ch6.version = 1;

MERGE (th1)-[:HAS_COLUMN]->(ch1);
MERGE (th1)-[:HAS_COLUMN]->(ch2);
MERGE (th1)-[:HAS_COLUMN]->(ch3);
MERGE (th1)-[:HAS_COLUMN]->(ch4);
MERGE (th1)-[:HAS_COLUMN]->(ch5);
MERGE (th1)-[:HAS_COLUMN]->(ch6);

// Column regulatory links
MERGE (ch2)-[:COLUMN_REGULATED_BY]->(r_hipaa);
MERGE (ch2)-[:COLUMN_REGULATED_BY]->(r_dpdpa);

// --- Key Columns (lab_results) ---
MERGE (cl1:Column {fqn: "ApolloHIS.laboratory.lab_results.result_id"})
SET cl1.name = "result_id", cl1.data_type = "bigint", cl1.is_pk = true, cl1.is_nullable = false,
    cl1.sensitivity_level = 1, cl1.is_pii = false, cl1.is_active = true, cl1.version = 1;

MERGE (cl2:Column {fqn: "ApolloHIS.laboratory.lab_results.patient_id"})
SET cl2.name = "patient_id", cl2.data_type = "int", cl2.is_nullable = false,
    cl2.sensitivity_level = 2, cl2.is_pii = false, cl2.is_active = true, cl2.version = 1;

MERGE (cl3:Column {fqn: "ApolloHIS.laboratory.lab_results.test_name"})
SET cl3.name = "test_name", cl3.data_type = "varchar(100)", cl3.is_nullable = false,
    cl3.sensitivity_level = 3, cl3.is_pii = false, cl3.is_active = true, cl3.version = 1;

MERGE (cl4:Column {fqn: "ApolloHIS.laboratory.lab_results.result_value"})
SET cl4.name = "result_value", cl4.data_type = "varchar(200)", cl4.is_nullable = true,
    cl4.sensitivity_level = 4, cl4.is_pii = true, cl4.pii_type = "MEDICAL",
    cl4.masking_strategy = "REDACT", cl4.is_active = true, cl4.version = 1;

MERGE (cl5:Column {fqn: "ApolloHIS.laboratory.lab_results.hiv_status"})
SET cl5.name = "hiv_status", cl5.data_type = "varchar(20)", cl5.is_nullable = true,
    cl5.sensitivity_level = 5, cl5.is_pii = true, cl5.pii_type = "MEDICAL_SENSITIVE",
    cl5.masking_strategy = "REDACT", cl5.hard_deny = true,
    cl5.description = "HIV test status — maximum sensitivity",
    cl5.is_active = true, cl5.version = 1;

MERGE (th6)-[:HAS_COLUMN]->(cl1);
MERGE (th6)-[:HAS_COLUMN]->(cl2);
MERGE (th6)-[:HAS_COLUMN]->(cl3);
MERGE (th6)-[:HAS_COLUMN]->(cl4);
MERGE (th6)-[:HAS_COLUMN]->(cl5);

// FK: lab_results.patient_id -> patient_registry.patient_id
MERGE (cl2)-[:FOREIGN_KEY_TO]->(ch1);

// --- HIS-specific Roles ---
MERGE (r_radiologist:Role {name: "radiologist"})
SET r_radiologist.description = "Radiologist — imaging orders and report access",
    r_radiologist.is_active = true, r_radiologist.version = 1;

MERGE (r_lab_tech:Role {name: "lab_technician"})
SET r_lab_tech.description = "Lab technician — lab orders and result entry",
    r_lab_tech.is_active = true, r_lab_tech.version = 1;

MERGE (r_surgeon:Role {name: "surgeon"})
SET r_surgeon.description = "Surgeon — procedures and OR schedule access",
    r_surgeon.is_active = true, r_surgeon.version = 1;

MERGE (r_doctor:Role {name: "doctor"});
MERGE (r_surgeon)-[:INHERITS_FROM]->(r_doctor);
MERGE (r_radiologist)-[:ACCESSES_DOMAIN]->(d_radiology);
MERGE (r_radiologist)-[:ACCESSES_DOMAIN]->(d_clinical);
MERGE (r_lab_tech)-[:ACCESSES_DOMAIN]->(d_lab);
MERGE (r_surgeon)-[:ACCESSES_DOMAIN]->(d_clinical);

// --- HIS Policies ---
MERGE (p_his1:Policy {policy_id: "POL-HIS-001"})
SET p_his1.policy_type = "ALLOW",
    p_his1.nl_description = "Lab technicians can view and enter lab results but not patient demographics",
    p_his1.structured_rule = '{"effect":"ALLOW","target":{"tables":["lab_results","lab_orders"]},"subject":{"role":"lab_technician"}}',
    p_his1.priority = 100, p_his1.is_active = true, p_his1.created_at = datetime(), p_his1.version = 1;
MERGE (p_his1)-[:APPLIES_TO_ROLE]->(r_lab_tech);
MERGE (p_his1)-[:GOVERNS_TABLE]->(th6);
MERGE (p_his1)-[:GOVERNS_TABLE]->(th7);

MERGE (p_his2:Policy {policy_id: "POL-HIS-002"})
SET p_his2.policy_type = "DENY",
    p_his2.nl_description = "HIV status column is HARD DENIED from all NL-to-SQL queries",
    p_his2.structured_rule = '{"effect":"HARD_DENY","target":{"table":"lab_results","columns":["hiv_status"]},"subject":{"role":"*"}}',
    p_his2.priority = 1000, p_his2.is_active = true, p_his2.is_hard_deny = true,
    p_his2.created_at = datetime(), p_his2.version = 1;
MERGE (p_his2)-[:GOVERNS_TABLE]->(th6);
MERGE (p_his2)-[:GOVERNS_COLUMN]->(cl5);

MERGE (p_his3:Policy {policy_id: "POL-HIS-003"})
SET p_his3.policy_type = "ALLOW",
    p_his3.nl_description = "Radiologists can access imaging orders and reports",
    p_his3.structured_rule = '{"effect":"ALLOW","target":{"tables":["imaging_orders","imaging_reports"]},"subject":{"role":"radiologist"}}',
    p_his3.priority = 100, p_his3.is_active = true, p_his3.created_at = datetime(), p_his3.version = 1;
MERGE (p_his3)-[:APPLIES_TO_ROLE]->(r_radiologist);
MERGE (p_his3)-[:GOVERNS_TABLE]->(th8);
MERGE (p_his3)-[:GOVERNS_TABLE]->(th9);
