// ============================================================
// 010 — Policy & Regulation Relationship Fix
// Wires: Policy → GOVERNS_TABLE/COLUMN/DOMAIN/APPLIES_TO_ROLE
//        Table → REGULATED_BY → Regulation
//        Column → COLUMN_REGULATED_BY → Regulation
// ============================================================

// ─── STEP 1: Role nodes (needed for APPLIES_TO_ROLE) ─────────────────────────

MERGE (:Role {name: "doctor"})         SET (MATCH (r:Role {name:"doctor"})         RETURN r LIMIT 1) SKIP 0;
MERGE (:Role {name: "nurse"})          ON CREATE SET (MATCH (r:Role {name:"nurse"})          RETURN r LIMIT 1) SKIP 0;
MERGE (:Role {name: "clinical_staff"});
MERGE (:Role {name: "billing_staff"});
MERGE (:Role {name: "pharmacy_staff"});
MERGE (:Role {name: "analyst"});
MERGE (:Role {name: "admin"});
MERGE (:Role {name: "auditor"});
MERGE (:Role {name: "researcher"});
MERGE (:Role {name: "hr_staff"});
MERGE (:Role {name: "security_officer"});
MERGE (:Role {name: "base_user"});

// ─── STEP 2: APPLIES_TO_ROLE — who each Policy applies to ────────────────────

// POL-001: Base ALLOW for clinical readers
MATCH (p:Policy {policy_id: "POL-001"}), (r:Role {name: "clinical_staff"}) MERGE (p)-[:APPLIES_TO_ROLE]->(r);
MATCH (p:Policy {policy_id: "POL-001"}), (r:Role {name: "doctor"})         MERGE (p)-[:APPLIES_TO_ROLE]->(r);
MATCH (p:Policy {policy_id: "POL-001"}), (r:Role {name: "nurse"})          MERGE (p)-[:APPLIES_TO_ROLE]->(r);

// POL-002: MASK on PII columns (HIPAA) — any authenticated user
MATCH (p:Policy {policy_id: "POL-002"}), (r:Role {name: "base_user"})     MERGE (p)-[:APPLIES_TO_ROLE]->(r);

// POL-003: Row-level FILTER — doctor sees only own patients
MATCH (p:Policy {policy_id: "POL-003"}), (r:Role {name: "doctor"})        MERGE (p)-[:APPLIES_TO_ROLE]->(r);

// POL-004: 42 CFR Part 2 DENY — substance abuse for all
MATCH (p:Policy {policy_id: "POL-004"}), (r:Role {name: "base_user"})     MERGE (p)-[:APPLIES_TO_ROLE]->(r);

// POL-005: Billing ALLOW for billing staff
MATCH (p:Policy {policy_id: "POL-005"}), (r:Role {name: "billing_staff"}) MERGE (p)-[:APPLIES_TO_ROLE]->(r);

// POL-006: DENY psychotherapy notes except treating doctor
MATCH (p:Policy {policy_id: "POL-006"}), (r:Role {name: "base_user"})     MERGE (p)-[:APPLIES_TO_ROLE]->(r);

// POL-007: FILTER time-window audit queries for auditors
MATCH (p:Policy {policy_id: "POL-007"}), (r:Role {name: "auditor"})       MERGE (p)-[:APPLIES_TO_ROLE]->(r);

// POL-008: Row-limited FILTER for analysts (max 1000 rows)
MATCH (p:Policy {policy_id: "POL-008"}), (r:Role {name: "analyst"})       MERGE (p)-[:APPLIES_TO_ROLE]->(r);
MATCH (p:Policy {policy_id: "POL-008"}), (r:Role {name: "researcher"})    MERGE (p)-[:APPLIES_TO_ROLE]->(r);

// POL-009: DENY psychotherapy notes (HIPAA psychotherapy notes)
MATCH (p:Policy {policy_id: "POL-009"}), (r:Role {name: "base_user"})     MERGE (p)-[:APPLIES_TO_ROLE]->(r);

// POL-010: DPDPA Aadhaar MASK — all users
MATCH (p:Policy {policy_id: "POL-010"}), (r:Role {name: "base_user"})     MERGE (p)-[:APPLIES_TO_ROLE]->(r);

// POL-011: GINA genetic DENY — all users
MATCH (p:Policy {policy_id: "POL-011"}), (r:Role {name: "base_user"})     MERGE (p)-[:APPLIES_TO_ROLE]->(r);

