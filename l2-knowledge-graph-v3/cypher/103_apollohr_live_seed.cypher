// ============================================================
// ApolloHR — Human Resources Database (AWS RDS SQL Server)
// Auto-generated from live crawl at 2026-03-03 19:28:09
// ============================================================

// --- Database ---
MERGE (db:Database {name: "ApolloHR"})
SET db.engine = "sqlserver", db.is_active = true,
    db.created_at = datetime(), db.source = "live_crawl";

// --- Schemas ---
MERGE (s0:Schema {fqn: "ApolloHR.dbo"})
SET s0.name = "dbo", s0.is_active = true;

MERGE (db)-[:HAS_SCHEMA]->(s0);

// --- Tables ---
MERGE (t0:Table {fqn: "ApolloHR.dbo.certifications"})
SET t0.name = "certifications", t0.is_active = true,
    t0.row_count_approx = 411,
    t0.sensitivity_level = 0, t0.has_pii = false,
    t0.domain = "hr", t0.source = "live_crawl";

MERGE (t1:Table {fqn: "ApolloHR.dbo.credentials"})
SET t1.name = "credentials", t1.is_active = true,
    t1.row_count_approx = 150,
    t1.sensitivity_level = 2, t1.has_pii = true,
    t1.domain = "hr", t1.source = "live_crawl";

MERGE (t2:Table {fqn: "ApolloHR.dbo.employees"})
SET t2.name = "employees", t2.is_active = true,
    t2.row_count_approx = 400,
    t2.sensitivity_level = 5, t2.has_pii = true,
    t2.domain = "hr", t2.source = "live_crawl";

MERGE (t3:Table {fqn: "ApolloHR.dbo.leave_records"})
SET t3.name = "leave_records", t3.is_active = true,
    t3.row_count_approx = 0,
    t3.sensitivity_level = 0, t3.has_pii = false,
    t3.domain = "hr", t3.source = "live_crawl";

MERGE (t4:Table {fqn: "ApolloHR.dbo.payroll"})
SET t4.name = "payroll", t4.is_active = true,
    t4.row_count_approx = 1200,
    t4.sensitivity_level = 5, t4.has_pii = true,
    t4.domain = "hr", t4.source = "live_crawl";

// Schema-Table links
MERGE (s0)-[:HAS_TABLE]->(t0);
MERGE (s0)-[:HAS_TABLE]->(t1);
MERGE (s0)-[:HAS_TABLE]->(t2);
MERGE (s0)-[:HAS_TABLE]->(t3);
MERGE (s0)-[:HAS_TABLE]->(t4);

// --- Columns (certifications) ---
MERGE (c0:Column {fqn: "ApolloHR.dbo.certifications.certification_id"})
SET c0.name = "certification_id", c0.data_type = "varchar", c0.is_pk = true, c0.is_nullable = false, c0.ordinal_position = 1, c0.is_active = true;

MERGE (c1:Column {fqn: "ApolloHR.dbo.certifications.employee_id"})
SET c1.name = "employee_id", c1.data_type = "varchar", c1.is_nullable = false, c1.ordinal_position = 2, c1.is_active = true;

MERGE (c2:Column {fqn: "ApolloHR.dbo.certifications.certification_name"})
SET c2.name = "certification_name", c2.data_type = "nvarchar", c2.is_nullable = false, c2.ordinal_position = 3, c2.is_active = true;

MERGE (c3:Column {fqn: "ApolloHR.dbo.certifications.certification_body"})
SET c3.name = "certification_body", c3.data_type = "nvarchar", c3.is_nullable = true, c3.ordinal_position = 4, c3.is_active = true;

MERGE (c4:Column {fqn: "ApolloHR.dbo.certifications.date_obtained"})
SET c4.name = "date_obtained", c4.data_type = "date", c4.is_nullable = false, c4.ordinal_position = 5, c4.is_active = true;

MERGE (c5:Column {fqn: "ApolloHR.dbo.certifications.expiry_date"})
SET c5.name = "expiry_date", c5.data_type = "date", c5.is_nullable = true, c5.ordinal_position = 6, c5.is_active = true;

MERGE (c6:Column {fqn: "ApolloHR.dbo.certifications.is_active"})
SET c6.name = "is_active", c6.data_type = "bit", c6.is_nullable = true, c6.ordinal_position = 7, c6.is_active = true;

