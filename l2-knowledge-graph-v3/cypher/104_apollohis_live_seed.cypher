// ============================================================
// ApolloHIS — Hospital Information System (AWS RDS SQL Server)
// Auto-generated from live crawl at 2026-03-03 19:28:09
// ============================================================

// --- Database ---
MERGE (db:Database {name: "ApolloHIS"})
SET db.engine = "sqlserver", db.is_active = true,
    db.created_at = datetime(), db.source = "live_crawl";

// --- Schemas ---
MERGE (s0:Schema {fqn: "ApolloHIS.dbo"})
SET s0.name = "dbo", s0.is_active = true;

MERGE (db)-[:HAS_SCHEMA]->(s0);

// --- Tables ---
MERGE (t0:Table {fqn: "ApolloHIS.dbo.allergies"})
SET t0.name = "allergies", t0.is_active = true,
    t0.row_count_approx = 300,
    t0.sensitivity_level = 4, t0.has_pii = true,
    t0.domain = "general", t0.source = "live_crawl";

MERGE (t1:Table {fqn: "ApolloHIS.dbo.appointments"})
SET t1.name = "appointments", t1.is_active = true,
    t1.row_count_approx = 2000,
    t1.sensitivity_level = 0, t1.has_pii = false,
    t1.domain = "general", t1.source = "live_crawl";

MERGE (t2:Table {fqn: "ApolloHIS.dbo.clinical_notes"})
SET t2.name = "clinical_notes", t2.is_active = true,
    t2.row_count_approx = 1000,
    t2.sensitivity_level = 3, t2.has_pii = true,
    t2.domain = "general", t2.source = "live_crawl";

MERGE (t3:Table {fqn: "ApolloHIS.dbo.departments"})
SET t3.name = "departments", t3.is_active = true,
    t3.row_count_approx = 104,
    t3.sensitivity_level = 0, t3.has_pii = false,
    t3.domain = "hr", t3.source = "live_crawl";

MERGE (t4:Table {fqn: "ApolloHIS.dbo.encounters"})
SET t4.name = "encounters", t4.is_active = true,
    t4.row_count_approx = 1500,
    t4.sensitivity_level = 3, t4.has_pii = true,
    t4.domain = "clinical", t4.source = "live_crawl";

MERGE (t5:Table {fqn: "ApolloHIS.dbo.facilities"})
SET t5.name = "facilities", t5.is_active = true,
    t5.row_count_approx = 8,
    t5.sensitivity_level = 3, t5.has_pii = true,
    t5.domain = "general", t5.source = "live_crawl";

MERGE (t6:Table {fqn: "ApolloHIS.dbo.lab_results"})
SET t6.name = "lab_results", t6.is_active = true,
    t6.row_count_approx = 4000,
    t6.sensitivity_level = 3, t6.has_pii = true,
    t6.domain = "clinical", t6.source = "live_crawl";

MERGE (t7:Table {fqn: "ApolloHIS.dbo.patients"})
SET t7.name = "patients", t7.is_active = true,
    t7.row_count_approx = 500,
    t7.sensitivity_level = 5, t7.has_pii = true,
    t7.domain = "clinical", t7.source = "live_crawl";

MERGE (t8:Table {fqn: "ApolloHIS.dbo.prescriptions"})
SET t8.name = "prescriptions", t8.is_active = true,
    t8.row_count_approx = 3000,
    t8.sensitivity_level = 3, t8.has_pii = true,
    t8.domain = "clinical", t8.source = "live_crawl";

MERGE (t9:Table {fqn: "ApolloHIS.dbo.staff_schedules"})
SET t9.name = "staff_schedules", t9.is_active = true,
    t9.row_count_approx = 0,
    t9.sensitivity_level = 0, t9.has_pii = false,
    t9.domain = "general", t9.source = "live_crawl";

MERGE (t10:Table {fqn: "ApolloHIS.dbo.units"})
SET t10.name = "units", t10.is_active = true,
    t10.row_count_approx = 72,
    t10.sensitivity_level = 0, t10.has_pii = false,
    t10.domain = "general", t10.source = "live_crawl";

MERGE (t11:Table {fqn: "ApolloHIS.dbo.vital_signs"})
SET t11.name = "vital_signs", t11.is_active = true,
    t11.row_count_approx = 5000,
    t11.sensitivity_level = 3, t11.has_pii = true,
    t11.domain = "clinical", t11.source = "live_crawl";

// Schema-Table links
MERGE (s0)-[:HAS_TABLE]->(t0);
MERGE (s0)-[:HAS_TABLE]->(t1);
MERGE (s0)-[:HAS_TABLE]->(t2);
MERGE (s0)-[:HAS_TABLE]->(t3);
MERGE (s0)-[:HAS_TABLE]->(t4);
MERGE (s0)-[:HAS_TABLE]->(t5);
MERGE (s0)-[:HAS_TABLE]->(t6);
MERGE (s0)-[:HAS_TABLE]->(t7);
MERGE (s0)-[:HAS_TABLE]->(t8);
MERGE (s0)-[:HAS_TABLE]->(t9);
MERGE (s0)-[:HAS_TABLE]->(t10);
MERGE (s0)-[:HAS_TABLE]->(t11);

// --- Columns (allergies) ---
MERGE (c0:Column {fqn: "ApolloHIS.dbo.allergies.allergy_id"})
SET c0.name = "allergy_id", c0.data_type = "varchar", c0.is_pk = true, c0.is_nullable = false, c0.ordinal_position = 1, c0.sensitivity_level = 4, c0.is_pii = true, c0.pii_type = "MEDICAL", c0.masking_strategy = "REDACT", c0.is_active = true;

MERGE (c1:Column {fqn: "ApolloHIS.dbo.allergies.patient_id"})
SET c1.name = "patient_id", c1.data_type = "varchar", c1.is_nullable = false, c1.ordinal_position = 2, c1.is_active = true;

MERGE (c2:Column {fqn: "ApolloHIS.dbo.allergies.allergen"})
SET c2.name = "allergen", c2.data_type = "nvarchar", c2.is_nullable = false, c2.ordinal_position = 3, c2.sensitivity_level = 4, c2.is_pii = true, c2.pii_type = "MEDICAL", c2.masking_strategy = "REDACT", c2.is_active = true;

MERGE (c3:Column {fqn: "ApolloHIS.dbo.allergies.allergy_type"})
SET c3.name = "allergy_type", c3.data_type = "varchar", c3.is_nullable = true, c3.ordinal_position = 4, c3.sensitivity_level = 4, c3.is_pii = true, c3.pii_type = "MEDICAL", c3.masking_strategy = "REDACT", c3.is_active = true;

MERGE (c4:Column {fqn: "ApolloHIS.dbo.allergies.severity"})
SET c4.name = "severity", c4.data_type = "varchar", c4.is_nullable = true, c4.ordinal_position = 5, c4.is_active = true;

MERGE (c5:Column {fqn: "ApolloHIS.dbo.allergies.reaction"})
SET c5.name = "reaction", c5.data_type = "nvarchar", c5.is_nullable = true, c5.ordinal_position = 6, c5.is_active = true;

MERGE (c6:Column {fqn: "ApolloHIS.dbo.allergies.onset_date"})
SET c6.name = "onset_date", c6.data_type = "date", c6.is_nullable = true, c6.ordinal_position = 7, c6.is_active = true;

MERGE (c7:Column {fqn: "ApolloHIS.dbo.allergies.reported_by"})
SET c7.name = "reported_by", c7.data_type = "varchar", c7.is_nullable = true, c7.ordinal_position = 8, c7.is_active = true;

MERGE (c8:Column {fqn: "ApolloHIS.dbo.allergies.is_active"})
SET c8.name = "is_active", c8.data_type = "bit", c8.is_nullable = true, c8.ordinal_position = 9, c8.is_active = true;

MERGE (c9:Column {fqn: "ApolloHIS.dbo.allergies.created_at"})
SET c9.name = "created_at", c9.data_type = "datetime2", c9.is_nullable = true, c9.ordinal_position = 10, c9.is_active = true;

// Column-Table links (allergies)
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

// --- Columns (appointments) ---
MERGE (c10:Column {fqn: "ApolloHIS.dbo.appointments.appointment_id"})
SET c10.name = "appointment_id", c10.data_type = "varchar", c10.is_pk = true, c10.is_nullable = false, c10.ordinal_position = 1, c10.is_active = true;

MERGE (c11:Column {fqn: "ApolloHIS.dbo.appointments.patient_id"})
SET c11.name = "patient_id", c11.data_type = "varchar", c11.is_nullable = false, c11.ordinal_position = 2, c11.is_active = true;

MERGE (c12:Column {fqn: "ApolloHIS.dbo.appointments.provider_id"})
SET c12.name = "provider_id", c12.data_type = "varchar", c12.is_nullable = false, c12.ordinal_position = 3, c12.is_active = true;

MERGE (c13:Column {fqn: "ApolloHIS.dbo.appointments.facility_id"})
SET c13.name = "facility_id", c13.data_type = "varchar", c13.is_nullable = false, c13.ordinal_position = 4, c13.is_active = true;

MERGE (c14:Column {fqn: "ApolloHIS.dbo.appointments.department_id"})
SET c14.name = "department_id", c14.data_type = "varchar", c14.is_nullable = true, c14.ordinal_position = 5, c14.is_active = true;

MERGE (c15:Column {fqn: "ApolloHIS.dbo.appointments.appointment_datetime"})
SET c15.name = "appointment_datetime", c15.data_type = "datetime2", c15.is_nullable = false, c15.ordinal_position = 6, c15.is_active = true;

MERGE (c16:Column {fqn: "ApolloHIS.dbo.appointments.duration_minutes"})
SET c16.name = "duration_minutes", c16.data_type = "int", c16.is_nullable = true, c16.ordinal_position = 7, c16.is_active = true;

MERGE (c17:Column {fqn: "ApolloHIS.dbo.appointments.appointment_type"})
SET c17.name = "appointment_type", c17.data_type = "varchar", c17.is_nullable = true, c17.ordinal_position = 8, c17.is_active = true;

MERGE (c18:Column {fqn: "ApolloHIS.dbo.appointments.status"})
SET c18.name = "status", c18.data_type = "varchar", c18.is_nullable = true, c18.ordinal_position = 9, c18.is_active = true;

MERGE (c19:Column {fqn: "ApolloHIS.dbo.appointments.reason_for_visit"})
SET c19.name = "reason_for_visit", c19.data_type = "nvarchar", c19.is_nullable = true, c19.ordinal_position = 10, c19.is_active = true;

