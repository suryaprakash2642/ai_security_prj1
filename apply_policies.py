"""Apply spec-aligned policies to Neo4j."""
from neo4j import GraphDatabase
import json

URI = "neo4j+ssc://5ddec823.databases.neo4j.io"
AUTH = ("5ddec823", "ONSdw4TWjQSwIhR_0edgqxvNF0JS-4dw7df4nxXeiec")
DB = "5ddec823"

POLICIES = [
    # Federal Regulatory (Priority 200)
    dict(policy_id="FED-001", name="42 CFR Part 2 Substance Abuse Protection",
         effect="DENY", priority=200, is_active=True, policy_type="REGULATORY",
         regulation="42_CFR_PART_2",
         nl_description="Substance abuse treatment records are PERMANENTLY DENIED for ALL roles via the NL-to-SQL query system per 42 CFR Part 2. No break-the-glass override.",
         structured_rule='{"type":"TABLE_DENY","tables":["substance_abuse_records","behavioral_health_substance","42cfr_part2"],"exception":"NONE_VIA_QUERY_SYSTEM"}'),

    dict(policy_id="HIPAA-005", name="Psychotherapy Notes Protection",
         effect="DENY", priority=200, is_active=True, policy_type="REGULATORY",
         regulation="HIPAA",
         nl_description="Psychotherapy notes are DENIED for all roles via NL-to-SQL. Access only via dedicated EMR module for the authoring provider.",
         structured_rule='{"type":"TABLE_DENY","tables":["mental_health_records"],"filter":"note_type = PSYCHOTHERAPY","exception":"AUTHORING_PROVIDER_ONLY"}'),

    # Security Boundary (Priority 140-160)
    dict(policy_id="SEC-001", name="No Clinical-HR Cross Join",
         effect="DENY", priority=150, is_active=True, policy_type="SECURITY_BOUNDARY",
         nl_description="Do NOT join clinical tables (encounters, patients, prescriptions, lab_results, vital_signs, clinical_notes) with HR tables (employees, payroll, leave_records, credentials). This prevents correlation of patient outcomes with staff performance.",
         structured_rule='{"type":"JOIN_RESTRICTION","from_domain":"clinical","to_domain":"hr","exception":"NONE"}'),

    dict(policy_id="SEC-002", name="No Payer Contract-Salary Cross Join",
         effect="DENY", priority=150, is_active=True, policy_type="SECURITY_BOUNDARY",
         nl_description="Do NOT join payer contract tables (payer_contracts, insurance_plans) with HR compensation tables (payroll, employees). Prevents exposure of negotiated rates alongside staff compensation.",
         structured_rule='{"type":"JOIN_RESTRICTION","from_tables":["payer_contracts","insurance_plans"],"to_domain":"hr","exception":"NONE"}'),

    dict(policy_id="SEC-003", name="No Genetic-Insurance Cross Join",
         effect="DENY", priority=150, is_active=True, policy_type="SECURITY_BOUNDARY",
         nl_description="Do NOT join genetic or genomic data with billing or insurance tables. GINA prohibits use of genetic information in insurance decisions.",
         structured_rule='{"type":"JOIN_RESTRICTION","from_tables":["genetic_records"],"to_domain":"billing","exception":"NONE"}'),

    # HIPAA Compliance (Priority 80-100)
    dict(policy_id="HIPAA-001", name="Minimum Necessary Standard",
         effect="FILTER", priority=100, is_active=True, policy_type="COMPLIANCE",
         regulation="HIPAA",
         nl_description="All queries MUST include a WHERE clause to limit scope. Unbounded queries are limited to a maximum of 1000 rows. This enforces the HIPAA minimum necessary standard.",
         structured_rule='{"type":"QUERY_SCOPE","max_rows":1000,"require_where":true}'),

    dict(policy_id="CLIN-001", name="Treatment Relationship Required",
         effect="FILTER", priority=90, is_active=True, policy_type="COMPLIANCE",
         regulation="HIPAA",
         nl_description="Filter encounters, clinical_notes, vital_signs, and lab_results to only include rows where treating_provider_id matches the current user OR unit_id matches the users assigned unit.",
         structured_rule='{"type":"ROW_FILTER","tables":["encounters","clinical_notes","vital_signs","lab_results"],"filter":"treating_provider_id = {{user.provider_id}} OR unit_id = {{user.unit_id}}"}'),

    dict(policy_id="HIPAA-003", name="SSN Protection",
         effect="MASK", priority=90, is_active=True, policy_type="COMPLIANCE",
         regulation="HIPAA",
         nl_description="Patient SSN and employee SSN must NEVER be displayed. Always mask SSN columns completely.",
         structured_rule='{"type":"COLUMN_MASK","columns":{"patients.ssn":"FULL","employees.ssn":"FULL"},"mask_format":"***-**-XXXX"}'),

    dict(policy_id="HIPAA-004", name="PII Default Masking",
         effect="MASK", priority=80, is_active=True, policy_type="COMPLIANCE",
         regulation="HIPAA",
         nl_description="When selecting PII columns, apply default masking: phone numbers show last 4 digits only, email addresses show partial, physical addresses are fully redacted, date of birth shows year only for non-clinical roles.",
         structured_rule='{"type":"COLUMN_MASK","strategies":{"phone":"LAST_4","email":"PARTIAL","address":"REDACT","dob":"YEAR_ONLY"},"scope":"non_clinical_roles"}'),

    # Role-Based Access (Priority 40-70)
    dict(policy_id="CLIN-100", name="Doctor Clinical Data Access",
         effect="ALLOW", priority=60, is_active=True, policy_type="ROLE_BASED",
         nl_description="Attending physicians may access clinical patient data including encounters, patients, prescriptions, vital signs, lab results, clinical notes, allergies, and encounter summaries for treatment purposes.",
         structured_rule='{"type":"TABLE_ALLOW","tables":["encounters","patients","prescriptions","vital_signs","lab_results","clinical_notes","allergies","encounter_summaries"],"columns":"*"}'),

    dict(policy_id="NURSE-100", name="Nurse Clinical Data Access",
         effect="ALLOW", priority=50, is_active=True, policy_type="ROLE_BASED",
         nl_description="Registered nurses may access clinical data including encounters, patients, vital signs, prescriptions, allergies, and clinical notes within their assigned unit. PII columns are partially masked.",
         structured_rule='{"type":"TABLE_ALLOW","tables":["encounters","patients","vital_signs","prescriptions","allergies","clinical_notes"],"column_overrides":{"patients":["mrn","full_name","dob","room_number","unit_id","allergies"]}}'),

    dict(policy_id="BIZ-001", name="Billing Minimum Clinical Access",
         effect="ALLOW", priority=50, is_active=True, policy_type="ROLE_BASED",
         nl_description="Billing staff can access patient demographics (mrn, full_name, dob, insurance_id) and encounter codes for claims processing. Full access to claims and patient_billing. CANNOT access clinical_notes, vital_signs, lab_results, prescriptions.",
         structured_rule='{"type":"COLUMN_ALLOW","tables":{"patients":["mrn","full_name","dob","insurance_id","insurance_group"],"encounters":["encounter_id","mrn","date_of_service","discharge_date","facility_id"],"claims":["*"],"claim_line_items":["*"],"patient_billing":["*"],"payments":["*"],"insurance_plans":["*"]},"denied_tables":["clinical_notes","vital_signs","lab_results","prescriptions","imaging_results"]}'),

    dict(policy_id="CLIN-005", name="Pharmacist Medication Access",
         effect="ALLOW", priority=50, is_active=True, policy_type="ROLE_BASED",
         nl_description="Pharmacists can access prescriptions, allergies, and patient basics (mrn, full_name, dob). CANNOT access clinical notes, lab results, vital signs, or billing data.",
         structured_rule='{"type":"TABLE_ALLOW","tables":["prescriptions","allergies"],"column_overrides":{"patients":["mrn","full_name","dob"]},"denied_tables":["clinical_notes","lab_results","vital_signs","encounters"]}'),

    dict(policy_id="BIZ-010", name="Revenue Cycle Aggregate Only",
         effect="ALLOW", priority=50, is_active=True, policy_type="ROLE_BASED",
         nl_description="Revenue Cycle Manager access to encounters, claims, and payments requires aggregate functions (COUNT, SUM, AVG) with GROUP BY. Results must be summary-level only. Individual patient records must NEVER appear. Do NOT include mrn, full_name, ssn, or dob in SELECT.",
         structured_rule='{"type":"AGGREGATION_ONLY","tables":["encounters","claims","payments"],"require_group_by":true,"denied_in_select":["mrn","full_name","ssn","dob"]}'),

    dict(policy_id="HR-001", name="HR Staff Domain Access",
         effect="ALLOW", priority=50, is_active=True, policy_type="ROLE_BASED",
         nl_description="HR managers can access all HR domain tables including employees, payroll, leave records, certifications, credentials, and departments.",
         structured_rule='{"type":"TABLE_ALLOW","domain":"hr","tables":["employees","payroll","leave_records","certifications","credentials","departments"],"columns":"*"}'),

    dict(policy_id="ADMIN-001", name="Hospital Admin Infrastructure Access",
         effect="ALLOW", priority=50, is_active=True, policy_type="ROLE_BASED",
         nl_description="Hospital administrators can access analytics (quality_metrics, encounter_summaries, population_health), general reference data (facilities, units, departments, appointments, staff_schedules), and HR records. CANNOT access clinical patient data directly.",
         structured_rule='{"type":"TABLE_ALLOW","domains":["analytics","general","hr"],"columns":"*"}'),

    dict(policy_id="ADMIN-DENY-CLIN", name="Hospital Admin Clinical Data Deny",
         effect="DENY", priority=200, is_active=True, policy_type="SECURITY_BOUNDARY",
         nl_description="Hospital administrators cannot access clinical patient data via the NL-to-SQL query system.",
         structured_rule='{"type":"TABLE_DENY","domain":"clinical","subject":{"role":"hospital_admin"}}'),

    dict(policy_id="REVENUE-DENY-CLIN", name="Revenue Manager Non-Aggregate Clinical Deny",
         effect="DENY", priority=160, is_active=True, policy_type="SECURITY_BOUNDARY",
         nl_description="Revenue managers cannot directly access clinical patient data. Access to encounters is aggregate-only via BIZ-010. All other clinical tables are denied.",
         structured_rule='{"type":"TABLE_DENY","domain":"clinical","exception":{"tables":["encounters"],"condition":"AGGREGATION_ONLY"}}'),

    dict(policy_id="RES-001", name="Researcher Aggregation-Only Clinical Access",
         effect="ALLOW", priority=50, is_active=True, policy_type="ROLE_BASED",
         nl_description="Clinical researchers can access clinical data only in aggregated form. Must use aggregate functions with GROUP BY. Patient identifiers must NOT appear in SELECT. Max 1000 rows.",
         structured_rule='{"type":"AGGREGATION_ONLY","domain":"clinical","tables":["encounters","patients","prescriptions","vital_signs","lab_results","allergies","encounter_summaries"],"denied_in_select":["mrn","full_name","ssn","dob","aadhaar_number"]}'),

    dict(policy_id="RES-002", name="Researcher Analytics Access",
         effect="ALLOW", priority=50, is_active=True, policy_type="ROLE_BASED",
         nl_description="Clinical researchers can access analytics tables (quality_metrics, population_health, research_cohorts, encounter_summaries) for research.",
         structured_rule='{"type":"TABLE_ALLOW","domain":"analytics","tables":["quality_metrics","population_health","research_cohorts","encounter_summaries"],"columns":"*"}'),

    dict(policy_id="NURSE-PII", name="Nurse PII Masking",
         effect="MASK", priority=90, is_active=True, policy_type="COMPLIANCE",
         nl_description="Nurses may access patient data but PII columns (mrn, full_name, aadhaar_number) must be partially masked.",
         structured_rule='{"type":"COLUMN_MASK","columns":{"patients.mrn":"PARTIAL","patients.full_name":"PARTIAL","patients.aadhaar_number":"FULL"},"mask_strategy":"PARTIAL_MASK"}'),

    dict(policy_id="EMER-001", name="Break-the-Glass Emergency Access",
         effect="ALLOW", priority=300, is_active=True, policy_type="EMERGENCY",
         nl_description="EMERGENCY ACCESS: Break-the-glass protocol activated. Overrides normal access restrictions for clinical emergency. Substance abuse records remain DENIED even under BTG. 4-hour time limit.",
         structured_rule='{"type":"EMERGENCY_OVERRIDE","duration_hours":4,"still_denied":["substance_abuse_records"],"requires":["reason","patient_id"],"triggers":["HIPAA_OFFICER_NOTIFICATION","RETROSPECTIVE_REVIEW"]}'),
]