MERGE (c7:Column {fqn: "ApolloHR.dbo.certifications.created_at"})
SET c7.name = "created_at", c7.data_type = "datetime2", c7.is_nullable = true, c7.ordinal_position = 8, c7.is_active = true;

// Column-Table links (certifications)
MERGE (t0)-[:HAS_COLUMN]->(c0);
MERGE (t0)-[:HAS_COLUMN]->(c1);
MERGE (t0)-[:HAS_COLUMN]->(c2);
MERGE (t0)-[:HAS_COLUMN]->(c3);
MERGE (t0)-[:HAS_COLUMN]->(c4);
MERGE (t0)-[:HAS_COLUMN]->(c5);
MERGE (t0)-[:HAS_COLUMN]->(c6);
MERGE (t0)-[:HAS_COLUMN]->(c7);

// --- Columns (credentials) ---
MERGE (c8:Column {fqn: "ApolloHR.dbo.credentials.credential_id"})
SET c8.name = "credential_id", c8.data_type = "varchar", c8.is_pk = true, c8.is_nullable = false, c8.ordinal_position = 1, c8.is_active = true;

MERGE (c9:Column {fqn: "ApolloHR.dbo.credentials.employee_id"})
SET c9.name = "employee_id", c9.data_type = "varchar", c9.is_nullable = false, c9.ordinal_position = 2, c9.is_active = true;

MERGE (c10:Column {fqn: "ApolloHR.dbo.credentials.credential_type"})
SET c10.name = "credential_type", c10.data_type = "varchar", c10.is_nullable = false, c10.ordinal_position = 3, c10.is_active = true;

MERGE (c11:Column {fqn: "ApolloHR.dbo.credentials.credential_number"})
SET c11.name = "credential_number", c11.data_type = "varchar", c11.is_nullable = false, c11.ordinal_position = 4, c11.is_active = true;

MERGE (c12:Column {fqn: "ApolloHR.dbo.credentials.issuing_authority"})
SET c12.name = "issuing_authority", c12.data_type = "nvarchar", c12.is_nullable = true, c12.ordinal_position = 5, c12.is_active = true;

MERGE (c13:Column {fqn: "ApolloHR.dbo.credentials.issue_date"})
SET c13.name = "issue_date", c13.data_type = "date", c13.is_nullable = true, c13.ordinal_position = 6, c13.is_active = true;

MERGE (c14:Column {fqn: "ApolloHR.dbo.credentials.expiry_date"})
SET c14.name = "expiry_date", c14.data_type = "date", c14.is_nullable = true, c14.ordinal_position = 7, c14.is_active = true;

MERGE (c15:Column {fqn: "ApolloHR.dbo.credentials.state_of_issue"})
SET c15.name = "state_of_issue", c15.data_type = "varchar", c15.is_nullable = true, c15.ordinal_position = 8, c15.sensitivity_level = 2, c15.is_pii = true, c15.pii_type = "ADDRESS", c15.masking_strategy = "GENERALIZE", c15.is_active = true;

MERGE (c16:Column {fqn: "ApolloHR.dbo.credentials.verification_status"})
SET c16.name = "verification_status", c16.data_type = "varchar", c16.is_nullable = true, c16.ordinal_position = 9, c16.is_active = true;

MERGE (c17:Column {fqn: "ApolloHR.dbo.credentials.created_at"})
SET c17.name = "created_at", c17.data_type = "datetime2", c17.is_nullable = true, c17.ordinal_position = 10, c17.is_active = true;

// Column-Table links (credentials)
MERGE (t1)-[:HAS_COLUMN]->(c8);
MERGE (t1)-[:HAS_COLUMN]->(c9);
MERGE (t1)-[:HAS_COLUMN]->(c10);
MERGE (t1)-[:HAS_COLUMN]->(c11);
MERGE (t1)-[:HAS_COLUMN]->(c12);
MERGE (t1)-[:HAS_COLUMN]->(c13);
MERGE (t1)-[:HAS_COLUMN]->(c14);
MERGE (t1)-[:HAS_COLUMN]->(c15);
MERGE (t1)-[:HAS_COLUMN]->(c16);
MERGE (t1)-[:HAS_COLUMN]->(c17);

