// ============================================================
// 011_spec_policy_alignment.cypher
// Aligns ALL policies with Policy-Resolution-Layer-Specification
// (XENDEX-ZT-L4-SPEC-001)
//
// This script:
//   1. Deletes all existing Policy + Condition nodes & relationships
//   2. Fixes table domain misclassifications
//   3. Creates spec-aligned policies (Section 11)
//   4. Creates conditions (row filters, join restrictions, etc.)
//   5. Wires APPLIES_TO_ROLE, GOVERNS_DOMAIN, GOVERNS_TABLE, HAS_CONDITION
//   6. Updates ACCESSES_DOMAIN for each role
// ============================================================


// ── 1. CLEAN SLATE ──────────────────────────────────────────

// Delete all Condition nodes and their relationships
MATCH (c:Condition) DETACH DELETE c;

// Delete all Policy nodes and their relationships
MATCH (p:Policy) DETACH DELETE p;


// ── 2. FIX TABLE DOMAIN ASSIGNMENTS ─────────────────────────

// allergies is clinical data (patient allergy records), not general
MATCH (t:Table {table_id: "ApolloHIS.ApolloHIS.allergies"})-[r:BELONGS_TO_DOMAIN]->(:Domain {name: "general"})
DELETE r;
MATCH (t:Table {table_id: "ApolloHIS.ApolloHIS.allergies"}), (d:Domain {name: "clinical"})
MERGE (t)-[:BELONGS_TO_DOMAIN]->(d);

// clinical_notes is clinical data, not general
MATCH (t:Table {table_id: "ApolloHIS.ApolloHIS.clinical_notes"})-[r:BELONGS_TO_DOMAIN]->(:Domain {name: "general"})
DELETE r;
MATCH (t:Table {table_id: "ApolloHIS.ApolloHIS.clinical_notes"}), (d:Domain {name: "clinical"})
MERGE (t)-[:BELONGS_TO_DOMAIN]->(d);

// population_health → analytics (not general)
MATCH (t:Table {table_id: "apollo_analytics.public.population_health"})-[r:BELONGS_TO_DOMAIN]->(:Domain {name: "general"})
DELETE r;
MATCH (t:Table {table_id: "apollo_analytics.public.population_health"}), (d:Domain {name: "analytics"})
MERGE (t)-[:BELONGS_TO_DOMAIN]->(d);

// research_cohorts → analytics (not general)
MATCH (t:Table {table_id: "apollo_analytics.public.research_cohorts"})-[r:BELONGS_TO_DOMAIN]->(:Domain {name: "general"})
DELETE r;
MATCH (t:Table {table_id: "apollo_analytics.public.research_cohorts"}), (d:Domain {name: "analytics"})
MERGE (t)-[:BELONGS_TO_DOMAIN]->(d);

// Update allergies sensitivity to 3 (was 4, clinical data but not top-secret)
MATCH (t:Table {table_id: "ApolloHIS.ApolloHIS.allergies"})
SET t.sensitivity_level = 3;


// ── 3. CREATE SPEC-ALIGNED POLICIES ─────────────────────────

// ── Federal Regulatory (Priority 200) ──

// FED-001: 42 CFR Part 2 — Substance Abuse Records HARD DENY
// Spec §11.1: Applies to ALL roles. Exception: NONE_VIA_QUERY_SYSTEM
CREATE (p:Policy {
  policy_id: "FED-001",
  name: "42 CFR Part 2 Substance Abuse Protection",
  effect: "DENY",
  priority: 200,
  is_active: true,
  regulation: "42_CFR_PART_2",
  nl_description: "Substance abuse treatment records are PERMANENTLY DENIED for ALL roles via the NL-to-SQL query system per 42 CFR Part 2. These records require explicit written patient consent per disclosure. No break-the-glass override.",
  structured_rule: '{"type":"TABLE_DENY","tables":["substance_abuse_records","behavioral_health_substance","42cfr_part2"],"exception":"NONE_VIA_QUERY_SYSTEM"}'
});

// HIPAA-005: Psychotherapy Notes Protection
// Spec §11.1: Exception: AUTHORING_PROVIDER_ONLY (via separate EMR module)
CREATE (p:Policy {
  policy_id: "HIPAA-005",
  name: "Psychotherapy Notes Protection",
  effect: "DENY",
  priority: 200,
  is_active: true,
  regulation: "HIPAA",
  nl_description: "Psychotherapy notes are DENIED for all roles via NL-to-SQL. These require separate authorization from general PHI disclosures. Access only via dedicated EMR module for the authoring provider.",
  structured_rule: '{"type":"TABLE_DENY","tables":["mental_health_records"],"filter":"note_type = PSYCHOTHERAPY","exception":"AUTHORING_PROVIDER_ONLY"}'
});


// ── Security Boundary (Priority 140–160) ──

