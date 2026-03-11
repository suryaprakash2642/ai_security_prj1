// ============================================================
// Policy Relationships — Connect policies to roles, tables, domains
// Must use MATCH (not variables) since init_graph splits on semicolons
// ============================================================

// ────────────────────────────────────────────────────────────
// POL-001: Doctor Clinical Data Access (ALLOW)
// Doctors can access all clinical tables
// ────────────────────────────────────────────────────────────
MATCH (p:Policy {policy_id: "POL-001"}), (r:Role {name: "doctor"})
MERGE (p)-[:APPLIES_TO_ROLE]->(r);

MATCH (p:Policy {policy_id: "POL-001"}), (d:Domain {name: "clinical"})
MERGE (p)-[:GOVERNS_DOMAIN]->(d);

// Also grant to hospital_admin (inherits doctor)
MATCH (p:Policy {policy_id: "POL-001"}), (r:Role {name: "hospital_admin"})
MERGE (p)-[:APPLIES_TO_ROLE]->(r);

// ────────────────────────────────────────────────────────────
// POL-002: Nurse PII Masking Policy (MASK)
// Nurses see patient data but PII masked
// ────────────────────────────────────────────────────────────
MATCH (p:Policy {policy_id: "POL-002"}), (r:Role {name: "nurse"})
MERGE (p)-[:APPLIES_TO_ROLE]->(r);

MATCH (p:Policy {policy_id: "POL-002"}), (t:Table)
WHERE t.name = "patients" AND t.is_active = true
MERGE (p)-[:GOVERNS_TABLE]->(t);

// ────────────────────────────────────────────────────────────
// POL-003: Researcher Aggregation-Only (FILTER)
// Researchers get aggregated clinical data only
// ────────────────────────────────────────────────────────────
MATCH (p:Policy {policy_id: "POL-003"}), (r:Role {name: "researcher"})
MERGE (p)-[:APPLIES_TO_ROLE]->(r);

MATCH (p:Policy {policy_id: "POL-003"}), (d:Domain {name: "clinical"})
MERGE (p)-[:GOVERNS_DOMAIN]->(d);

MATCH (p:Policy {policy_id: "POL-003"}), (c:Condition {condition_id: "COND-001"})
MERGE (p)-[:HAS_CONDITION]->(c);

// ────────────────────────────────────────────────────────────
// POL-004: 42 CFR Part 2 — HARD DENY on substance abuse
// No specific table in Aiven, kept as universal deny marker
// ────────────────────────────────────────────────────────────

// ────────────────────────────────────────────────────────────
// POL-005: Billing Staff Domain Access (ALLOW)
// Billing staff can access all billing domain tables
// ────────────────────────────────────────────────────────────
MATCH (p:Policy {policy_id: "POL-005"}), (r:Role {name: "billing_staff"})
MERGE (p)-[:APPLIES_TO_ROLE]->(r);

MATCH (p:Policy {policy_id: "POL-005"}), (d:Domain {name: "billing"})
MERGE (p)-[:GOVERNS_DOMAIN]->(d);

// ────────────────────────────────────────────────────────────
// POL-006: Billing-Clinical Cross-Domain Join Restriction (DENY)
// ────────────────────────────────────────────────────────────
MATCH (p:Policy {policy_id: "POL-006"}), (r:Role {name: "billing_staff"})
MERGE (p)-[:APPLIES_TO_ROLE]->(r);

MATCH (p:Policy {policy_id: "POL-006"}), (c:Condition {condition_id: "COND-002"})
MERGE (p)-[:HAS_CONDITION]->(c);

MATCH (p:Policy {policy_id: "POL-006"}), (d:Domain {name: "clinical"})
MERGE (p)-[:RESTRICTS_JOIN {source_domain: "billing", target_domain: "clinical"}]->(d);

// ────────────────────────────────────────────────────────────
// POL-007: Night Shift Nurse Time-Window Access (FILTER)
// Nurses restricted to encounters within shift window
// ────────────────────────────────────────────────────────────
MATCH (p:Policy {policy_id: "POL-007"}), (r:Role {name: "nurse"})
MERGE (p)-[:APPLIES_TO_ROLE]->(r);

