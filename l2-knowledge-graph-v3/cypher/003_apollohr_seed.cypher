// ============================================================
// ApolloHR — Human Resources Database (SQL Server)
// ============================================================

// --- Database & Schema ---
MERGE (db_hr:Database {name: "ApolloHR"})
SET db_hr.engine = "sqlserver", db_hr.host = "sql-server-hr",
    db_hr.port = 1433, db_hr.is_active = true,
    db_hr.created_at = datetime(), db_hr.version = 1;

MERGE (s_hr:Schema {fqn: "ApolloHR.dbo"})
SET s_hr.name = "dbo", s_hr.is_active = true, s_hr.created_at = datetime(), s_hr.version = 1;
MERGE (s_payroll:Schema {fqn: "ApolloHR.payroll"})
SET s_payroll.name = "payroll", s_payroll.is_active = true, s_payroll.created_at = datetime(), s_payroll.version = 1;

MERGE (db_hr)-[:HAS_SCHEMA]->(s_hr);
MERGE (db_hr)-[:HAS_SCHEMA]->(s_payroll);

// --- Domain links ---
MERGE (d_hr:Domain {name: "hr"});
MERGE (d_admin:Domain {name: "admin"});

// --- Tables ---
MERGE (t_emp:Table {fqn: "ApolloHR.dbo.employees"})
SET t_emp.name = "employees", t_emp.description = "All hospital employees and staff records",
    t_emp.sensitivity_level = 4, t_emp.is_active = true, t_emp.row_count_approx = 45000,
    t_emp.domain = "hr", t_emp.created_at = datetime(), t_emp.version = 1;

MERGE (t_dept:Table {fqn: "ApolloHR.dbo.departments"})
SET t_dept.name = "departments", t_dept.description = "Hospital departments and units",
    t_dept.sensitivity_level = 1, t_dept.is_active = true, t_dept.row_count_approx = 120,
    t_dept.domain = "hr", t_dept.created_at = datetime(), t_dept.version = 1;

MERGE (t_pos:Table {fqn: "ApolloHR.dbo.positions"})
SET t_pos.name = "positions", t_pos.description = "Job positions and designations",
    t_pos.sensitivity_level = 1, t_pos.is_active = true, t_pos.row_count_approx = 350,
    t_pos.domain = "hr", t_pos.created_at = datetime(), t_pos.version = 1;

MERGE (t_pay:Table {fqn: "ApolloHR.payroll.salary_records"})
SET t_pay.name = "salary_records", t_pay.description = "Employee salary history and compensation",
    t_pay.sensitivity_level = 5, t_pay.is_active = true, t_pay.row_count_approx = 540000,
    t_pay.domain = "hr", t_pay.created_at = datetime(), t_pay.version = 1;

MERGE (t_att:Table {fqn: "ApolloHR.dbo.attendance"})
SET t_att.name = "attendance", t_att.description = "Employee attendance and shift records",
    t_att.sensitivity_level = 2, t_att.is_active = true, t_att.row_count_approx = 3200000,
    t_att.domain = "hr", t_att.created_at = datetime(), t_att.version = 1;

MERGE (t_leave:Table {fqn: "ApolloHR.dbo.leave_records"})
SET t_leave.name = "leave_records", t_leave.description = "Employee leave requests and approvals",
    t_leave.sensitivity_level = 3, t_leave.is_active = true, t_leave.row_count_approx = 180000,
    t_leave.domain = "hr", t_leave.created_at = datetime(), t_leave.version = 1;

MERGE (t_ben:Table {fqn: "ApolloHR.dbo.benefits"})
SET t_ben.name = "benefits", t_ben.description = "Employee benefits enrollment — insurance and retirement",
    t_ben.sensitivity_level = 4, t_ben.is_active = true, t_ben.row_count_approx = 45000,
    t_ben.domain = "hr", t_ben.created_at = datetime(), t_ben.version = 1;