# Relationship wiring: policy_id -> { roles, domains, tables, conditions }
WIRING = {
    "FED-001":    dict(roles="ALL"),
    "HIPAA-005":  dict(roles="ALL"),
    "SEC-001":    dict(roles="ALL", domains=["clinical", "hr"], conditions=["COND-SEC-001"]),
    "SEC-002":    dict(roles="ALL", domains=["billing", "hr"], conditions=["COND-SEC-002"]),
    "SEC-003":    dict(roles="ALL", conditions=["COND-SEC-003"]),
    "HIPAA-001":  dict(roles="ALL", conditions=["COND-HIPAA-001"]),
    "CLIN-001":   dict(roles=["doctor", "nurse"], domains=["clinical"], conditions=["COND-CLIN-001"],
                       tables=["encounters", "clinical_notes", "vital_signs", "lab_results"]),
    "HIPAA-003":  dict(roles="ALL"),
    "HIPAA-004":  dict(roles="ALL"),
    "CLIN-100":   dict(roles=["doctor"], domains=["clinical"],
                       tables=["encounters", "patients", "prescriptions", "vital_signs",
                               "lab_results", "clinical_notes", "allergies", "encounter_summaries"]),
    "NURSE-100":  dict(roles=["nurse"], domains=["clinical"],
                       tables=["encounters", "patients", "vital_signs", "prescriptions",
                               "allergies", "clinical_notes"]),
    "BIZ-001":    dict(roles=["billing_staff"], domains=["billing"],
                       tables=["claims", "claim_line_items", "payments", "insurance_plans",
                               "patient_billing", "patients", "encounters"]),
    "CLIN-005":   dict(roles=["pharmacist"], domains=["clinical"],
                       tables=["prescriptions", "allergies", "patients"]),
    "BIZ-010":    dict(roles=["revenue_manager"], domains=["billing"],
                       tables=["encounters", "claims", "payments"],
                       conditions=["COND-BIZ-010"]),
    "HR-001":     dict(roles=["hr_manager"], domains=["hr"],
                       tables=["employees", "payroll", "leave_records", "certifications",
                               "credentials", "departments"]),
    "ADMIN-001":  dict(roles=["hospital_admin"], domains=["analytics", "general", "hr"],
                       tables=["quality_metrics", "encounter_summaries", "population_health",
                               "facilities", "units", "departments", "appointments",
                               "staff_schedules", "employees", "payroll", "leave_records",
                               "certifications", "credentials", "research_cohorts"]),
    "ADMIN-DENY-CLIN": dict(roles=["hospital_admin"], domains=["clinical"]),
    "REVENUE-DENY-CLIN": dict(roles=["revenue_manager"], domains=["clinical"]),
    "RES-001":    dict(roles=["researcher"], domains=["clinical"],
                       tables=["encounters", "patients", "prescriptions", "vital_signs",
                               "lab_results", "allergies", "encounter_summaries"],
                       conditions=["COND-RES-001"]),
    "RES-002":    dict(roles=["researcher"], domains=["analytics"],
                       tables=["quality_metrics", "population_health", "research_cohorts",
                               "encounter_summaries"]),
    "NURSE-PII":  dict(roles=["nurse"], tables=["patients"]),
    "EMER-001":   dict(roles="ALL"),
}