MERGE (c20:Column {fqn: "ApolloHIS.dbo.appointments.notes"})
SET c20.name = "notes", c20.data_type = "nvarchar", c20.is_nullable = true, c20.ordinal_position = 11, c20.is_active = true;

MERGE (c21:Column {fqn: "ApolloHIS.dbo.appointments.is_telemedicine"})
SET c21.name = "is_telemedicine", c21.data_type = "bit", c21.is_nullable = true, c21.ordinal_position = 12, c21.is_active = true;

MERGE (c22:Column {fqn: "ApolloHIS.dbo.appointments.cancellation_reason"})
SET c22.name = "cancellation_reason", c22.data_type = "nvarchar", c22.is_nullable = true, c22.ordinal_position = 13, c22.is_active = true;

MERGE (c23:Column {fqn: "ApolloHIS.dbo.appointments.created_at"})
SET c23.name = "created_at", c23.data_type = "datetime2", c23.is_nullable = true, c23.ordinal_position = 14, c23.is_active = true;

// Column-Table links (appointments)
MERGE (t1)-[:HAS_COLUMN]->(c10);
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

// --- Columns (clinical_notes) ---
MERGE (c24:Column {fqn: "ApolloHIS.dbo.clinical_notes.note_id"})
SET c24.name = "note_id", c24.data_type = "varchar", c24.is_pk = true, c24.is_nullable = false, c24.ordinal_position = 1, c24.sensitivity_level = 3, c24.is_pii = true, c24.pii_type = "CLINICAL_CONTEXT", c24.masking_strategy = "REVIEW", c24.is_active = true;

MERGE (c25:Column {fqn: "ApolloHIS.dbo.clinical_notes.encounter_id"})
SET c25.name = "encounter_id", c25.data_type = "varchar", c25.is_nullable = false, c25.ordinal_position = 2, c25.sensitivity_level = 3, c25.is_pii = true, c25.pii_type = "CLINICAL_CONTEXT", c25.masking_strategy = "REVIEW", c25.is_active = true;

MERGE (c26:Column {fqn: "ApolloHIS.dbo.clinical_notes.patient_id"})
SET c26.name = "patient_id", c26.data_type = "varchar", c26.is_nullable = false, c26.ordinal_position = 3, c26.sensitivity_level = 3, c26.is_pii = true, c26.pii_type = "CLINICAL_CONTEXT", c26.masking_strategy = "REVIEW", c26.is_active = true;

MERGE (c27:Column {fqn: "ApolloHIS.dbo.clinical_notes.author_id"})
SET c27.name = "author_id", c27.data_type = "varchar", c27.is_nullable = false, c27.ordinal_position = 4, c27.sensitivity_level = 3, c27.is_pii = true, c27.pii_type = "CLINICAL_CONTEXT", c27.masking_strategy = "REVIEW", c27.is_active = true;

MERGE (c28:Column {fqn: "ApolloHIS.dbo.clinical_notes.note_type"})
SET c28.name = "note_type", c28.data_type = "varchar", c28.is_nullable = false, c28.ordinal_position = 5, c28.sensitivity_level = 3, c28.is_pii = true, c28.pii_type = "CLINICAL_CONTEXT", c28.masking_strategy = "REVIEW", c28.is_active = true;

MERGE (c29:Column {fqn: "ApolloHIS.dbo.clinical_notes.note_datetime"})
SET c29.name = "note_datetime", c29.data_type = "datetime2", c29.is_nullable = false, c29.ordinal_position = 6, c29.sensitivity_level = 3, c29.is_pii = true, c29.pii_type = "CLINICAL_CONTEXT", c29.masking_strategy = "REVIEW", c29.is_active = true;

MERGE (c30:Column {fqn: "ApolloHIS.dbo.clinical_notes.note_text"})
SET c30.name = "note_text", c30.data_type = "nvarchar", c30.is_nullable = false, c30.ordinal_position = 7, c30.sensitivity_level = 3, c30.is_pii = true, c30.pii_type = "CLINICAL_CONTEXT", c30.masking_strategy = "REVIEW", c30.is_active = true;

MERGE (c31:Column {fqn: "ApolloHIS.dbo.clinical_notes.is_addendum"})
SET c31.name = "is_addendum", c31.data_type = "bit", c31.is_nullable = true, c31.ordinal_position = 8, c31.sensitivity_level = 3, c31.is_pii = true, c31.pii_type = "CLINICAL_CONTEXT", c31.masking_strategy = "REVIEW", c31.is_active = true;

MERGE (c32:Column {fqn: "ApolloHIS.dbo.clinical_notes.parent_note_id"})
SET c32.name = "parent_note_id", c32.data_type = "varchar", c32.is_nullable = true, c32.ordinal_position = 9, c32.sensitivity_level = 3, c32.is_pii = true, c32.pii_type = "CLINICAL_CONTEXT", c32.masking_strategy = "REVIEW", c32.is_active = true;

MERGE (c33:Column {fqn: "ApolloHIS.dbo.clinical_notes.is_signed"})
SET c33.name = "is_signed", c33.data_type = "bit", c33.is_nullable = true, c33.ordinal_position = 10, c33.sensitivity_level = 3, c33.is_pii = true, c33.pii_type = "CLINICAL_CONTEXT", c33.masking_strategy = "REVIEW", c33.is_active = true;

MERGE (c34:Column {fqn: "ApolloHIS.dbo.clinical_notes.signed_datetime"})
SET c34.name = "signed_datetime", c34.data_type = "datetime2", c34.is_nullable = true, c34.ordinal_position = 11, c34.sensitivity_level = 3, c34.is_pii = true, c34.pii_type = "CLINICAL_CONTEXT", c34.masking_strategy = "REVIEW", c34.is_active = true;

MERGE (c35:Column {fqn: "ApolloHIS.dbo.clinical_notes.created_at"})
SET c35.name = "created_at", c35.data_type = "datetime2", c35.is_nullable = true, c35.ordinal_position = 12, c35.sensitivity_level = 3, c35.is_pii = true, c35.pii_type = "CLINICAL_CONTEXT", c35.masking_strategy = "REVIEW", c35.is_active = true;

// Column-Table links (clinical_notes)
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

// --- Columns (departments) ---
MERGE (c36:Column {fqn: "ApolloHIS.dbo.departments.department_id"})
SET c36.name = "department_id", c36.data_type = "varchar", c36.is_pk = true, c36.is_nullable = false, c36.ordinal_position = 1, c36.is_active = true;

MERGE (c37:Column {fqn: "ApolloHIS.dbo.departments.department_name"})
SET c37.name = "department_name", c37.data_type = "nvarchar", c37.is_nullable = false, c37.ordinal_position = 2, c37.is_active = true;

MERGE (c38:Column {fqn: "ApolloHIS.dbo.departments.domain"})
SET c38.name = "domain", c38.data_type = "varchar", c38.is_nullable = false, c38.ordinal_position = 3, c38.is_active = true;

MERGE (c39:Column {fqn: "ApolloHIS.dbo.departments.facility_id"})
SET c39.name = "facility_id", c39.data_type = "varchar", c39.is_nullable = true, c39.ordinal_position = 4, c39.is_active = true;

MERGE (c40:Column {fqn: "ApolloHIS.dbo.departments.head_employee_id"})
SET c40.name = "head_employee_id", c40.data_type = "varchar", c40.is_nullable = true, c40.ordinal_position = 5, c40.is_active = true;

MERGE (c41:Column {fqn: "ApolloHIS.dbo.departments.floor_number"})
SET c41.name = "floor_number", c41.data_type = "int", c41.is_nullable = true, c41.ordinal_position = 6, c41.is_active = true;

MERGE (c42:Column {fqn: "ApolloHIS.dbo.departments.extension"})
SET c42.name = "extension", c42.data_type = "varchar", c42.is_nullable = true, c42.ordinal_position = 7, c42.is_active = true;

MERGE (c43:Column {fqn: "ApolloHIS.dbo.departments.is_active"})
SET c43.name = "is_active", c43.data_type = "bit", c43.is_nullable = true, c43.ordinal_position = 8, c43.is_active = true;

MERGE (c44:Column {fqn: "ApolloHIS.dbo.departments.created_at"})
SET c44.name = "created_at", c44.data_type = "datetime2", c44.is_nullable = true, c44.ordinal_position = 9, c44.is_active = true;

// Column-Table links (departments)
MERGE (t3)-[:HAS_COLUMN]->(c36);
MERGE (t3)-[:HAS_COLUMN]->(c37);
MERGE (t3)-[:HAS_COLUMN]->(c38);
MERGE (t3)-[:HAS_COLUMN]->(c39);
MERGE (t3)-[:HAS_COLUMN]->(c40);
MERGE (t3)-[:HAS_COLUMN]->(c41);
MERGE (t3)-[:HAS_COLUMN]->(c42);
MERGE (t3)-[:HAS_COLUMN]->(c43);
MERGE (t3)-[:HAS_COLUMN]->(c44);

// --- Columns (encounters) ---
MERGE (c45:Column {fqn: "ApolloHIS.dbo.encounters.encounter_id"})
SET c45.name = "encounter_id", c45.data_type = "varchar", c45.is_pk = true, c45.is_nullable = false, c45.ordinal_position = 1, c45.sensitivity_level = 3, c45.is_pii = true, c45.pii_type = "CLINICAL_CONTEXT", c45.masking_strategy = "REVIEW", c45.is_active = true;

MERGE (c46:Column {fqn: "ApolloHIS.dbo.encounters.patient_id"})
SET c46.name = "patient_id", c46.data_type = "varchar", c46.is_nullable = false, c46.ordinal_position = 2, c46.sensitivity_level = 3, c46.is_pii = true, c46.pii_type = "CLINICAL_CONTEXT", c46.masking_strategy = "REVIEW", c46.is_active = true;

MERGE (c47:Column {fqn: "ApolloHIS.dbo.encounters.encounter_type"})
SET c47.name = "encounter_type", c47.data_type = "varchar", c47.is_nullable = false, c47.ordinal_position = 3, c47.sensitivity_level = 3, c47.is_pii = true, c47.pii_type = "CLINICAL_CONTEXT", c47.masking_strategy = "REVIEW", c47.is_active = true;

MERGE (c48:Column {fqn: "ApolloHIS.dbo.encounters.facility_id"})
SET c48.name = "facility_id", c48.data_type = "varchar", c48.is_nullable = false, c48.ordinal_position = 4, c48.sensitivity_level = 3, c48.is_pii = true, c48.pii_type = "CLINICAL_CONTEXT", c48.masking_strategy = "REVIEW", c48.is_active = true;