MERGE (t_train:Table {fqn: "ApolloHR.dbo.training_records"})
SET t_train.name = "training_records", t_train.description = "Compliance training and certifications",
    t_train.sensitivity_level = 2, t_train.is_active = true, t_train.row_count_approx = 250000,
    t_train.domain = "hr", t_train.created_at = datetime(), t_train.version = 1;

// Schema-Table links
MERGE (s_hr)-[:HAS_TABLE]->(t_emp);
MERGE (s_hr)-[:HAS_TABLE]->(t_dept);
MERGE (s_hr)-[:HAS_TABLE]->(t_pos);
MERGE (s_payroll)-[:HAS_TABLE]->(t_pay);
MERGE (s_hr)-[:HAS_TABLE]->(t_att);
MERGE (s_hr)-[:HAS_TABLE]->(t_leave);
MERGE (s_hr)-[:HAS_TABLE]->(t_ben);
MERGE (s_hr)-[:HAS_TABLE]->(t_train);

// Domain links
MERGE (t_emp)-[:BELONGS_TO_DOMAIN]->(d_hr);
MERGE (t_dept)-[:BELONGS_TO_DOMAIN]->(d_hr);
MERGE (t_pos)-[:BELONGS_TO_DOMAIN]->(d_hr);
MERGE (t_pay)-[:BELONGS_TO_DOMAIN]->(d_hr);
MERGE (t_att)-[:BELONGS_TO_DOMAIN]->(d_hr);
MERGE (t_leave)-[:BELONGS_TO_DOMAIN]->(d_hr);
MERGE (t_ben)-[:BELONGS_TO_DOMAIN]->(d_hr);
MERGE (t_train)-[:BELONGS_TO_DOMAIN]->(d_hr);

// Regulatory links
MERGE (r_dpdpa:Regulation {code: "DPDPA_2023"});
MERGE (r_gina:Regulation {code: "GINA"});
MERGE (t_emp)-[:REGULATED_BY]->(r_dpdpa);
MERGE (t_pay)-[:REGULATED_BY]->(r_dpdpa);
MERGE (t_ben)-[:REGULATED_BY]->(r_gina);

// --- Columns (employees) ---
MERGE (ce1:Column {fqn: "ApolloHR.dbo.employees.employee_id"})
SET ce1.name = "employee_id", ce1.data_type = "int", ce1.is_pk = true, ce1.is_nullable = false,
    ce1.sensitivity_level = 1, ce1.is_pii = false, ce1.is_active = true, ce1.version = 1;

MERGE (ce2:Column {fqn: "ApolloHR.dbo.employees.full_name"})
SET ce2.name = "full_name", ce2.data_type = "nvarchar(200)", ce2.is_nullable = false,
    ce2.sensitivity_level = 4, ce2.is_pii = true, ce2.pii_type = "FULL_NAME",
    ce2.masking_strategy = "REDACT", ce2.is_active = true, ce2.version = 1;

MERGE (ce3:Column {fqn: "ApolloHR.dbo.employees.aadhaar_number"})
SET ce3.name = "aadhaar_number", ce3.data_type = "varchar(12)", ce3.is_nullable = true,
    ce3.sensitivity_level = 5, ce3.is_pii = true, ce3.pii_type = "NATIONAL_ID",
    ce3.masking_strategy = "HASH", ce3.is_active = true, ce3.version = 1;

MERGE (ce4:Column {fqn: "ApolloHR.dbo.employees.email"})
SET ce4.name = "email", ce4.data_type = "varchar(255)", ce4.is_nullable = false,
    ce4.sensitivity_level = 3, ce4.is_pii = true, ce4.pii_type = "EMAIL",
    ce4.masking_strategy = "PARTIAL_MASK", ce4.is_active = true, ce4.version = 1;

MERGE (ce5:Column {fqn: "ApolloHR.dbo.employees.phone"})
SET ce5.name = "phone", ce5.data_type = "varchar(15)", ce5.is_nullable = true,
    ce5.sensitivity_level = 3, ce5.is_pii = true, ce5.pii_type = "PHONE",
    ce5.masking_strategy = "PARTIAL_MASK", ce5.is_active = true, ce5.version = 1;

