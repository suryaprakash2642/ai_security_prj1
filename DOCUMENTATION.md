# Apollo Hospitals — Zero Trust NL-to-SQL Pipeline
## Project Documentation

> **Version:** 1.0 &nbsp;|&nbsp; **Environment:** Development &nbsp;|&nbsp; **Last Updated:** 2026-03-08

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture Summary](#2-architecture-summary)
3. [Data Flow](#3-data-flow)
4. [Layer Reference](#4-layer-reference)
   - [L1 — Identity & Context](#l1--identity--context-resolution)
   - [L2 — Knowledge Graph](#l2--knowledge-graph)
   - [L3 — Intelligent Retrieval](#l3--intelligent-retrieval)
   - [L4 — Policy Resolution](#l4--policy-resolution)
   - [L5 — Secure Generation](#l5--secure-generation)
   - [L6 — Multi-Gate Validation](#l6--multi-gate-validation)
   - [L7 — Secure Execution](#l7--secure-execution)
   - [L8 — Audit & Anomaly Detection](#l8--audit--anomaly-detection)
5. [Frontend Dashboard](#5-frontend-dashboard)
6. [Mock Database & Knowledge Graph](#6-mock-database--knowledge-graph)
7. [Security Model](#7-security-model)
8. [Configuration Reference](#8-configuration-reference)
9. [Test Suite](#9-test-suite)
10. [Running the System](#10-running-the-system)
11. [Role-Based Access Control](#11-role-based-access-control)
12. [API Quick Reference](#12-api-quick-reference)

---

## 1. Project Overview

This project is a **Zero Trust, 8-layer AI security pipeline** built for Apollo Hospitals that transforms natural language questions into safe, policy-enforced SQL queries. It demonstrates how hospital staff can query clinical, financial, and administrative data using plain English — while the system automatically enforces role-based access control, PHI masking, audit logging, and anomaly detection at every step.

### Key Goals

| Goal | Implementation |
|------|----------------|
| Natural language → SQL | Azure OpenAI GPT-4.1 (L5) |
| Zero-trust access control | JWT auth (L1) + policy engine (L4) |
| Schema isolation | Semantic retrieval returns only authorized tables (L3) |
| PHI protection | Column masking + PII sanitization (L6, L7) |
| Immutable audit trail | SHA-256 hash chain in SQLite (L8) |
| Anomaly detection | Z-score, temporal, BTG monitoring (L8) |
| SQL injection prevention | 3-gate validation + rewriter (L6) |

### Technology Stack

| Component | Technology |
|-----------|------------|
| API Framework | FastAPI (Python 3.12) |
| Identity | Azure AD JWT (RS256) + HMAC-SHA256 |
| Knowledge Graph | Neo4j 5.x |
| Vector Search | TimescaleDB Cloud (pgvector) |
| LLM | Azure OpenAI (gpt-4.1 / gpt-4.1-mini) |
| SQL Parsing | sqlglot |
| Caching | Redis |
| Audit Store | SQLite (append-only, hash chain) |
| Frontend | Vanilla HTML/CSS/JS (single file) |

---

## 2. Architecture Summary

```
┌─────────────────────────────────────────────────────────────┐
│                    Apollo Hospitals Staff                    │
│              (Physician / Nurse / Billing / HR / Admin)     │
└──────────────────────────┬──────────────────────────────────┘
                           │  Natural Language Question
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                   Frontend Dashboard                          │
│          (Single-page HTML, localhost:3000)                   │
└──────────────────────────┬───────────────────────────────────┘
                           │
        ┌──────────────────▼───────────────────────────────────┐
        │  L1 — Identity & Context Resolution  (port 8001)     │
        │  JWT validation → SecurityContext (HMAC-signed)       │
        └──────────────────┬───────────────────────────────────┘
                           │ SecurityContext
        ┌──────────────────▼───────────────────────────────────┐
        │  L2 — Knowledge Graph              (port 8002)       │
        │  Neo4j: schema metadata, policies, role DAG           │
        └──────────────────┬───────────────────────────────────┘
                           │ Schema + Policy rules
        ┌──────────────────▼───────────────────────────────────┐
        │  L3 — Intelligent Retrieval        (port 8300)       │
        │  pgvector semantic search → filtered schema           │
        └────────┬─────────────────────────┬──────────────────┘
                 │                         │
        ┌────────▼────────┐   ┌────────────▼─────────────────┐
        │  L4 — Policy    │   │  filtered_schema + join_graph │
        │  Resolution     │   └─────────────┬────────────────┘
        │  (port 8400)    │                 │
        └────────┬────────┘                 │
                 │ PermissionEnvelope        │
        ┌────────▼─────────────────────────▼─────────────────┐
        │  L5 — Secure SQL Generation        (port 8500)      │
        │  Azure OpenAI GPT-4.1 → raw SQL                     │
        └──────────────────┬──────────────────────────────────┘
                           │ raw SQL
        ┌──────────────────▼───────────────────────────────────┐
        │  L6 — Multi-Gate Validation        (port 8600)       │
        │  Gate1 (structural) + Gate2 (classification)         │
        │  + Gate3 (behavioral) + Rewriter                     │
        └──────────────────┬───────────────────────────────────┘
                           │ validated SQL
        ┌──────────────────▼───────────────────────────────────┐
        │  L7 — Secure Execution             (port 8700)       │
        │  Circuit breaker + resource governor + PII masking   │
        └──────────────────┬───────────────────────────────────┘
                           │ sanitized results
        ┌──────────────────▼───────────────────────────────────┐
        │  L8 — Audit & Anomaly Detection    (port 8800)       │
        │  Immutable log + z-score anomaly + alert management  │
        └──────────────────────────────────────────────────────┘
```

---

## 3. Data Flow

A single query passes through the pipeline in the following sequence:

### Step-by-Step Flow

```
1. User selects role + types question in the Frontend

2. Frontend → L1 (Identity)
   POST /mock/token           → JWT token
   POST /identity/resolve     → SecurityContext (signed, ctx_id)
   GET  /identity/verify/{id} → full context (dept, clearance, session_id)

3. Frontend → L3 (Retrieval)
   POST /api/v1/retrieval/resolve
   Body: { question, security_context, request_id }
   Auth: Bearer <service_token>

   L3 internally:
   ├── Validates SecurityContext HMAC
   ├── Classifies query intent (CLINICAL_LOOKUP, AGGREGATION, TREND, etc.)
   ├── Embeds question → vector search in pgvector (TimescaleDB)
   ├── Keyword search in Neo4j
   ├── FK-walk graph expansion
   ├── Ranking by domain + relevance
   ├── Calls L4 for policy resolution
   └── Returns filtered_schema (only authorized tables + columns)

4. Frontend → L5 (SQL Generation)
   POST /api/v1/generate/sql
   Body: { question, filtered_schema, permission_envelope, dialect }

   L5 internally:
   ├── Scans question for injection patterns
   ├── Assembles secure prompt with schema fragment
   └── Calls Azure OpenAI GPT-4.1 → raw SQL

5. Frontend → L6 (Validation)
   POST /api/v1/validate/sql
   Body: { raw_sql, permission_envelope, dialect }

   L6 internally:
   ├── Gate1: structural checks (authorized tables/columns only)
   ├── Gate2: sensitivity classification (PII, PHI, regulatory)
   ├── Gate3: behavioral checks (DML/DDL, UNION, dynamic SQL)
   └── Rewriter: injects required filters, masks sensitive columns

6. Frontend → L7 (Execution)
   POST /api/v1/execute/sql
   Body: { validated_sql, permission_envelope, security_context }

   L7 internally:
   ├── Verifies permission envelope
   ├── Circuit breaker check
   ├── BTG monitoring
   ├── Resource governor (timeout, row limits)
   ├── Mock SQL execution → result set
   ├── Column-level masking
   └── PII sanitization

7. Frontend → L8 (Audit — fire-and-forget)
   POST /api/v1/audit/ingest
   Each pipeline step emits an audit event.

8. Frontend renders result table with masked values indicated
```

---

## 4. Layer Reference

---

### L1 — Identity & Context Resolution

**Port:** `8001` (Docker)
**Directory:** `l1-identity-context/`
**Venv:** `l1-identity-context/.venv/`

#### Purpose
Validates Azure AD JWTs, enriches the identity with organizational context, resolves role inheritance, and issues a signed **SecurityContext** stored in Redis.

#### Key Files

| File | Description |
|------|-------------|
| `app/api/routes.py` | All HTTP endpoints |
| `app/services/token_validation.py` | RS256 JWT validation + mock JWKS |
| `app/services/role_resolver.py` | Neo4j role inheritance DAG + clearance |
| `app/services/user_enrichment.py` | Mock HR/LDAP data (15 Apollo test users) |
| `app/services/context_builder.py` | Orchestrator: JWT → SecurityContext |
| `app/services/signing.py` | HMAC-SHA256 deterministic signing |
| `app/services/redis_store.py` | Redis sessions + JTI blacklist |
| `app/models/security_context.py` | SecurityContext schema (5 blocks) |

#### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/identity/resolve` | JWT → SecurityContext (primary entry point) |
| `GET` | `/identity/verify/{ctx_id}` | Fetch full SecurityContext from Redis |
| `POST` | `/identity/emergency` | Break-the-Glass escalation |
| `POST` | `/identity/revoke` | Revoke context + blacklist JTI |
| `GET` | `/health` | Service health |
| `POST` | `/mock/token` | Generate test JWT (dev only) |

#### SecurityContext Structure

```python
{
  # Identity block
  "user_id": "oid-dr-patel-4521",
  "effective_roles": ["ATTENDING_PHYSICIAN"],
  "department": "Cardiology",
  "clearance_level": 4,

  # Session block
  "session_id": "sess-abc123",
  "context_expiry": 1741700000,   # Unix timestamp
  "facility_id": "APJH",

  # Auth block
  "mfa_verified": true,
  "context_signature": "user_id|roles|dept|session_id|expiry|clearance|<hmac>"
}
```

#### Clearance Levels

| Level | Role Examples | Access |
|-------|--------------|--------|
| 1 | GUEST | Public data only |
| 2 | REGISTERED_NURSE, BILLING_STAFF, ADMIN | Operational data |
| 3 | HR_STAFF | HR + employee data |
| 4 | ATTENDING_PHYSICIAN | Full clinical data |
| 5 | CHIEF_MEDICAL_OFFICER | All data including PHI |

#### Signing Key
```
context_signing_key: dev-context-signing-key-32-chars-min
```
Signable payload: `user_id|sorted_roles|dept|session_id|expiry_ts|clearance`

---

### L2 — Knowledge Graph

**Port:** `8002`
**Directory:** `l2-knowledge-graph-v3/`
**Database:** Neo4j 5.x
**UI:** `l2-knowledge-graph-v3/ui/policy-console/` (React)

#### Purpose
Serves as the central schema registry and policy store. Contains all table/column metadata, data classifications, role hierarchy, and access policies as a Neo4j property graph.

#### Key Files

| File | Description |
|------|-------------|
| `app/routes/schema_routes.py` | Schema query endpoints |
| `app/routes/policy_routes.py` | Policy CRUD + simulation |
| `app/routes/classification_routes.py` | PII, masking, regulations |
| `app/routes/admin_routes.py` | Crawl, classify, embed, health |
| `app/repositories/graph_read_repo.py` | Parameterized read-only Neo4j queries |
| `app/services/classification_engine.py` | 15+ PII patterns, review queue |
| `app/services/embedding_pipeline.py` | pgvector + hash-based refresh |

#### Neo4j Graph Schema

**Node types:**

| Node | Properties | Count |
|------|-----------|-------|
| `Database` | name, type, host | 5 |
| `Schema` | name, database | 5 |
| `Table` | name, description, domain | 36 |
| `Column` | name, data_type, sensitivity, masked | 200+ |
| `Domain` | name (Clinical, Financial, HR, Admin, IT) | 5 |
| `Role` | name, clearance_level | 17 |
| `Policy` | id, effect (ALLOW/DENY), priority | 11 |
| `Condition` | type, value | varies |
| `Regulation` | name (HIPAA, GDPR, etc.) | 4 |

**Relationship types:**

| Relationship | From → To | Description |
|--------------|-----------|-------------|
| `HAS_SCHEMA` | Database → Schema | Containment |
| `HAS_TABLE` | Schema → Table | Containment |
| `HAS_COLUMN` | Table → Column | Containment |
| `FOREIGN_KEY_TO` | Column → Column | FK reference |
| `BELONGS_TO_DOMAIN` | Table/Column → Domain | Domain classification |
| `INHERITS_FROM` | Role → Role | Role inheritance DAG |
| `APPLIES_TO_ROLE` | Policy → Role | Policy applicability |
| `GOVERNS_TABLE` | Policy → Table | Table-level control |
| `GOVERNS_COLUMN` | Policy → Column | Column-level control |
| `REGULATED_BY` | Table/Column → Regulation | Compliance mapping |

#### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/graph/schema/{db}` | Full schema for a database |
| `GET` | `/api/v1/graph/tables/{table_id}` | Single table with columns |
| `POST` | `/api/v1/graph/roles/inherited` | Resolved role inheritance |
| `POST` | `/api/v1/graph/policies/resolve` | Policy simulation |
| `GET` | `/api/v1/graph/health` | 8-point integrity check |

---

### L3 — Intelligent Retrieval

**Port:** `8300`
**Directory:** `l3-intelligent-retrieval/`
**Venv:** `l3-intelligent-retrieval/.venv/`
**Config:** `config/settings.yaml`

#### Purpose
The core intelligence layer. Transforms a natural language question + SecurityContext into a `filtered_schema` containing only the tables and columns the user is authorized to see, ranked by semantic relevance to the question.

#### Key Files

| File | Description |
|------|-------------|
| `app/routes/retrieval_routes.py` | HTTP endpoints |
| `app/services/retrieval_pipeline.py` | 9-stage orchestration |
| `app/services/ranking_engine.py` | Domain-aware composite scoring |
| `app/services/column_scoper.py` | Column visibility (visible/masked/hidden) |
| `app/services/embedding_engine.py` | Question → embedding vector |
| `app/clients/l2_client.py` | Neo4j schema + fulltext search |
| `app/clients/l4_client.py` | Policy resolution calls |
| `app/clients/vector_search.py` | pgvector semantic search |
| `app/cache/cache_service.py` | Redis dual-layer cache |
| `app/auth.py` | HMAC service token validation |

#### 9-Stage Pipeline

```
Stage 1: SecurityContext validation
         ├── HMAC signature verification
         └── Context expiry check

Stage 2: Question embedding
         ├── SHA-256 cache lookup (Redis TTL 15min)
         └── Azure OpenAI text-embedding-ada-002

Stage 3: Intent classification
         ├── Rule-based regex matching
         └── Intents: DATA_LOOKUP, AGGREGATION, TREND,
                      CLINICAL_LOOKUP, FINANCIAL_LOOKUP,
                      HR_LOOKUP, ADMINISTRATIVE_LOOKUP

Stage 4: Multi-strategy retrieval (concurrent)
         ├── Semantic: pgvector cosine similarity
         ├── Keyword: Neo4j fulltext search
         └── FK-walk: graph expansion from anchor tables

Stage 5: Domain-aware ranking
         ├── Relevance score (vector distance)
         ├── Domain bonus (intent ↔ table domain match)
         └── Composite scoring

Stage 6: RBAC + L4 policy resolution
         ├── Role-domain pre-filter
         ├── POST /api/v1/policy/resolve → PermissionEnvelope
         └── Hard DENY overrides any ALLOW

Stage 7: Column-level scoping
         ├── VISIBLE: returned in filtered_schema
         ├── MASKED: returned with *** placeholder
         ├── HIDDEN: excluded from schema (not disclosed)
         └── COMPUTED: derived column definition

Stage 8: Join graph construction
         └── FK edges between all allowed tables

Stage 9: Context assembly
         └── Token budget enforcement (DDL fragments)
```

#### Intent Classification Gotchas

| Pattern | Detected Intent |
|---------|----------------|
| "last N months/weeks" | `TREND` |
| "CBC" (expands to "complete blood count") | `AGGREGATION` |
| "since", "over the past year" | `TREND` |
| "count of", "total", "average" | `AGGREGATION` |

#### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/retrieval/resolve` | Primary retrieval (main entry point) |
| `GET` | `/api/v1/retrieval/health` | Health + dependency status |
| `POST` | `/api/v1/retrieval/explain` | Debug trace (admin only) |
| `POST` | `/api/v1/retrieval/cache/clear` | Flush Redis caches |
| `GET` | `/api/v1/retrieval/stats` | Runtime statistics |
| `GET` | `/mock/service-token` | Dev service token (dev only) |

#### Request Format

```json
{
  "question": "Show all diagnoses for cardiology patients",
  "security_context": {
    "user_id": "oid-dr-patel-4521",
    "effective_roles": ["ATTENDING_PHYSICIAN"],
    "department": "Cardiology",
    "clearance_level": 4,
    "session_id": "sess-abc123",
    "context_expiry": 1741700000,
    "facility_id": "APJH",
    "context_signature": "<hmac-signature>"
  },
  "request_id": "req-abc123",
  "max_tables": 10,
  "include_ddl": true
}
```

#### Response Format

```json
{
  "success": true,
  "data": {
    "filtered_schema": [
      {
        "table_id": "diagnoses",
        "table_name": "diagnoses",
        "description": "Patient diagnosis records",
        "relevance_score": 0.92,
        "domain_tags": ["clinical"],
        "visible_columns": [
          { "name": "patient_id", "data_type": "varchar" },
          { "name": "diagnosis_code", "data_type": "varchar" }
        ],
        "masked_columns": [],
        "hidden_column_count": 0,
        "row_filters": ["facility_id = 'APJH'"],
        "aggregation_only": false,
        "ddl_fragment": "CREATE TABLE diagnoses ..."
      }
    ],
    "join_graph": {
      "edges": [
        { "from_table": "diagnoses", "to_table": "admissions",
          "from_column": "admission_id", "to_column": "id" }
      ]
    },
    "intent": {
      "intent": "CLINICAL_LOOKUP",
      "confidence": 0.95,
      "matched_keywords": ["diagnoses", "cardiology"]
    },
    "nl_policy_rules": ["Return results only for current facility"]
  }
}
```

#### Service Token Format

```
{service_id}|{role}|{issued_unix}|{hmac-sha256}

Example: test-service|pipeline_reader|1741600000|abc123...
Secret:  dev-secret-change-in-production-min-32-chars-xx
Auth:    Authorization: Bearer <token>
```

---

### L4 — Policy Resolution

**Port:** `8400`
**Directory:** `l4-policy-resolution/`

#### Purpose
A deterministic rules engine that resolves which tables a user can access, what columns are visible/masked, and what row-level filters apply — based on their roles, clearance level, and Neo4j policy graph.

#### Key Files

| File | Description |
|------|-------------|
| `app/api/routes/resolve.py` | `/api/v1/policy/resolve` endpoint |
| `app/services/orchestrator.py` | PolicyOrchestrator (rules engine) |
| `app/services/graph_client.py` | Neo4j read-only client |

#### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/policy/resolve` | Resolve policies for candidate tables |
| `GET` | `/health` | Service health |

#### Request / Response

```json
// Request
{
  "candidate_table_ids": ["diagnoses", "lab_results", "claims"],
  "effective_roles": ["ATTENDING_PHYSICIAN"],
  "user_context": {
    "clearance_level": 4,
    "department": "Cardiology",
    "facility_id": "APJH"
  },
  "request_id": "req-abc123"
}

// Response (PermissionEnvelope)
{
  "request_id": "req-abc123",
  "table_permissions": [
    {
      "table_id": "diagnoses",
      "decision": "ALLOW",
      "columns": [
        { "column_name": "patient_id", "visibility": "VISIBLE" },
        { "column_name": "hiv_status",  "visibility": "HIDDEN" }
      ],
      "row_filters": ["facility_id = 'APJH'"],
      "aggregation_only": false,
      "nl_rules": []
    },
    {
      "table_id": "claims",
      "decision": "DENY"
    }
  ],
  "global_nl_rules": ["Only return data for current facility"],
  "join_restrictions": []
}
```

#### Policy Evaluation Rules

1. **Hard DENY** always overrides ALLOW
2. **Clearance check**: `user.clearance_level >= table.min_clearance`
3. **Role match**: `policy.role IN user.effective_roles` (case-sensitive)
4. **Domain match**: role must have domain access for table's domain
5. **Facility scope**: row filter injected for multi-facility users

---

### L5 — Secure Generation

**Port:** `8500`
**Directory:** `l5-secure-generation/`
**Venv:** `l5-secure-generation/.venv/`

#### Purpose
Receives the filtered schema and permission envelope, assembles a security-constrained prompt, and calls Azure OpenAI to generate SQL. Returns raw SQL for L6 to validate.

#### Key Files

| File | Description |
|------|-------------|
| `app/api/routes/generate.py` | `/api/v1/generate/sql` endpoint |
| `app/services/generation_orchestrator.py` | Orchestration |
| `app/services/llm_client.py` | Azure OpenAI client (gpt-4.1 + fallback) |
| `app/services/prompt_assembler.py` | Secure prompt construction |
| `app/services/injection_scanner.py` | Input SQL injection risk scan |
| `app/services/response_parser.py` | Parse LLM output → clean SQL |
| `app/services/envelope_verifier.py` | Permission envelope validation |

#### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/generate/sql` | Generate SQL from NL question |
| `GET` | `/health` | Service health |

#### LLM Configuration

```
Provider:    Azure OpenAI
Primary:     gpt-4.1
Fallback:    gpt-4.1-mini
API Version: 2024-02-01
Max tokens:  2048 (prompt) + 1024 (completion)
```

#### Prompt Structure

```
[SYSTEM]
You are a secure SQL generator for Apollo Hospitals.
You MUST only use these authorized tables and columns:
{ddl_fragments}

Policy constraints:
{nl_policy_rules}
Row filters required: {row_filters}

[USER]
Generate a {dialect} SQL query for: {user_question}

Rules:
- Use ONLY the tables/columns listed above
- Always apply required row filters
- Return ONLY the SQL, no explanation
- If the question cannot be answered, return: CANNOT_ANSWER
```

---

### L6 — Multi-Gate Validation

**Port:** `8600`
**Directory:** `l6-multi-gate-validation/`
**Venv:** `l6-multi-gate-validation/.venv/`

#### Purpose
Three-gate security validator that inspects LLM-generated SQL for structural compliance, sensitivity violations, and behavioral anomalies. A rewriter injects required filters and masks sensitive columns before approving.

#### Key Files

| File | Description |
|------|-------------|
| `app/api/routes/validate.py` | `/api/v1/validate/sql` endpoint |
| `app/services/validation_orchestrator.py` | Gate pipeline orchestration |
| `app/services/gate1_structural.py` | Tables, columns, joins, aggregation |
| `app/services/gate2_classification.py` | Sensitivity, masking, regulations |
| `app/services/gate3_behavioral.py` | DML/DDL, UNION, dynamic SQL |
| `app/services/query_rewriter.py` | Filter injection + column masking |
| `app/services/sql_parser.py` | sqlglot-based SQL parsing |

#### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/validate/sql` | Validate SQL through all 3 gates |
| `GET` | `/health` | Service health |

#### Three Security Gates

**Gate 1 — Structural Validation**

| Check | Action on Fail |
|-------|---------------|
| Unauthorized table referenced | FAIL (CRITICAL) |
| Unauthorized column referenced | FAIL (CRITICAL) |
| JOIN to unauthorized table | FAIL (CRITICAL) |
| Missing required row filter | HIGH → Rewriter injects filter |
| Aggregation-only violation | FAIL (CRITICAL) |

**Gate 2 — Classification Validation**

| Check | Action on Fail |
|-------|---------------|
| Sensitive column not masked | FAIL (CRITICAL) |
| PHI column exposed | FAIL (CRITICAL) |
| HIPAA/GDPR violation | FAIL (CRITICAL) |

**Gate 3 — Behavioral Validation**

| Check | Action on Fail |
|-------|---------------|
| DML statement (INSERT/UPDATE/DELETE) | FAIL (CRITICAL) |
| DDL statement (DROP/TRUNCATE/ALTER) | FAIL (CRITICAL) |
| UNION / INTERSECT / EXCEPT | FAIL (HIGH) |
| Dynamic SQL (EXEC, sp_executesql) | FAIL (CRITICAL) |
| System table access | FAIL (CRITICAL) |
| Subquery injection pattern | FAIL (HIGH) |

#### Decision Logic

```
CRITICAL violation in any gate → decision = BLOCKED
HIGH violation → Rewriter attempts fix → re-evaluate
All gates PASS → decision = APPROVED + rewritten SQL
```

---

### L7 — Secure Execution

**Port:** `8700`
**Directory:** `l7-secure-execution/`
**Venv:** `l7-secure-execution/venv/`

#### Purpose
Executes the validated SQL against the (mock) database, enforcing resource limits, circuit breaking, BTG session monitoring, and post-execution PII sanitization.

#### Key Files

| File | Description |
|------|-------------|
| `app/api/routes/execute.py` | `/api/v1/execute/sql` endpoint |
| `app/services/execution_orchestrator.py` | 13-step pipeline |
| `app/services/circuit_breaker.py` | CLOSED / HALF_OPEN / OPEN state machine |
| `app/services/resource_governor.py` | Query timeout + row limits |
| `app/services/btg_monitor.py` | Break-the-Glass session tracking |
| `app/services/result_sanitizer.py` | PII masking + column sanitization |
| `app/services/envelope_verifier.py` | Permission envelope validation |

#### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/execute/sql` | Execute validated SQL |
| `GET` | `/api/v1/execute/health` | Service health |

#### 13-Step Execution Pipeline

```
 1. Permission envelope verification (signature + table list)
 2. SecurityContext validation (expiry + HMAC)
 3. Circuit breaker check (OPEN → reject immediately)
 4. BTG session monitoring (log elevated access)
 5. Resource governor (timeout budget, max rows)
 6. Connection acquisition (read-only DB connection pool)
 7. SQL execution (mock: returns typed result set)
 8. Row limit enforcement (truncate at max_rows)
 9. Column masking (apply PermissionEnvelope visibility)
10. PII sanitization (regex patterns: SSN, phone, email)
11. Result packaging (columns + rows + metadata)
12. Circuit breaker success recording
13. Audit event emission → L8
```

#### Circuit Breaker States

```
CLOSED (normal) → failure_count >= threshold → OPEN
OPEN (blocking)  → cooldown elapsed → HALF_OPEN
HALF_OPEN       → next request success → CLOSED
                → next request fail    → OPEN
```

#### Resource Limits (default)

| Parameter | Default |
|-----------|---------|
| Query timeout | 30s |
| Max rows returned | 500 |
| Max memory | 256 MB |
| Connection pool size | 5 |

---

### L8 — Audit & Anomaly Detection

**Port:** `8800`
**Directory:** `l8-audit-anomaly/`
**Venv:** `l8-audit-anomaly/venv/`

#### Purpose
The immutable audit backbone of the pipeline. All layers emit events to L8. Events are stored in an append-only SQLite database with a SHA-256 hash chain for tamper evidence. An anomaly detector runs z-score analysis and pattern detection to generate security alerts.

#### Key Files

| File | Description |
|------|-------------|
| `app/api/routes/ingest.py` | Event ingestion endpoint |
| `app/api/routes/query.py` | Audit log query + replay |
| `app/api/routes/alerts.py` | Alert management |
| `app/api/routes/reports.py` | Compliance report generation |
| `app/services/audit_store.py` | SQLite append-only log + hash chain |
| `app/services/anomaly_detector.py` | Z-score + pattern detection |
| `app/services/alert_manager.py` | Alert lifecycle management |
| `app/services/compliance_reporter.py` | Report generation |

#### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/audit/ingest` | Ingest event from any layer |
| `POST` | `/api/v1/audit/query` | Query log with filters + pagination |
| `GET` | `/api/v1/audit/replay/{request_id}` | Reconstruct full pipeline trace |
| `GET` | `/api/v1/audit/integrity/{layer}` | Verify hash chain for a layer |
| `GET` | `/api/v1/alerts` | List alerts (filterable) |
| `POST` | `/api/v1/alerts/{id}/acknowledge` | Acknowledge alert |
| `POST` | `/api/v1/alerts/{id}/resolve` | Resolve alert |
| `POST` | `/api/v1/audit/reports/generate` | Generate compliance report |
| `GET` | `/health` | Service health |

#### Audit Event Schema

```json
{
  "event_id": "evt-abc123",
  "event_type": "EXECUTION_COMPLETE",
  "source_layer": "L7",
  "timestamp": "2026-03-08T10:30:00Z",
  "request_id": "req-xyz789",
  "user_id": "oid-dr-patel-4521",
  "session_id": "sess-abc123",
  "severity": "INFO",
  "btg_active": false,
  "payload": {
    "rows_returned": 42,
    "execution_time_ms": 187,
    "database": "mock",
    "sanitization_events": 0
  }
}
```

#### Anomaly Detectors

| Detector | Algorithm | Trigger |
|----------|-----------|---------|
| Volume spike | Z-score (std=0 → 10.0) | Requests/hour > 3σ from baseline |
| Off-hours access | Temporal pattern | Access outside 06:00–22:00 local |
| Validation block spike | Rate tracking | > 5 blocks in 10 minutes |
| Sanitization spike | Rate tracking | > 10 PII masks in 5 minutes |
| BTG duration | Time threshold | BTG session > 4 hours |

#### Alert Severity Levels

| Severity | Color | Example |
|----------|-------|---------|
| `CRITICAL` | Red | Integrity violation, mass data export |
| `HIGH` | Amber | Repeated validation blocks |
| `WARNING` | Gray | Off-hours access |
| `INFO` | Blue | Normal operational event |

#### Hash Chain Integrity

Every ingested event is linked to the previous event's hash:
```
event_hash = SHA-256(prev_hash + event_id + timestamp + user_id + payload)
```
The `/api/v1/audit/integrity/{layer}` endpoint re-computes the entire chain and verifies each link.

#### Report Types

| Type | Description |
|------|-------------|
| `daily_summary` | Access counts by user/layer for today |
| `weekly_security` | Blocks, violations, anomalies for the week |
| `monthly_compliance` | HIPAA/GDPR access log for the month |
| `btg_justification` | All Break-the-Glass sessions with reasons |
| `breach_investigation` | Cross-user correlation for a time window |

---

## 5. Frontend Dashboard

**File:** `frontend/index.html`
**Served locally:** Open directly in browser (no build step)

### Features

| Feature | Description |
|---------|-------------|
| Role selector | 5 test users (physician, nurse, billing, admin, HR) |
| Auth flow | Login → L1 JWT → SecurityContext |
| Query input | Textarea + quick query shortcuts |
| Pipeline visualization | L1→L3→L5→L6→L7→L8 step status |
| Layer status panel | Real-time dot indicators per layer |
| Service health | ↻ Refresh pings all layer `/health` endpoints |
| SQL display | Syntax-highlighted SQL block |
| Validation panel | Gate1/Gate2/Gate3 pass/fail indicators |
| Results table | Paginated with masked columns (🔒) |
| Execution metrics | Rows, time, memory, PII masks |
| Audit log tab | Filter by layer, severity, user ID |
| Alerts tab | Active anomaly alerts with acknowledge/resolve |
| Reports tab | Generate compliance reports on-demand |

### Theme (Apollo Hospitals)

| Element | Color |
|---------|-------|
| Topbar background | `#003087` (Apollo deep navy) |
| Topbar accent border | `#C8102E` (Apollo red) |
| Page background | `#F2F6FC` (light blue-gray) |
| Cards | `#FFFFFF` (white) |
| Primary button | `#0057A8` (Apollo blue) |
| Error / danger | `#C8102E` (Apollo red) |
| Success | `#16A34A` |
| Text | `#1A2B4A` (dark navy) |

---

## 6. Mock Database & Knowledge Graph

**Directory:** `db_claude/apollo-mock-data/`

### Simulated Databases

| Database | Technology | Tables | Mock Records |
|----------|-----------|--------|-------------|
| Hospital Information System (HIS) | SQL Server | 11 | ~15,000 (patients, encounters, vitals, labs, Rx) |
| Human Resources | SQL Server | 5 | ~2,000 (employees, payroll, credentials) |
| Financial / Revenue Cycle | Oracle | 6 | ~7,700 (billings, claims, payments) |
| Analytics Warehouse | PostgreSQL | 4 | 12 months aggregated |
| Audit & Anomaly | PostgreSQL (TimescaleDB) | 6 | BTG sessions, alerts |

### Clinical Tables (HIS domain)

| Table | Key Columns | Clearance |
|-------|------------|-----------|
| `admissions` | patient_id, ward, admitted_at, discharge_at | 2 |
| `diagnoses` | patient_id, icd10_code, diagnosed_by | 2 |
| `prescriptions` | patient_id, drug_name, dosage, prescribed_by | 2 |
| `lab_orders` | patient_id, test_name, ordered_at | 2 |
| `lab_results` | patient_id, result_value, **hiv_status** (HIDDEN) | 2 |
| `vital_signs` | patient_id, bp, pulse, temperature | 2 |
| `nursing_assessments` | patient_id, nurse_id, notes | 2 |
| `therapy_notes` | patient_id, therapist_id, session_notes | 2 |
| `procedures` | patient_id, procedure_code, performed_at | 3 |
| `operating_room_schedules` | patient_id, surgeon_id, scheduled_at | 3 |
| `allergies` | patient_id, allergen, severity | 2 |
| `immunizations` | patient_id, vaccine_name, administered_at | 2 |

### Financial Tables

| Table | Domain | Access |
|-------|--------|--------|
| `claims` | Financial | BILLING_STAFF only |
| `accounts_receivable` | Financial | BILLING_STAFF only |
| `revenue_analytics` | Financial | BILLING_STAFF only |

### Administrative Tables

| Table | Domain | Access |
|-------|--------|--------|
| `department_kpis` | Administrative | ADMIN only |
| `cost_centers` | Administrative | ADMIN only |
| `vendor_master` | Administrative | ADMIN only |

### HR Tables

| Table | Domain | Access |
|-------|--------|--------|
| `attendance` | HR | HR_STAFF only |
| `leave_records` | HR | HR_STAFF only |
| `benefits` | HR | HR_STAFF only |
| `positions` | HR | HR_STAFF only |
| `departments` | HR | HR_STAFF only |
| `training_records` | HR | HR_STAFF only |

### Apollo Hospital Facilities

| ID | Name | City | Beds |
|----|------|------|------|
| APJH | Apollo Hospitals Jubilee Hills | Hyderabad | 550 |
| IPAH | Indraprastha Apollo | New Delhi | 710 |
| APGR | Apollo Hospitals Greams Road | Chennai | 560 |
| APBG | Apollo Hospitals Bannerghatta | Bangalore | 250 |
| APGL | Apollo Gleneagles | Kolkata | 510 |
| APNM | Apollo Hospitals Navi Mumbai | Mumbai | 200 |
| APBS | Apollo BGS Hospitals | Mysore | 200 |
| APAD | Apollo Adlux Hospital | Kochi | 150 |

---

## 7. Security Model

### Zero-Trust Principles

1. **Never trust, always verify** — every request validates the SecurityContext HMAC before processing
2. **Least-privilege** — users see only the schema relevant to their role
3. **Deny by default** — if no ALLOW policy matches, access is denied
4. **Hard DENY overrides** — explicit DENY cannot be overridden by any ALLOW
5. **No schema leakage** — denied table names are not disclosed in error responses
6. **Immutable audit trail** — every access is logged with hash-chain integrity

### Authentication Flow

```
1. User → L1: POST /mock/token (dev) or validate Azure AD JWT (prod)
   └── Returns signed JWT

2. JWT → L1: POST /identity/resolve
   ├── Validates JWT signature (RS256)
   ├── Enriches with HR/org data
   ├── Resolves role inheritance via Neo4j DAG
   ├── Computes clearance (MFA caps at level 3 if unverified)
   ├── Signs SecurityContext with HMAC-SHA256
   └── Stores in Redis (TTL 900s / 14400s for BTG)

3. SecurityContext passed to L3 with every query
   └── L3 re-validates HMAC + expiry before processing
```

### HMAC Signing

```python
# Signable payload (pipe-delimited)
payload = f"{user_id}|{sorted_roles}|{dept}|{session_id}|{expiry_ts}|{clearance}"

# Sign
import hmac, hashlib
sig = hmac.new(key.encode(), payload.encode(), hashlib.sha256).hexdigest()
context_signature = f"{payload}|{sig}"
```

### PHI Protection

| PHI Type | Mechanism |
|----------|-----------|
| HIV status | `HIDDEN` in column schema (not disclosed) |
| SSN / Tax ID | Regex masking in L7 result sanitizer |
| Phone numbers | Regex masking in L7 |
| Email addresses | Regex masking in L7 |
| Sensitive columns | `MASKED` visibility → `***` in results |

### Break-the-Glass (BTG)

Elevated emergency access for critical situations:
- Requires justification reason
- Extended session TTL (14400s vs 900s normal)
- All BTG queries logged with `btg_active: true`
- BTG duration anomaly triggers alert if > 4 hours
- `BTG Justification Report` available in L8

---

## 8. Configuration Reference

### L3 Settings (`l3-intelligent-retrieval/config/settings.yaml`)

```yaml
service:
  name: l3-intelligent-retrieval
  version: "1.0.0"
  environment: development
  host: "0.0.0.0"
  port: 8300

security:
  service_token_secret: "dev-secret-change-in-production-min-32-chars-xx"
  context_signing_key: "dev-context-signing-key-32-chars-min"
  token_expiry_seconds: 900

embedding:
  provider: azure_openai         # or: voyage, openai
  azure_endpoint: <endpoint>
  azure_api_key: <key>
  azure_deployment: text-embedding-ada-002
  dimension: 1536

dependencies:
  l2_base_url: "http://localhost:8002"
  l4_base_url: "http://localhost:8400"
  l2_timeout_seconds: 10
  l4_timeout_seconds: 10

cache:
  redis_url: "redis://localhost:6379"
  embedding_ttl: 900
  search_ttl: 300

vector_db:
  dsn: "postgresql://user:pass@timescale.cloud:5432/vectordb"
  table: schema_embeddings
```

### L5 Environment (`l5-secure-generation/.env`)

```env
LLM_PROVIDER=azure_openai
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com/
AZURE_OPENAI_API_KEY=<key>
AZURE_OPENAI_DEPLOYMENT=gpt-4.1
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_OPENAI_FALLBACK_DEPLOYMENT=gpt-4.1-mini

ENVELOPE_SIGNING_KEY=dev-context-signing-key-32-chars-min
SERVICE_TOKEN_SECRET=dev-secret-change-in-production-min-32-chars-xx

MAX_ROWS=500
MAX_PROMPT_TOKENS=2048
INJECTION_THRESHOLD=0.8
GENERATION_TIMEOUT=30
```

### Shared Secrets

| Secret | Value | Used By |
|--------|-------|---------|
| `service_token_secret` | `dev-secret-change-in-production-min-32-chars-xx` | L3, L5, L6 service tokens |
| `context_signing_key` | `dev-context-signing-key-32-chars-min` | L1 SecurityContext HMAC, L3 verify, L5 envelope |

> ⚠️ **These are development secrets. Rotate all secrets before any production deployment.**

---

## 9. Test Suite

### Summary

| Layer | Tests | Status | Run Command |
|-------|-------|--------|-------------|
| L1 | ~51 | ✅ Passing | `cd l1-identity-context && .venv/bin/python -m pytest tests/ -v` |
| L2 | 8+ | ✅ Passing | `cd l2-knowledge-graph-v3 && .venv/bin/python -m pytest tests/ -v` |
| L3 | 206 | ✅ Passing | `cd l3-intelligent-retrieval && .venv/bin/python -m pytest tests/ -v` |
| L4 | 2+ | ✅ Passing | `cd l4-policy-resolution && .venv/bin/python -m pytest tests/ -v` |
| L5 | 50 | ✅ Passing | `cd l5-secure-generation && .venv/bin/python -m pytest tests/ -v` |
| L6 | 56 | ✅ Passing | `cd l6-multi-gate-validation && .venv/bin/python -m pytest tests/ -v` |
| L7 | 49 | ✅ Passing | `cd l7-secure-execution && .venv/bin/python -m pytest tests/ -v` |
| L8 | 63 | ✅ Passing | `cd l8-audit-anomaly && .venv/bin/python -m pytest tests/ -v` |
| **Total** | **~485** | **✅** | |

### End-to-End Test Scripts

| Script | Description | Tests |
|--------|-------------|-------|
| `test_role_queries.py` | 33 role-based access tests (L1→L3) | 33/33 |
| `test_30_queries.py` | 30 queries × 5 roles = 150 tests | 150/150 |

Run E2E tests:
```bash
# From project root
l3-intelligent-retrieval/.venv/bin/python test_role_queries.py
l3-intelligent-retrieval/.venv/bin/python test_30_queries.py
```

### Key Test Patterns

**SecurityContext fixture (conftest.py):**
```python
# L3 conftest uses:
service_token_secret = "dev-l3-secret-must-be-at-least-32-characters-long"
context_signing_key  = "dev-context-signing-key-32-chars-min"

# Patch the underlying load function (not the lru_cached wrapper):
monkeypatch.setattr("app.config.load_settings", lambda: mock_settings)
```

**L4 mock signature:**
```python
def _fn(candidate_table_ids=None, **_kwargs):
    # Accept all kwargs — L3 passes: candidate_table_ids, effective_roles,
    # user_context, request_id
    return mock_permission_envelope
```

---

## 10. Running the System

### Prerequisites

| Service | Version | Notes |
|---------|---------|-------|
| Python | 3.12 | Each layer has its own venv |
| Neo4j | 5.x | Local or AuraDB |
| Redis | 7.x | Local |
| TimescaleDB / pgvector | Cloud | For vector search |
| Docker | 24+ | For L1 |

### Start All Services

```bash
cd /Users/apple/Documents/projects/ai_security
./start_all.sh
```

Or start individually:

```bash
# L1 (Docker)
cd l1-identity-context && docker compose up -d

# L2
cd l2-knowledge-graph-v3 && .venv/bin/uvicorn app.main:app --port 8002

# L3
cd l3-intelligent-retrieval && .venv/bin/uvicorn app.main:app --port 8300

# L4
cd l4-policy-resolution && .venv/bin/uvicorn app.api.main:app --port 8400

# L5
cd l5-secure-generation && .venv/bin/uvicorn app.main:app --port 8500

# L6
cd l6-multi-gate-validation && .venv/bin/uvicorn app.main:app --port 8600

# L7
cd l7-secure-execution && venv/bin/uvicorn app.main:app --port 8700

# L8
cd l8-audit-anomaly && venv/bin/uvicorn app.main:app --port 8800
```

### Frontend

```bash
# No build step needed — open directly:
open frontend/index.html
# Or serve with any static file server:
python3 -m http.server 3000 --directory frontend/
```

### One-Time Setup (Vector Search)

```bash
# Creates pgvector table + Neo4j fulltext index + embeds all 36 tables
cd l2-knowledge-graph-v3
.venv/bin/python ../setup_retrieval.py
```

### Health Check (all layers)

```bash
for port in 8001 8002 8300 8400 8500 8600 8700 8800; do
  echo -n "Port $port: "
  curl -s http://localhost:$port/health | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','unknown'))" 2>/dev/null || echo "offline"
done
```

---

## 11. Role-Based Access Control

### Test Users

| User | Role | Clearance | Department | OID |
|------|------|-----------|------------|-----|
| Dr. Rajesh Patel | `ATTENDING_PHYSICIAN` | 4 | Cardiology | `oid-dr-patel-4521` |
| Anita Kumar | `REGISTERED_NURSE` | 2 | Cardiology | `oid-nurse-kumar-2847` |
| Maria Fernandes | `BILLING_STAFF` | 2 | Finance | `oid-bill-maria-5521` |
| Vikram Joshi | `ADMIN` | 2 | IT | `oid-it-admin-7801` |
| Priya Mehta | `HR_STAFF` | 3 | Human Resources | `oid-hr-priya-7701` |

### Domain Access Matrix

| Domain | ATTENDING_PHYSICIAN | REGISTERED_NURSE | BILLING_STAFF | ADMIN | HR_STAFF |
|--------|:------------------:|:----------------:|:-------------:|:-----:|:--------:|
| Clinical | ✅ Full | ✅ Full | ❌ | ❌ | ❌ |
| Financial | ❌ | ❌ | ✅ Full | ❌ | ❌ |
| Administrative | ❌ | ❌ | ❌ | ✅ Full | ❌ |
| HR | ❌ | ❌ | ❌ | ❌ | ✅ Full |
| Audit | ❌ | ❌ | ❌ | ❌ | ❌ |

### PHI Masking Rules

| Column | Table | Physician | Nurse | Other |
|--------|-------|-----------|-------|-------|
| `hiv_status` | `lab_results` | HIDDEN | HIDDEN | HIDDEN |
| `ssn` | `patients` | MASKED | MASKED | DENIED |
| `salary` | `payroll` | DENIED | DENIED | DENIED |
| `tax_id` | `billing` | DENIED | DENIED | DENIED |

> `HIDDEN`: column not disclosed at all (hidden_column_count incremented)
> `MASKED`: column returned as `***` in results
> `DENIED`: table not accessible by that role

### Test Results (150-Query Role-Based Suite)

```
Dr. Rajesh Patel    [██████████████████████████████] 30/30
Anita Kumar         [██████████████████████████████] 30/30
Maria Fernandes     [██████████████████████████████] 30/30
Vikram Joshi        [██████████████████████████████] 30/30
Priya Mehta         [██████████████████████████████] 30/30
─────────────────────────────────────────────────────
TOTAL: 150/150 passed  |  0 failed
```

---

## 12. API Quick Reference

### L1 — Identity

```bash
# Get mock JWT
curl -X POST "http://localhost:8001/mock/token?oid=oid-dr-patel-4521&name=Dr.+Rajesh+Patel&email=dr.patel@apollo.com&include_mfa=true" \
  -H "Content-Type: application/json" \
  -d '{"roles":["ATTENDING_PHYSICIAN"],"groups":["clinical-cardiology"]}'

# Resolve SecurityContext
curl -X POST http://localhost:8001/identity/resolve \
  -H "Authorization: Bearer <jwt>"

# Verify full context
curl http://localhost:8001/identity/verify/<ctx_id> \
  -H "Authorization: Bearer <jwt>"
```

### L3 — Retrieval

```bash
# Get dev service token
curl http://localhost:8300/mock/service-token

# Query
curl -X POST http://localhost:8300/api/v1/retrieval/resolve \
  -H "Authorization: Bearer <service_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Show all patient admissions this month",
    "security_context": { ... },
    "request_id": "req-001"
  }'
```

### L6 — Validation

```bash
curl -X POST http://localhost:8600/api/v1/validate/sql \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "req-001",
    "raw_sql": "SELECT * FROM diagnoses WHERE facility_id = '\''APJH'\''",
    "dialect": "postgresql",
    "permission_envelope": { ... }
  }'
```

### L8 — Audit

```bash
# Query audit log
curl -X POST http://localhost:8800/api/v1/audit/query \
  -H "Content-Type: application/json" \
  -d '{
    "filters": { "source_layer": ["L7"], "severity": ["HIGH"] },
    "pagination": { "offset": 0, "limit": 50 },
    "sort": { "field": "timestamp", "order": "desc" }
  }'

# Verify hash chain
curl http://localhost:8800/api/v1/audit/integrity/L7

# List active alerts
curl "http://localhost:8800/api/v1/alerts?alert_status=OPEN&limit=20"

# Generate report
curl -X POST http://localhost:8800/api/v1/audit/reports/generate \
  -H "Content-Type: application/json" \
  -d '{"report_type": "daily_summary"}'
```

---

## Appendix: File Structure

```
ai_security/
├── frontend/
│   └── index.html                    # Single-page dashboard (Apollo theme)
│
├── l1-identity-context/              # Port 8001 (Docker)
│   ├── app/
│   │   ├── api/routes.py
│   │   ├── models/security_context.py
│   │   └── services/
│   │       ├── token_validation.py
│   │       ├── role_resolver.py
│   │       ├── context_builder.py
│   │       └── signing.py
│   └── tests/ (51 tests)
│
├── l2-knowledge-graph-v3/            # Port 8002
│   ├── app/
│   │   ├── routes/
│   │   ├── repositories/
│   │   └── services/
│   ├── ui/policy-console/            # React admin UI
│   └── tests/
│
├── l3-intelligent-retrieval/         # Port 8300
│   ├── app/
│   │   ├── routes/retrieval_routes.py
│   │   ├── services/
│   │   │   ├── retrieval_pipeline.py
│   │   │   ├── ranking_engine.py
│   │   │   └── column_scoper.py
│   │   ├── clients/
│   │   │   ├── l2_client.py
│   │   │   ├── l4_client.py
│   │   │   └── vector_search.py
│   │   └── cache/
│   ├── config/settings.yaml
│   └── tests/ (206 tests)
│
├── l4-policy-resolution/             # Port 8400
│   ├── app/api/routes/resolve.py
│   ├── app/services/orchestrator.py
│   └── tests/
│
├── l5-secure-generation/             # Port 8500
│   ├── app/
│   │   ├── services/
│   │   │   ├── llm_client.py
│   │   │   ├── prompt_assembler.py
│   │   │   ├── injection_scanner.py
│   │   │   └── response_parser.py
│   │   └── api/routes/generate.py
│   ├── .env
│   └── tests/ (50 tests)
│
├── l6-multi-gate-validation/         # Port 8600
│   ├── app/services/
│   │   ├── gate1_structural.py
│   │   ├── gate2_classification.py
│   │   ├── gate3_behavioral.py
│   │   └── query_rewriter.py
│   └── tests/ (56 tests)
│
├── l7-secure-execution/              # Port 8700
│   ├── app/services/
│   │   ├── circuit_breaker.py
│   │   ├── resource_governor.py
│   │   ├── result_sanitizer.py
│   │   └── btg_monitor.py
│   └── tests/ (49 tests)
│
├── l8-audit-anomaly/                 # Port 8800
│   ├── app/services/
│   │   ├── audit_store.py
│   │   ├── anomaly_detector.py
│   │   └── alert_manager.py
│   └── tests/ (63 tests)
│
├── db_claude/apollo-mock-data/
│   ├── sql-server-his/               # 11 clinical tables, ~15K records
│   ├── sql-server-hr/                # 5 HR tables, ~2K records
│   ├── oracle-financial/             # 6 financial tables, ~7.7K records
│   ├── pg-analytics/                 # 4 analytics tables
│   ├── pg-audit/                     # 6 audit tables
│   ├── neo4j-knowledge-graph/        # Graph schema (Cypher)
│   ├── policy-config/                # policies.json, roles.json
│   └── identity-config/              # users.json (15 test users)
│
├── setup_retrieval.py                # One-time vector index setup
├── test_role_queries.py              # 33-query role-based E2E tests
├── test_30_queries.py                # 150-query role-based E2E tests
├── start_all.sh                      # Start all services
├── stop_all.sh                       # Stop all services
└── MANUAL_TEST_GUIDE.md              # Manual testing walkthrough
```

---

*Documentation generated for Apollo Hospitals — Zero Trust NL-to-SQL Pipeline v1.0*
