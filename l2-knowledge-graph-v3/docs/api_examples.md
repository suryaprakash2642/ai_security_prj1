# L2 Knowledge Graph — API Examples

All endpoints require service authentication via `Authorization: Bearer <token>`.
Tokens are HMAC-signed with format: `service_id|role|issued_at|signature`.

---

## Schema APIs

### GET /api/v1/graph/tables/by-domain

**Request:**
```bash
curl -H "Authorization: Bearer l3-retrieval|pipeline_reader|1709312000|<sig>" \
  "http://localhost:8000/api/v1/graph/tables/by-domain?domain=clinical"
```

**Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "fqn": "apollo_his.clinical.patients",
      "name": "patients",
      "description": "Core patient demographics and identifiers",
      "sensitivity_level": 4,
      "domain": "clinical",
      "is_active": true,
      "hard_deny": false,
      "schema_name": "clinical",
      "database_name": "apollo_his",
      "row_count_approx": 52300,
      "version": 3,
      "regulations": ["HIPAA", "DPDPA_2023"]
    },
    {
      "fqn": "apollo_his.clinical.encounters",
      "name": "encounters",
      "description": "Patient visit and encounter records",
      "sensitivity_level": 3,
      "domain": "clinical",
      "is_active": true,
      "hard_deny": false,
      "schema_name": "clinical",
      "database_name": "apollo_his",
      "row_count_approx": 184500,
      "version": 2,
      "regulations": ["HIPAA"]
    }
  ],
  "error": null,
  "meta": {"count": 2}
}
```

---

### GET /api/v1/graph/tables/{table_fqn}/columns

**Request:**
```bash
curl -H "Authorization: Bearer l3-retrieval|pipeline_reader|1709312000|<sig>" \
  "http://localhost:8000/api/v1/graph/tables/apollo_his.clinical.patients/columns"
```

**Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "fqn": "apollo_his.clinical.patients.mrn",
      "name": "mrn",
      "data_type": "varchar(20)",
      "is_pk": true,
      "is_nullable": false,
      "is_pii": true,
      "pii_type": "MEDICAL_RECORD_NUMBER",
      "sensitivity_level": 5,
      "masking_strategy": "HASH",
      "description": "Medical record number — primary patient identifier",
      "is_active": true,
      "regulations": ["HIPAA"]
    },
    {
      "fqn": "apollo_his.clinical.patients.full_name",
      "name": "full_name",
      "data_type": "varchar(200)",
      "is_pk": false,
      "is_nullable": false,
      "is_pii": true,
      "pii_type": "FULL_NAME",
      "sensitivity_level": 4,
      "masking_strategy": "REDACT",
      "description": "Patient full name",
      "is_active": true,
      "regulations": ["HIPAA"]
    }
  ],
  "error": null,
  "meta": {"count": 2}
}
```

---

### GET /api/v1/graph/tables/by-sensitivity

**Request:**
```bash
curl -H "Authorization: Bearer l6-validation|pipeline_reader|1709312000|<sig>" \
  "http://localhost:8000/api/v1/graph/tables/by-sensitivity?min_level=4"
```

**Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "fqn": "apollo_his.clinical.patients",
      "name": "patients",
      "sensitivity_level": 4,
      "domain": "clinical",
      "hard_deny": false
    },
    {
      "fqn": "apollo_his.behavioral_health.substance_abuse_records",
      "name": "substance_abuse_records",
      "sensitivity_level": 5,
      "domain": "behavioral_health",
      "hard_deny": true
    }
  ],
  "meta": {"count": 2}
}
```

---

### GET /api/v1/graph/foreign-keys/{table_fqn}

**Request:**
```bash
curl -H "Authorization: Bearer l6-validation|pipeline_reader|1709312000|<sig>" \
  "http://localhost:8000/api/v1/graph/foreign-keys/apollo_his.clinical.encounters"
```

**Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "source_column_fqn": "apollo_his.clinical.encounters.patient_mrn",
      "target_column_fqn": "apollo_his.clinical.patients.mrn",
      "source_table_fqn": "apollo_his.clinical.encounters",
      "target_table_fqn": "apollo_his.clinical.patients"
    }
  ],
  "meta": {"count": 1}
}
```

---

### GET /api/v1/graph/search/tables

**Request:**
```bash
curl -H "Authorization: Bearer l3-retrieval|pipeline_reader|1709312000|<sig>" \
  "http://localhost:8000/api/v1/graph/search/tables?q=patient&limit=5"
```

**Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "fqn": "apollo_his.clinical.patients",
      "name": "patients",
      "description": "Core patient demographics and identifiers",
      "sensitivity_level": 4,
      "domain": "clinical"
    }
  ],
  "meta": {"count": 1}
}
```

---

## Policy APIs

### GET /api/v1/graph/policies/for-roles

**Request:**
```bash
curl -H "Authorization: Bearer l4-policy|pipeline_reader|1709312000|<sig>" \
  "http://localhost:8000/api/v1/graph/policies/for-roles?roles=doctor&roles=nurse"
```

**Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "policy_id": "POL-001",
      "policy_type": "ALLOW",
      "nl_description": "Doctors may access patient demographic and clinical records for treatment purposes.",
      "structured_rule": {"effect": "ALLOW", "resources": ["patients", "encounters", "diagnoses"]},
      "priority": 100,
      "is_hard_deny": false,
      "bound_roles": ["doctor"],
      "target_tables": [],
      "target_domains": ["clinical"]
    },
    {
      "policy_id": "POL-002",
      "policy_type": "MASK",
      "nl_description": "Nurses may view patient records but PII fields must be masked.",
      "structured_rule": {"effect": "MASK", "columns": ["full_name", "date_of_birth", "aadhaar_number"]},
      "priority": 90,
      "is_hard_deny": false,
      "bound_roles": ["nurse"],
      "target_tables": [],
      "target_domains": ["clinical"]
    }
  ],
  "meta": {"count": 2}
}
```

---

### POST /api/v1/graph/policies/simulate

**Request:**
```bash
curl -X POST -H "Authorization: Bearer l4-policy|pipeline_reader|1709312000|<sig>" \
  -H "Content-Type: application/json" \
  "http://localhost:8000/api/v1/graph/policies/simulate" \
  -d '{
    "roles": ["nurse"],
    "table_fqns": [
      "apollo_his.clinical.patients",
      "apollo_his.behavioral_health.substance_abuse_records"
    ]
  }'
```

**Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "table_fqn": "apollo_his.clinical.patients",
      "effective_policy": "MASK",
      "is_hard_deny": false,
      "deny_reason": null,
      "masked_columns": ["full_name", "date_of_birth", "aadhaar_number"],
      "conditions": [],
      "applicable_policies": ["POL-002"]
    },
    {
      "table_fqn": "apollo_his.behavioral_health.substance_abuse_records",
      "effective_policy": "DENY",
      "is_hard_deny": true,
      "deny_reason": "Table is under HARD DENY protection (42 CFR Part 2). No NL-to-SQL access permitted.",
      "masked_columns": [],
      "conditions": [],
      "applicable_policies": []
    }
  ]
}
```

---

### GET /api/v1/graph/policies/join-restrictions

**Request:**
```bash
curl -H "Authorization: Bearer l4-policy|pipeline_reader|1709312000|<sig>" \
  "http://localhost:8000/api/v1/graph/policies/join-restrictions?roles=billing_staff"
```

**Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "policy_id": "POL-006",
      "restricted_domains": ["billing", "clinical"],
      "nl_description": "Billing staff denied from joining billing with clinical tables."
    }
  ],
  "meta": {"count": 1}
}
```

---

## Classification APIs

### GET /api/v1/graph/columns/pii

**Request:**
```bash
curl -H "Authorization: Bearer l6-validation|pipeline_reader|1709312000|<sig>" \
  "http://localhost:8000/api/v1/graph/columns/pii?domain=clinical"
```

**Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "column_fqn": "apollo_his.clinical.patients.mrn",
      "table_fqn": "apollo_his.clinical.patients",
      "pii_type": "MEDICAL_RECORD_NUMBER",
      "sensitivity_level": 5,
      "masking_strategy": "HASH"
    },
    {
      "column_fqn": "apollo_his.clinical.patients.full_name",
      "table_fqn": "apollo_his.clinical.patients",
      "pii_type": "FULL_NAME",
      "sensitivity_level": 4,
      "masking_strategy": "REDACT"
    },
    {
      "column_fqn": "apollo_his.clinical.patients.aadhaar_number",
      "table_fqn": "apollo_his.clinical.patients",
      "pii_type": "AADHAAR",
      "sensitivity_level": 5,
      "masking_strategy": "REDACT"
    }
  ],
  "meta": {"count": 3}
}
```

---

### GET /api/v1/graph/masking-rules/{table_fqn}

**Request:**
```bash
curl -H "Authorization: Bearer l6-validation|pipeline_reader|1709312000|<sig>" \
  "http://localhost:8000/api/v1/graph/masking-rules/apollo_his.clinical.patients"