MERGE (ce6:Column {fqn: "ApolloHR.dbo.employees.department_id"})
SET ce6.name = "department_id", ce6.data_type = "int", ce6.is_nullable = false,
    ce6.sensitivity_level = 1, ce6.is_pii = false, ce6.is_active = true, ce6.version = 1;

MERGE (ce7:Column {fqn: "ApolloHR.dbo.employees.date_of_birth"})
SET ce7.name = "date_of_birth", ce7.data_type = "date", ce7.is_nullable = false,
    ce7.sensitivity_level = 4, ce7.is_pii = true, ce7.pii_type = "DATE_OF_BIRTH",
    ce7.masking_strategy = "GENERALIZE_YEAR", ce7.is_active = true, ce7.version = 1;

MERGE (ce8:Column {fqn: "ApolloHR.dbo.employees.pan_number"})
SET ce8.name = "pan_number", ce8.data_type = "varchar(10)", ce8.is_nullable = true,
    ce8.sensitivity_level = 5, ce8.is_pii = true, ce8.pii_type = "TAX_ID",
    ce8.masking_strategy = "HASH", ce8.is_active = true, ce8.version = 1;

MERGE (ce9:Column {fqn: "ApolloHR.dbo.employees.bank_account"})
SET ce9.name = "bank_account", ce9.data_type = "varchar(20)", ce9.is_nullable = true,
    ce9.sensitivity_level = 5, ce9.is_pii = true, ce9.pii_type = "BANK_ACCOUNT",
    ce9.masking_strategy = "HASH", ce9.is_active = true, ce9.version = 1;

// Column-Table links
MERGE (t_emp)-[:HAS_COLUMN]->(ce1);
MERGE (t_emp)-[:HAS_COLUMN]->(ce2);
MERGE (t_emp)-[:HAS_COLUMN]->(ce3);
MERGE (t_emp)-[:HAS_COLUMN]->(ce4);
MERGE (t_emp)-[:HAS_COLUMN]->(ce5);
MERGE (t_emp)-[:HAS_COLUMN]->(ce6);
MERGE (t_emp)-[:HAS_COLUMN]->(ce7);
MERGE (t_emp)-[:HAS_COLUMN]->(ce8);
MERGE (t_emp)-[:HAS_COLUMN]->(ce9);

// Column regulatory links
MERGE (ce3)-[:COLUMN_REGULATED_BY]->(r_dpdpa);
MERGE (ce8)-[:COLUMN_REGULATED_BY]->(r_dpdpa);
MERGE (ce9)-[:COLUMN_REGULATED_BY]->(r_dpdpa);

// --- Columns (salary_records) ---
MERGE (cs1:Column {fqn: "ApolloHR.payroll.salary_records.record_id"})
SET cs1.name = "record_id", cs1.data_type = "bigint", cs1.is_pk = true, cs1.is_nullable = false,
    cs1.sensitivity_level = 1, cs1.is_pii = false, cs1.is_active = true, cs1.version = 1;

MERGE (cs2:Column {fqn: "ApolloHR.payroll.salary_records.employee_id"})
SET cs2.name = "employee_id", cs2.data_type = "int", cs2.is_nullable = false,
    cs2.sensitivity_level = 2, cs2.is_pii = false, cs2.is_active = true, cs2.version = 1;

MERGE (cs3:Column {fqn: "ApolloHR.payroll.salary_records.gross_salary"})
SET cs3.name = "gross_salary", cs3.data_type = "decimal(12,2)", cs3.is_nullable = false,
    cs3.sensitivity_level = 5, cs3.is_pii = true, cs3.pii_type = "FINANCIAL",
    cs3.masking_strategy = "REDACT", cs3.is_active = true, cs3.version = 1;

MERGE (cs4:Column {fqn: "ApolloHR.payroll.salary_records.net_salary"})
SET cs4.name = "net_salary", cs4.data_type = "decimal(12,2)", cs4.is_nullable = false,
    cs4.sensitivity_level = 5, cs4.is_pii = true, cs4.pii_type = "FINANCIAL",
    cs4.masking_strategy = "REDACT", cs4.is_active = true, cs4.version = 1;

