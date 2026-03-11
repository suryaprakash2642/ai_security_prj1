// ============================================================
// apollo_financial — Financial & Procurement Database (AWS RDS PostgreSQL)
// Auto-generated from live crawl at 2026-03-03 19:28:09
// ============================================================

// --- Database ---
MERGE (db:Database {name: "apollo_financial"})
SET db.engine = "postgresql", db.is_active = true,
    db.created_at = datetime(), db.source = "live_crawl";

// --- Schemas ---
MERGE (s0:Schema {fqn: "apollo_financial.public"})
SET s0.name = "public", s0.is_active = true;

MERGE (db)-[:HAS_SCHEMA]->(s0);

// --- Tables ---
MERGE (t0:Table {fqn: "apollo_financial.public.claim_line_items"})
SET t0.name = "claim_line_items", t0.is_active = true,
    t0.row_count_approx = 4013,
    t0.sensitivity_level = 0, t0.has_pii = false,
    t0.domain = "billing", t0.source = "live_crawl";

MERGE (t1:Table {fqn: "apollo_financial.public.claims"})
SET t1.name = "claims", t1.is_active = true,
    t1.row_count_approx = 1200,
    t1.sensitivity_level = 0, t1.has_pii = false,
    t1.domain = "billing", t1.source = "live_crawl";

MERGE (t2:Table {fqn: "apollo_financial.public.insurance_plans"})
SET t2.name = "insurance_plans", t2.is_active = true,
    t2.row_count_approx = 0,
    t2.sensitivity_level = 0, t2.has_pii = false,
    t2.domain = "billing", t2.source = "live_crawl";

MERGE (t3:Table {fqn: "apollo_financial.public.patient_billing"})
SET t3.name = "patient_billing", t3.is_active = true,
    t3.row_count_approx = 1500,
    t3.sensitivity_level = 3, t3.has_pii = true,
    t3.domain = "clinical", t3.source = "live_crawl";

MERGE (t4:Table {fqn: "apollo_financial.public.payer_contracts"})
SET t4.name = "payer_contracts", t4.is_active = true,
    t4.row_count_approx = 0,
    t4.sensitivity_level = 0, t4.has_pii = false,
    t4.domain = "billing", t4.source = "live_crawl";

MERGE (t5:Table {fqn: "apollo_financial.public.payments"})
SET t5.name = "payments", t5.is_active = true,
    t5.row_count_approx = 1000,
    t5.sensitivity_level = 0, t5.has_pii = false,
    t5.domain = "billing", t5.source = "live_crawl";

// Schema-Table links
MERGE (s0)-[:HAS_TABLE]->(t0);
MERGE (s0)-[:HAS_TABLE]->(t1);
MERGE (s0)-[:HAS_TABLE]->(t2);
MERGE (s0)-[:HAS_TABLE]->(t3);
MERGE (s0)-[:HAS_TABLE]->(t4);
MERGE (s0)-[:HAS_TABLE]->(t5);

// --- Columns (claim_line_items) ---
MERGE (c0:Column {fqn: "apollo_financial.public.claim_line_items.line_item_id"})
SET c0.name = "line_item_id", c0.data_type = "character varying", c0.is_pk = true, c0.is_nullable = false, c0.ordinal_position = 1, c0.is_active = true;

MERGE (c1:Column {fqn: "apollo_financial.public.claim_line_items.claim_id"})
SET c1.name = "claim_id", c1.data_type = "character varying", c1.is_nullable = false, c1.ordinal_position = 2, c1.is_active = true;

MERGE (c2:Column {fqn: "apollo_financial.public.claim_line_items.service_date"})
SET c2.name = "service_date", c2.data_type = "date", c2.is_nullable = false, c2.ordinal_position = 3, c2.is_active = true;

MERGE (c3:Column {fqn: "apollo_financial.public.claim_line_items.service_code"})
SET c3.name = "service_code", c3.data_type = "character varying", c3.is_nullable = false, c3.ordinal_position = 4, c3.is_active = true;