MERGE (c49:Column {fqn: "ApolloHIS.dbo.encounters.department_id"})
SET c49.name = "department_id", c49.data_type = "varchar", c49.is_nullable = true, c49.ordinal_position = 5, c49.sensitivity_level = 3, c49.is_pii = true, c49.pii_type = "CLINICAL_CONTEXT", c49.masking_strategy = "REVIEW", c49.is_active = true;

MERGE (c50:Column {fqn: "ApolloHIS.dbo.encounters.unit_id"})
SET c50.name = "unit_id", c50.data_type = "varchar", c50.is_nullable = true, c50.ordinal_position = 6, c50.sensitivity_level = 3, c50.is_pii = true, c50.pii_type = "CLINICAL_CONTEXT", c50.masking_strategy = "REVIEW", c50.is_active = true;

MERGE (c51:Column {fqn: "ApolloHIS.dbo.encounters.treating_provider_id"})
SET c51.name = "treating_provider_id", c51.data_type = "varchar", c51.is_nullable = true, c51.ordinal_position = 7, c51.sensitivity_level = 3, c51.is_pii = true, c51.pii_type = "CLINICAL_CONTEXT", c51.masking_strategy = "REVIEW", c51.is_active = true;

MERGE (c52:Column {fqn: "ApolloHIS.dbo.encounters.attending_provider_id"})
SET c52.name = "attending_provider_id", c52.data_type = "varchar", c52.is_nullable = true, c52.ordinal_position = 8, c52.sensitivity_level = 3, c52.is_pii = true, c52.pii_type = "CLINICAL_CONTEXT", c52.masking_strategy = "REVIEW", c52.is_active = true;

MERGE (c53:Column {fqn: "ApolloHIS.dbo.encounters.admission_date"})
SET c53.name = "admission_date", c53.data_type = "datetime2", c53.is_nullable = false, c53.ordinal_position = 9, c53.sensitivity_level = 3, c53.is_pii = true, c53.pii_type = "CLINICAL_CONTEXT", c53.masking_strategy = "REVIEW", c53.is_active = true;

MERGE (c54:Column {fqn: "ApolloHIS.dbo.encounters.discharge_date"})
SET c54.name = "discharge_date", c54.data_type = "datetime2", c54.is_nullable = true, c54.ordinal_position = 10, c54.sensitivity_level = 3, c54.is_pii = true, c54.pii_type = "CLINICAL_CONTEXT", c54.masking_strategy = "REVIEW", c54.is_active = true;

MERGE (c55:Column {fqn: "ApolloHIS.dbo.encounters.expected_discharge"})
SET c55.name = "expected_discharge", c55.data_type = "date", c55.is_nullable = true, c55.ordinal_position = 11, c55.sensitivity_level = 3, c55.is_pii = true, c55.pii_type = "CLINICAL_CONTEXT", c55.masking_strategy = "REVIEW", c55.is_active = true;

MERGE (c56:Column {fqn: "ApolloHIS.dbo.encounters.length_of_stay_days"})
SET c56.name = "length_of_stay_days", c56.data_type = "int", c56.is_nullable = true, c56.ordinal_position = 12, c56.sensitivity_level = 3, c56.is_pii = true, c56.pii_type = "CLINICAL_CONTEXT", c56.masking_strategy = "REVIEW", c56.is_active = true;

MERGE (c57:Column {fqn: "ApolloHIS.dbo.encounters.primary_dx_code"})
SET c57.name = "primary_dx_code", c57.data_type = "varchar", c57.is_nullable = true, c57.ordinal_position = 13, c57.sensitivity_level = 3, c57.is_pii = true, c57.pii_type = "CLINICAL_CONTEXT", c57.masking_strategy = "REVIEW", c57.is_active = true;

MERGE (c58:Column {fqn: "ApolloHIS.dbo.encounters.primary_dx_desc"})
SET c58.name = "primary_dx_desc", c58.data_type = "nvarchar", c58.is_nullable = true, c58.ordinal_position = 14, c58.sensitivity_level = 3, c58.is_pii = true, c58.pii_type = "CLINICAL_CONTEXT", c58.masking_strategy = "REVIEW", c58.is_active = true;

MERGE (c59:Column {fqn: "ApolloHIS.dbo.encounters.secondary_dx_codes"})
SET c59.name = "secondary_dx_codes", c59.data_type = "nvarchar", c59.is_nullable = true, c59.ordinal_position = 15, c59.sensitivity_level = 3, c59.is_pii = true, c59.pii_type = "CLINICAL_CONTEXT", c59.masking_strategy = "REVIEW", c59.is_active = true;

MERGE (c60:Column {fqn: "ApolloHIS.dbo.encounters.procedure_codes"})
SET c60.name = "procedure_codes", c60.data_type = "nvarchar", c60.is_nullable = true, c60.ordinal_position = 16, c60.sensitivity_level = 3, c60.is_pii = true, c60.pii_type = "CLINICAL_CONTEXT", c60.masking_strategy = "REVIEW", c60.is_active = true;

MERGE (c61:Column {fqn: "ApolloHIS.dbo.encounters.admission_source"})
SET c61.name = "admission_source", c61.data_type = "varchar", c61.is_nullable = true, c61.ordinal_position = 17, c61.sensitivity_level = 3, c61.is_pii = true, c61.pii_type = "CLINICAL_CONTEXT", c61.masking_strategy = "REVIEW", c61.is_active = true;

MERGE (c62:Column {fqn: "ApolloHIS.dbo.encounters.discharge_disposition"})
SET c62.name = "discharge_disposition", c62.data_type = "varchar", c62.is_nullable = true, c62.ordinal_position = 18, c62.sensitivity_level = 3, c62.is_pii = true, c62.pii_type = "CLINICAL_CONTEXT", c62.masking_strategy = "REVIEW", c62.is_active = true;

MERGE (c63:Column {fqn: "ApolloHIS.dbo.encounters.bed_number"})
SET c63.name = "bed_number", c63.data_type = "varchar", c63.is_nullable = true, c63.ordinal_position = 19, c63.sensitivity_level = 3, c63.is_pii = true, c63.pii_type = "CLINICAL_CONTEXT", c63.masking_strategy = "REVIEW", c63.is_active = true;

MERGE (c64:Column {fqn: "ApolloHIS.dbo.encounters.room_type"})
SET c64.name = "room_type", c64.data_type = "varchar", c64.is_nullable = true, c64.ordinal_position = 20, c64.sensitivity_level = 3, c64.is_pii = true, c64.pii_type = "CLINICAL_CONTEXT", c64.masking_strategy = "REVIEW", c64.is_active = true;

MERGE (c65:Column {fqn: "ApolloHIS.dbo.encounters.acuity_level"})
SET c65.name = "acuity_level", c65.data_type = "int", c65.is_nullable = true, c65.ordinal_position = 21, c65.sensitivity_level = 3, c65.is_pii = true, c65.pii_type = "CLINICAL_CONTEXT", c65.masking_strategy = "REVIEW", c65.is_active = true;

MERGE (c66:Column {fqn: "ApolloHIS.dbo.encounters.is_readmission"})
SET c66.name = "is_readmission", c66.data_type = "bit", c66.is_nullable = true, c66.ordinal_position = 22, c66.sensitivity_level = 3, c66.is_pii = true, c66.pii_type = "CLINICAL_CONTEXT", c66.masking_strategy = "REVIEW", c66.is_active = true;

MERGE (c67:Column {fqn: "ApolloHIS.dbo.encounters.btg_access_flag"})
SET c67.name = "btg_access_flag", c67.data_type = "bit", c67.is_nullable = true, c67.ordinal_position = 23, c67.sensitivity_level = 3, c67.is_pii = true, c67.pii_type = "CLINICAL_CONTEXT", c67.masking_strategy = "REVIEW", c67.is_active = true;

MERGE (c68:Column {fqn: "ApolloHIS.dbo.encounters.status"})
SET c68.name = "status", c68.data_type = "varchar", c68.is_nullable = true, c68.ordinal_position = 24, c68.sensitivity_level = 3, c68.is_pii = true, c68.pii_type = "CLINICAL_CONTEXT", c68.masking_strategy = "REVIEW", c68.is_active = true;

MERGE (c69:Column {fqn: "ApolloHIS.dbo.encounters.created_at"})
SET c69.name = "created_at", c69.data_type = "datetime2", c69.is_nullable = true, c69.ordinal_position = 25, c69.sensitivity_level = 3, c69.is_pii = true, c69.pii_type = "CLINICAL_CONTEXT", c69.masking_strategy = "REVIEW", c69.is_active = true;

MERGE (c70:Column {fqn: "ApolloHIS.dbo.encounters.updated_at"})
SET c70.name = "updated_at", c70.data_type = "datetime2", c70.is_nullable = true, c70.ordinal_position = 26, c70.sensitivity_level = 3, c70.is_pii = true, c70.pii_type = "CLINICAL_CONTEXT", c70.masking_strategy = "REVIEW", c70.is_active = true;

// Column-Table links (encounters)
MERGE (t4)-[:HAS_COLUMN]->(c45);
MERGE (t4)-[:HAS_COLUMN]->(c46);
MERGE (t4)-[:HAS_COLUMN]->(c47);
MERGE (t4)-[:HAS_COLUMN]->(c48);
MERGE (t4)-[:HAS_COLUMN]->(c49);
MERGE (t4)-[:HAS_COLUMN]->(c50);
MERGE (t4)-[:HAS_COLUMN]->(c51);
MERGE (t4)-[:HAS_COLUMN]->(c52);
MERGE (t4)-[:HAS_COLUMN]->(c53);
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

// --- Columns (facilities) ---
MERGE (c71:Column {fqn: "ApolloHIS.dbo.facilities.facility_id"})
SET c71.name = "facility_id", c71.data_type = "varchar", c71.is_pk = true, c71.is_nullable = false, c71.ordinal_position = 1, c71.is_active = true;

MERGE (c72:Column {fqn: "ApolloHIS.dbo.facilities.facility_name"})
SET c72.name = "facility_name", c72.data_type = "nvarchar", c72.is_nullable = false, c72.ordinal_position = 2, c72.is_active = true;

MERGE (c73:Column {fqn: "ApolloHIS.dbo.facilities.city"})
SET c73.name = "city", c73.data_type = "nvarchar", c73.is_nullable = false, c73.ordinal_position = 3, c73.sensitivity_level = 2, c73.is_pii = true, c73.pii_type = "ADDRESS", c73.masking_strategy = "GENERALIZE", c73.is_active = true;

MERGE (c74:Column {fqn: "ApolloHIS.dbo.facilities.state"})
SET c74.name = "state", c74.data_type = "nvarchar", c74.is_nullable = false, c74.ordinal_position = 4, c74.sensitivity_level = 2, c74.is_pii = true, c74.pii_type = "ADDRESS", c74.masking_strategy = "GENERALIZE", c74.is_active = true;