// SEC-001: No Clinical-HR Cross Join
// Spec §11.2: Prevents correlation of patient outcomes with staff performance
CREATE (p:Policy {
  policy_id: "SEC-001",
  name: "No Clinical-HR Cross Join",
  effect: "DENY",
  priority: 150,
  is_active: true,
  nl_description: "Do NOT join clinical tables (encounters, patients, prescriptions, lab_results, vital_signs, clinical_notes) with HR tables (employees, payroll, leave_records, credentials). This prevents correlation of patient outcomes with staff performance.",
  structured_rule: '{"type":"JOIN_RESTRICTION","from_domain":"clinical","to_domain":"hr","exception":"NONE"}'
});

// SEC-002: No Payer Contract-Salary Cross Join
// Spec §11.2: Prevents exposure of negotiated rates alongside compensation
CREATE (p:Policy {
  policy_id: "SEC-002",
  name: "No Payer Contract-Salary Cross Join",
  effect: "DENY",
  priority: 150,
  is_active: true,
  nl_description: "Do NOT join payer contract tables (payer_contracts, insurance_plans) with HR compensation tables (payroll, employees). This prevents exposure of negotiated rates alongside staff compensation.",
  structured_rule: '{"type":"JOIN_RESTRICTION","from_tables":["payer_contracts","insurance_plans"],"to_domain":"hr","exception":"NONE"}'
});

// SEC-003: No Genetic-Insurance Cross Join
// Spec §11.2: GINA compliance
CREATE (p:Policy {
  policy_id: "SEC-003",
  name: "No Genetic-Insurance Cross Join",
  effect: "DENY",
  priority: 150,
  is_active: true,
  nl_description: "Do NOT join genetic or genomic data with billing or insurance tables. GINA (Genetic Information Nondiscrimination Act) prohibits use of genetic information in insurance decisions.",
  structured_rule: '{"type":"JOIN_RESTRICTION","from_tables":["genetic_records"],"to_domain":"billing","exception":"NONE"}'
});


// ── HIPAA Compliance (Priority 80–100) ──

// HIPAA-001: Minimum Necessary Standard
// Spec §11.3: Must have WHERE clause, max 1000 unbounded rows, all roles
CREATE (p:Policy {
  policy_id: "HIPAA-001",
  name: "Minimum Necessary Standard",
  effect: "FILTER",
  priority: 100,
  is_active: true,
  regulation: "HIPAA",
  nl_description: "All queries MUST include a WHERE clause to limit scope. Unbounded queries are limited to a maximum of 1000 rows. This enforces the HIPAA minimum necessary standard.",
  structured_rule: '{"type":"QUERY_SCOPE","max_rows":1000,"require_where":true}'
});

// CLIN-001: Treatment Relationship Required
// Spec §11.3: ROW_FILTER on encounters, clinical_notes, vital_signs, lab_results
// for doctors and nurses
CREATE (p:Policy {
  policy_id: "CLIN-001",
  name: "Treatment Relationship Required",
  effect: "FILTER",
  priority: 90,
  is_active: true,
  regulation: "HIPAA",
  nl_description: "Filter encounters, clinical_notes, vital_signs, and lab_results to only include rows where treating_provider_id matches the current user OR unit_id matches the user's assigned unit. Physicians and nurses may only access records for patients in their care.",
  structured_rule: '{"type":"ROW_FILTER","tables":["encounters","clinical_notes","vital_signs","lab_results"],"filter":"treating_provider_id = {{user.provider_id}} OR unit_id = {{user.unit_id}}"}'
});

// HIPAA-003: SSN Protection
// Spec §11.3: Column MASK on patients.ssn, employees.ssn — FULL for ALL roles
CREATE (p:Policy {
  policy_id: "HIPAA-003",
  name: "SSN Protection",
  effect: "MASK",
  priority: 90,
  is_active: true,
  regulation: "HIPAA",
  nl_description: "Patient SSN (social security number) and employee SSN must NEVER be displayed. Always mask SSN columns completely. Use '***-**-XXXX' format if partial display is needed.",
  structured_rule: '{"type":"COLUMN_MASK","columns":{"patients.ssn":"FULL","employees.ssn":"FULL"},"mask_format":"***-**-XXXX"}'
});

// HIPAA-004: PII Default Masking
// Spec §11.3: Phone: LAST_4, Email: PARTIAL, Address: REDACT, DOB: YEAR_ONLY (non-clinical)
CREATE (p:Policy {
  policy_id: "HIPAA-004",
  name: "PII Default Masking",
  effect: "MASK",
  priority: 80,
  is_active: true,
  regulation: "HIPAA",
  nl_description: "When selecting PII columns, apply default masking: phone numbers show last 4 digits only, email addresses show partial (first character + domain), physical addresses are fully redacted, date of birth shows year only for non-clinical roles.",
  structured_rule: '{"type":"COLUMN_MASK","strategies":{"phone":"LAST_4","email":"PARTIAL","address":"REDACT","dob":"YEAR_ONLY"},"scope":"non_clinical_roles"}'
});


// ── Role-Based Access (Priority 40–70) ──