MERGE (c4:Column {fqn: "apollo_financial.public.claim_line_items.service_description"})
SET c4.name = "service_description", c4.data_type = "character varying", c4.is_nullable = true, c4.ordinal_position = 5, c4.is_active = true;

MERGE (c5:Column {fqn: "apollo_financial.public.claim_line_items.quantity"})
SET c5.name = "quantity", c5.data_type = "integer", c5.is_nullable = true, c5.ordinal_position = 6, c5.is_active = true;

MERGE (c6:Column {fqn: "apollo_financial.public.claim_line_items.unit_charge"})
SET c6.name = "unit_charge", c6.data_type = "numeric", c6.is_nullable = false, c6.ordinal_position = 7, c6.is_active = true;

MERGE (c7:Column {fqn: "apollo_financial.public.claim_line_items.total_charge"})
SET c7.name = "total_charge", c7.data_type = "numeric", c7.is_nullable = false, c7.ordinal_position = 8, c7.is_active = true;

MERGE (c8:Column {fqn: "apollo_financial.public.claim_line_items.approved_amount"})
SET c8.name = "approved_amount", c8.data_type = "numeric", c8.is_nullable = true, c8.ordinal_position = 9, c8.is_active = true;

MERGE (c9:Column {fqn: "apollo_financial.public.claim_line_items.denial_code"})
SET c9.name = "denial_code", c9.data_type = "character varying", c9.is_nullable = true, c9.ordinal_position = 10, c9.is_active = true;

MERGE (c10:Column {fqn: "apollo_financial.public.claim_line_items.created_at"})
SET c10.name = "created_at", c10.data_type = "timestamp without time zone", c10.is_nullable = true, c10.ordinal_position = 11, c10.is_active = true;

// Column-Table links (claim_line_items)
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

// --- Columns (claims) ---
MERGE (c11:Column {fqn: "apollo_financial.public.claims.claim_id"})
SET c11.name = "claim_id", c11.data_type = "character varying", c11.is_pk = true, c11.is_nullable = false, c11.ordinal_position = 1, c11.is_active = true;

MERGE (c12:Column {fqn: "apollo_financial.public.claims.encounter_id"})
SET c12.name = "encounter_id", c12.data_type = "character varying", c12.is_nullable = false, c12.ordinal_position = 2, c12.is_active = true;

MERGE (c13:Column {fqn: "apollo_financial.public.claims.patient_id"})
SET c13.name = "patient_id", c13.data_type = "character varying", c13.is_nullable = false, c13.ordinal_position = 3, c13.is_active = true;

MERGE (c14:Column {fqn: "apollo_financial.public.claims.payer_id"})
SET c14.name = "payer_id", c14.data_type = "character varying", c14.is_nullable = false, c14.ordinal_position = 4, c14.is_active = true;

MERGE (c15:Column {fqn: "apollo_financial.public.claims.insurance_plan_id"})
SET c15.name = "insurance_plan_id", c15.data_type = "character varying", c15.is_nullable = true, c15.ordinal_position = 5, c15.is_active = true;

MERGE (c16:Column {fqn: "apollo_financial.public.claims.claim_date"})
SET c16.name = "claim_date", c16.data_type = "date", c16.is_nullable = false, c16.ordinal_position = 6, c16.is_active = true;

MERGE (c17:Column {fqn: "apollo_financial.public.claims.claim_type"})
SET c17.name = "claim_type", c17.data_type = "character varying", c17.is_nullable = true, c17.ordinal_position = 7, c17.is_active = true;

MERGE (c18:Column {fqn: "apollo_financial.public.claims.total_amount"})
SET c18.name = "total_amount", c18.data_type = "numeric", c18.is_nullable = false, c18.ordinal_position = 8, c18.is_active = true;

MERGE (c19:Column {fqn: "apollo_financial.public.claims.approved_amount"})
SET c19.name = "approved_amount", c19.data_type = "numeric", c19.is_nullable = true, c19.ordinal_position = 9, c19.is_active = true;

MERGE (c20:Column {fqn: "apollo_financial.public.claims.denied_amount"})
SET c20.name = "denied_amount", c20.data_type = "numeric", c20.is_nullable = true, c20.ordinal_position = 10, c20.is_active = true;