MERGE (t_pay)-[:HAS_COLUMN]->(cs1);
MERGE (t_pay)-[:HAS_COLUMN]->(cs2);
MERGE (t_pay)-[:HAS_COLUMN]->(cs3);
MERGE (t_pay)-[:HAS_COLUMN]->(cs4);

// FK: salary_records.employee_id -> employees.employee_id
MERGE (cs2)-[:FOREIGN_KEY_TO]->(ce1);

// --- HR Roles ---
MERGE (r_hr_manager:Role {name: "hr_manager"})
SET r_hr_manager.description = "HR department manager — full HR data access",
    r_hr_manager.is_active = true, r_hr_manager.version = 1;

MERGE (r_hr_staff:Role {name: "hr_staff"})
SET r_hr_staff.description = "HR staff — limited employee data access",
    r_hr_staff.is_active = true, r_hr_staff.version = 1;

MERGE (r_payroll_admin:Role {name: "payroll_admin"})
SET r_payroll_admin.description = "Payroll administrator — salary and compensation access",
    r_payroll_admin.is_active = true, r_payroll_admin.version = 1;

MERGE (r_hr_manager)-[:INHERITS_FROM]->(r_hr_staff);
MERGE (r_hr_manager)-[:ACCESSES_DOMAIN]->(d_hr);
MERGE (r_hr_staff)-[:ACCESSES_DOMAIN]->(d_hr);
MERGE (r_payroll_admin)-[:ACCESSES_DOMAIN]->(d_hr);

// --- HR Policies ---
MERGE (p_hr1:Policy {policy_id: "POL-HR-001"})
SET p_hr1.policy_type = "ALLOW",
    p_hr1.nl_description = "HR managers can access all employee records including PII",
    p_hr1.structured_rule = '{"effect":"ALLOW","target":{"table":"employees","columns":"*"},"subject":{"role":"hr_manager"}}',
    p_hr1.priority = 100, p_hr1.is_active = true, p_hr1.created_at = datetime(), p_hr1.version = 1;
MERGE (p_hr1)-[:APPLIES_TO_ROLE]->(r_hr_manager);
MERGE (p_hr1)-[:GOVERNS_TABLE]->(t_emp);

MERGE (p_hr2:Policy {policy_id: "POL-HR-002"})
SET p_hr2.policy_type = "DENY",
    p_hr2.nl_description = "Salary records are restricted — only payroll admin and HR managers can access",
    p_hr2.structured_rule = '{"effect":"DENY","target":{"table":"salary_records"},"subject":{"role":"*"},"exception":{"roles":["payroll_admin","hr_manager"]}}',
    p_hr2.priority = 200, p_hr2.is_active = true, p_hr2.created_at = datetime(), p_hr2.version = 1;
MERGE (p_hr2)-[:GOVERNS_TABLE]->(t_pay);

MERGE (p_hr3:Policy {policy_id: "POL-HR-003"})
SET p_hr3.policy_type = "MASK",
    p_hr3.nl_description = "HR staff see masked PII — Aadhaar, PAN, and bank account are hashed",
    p_hr3.structured_rule = '{"effect":"MASK","target":{"table":"employees","columns":["aadhaar_number","pan_number","bank_account"]},"subject":{"role":"hr_staff"}}',
    p_hr3.priority = 90, p_hr3.is_active = true, p_hr3.created_at = datetime(), p_hr3.version = 1;
MERGE (p_hr3)-[:APPLIES_TO_ROLE]->(r_hr_staff);
MERGE (p_hr3)-[:GOVERNS_TABLE]->(t_emp);
MERGE (p_hr3)-[:GOVERNS_COLUMN]->(ce3);
MERGE (p_hr3)-[:GOVERNS_COLUMN]->(ce8);
MERGE (p_hr3)-[:GOVERNS_COLUMN]->(ce9);
