// ============================================================
// 009 — Policy & Regulation Full Push (Section 5 Compliant)
// Pushes all Policy nodes (with effect, name, regulation, DUAL REP)
// Pushes all Regulation nodes (with regulation_id, jurisdiction,
// retention_years, penalty_description)
// Creates IMPLEMENTS relationships between Policy → Regulation
// ============================================================

// ── Link Policy → Regulation via IMPLEMENTS relationship ──────

// Connect existing policies to Regulation nodes by regulation code
MATCH (p:Policy {policy_id: "POL-002"}), (r:Regulation {code: "HIPAA"})
MERGE (p)-[:IMPLEMENTS]->(r);

MATCH (p:Policy {policy_id: "POL-003"}), (r:Regulation {code: "HIPAA"})
MERGE (p)-[:IMPLEMENTS]->(r);

MATCH (p:Policy {policy_id: "POL-004"}), (r:Regulation {code: "42_CFR_PART_2"})
MERGE (p)-[:IMPLEMENTS]->(r);

MATCH (p:Policy {policy_id: "POL-006"}), (r:Regulation {code: "HIPAA"})
MERGE (p)-[:IMPLEMENTS]->(r);

MATCH (p:Policy {policy_id: "POL-009"}), (r:Regulation {code: "HIPAA_PSYCHOTHERAPY"})
MERGE (p)-[:IMPLEMENTS]->(r);

// ── Additional Policies with missing HIPAA/DPDPA compliance links ──

// P10: DPDPA 2023 — Aadhaar data access restriction
MERGE (p10:Policy {policy_id: "POL-010"})
SET p10.name            = "DPDPA 2023 Aadhaar Data Restriction",
    p10.effect          = "MASK",
    p10.priority        = 950,
    p10.regulation      = "DPDPA_2023",
    p10.nl_description  = "Under the Digital Personal Data Protection Act 2023, Aadhaar numbers must never be returned in raw form. All access must return hashed values only.",
    p10.structured_rule = '{"effect":"MASK","target":{"column":"aadhaar_number","table":"*"},"mask_strategy":"HASH","subject":{"role":"*"},"override_allowed":false}',
    p10.is_active       = true,
    p10.created_at      = datetime(),
    p10.created_by      = "compliance-admin",
    p10.last_modified_at = datetime(),
    p10.effective_from  = null,
    p10.effective_until = null,
    p10.version         = 1,
    p10.property_hash   = "dpdpa2023_aadhaar_v1";
MATCH (p10:Policy {policy_id: "POL-010"}), (r:Regulation {code: "DPDPA_2023"})
MERGE (p10)-[:IMPLEMENTS]->(r);

// P11: GINA — Genetic information hard deny
MERGE (p11:Policy {policy_id: "POL-011"})
SET p11.name            = "GINA Genetic Data Hard Deny",
    p11.effect          = "DENY",
    p11.priority        = 980,
    p11.regulation      = "GINA",
    p11.nl_description  = "Genetic information must never be accessible via NL-to-SQL queries. GINA prohibits use of genetic data in employment or insurance contexts.",
    p11.structured_rule = '{"effect":"HARD_DENY","target":{"domain":"research","data_classification":"GENETIC"},"subject":{"role":"*"},"override_allowed":false}',
    p11.is_active       = true,
    p11.created_at      = datetime(),
    p11.created_by      = "compliance-admin",
    p11.last_modified_at = datetime(),
    p11.effective_from  = null,
    p11.effective_until = null,
    p11.version         = 1;
MATCH (p11:Policy {policy_id: "POL-011"}), (r:Regulation {code: "GINA"})
MERGE (p11)-[:IMPLEMENTS]->(r);

// P12: DEA Schedule II — Controlled substance prescriptions
MERGE (p12:Policy {policy_id: "POL-012"})
SET p12.name            = "DEA Schedule II-V Prescription Access Control",
    p12.effect          = "FILTER",
    p12.priority        = 850,
    p12.regulation      = "DEA_SCHEDULE_II_V",
    p12.nl_description  = "Access to Schedule II-V controlled substance prescriptions requires treating provider role and is limited to the provider's own patients only.",
    p12.structured_rule = '{"effect":"FILTER","target":{"table":"prescriptions","condition":"schedule IN (2,3,4,5)"},"subject":{"role":"doctor"},"row_filter":"prescribing_provider_id = {{user.provider_id}}"}',
    p12.is_active       = true,
    p12.created_at      = datetime(),
    p12.created_by      = "compliance-admin",
    p12.last_modified_at = datetime(),
    p12.effective_from  = null,
    p12.effective_until = null,
    p12.version         = 1;
MATCH (p12:Policy {policy_id: "POL-012"}), (r:Regulation {code: "DEA_SCHEDULE_II_V"})
MERGE (p12)-[:IMPLEMENTS]->(r);

// P13: STATE_HIV_LAWS — HIV test/status columns hard deny
MERGE (p13:Policy {policy_id: "POL-013"})
SET p13.name            = "State HIV Confidentiality Hard Deny",
    p13.effect          = "DENY",
    p13.priority        = 990,
    p13.regulation      = "STATE_HIV_LAWS",
    p13.nl_description  = "HIV/AIDS test results and status columns are hard denied from all NL-to-SQL output per state HIV confidentiality laws. Even treating providers must use direct EHR access.",
    p13.structured_rule = '{"effect":"HARD_DENY","target":{"column_pattern":"hiv_*","table":"*"},"subject":{"role":"*"},"override_allowed":false}',
    p13.is_active       = true,
    p13.created_at      = datetime(),
    p13.created_by      = "compliance-admin",
    p13.last_modified_at = datetime(),
    p13.effective_from  = null,
    p13.effective_until = null,
    p13.version         = 1;