MERGE (c75:Column {fqn: "ApolloHIS.dbo.facilities.facility_code"})
SET c75.name = "facility_code", c75.data_type = "varchar", c75.is_nullable = false, c75.ordinal_position = 5, c75.is_active = true;

MERGE (c76:Column {fqn: "ApolloHIS.dbo.facilities.total_beds"})
SET c76.name = "total_beds", c76.data_type = "int", c76.is_nullable = false, c76.ordinal_position = 6, c76.is_active = true;

MERGE (c77:Column {fqn: "ApolloHIS.dbo.facilities.nabh_accredited"})
SET c77.name = "nabh_accredited", c77.data_type = "bit", c77.is_nullable = true, c77.ordinal_position = 7, c77.is_active = true;

MERGE (c78:Column {fqn: "ApolloHIS.dbo.facilities.jci_accredited"})
SET c78.name = "jci_accredited", c78.data_type = "bit", c78.is_nullable = true, c78.ordinal_position = 8, c78.is_active = true;

MERGE (c79:Column {fqn: "ApolloHIS.dbo.facilities.established_year"})
SET c79.name = "established_year", c79.data_type = "int", c79.is_nullable = true, c79.ordinal_position = 9, c79.is_active = true;

MERGE (c80:Column {fqn: "ApolloHIS.dbo.facilities.address"})
SET c80.name = "address", c80.data_type = "nvarchar", c80.is_nullable = true, c80.ordinal_position = 10, c80.sensitivity_level = 3, c80.is_pii = true, c80.pii_type = "ADDRESS", c80.masking_strategy = "REDACT", c80.is_active = true;

MERGE (c81:Column {fqn: "ApolloHIS.dbo.facilities.phone"})
SET c81.name = "phone", c81.data_type = "varchar", c81.is_nullable = true, c81.ordinal_position = 11, c81.sensitivity_level = 3, c81.is_pii = true, c81.pii_type = "PHONE", c81.masking_strategy = "PARTIAL_MASK", c81.is_active = true;

MERGE (c82:Column {fqn: "ApolloHIS.dbo.facilities.email"})
SET c82.name = "email", c82.data_type = "varchar", c82.is_nullable = true, c82.ordinal_position = 12, c82.sensitivity_level = 3, c82.is_pii = true, c82.pii_type = "EMAIL", c82.masking_strategy = "PARTIAL_MASK", c82.is_active = true;

MERGE (c83:Column {fqn: "ApolloHIS.dbo.facilities.is_active"})
SET c83.name = "is_active", c83.data_type = "bit", c83.is_nullable = true, c83.ordinal_position = 13, c83.is_active = true;

MERGE (c84:Column {fqn: "ApolloHIS.dbo.facilities.created_at"})
SET c84.name = "created_at", c84.data_type = "datetime2", c84.is_nullable = true, c84.ordinal_position = 14, c84.is_active = true;

MERGE (c85:Column {fqn: "ApolloHIS.dbo.facilities.updated_at"})
SET c85.name = "updated_at", c85.data_type = "datetime2", c85.is_nullable = true, c85.ordinal_position = 15, c85.is_active = true;

// Column-Table links (facilities)
MERGE (t5)-[:HAS_COLUMN]->(c71);
MERGE (t5)-[:HAS_COLUMN]->(c72);
MERGE (t5)-[:HAS_COLUMN]->(c73);
MERGE (t5)-[:HAS_COLUMN]->(c74);
MERGE (t5)-[:HAS_COLUMN]->(c75);
MERGE (t5)-[:HAS_COLUMN]->(c76);
MERGE (t5)-[:HAS_COLUMN]->(c77);
MERGE (t5)-[:HAS_COLUMN]->(c78);
MERGE (t5)-[:HAS_COLUMN]->(c79);
MERGE (t5)-[:HAS_COLUMN]->(c80);
MERGE (t5)-[:HAS_COLUMN]->(c81);
MERGE (t5)-[:HAS_COLUMN]->(c82);
MERGE (t5)-[:HAS_COLUMN]->(c83);
MERGE (t5)-[:HAS_COLUMN]->(c84);
MERGE (t5)-[:HAS_COLUMN]->(c85);

// --- Columns (lab_results) ---
MERGE (c86:Column {fqn: "ApolloHIS.dbo.lab_results.result_id"})
SET c86.name = "result_id", c86.data_type = "varchar", c86.is_pk = true, c86.is_nullable = false, c86.ordinal_position = 1, c86.sensitivity_level = 3, c86.is_pii = true, c86.pii_type = "CLINICAL_CONTEXT", c86.masking_strategy = "REVIEW", c86.is_active = true;

MERGE (c87:Column {fqn: "ApolloHIS.dbo.lab_results.encounter_id"})
SET c87.name = "encounter_id", c87.data_type = "varchar", c87.is_nullable = false, c87.ordinal_position = 2, c87.sensitivity_level = 3, c87.is_pii = true, c87.pii_type = "CLINICAL_CONTEXT", c87.masking_strategy = "REVIEW", c87.is_active = true;

MERGE (c88:Column {fqn: "ApolloHIS.dbo.lab_results.patient_id"})
SET c88.name = "patient_id", c88.data_type = "varchar", c88.is_nullable = false, c88.ordinal_position = 3, c88.sensitivity_level = 3, c88.is_pii = true, c88.pii_type = "CLINICAL_CONTEXT", c88.masking_strategy = "REVIEW", c88.is_active = true;

MERGE (c89:Column {fqn: "ApolloHIS.dbo.lab_results.ordering_provider_id"})
SET c89.name = "ordering_provider_id", c89.data_type = "varchar", c89.is_nullable = false, c89.ordinal_position = 4, c89.sensitivity_level = 3, c89.is_pii = true, c89.pii_type = "CLINICAL_CONTEXT", c89.masking_strategy = "REVIEW", c89.is_active = true;

MERGE (c90:Column {fqn: "ApolloHIS.dbo.lab_results.test_code"})
SET c90.name = "test_code", c90.data_type = "varchar", c90.is_nullable = false, c90.ordinal_position = 5, c90.sensitivity_level = 3, c90.is_pii = true, c90.pii_type = "CLINICAL_CONTEXT", c90.masking_strategy = "REVIEW", c90.is_active = true;

MERGE (c91:Column {fqn: "ApolloHIS.dbo.lab_results.test_name"})
SET c91.name = "test_name", c91.data_type = "nvarchar", c91.is_nullable = false, c91.ordinal_position = 6, c91.sensitivity_level = 3, c91.is_pii = true, c91.pii_type = "CLINICAL_CONTEXT", c91.masking_strategy = "REVIEW", c91.is_active = true;

MERGE (c92:Column {fqn: "ApolloHIS.dbo.lab_results.test_category"})
SET c92.name = "test_category", c92.data_type = "varchar", c92.is_nullable = true, c92.ordinal_position = 7, c92.sensitivity_level = 3, c92.is_pii = true, c92.pii_type = "CLINICAL_CONTEXT", c92.masking_strategy = "REVIEW", c92.is_active = true;

MERGE (c93:Column {fqn: "ApolloHIS.dbo.lab_results.specimen_type"})
SET c93.name = "specimen_type", c93.data_type = "varchar", c93.is_nullable = true, c93.ordinal_position = 8, c93.sensitivity_level = 3, c93.is_pii = true, c93.pii_type = "CLINICAL_CONTEXT", c93.masking_strategy = "REVIEW", c93.is_active = true;

MERGE (c94:Column {fqn: "ApolloHIS.dbo.lab_results.collected_datetime"})
SET c94.name = "collected_datetime", c94.data_type = "datetime2", c94.is_nullable = true, c94.ordinal_position = 9, c94.sensitivity_level = 3, c94.is_pii = true, c94.pii_type = "CLINICAL_CONTEXT", c94.masking_strategy = "REVIEW", c94.is_active = true;

MERGE (c95:Column {fqn: "ApolloHIS.dbo.lab_results.result_datetime"})
SET c95.name = "result_datetime", c95.data_type = "datetime2", c95.is_nullable = false, c95.ordinal_position = 10, c95.sensitivity_level = 3, c95.is_pii = true, c95.pii_type = "CLINICAL_CONTEXT", c95.masking_strategy = "REVIEW", c95.is_active = true;

MERGE (c96:Column {fqn: "ApolloHIS.dbo.lab_results.result_value"})
SET c96.name = "result_value", c96.data_type = "nvarchar", c96.is_nullable = true, c96.ordinal_position = 11, c96.sensitivity_level = 3, c96.is_pii = true, c96.pii_type = "CLINICAL_CONTEXT", c96.masking_strategy = "REVIEW", c96.is_active = true;

MERGE (c97:Column {fqn: "ApolloHIS.dbo.lab_results.result_unit"})
SET c97.name = "result_unit", c97.data_type = "varchar", c97.is_nullable = true, c97.ordinal_position = 12, c97.sensitivity_level = 3, c97.is_pii = true, c97.pii_type = "CLINICAL_CONTEXT", c97.masking_strategy = "REVIEW", c97.is_active = true;

MERGE (c98:Column {fqn: "ApolloHIS.dbo.lab_results.reference_range"})
SET c98.name = "reference_range", c98.data_type = "varchar", c98.is_nullable = true, c98.ordinal_position = 13, c98.sensitivity_level = 3, c98.is_pii = true, c98.pii_type = "CLINICAL_CONTEXT", c98.masking_strategy = "REVIEW", c98.is_active = true;

MERGE (c99:Column {fqn: "ApolloHIS.dbo.lab_results.abnormal_flag"})
SET c99.name = "abnormal_flag", c99.data_type = "varchar", c99.is_nullable = true, c99.ordinal_position = 14, c99.sensitivity_level = 3, c99.is_pii = true, c99.pii_type = "CLINICAL_CONTEXT", c99.masking_strategy = "REVIEW", c99.is_active = true;

MERGE (c100:Column {fqn: "ApolloHIS.dbo.lab_results.status"})
SET c100.name = "status", c100.data_type = "varchar", c100.is_nullable = true, c100.ordinal_position = 15, c100.sensitivity_level = 3, c100.is_pii = true, c100.pii_type = "CLINICAL_CONTEXT", c100.masking_strategy = "REVIEW", c100.is_active = true;

MERGE (c101:Column {fqn: "ApolloHIS.dbo.lab_results.created_at"})
SET c101.name = "created_at", c101.data_type = "datetime2", c101.is_nullable = true, c101.ordinal_position = 16, c101.sensitivity_level = 3, c101.is_pii = true, c101.pii_type = "CLINICAL_CONTEXT", c101.masking_strategy = "REVIEW", c101.is_active = true;