MERGE (c21:Column {fqn: "apollo_financial.public.claims.adjustment_amount"})
SET c21.name = "adjustment_amount", c21.data_type = "numeric", c21.is_nullable = true, c21.ordinal_position = 11, c21.is_active = true;

MERGE (c22:Column {fqn: "apollo_financial.public.claims.primary_dx_code"})
SET c22.name = "primary_dx_code", c22.data_type = "character varying", c22.is_nullable = true, c22.ordinal_position = 12, c22.is_active = true;

MERGE (c23:Column {fqn: "apollo_financial.public.claims.procedure_codes"})
SET c23.name = "procedure_codes", c23.data_type = "character varying", c23.is_nullable = true, c23.ordinal_position = 13, c23.is_active = true;

MERGE (c24:Column {fqn: "apollo_financial.public.claims.claim_status"})
SET c24.name = "claim_status", c24.data_type = "character varying", c24.is_nullable = true, c24.ordinal_position = 14, c24.is_active = true;

MERGE (c25:Column {fqn: "apollo_financial.public.claims.denial_reason"})
SET c25.name = "denial_reason", c25.data_type = "character varying", c25.is_nullable = true, c25.ordinal_position = 15, c25.is_active = true;

MERGE (c26:Column {fqn: "apollo_financial.public.claims.submitted_date"})
SET c26.name = "submitted_date", c26.data_type = "date", c26.is_nullable = true, c26.ordinal_position = 16, c26.is_active = true;

MERGE (c27:Column {fqn: "apollo_financial.public.claims.adjudicated_date"})
SET c27.name = "adjudicated_date", c27.data_type = "date", c27.is_nullable = true, c27.ordinal_position = 17, c27.is_active = true;

MERGE (c28:Column {fqn: "apollo_financial.public.claims.payment_date"})
SET c28.name = "payment_date", c28.data_type = "date", c28.is_nullable = true, c28.ordinal_position = 18, c28.is_active = true;

MERGE (c29:Column {fqn: "apollo_financial.public.claims.created_at"})
SET c29.name = "created_at", c29.data_type = "timestamp without time zone", c29.is_nullable = true, c29.ordinal_position = 19, c29.is_active = true;

// Column-Table links (claims)
MERGE (t1)-[:HAS_COLUMN]->(c11);
MERGE (t1)-[:HAS_COLUMN]->(c12);
MERGE (t1)-[:HAS_COLUMN]->(c13);
MERGE (t1)-[:HAS_COLUMN]->(c14);
MERGE (t1)-[:HAS_COLUMN]->(c15);
MERGE (t1)-[:HAS_COLUMN]->(c16);
MERGE (t1)-[:HAS_COLUMN]->(c17);
MERGE (t1)-[:HAS_COLUMN]->(c18);
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

// --- Columns (insurance_plans) ---
MERGE (c30:Column {fqn: "apollo_financial.public.insurance_plans.plan_id"})
SET c30.name = "plan_id", c30.data_type = "character varying", c30.is_pk = true, c30.is_nullable = false, c30.ordinal_position = 1, c30.is_active = true;

MERGE (c31:Column {fqn: "apollo_financial.public.insurance_plans.payer_id"})
SET c31.name = "payer_id", c31.data_type = "character varying", c31.is_nullable = false, c31.ordinal_position = 2, c31.is_active = true;

MERGE (c32:Column {fqn: "apollo_financial.public.insurance_plans.payer_name"})
SET c32.name = "payer_name", c32.data_type = "character varying", c32.is_nullable = false, c32.ordinal_position = 3, c32.is_active = true;

MERGE (c33:Column {fqn: "apollo_financial.public.insurance_plans.plan_name"})
SET c33.name = "plan_name", c33.data_type = "character varying", c33.is_nullable = false, c33.ordinal_position = 4, c33.is_active = true;

MERGE (c34:Column {fqn: "apollo_financial.public.insurance_plans.plan_type"})
SET c34.name = "plan_type", c34.data_type = "character varying", c34.is_nullable = true, c34.ordinal_position = 5, c34.is_active = true;