// POL-012: DEA Schedule II FILTER — doctors only
MATCH (p:Policy {policy_id: "POL-012"}), (r:Role {name: "doctor"})        MERGE (p)-[:APPLIES_TO_ROLE]->(r);
MATCH (p:Policy {policy_id: "POL-012"}), (r:Role {name: "pharmacy_staff"})MERGE (p)-[:APPLIES_TO_ROLE]->(r);

// POL-013: State HIV DENY — all users
MATCH (p:Policy {policy_id: "POL-013"}), (r:Role {name: "base_user"})     MERGE (p)-[:APPLIES_TO_ROLE]->(r);

// ─── STEP 3: GOVERNS_DOMAIN — Policies governing entire domains ──────────────

// POL-001 → clinical domain (base ALLOW)
MATCH (p:Policy {policy_id: "POL-001"}), (d:Domain {name: "clinical"})           MERGE (p)-[:GOVERNS_DOMAIN]->(d);
// POL-002 → clinical & pharmacy (PII masking)
MATCH (p:Policy {policy_id: "POL-002"}), (d:Domain {name: "clinical"})           MERGE (p)-[:GOVERNS_DOMAIN]->(d);
MATCH (p:Policy {policy_id: "POL-002"}), (d:Domain {name: "pharmacy"})           MERGE (p)-[:GOVERNS_DOMAIN]->(d);
// POL-003 → clinical (row filtering)
MATCH (p:Policy {policy_id: "POL-003"}), (d:Domain {name: "clinical"})           MERGE (p)-[:GOVERNS_DOMAIN]->(d);
// POL-004 → behavioral_health (42 CFR Part 2)
MATCH (p:Policy {policy_id: "POL-004"}), (d:Domain {name: "behavioral_health"})  MERGE (p)-[:GOVERNS_DOMAIN]->(d);
// POL-005 → billing
MATCH (p:Policy {policy_id: "POL-005"}), (d:Domain {name: "billing"})            MERGE (p)-[:GOVERNS_DOMAIN]->(d);
// POL-006 → behavioral_health (psychotherapy)
MATCH (p:Policy {policy_id: "POL-006"}), (d:Domain {name: "behavioral_health"})  MERGE (p)-[:GOVERNS_DOMAIN]->(d);
// POL-007 → audit
MATCH (p:Policy {policy_id: "POL-007"}), (d:Domain {name: "audit"})              MERGE (p)-[:GOVERNS_DOMAIN]->(d);
// POL-008 → analytics/research (row limit)
MATCH (p:Policy {policy_id: "POL-008"}), (d:Domain {name: "analytics"})          MERGE (p)-[:GOVERNS_DOMAIN]->(d);
// POL-009 → behavioral_health (HIPAA psychotherapy)
MATCH (p:Policy {policy_id: "POL-009"}), (d:Domain {name: "behavioral_health"})  MERGE (p)-[:GOVERNS_DOMAIN]->(d);
// POL-010 → clinical (Aadhaar DPDPA)
MATCH (p:Policy {policy_id: "POL-010"}), (d:Domain {name: "clinical"})           MERGE (p)-[:GOVERNS_DOMAIN]->(d);
// POL-011 → Research (GINA genetic)
MATCH (p:Policy {policy_id: "POL-011"}), (d:Domain {name: "Research"})           MERGE (p)-[:GOVERNS_DOMAIN]->(d);
// POL-012 → pharmacy (DEA Schedule II)
MATCH (p:Policy {policy_id: "POL-012"}), (d:Domain {name: "pharmacy"})           MERGE (p)-[:GOVERNS_DOMAIN]->(d);
// POL-013 → clinical (HIV laws)
MATCH (p:Policy {policy_id: "POL-013"}), (d:Domain {name: "clinical"})           MERGE (p)-[:GOVERNS_DOMAIN]->(d);

// ─── STEP 4: GOVERNS_TABLE — Policies to specific tables ─────────────────────

// POL-002: PII Masking → patients (has mrn, full_name, dob, aadhaar, phone, email)
MATCH (p:Policy {policy_id: "POL-002"}), (t:Table {name: "patients"})             MERGE (p)-[:GOVERNS_TABLE]->(t);
// POL-003: Row filter → patients (doctor sees own patients)
MATCH (p:Policy {policy_id: "POL-003"}), (t:Table {name: "patients"})             MERGE (p)-[:GOVERNS_TABLE]->(t);
// POL-004: 42 CFR DENY → substance_abuse_records
MATCH (p:Policy {policy_id: "POL-004"}), (t:Table)
  WHERE t.name CONTAINS "substance" OR t.fqn CONTAINS "substance"
  MERGE (p)-[:GOVERNS_TABLE]->(t);