// Column-Table links (lab_results)
MERGE (t6)-[:HAS_COLUMN]->(c86);
MERGE (t6)-[:HAS_COLUMN]->(c87);
MERGE (t6)-[:HAS_COLUMN]->(c88);
MERGE (t6)-[:HAS_COLUMN]->(c89);
MERGE (t6)-[:HAS_COLUMN]->(c90);
MERGE (t6)-[:HAS_COLUMN]->(c91);
MERGE (t6)-[:HAS_COLUMN]->(c92);
MERGE (t6)-[:HAS_COLUMN]->(c93);
MERGE (t6)-[:HAS_COLUMN]->(c94);
MERGE (t6)-[:HAS_COLUMN]->(c95);
MERGE (t6)-[:HAS_COLUMN]->(c96);
MERGE (t6)-[:HAS_COLUMN]->(c97);
MERGE (t6)-[:HAS_COLUMN]->(c98);
MERGE (t6)-[:HAS_COLUMN]->(c99);
MERGE (t6)-[:HAS_COLUMN]->(c100);
MERGE (t6)-[:HAS_COLUMN]->(c101);

// --- Columns (patients) ---
MERGE (c102:Column {fqn: "ApolloHIS.dbo.patients.patient_id"})
SET c102.name = "patient_id", c102.data_type = "varchar", c102.is_pk = true, c102.is_nullable = false, c102.ordinal_position = 1, c102.sensitivity_level = 3, c102.is_pii = true, c102.pii_type = "CLINICAL_CONTEXT", c102.masking_strategy = "REVIEW", c102.is_active = true;

MERGE (c103:Column {fqn: "ApolloHIS.dbo.patients.mrn"})
SET c103.name = "mrn", c103.data_type = "varchar", c103.is_nullable = false, c103.ordinal_position = 2, c103.sensitivity_level = 3, c103.is_pii = true, c103.pii_type = "CLINICAL_CONTEXT", c103.masking_strategy = "REVIEW", c103.is_active = true;

MERGE (c104:Column {fqn: "ApolloHIS.dbo.patients.aadhaar_number"})
SET c104.name = "aadhaar_number", c104.data_type = "varchar", c104.is_nullable = true, c104.ordinal_position = 3, c104.sensitivity_level = 5, c104.is_pii = true, c104.pii_type = "NATIONAL_ID", c104.masking_strategy = "HASH", c104.is_active = true;

MERGE (c105:Column {fqn: "ApolloHIS.dbo.patients.first_name"})
SET c105.name = "first_name", c105.data_type = "nvarchar", c105.is_nullable = false, c105.ordinal_position = 4, c105.sensitivity_level = 4, c105.is_pii = true, c105.pii_type = "FULL_NAME", c105.masking_strategy = "REDACT", c105.is_active = true;

MERGE (c106:Column {fqn: "ApolloHIS.dbo.patients.last_name"})
SET c106.name = "last_name", c106.data_type = "nvarchar", c106.is_nullable = false, c106.ordinal_position = 5, c106.sensitivity_level = 4, c106.is_pii = true, c106.pii_type = "FULL_NAME", c106.masking_strategy = "REDACT", c106.is_active = true;

MERGE (c107:Column {fqn: "ApolloHIS.dbo.patients.full_name"})
SET c107.name = "full_name", c107.data_type = "nvarchar", c107.is_nullable = false, c107.ordinal_position = 6, c107.sensitivity_level = 4, c107.is_pii = true, c107.pii_type = "FULL_NAME", c107.masking_strategy = "REDACT", c107.is_active = true;

MERGE (c108:Column {fqn: "ApolloHIS.dbo.patients.date_of_birth"})
SET c108.name = "date_of_birth", c108.data_type = "date", c108.is_nullable = false, c108.ordinal_position = 7, c108.sensitivity_level = 4, c108.is_pii = true, c108.pii_type = "DATE_OF_BIRTH", c108.masking_strategy = "GENERALIZE_YEAR", c108.is_active = true;

MERGE (c109:Column {fqn: "ApolloHIS.dbo.patients.gender"})
SET c109.name = "gender", c109.data_type = "varchar", c109.is_nullable = false, c109.ordinal_position = 8, c109.sensitivity_level = 3, c109.is_pii = true, c109.pii_type = "DEMOGRAPHIC", c109.masking_strategy = "GENERALIZE", c109.is_active = true;

MERGE (c110:Column {fqn: "ApolloHIS.dbo.patients.blood_group"})
SET c110.name = "blood_group", c110.data_type = "varchar", c110.is_nullable = true, c110.ordinal_position = 9, c110.sensitivity_level = 4, c110.is_pii = true, c110.pii_type = "MEDICAL", c110.masking_strategy = "REDACT", c110.is_active = true;

MERGE (c111:Column {fqn: "ApolloHIS.dbo.patients.phone_primary"})
SET c111.name = "phone_primary", c111.data_type = "varchar", c111.is_nullable = true, c111.ordinal_position = 10, c111.sensitivity_level = 3, c111.is_pii = true, c111.pii_type = "PHONE", c111.masking_strategy = "PARTIAL_MASK", c111.is_active = true;

MERGE (c112:Column {fqn: "ApolloHIS.dbo.patients.phone_secondary"})
SET c112.name = "phone_secondary", c112.data_type = "varchar", c112.is_nullable = true, c112.ordinal_position = 11, c112.sensitivity_level = 3, c112.is_pii = true, c112.pii_type = "PHONE", c112.masking_strategy = "PARTIAL_MASK", c112.is_active = true;

MERGE (c113:Column {fqn: "ApolloHIS.dbo.patients.email"})
SET c113.name = "email", c113.data_type = "varchar", c113.is_nullable = true, c113.ordinal_position = 12, c113.sensitivity_level = 3, c113.is_pii = true, c113.pii_type = "EMAIL", c113.masking_strategy = "PARTIAL_MASK", c113.is_active = true;

MERGE (c114:Column {fqn: "ApolloHIS.dbo.patients.address_line1"})
SET c114.name = "address_line1", c114.data_type = "nvarchar", c114.is_nullable = true, c114.ordinal_position = 13, c114.sensitivity_level = 3, c114.is_pii = true, c114.pii_type = "ADDRESS", c114.masking_strategy = "REDACT", c114.is_active = true;

MERGE (c115:Column {fqn: "ApolloHIS.dbo.patients.address_line2"})
SET c115.name = "address_line2", c115.data_type = "nvarchar", c115.is_nullable = true, c115.ordinal_position = 14, c115.sensitivity_level = 3, c115.is_pii = true, c115.pii_type = "ADDRESS", c115.masking_strategy = "REDACT", c115.is_active = true;

MERGE (c116:Column {fqn: "ApolloHIS.dbo.patients.city"})
SET c116.name = "city", c116.data_type = "nvarchar", c116.is_nullable = true, c116.ordinal_position = 15, c116.sensitivity_level = 3, c116.is_pii = true, c116.pii_type = "ADDRESS", c116.masking_strategy = "GENERALIZE", c116.is_active = true;

MERGE (c117:Column {fqn: "ApolloHIS.dbo.patients.state"})
SET c117.name = "state", c117.data_type = "nvarchar", c117.is_nullable = true, c117.ordinal_position = 16, c117.sensitivity_level = 3, c117.is_pii = true, c117.pii_type = "ADDRESS", c117.masking_strategy = "GENERALIZE", c117.is_active = true;

MERGE (c118:Column {fqn: "ApolloHIS.dbo.patients.pin_code"})
SET c118.name = "pin_code", c118.data_type = "varchar", c118.is_nullable = true, c118.ordinal_position = 17, c118.sensitivity_level = 3, c118.is_pii = true, c118.pii_type = "ADDRESS", c118.masking_strategy = "GENERALIZE", c118.is_active = true;

MERGE (c119:Column {fqn: "ApolloHIS.dbo.patients.country"})
SET c119.name = "country", c119.data_type = "varchar", c119.is_nullable = true, c119.ordinal_position = 18, c119.sensitivity_level = 3, c119.is_pii = true, c119.pii_type = "CLINICAL_CONTEXT", c119.masking_strategy = "REVIEW", c119.is_active = true;

MERGE (c120:Column {fqn: "ApolloHIS.dbo.patients.emergency_contact_name"})
SET c120.name = "emergency_contact_name", c120.data_type = "nvarchar", c120.is_nullable = true, c120.ordinal_position = 19, c120.sensitivity_level = 3, c120.is_pii = true, c120.pii_type = "PHONE", c120.masking_strategy = "PARTIAL_MASK", c120.is_active = true;

MERGE (c121:Column {fqn: "ApolloHIS.dbo.patients.emergency_contact_phone"})
SET c121.name = "emergency_contact_phone", c121.data_type = "varchar", c121.is_nullable = true, c121.ordinal_position = 20, c121.sensitivity_level = 3, c121.is_pii = true, c121.pii_type = "PHONE", c121.masking_strategy = "PARTIAL_MASK", c121.is_active = true;

MERGE (c122:Column {fqn: "ApolloHIS.dbo.patients.emergency_contact_relation"})
SET c122.name = "emergency_contact_relation", c122.data_type = "varchar", c122.is_nullable = true, c122.ordinal_position = 21, c122.sensitivity_level = 3, c122.is_pii = true, c122.pii_type = "PHONE", c122.masking_strategy = "PARTIAL_MASK", c122.is_active = true;

MERGE (c123:Column {fqn: "ApolloHIS.dbo.patients.primary_insurance_id"})
SET c123.name = "primary_insurance_id", c123.data_type = "varchar", c123.is_nullable = true, c123.ordinal_position = 22, c123.sensitivity_level = 3, c123.is_pii = true, c123.pii_type = "CLINICAL_CONTEXT", c123.masking_strategy = "REVIEW", c123.is_active = true;

MERGE (c124:Column {fqn: "ApolloHIS.dbo.patients.registration_date"})
SET c124.name = "registration_date", c124.data_type = "date", c124.is_nullable = false, c124.ordinal_position = 23, c124.sensitivity_level = 3, c124.is_pii = true, c124.pii_type = "CLINICAL_CONTEXT", c124.masking_strategy = "REVIEW", c124.is_active = true;

MERGE (c125:Column {fqn: "ApolloHIS.dbo.patients.registration_facility_id"})
SET c125.name = "registration_facility_id", c125.data_type = "varchar", c125.is_nullable = true, c125.ordinal_position = 24, c125.sensitivity_level = 3, c125.is_pii = true, c125.pii_type = "CLINICAL_CONTEXT", c125.masking_strategy = "REVIEW", c125.is_active = true;