// --- Columns (employees) ---
MERGE (c18:Column {fqn: "ApolloHR.dbo.employees.employee_id"})
SET c18.name = "employee_id", c18.data_type = "varchar", c18.is_pk = true, c18.is_nullable = false, c18.ordinal_position = 1, c18.is_active = true;

MERGE (c19:Column {fqn: "ApolloHR.dbo.employees.first_name"})
SET c19.name = "first_name", c19.data_type = "nvarchar", c19.is_nullable = false, c19.ordinal_position = 2, c19.sensitivity_level = 4, c19.is_pii = true, c19.pii_type = "FULL_NAME", c19.masking_strategy = "REDACT", c19.is_active = true;

MERGE (c20:Column {fqn: "ApolloHR.dbo.employees.last_name"})
SET c20.name = "last_name", c20.data_type = "nvarchar", c20.is_nullable = false, c20.ordinal_position = 3, c20.sensitivity_level = 4, c20.is_pii = true, c20.pii_type = "FULL_NAME", c20.masking_strategy = "REDACT", c20.is_active = true;

MERGE (c21:Column {fqn: "ApolloHR.dbo.employees.full_name"})
SET c21.name = "full_name", c21.data_type = "nvarchar", c21.is_nullable = false, c21.ordinal_position = 4, c21.sensitivity_level = 4, c21.is_pii = true, c21.pii_type = "FULL_NAME", c21.masking_strategy = "REDACT", c21.is_active = true;

MERGE (c22:Column {fqn: "ApolloHR.dbo.employees.date_of_birth"})
SET c22.name = "date_of_birth", c22.data_type = "date", c22.is_nullable = false, c22.ordinal_position = 5, c22.sensitivity_level = 4, c22.is_pii = true, c22.pii_type = "DATE_OF_BIRTH", c22.masking_strategy = "GENERALIZE_YEAR", c22.is_active = true;

MERGE (c23:Column {fqn: "ApolloHR.dbo.employees.gender"})
SET c23.name = "gender", c23.data_type = "varchar", c23.is_nullable = true, c23.ordinal_position = 6, c23.sensitivity_level = 3, c23.is_pii = true, c23.pii_type = "DEMOGRAPHIC", c23.masking_strategy = "GENERALIZE", c23.is_active = true;

MERGE (c24:Column {fqn: "ApolloHR.dbo.employees.aadhaar_number"})
SET c24.name = "aadhaar_number", c24.data_type = "varchar", c24.is_nullable = true, c24.ordinal_position = 7, c24.sensitivity_level = 5, c24.is_pii = true, c24.pii_type = "NATIONAL_ID", c24.masking_strategy = "HASH", c24.is_active = true;

MERGE (c25:Column {fqn: "ApolloHR.dbo.employees.pan_number"})
SET c25.name = "pan_number", c25.data_type = "varchar", c25.is_nullable = true, c25.ordinal_position = 8, c25.sensitivity_level = 5, c25.is_pii = true, c25.pii_type = "TAX_ID", c25.masking_strategy = "HASH", c25.is_active = true;

MERGE (c26:Column {fqn: "ApolloHR.dbo.employees.phone"})
SET c26.name = "phone", c26.data_type = "varchar", c26.is_nullable = true, c26.ordinal_position = 9, c26.sensitivity_level = 3, c26.is_pii = true, c26.pii_type = "PHONE", c26.masking_strategy = "PARTIAL_MASK", c26.is_active = true;

MERGE (c27:Column {fqn: "ApolloHR.dbo.employees.email"})
SET c27.name = "email", c27.data_type = "varchar", c27.is_nullable = false, c27.ordinal_position = 10, c27.sensitivity_level = 3, c27.is_pii = true, c27.pii_type = "EMAIL", c27.masking_strategy = "PARTIAL_MASK", c27.is_active = true;

MERGE (c28:Column {fqn: "ApolloHR.dbo.employees.personal_email"})
SET c28.name = "personal_email", c28.data_type = "varchar", c28.is_nullable = true, c28.ordinal_position = 11, c28.sensitivity_level = 4, c28.is_pii = true, c28.pii_type = "EMAIL", c28.masking_strategy = "PARTIAL_MASK", c28.is_active = true;

