// ============================================================
// apollo_financial — Financial Database (PostgreSQL)
// ============================================================

// --- Database & Schemas ---
MERGE (db_fin:Database {name: "apollo_financial"})
SET db_fin.engine = "postgresql", db_fin.host = "oracle-financial",
    db_fin.port = 5432, db_fin.is_active = true,
    db_fin.created_at = datetime(), db_fin.version = 1;

MERGE (s_gl:Schema {fqn: "apollo_financial.general_ledger"})
SET s_gl.name = "general_ledger", s_gl.is_active = true, s_gl.created_at = datetime(), s_gl.version = 1;
MERGE (s_ap:Schema {fqn: "apollo_financial.accounts"})
SET s_ap.name = "accounts", s_ap.is_active = true, s_ap.created_at = datetime(), s_ap.version = 1;
MERGE (s_proc:Schema {fqn: "apollo_financial.procurement"})
SET s_proc.name = "procurement", s_proc.is_active = true, s_proc.created_at = datetime(), s_proc.version = 1;

MERGE (db_fin)-[:HAS_SCHEMA]->(s_gl);
MERGE (db_fin)-[:HAS_SCHEMA]->(s_ap);
MERGE (db_fin)-[:HAS_SCHEMA]->(s_proc);

// --- Domain ---
MERGE (d_finance:Domain {name: "finance"})
SET d_finance.description = "Financial accounting, GL, AP/AR, and procurement",
    d_finance.created_at = datetime(), d_finance.version = 1;
MERGE (d_billing:Domain {name: "billing"});

// --- Regulations ---
MERGE (r_dpdpa:Regulation {code: "DPDPA_2023"});

// --- Tables ---
MERGE (tf1:Table {fqn: "apollo_financial.general_ledger.gl_entries"})
SET tf1.name = "gl_entries", tf1.description = "General ledger journal entries",
    tf1.sensitivity_level = 3, tf1.is_active = true, tf1.row_count_approx = 28000000,
    tf1.domain = "finance", tf1.created_at = datetime(), tf1.version = 1;

MERGE (tf2:Table {fqn: "apollo_financial.general_ledger.chart_of_accounts"})
SET tf2.name = "chart_of_accounts", tf2.description = "Chart of accounts master",
    tf2.sensitivity_level = 2, tf2.is_active = true, tf2.row_count_approx = 2500,
    tf2.domain = "finance", tf2.created_at = datetime(), tf2.version = 1;

MERGE (tf3:Table {fqn: "apollo_financial.accounts.accounts_payable"})
SET tf3.name = "accounts_payable", tf3.description = "Vendor invoices and payment obligations",
    tf3.sensitivity_level = 3, tf3.is_active = true, tf3.row_count_approx = 4500000,
    tf3.domain = "finance", tf3.created_at = datetime(), tf3.version = 1;

MERGE (tf4:Table {fqn: "apollo_financial.accounts.accounts_receivable"})
SET tf4.name = "accounts_receivable", tf4.description = "Patient and insurance receivables",
    tf4.sensitivity_level = 3, tf4.is_active = true, tf4.row_count_approx = 6200000,
    tf4.domain = "finance", tf4.created_at = datetime(), tf4.version = 1;

MERGE (tf5:Table {fqn: "apollo_financial.procurement.purchase_orders"})
SET tf5.name = "purchase_orders", tf5.description = "Purchase orders for medical supplies and equipment",
    tf5.sensitivity_level = 2, tf5.is_active = true, tf5.row_count_approx = 850000,
    tf5.domain = "finance", tf5.created_at = datetime(), tf5.version = 1;

MERGE (tf6:Table {fqn: "apollo_financial.procurement.vendor_master"})
SET tf6.name = "vendor_master", tf6.description = "Vendor/supplier master records with bank details",
    tf6.sensitivity_level = 4, tf6.is_active = true, tf6.row_count_approx = 12000,
    tf6.domain = "finance", tf6.created_at = datetime(), tf6.version = 1;