MERGE (c126:Column {fqn: "ApolloHIS.dbo.patients.is_vip"})
SET c126.name = "is_vip", c126.data_type = "bit", c126.is_nullable = true, c126.ordinal_position = 25, c126.sensitivity_level = 3, c126.is_pii = true, c126.pii_type = "CLINICAL_CONTEXT", c126.masking_strategy = "REVIEW", c126.is_active = true;

MERGE (c127:Column {fqn: "ApolloHIS.dbo.patients.is_active"})
SET c127.name = "is_active", c127.data_type = "bit", c127.is_nullable = true, c127.ordinal_position = 26, c127.sensitivity_level = 3, c127.is_pii = true, c127.pii_type = "CLINICAL_CONTEXT", c127.masking_strategy = "REVIEW", c127.is_active = true;

MERGE (c128:Column {fqn: "ApolloHIS.dbo.patients.deceased_flag"})
SET c128.name = "deceased_flag", c128.data_type = "bit", c128.is_nullable = true, c128.ordinal_position = 27, c128.sensitivity_level = 3, c128.is_pii = true, c128.pii_type = "CLINICAL_CONTEXT", c128.masking_strategy = "REVIEW", c128.is_active = true;

MERGE (c129:Column {fqn: "ApolloHIS.dbo.patients.deceased_date"})
SET c129.name = "deceased_date", c129.data_type = "date", c129.is_nullable = true, c129.ordinal_position = 28, c129.sensitivity_level = 3, c129.is_pii = true, c129.pii_type = "CLINICAL_CONTEXT", c129.masking_strategy = "REVIEW", c129.is_active = true;

MERGE (c130:Column {fqn: "ApolloHIS.dbo.patients.created_at"})
SET c130.name = "created_at", c130.data_type = "datetime2", c130.is_nullable = true, c130.ordinal_position = 29, c130.sensitivity_level = 3, c130.is_pii = true, c130.pii_type = "CLINICAL_CONTEXT", c130.masking_strategy = "REVIEW", c130.is_active = true;

MERGE (c131:Column {fqn: "ApolloHIS.dbo.patients.updated_at"})
SET c131.name = "updated_at", c131.data_type = "datetime2", c131.is_nullable = true, c131.ordinal_position = 30, c131.sensitivity_level = 3, c131.is_pii = true, c131.pii_type = "CLINICAL_CONTEXT", c131.masking_strategy = "REVIEW", c131.is_active = true;

// Column-Table links (patients)
MERGE (t7)-[:HAS_COLUMN]->(c102);
MERGE (t7)-[:HAS_COLUMN]->(c103);
MERGE (t7)-[:HAS_COLUMN]->(c104);
MERGE (t7)-[:HAS_COLUMN]->(c105);
MERGE (t7)-[:HAS_COLUMN]->(c106);
MERGE (t7)-[:HAS_COLUMN]->(c107);
MERGE (t7)-[:HAS_COLUMN]->(c108);
MERGE (t7)-[:HAS_COLUMN]->(c109);
MERGE (t7)-[:HAS_COLUMN]->(c110);
MERGE (t7)-[:HAS_COLUMN]->(c111);
MERGE (t7)-[:HAS_COLUMN]->(c112);
MERGE (t7)-[:HAS_COLUMN]->(c113);
MERGE (t7)-[:HAS_COLUMN]->(c114);
MERGE (t7)-[:HAS_COLUMN]->(c115);
MERGE (t7)-[:HAS_COLUMN]->(c116);
MERGE (t7)-[:HAS_COLUMN]->(c117);
MERGE (t7)-[:HAS_COLUMN]->(c118);
MERGE (t7)-[:HAS_COLUMN]->(c119);
MERGE (t7)-[:HAS_COLUMN]->(c120);
MERGE (t7)-[:HAS_COLUMN]->(c121);
MERGE (t7)-[:HAS_COLUMN]->(c122);
MERGE (t7)-[:HAS_COLUMN]->(c123);
MERGE (t7)-[:HAS_COLUMN]->(c124);
MERGE (t7)-[:HAS_COLUMN]->(c125);
MERGE (t7)-[:HAS_COLUMN]->(c126);
MERGE (t7)-[:HAS_COLUMN]->(c127);
MERGE (t7)-[:HAS_COLUMN]->(c128);
MERGE (t7)-[:HAS_COLUMN]->(c129);
MERGE (t7)-[:HAS_COLUMN]->(c130);
MERGE (t7)-[:HAS_COLUMN]->(c131);

// --- Columns (prescriptions) ---
MERGE (c132:Column {fqn: "ApolloHIS.dbo.prescriptions.prescription_id"})
SET c132.name = "prescription_id", c132.data_type = "varchar", c132.is_pk = true, c132.is_nullable = false, c132.ordinal_position = 1, c132.sensitivity_level = 3, c132.is_pii = true, c132.pii_type = "CLINICAL_CONTEXT", c132.masking_strategy = "REVIEW", c132.is_active = true;

MERGE (c133:Column {fqn: "ApolloHIS.dbo.prescriptions.encounter_id"})
SET c133.name = "encounter_id", c133.data_type = "varchar", c133.is_nullable = false, c133.ordinal_position = 2, c133.sensitivity_level = 3, c133.is_pii = true, c133.pii_type = "CLINICAL_CONTEXT", c133.masking_strategy = "REVIEW", c133.is_active = true;

MERGE (c134:Column {fqn: "ApolloHIS.dbo.prescriptions.patient_id"})
SET c134.name = "patient_id", c134.data_type = "varchar", c134.is_nullable = false, c134.ordinal_position = 3, c134.sensitivity_level = 3, c134.is_pii = true, c134.pii_type = "CLINICAL_CONTEXT", c134.masking_strategy = "REVIEW", c134.is_active = true;

MERGE (c135:Column {fqn: "ApolloHIS.dbo.prescriptions.prescribing_provider_id"})
SET c135.name = "prescribing_provider_id", c135.data_type = "varchar", c135.is_nullable = false, c135.ordinal_position = 4, c135.sensitivity_level = 3, c135.is_pii = true, c135.pii_type = "CLINICAL_CONTEXT", c135.masking_strategy = "REVIEW", c135.is_active = true;

MERGE (c136:Column {fqn: "ApolloHIS.dbo.prescriptions.medication_name"})
SET c136.name = "medication_name", c136.data_type = "nvarchar", c136.is_nullable = false, c136.ordinal_position = 5, c136.sensitivity_level = 3, c136.is_pii = true, c136.pii_type = "CLINICAL_CONTEXT", c136.masking_strategy = "REVIEW", c136.is_active = true;

MERGE (c137:Column {fqn: "ApolloHIS.dbo.prescriptions.generic_name"})
SET c137.name = "generic_name", c137.data_type = "nvarchar", c137.is_nullable = true, c137.ordinal_position = 6, c137.sensitivity_level = 3, c137.is_pii = true, c137.pii_type = "CLINICAL_CONTEXT", c137.masking_strategy = "REVIEW", c137.is_active = true;

MERGE (c138:Column {fqn: "ApolloHIS.dbo.prescriptions.dosage"})
SET c138.name = "dosage", c138.data_type = "nvarchar", c138.is_nullable = true, c138.ordinal_position = 7, c138.sensitivity_level = 3, c138.is_pii = true, c138.pii_type = "CLINICAL_CONTEXT", c138.masking_strategy = "REVIEW", c138.is_active = true;

MERGE (c139:Column {fqn: "ApolloHIS.dbo.prescriptions.route"})
SET c139.name = "route", c139.data_type = "varchar", c139.is_nullable = true, c139.ordinal_position = 8, c139.sensitivity_level = 3, c139.is_pii = true, c139.pii_type = "CLINICAL_CONTEXT", c139.masking_strategy = "REVIEW", c139.is_active = true;

MERGE (c140:Column {fqn: "ApolloHIS.dbo.prescriptions.frequency"})
SET c140.name = "frequency", c140.data_type = "varchar", c140.is_nullable = true, c140.ordinal_position = 9, c140.sensitivity_level = 3, c140.is_pii = true, c140.pii_type = "CLINICAL_CONTEXT", c140.masking_strategy = "REVIEW", c140.is_active = true;

MERGE (c141:Column {fqn: "ApolloHIS.dbo.prescriptions.start_date"})
SET c141.name = "start_date", c141.data_type = "date", c141.is_nullable = false, c141.ordinal_position = 10, c141.sensitivity_level = 3, c141.is_pii = true, c141.pii_type = "CLINICAL_CONTEXT", c141.masking_strategy = "REVIEW", c141.is_active = true;

MERGE (c142:Column {fqn: "ApolloHIS.dbo.prescriptions.end_date"})
SET c142.name = "end_date", c142.data_type = "date", c142.is_nullable = true, c142.ordinal_position = 11, c142.sensitivity_level = 3, c142.is_pii = true, c142.pii_type = "CLINICAL_CONTEXT", c142.masking_strategy = "REVIEW", c142.is_active = true;

MERGE (c143:Column {fqn: "ApolloHIS.dbo.prescriptions.duration_days"})
SET c143.name = "duration_days", c143.data_type = "int", c143.is_nullable = true, c143.ordinal_position = 12, c143.sensitivity_level = 3, c143.is_pii = true, c143.pii_type = "CLINICAL_CONTEXT", c143.masking_strategy = "REVIEW", c143.is_active = true;

MERGE (c144:Column {fqn: "ApolloHIS.dbo.prescriptions.quantity"})
SET c144.name = "quantity", c144.data_type = "int", c144.is_nullable = true, c144.ordinal_position = 13, c144.sensitivity_level = 3, c144.is_pii = true, c144.pii_type = "CLINICAL_CONTEXT", c144.masking_strategy = "REVIEW", c144.is_active = true;

MERGE (c145:Column {fqn: "ApolloHIS.dbo.prescriptions.refills_remaining"})
SET c145.name = "refills_remaining", c145.data_type = "int", c145.is_nullable = true, c145.ordinal_position = 14, c145.sensitivity_level = 3, c145.is_pii = true, c145.pii_type = "CLINICAL_CONTEXT", c145.masking_strategy = "REVIEW", c145.is_active = true;

MERGE (c146:Column {fqn: "ApolloHIS.dbo.prescriptions.is_active"})
SET c146.name = "is_active", c146.data_type = "bit", c146.is_nullable = true, c146.ordinal_position = 15, c146.sensitivity_level = 3, c146.is_pii = true, c146.pii_type = "CLINICAL_CONTEXT", c146.masking_strategy = "REVIEW", c146.is_active = true;