MERGE (c35:Column {fqn: "apollo_financial.public.insurance_plans.coverage_type"})
SET c35.name = "coverage_type", c35.data_type = "character varying", c35.is_nullable = true, c35.ordinal_position = 6, c35.is_active = true;

MERGE (c36:Column {fqn: "apollo_financial.public.insurance_plans.annual_limit"})
SET c36.name = "annual_limit", c36.data_type = "numeric", c36.is_nullable = true, c36.ordinal_position = 7, c36.is_active = true;

MERGE (c37:Column {fqn: "apollo_financial.public.insurance_plans.room_rent_limit"})
SET c37.name = "room_rent_limit", c37.data_type = "numeric", c37.is_nullable = true, c37.ordinal_position = 8, c37.is_active = true;

MERGE (c38:Column {fqn: "apollo_financial.public.insurance_plans.copay_percent"})
SET c38.name = "copay_percent", c38.data_type = "numeric", c38.is_nullable = true, c38.ordinal_position = 9, c38.is_active = true;

MERGE (c39:Column {fqn: "apollo_financial.public.insurance_plans.network_type"})
SET c39.name = "network_type", c39.data_type = "character varying", c39.is_nullable = true, c39.ordinal_position = 10, c39.is_active = true;

MERGE (c40:Column {fqn: "apollo_financial.public.insurance_plans.is_active"})
SET c40.name = "is_active", c40.data_type = "smallint", c40.is_nullable = true, c40.ordinal_position = 11, c40.is_active = true;

MERGE (c41:Column {fqn: "apollo_financial.public.insurance_plans.created_at"})
SET c41.name = "created_at", c41.data_type = "timestamp without time zone", c41.is_nullable = true, c41.ordinal_position = 12, c41.is_active = true;

// Column-Table links (insurance_plans)
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

// --- Columns (patient_billing) ---
MERGE (c42:Column {fqn: "apollo_financial.public.patient_billing.billing_id"})
SET c42.name = "billing_id", c42.data_type = "character varying", c42.is_pk = true, c42.is_nullable = false, c42.ordinal_position = 1, c42.sensitivity_level = 3, c42.is_pii = true, c42.pii_type = "CLINICAL_CONTEXT", c42.masking_strategy = "REVIEW", c42.is_active = true;

MERGE (c43:Column {fqn: "apollo_financial.public.patient_billing.patient_id"})
SET c43.name = "patient_id", c43.data_type = "character varying", c43.is_nullable = false, c43.ordinal_position = 2, c43.sensitivity_level = 3, c43.is_pii = true, c43.pii_type = "CLINICAL_CONTEXT", c43.masking_strategy = "REVIEW", c43.is_active = true;

MERGE (c44:Column {fqn: "apollo_financial.public.patient_billing.encounter_id"})
SET c44.name = "encounter_id", c44.data_type = "character varying", c44.is_nullable = false, c44.ordinal_position = 3, c44.sensitivity_level = 3, c44.is_pii = true, c44.pii_type = "CLINICAL_CONTEXT", c44.masking_strategy = "REVIEW", c44.is_active = true;

MERGE (c45:Column {fqn: "apollo_financial.public.patient_billing.insurance_plan_id"})
SET c45.name = "insurance_plan_id", c45.data_type = "character varying", c45.is_nullable = true, c45.ordinal_position = 4, c45.sensitivity_level = 3, c45.is_pii = true, c45.pii_type = "CLINICAL_CONTEXT", c45.masking_strategy = "REVIEW", c45.is_active = true;

MERGE (c46:Column {fqn: "apollo_financial.public.patient_billing.billing_date"})
SET c46.name = "billing_date", c46.data_type = "date", c46.is_nullable = false, c46.ordinal_position = 5, c46.sensitivity_level = 3, c46.is_pii = true, c46.pii_type = "CLINICAL_CONTEXT", c46.masking_strategy = "REVIEW", c46.is_active = true;