MATCH (p:Policy {policy_id: "POL-007"}), (t:Table)
WHERE t.name = "encounters" AND t.is_active = true
MERGE (p)-[:GOVERNS_TABLE]->(t);

MATCH (p:Policy {policy_id: "POL-007"}), (c:Condition {condition_id: "COND-003"})
MERGE (p)-[:HAS_CONDITION]->(c);

// ────────────────────────────────────────────────────────────
// POL-008: Researcher Max-Row Limit (FILTER)
// ────────────────────────────────────────────────────────────
MATCH (p:Policy {policy_id: "POL-008"}), (r:Role {name: "researcher"})
MERGE (p)-[:APPLIES_TO_ROLE]->(r);

MATCH (p:Policy {policy_id: "POL-008"}), (c:Condition {condition_id: "COND-004"})
MERGE (p)-[:HAS_CONDITION]->(c);

// ────────────────────────────────────────────────────────────
// POL-009: Psychotherapy Notes DENY — no matching Aiven table currently
// ────────────────────────────────────────────────────────────

// ────────────────────────────────────────────────────────────
// Additional broad policies for new Aiven tables
// ────────────────────────────────────────────────────────────

// Doctor/Admin can access all clinical domain tables (encounters, lab_results, vital_signs, etc.)
MATCH (p:Policy {policy_id: "POL-001"}), (t:Table)-[:BELONGS_TO_DOMAIN]->(d:Domain {name: "clinical"})
WHERE t.is_active = true
MERGE (p)-[:GOVERNS_TABLE]->(t);

// Nurse can access clinical domain tables (with masking on patient PII)
MATCH (p:Policy {policy_id: "POL-002"}), (t:Table)-[:BELONGS_TO_DOMAIN]->(d:Domain {name: "clinical"})
WHERE t.is_active = true
MERGE (p)-[:GOVERNS_TABLE]->(t);

// Billing staff can access all billing tables
MATCH (p:Policy {policy_id: "POL-005"}), (t:Table)-[:BELONGS_TO_DOMAIN]->(d:Domain {name: "billing"})
WHERE t.is_active = true
MERGE (p)-[:GOVERNS_TABLE]->(t);

// ────────────────────────────────────────────────────────────
// HR Policies — new for Aiven HR tables
// ────────────────────────────────────────────────────────────

// Create HR manager policy
MATCH (r:Role {name: "hospital_admin"})
MERGE (p_hr:Policy {policy_id: "POL-HR-001"})
SET p_hr.name = "HR Admin Full Access",
    p_hr.nl_description = "Hospital administrators can access all HR records including payroll and credentials",
    p_hr.structured_rule = '{"effect":"ALLOW","target":{"domain":"hr"},"subject":{"role":"hospital_admin"}}',
    p_hr.policy_type = "ALLOW",
    p_hr.priority = 100,
    p_hr.is_active = true,
    p_hr.created_by = "compliance-admin",
    p_hr.created_at = datetime(),
    p_hr.version = 1
MERGE (p_hr)-[:APPLIES_TO_ROLE]->(r);

MATCH (p:Policy {policy_id: "POL-HR-001"}), (d:Domain {name: "hr"})
MERGE (p)-[:GOVERNS_DOMAIN]->(d);

MATCH (p:Policy {policy_id: "POL-HR-001"}), (t:Table)-[:BELONGS_TO_DOMAIN]->(d:Domain {name: "hr"})
WHERE t.is_active = true
MERGE (p)-[:GOVERNS_TABLE]->(t);

// ────────────────────────────────────────────────────────────
// Analytics Domain — doctors and admins can access
// ────────────────────────────────────────────────────────────