```

**Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "column_fqn": "apollo_his.clinical.patients.mrn",
      "column_name": "mrn",
      "masking_strategy": "HASH",
      "pii_type": "MEDICAL_RECORD_NUMBER"
    },
    {
      "column_fqn": "apollo_his.clinical.patients.full_name",
      "column_name": "full_name",
      "masking_strategy": "REDACT",
      "pii_type": "FULL_NAME"
    },
    {
      "column_fqn": "apollo_his.clinical.patients.date_of_birth",
      "column_name": "date_of_birth",
      "masking_strategy": "GENERALIZE",
      "pii_type": "DATE_OF_BIRTH"
    },
    {
      "column_fqn": "apollo_his.clinical.patients.aadhaar_number",
      "column_name": "aadhaar_number",
      "masking_strategy": "REDACT",
      "pii_type": "AADHAAR"
    },
    {
      "column_fqn": "apollo_his.clinical.patients.email",
      "column_name": "email",
      "masking_strategy": "PARTIAL_MASK",
      "pii_type": "EMAIL"
    },
    {
      "column_fqn": "apollo_his.clinical.patients.phone",
      "column_name": "phone",
      "masking_strategy": "PARTIAL_MASK",
      "pii_type": "PHONE"
    }
  ],
  "meta": {"count": 6}
}
```

---

### GET /api/v1/graph/tables/regulated-by

**Request:**
```bash
curl -H "Authorization: Bearer l6-validation|pipeline_reader|1709312000|<sig>" \
  "http://localhost:8000/api/v1/graph/tables/regulated-by?regulation=42_CFR_PART_2"
```

**Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "fqn": "apollo_his.behavioral_health.substance_abuse_records",
      "name": "substance_abuse_records",
      "regulation_code": "42_CFR_PART_2",
      "hard_deny": true
    }
  ],
  "meta": {"count": 1}
}
```

---

## Admin APIs

### POST /api/v1/admin/crawl

**Request:**
```bash
curl -X POST -H "Authorization: Bearer schema-svc|schema_writer|1709312000|<sig>" \
  -H "Content-Type: application/json" \
  "http://localhost:8000/api/v1/admin/crawl" \
  -d '{
    "database_name": "apollo_his",
    "engine": "sqlserver",
    "connection_string": "mssql+aioodbc://readonly:***@db-host/apollo_his",
    "schemas": ["clinical", "billing"]
  }'
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "database": "apollo_his",
    "schemas_crawled": ["clinical", "billing"],
    "tables_found": 5,
    "tables_new": 0,
    "tables_updated": 2,
    "tables_deactivated": 0,
    "columns_found": 28,
    "columns_new": 3,
    "duration_seconds": 4.2
  },
  "meta": {"crawled_by": "schema-svc"}
}
```

---

### GET /api/v1/admin/health-checks

**Request:**
```bash
curl -H "Authorization: Bearer admin-svc|admin|1709312000|<sig>" \
  "http://localhost:8000/api/v1/admin/health-checks"
```

**Response (200):**
```json
{
  "success": true,
  "data": [
    {"check_name": "neo4j_connectivity", "passed": true, "details": "Neo4j read driver responsive", "items": []},
    {"check_name": "pg_audit_connectivity", "passed": true, "details": "PostgreSQL audit DB responsive", "items": []},
    {"check_name": "orphan_policies", "passed": true, "details": "No orphan policies", "items": []},
    {"check_name": "circular_role_inheritance", "passed": true, "details": "No circular inheritance", "items": []},
    {"check_name": "missing_domain_assignment", "passed": true, "details": "All tables have domains", "items": []},
    {"check_name": "pii_sensitivity_consistency", "passed": true, "details": "All PII columns meet minimum sensitivity", "items": []},
    {"check_name": "masking_consistency", "passed": true, "details": "All PII columns have masking strategies", "items": []},
    {"check_name": "substance_abuse_deny_enforcement", "passed": true, "details": "All substance abuse tables properly protected", "items": []}
  ],
  "meta": {"passed_all": true, "total_checks": 8}
}
```

---

## Error Responses

### 401 Unauthorized
```json
{"success": false, "error": "Invalid token signature", "data": null, "meta": {}}
```

### 403 Forbidden
```json
{"success": false, "error": "Service 'l3-retrieval' (role=pipeline_reader) lacks permission 'admin'", "data": null, "meta": {}}
```

### 500 Internal Server Error
```json
{"success": false, "error": "Internal server error", "data": null, "meta": {}}
```