// POL-005: Billing ALLOW → claims
MATCH (p:Policy {policy_id: "POL-005"}), (t:Table {name: "claims"})               MERGE (p)-[:GOVERNS_TABLE]->(t);
// POL-006: DENY psychotherapy → therapy_notes
MATCH (p:Policy {policy_id: "POL-006"}), (t:Table {name: "therapy_notes"})        MERGE (p)-[:GOVERNS_TABLE]->(t);
// POL-009: HIPAA psychotherapy → therapy_notes
MATCH (p:Policy {policy_id: "POL-009"}), (t:Table {name: "therapy_notes"})        MERGE (p)-[:GOVERNS_TABLE]->(t);
// POL-010: Aadhaar DPDPA MASK → patients
MATCH (p:Policy {policy_id: "POL-010"}), (t:Table {name: "patients"})             MERGE (p)-[:GOVERNS_TABLE]->(t);
// POL-011: GINA genetic DENY → all research/lab tables
MATCH (p:Policy {policy_id: "POL-011"}), (t:Table)
  WHERE t.domain = "research" OR t.fqn CONTAINS "research"
  MERGE (p)-[:GOVERNS_TABLE]->(t);
// POL-012: DEA Schedule II → prescriptions
MATCH (p:Policy {policy_id: "POL-012"}), (t:Table {name: "prescriptions"})        MERGE (p)-[:GOVERNS_TABLE]->(t);
// POL-013: HIV DENY → all clinical tables
MATCH (p:Policy {policy_id: "POL-013"}), (t:Table)
  WHERE t.sensitivity_level >= 4 AND t.domain = "clinical"
  MERGE (p)-[:GOVERNS_TABLE]->(t);

// ─── STEP 5: GOVERNS_COLUMN — Policies to specific high-sensitivity columns ───

// POL-002 (PII MASK) → PII columns in patients table
MATCH (p:Policy {policy_id: "POL-002"}), (c:Column)
  WHERE c.is_pii = true AND c.is_active = true
  AND (c.fqn CONTAINS "patients" OR c.fqn CONTAINS "encounters")
  MERGE (p)-[:GOVERNS_COLUMN]->(c);

// POL-010 (Aadhaar DPDPA) → specifically the aadhaar_number column
MATCH (p:Policy {policy_id: "POL-010"}), (c:Column)
  WHERE c.name CONTAINS "aadhaar" OR c.pii_type = "AADHAAR"
  MERGE (p)-[:GOVERNS_COLUMN]->(c);

// POL-013 (HIV laws) → hiv-related columns
MATCH (p:Policy {policy_id: "POL-013"}), (c:Column)
  WHERE toLower(c.name) CONTAINS "hiv" OR toLower(c.name) CONTAINS "aids"
  MERGE (p)-[:GOVERNS_COLUMN]->(c);

// ─── STEP 6: Table → REGULATED_BY → Regulation ───────────────────────────────

// All clinical tables → HIPAA
MATCH (t:Table), (r:Regulation {code: "HIPAA"})
  WHERE t.domain = "clinical" AND t.is_active = true
  MERGE (t)-[:REGULATED_BY]->(r);

// Pharmacy tables → HIPAA
MATCH (t:Table), (r:Regulation {code: "HIPAA"})
  WHERE t.domain = "pharmacy" AND t.is_active = true
  MERGE (t)-[:REGULATED_BY]->(r);

// Behavioral health tables → HIPAA
MATCH (t:Table), (r:Regulation {code: "HIPAA"})
  WHERE t.domain = "behavioral_health" AND t.is_active = true
  MERGE (t)-[:REGULATED_BY]->(r);

// Substance abuse → 42 CFR Part 2
MATCH (t:Table), (r:Regulation {code: "42_CFR_PART_2"})
  WHERE (t.name CONTAINS "substance" OR t.fqn CONTAINS "substance") AND t.is_active = true
  MERGE (t)-[:REGULATED_BY]->(r);

// Prescriptions → DEA Schedule II-V
MATCH (t:Table), (r:Regulation {code: "DEA_SCHEDULE_II_V"})
  WHERE t.name = "prescriptions" AND t.is_active = true
  MERGE (t)-[:REGULATED_BY]->(r);