MATCH (r:Role {name: "doctor"})
MERGE (p_an:Policy {policy_id: "POL-ANALYTICS-001"})
SET p_an.name = "Clinical Analytics Access",
    p_an.nl_description = "Doctors can access clinical analytics for quality metrics and encounter summaries",
    p_an.structured_rule = '{"effect":"ALLOW","target":{"domain":"analytics"},"subject":{"role":"doctor"}}',
    p_an.policy_type = "ALLOW",
    p_an.priority = 100,
    p_an.is_active = true,
    p_an.created_by = "compliance-admin",
    p_an.created_at = datetime(),
    p_an.version = 1
MERGE (p_an)-[:APPLIES_TO_ROLE]->(r);

MATCH (p:Policy {policy_id: "POL-ANALYTICS-001"}), (r:Role {name: "hospital_admin"})
MERGE (p)-[:APPLIES_TO_ROLE]->(r);

MATCH (p:Policy {policy_id: "POL-ANALYTICS-001"}), (d:Domain {name: "analytics"})
MERGE (p)-[:GOVERNS_DOMAIN]->(d);

MATCH (p:Policy {policy_id: "POL-ANALYTICS-001"}), (t:Table)-[:BELONGS_TO_DOMAIN]->(d:Domain {name: "analytics"})
WHERE t.is_active = true
MERGE (p)-[:GOVERNS_TABLE]->(t);

// ────────────────────────────────────────────────────────────
// General domain tables — accessible by doctors and admins
// (departments, facilities, appointments, etc.)
// ────────────────────────────────────────────────────────────

MATCH (r:Role {name: "doctor"})
MERGE (p_gen:Policy {policy_id: "POL-GENERAL-001"})
SET p_gen.name = "General Reference Data Access",
    p_gen.nl_description = "Clinical staff can access general reference data like departments, facilities, and appointments",
    p_gen.structured_rule = '{"effect":"ALLOW","target":{"domain":"general"},"subject":{"role":"doctor"}}',
    p_gen.policy_type = "ALLOW",
    p_gen.priority = 100,
    p_gen.is_active = true,
    p_gen.created_by = "compliance-admin",
    p_gen.created_at = datetime(),
    p_gen.version = 1
MERGE (p_gen)-[:APPLIES_TO_ROLE]->(r);

MATCH (p:Policy {policy_id: "POL-GENERAL-001"}), (r:Role {name: "nurse"})
MERGE (p)-[:APPLIES_TO_ROLE]->(r);

MATCH (p:Policy {policy_id: "POL-GENERAL-001"}), (r:Role {name: "hospital_admin"})
MERGE (p)-[:APPLIES_TO_ROLE]->(r);

MATCH (p:Policy {policy_id: "POL-GENERAL-001"}), (d:Domain {name: "general"})
MERGE (p)-[:GOVERNS_DOMAIN]->(d);

MATCH (p:Policy {policy_id: "POL-GENERAL-001"}), (t:Table)-[:BELONGS_TO_DOMAIN]->(d:Domain {name: "general"})
WHERE t.is_active = true
MERGE (p)-[:GOVERNS_TABLE]->(t);

// ────────────────────────────────────────────────────────────
// Pharmacist access to clinical + pharmacy-related tables
// ────────────────────────────────────────────────────────────

MATCH (r:Role {name: "pharmacist"})
MERGE (p_rx:Policy {policy_id: "POL-PHARMACY-001"})
SET p_rx.name = "Pharmacist Prescription Access",
    p_rx.nl_description = "Pharmacists can access prescription, allergy, and medication-related clinical data",
    p_rx.structured_rule = '{"effect":"ALLOW","target":{"tables":["prescriptions","allergies","patients"]},"subject":{"role":"pharmacist"}}',
    p_rx.policy_type = "ALLOW",
    p_rx.priority = 100,
    p_rx.is_active = true,
    p_rx.created_by = "compliance-admin",
    p_rx.created_at = datetime(),
    p_rx.version = 1
MERGE (p_rx)-[:APPLIES_TO_ROLE]->(r);

MATCH (p:Policy {policy_id: "POL-PHARMACY-001"}), (t:Table)
WHERE t.name IN ["prescriptions", "allergies", "patients"] AND t.is_active = true
MERGE (p)-[:GOVERNS_TABLE]->(t);