// CLIN-100: Doctor Full Clinical Access
// Not in spec as a named policy, but implied by Scenario 1 (§12)
// Doctors need a base ALLOW for clinical tables; CLIN-001 adds row filters on top
CREATE (p:Policy {
  policy_id: "CLIN-100",
  name: "Doctor Clinical Data Access",
  effect: "ALLOW",
  priority: 60,
  is_active: true,
  nl_description: "Attending physicians may access clinical patient data including encounters, patients, prescriptions, vital signs, lab results, clinical notes, allergies, and encounter summaries for treatment purposes. SSN and other PII columns are subject to masking policies.",
  structured_rule: '{"type":"TABLE_ALLOW","tables":["encounters","patients","prescriptions","vital_signs","lab_results","clinical_notes","allergies","encounter_summaries"],"columns":"*"}'
});

// NURSE-100: Nurse Clinical Access
// Implied by spec role hierarchy — nurses get clinical access with PII masking (POL-002)
CREATE (p:Policy {
  policy_id: "NURSE-100",
  name: "Nurse Clinical Data Access",
  effect: "ALLOW",
  priority: 50,
  is_active: true,
  nl_description: "Registered nurses may access clinical patient data including encounters, patients, vital signs, prescriptions, allergies, and clinical notes within their assigned unit. PII columns are masked per HIPAA-004. Patient identifiers (mrn, full_name, aadhaar_number) are partially masked.",
  structured_rule: '{"type":"TABLE_ALLOW","tables":["encounters","patients","vital_signs","prescriptions","allergies","clinical_notes"],"column_overrides":{"patients":["mrn","full_name","dob","room_number","unit_id","allergies"]}}'
});

// BIZ-001: Billing Minimum Clinical Access
// Spec §11.4: Specific columns on patients/encounters + all on claims/patient_billing
CREATE (p:Policy {
  policy_id: "BIZ-001",
  name: "Billing Minimum Clinical Access",
  effect: "ALLOW",
  priority: 50,
  is_active: true,
  nl_description: "Billing staff can access patient demographics (mrn, full_name, dob, insurance_id, insurance_group) and encounter codes (encounter_id, mrn, date_of_service, discharge_date, facility_id) for claims processing. Full access to claims and patient_billing tables. Billing staff CANNOT access clinical_notes, vital_signs, lab_results, prescriptions, or imaging_results.",
  structured_rule: '{"type":"COLUMN_ALLOW","tables":{"patients":["mrn","full_name","dob","insurance_id","insurance_group"],"encounters":["encounter_id","mrn","date_of_service","discharge_date","facility_id"],"claims":["*"],"claim_line_items":["*"],"patient_billing":["*"],"payments":["*"],"insurance_plans":["*"]},"denied_tables":["clinical_notes","vital_signs","lab_results","prescriptions","imaging_results"]}'
});

// CLIN-005: Pharmacist Medication Access
// Spec §11.4: prescriptions, dispensing_records, drug_interactions, controlled_substances,
// medication_inventory, allergies, patients(mrn, full_name, dob)
CREATE (p:Policy {
  policy_id: "CLIN-005",
  name: "Pharmacist Medication Access",
  effect: "ALLOW",
  priority: 50,
  is_active: true,
  nl_description: "Pharmacists can access prescription records, dispensing records, drug interactions, controlled substances, medication inventory, and patient allergies. Patient access is limited to mrn, full_name, and dob. Pharmacists CANNOT access clinical notes, lab results, vital signs, or billing data.",
  structured_rule: '{"type":"TABLE_ALLOW","tables":["prescriptions","allergies"],"column_overrides":{"patients":["mrn","full_name","dob"]},"denied_tables":["clinical_notes","lab_results","vital_signs","encounters"]}'
});

// BIZ-010: Revenue Cycle Aggregate Only
// Spec §11.4 + Scenario 3 (§12): AGGREGATION_ONLY on encounters, claims, payments
CREATE (p:Policy {
  policy_id: "BIZ-010",
  name: "Revenue Cycle Aggregate Only",
  effect: "ALLOW",
  priority: 50,
  is_active: true,
  nl_description: "Revenue Cycle Manager access to encounters, claims, and payments requires aggregate functions (COUNT, SUM, AVG, etc.) with GROUP BY. Results must be summary-level only. Individual patient records must NEVER appear in results. Do NOT include mrn, full_name, ssn, or dob in SELECT.",
  structured_rule: '{"type":"AGGREGATION_ONLY","tables":["encounters","claims","payments"],"require_group_by":true,"denied_in_select":["mrn","full_name","ssn","dob"]}'
});


// ── Custom Policies for Extended Roles ──

// HR-001: HR Manager/Director Access
CREATE (p:Policy {
  policy_id: "HR-001",
  name: "HR Staff Domain Access",
  effect: "ALLOW",
  priority: 50,
  is_active: true,
  nl_description: "HR managers and directors can access all HR domain tables including employees, payroll, leave records, certifications, credentials, and departments. SSN and sensitive compensation details are subject to masking policies.",
  structured_rule: '{"type":"TABLE_ALLOW","domain":"hr","tables":["employees","payroll","leave_records","certifications","credentials","departments"],"columns":"*"}'
});