MATCH (p13:Policy {policy_id: "POL-013"}), (r:Regulation {code: "STATE_HIV_LAWS"})
MERGE (p13)-[:IMPLEMENTS]->(r);

// ── Fix: Set `effect` from `policy_type` on older nodes that still use policy_type ──
MATCH (p:Policy) WHERE p.effect IS NULL AND p.policy_type IS NOT NULL
SET p.effect = p.policy_type;

// ── Fix: Ensure all Policies have `name` ──
MATCH (p:Policy) WHERE p.name IS NULL
SET p.name = p.policy_id;

// ── Fix: Ensure all Policies have `created_by` ──
MATCH (p:Policy) WHERE p.created_by IS NULL
SET p.created_by = "compliance-admin";

// ── Fix: Ensure all Policies have `last_modified_at` ──
MATCH (p:Policy) WHERE p.last_modified_at IS NULL
SET p.last_modified_at = datetime();

// ── Fix: Ensure all Policies have `version` ──
MATCH (p:Policy) WHERE p.version IS NULL
SET p.version = 1;

// ── Regulation: Fix `name` field (spec uses `name`, seed used `full_name`) ──
MATCH (r:Regulation) WHERE r.name IS NULL AND r.full_name IS NOT NULL
SET r.name = r.full_name;

// ── Regulation: Set regulation_id = code if not already set ──
MATCH (r:Regulation) WHERE r.regulation_id IS NULL
SET r.regulation_id = r.code;

// ── Regulation: Fix jurisdiction to FEDERAL | STATE | INDUSTRY enum ──
MATCH (r:Regulation) WHERE r.jurisdiction = "US" OR r.jurisdiction IS NULL
SET r.jurisdiction = "FEDERAL";

MATCH (r:Regulation) WHERE r.code IN ["STATE_MH_LAWS", "STATE_HIV_LAWS"]
SET r.jurisdiction = "STATE";

// ── Regulation: Ensure retention_years on all regulations ──
MATCH (r:Regulation {code: "HIPAA"})              WHERE r.retention_years IS NULL SET r.retention_years = 6;
MATCH (r:Regulation {code: "42_CFR_PART_2"})      WHERE r.retention_years IS NULL SET r.retention_years = 7;
MATCH (r:Regulation {code: "HIPAA_PSYCHOTHERAPY"}) WHERE r.retention_years IS NULL SET r.retention_years = 6;
MATCH (r:Regulation {code: "DPDPA_2023"})         WHERE r.retention_years IS NULL SET r.retention_years = 5;
MATCH (r:Regulation {code: "STATE_MH_LAWS"})      WHERE r.retention_years IS NULL SET r.retention_years = 5;
MATCH (r:Regulation {code: "GINA"})               WHERE r.retention_years IS NULL SET r.retention_years = 3;
MATCH (r:Regulation {code: "DEA_SCHEDULE_II_V"})  WHERE r.retention_years IS NULL SET r.retention_years = 7;
MATCH (r:Regulation {code: "STATE_HIV_LAWS"})     WHERE r.retention_years IS NULL SET r.retention_years = 5;

// ── Additional Condition nodes (for new policies P10-P13) ──

MERGE (cond10:Condition {condition_id: "COND-010"})
SET cond10.condition_type = "COLUMN_MASK",
    cond10.expression     = "SHA256(aadhaar_number) AS aadhaar_number",
    cond10.description    = "Replaces raw Aadhaar with SHA-256 hash in all query outputs",
    cond10.parameters     = '{"algorithm":"SHA256","column":"aadhaar_number"}';
MATCH (p10:Policy {policy_id: "POL-010"}), (cond10:Condition {condition_id: "COND-010"})
MERGE (p10)-[:HAS_CONDITION]->(cond10);

MERGE (cond11:Condition {condition_id: "COND-011"})
SET cond11.condition_type = "ROW_FILTER",
    cond11.expression     = "prescribing_provider_id = {{user.provider_id}}",
    cond11.description    = "Limits controlled substance prescription access to the prescribing provider only",
    cond11.parameters     = '{"field":"prescribing_provider_id","context_key":"user.provider_id"}';
MATCH (p12:Policy {policy_id: "POL-012"}), (cond11:Condition {condition_id: "COND-011"})
MERGE (p12)-[:HAS_CONDITION]->(cond11);

// ── Table → Regulation REGULATED_BY links for new regulation nodes ──
MATCH (t:Table {fqn: "apollo_emr.pharmacy.prescriptions"}), (r:Regulation {code: "DEA_SCHEDULE_II_V"})
MERGE (t)-[:REGULATED_BY]->(r);

MATCH (t:Table {fqn: "apollo_emr.clinical.patients"}), (r:Regulation {code: "GINA"})
MERGE (t)-[:REGULATED_BY]->(r);

MATCH (t:Table {fqn: "apollo_emr.clinical.patients"}), (r:Regulation {code: "STATE_HIV_LAWS"})
MERGE (t)-[:REGULATED_BY]->(r);