// Therapy notes → HIPAA Psychotherapy
MATCH (t:Table), (r:Regulation {code: "HIPAA_PSYCHOTHERAPY"})
  WHERE (t.name CONTAINS "therapy" OR t.name CONTAINS "psych") AND t.is_active = true
  MERGE (t)-[:REGULATED_BY]->(r);

// All tables with sensitivity_level >= 3 and schema ~behavioral_health → STATE_MH_LAWS
MATCH (t:Table), (r:Regulation {code: "STATE_MH_LAWS"})
  WHERE t.domain = "behavioral_health" AND t.is_active = true
  MERGE (t)-[:REGULATED_BY]->(r);

// Patients → DPDPA_2023 (has Aadhaar)
MATCH (t:Table), (r:Regulation {code: "DPDPA_2023"})
  WHERE t.name = "patients" AND t.is_active = true
  MERGE (t)-[:REGULATED_BY]->(r);

// Patients → GINA (clinical genetics data risk)
MATCH (t:Table), (r:Regulation {code: "GINA"})
  WHERE t.name = "patients" AND t.is_active = true
  MERGE (t)-[:REGULATED_BY]->(r);

// HIV: any clinical table
MATCH (t:Table), (r:Regulation {code: "STATE_HIV_LAWS"})
  WHERE t.domain = "clinical" AND t.sensitivity_level >= 4 AND t.is_active = true
  MERGE (t)-[:REGULATED_BY]->(r);

// HR tables → no specific reg but tag with general compliance
// (HR has salary data which may be regulated by state laws)
MATCH (t:Table), (r:Regulation {code: "DPDPA_2023"})
  WHERE t.domain = "hr" AND t.is_active = true
  MERGE (t)-[:REGULATED_BY]->(r);

// ─── STEP 7: Column → COLUMN_REGULATED_BY → Regulation ──────────────────────

// PII columns in clinical → HIPAA
MATCH (c:Column), (r:Regulation {code: "HIPAA"})
  WHERE c.is_pii = true AND c.is_active = true
  AND (c.fqn CONTAINS ".clinical." OR c.fqn CONTAINS ".pharmacy." OR c.fqn CONTAINS ".behavioral_health.")
  MERGE (c)-[:COLUMN_REGULATED_BY]->(r);

// Aadhaar columns → DPDPA_2023
MATCH (c:Column), (r:Regulation {code: "DPDPA_2023"})
  WHERE (c.name CONTAINS "aadhaar" OR c.pii_type = "AADHAAR") AND c.is_active = true
  MERGE (c)-[:COLUMN_REGULATED_BY]->(r);

// MRN columns → HIPAA
MATCH (c:Column), (r:Regulation {code: "HIPAA"})
  WHERE (c.pii_type = "MEDICAL_RECORD_NUMBER" OR c.name = "mrn") AND c.is_active = true
  MERGE (c)-[:COLUMN_REGULATED_BY]->(r);

// Any column in substance_abuse tables → 42 CFR Part 2
MATCH (t:Table)-[:HAS_COLUMN]->(c:Column), (r:Regulation {code: "42_CFR_PART_2"})
  WHERE (t.name CONTAINS "substance" OR t.fqn CONTAINS "substance") AND c.is_active = true
  MERGE (c)-[:COLUMN_REGULATED_BY]->(r);

// prescriptions columns → DEA
MATCH (t:Table {name: "prescriptions"})-[:HAS_COLUMN]->(c:Column), (r:Regulation {code: "DEA_SCHEDULE_II_V"})
  WHERE c.is_active = true
  MERGE (c)-[:COLUMN_REGULATED_BY]->(r);

// ─── STEP 8: Schema → GOVERNED_BY — Policy scoping at schema level ───────────

// clinical schema → governed by HIPAA policy (POL-002)
MATCH (p:Policy {policy_id: "POL-002"}), (s:Schema)
  WHERE s.name = "clinical" OR s.fqn CONTAINS ".clinical"
  MERGE (p)-[:GOVERNS_SCHEMA]->(s);

// behavioral_health schema → governed by 42 CFR (POL-004)
MATCH (p:Policy {policy_id: "POL-004"}), (s:Schema)
  WHERE s.name = "behavioral_health" OR s.fqn CONTAINS ".behavioral_health"
  MERGE (p)-[:GOVERNS_SCHEMA]->(s);

// pharmacy schema → governed by DEA (POL-012)
MATCH (p:Policy {policy_id: "POL-012"}), (s:Schema)
  WHERE s.name = "pharmacy" OR s.fqn CONTAINS ".pharmacy"
  MERGE (p)-[:GOVERNS_SCHEMA]->(s);