// ADMIN-001: Hospital Admin Infrastructure Access
// Admins get analytics, general reference, and HR — NOT clinical
CREATE (p:Policy {
  policy_id: "ADMIN-001",
  name: "Hospital Admin Infrastructure Access",
  effect: "ALLOW",
  priority: 50,
  is_active: true,
  nl_description: "Hospital administrators can access analytics dashboards (quality_metrics, encounter_summaries, population_health), general reference data (facilities, units, departments, appointments, staff_schedules), and HR records. Administrators CANNOT access clinical patient data directly.",
  structured_rule: '{"type":"TABLE_ALLOW","domains":["analytics","general","hr"],"columns":"*"}'
});

// ADMIN-DENY-CLIN: Hospital Admin Clinical Data Deny
// Safety net — admins should not access clinical data
CREATE (p:Policy {
  policy_id: "ADMIN-DENY-CLIN",
  name: "Hospital Admin Clinical Data Deny",
  effect: "DENY",
  priority: 200,
  is_active: true,
  nl_description: "Hospital administrators cannot access clinical patient data (encounters, patients, prescriptions, vital_signs, lab_results, clinical_notes, allergies) via the NL-to-SQL query system.",
  structured_rule: '{"type":"TABLE_DENY","domain":"clinical","subject":{"role":"hospital_admin"}}'
});

// REVENUE-DENY-CLIN: Revenue Manager Clinical Data Deny
// Safety net for clinical tables NOT covered by BIZ-010 aggregate-only
CREATE (p:Policy {
  policy_id: "REVENUE-DENY-CLIN",
  name: "Revenue Manager Non-Aggregate Clinical Deny",
  effect: "DENY",
  priority: 160,
  is_active: true,
  nl_description: "Revenue managers cannot directly access clinical patient data. Access to encounters is aggregate-only via BIZ-010. All other clinical tables (patients, prescriptions, vital_signs, lab_results, clinical_notes, allergies) are denied.",
  structured_rule: '{"type":"TABLE_DENY","domain":"clinical","exception":{"tables":["encounters"],"condition":"AGGREGATION_ONLY"}}'
});

// RES-001: Researcher Aggregation-Only Clinical Access
CREATE (p:Policy {
  policy_id: "RES-001",
  name: "Researcher Aggregation-Only Clinical Access",
  effect: "ALLOW",
  priority: 50,
  is_active: true,
  nl_description: "Clinical researchers can access clinical data only in aggregated, de-identified form. All clinical queries must use aggregate functions (COUNT, SUM, AVG) with GROUP BY. Patient identifiers (mrn, full_name, ssn, dob) must NOT appear in SELECT. Maximum 1000 rows per result set.",
  structured_rule: '{"type":"AGGREGATION_ONLY","domain":"clinical","tables":["encounters","patients","prescriptions","vital_signs","lab_results","allergies","encounter_summaries"],"denied_in_select":["mrn","full_name","ssn","dob","aadhaar_number"]}'
});

// RES-002: Researcher Analytics Access
CREATE (p:Policy {
  policy_id: "RES-002",
  name: "Researcher Analytics Access",
  effect: "ALLOW",
  priority: 50,
  is_active: true,
  nl_description: "Clinical researchers can access analytics tables (quality_metrics, population_health, research_cohorts, encounter_summaries) for population health studies and quality improvement research.",
  structured_rule: '{"type":"TABLE_ALLOW","domain":"analytics","tables":["quality_metrics","population_health","research_cohorts","encounter_summaries"],"columns":"*"}'
});

// NURSE-PII: Nurse PII Masking (from original POL-002)
CREATE (p:Policy {
  policy_id: "NURSE-PII",
  name: "Nurse PII Masking",
  effect: "MASK",
  priority: 90,
  is_active: true,
  nl_description: "Nurses may access patient data but PII columns (mrn, full_name, aadhaar_number) must be partially masked. Show first initial + last name only for full_name. Mask MRN partially.",
  structured_rule: '{"type":"COLUMN_MASK","columns":{"patients.mrn":"PARTIAL","patients.full_name":"PARTIAL","patients.aadhaar_number":"FULL"},"mask_strategy":"PARTIAL_MASK"}'
});

// EMER-001: Break-the-Glass Emergency Access
// Spec §11.5: Overrides DENY < 200. Still denied: substance_abuse_records
CREATE (p:Policy {
  policy_id: "EMER-001",
  name: "Break-the-Glass Emergency Access",
  effect: "ALLOW",
  priority: 300,
  is_active: true,
  nl_description: "EMERGENCY ACCESS: Break-the-glass protocol activated. Overrides normal access restrictions for clinical emergency. Substance abuse records (42 CFR Part 2) remain DENIED even under BTG. Access is logged with EMERGENCY flag and triggers HIPAA Officer notification. 4-hour time limit. Written justification required within 24 hours.",
  structured_rule: '{"type":"EMERGENCY_OVERRIDE","duration_hours":4,"still_denied":["substance_abuse_records"],"requires":["reason","patient_id"],"triggers":["HIPAA_OFFICER_NOTIFICATION","RETROSPECTIVE_REVIEW"]}'
});