MERGE (c147:Column {fqn: "ApolloHIS.dbo.prescriptions.discontinued_reason"})
SET c147.name = "discontinued_reason", c147.data_type = "nvarchar", c147.is_nullable = true, c147.ordinal_position = 16, c147.sensitivity_level = 3, c147.is_pii = true, c147.pii_type = "CLINICAL_CONTEXT", c147.masking_strategy = "REVIEW", c147.is_active = true;

MERGE (c148:Column {fqn: "ApolloHIS.dbo.prescriptions.pharmacy_status"})
SET c148.name = "pharmacy_status", c148.data_type = "varchar", c148.is_nullable = true, c148.ordinal_position = 17, c148.sensitivity_level = 3, c148.is_pii = true, c148.pii_type = "CLINICAL_CONTEXT", c148.masking_strategy = "REVIEW", c148.is_active = true;

MERGE (c149:Column {fqn: "ApolloHIS.dbo.prescriptions.created_at"})
SET c149.name = "created_at", c149.data_type = "datetime2", c149.is_nullable = true, c149.ordinal_position = 18, c149.sensitivity_level = 3, c149.is_pii = true, c149.pii_type = "CLINICAL_CONTEXT", c149.masking_strategy = "REVIEW", c149.is_active = true;

// Column-Table links (prescriptions)
MERGE (t8)-[:HAS_COLUMN]->(c132);
MERGE (t8)-[:HAS_COLUMN]->(c133);
MERGE (t8)-[:HAS_COLUMN]->(c134);
MERGE (t8)-[:HAS_COLUMN]->(c135);
MERGE (t8)-[:HAS_COLUMN]->(c136);
MERGE (t8)-[:HAS_COLUMN]->(c137);
MERGE (t8)-[:HAS_COLUMN]->(c138);
MERGE (t8)-[:HAS_COLUMN]->(c139);
MERGE (t8)-[:HAS_COLUMN]->(c140);
MERGE (t8)-[:HAS_COLUMN]->(c141);
MERGE (t8)-[:HAS_COLUMN]->(c142);
MERGE (t8)-[:HAS_COLUMN]->(c143);
MERGE (t8)-[:HAS_COLUMN]->(c144);
MERGE (t8)-[:HAS_COLUMN]->(c145);
MERGE (t8)-[:HAS_COLUMN]->(c146);
MERGE (t8)-[:HAS_COLUMN]->(c147);
MERGE (t8)-[:HAS_COLUMN]->(c148);
MERGE (t8)-[:HAS_COLUMN]->(c149);

// --- Columns (staff_schedules) ---
MERGE (c150:Column {fqn: "ApolloHIS.dbo.staff_schedules.schedule_id"})
SET c150.name = "schedule_id", c150.data_type = "varchar", c150.is_pk = true, c150.is_nullable = false, c150.ordinal_position = 1, c150.is_active = true;

MERGE (c151:Column {fqn: "ApolloHIS.dbo.staff_schedules.employee_id"})
SET c151.name = "employee_id", c151.data_type = "varchar", c151.is_nullable = false, c151.ordinal_position = 2, c151.is_active = true;

MERGE (c152:Column {fqn: "ApolloHIS.dbo.staff_schedules.facility_id"})
SET c152.name = "facility_id", c152.data_type = "varchar", c152.is_nullable = false, c152.ordinal_position = 3, c152.is_active = true;

MERGE (c153:Column {fqn: "ApolloHIS.dbo.staff_schedules.unit_id"})
SET c153.name = "unit_id", c153.data_type = "varchar", c153.is_nullable = true, c153.ordinal_position = 4, c153.is_active = true;

MERGE (c154:Column {fqn: "ApolloHIS.dbo.staff_schedules.shift_date"})
SET c154.name = "shift_date", c154.data_type = "date", c154.is_nullable = false, c154.ordinal_position = 5, c154.is_active = true;

MERGE (c155:Column {fqn: "ApolloHIS.dbo.staff_schedules.shift_type"})
SET c155.name = "shift_type", c155.data_type = "varchar", c155.is_nullable = false, c155.ordinal_position = 6, c155.is_active = true;

MERGE (c156:Column {fqn: "ApolloHIS.dbo.staff_schedules.shift_start"})
SET c156.name = "shift_start", c156.data_type = "time", c156.is_nullable = false, c156.ordinal_position = 7, c156.is_active = true;

MERGE (c157:Column {fqn: "ApolloHIS.dbo.staff_schedules.shift_end"})
SET c157.name = "shift_end", c157.data_type = "time", c157.is_nullable = false, c157.ordinal_position = 8, c157.is_active = true;

MERGE (c158:Column {fqn: "ApolloHIS.dbo.staff_schedules.is_on_call"})
SET c158.name = "is_on_call", c158.data_type = "bit", c158.is_nullable = true, c158.ordinal_position = 9, c158.is_active = true;

MERGE (c159:Column {fqn: "ApolloHIS.dbo.staff_schedules.status"})
SET c159.name = "status", c159.data_type = "varchar", c159.is_nullable = true, c159.ordinal_position = 10, c159.is_active = true;

MERGE (c160:Column {fqn: "ApolloHIS.dbo.staff_schedules.created_at"})
SET c160.name = "created_at", c160.data_type = "datetime2", c160.is_nullable = true, c160.ordinal_position = 11, c160.is_active = true;

// Column-Table links (staff_schedules)
MERGE (t9)-[:HAS_COLUMN]->(c150);
MERGE (t9)-[:HAS_COLUMN]->(c151);
MERGE (t9)-[:HAS_COLUMN]->(c152);
MERGE (t9)-[:HAS_COLUMN]->(c153);
MERGE (t9)-[:HAS_COLUMN]->(c154);
MERGE (t9)-[:HAS_COLUMN]->(c155);
MERGE (t9)-[:HAS_COLUMN]->(c156);
MERGE (t9)-[:HAS_COLUMN]->(c157);
MERGE (t9)-[:HAS_COLUMN]->(c158);
MERGE (t9)-[:HAS_COLUMN]->(c159);
MERGE (t9)-[:HAS_COLUMN]->(c160);

// --- Columns (units) ---
MERGE (c161:Column {fqn: "ApolloHIS.dbo.units.unit_id"})
SET c161.name = "unit_id", c161.data_type = "varchar", c161.is_pk = true, c161.is_nullable = false, c161.ordinal_position = 1, c161.is_active = true;

MERGE (c162:Column {fqn: "ApolloHIS.dbo.units.unit_name"})
SET c162.name = "unit_name", c162.data_type = "nvarchar", c162.is_nullable = false, c162.ordinal_position = 2, c162.is_active = true;

MERGE (c163:Column {fqn: "ApolloHIS.dbo.units.department_id"})
SET c163.name = "department_id", c163.data_type = "varchar", c163.is_nullable = true, c163.ordinal_position = 3, c163.is_active = true;

MERGE (c164:Column {fqn: "ApolloHIS.dbo.units.facility_id"})
SET c164.name = "facility_id", c164.data_type = "varchar", c164.is_nullable = true, c164.ordinal_position = 4, c164.is_active = true;

MERGE (c165:Column {fqn: "ApolloHIS.dbo.units.unit_type"})
SET c165.name = "unit_type", c165.data_type = "varchar", c165.is_nullable = false, c165.ordinal_position = 5, c165.is_active = true;

MERGE (c166:Column {fqn: "ApolloHIS.dbo.units.floor_number"})
SET c166.name = "floor_number", c166.data_type = "int", c166.is_nullable = true, c166.ordinal_position = 6, c166.is_active = true;

MERGE (c167:Column {fqn: "ApolloHIS.dbo.units.bed_count"})
SET c167.name = "bed_count", c167.data_type = "int", c167.is_nullable = true, c167.ordinal_position = 7, c167.is_active = true;

MERGE (c168:Column {fqn: "ApolloHIS.dbo.units.is_active"})
SET c168.name = "is_active", c168.data_type = "bit", c168.is_nullable = true, c168.ordinal_position = 8, c168.is_active = true;

MERGE (c169:Column {fqn: "ApolloHIS.dbo.units.created_at"})
SET c169.name = "created_at", c169.data_type = "datetime2", c169.is_nullable = true, c169.ordinal_position = 9, c169.is_active = true;

// Column-Table links (units)
MERGE (t10)-[:HAS_COLUMN]->(c161);
MERGE (t10)-[:HAS_COLUMN]->(c162);
MERGE (t10)-[:HAS_COLUMN]->(c163);
MERGE (t10)-[:HAS_COLUMN]->(c164);
MERGE (t10)-[:HAS_COLUMN]->(c165);
MERGE (t10)-[:HAS_COLUMN]->(c166);
MERGE (t10)-[:HAS_COLUMN]->(c167);
MERGE (t10)-[:HAS_COLUMN]->(c168);
MERGE (t10)-[:HAS_COLUMN]->(c169);

// --- Columns (vital_signs) ---
MERGE (c170:Column {fqn: "ApolloHIS.dbo.vital_signs.vital_id"})
SET c170.name = "vital_id", c170.data_type = "varchar", c170.is_pk = true, c170.is_nullable = false, c170.ordinal_position = 1, c170.sensitivity_level = 3, c170.is_pii = true, c170.pii_type = "CLINICAL_CONTEXT", c170.masking_strategy = "REVIEW", c170.is_active = true;

MERGE (c171:Column {fqn: "ApolloHIS.dbo.vital_signs.encounter_id"})
SET c171.name = "encounter_id", c171.data_type = "varchar", c171.is_nullable = false, c171.ordinal_position = 2, c171.sensitivity_level = 3, c171.is_pii = true, c171.pii_type = "CLINICAL_CONTEXT", c171.masking_strategy = "REVIEW", c171.is_active = true;

MERGE (c172:Column {fqn: "ApolloHIS.dbo.vital_signs.patient_id"})
SET c172.name = "patient_id", c172.data_type = "varchar", c172.is_nullable = false, c172.ordinal_position = 3, c172.sensitivity_level = 3, c172.is_pii = true, c172.pii_type = "CLINICAL_CONTEXT", c172.masking_strategy = "REVIEW", c172.is_active = true;

MERGE (c173:Column {fqn: "ApolloHIS.dbo.vital_signs.recorded_by"})
SET c173.name = "recorded_by", c173.data_type = "varchar", c173.is_nullable = false, c173.ordinal_position = 4, c173.sensitivity_level = 3, c173.is_pii = true, c173.pii_type = "CLINICAL_CONTEXT", c173.masking_strategy = "REVIEW", c173.is_active = true;