MERGE (c29:Column {fqn: "ApolloHR.dbo.employees.address"})
SET c29.name = "address", c29.data_type = "nvarchar", c29.is_nullable = true, c29.ordinal_position = 12, c29.sensitivity_level = 3, c29.is_pii = true, c29.pii_type = "ADDRESS", c29.masking_strategy = "REDACT", c29.is_active = true;

MERGE (c30:Column {fqn: "ApolloHR.dbo.employees.city"})
SET c30.name = "city", c30.data_type = "nvarchar", c30.is_nullable = true, c30.ordinal_position = 13, c30.sensitivity_level = 2, c30.is_pii = true, c30.pii_type = "ADDRESS", c30.masking_strategy = "GENERALIZE", c30.is_active = true;

MERGE (c31:Column {fqn: "ApolloHR.dbo.employees.state"})
SET c31.name = "state", c31.data_type = "nvarchar", c31.is_nullable = true, c31.ordinal_position = 14, c31.sensitivity_level = 2, c31.is_pii = true, c31.pii_type = "ADDRESS", c31.masking_strategy = "GENERALIZE", c31.is_active = true;

MERGE (c32:Column {fqn: "ApolloHR.dbo.employees.pin_code"})
SET c32.name = "pin_code", c32.data_type = "varchar", c32.is_nullable = true, c32.ordinal_position = 15, c32.sensitivity_level = 2, c32.is_pii = true, c32.pii_type = "ADDRESS", c32.masking_strategy = "GENERALIZE", c32.is_active = true;

MERGE (c33:Column {fqn: "ApolloHR.dbo.employees.employee_type"})
SET c33.name = "employee_type", c33.data_type = "varchar", c33.is_nullable = false, c33.ordinal_position = 16, c33.is_active = true;

MERGE (c34:Column {fqn: "ApolloHR.dbo.employees.designation"})
SET c34.name = "designation", c34.data_type = "nvarchar", c34.is_nullable = true, c34.ordinal_position = 17, c34.is_active = true;

MERGE (c35:Column {fqn: "ApolloHR.dbo.employees.department_id"})
SET c35.name = "department_id", c35.data_type = "varchar", c35.is_nullable = true, c35.ordinal_position = 18, c35.is_active = true;

MERGE (c36:Column {fqn: "ApolloHR.dbo.employees.facility_id"})
SET c36.name = "facility_id", c36.data_type = "varchar", c36.is_nullable = true, c36.ordinal_position = 19, c36.is_active = true;

MERGE (c37:Column {fqn: "ApolloHR.dbo.employees.reporting_manager_id"})
SET c37.name = "reporting_manager_id", c37.data_type = "varchar", c37.is_nullable = true, c37.ordinal_position = 20, c37.is_active = true;

MERGE (c38:Column {fqn: "ApolloHR.dbo.employees.hire_date"})
SET c38.name = "hire_date", c38.data_type = "date", c38.is_nullable = false, c38.ordinal_position = 21, c38.is_active = true;

MERGE (c39:Column {fqn: "ApolloHR.dbo.employees.termination_date"})
SET c39.name = "termination_date", c39.data_type = "date", c39.is_nullable = true, c39.ordinal_position = 22, c39.is_active = true;

MERGE (c40:Column {fqn: "ApolloHR.dbo.employees.employment_status"})
SET c40.name = "employment_status", c40.data_type = "varchar", c40.is_nullable = true, c40.ordinal_position = 23, c40.is_active = true;

MERGE (c41:Column {fqn: "ApolloHR.dbo.employees.is_active"})
SET c41.name = "is_active", c41.data_type = "bit", c41.is_nullable = true, c41.ordinal_position = 24, c41.is_active = true;

MERGE (c42:Column {fqn: "ApolloHR.dbo.employees.created_at"})
SET c42.name = "created_at", c42.data_type = "datetime2", c42.is_nullable = true, c42.ordinal_position = 25, c42.is_active = true;

MERGE (c43:Column {fqn: "ApolloHR.dbo.employees.updated_at"})
SET c43.name = "updated_at", c43.data_type = "datetime2", c43.is_nullable = true, c43.ordinal_position = 26, c43.is_active = true;