// ── 4. CREATE CONDITIONS ────────────────────────────────────

// SEC-001 join restriction condition
CREATE (c:Condition {
  condition_id: "COND-SEC-001",
  condition_type: "JOIN_RESTRICTION",
  expression: "source_domain != target_domain",
  parameters: '{"source_domain":"clinical","target_domain":"hr"}'
});

// SEC-002 join restriction condition
CREATE (c:Condition {
  condition_id: "COND-SEC-002",
  condition_type: "JOIN_RESTRICTION",
  expression: "source_tables NOT IN target_domain",
  parameters: '{"source_tables":["payer_contracts","insurance_plans"],"target_domain":"hr"}'
});

// SEC-003 join restriction condition
CREATE (c:Condition {
  condition_id: "COND-SEC-003",
  condition_type: "JOIN_RESTRICTION",
  expression: "source_tables NOT IN target_domain",
  parameters: '{"source_tables":["genetic_records"],"target_domain":"billing"}'
});

// HIPAA-001 minimum necessary condition
CREATE (c:Condition {
  condition_id: "COND-HIPAA-001",
  condition_type: "MAX_ROWS",
  expression: "LIMIT 1000",
  parameters: '{"limit":1000,"require_where":true}'
});

// CLIN-001 treatment relationship row filter
CREATE (c:Condition {
  condition_id: "COND-CLIN-001",
  condition_type: "ROW_FILTER",
  expression: "treating_provider_id = {{user.provider_id}} OR unit_id = {{user.unit_id}}",
  parameters: '{"tables":["encounters","clinical_notes","vital_signs","lab_results"]}'
});

// BIZ-010 aggregation-only condition
CREATE (c:Condition {
  condition_id: "COND-BIZ-010",
  condition_type: "AGGREGATION_ONLY",
  expression: "Must use GROUP BY. Denied in SELECT: mrn, full_name, ssn, dob",
  parameters: '{"require_group_by":true,"denied_in_select":["mrn","full_name","ssn","dob"]}'
});

// RES-001 aggregation + max rows condition
CREATE (c:Condition {
  condition_id: "COND-RES-001",
  condition_type: "AGGREGATION_ONLY",
  expression: "Must use GROUP BY. Denied in SELECT: mrn, full_name, ssn, dob, aadhaar_number. LIMIT 1000",
  parameters: '{"require_group_by":true,"denied_in_select":["mrn","full_name","ssn","dob","aadhaar_number"],"max_rows":1000}'
});


// ── 5. WIRE RELATIONSHIPS ───────────────────────────────────

// ── FED-001 → ALL roles ──
MATCH (p:Policy {policy_id: "FED-001"}), (r:Role) MERGE (p)-[:APPLIES_TO_ROLE]->(r);

// ── HIPAA-005 → ALL roles ──
MATCH (p:Policy {policy_id: "HIPAA-005"}), (r:Role) MERGE (p)-[:APPLIES_TO_ROLE]->(r);

// ── SEC-001 → ALL roles + Clinical/HR domains + condition ──
MATCH (p:Policy {policy_id: "SEC-001"}), (r:Role) MERGE (p)-[:APPLIES_TO_ROLE]->(r);
MATCH (p:Policy {policy_id: "SEC-001"}), (d:Domain {name: "clinical"}) MERGE (p)-[:GOVERNS_DOMAIN]->(d);
MATCH (p:Policy {policy_id: "SEC-001"}), (d:Domain {name: "hr"}) MERGE (p)-[:GOVERNS_DOMAIN]->(d);
MATCH (p:Policy {policy_id: "SEC-001"}), (c:Condition {condition_id: "COND-SEC-001"}) MERGE (p)-[:HAS_CONDITION]->(c);

// ── SEC-002 → ALL roles + billing/hr domains + condition ──
MATCH (p:Policy {policy_id: "SEC-002"}), (r:Role) MERGE (p)-[:APPLIES_TO_ROLE]->(r);
MATCH (p:Policy {policy_id: "SEC-002"}), (d:Domain {name: "billing"}) MERGE (p)-[:GOVERNS_DOMAIN]->(d);
MATCH (p:Policy {policy_id: "SEC-002"}), (d:Domain {name: "hr"}) MERGE (p)-[:GOVERNS_DOMAIN]->(d);
MATCH (p:Policy {policy_id: "SEC-002"}), (c:Condition {condition_id: "COND-SEC-002"}) MERGE (p)-[:HAS_CONDITION]->(c);

// ── SEC-003 → ALL roles + condition ──
MATCH (p:Policy {policy_id: "SEC-003"}), (r:Role) MERGE (p)-[:APPLIES_TO_ROLE]->(r);
MATCH (p:Policy {policy_id: "SEC-003"}), (c:Condition {condition_id: "COND-SEC-003"}) MERGE (p)-[:HAS_CONDITION]->(c);