MERGE (c174:Column {fqn: "ApolloHIS.dbo.vital_signs.recorded_datetime"})
SET c174.name = "recorded_datetime", c174.data_type = "datetime2", c174.is_nullable = false, c174.ordinal_position = 5, c174.sensitivity_level = 3, c174.is_pii = true, c174.pii_type = "CLINICAL_CONTEXT", c174.masking_strategy = "REVIEW", c174.is_active = true;

MERGE (c175:Column {fqn: "ApolloHIS.dbo.vital_signs.temperature_celsius"})
SET c175.name = "temperature_celsius", c175.data_type = "decimal", c175.is_nullable = true, c175.ordinal_position = 6, c175.sensitivity_level = 3, c175.is_pii = true, c175.pii_type = "CLINICAL_CONTEXT", c175.masking_strategy = "REVIEW", c175.is_active = true;

MERGE (c176:Column {fqn: "ApolloHIS.dbo.vital_signs.heart_rate_bpm"})
SET c176.name = "heart_rate_bpm", c176.data_type = "int", c176.is_nullable = true, c176.ordinal_position = 7, c176.sensitivity_level = 3, c176.is_pii = true, c176.pii_type = "CLINICAL_CONTEXT", c176.masking_strategy = "REVIEW", c176.is_active = true;

MERGE (c177:Column {fqn: "ApolloHIS.dbo.vital_signs.respiratory_rate"})
SET c177.name = "respiratory_rate", c177.data_type = "int", c177.is_nullable = true, c177.ordinal_position = 8, c177.sensitivity_level = 3, c177.is_pii = true, c177.pii_type = "CLINICAL_CONTEXT", c177.masking_strategy = "REVIEW", c177.is_active = true;

MERGE (c178:Column {fqn: "ApolloHIS.dbo.vital_signs.systolic_bp"})
SET c178.name = "systolic_bp", c178.data_type = "int", c178.is_nullable = true, c178.ordinal_position = 9, c178.sensitivity_level = 3, c178.is_pii = true, c178.pii_type = "CLINICAL_CONTEXT", c178.masking_strategy = "REVIEW", c178.is_active = true;

MERGE (c179:Column {fqn: "ApolloHIS.dbo.vital_signs.diastolic_bp"})
SET c179.name = "diastolic_bp", c179.data_type = "int", c179.is_nullable = true, c179.ordinal_position = 10, c179.sensitivity_level = 3, c179.is_pii = true, c179.pii_type = "CLINICAL_CONTEXT", c179.masking_strategy = "REVIEW", c179.is_active = true;

MERGE (c180:Column {fqn: "ApolloHIS.dbo.vital_signs.spo2_percent"})
SET c180.name = "spo2_percent", c180.data_type = "decimal", c180.is_nullable = true, c180.ordinal_position = 11, c180.sensitivity_level = 3, c180.is_pii = true, c180.pii_type = "CLINICAL_CONTEXT", c180.masking_strategy = "REVIEW", c180.is_active = true;

MERGE (c181:Column {fqn: "ApolloHIS.dbo.vital_signs.pain_scale"})
SET c181.name = "pain_scale", c181.data_type = "int", c181.is_nullable = true, c181.ordinal_position = 12, c181.sensitivity_level = 3, c181.is_pii = true, c181.pii_type = "CLINICAL_CONTEXT", c181.masking_strategy = "REVIEW", c181.is_active = true;

MERGE (c182:Column {fqn: "ApolloHIS.dbo.vital_signs.weight_kg"})
SET c182.name = "weight_kg", c182.data_type = "decimal", c182.is_nullable = true, c182.ordinal_position = 13, c182.sensitivity_level = 3, c182.is_pii = true, c182.pii_type = "CLINICAL_CONTEXT", c182.masking_strategy = "REVIEW", c182.is_active = true;

MERGE (c183:Column {fqn: "ApolloHIS.dbo.vital_signs.height_cm"})
SET c183.name = "height_cm", c183.data_type = "decimal", c183.is_nullable = true, c183.ordinal_position = 14, c183.sensitivity_level = 3, c183.is_pii = true, c183.pii_type = "CLINICAL_CONTEXT", c183.masking_strategy = "REVIEW", c183.is_active = true;

MERGE (c184:Column {fqn: "ApolloHIS.dbo.vital_signs.bmi"})
SET c184.name = "bmi", c184.data_type = "numeric", c184.is_nullable = true, c184.ordinal_position = 15, c184.sensitivity_level = 3, c184.is_pii = true, c184.pii_type = "CLINICAL_CONTEXT", c184.masking_strategy = "REVIEW", c184.is_active = true;

MERGE (c185:Column {fqn: "ApolloHIS.dbo.vital_signs.gcs_score"})
SET c185.name = "gcs_score", c185.data_type = "int", c185.is_nullable = true, c185.ordinal_position = 16, c185.sensitivity_level = 3, c185.is_pii = true, c185.pii_type = "CLINICAL_CONTEXT", c185.masking_strategy = "REVIEW", c185.is_active = true;

MERGE (c186:Column {fqn: "ApolloHIS.dbo.vital_signs.created_at"})
SET c186.name = "created_at", c186.data_type = "datetime2", c186.is_nullable = true, c186.ordinal_position = 17, c186.sensitivity_level = 3, c186.is_pii = true, c186.pii_type = "CLINICAL_CONTEXT", c186.masking_strategy = "REVIEW", c186.is_active = true;

// Column-Table links (vital_signs)
MERGE (t11)-[:HAS_COLUMN]->(c170);
MERGE (t11)-[:HAS_COLUMN]->(c171);
MERGE (t11)-[:HAS_COLUMN]->(c172);
MERGE (t11)-[:HAS_COLUMN]->(c173);
MERGE (t11)-[:HAS_COLUMN]->(c174);
MERGE (t11)-[:HAS_COLUMN]->(c175);
MERGE (t11)-[:HAS_COLUMN]->(c176);
MERGE (t11)-[:HAS_COLUMN]->(c177);
MERGE (t11)-[:HAS_COLUMN]->(c178);
MERGE (t11)-[:HAS_COLUMN]->(c179);
MERGE (t11)-[:HAS_COLUMN]->(c180);
MERGE (t11)-[:HAS_COLUMN]->(c181);
MERGE (t11)-[:HAS_COLUMN]->(c182);
MERGE (t11)-[:HAS_COLUMN]->(c183);
MERGE (t11)-[:HAS_COLUMN]->(c184);
MERGE (t11)-[:HAS_COLUMN]->(c185);
MERGE (t11)-[:HAS_COLUMN]->(c186);

// --- Foreign Keys ---
MERGE (c1)-[:FOREIGN_KEY_TO {constraint: "FK__allergies__patie__04E4BC85"}]->(c1);
MERGE (c14)-[:FOREIGN_KEY_TO {constraint: "FK__appointme__depar__778AC167"}]->(c14);
MERGE (c13)-[:FOREIGN_KEY_TO {constraint: "FK__appointme__facil__76969D2E"}]->(c13);
MERGE (c11)-[:FOREIGN_KEY_TO {constraint: "FK__appointme__patie__75A278F5"}]->(c11);
MERGE (c25)-[:FOREIGN_KEY_TO {constraint: "FK__clinical___encou__5CD6CB2B"}]->(c25);
MERGE (c26)-[:FOREIGN_KEY_TO {constraint: "FK__clinical___patie__5DCAEF64"}]->(c26);
MERGE (c39)-[:FOREIGN_KEY_TO {constraint: "FK__departmen__facil__3E52440B"}]->(c39);
MERGE (c49)-[:FOREIGN_KEY_TO {constraint: "FK__encounter__depar__5441852A"}]->(c49);
MERGE (c48)-[:FOREIGN_KEY_TO {constraint: "FK__encounter__facil__534D60F1"}]->(c48);
MERGE (c46)-[:FOREIGN_KEY_TO {constraint: "FK__encounter__patie__52593CB8"}]->(c46);
MERGE (c50)-[:FOREIGN_KEY_TO {constraint: "FK__encounter__unit___5535A963"}]->(c50);
MERGE (c87)-[:FOREIGN_KEY_TO {constraint: "FK__lab_resul__encou__68487DD7"}]->(c87);
MERGE (c88)-[:FOREIGN_KEY_TO {constraint: "FK__lab_resul__patie__693CA210"}]->(c88);
MERGE (c125)-[:FOREIGN_KEY_TO {constraint: "FK__patients__regist__4AB81AF0"}]->(c125);
MERGE (c133)-[:FOREIGN_KEY_TO {constraint: "FK__prescript__encou__6E01572D"}]->(c133);
MERGE (c134)-[:FOREIGN_KEY_TO {constraint: "FK__prescript__patie__6EF57B66"}]->(c134);
MERGE (c152)-[:FOREIGN_KEY_TO {constraint: "FK__staff_sch__facil__7E37BEF6"}]->(c152);
MERGE (c153)-[:FOREIGN_KEY_TO {constraint: "FK__staff_sch__unit___7F2BE32F"}]->(c153);
MERGE (c163)-[:FOREIGN_KEY_TO {constraint: "FK__units__departmen__4316F928"}]->(c163);
MERGE (c164)-[:FOREIGN_KEY_TO {constraint: "FK__units__facility___440B1D61"}]->(c164);
MERGE (c171)-[:FOREIGN_KEY_TO {constraint: "FK__vital_sig__encou__6383C8BA"}]->(c171);
MERGE (c172)-[:FOREIGN_KEY_TO {constraint: "FK__vital_sig__patie__6477ECF3"}]->(c172);

// --- Domains ---
MERGE (dom_clinical:Domain {name: "clinical"});
MERGE (dom_general:Domain {name: "general"});
MERGE (dom_hr:Domain {name: "hr"});

// Domain-Table links
MERGE (t0)-[:BELONGS_TO_DOMAIN]->(dom_general);
MERGE (t1)-[:BELONGS_TO_DOMAIN]->(dom_general);
MERGE (t2)-[:BELONGS_TO_DOMAIN]->(dom_general);
MERGE (t3)-[:BELONGS_TO_DOMAIN]->(dom_hr);
MERGE (t4)-[:BELONGS_TO_DOMAIN]->(dom_clinical);
MERGE (t5)-[:BELONGS_TO_DOMAIN]->(dom_general);
MERGE (t6)-[:BELONGS_TO_DOMAIN]->(dom_clinical);
MERGE (t7)-[:BELONGS_TO_DOMAIN]->(dom_clinical);
MERGE (t8)-[:BELONGS_TO_DOMAIN]->(dom_clinical);
MERGE (t9)-[:BELONGS_TO_DOMAIN]->(dom_general);
MERGE (t10)-[:BELONGS_TO_DOMAIN]->(dom_general);
MERGE (t11)-[:BELONGS_TO_DOMAIN]->(dom_clinical);