// Column-Table links (employees)
MERGE (t2)-[:HAS_COLUMN]->(c18);
MERGE (t2)-[:HAS_COLUMN]->(c19);
MERGE (t2)-[:HAS_COLUMN]->(c20);
MERGE (t2)-[:HAS_COLUMN]->(c21);
MERGE (t2)-[:HAS_COLUMN]->(c22);
MERGE (t2)-[:HAS_COLUMN]->(c23);
MERGE (t2)-[:HAS_COLUMN]->(c24);
MERGE (t2)-[:HAS_COLUMN]->(c25);
MERGE (t2)-[:HAS_COLUMN]->(c26);
MERGE (t2)-[:HAS_COLUMN]->(c27);
MERGE (t2)-[:HAS_COLUMN]->(c28);
MERGE (t2)-[:HAS_COLUMN]->(c29);
MERGE (t2)-[:HAS_COLUMN]->(c30);
MERGE (t2)-[:HAS_COLUMN]->(c31);
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

// --- Columns (leave_records) ---
MERGE (c44:Column {fqn: "ApolloHR.dbo.leave_records.leave_id"})
SET c44.name = "leave_id", c44.data_type = "varchar", c44.is_pk = true, c44.is_nullable = false, c44.ordinal_position = 1, c44.is_active = true;

MERGE (c45:Column {fqn: "ApolloHR.dbo.leave_records.employee_id"})
SET c45.name = "employee_id", c45.data_type = "varchar", c45.is_nullable = false, c45.ordinal_position = 2, c45.is_active = true;

MERGE (c46:Column {fqn: "ApolloHR.dbo.leave_records.leave_type"})
SET c46.name = "leave_type", c46.data_type = "varchar", c46.is_nullable = false, c46.ordinal_position = 3, c46.is_active = true;

MERGE (c47:Column {fqn: "ApolloHR.dbo.leave_records.start_date"})
SET c47.name = "start_date", c47.data_type = "date", c47.is_nullable = false, c47.ordinal_position = 4, c47.is_active = true;

MERGE (c48:Column {fqn: "ApolloHR.dbo.leave_records.end_date"})
SET c48.name = "end_date", c48.data_type = "date", c48.is_nullable = false, c48.ordinal_position = 5, c48.is_active = true;

MERGE (c49:Column {fqn: "ApolloHR.dbo.leave_records.days_count"})
SET c49.name = "days_count", c49.data_type = "int", c49.is_nullable = false, c49.ordinal_position = 6, c49.is_active = true;

MERGE (c50:Column {fqn: "ApolloHR.dbo.leave_records.reason"})
SET c50.name = "reason", c50.data_type = "nvarchar", c50.is_nullable = true, c50.ordinal_position = 7, c50.is_active = true;

MERGE (c51:Column {fqn: "ApolloHR.dbo.leave_records.status"})
SET c51.name = "status", c51.data_type = "varchar", c51.is_nullable = true, c51.ordinal_position = 8, c51.is_active = true;

MERGE (c52:Column {fqn: "ApolloHR.dbo.leave_records.approved_by"})
SET c52.name = "approved_by", c52.data_type = "varchar", c52.is_nullable = true, c52.ordinal_position = 9, c52.is_active = true;

MERGE (c53:Column {fqn: "ApolloHR.dbo.leave_records.created_at"})
SET c53.name = "created_at", c53.data_type = "datetime2", c53.is_nullable = true, c53.ordinal_position = 10, c53.is_active = true;

// Column-Table links (leave_records)
MERGE (t3)-[:HAS_COLUMN]->(c44);
MERGE (t3)-[:HAS_COLUMN]->(c45);
MERGE (t3)-[:HAS_COLUMN]->(c46);
MERGE (t3)-[:HAS_COLUMN]->(c47);
MERGE (t3)-[:HAS_COLUMN]->(c48);
MERGE (t3)-[:HAS_COLUMN]->(c49);
MERGE (t3)-[:HAS_COLUMN]->(c50);
MERGE (t3)-[:HAS_COLUMN]->(c51);
MERGE (t3)-[:HAS_COLUMN]->(c52);
MERGE (t3)-[:HAS_COLUMN]->(c53);