MERGE (c47:Column {fqn: "apollo_financial.public.patient_billing.total_charges"})
SET c47.name = "total_charges", c47.data_type = "numeric", c47.is_nullable = false, c47.ordinal_position = 6, c47.sensitivity_level = 3, c47.is_pii = true, c47.pii_type = "CLINICAL_CONTEXT", c47.masking_strategy = "REVIEW", c47.is_active = true;

MERGE (c48:Column {fqn: "apollo_financial.public.patient_billing.insurance_covered"})
SET c48.name = "insurance_covered", c48.data_type = "numeric", c48.is_nullable = true, c48.ordinal_position = 7, c48.sensitivity_level = 3, c48.is_pii = true, c48.pii_type = "CLINICAL_CONTEXT", c48.masking_strategy = "REVIEW", c48.is_active = true;

MERGE (c49:Column {fqn: "apollo_financial.public.patient_billing.patient_copay"})
SET c49.name = "patient_copay", c49.data_type = "numeric", c49.is_nullable = true, c49.ordinal_position = 8, c49.sensitivity_level = 3, c49.is_pii = true, c49.pii_type = "CLINICAL_CONTEXT", c49.masking_strategy = "REVIEW", c49.is_active = true;

MERGE (c50:Column {fqn: "apollo_financial.public.patient_billing.discount_amount"})
SET c50.name = "discount_amount", c50.data_type = "numeric", c50.is_nullable = true, c50.ordinal_position = 9, c50.sensitivity_level = 3, c50.is_pii = true, c50.pii_type = "CLINICAL_CONTEXT", c50.masking_strategy = "REVIEW", c50.is_active = true;

MERGE (c51:Column {fqn: "apollo_financial.public.patient_billing.net_amount"})
SET c51.name = "net_amount", c51.data_type = "numeric", c51.is_nullable = false, c51.ordinal_position = 10, c51.sensitivity_level = 3, c51.is_pii = true, c51.pii_type = "CLINICAL_CONTEXT", c51.masking_strategy = "REVIEW", c51.is_active = true;

MERGE (c52:Column {fqn: "apollo_financial.public.patient_billing.amount_paid"})
SET c52.name = "amount_paid", c52.data_type = "numeric", c52.is_nullable = true, c52.ordinal_position = 11, c52.sensitivity_level = 3, c52.is_pii = true, c52.pii_type = "CLINICAL_CONTEXT", c52.masking_strategy = "REVIEW", c52.is_active = true;

MERGE (c53:Column {fqn: "apollo_financial.public.patient_billing.balance_due"})
SET c53.name = "balance_due", c53.data_type = "numeric", c53.is_nullable = true, c53.ordinal_position = 12, c53.sensitivity_level = 3, c53.is_pii = true, c53.pii_type = "CLINICAL_CONTEXT", c53.masking_strategy = "REVIEW", c53.is_active = true;

MERGE (c54:Column {fqn: "apollo_financial.public.patient_billing.billing_status"})
SET c54.name = "billing_status", c54.data_type = "character varying", c54.is_nullable = true, c54.ordinal_position = 13, c54.sensitivity_level = 3, c54.is_pii = true, c54.pii_type = "CLINICAL_CONTEXT", c54.masking_strategy = "REVIEW", c54.is_active = true;

MERGE (c55:Column {fqn: "apollo_financial.public.patient_billing.payment_method"})
SET c55.name = "payment_method", c55.data_type = "character varying", c55.is_nullable = true, c55.ordinal_position = 14, c55.sensitivity_level = 3, c55.is_pii = true, c55.pii_type = "CLINICAL_CONTEXT", c55.masking_strategy = "REVIEW", c55.is_active = true;

MERGE (c56:Column {fqn: "apollo_financial.public.patient_billing.created_at"})
SET c56.name = "created_at", c56.data_type = "timestamp without time zone", c56.is_nullable = true, c56.ordinal_position = 15, c56.sensitivity_level = 3, c56.is_pii = true, c56.pii_type = "CLINICAL_CONTEXT", c56.masking_strategy = "REVIEW", c56.is_active = true;