// ── HIPAA-001 → ALL roles + condition ──
MATCH (p:Policy {policy_id: "HIPAA-001"}), (r:Role) MERGE (p)-[:APPLIES_TO_ROLE]->(r);
MATCH (p:Policy {policy_id: "HIPAA-001"}), (c:Condition {condition_id: "COND-HIPAA-001"}) MERGE (p)-[:HAS_CONDITION]->(c);

// ── CLIN-001 → doctor, nurse + clinical domain + condition ──
MATCH (p:Policy {policy_id: "CLIN-001"}), (r:Role {name: "doctor"}) MERGE (p)-[:APPLIES_TO_ROLE]->(r);
MATCH (p:Policy {policy_id: "CLIN-001"}), (r:Role {name: "nurse"}) MERGE (p)-[:APPLIES_TO_ROLE]->(r);
MATCH (p:Policy {policy_id: "CLIN-001"}), (d:Domain {name: "clinical"}) MERGE (p)-[:GOVERNS_DOMAIN]->(d);
MATCH (p:Policy {policy_id: "CLIN-001"}), (c:Condition {condition_id: "COND-CLIN-001"}) MERGE (p)-[:HAS_CONDITION]->(c);
// CLIN-001 governs specific clinical tables
MATCH (p:Policy {policy_id: "CLIN-001"}), (t:Table {name: "encounters"}) WHERE t.is_active = true MERGE (p)-[:GOVERNS_TABLE]->(t);
MATCH (p:Policy {policy_id: "CLIN-001"}), (t:Table {name: "clinical_notes"}) WHERE t.is_active = true MERGE (p)-[:GOVERNS_TABLE]->(t);
MATCH (p:Policy {policy_id: "CLIN-001"}), (t:Table {name: "vital_signs"}) WHERE t.is_active = true MERGE (p)-[:GOVERNS_TABLE]->(t);
MATCH (p:Policy {policy_id: "CLIN-001"}), (t:Table {name: "lab_results"}) WHERE t.is_active = true MERGE (p)-[:GOVERNS_TABLE]->(t);

// ── HIPAA-003 → ALL roles ──
MATCH (p:Policy {policy_id: "HIPAA-003"}), (r:Role) MERGE (p)-[:APPLIES_TO_ROLE]->(r);

// ── HIPAA-004 → ALL roles ──
MATCH (p:Policy {policy_id: "HIPAA-004"}), (r:Role) MERGE (p)-[:APPLIES_TO_ROLE]->(r);

// ── CLIN-100 → doctor + clinical domain + specific tables ──
MATCH (p:Policy {policy_id: "CLIN-100"}), (r:Role {name: "doctor"}) MERGE (p)-[:APPLIES_TO_ROLE]->(r);
MATCH (p:Policy {policy_id: "CLIN-100"}), (d:Domain {name: "clinical"}) MERGE (p)-[:GOVERNS_DOMAIN]->(d);
MATCH (p:Policy {policy_id: "CLIN-100"}), (t:Table) WHERE t.is_active = true AND t.name IN ["encounters","patients","prescriptions","vital_signs","lab_results","clinical_notes","allergies","encounter_summaries"] MERGE (p)-[:GOVERNS_TABLE]->(t);

// ── NURSE-100 → nurse + clinical domain + specific tables ──
MATCH (p:Policy {policy_id: "NURSE-100"}), (r:Role {name: "nurse"}) MERGE (p)-[:APPLIES_TO_ROLE]->(r);
MATCH (p:Policy {policy_id: "NURSE-100"}), (d:Domain {name: "clinical"}) MERGE (p)-[:GOVERNS_DOMAIN]->(d);
MATCH (p:Policy {policy_id: "NURSE-100"}), (t:Table) WHERE t.is_active = true AND t.name IN ["encounters","patients","vital_signs","prescriptions","allergies","clinical_notes"] MERGE (p)-[:GOVERNS_TABLE]->(t);

// ── NURSE-PII → nurse ──
MATCH (p:Policy {policy_id: "NURSE-PII"}), (r:Role {name: "nurse"}) MERGE (p)-[:APPLIES_TO_ROLE]->(r);
MATCH (p:Policy {policy_id: "NURSE-PII"}), (t:Table {name: "patients"}) WHERE t.is_active = true MERGE (p)-[:GOVERNS_TABLE]->(t);

// ── BIZ-001 → billing_staff + billing domain + specific tables ──
MATCH (p:Policy {policy_id: "BIZ-001"}), (r:Role {name: "billing_staff"}) MERGE (p)-[:APPLIES_TO_ROLE]->(r);
MATCH (p:Policy {policy_id: "BIZ-001"}), (d:Domain {name: "billing"}) MERGE (p)-[:GOVERNS_DOMAIN]->(d);
MATCH (p:Policy {policy_id: "BIZ-001"}), (t:Table) WHERE t.is_active = true AND t.name IN ["claims","claim_line_items","payments","insurance_plans","patient_billing"] MERGE (p)-[:GOVERNS_TABLE]->(t);
// BIZ-001 also grants limited access to patients and encounters (column-restricted)
MATCH (p:Policy {policy_id: "BIZ-001"}), (t:Table {name: "patients"}) WHERE t.is_active = true MERGE (p)-[:GOVERNS_TABLE]->(t);
MATCH (p:Policy {policy_id: "BIZ-001"}), (t:Table {name: "encounters"}) WHERE t.is_active = true MERGE (p)-[:GOVERNS_TABLE]->(t);