// --- Columns (payroll) ---
MERGE (c54:Column {fqn: "ApolloHR.dbo.payroll.payroll_id"})
SET c54.name = "payroll_id", c54.data_type = "varchar", c54.is_pk = true, c54.is_nullable = false, c54.ordinal_position = 1, c54.is_active = true;

MERGE (c55:Column {fqn: "ApolloHR.dbo.payroll.employee_id"})
SET c55.name = "employee_id", c55.data_type = "varchar", c55.is_nullable = false, c55.ordinal_position = 2, c55.is_active = true;

MERGE (c56:Column {fqn: "ApolloHR.dbo.payroll.pay_period_start"})
SET c56.name = "pay_period_start", c56.data_type = "date", c56.is_nullable = false, c56.ordinal_position = 3, c56.is_active = true;

MERGE (c57:Column {fqn: "ApolloHR.dbo.payroll.pay_period_end"})
SET c57.name = "pay_period_end", c57.data_type = "date", c57.is_nullable = false, c57.ordinal_position = 4, c57.is_active = true;

MERGE (c58:Column {fqn: "ApolloHR.dbo.payroll.basic_salary"})
SET c58.name = "basic_salary", c58.data_type = "decimal", c58.is_nullable = false, c58.ordinal_position = 5, c58.sensitivity_level = 5, c58.is_pii = true, c58.pii_type = "FINANCIAL", c58.masking_strategy = "REDACT", c58.is_active = true;

MERGE (c59:Column {fqn: "ApolloHR.dbo.payroll.hra"})
SET c59.name = "hra", c59.data_type = "decimal", c59.is_nullable = true, c59.ordinal_position = 6, c59.is_active = true;

MERGE (c60:Column {fqn: "ApolloHR.dbo.payroll.da"})
SET c60.name = "da", c60.data_type = "decimal", c60.is_nullable = true, c60.ordinal_position = 7, c60.is_active = true;

MERGE (c61:Column {fqn: "ApolloHR.dbo.payroll.special_allowance"})
SET c61.name = "special_allowance", c61.data_type = "decimal", c61.is_nullable = true, c61.ordinal_position = 8, c61.is_active = true;

MERGE (c62:Column {fqn: "ApolloHR.dbo.payroll.overtime_amount"})
SET c62.name = "overtime_amount", c62.data_type = "decimal", c62.is_nullable = true, c62.ordinal_position = 9, c62.is_active = true;

MERGE (c63:Column {fqn: "ApolloHR.dbo.payroll.gross_salary"})
SET c63.name = "gross_salary", c63.data_type = "decimal", c63.is_nullable = false, c63.ordinal_position = 10, c63.sensitivity_level = 5, c63.is_pii = true, c63.pii_type = "FINANCIAL", c63.masking_strategy = "REDACT", c63.is_active = true;

MERGE (c64:Column {fqn: "ApolloHR.dbo.payroll.pf_deduction"})
SET c64.name = "pf_deduction", c64.data_type = "decimal", c64.is_nullable = true, c64.ordinal_position = 11, c64.is_active = true;

MERGE (c65:Column {fqn: "ApolloHR.dbo.payroll.esi_deduction"})
SET c65.name = "esi_deduction", c65.data_type = "decimal", c65.is_nullable = true, c65.ordinal_position = 12, c65.is_active = true;

MERGE (c66:Column {fqn: "ApolloHR.dbo.payroll.professional_tax"})
SET c66.name = "professional_tax", c66.data_type = "decimal", c66.is_nullable = true, c66.ordinal_position = 13, c66.is_active = true;

MERGE (c67:Column {fqn: "ApolloHR.dbo.payroll.tds"})
SET c67.name = "tds", c67.data_type = "decimal", c67.is_nullable = true, c67.ordinal_position = 14, c67.is_active = true;

MERGE (c68:Column {fqn: "ApolloHR.dbo.payroll.other_deductions"})
SET c68.name = "other_deductions", c68.data_type = "decimal", c68.is_nullable = true, c68.ordinal_position = 15, c68.is_active = true;

MERGE (c69:Column {fqn: "ApolloHR.dbo.payroll.net_salary"})
SET c69.name = "net_salary", c69.data_type = "decimal", c69.is_nullable = false, c69.ordinal_position = 16, c69.sensitivity_level = 5, c69.is_pii = true, c69.pii_type = "FINANCIAL", c69.masking_strategy = "REDACT", c69.is_active = true;