// Column-Table links (patient_billing)
MERGE (t3)-[:HAS_COLUMN]->(c42);
MERGE (t3)-[:HAS_COLUMN]->(c43);
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
MERGE (t3)-[:HAS_COLUMN]->(c54);
MERGE (t3)-[:HAS_COLUMN]->(c55);
MERGE (t3)-[:HAS_COLUMN]->(c56);

// --- Columns (payer_contracts) ---
MERGE (c57:Column {fqn: "apollo_financial.public.payer_contracts.contract_id"})
SET c57.name = "contract_id", c57.data_type = "character varying", c57.is_pk = true, c57.is_nullable = false, c57.ordinal_position = 1, c57.is_active = true;

MERGE (c58:Column {fqn: "apollo_financial.public.payer_contracts.payer_id"})
SET c58.name = "payer_id", c58.data_type = "character varying", c58.is_nullable = false, c58.ordinal_position = 2, c58.is_active = true;

MERGE (c59:Column {fqn: "apollo_financial.public.payer_contracts.payer_name"})
SET c59.name = "payer_name", c59.data_type = "character varying", c59.is_nullable = false, c59.ordinal_position = 3, c59.is_active = true;

MERGE (c60:Column {fqn: "apollo_financial.public.payer_contracts.contract_start_date"})
SET c60.name = "contract_start_date", c60.data_type = "date", c60.is_nullable = false, c60.ordinal_position = 4, c60.is_active = true;

MERGE (c61:Column {fqn: "apollo_financial.public.payer_contracts.contract_end_date"})
SET c61.name = "contract_end_date", c61.data_type = "date", c61.is_nullable = false, c61.ordinal_position = 5, c61.is_active = true;

MERGE (c62:Column {fqn: "apollo_financial.public.payer_contracts.discount_percent"})
SET c62.name = "discount_percent", c62.data_type = "numeric", c62.is_nullable = true, c62.ordinal_position = 6, c62.is_active = true;

MERGE (c63:Column {fqn: "apollo_financial.public.payer_contracts.payment_terms_days"})
SET c63.name = "payment_terms_days", c63.data_type = "integer", c63.is_nullable = true, c63.ordinal_position = 7, c63.is_active = true;

MERGE (c64:Column {fqn: "apollo_financial.public.payer_contracts.auto_approval_limit"})
SET c64.name = "auto_approval_limit", c64.data_type = "numeric", c64.is_nullable = true, c64.ordinal_position = 8, c64.is_active = true;

MERGE (c65:Column {fqn: "apollo_financial.public.payer_contracts.requires_preauth"})
SET c65.name = "requires_preauth", c65.data_type = "smallint", c65.is_nullable = true, c65.ordinal_position = 9, c65.is_active = true;

MERGE (c66:Column {fqn: "apollo_financial.public.payer_contracts.contract_type"})
SET c66.name = "contract_type", c66.data_type = "character varying", c66.is_nullable = true, c66.ordinal_position = 10, c66.is_active = true;

MERGE (c67:Column {fqn: "apollo_financial.public.payer_contracts.is_active"})
SET c67.name = "is_active", c67.data_type = "smallint", c67.is_nullable = true, c67.ordinal_position = 11, c67.is_active = true;

MERGE (c68:Column {fqn: "apollo_financial.public.payer_contracts.created_at"})
SET c68.name = "created_at", c68.data_type = "timestamp without time zone", c68.is_nullable = true, c68.ordinal_position = 12, c68.is_active = true;

// Column-Table links (payer_contracts)
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

// --- Columns (payments) ---
MERGE (c69:Column {fqn: "apollo_financial.public.payments.payment_id"})
SET c69.name = "payment_id", c69.data_type = "character varying", c69.is_pk = true, c69.is_nullable = false, c69.ordinal_position = 1, c69.is_active = true;

MERGE (c70:Column {fqn: "apollo_financial.public.payments.claim_id"})
SET c70.name = "claim_id", c70.data_type = "character varying", c70.is_nullable = true, c70.ordinal_position = 2, c70.is_active = true;

MERGE (c71:Column {fqn: "apollo_financial.public.payments.billing_id"})
SET c71.name = "billing_id", c71.data_type = "character varying", c71.is_nullable = true, c71.ordinal_position = 3, c71.is_active = true;