MERGE (tf7:Table {fqn: "apollo_financial.general_ledger.cost_centers"})
SET tf7.name = "cost_centers", tf7.description = "Hospital cost center hierarchy",
    tf7.sensitivity_level = 1, tf7.is_active = true, tf7.row_count_approx = 500,
    tf7.domain = "finance", tf7.created_at = datetime(), tf7.version = 1;

MERGE (tf8:Table {fqn: "apollo_financial.general_ledger.budget_allocations"})
SET tf8.name = "budget_allocations", tf8.description = "Annual budget allocations by department and cost center",
    tf8.sensitivity_level = 3, tf8.is_active = true, tf8.row_count_approx = 35000,
    tf8.domain = "finance", tf8.created_at = datetime(), tf8.version = 1;

// Schema-Table links
MERGE (s_gl)-[:HAS_TABLE]->(tf1);
MERGE (s_gl)-[:HAS_TABLE]->(tf2);
MERGE (s_ap)-[:HAS_TABLE]->(tf3);
MERGE (s_ap)-[:HAS_TABLE]->(tf4);
MERGE (s_proc)-[:HAS_TABLE]->(tf5);
MERGE (s_proc)-[:HAS_TABLE]->(tf6);
MERGE (s_gl)-[:HAS_TABLE]->(tf7);
MERGE (s_gl)-[:HAS_TABLE]->(tf8);

// Domain links
MERGE (tf1)-[:BELONGS_TO_DOMAIN]->(d_finance);
MERGE (tf2)-[:BELONGS_TO_DOMAIN]->(d_finance);
MERGE (tf3)-[:BELONGS_TO_DOMAIN]->(d_finance);
MERGE (tf4)-[:BELONGS_TO_DOMAIN]->(d_finance);
MERGE (tf5)-[:BELONGS_TO_DOMAIN]->(d_finance);
MERGE (tf6)-[:BELONGS_TO_DOMAIN]->(d_finance);
MERGE (tf7)-[:BELONGS_TO_DOMAIN]->(d_finance);
MERGE (tf8)-[:BELONGS_TO_DOMAIN]->(d_finance);

// Regulatory
MERGE (tf6)-[:REGULATED_BY]->(r_dpdpa);

// --- Key Columns (vendor_master — has PII: bank details) ---
MERGE (cv1:Column {fqn: "apollo_financial.procurement.vendor_master.vendor_id"})
SET cv1.name = "vendor_id", cv1.data_type = "integer", cv1.is_pk = true, cv1.is_nullable = false,
    cv1.sensitivity_level = 1, cv1.is_pii = false, cv1.is_active = true, cv1.version = 1;

MERGE (cv2:Column {fqn: "apollo_financial.procurement.vendor_master.vendor_name"})
SET cv2.name = "vendor_name", cv2.data_type = "varchar(200)", cv2.is_nullable = false,
    cv2.sensitivity_level = 2, cv2.is_pii = false, cv2.is_active = true, cv2.version = 1;

MERGE (cv3:Column {fqn: "apollo_financial.procurement.vendor_master.bank_account_no"})
SET cv3.name = "bank_account_no", cv3.data_type = "varchar(20)", cv3.is_nullable = true,
    cv3.sensitivity_level = 5, cv3.is_pii = true, cv3.pii_type = "BANK_ACCOUNT",
    cv3.masking_strategy = "HASH", cv3.is_active = true, cv3.version = 1;

MERGE (cv4:Column {fqn: "apollo_financial.procurement.vendor_master.ifsc_code"})
SET cv4.name = "ifsc_code", cv4.data_type = "varchar(11)", cv4.is_nullable = true,
    cv4.sensitivity_level = 3, cv4.is_pii = false, cv4.is_active = true, cv4.version = 1;