// ── CLIN-005 → pharmacist + specific tables ──
MATCH (p:Policy {policy_id: "CLIN-005"}), (r:Role {name: "pharmacist"}) MERGE (p)-[:APPLIES_TO_ROLE]->(r);
MATCH (p:Policy {policy_id: "CLIN-005"}), (d:Domain {name: "clinical"}) MERGE (p)-[:GOVERNS_DOMAIN]->(d);
MATCH (p:Policy {policy_id: "CLIN-005"}), (t:Table {name: "prescriptions"}) WHERE t.is_active = true MERGE (p)-[:GOVERNS_TABLE]->(t);
MATCH (p:Policy {policy_id: "CLIN-005"}), (t:Table {name: "allergies"}) WHERE t.is_active = true MERGE (p)-[:GOVERNS_TABLE]->(t);
MATCH (p:Policy {policy_id: "CLIN-005"}), (t:Table {name: "patients"}) WHERE t.is_active = true MERGE (p)-[:GOVERNS_TABLE]->(t);

// ── BIZ-010 → revenue_manager + billing domain + specific tables + condition ──
MATCH (p:Policy {policy_id: "BIZ-010"}), (r:Role {name: "revenue_manager"}) MERGE (p)-[:APPLIES_TO_ROLE]->(r);
MATCH (p:Policy {policy_id: "BIZ-010"}), (d:Domain {name: "billing"}) MERGE (p)-[:GOVERNS_DOMAIN]->(d);
MATCH (p:Policy {policy_id: "BIZ-010"}), (t:Table {name: "encounters"}) WHERE t.is_active = true MERGE (p)-[:GOVERNS_TABLE]->(t);
MATCH (p:Policy {policy_id: "BIZ-010"}), (t:Table {name: "claims"}) WHERE t.is_active = true MERGE (p)-[:GOVERNS_TABLE]->(t);
MATCH (p:Policy {policy_id: "BIZ-010"}), (t:Table {name: "payments"}) WHERE t.is_active = true MERGE (p)-[:GOVERNS_TABLE]->(t);
MATCH (p:Policy {policy_id: "BIZ-010"}), (c:Condition {condition_id: "COND-BIZ-010"}) MERGE (p)-[:HAS_CONDITION]->(c);

// ── REVENUE-DENY-CLIN → revenue_manager + clinical domain ──
MATCH (p:Policy {policy_id: "REVENUE-DENY-CLIN"}), (r:Role {name: "revenue_manager"}) MERGE (p)-[:APPLIES_TO_ROLE]->(r);
MATCH (p:Policy {policy_id: "REVENUE-DENY-CLIN"}), (d:Domain {name: "clinical"}) MERGE (p)-[:GOVERNS_DOMAIN]->(d);

// ── HR-001 → hr_manager + hospital_admin + hr domain + specific tables ──
MATCH (p:Policy {policy_id: "HR-001"}), (r:Role {name: "hr_manager"}) MERGE (p)-[:APPLIES_TO_ROLE]->(r);
MATCH (p:Policy {policy_id: "HR-001"}), (d:Domain {name: "hr"}) MERGE (p)-[:GOVERNS_DOMAIN]->(d);
MATCH (p:Policy {policy_id: "HR-001"}), (t:Table) WHERE t.is_active = true AND t.name IN ["employees","payroll","leave_records","certifications","credentials","departments"] MERGE (p)-[:GOVERNS_TABLE]->(t);

// ── ADMIN-001 → hospital_admin + analytics/general domains ──
MATCH (p:Policy {policy_id: "ADMIN-001"}), (r:Role {name: "hospital_admin"}) MERGE (p)-[:APPLIES_TO_ROLE]->(r);
MATCH (p:Policy {policy_id: "ADMIN-001"}), (d:Domain {name: "analytics"}) MERGE (p)-[:GOVERNS_DOMAIN]->(d);
MATCH (p:Policy {policy_id: "ADMIN-001"}), (d:Domain {name: "general"}) MERGE (p)-[:GOVERNS_DOMAIN]->(d);
MATCH (p:Policy {policy_id: "ADMIN-001"}), (d:Domain {name: "hr"}) MERGE (p)-[:GOVERNS_DOMAIN]->(d);
MATCH (p:Policy {policy_id: "ADMIN-001"}), (t:Table) WHERE t.is_active = true AND t.name IN ["quality_metrics","encounter_summaries","population_health","facilities","units","departments","appointments","staff_schedules","employees","payroll","leave_records","certifications","credentials","research_cohorts"] MERGE (p)-[:GOVERNS_TABLE]->(t);