# ACCESSES_DOMAIN updates
ROLE_DOMAINS = {
    "doctor": ["clinical", "general"],
    "nurse": ["clinical", "general"],
    "billing_staff": ["billing"],
    "pharmacist": ["clinical"],
    "revenue_manager": ["billing"],
    "hospital_admin": ["analytics", "general", "hr"],
    "hr_manager": ["hr"],
    "researcher": ["clinical", "analytics"],
}


def main():
    driver = GraphDatabase.driver(URI, auth=AUTH)

    with driver.session(database=DB) as s:
        # Step 1: Create all policies
        print("Creating policies...")
        for p in POLICIES:
            try:
                s.run("CREATE (p:Policy) SET p = $props", props=p)
                print(f"  + {p['policy_id']}: {p['name']}")
            except Exception as e:
                print(f"  ERROR {p['policy_id']}: {e}")

        # Step 2: Wire relationships
        print("\nWiring relationships...")
        for pid, w in WIRING.items():
            # Roles
            if w.get("roles") == "ALL":
                result = s.run(
                    "MATCH (p:Policy {policy_id: $pid}), (r:Role) "
                    "MERGE (p)-[:APPLIES_TO_ROLE]->(r) "
                    "RETURN count(*) AS cnt",
                    pid=pid
                )
                cnt = result.single()["cnt"]
                print(f"  {pid} -> ALL roles ({cnt})")
            elif w.get("roles"):
                for role in w["roles"]:
                    s.run(
                        "MATCH (p:Policy {policy_id: $pid}), (r:Role {name: $role}) "
                        "MERGE (p)-[:APPLIES_TO_ROLE]->(r)",
                        pid=pid, role=role
                    )
                print(f"  {pid} -> roles: {w['roles']}")

            # Domains
            for domain in w.get("domains", []):
                s.run(
                    "MATCH (p:Policy {policy_id: $pid}), (d:Domain {name: $domain}) "
                    "MERGE (p)-[:GOVERNS_DOMAIN]->(d)",
                    pid=pid, domain=domain
                )
            if w.get("domains"):
                print(f"  {pid} -> domains: {w['domains']}")

            # Tables
            for tname in w.get("tables", []):
                s.run(
                    "MATCH (p:Policy {policy_id: $pid}), (t:Table {name: $tname}) "
                    "WHERE t.is_active = true "
                    "MERGE (p)-[:GOVERNS_TABLE]->(t)",
                    pid=pid, tname=tname
                )
            if w.get("tables"):
                print(f"  {pid} -> tables: {w['tables']}")

            # Conditions
            for cid in w.get("conditions", []):
                s.run(
                    "MATCH (p:Policy {policy_id: $pid}), (c:Condition {condition_id: $cid}) "
                    "MERGE (p)-[:HAS_CONDITION]->(c)",
                    pid=pid, cid=cid
                )
            if w.get("conditions"):
                print(f"  {pid} -> conditions: {w['conditions']}")

        # Step 3: Update ACCESSES_DOMAIN
        print("\nUpdating ACCESSES_DOMAIN...")
        for role, domains in ROLE_DOMAINS.items():
            for domain in domains:
                s.run(
                    "MATCH (r:Role {name: $role}), (d:Domain {name: $domain}) "
                    "MERGE (r)-[:ACCESSES_DOMAIN]->(d)",
                    role=role, domain=domain
                )
            print(f"  {role} -> {domains}")

    driver.close()
    print("\nAll policies applied!")


if __name__ == "__main__":
    main()