MERGE (cv5:Column {fqn: "apollo_financial.procurement.vendor_master.gst_number"})
SET cv5.name = "gst_number", cv5.data_type = "varchar(15)", cv5.is_nullable = true,
    cv5.sensitivity_level = 3, cv5.is_pii = true, cv5.pii_type = "TAX_ID",
    cv5.masking_strategy = "PARTIAL_MASK", cv5.is_active = true, cv5.version = 1;

MERGE (cv6:Column {fqn: "apollo_financial.procurement.vendor_master.contact_email"})
SET cv6.name = "contact_email", cv6.data_type = "varchar(255)", cv6.is_nullable = true,
    cv6.sensitivity_level = 3, cv6.is_pii = true, cv6.pii_type = "EMAIL",
    cv6.masking_strategy = "PARTIAL_MASK", cv6.is_active = true, cv6.version = 1;

MERGE (tf6)-[:HAS_COLUMN]->(cv1);
MERGE (tf6)-[:HAS_COLUMN]->(cv2);
MERGE (tf6)-[:HAS_COLUMN]->(cv3);
MERGE (tf6)-[:HAS_COLUMN]->(cv4);
MERGE (tf6)-[:HAS_COLUMN]->(cv5);
MERGE (tf6)-[:HAS_COLUMN]->(cv6);

// Column regulatory links
MERGE (cv3)-[:COLUMN_REGULATED_BY]->(r_dpdpa);
MERGE (cv5)-[:COLUMN_REGULATED_BY]->(r_dpdpa);

// --- Finance Roles ---
MERGE (r_cfo:Role {name: "cfo"})
SET r_cfo.description = "Chief Financial Officer — full financial data access",
    r_cfo.is_active = true, r_cfo.version = 1;

MERGE (r_fin_controller:Role {name: "finance_controller"})
SET r_fin_controller.description = "Finance controller — GL and budget access",
    r_fin_controller.is_active = true, r_fin_controller.version = 1;

MERGE (r_procurement:Role {name: "procurement_officer"})
SET r_procurement.description = "Procurement officer — PO and vendor management",
    r_procurement.is_active = true, r_procurement.version = 1;

MERGE (r_cfo)-[:INHERITS_FROM]->(r_fin_controller);
MERGE (r_cfo)-[:ACCESSES_DOMAIN]->(d_finance);
MERGE (r_cfo)-[:ACCESSES_DOMAIN]->(d_billing);
MERGE (r_fin_controller)-[:ACCESSES_DOMAIN]->(d_finance);
MERGE (r_procurement)-[:ACCESSES_DOMAIN]->(d_finance);

// --- Finance Policies ---
MERGE (p_fin1:Policy {policy_id: "POL-FIN-001"})
SET p_fin1.policy_type = "DENY",
    p_fin1.nl_description = "Vendor bank account numbers are restricted to CFO and finance controller only",
    p_fin1.structured_rule = '{"effect":"DENY","target":{"table":"vendor_master","columns":["bank_account_no"]},"subject":{"role":"*"},"exception":{"roles":["cfo","finance_controller"]}}',
    p_fin1.priority = 200, p_fin1.is_active = true, p_fin1.created_at = datetime(), p_fin1.version = 1;
MERGE (p_fin1)-[:GOVERNS_TABLE]->(tf6);
MERGE (p_fin1)-[:GOVERNS_COLUMN]->(cv3);

MERGE (p_fin2:Policy {policy_id: "POL-FIN-002"})
SET p_fin2.policy_type = "DENY",
    p_fin2.nl_description = "Finance domain cannot be joined with clinical patient data",
    p_fin2.structured_rule = '{"effect":"DENY","type":"JOIN_RESTRICTION","source_domain":"finance","target_domain":"clinical","subject":{"role":"*"}}',
    p_fin2.priority = 200, p_fin2.is_active = true, p_fin2.created_at = datetime(), p_fin2.version = 1;
MERGE (d_clinical:Domain {name: "clinical"});
MERGE (p_fin2)-[:RESTRICTS_JOIN {source_domain: "finance", target_domain: "clinical"}]->(d_clinical);