// ── ADMIN-DENY-CLIN → hospital_admin + clinical domain ──
MATCH (p:Policy {policy_id: "ADMIN-DENY-CLIN"}), (r:Role {name: "hospital_admin"}) MERGE (p)-[:APPLIES_TO_ROLE]->(r);
MATCH (p:Policy {policy_id: "ADMIN-DENY-CLIN"}), (d:Domain {name: "clinical"}) MERGE (p)-[:GOVERNS_DOMAIN]->(d);

// ── RES-001 → researcher + clinical domain + condition ──
MATCH (p:Policy {policy_id: "RES-001"}), (r:Role {name: "researcher"}) MERGE (p)-[:APPLIES_TO_ROLE]->(r);
MATCH (p:Policy {policy_id: "RES-001"}), (d:Domain {name: "clinical"}) MERGE (p)-[:GOVERNS_DOMAIN]->(d);
MATCH (p:Policy {policy_id: "RES-001"}), (t:Table) WHERE t.is_active = true AND t.name IN ["encounters","patients","prescriptions","vital_signs","lab_results","allergies","encounter_summaries"] MERGE (p)-[:GOVERNS_TABLE]->(t);
MATCH (p:Policy {policy_id: "RES-001"}), (c:Condition {condition_id: "COND-RES-001"}) MERGE (p)-[:HAS_CONDITION]->(c);

// ── RES-002 → researcher + analytics domain ──
MATCH (p:Policy {policy_id: "RES-002"}), (r:Role {name: "researcher"}) MERGE (p)-[:APPLIES_TO_ROLE]->(r);
MATCH (p:Policy {policy_id: "RES-002"}), (d:Domain {name: "analytics"}) MERGE (p)-[:GOVERNS_DOMAIN]->(d);
MATCH (p:Policy {policy_id: "RES-002"}), (t:Table) WHERE t.is_active = true AND t.name IN ["quality_metrics","population_health","research_cohorts","encounter_summaries"] MERGE (p)-[:GOVERNS_TABLE]->(t);

// ── EMER-001 → ALL roles (BTG is role-agnostic, resolved at runtime) ──
MATCH (p:Policy {policy_id: "EMER-001"}), (r:Role) MERGE (p)-[:APPLIES_TO_ROLE]->(r);


// ── 6. UPDATE ACCESSES_DOMAIN ───────────────────────────────
// Remove all existing ACCESSES_DOMAIN relationships
MATCH ()-[r:ACCESSES_DOMAIN]->() DELETE r;

// doctor: clinical + general (for reference data like facilities/units/appointments)
MATCH (r:Role {name: "doctor"}), (d:Domain {name: "clinical"}) MERGE (r)-[:ACCESSES_DOMAIN]->(d);
MATCH (r:Role {name: "doctor"}), (d:Domain {name: "general"}) MERGE (r)-[:ACCESSES_DOMAIN]->(d);

// nurse: clinical + general
MATCH (r:Role {name: "nurse"}), (d:Domain {name: "clinical"}) MERGE (r)-[:ACCESSES_DOMAIN]->(d);
MATCH (r:Role {name: "nurse"}), (d:Domain {name: "general"}) MERGE (r)-[:ACCESSES_DOMAIN]->(d);

// billing_staff: billing only (BIZ-001 grants limited clinical columns via table-level, not domain-level)
MATCH (r:Role {name: "billing_staff"}), (d:Domain {name: "billing"}) MERGE (r)-[:ACCESSES_DOMAIN]->(d);

// pharmacist: clinical (CLIN-005 is table-specific within clinical)
MATCH (r:Role {name: "pharmacist"}), (d:Domain {name: "clinical"}) MERGE (r)-[:ACCESSES_DOMAIN]->(d);

// revenue_manager: billing + clinical (BIZ-010 needs encounters from clinical; L4 enforces aggregate-only)
MATCH (r:Role {name: "revenue_manager"}), (d:Domain {name: "billing"}) MERGE (r)-[:ACCESSES_DOMAIN]->(d);

// hospital_admin: analytics + general + hr (NOT clinical, NOT billing)
MATCH (r:Role {name: "hospital_admin"}), (d:Domain {name: "analytics"}) MERGE (r)-[:ACCESSES_DOMAIN]->(d);
MATCH (r:Role {name: "hospital_admin"}), (d:Domain {name: "general"}) MERGE (r)-[:ACCESSES_DOMAIN]->(d);
MATCH (r:Role {name: "hospital_admin"}), (d:Domain {name: "hr"}) MERGE (r)-[:ACCESSES_DOMAIN]->(d);

// hr_manager: hr only
MATCH (r:Role {name: "hr_manager"}), (d:Domain {name: "hr"}) MERGE (r)-[:ACCESSES_DOMAIN]->(d);

// researcher: clinical + analytics (RES-001 enforces aggregation-only on clinical)
MATCH (r:Role {name: "researcher"}), (d:Domain {name: "clinical"}) MERGE (r)-[:ACCESSES_DOMAIN]->(d);
MATCH (r:Role {name: "researcher"}), (d:Domain {name: "analytics"}) MERGE (r)-[:ACCESSES_DOMAIN]->(d);