MERGE (c72:Column {fqn: "apollo_financial.public.payments.payment_date"})
SET c72.name = "payment_date", c72.data_type = "date", c72.is_nullable = false, c72.ordinal_position = 4, c72.is_active = true;

MERGE (c73:Column {fqn: "apollo_financial.public.payments.payment_amount"})
SET c73.name = "payment_amount", c73.data_type = "numeric", c73.is_nullable = false, c73.ordinal_position = 5, c73.is_active = true;

MERGE (c74:Column {fqn: "apollo_financial.public.payments.payment_source"})
SET c74.name = "payment_source", c74.data_type = "character varying", c74.is_nullable = true, c74.ordinal_position = 6, c74.is_active = true;

MERGE (c75:Column {fqn: "apollo_financial.public.payments.payment_method"})
SET c75.name = "payment_method", c75.data_type = "character varying", c75.is_nullable = true, c75.ordinal_position = 7, c75.is_active = true;

MERGE (c76:Column {fqn: "apollo_financial.public.payments.reference_number"})
SET c76.name = "reference_number", c76.data_type = "character varying", c76.is_nullable = true, c76.ordinal_position = 8, c76.is_active = true;

MERGE (c77:Column {fqn: "apollo_financial.public.payments.utr_number"})
SET c77.name = "utr_number", c77.data_type = "character varying", c77.is_nullable = true, c77.ordinal_position = 9, c77.is_active = true;

MERGE (c78:Column {fqn: "apollo_financial.public.payments.payment_status"})
SET c78.name = "payment_status", c78.data_type = "character varying", c78.is_nullable = true, c78.ordinal_position = 10, c78.is_active = true;

MERGE (c79:Column {fqn: "apollo_financial.public.payments.created_at"})
SET c79.name = "created_at", c79.data_type = "timestamp without time zone", c79.is_nullable = true, c79.ordinal_position = 11, c79.is_active = true;

// Column-Table links (payments)
MERGE (t5)-[:HAS_COLUMN]->(c69);
MERGE (t5)-[:HAS_COLUMN]->(c70);
MERGE (t5)-[:HAS_COLUMN]->(c71);
MERGE (t5)-[:HAS_COLUMN]->(c72);
MERGE (t5)-[:HAS_COLUMN]->(c73);
MERGE (t5)-[:HAS_COLUMN]->(c74);
MERGE (t5)-[:HAS_COLUMN]->(c75);
MERGE (t5)-[:HAS_COLUMN]->(c76);
MERGE (t5)-[:HAS_COLUMN]->(c77);
MERGE (t5)-[:HAS_COLUMN]->(c78);
MERGE (t5)-[:HAS_COLUMN]->(c79);

// --- Foreign Keys ---
MERGE (c1)-[:FOREIGN_KEY_TO {constraint: "claim_line_items_claim_id_fkey"}]->(c11);
MERGE (c15)-[:FOREIGN_KEY_TO {constraint: "claims_insurance_plan_id_fkey"}]->(c30);
MERGE (c45)-[:FOREIGN_KEY_TO {constraint: "patient_billing_insurance_plan_id_fkey"}]->(c30);
MERGE (c70)-[:FOREIGN_KEY_TO {constraint: "payments_claim_id_fkey"}]->(c11);
MERGE (c71)-[:FOREIGN_KEY_TO {constraint: "payments_billing_id_fkey"}]->(c42);

// --- Domains ---
MERGE (dom_billing:Domain {name: "billing"});
MERGE (dom_clinical:Domain {name: "clinical"});

// Domain-Table links
MERGE (t0)-[:BELONGS_TO_DOMAIN]->(dom_billing);
MERGE (t1)-[:BELONGS_TO_DOMAIN]->(dom_billing);
MERGE (t2)-[:BELONGS_TO_DOMAIN]->(dom_billing);
MERGE (t3)-[:BELONGS_TO_DOMAIN]->(dom_clinical);
MERGE (t4)-[:BELONGS_TO_DOMAIN]->(dom_billing);
MERGE (t5)-[:BELONGS_TO_DOMAIN]->(dom_billing);