MERGE (c70:Column {fqn: "ApolloHR.dbo.payroll.bank_account_number"})
SET c70.name = "bank_account_number", c70.data_type = "varchar", c70.is_nullable = true, c70.ordinal_position = 17, c70.sensitivity_level = 5, c70.is_pii = true, c70.pii_type = "BANK_ACCOUNT", c70.masking_strategy = "HASH", c70.is_active = true;

MERGE (c71:Column {fqn: "ApolloHR.dbo.payroll.ifsc_code"})
SET c71.name = "ifsc_code", c71.data_type = "varchar", c71.is_nullable = true, c71.ordinal_position = 18, c71.sensitivity_level = 5, c71.is_pii = true, c71.pii_type = "BANK_ACCOUNT", c71.masking_strategy = "HASH", c71.is_active = true;

MERGE (c72:Column {fqn: "ApolloHR.dbo.payroll.payment_date"})
SET c72.name = "payment_date", c72.data_type = "date", c72.is_nullable = true, c72.ordinal_position = 19, c72.is_active = true;

MERGE (c73:Column {fqn: "ApolloHR.dbo.payroll.payment_status"})
SET c73.name = "payment_status", c73.data_type = "varchar", c73.is_nullable = true, c73.ordinal_position = 20, c73.is_active = true;

MERGE (c74:Column {fqn: "ApolloHR.dbo.payroll.created_at"})
SET c74.name = "created_at", c74.data_type = "datetime2", c74.is_nullable = true, c74.ordinal_position = 21, c74.is_active = true;

// Column-Table links (payroll)
MERGE (t4)-[:HAS_COLUMN]->(c54);
MERGE (t4)-[:HAS_COLUMN]->(c55);
MERGE (t4)-[:HAS_COLUMN]->(c56);
MERGE (t4)-[:HAS_COLUMN]->(c57);
MERGE (t4)-[:HAS_COLUMN]->(c58);
MERGE (t4)-[:HAS_COLUMN]->(c59);
MERGE (t4)-[:HAS_COLUMN]->(c60);
MERGE (t4)-[:HAS_COLUMN]->(c61);
MERGE (t4)-[:HAS_COLUMN]->(c62);
MERGE (t4)-[:HAS_COLUMN]->(c63);
MERGE (t4)-[:HAS_COLUMN]->(c64);
MERGE (t4)-[:HAS_COLUMN]->(c65);
MERGE (t4)-[:HAS_COLUMN]->(c66);
MERGE (t4)-[:HAS_COLUMN]->(c67);
MERGE (t4)-[:HAS_COLUMN]->(c68);
MERGE (t4)-[:HAS_COLUMN]->(c69);
MERGE (t4)-[:HAS_COLUMN]->(c70);
MERGE (t4)-[:HAS_COLUMN]->(c71);
MERGE (t4)-[:HAS_COLUMN]->(c72);
MERGE (t4)-[:HAS_COLUMN]->(c73);
MERGE (t4)-[:HAS_COLUMN]->(c74);

// --- Foreign Keys ---
MERGE (c1)-[:FOREIGN_KEY_TO {constraint: "FK__certifica__emplo__35BCFE0A"}]->(c1);
MERGE (c9)-[:FOREIGN_KEY_TO {constraint: "FK__credentia__emplo__30F848ED"}]->(c9);
MERGE (c45)-[:FOREIGN_KEY_TO {constraint: "FK__leave_rec__emplo__3A81B327"}]->(c45);
MERGE (c55)-[:FOREIGN_KEY_TO {constraint: "FK__payroll__employe__2A4B4B5E"}]->(c55);

// --- Domains ---
MERGE (dom_hr:Domain {name: "hr"});

// Domain-Table links
MERGE (t0)-[:BELONGS_TO_DOMAIN]->(dom_hr);
MERGE (t1)-[:BELONGS_TO_DOMAIN]->(dom_hr);
MERGE (t2)-[:BELONGS_TO_DOMAIN]->(dom_hr);
MERGE (t3)-[:BELONGS_TO_DOMAIN]->(dom_hr);
MERGE (t4)-[:BELONGS_TO_DOMAIN]->(dom_hr);
