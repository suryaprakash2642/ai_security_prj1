# Apollo Hospitals Zero Trust NL-to-SQL — Manual Test Guide

**Document Version:** 2.0
**Pipeline:** L1 Identity → L2 Knowledge Graph → L3 Retrieval → L4 Policy → L5 SQL Generation → L6 Validation → L7 Execution → L8 Audit

---

## Table of Contents

1. [Prerequisites & Setup](#1-prerequisites--setup)
2. [Starting All Services](#2-starting-all-services)
3. [Role-Based Demo Scenarios (Frontend)](#3-role-based-demo-scenarios-frontend)
   - [Role 1 — Attending Physician (Dr. Rajesh Patel)](#role-1--attending-physician-dr-rajesh-patel)
   - [Role 2 — Registered Nurse (Anita Kumar)](#role-2--registered-nurse-anita-kumar)
   - [Role 3 — Billing Clerk (Maria Fernandes)](#role-3--billing-clerk-maria-fernandes)
   - [Role 4 — IT Administrator (Vikram Joshi)](#role-4--it-administrator-vikram-joshi)
   - [Role 5 — HR Manager (Priya Mehta)](#role-5--hr-manager-priya-mehta)
4. [Cross-Role Comparison Demo](#4-cross-role-comparison-demo)
5. [Security Feature Demonstrations](#5-security-feature-demonstrations)
6. [Layer-by-Layer API Tests (curl)](#6-layer-by-layer-api-tests-curl)
7. [Audit & Anomaly Detection Tests](#7-audit--anomaly-detection-tests)
8. [Compliance Report Tests](#8-compliance-report-tests)
9. [Expected Results Reference](#9-expected-results-reference)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Prerequisites & Setup

### Required Software
- Python 3.10+ (each layer uses its own venv)
- `curl` (for API tests)
- A browser (Chrome / Firefox / Safari)

### Directory Structure
```
ai_security/
  l1-identity-context/        # Port 8001
  l2-knowledge-graph-v3/      # Port 8002
  l3-intelligent-retrieval/   # Port 8300
  l4-policy-resolution/       # Port 8400
  l5-secure-generation/       # Port 8500
  l6-multi-gate-validation/   # Port 8600
  l7-secure-execution/        # Port 8700
  l8-audit-anomaly/           # Port 8800
  frontend/                   # Port 3000 (static HTML)
  start_all.sh
  stop_all.sh
```

### Install Dependencies (first time only)
```bash
cd l1-identity-context && python3 -m venv venv && venv/bin/pip install -r requirements.txt
cd l2-knowledge-graph-v3 && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cd l3-intelligent-retrieval && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cd l4-policy-resolution && python3 -m venv venv && venv/bin/pip install -r requirements.txt
cd l5-secure-generation && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cd l6-multi-gate-validation && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cd l7-secure-execution && python3 -m venv venv && venv/bin/pip install -r requirements.txt
cd l8-audit-anomaly && python3 -m venv venv && venv/bin/pip install -r requirements.txt
```

---

## 2. Starting All Services

### 2.1 Start Everything at Once
```bash
cd /Users/apple/Documents/projects/ai_security
./start_all.sh
```

**Expected output:** All 8 services start with PID numbers, followed by a health check table showing ✓ for each.

### 2.2 Verify All Services Are Online
```bash
for port in 8001 8002 8300 8400 8500 8600 8700 8800; do
  echo -n "Port $port: "
  curl -sf http://localhost:$port/health | python3 -m json.tool | grep status || echo "OFFLINE"
done
```

### 2.3 Open the Frontend Dashboard
Navigate to: **http://localhost:3000**

The left sidebar shows a live health indicator (●) for each layer. All 8 dots should be green before running demos.

### 2.4 Stop All Services
```bash
./stop_all.sh
```

---

## 3. Role-Based Demo Scenarios (Frontend)

Open **http://localhost:3000** in your browser before running any scenario below.

---

### Role 1 — Attending Physician (Dr. Rajesh Patel)

**Profile:**
| Field | Value |
|---|---|
| Name | Dr. Rajesh Patel |
| Role | ATTENDING_PHYSICIAN |
| Department | Cardiology |
| Facility | FAC-001 (Apollo Jubilee Hills) |
| Clearance Level | **4 — Highly Confidential** |
| MFA | Yes |
| Data Domain | Clinical |
| Policies | CLIN-001, HIPAA-001 |

**What this role can access:** Full clinical patient data — admissions, encounters, diagnoses, lab results, vitals, prescriptions — for patients in their assigned units. No financial or HR data.

---

#### TC-PHY-01: Login as Attending Physician

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Open http://localhost:3000 | Dashboard loads with dark theme, all layer dots green |
| 2 | Select **"Dr. Rajesh Patel — Attending Physician"** from the user dropdown | User selected |
| 3 | Click **Login** | Button shows "…" briefly |
| 4 | Wait 1–2 seconds | Auth badge turns **green**: "Dr. Rajesh Patel" |
| 5 | Inspect the auth info panel (sidebar) | Shows: `user_id: oid-dr-patel-4521`, `roles: ATTENDING_PHYSICIAN`, `clearance: 4`, `dept: Cardiology` |
| 6 | Confirm L1 layer dot | Turns green |

**Pass criteria:** Green auth badge. Clearance shown as **4**.

---

#### TC-PHY-02: Query — Patient Admissions (Happy Path)

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | (Logged in as Dr. Patel) In the query box, type: `Show all patients admitted this month with a cardiac diagnosis` | Query entered |
| 2 | Click **▶ Run** | Pipeline progress card appears; L3 → L5 → L6 → L7 → L8 lights animate |
| 3 | L3 retrieves schema | 3–5 clinical tables returned (admissions, patients, diagnoses) |
| 4 | L5 generates SQL | SQL visible in code block — a `SELECT` targeting clinical tables |
| 5 | L6 validates | Green **"APPROVED"** badge |
| 6 | L7 executes | Results table shows patient rows |
| 7 | Status bar | "✓ Success — N rows returned" |

**Pass criteria:** Clinical data rows returned. SQL is a valid `SELECT`. No data blocked.

---

#### TC-PHY-03: Query — Lab Results

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | (Logged in as Dr. Patel) Type: `Show blood test results for patients in the cardiology ward` | Query entered |
| 2 | Click **▶ Run** | Pipeline runs |
| 3 | L5 SQL | References lab_results or investigations table |
| 4 | L7 result | Lab result rows returned |
| 5 | PII columns (e.g. phone, address) | Shown as `****` or masked — physician sees clinical data but PII is still sanitised per HIPAA |

**Pass criteria:** Lab data returned. PII columns masked per HIPAA minimum necessary.

---

#### TC-PHY-04: Query — Billing Data (Access Denied)

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | (Logged in as Dr. Patel) Type: `Show me staff salary records and payroll data` | Query entered |
| 2 | Click **▶ Run** | Pipeline runs |
| 3 | L3/L4 outcome | HR/payroll tables denied by policy; L3 returns CANNOT_ANSWER or restricted schema |
| 4 | L5 | Returns CANNOT_ANSWER — no applicable schema for this user's domain |
| 5 | Status bar | Error or "No relevant tables found for this query" |

**Pass criteria:** No payroll data returned. Physician cannot access HR financial records.

---

### Role 2 — Registered Nurse (Anita Kumar)

**Profile:**
| Field | Value |
|---|---|
| Name | Anita Kumar |
| Role | REGISTERED_NURSE |
| Department | Cardiology |
| Facility | FAC-001 |
| Clearance Level | **2 — Internal** |
| MFA | Yes |
| Data Domain | Clinical |
| Policies | CLIN-002, HIPAA-001 |
| Assigned Units | UNIT-1A-APJH, UNIT-1B-APJH |

**What this role can access:** Clinical ward data for their assigned units. Sees patient demographics and vitals but **not** full diagnoses or sensitive clinical notes. Cannot access financial, HR, or other departments' patient data.

---

#### TC-NUR-01: Login as Registered Nurse

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Click **Logout** (if already logged in) | Auth badge turns red "Not Authenticated" |
| 2 | Select **"Anita Kumar — Registered Nurse"** from dropdown | User selected |
| 3 | Click **Login** | Authenticates successfully |
| 4 | Inspect auth info panel | `roles: REGISTERED_NURSE`, `clearance: 2`, `dept: Cardiology` |

**Pass criteria:** Green auth badge. Clearance shown as **2** (lower than physician's 4).

---

#### TC-NUR-02: Query — Ward Patient List (Allowed)

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | (Logged in as Anita Kumar) Type: `List patients currently admitted in the cardiology ward` | Query entered |
| 2 | Click **▶ Run** | Pipeline runs |
| 3 | L4 policy | Ward-level patient data permitted for CLIN-002 |
| 4 | L7 result | Patient list returned with basic demographics (name, MRN, admission date) |
| 5 | Note: **fewer columns** than physician query | Diagnosis columns may be absent or masked |

**Pass criteria:** Patient list returned. Fewer or different columns compared to physician view — demonstrates role-based column access.

---

#### TC-NUR-03: Query — Sensitive Diagnosis Data (Restricted)

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | (Logged in as Anita Kumar) Type: `Show psychiatric evaluation notes and mental health diagnoses` | Query entered |
| 2 | Click **▶ Run** | Pipeline runs |
| 3 | L3/L4 | Psychiatric data tables require RESTRICTED_DATA_HANDLER role (clearance 5); nurse is clearance 2 — tables denied |
| 4 | L5 | CANNOT_ANSWER or access denied |
| 5 | Status | Error indicating insufficient clearance |

**Pass criteria:** No psychiatric data returned. Demonstrates clearance-level enforcement (2 vs 5 required).

---

#### TC-NUR-04: Query — Financial/Billing Data (Out of Domain)

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | (Logged in as Anita Kumar) Type: `Show patient billing invoices and insurance claims` | Query entered |
| 2 | Click **▶ Run** | Pipeline runs |
| 3 | L4 policy | Billing tables require FINANCE domain — nurse is CLINICAL domain |
| 4 | Result | No financial tables in schema; CANNOT_ANSWER |

**Pass criteria:** Zero billing rows returned. Domain boundary enforced.

---

### Role 3 — Billing Clerk (Maria Fernandes)

**Profile:**
| Field | Value |
|---|---|
| Name | Maria Fernandes |
| Role | BILLING_CLERK |
| Department | Billing & Revenue Cycle |
| Facility | FAC-001 |
| Clearance Level | **2 — Internal** |
| MFA | Yes |
| Data Domain | Financial |
| Policies | BIZ-001, HIPAA-001, SEC-002 |

**What this role can access:** Billing tables — claims, invoices, insurance authorisations, payment records. **Cannot access** clinical patient records, diagnoses, lab results, or HR data. Patient identifiers visible only as MRN (not full name/DOB per HIPAA minimum necessary).

---

#### TC-BILL-01: Login as Billing Clerk

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Click **Logout** | Auth clears |
| 2 | Select **"Maria Fernandes — Billing Clerk"** from dropdown | User selected |
| 3 | Click **Login** | Authenticates |
| 4 | Auth info panel | `roles: BILLING_CLERK`, `clearance: 2`, `dept: Billing & Revenue Cycle` |

**Pass criteria:** Green auth badge. Domain shows Financial.

---

#### TC-BILL-02: Query — Insurance Claims (Allowed)

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | (Logged in as Maria Fernandes) Type: `Show all pending insurance claims from this month` | Query entered |
| 2 | Click **▶ Run** | Pipeline runs |
| 3 | L3 schema | Billing/claims tables included; clinical tables absent |
| 4 | L4 policy | BIZ-001 policy permits claims table access |
| 5 | L7 result | Claims rows returned — claim_id, amount, status, insurer |
| 6 | Patient columns | MRN only shown (not full name or DOB) |

**Pass criteria:** Claims data returned. Clinical columns absent. Demonstrates financial domain access.

---

#### TC-BILL-03: Query — Revenue Summary (Allowed)

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | (Logged in as Maria Fernandes) Type: `Total revenue collected by department this quarter` | Query entered |
| 2 | Click **▶ Run** | Pipeline runs |
| 3 | L5 SQL | Aggregation query against billing/revenue tables |
| 4 | L7 result | Department revenue totals returned |

**Pass criteria:** Revenue summary returned. Demonstrates billing domain aggregation.

---

#### TC-BILL-04: Query — Clinical Patient Records (Denied)

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | (Logged in as Maria Fernandes) Type: `Show me patient diagnoses and lab test results` | Query entered |
| 2 | Click **▶ Run** | Pipeline runs |
| 3 | L3/L4 | Clinical tables (diagnoses, lab_results) denied for FINANCIAL domain user |
| 4 | L5 | CANNOT_ANSWER — no clinical schema available for this user |
| 5 | Status | Access denied or no relevant tables |

**Pass criteria:** Zero clinical rows returned. This is the key zero-trust demonstration — billing staff cannot read patient clinical records even by asking in plain English.

---

### Role 4 — IT Administrator (Vikram Joshi)

**Profile:**
| Field | Value |
|---|---|
| Name | Vikram Joshi |
| Role | IT_ADMINISTRATOR |
| Department | Information Technology |
| Facility | FAC-001 |
| Clearance Level | **2 — Internal** |
| MFA | Yes |
| Data Domain | IT Operations |
| Policies | IT-001 |

**What this role can access:** System configuration data, IT service logs, infrastructure audit records. **Cannot access** patient clinical data, financial records, or HR staff data.

---

#### TC-IT-01: Login as IT Administrator

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Click **Logout** | Auth clears |
| 2 | Select **"Vikram Joshi — IT Administrator"** from dropdown | User selected |
| 3 | Click **Login** | Authenticates |
| 4 | Auth info panel | `roles: IT_ADMINISTRATOR`, `clearance: 2`, `dept: Information Technology` |

**Pass criteria:** Green auth badge. Domain shows IT_OPERATIONS.

---

#### TC-IT-02: Query — System Audit Logs (Allowed)

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | (Logged in as Vikram Joshi) Type: `Show system login events from the last 7 days` | Query entered |
| 2 | Click **▶ Run** | Pipeline runs |
| 3 | L3 schema | IT/audit-related tables returned |
| 4 | L7 result | Login event records returned (timestamp, user_id, source_ip, event_type) |

**Pass criteria:** System event data returned. No clinical or patient data visible.

---

#### TC-IT-03: Query — Patient Clinical Data (Denied)

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | (Logged in as Vikram Joshi) Type: `Show all patient admissions and their diagnoses` | Query entered |
| 2 | Click **▶ Run** | Pipeline runs |
| 3 | L3/L4 | Clinical tables denied for IT_OPERATIONS domain — policy IT-001 does not include CLIN tables |
| 4 | Result | CANNOT_ANSWER; clinical data not accessible |

**Pass criteria:** Zero patient rows. Demonstrates that IT staff cannot access clinical records even though they administer the systems running them.

---

#### TC-IT-04: Query — Financial Records (Denied)

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | (Logged in as Vikram Joshi) Type: `Show employee salary and payroll transactions` | Query entered |
| 2 | Click **▶ Run** | Pipeline runs |
| 3 | L3/L4 | Financial/HR tables denied for IT domain |
| 4 | Result | CANNOT_ANSWER |

**Pass criteria:** No financial data returned.

---

### Role 5 — HR Manager (Priya Mehta)

**Profile:**
| Field | Value |
|---|---|
| Name | Priya Mehta |
| Role | HR_MANAGER |
| Department | Human Resources |
| Facility | FAC-001 |
| Clearance Level | **3 — Confidential** |
| MFA | Yes |
| Data Domain | Administrative |
| Policies | HR-001, SEC-003 |

**What this role can access:** Employee records, HR data, staffing information. **Cannot access** patient clinical records, patient financial billing data, or IT system logs.

---

#### TC-HR-01: Login as HR Manager

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Click **Logout** | Auth clears |
| 2 | Select **"Priya Mehta — HR Manager"** from dropdown | User selected |
| 3 | Click **Login** | Authenticates |
| 4 | Auth info panel | `roles: HR_MANAGER`, `clearance: 3`, `dept: Human Resources` |

**Pass criteria:** Green auth badge. Clearance **3** — higher than nurse/billing (demonstrates role hierarchy).

---

#### TC-HR-02: Query — Employee Records (Allowed)

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | (Logged in as Priya Mehta) Type: `Show all active nursing staff in the cardiology department` | Query entered |
| 2 | Click **▶ Run** | Pipeline runs |
| 3 | L3 schema | HR/employee tables included |
| 4 | L7 result | Employee list with name, role, department, employment status |

**Pass criteria:** HR staff records returned. Demonstrates administrative data access.

---

#### TC-HR-03: Query — Staff Attendance / Leave (Allowed)

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | (Logged in as Priya Mehta) Type: `How many staff members are on leave this week?` | Query entered |
| 2 | Click **▶ Run** | Pipeline runs |
| 3 | L5 SQL | Aggregation against HR leave/attendance table |
| 4 | L7 result | Count of staff on leave, by department |

**Pass criteria:** HR leave summary returned.

---

#### TC-HR-04: Query — Patient Clinical Records (Denied)

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | (Logged in as Priya Mehta) Type: `Show me patient diagnoses and medical records` | Query entered |
| 2 | Click **▶ Run** | Pipeline runs |
| 3 | L3/L4 | Clinical tables denied for ADMINISTRATIVE domain |
| 4 | Result | CANNOT_ANSWER |

**Pass criteria:** No patient data returned. HR cannot read patient medical records.

---

## 4. Cross-Role Comparison Demo

This section demonstrates the same query producing different results for different roles — the clearest illustration of Zero Trust access control.

**Query to run for all 5 roles:** `Show patient admission records`

| User | Role | Clearance | Expected Result |
|------|------|-----------|-----------------|
| Dr. Rajesh Patel | ATTENDING_PHYSICIAN | 4 | Full admissions table — patient_id, name, DOB, diagnosis, admission_date, ward |
| Anita Kumar | REGISTERED_NURSE | 2 | Admissions for assigned units only — fewer columns, no full diagnosis |
| Maria Fernandes | BILLING_CLERK | 2 | CANNOT_ANSWER — clinical admissions table denied for financial domain |
| Vikram Joshi | IT_ADMINISTRATOR | 2 | CANNOT_ANSWER — clinical domain not accessible to IT |
| Priya Mehta | HR_MANAGER | 3 | CANNOT_ANSWER — patient records denied for administrative domain |

### How to run the comparison:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Login as Dr. Rajesh Patel, run query `Show patient admission records`, note the columns and row count | Full clinical data returned |
| 2 | Logout → Login as Anita Kumar, run same query | Fewer columns, unit-filtered rows |
| 3 | Logout → Login as Maria Fernandes, run same query | Access denied — zero clinical rows |
| 4 | Logout → Login as Vikram Joshi, run same query | Access denied — zero clinical rows |
| 5 | Logout → Login as Priya Mehta, run same query | Access denied — zero clinical rows |

**Key talking point for client:** The natural language question is identical. The Zero Trust pipeline — not the user — enforces what data is returned. No matter how the question is phrased, the policy boundary holds.

---

## 5. Security Feature Demonstrations

### TC-SEC-01: SQL Injection Attempt (Frontend)

Demonstrates that L6 blocks destructive SQL even if it somehow passes through L5.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Login as any user | Authenticated |
| 2 | In the query box type: `DROP TABLE patients` | Query entered |
| 3 | Click **▶ Run** | Pipeline starts |
| 4 | L6 validation | Must show **red "BLOCKED"** badge |
| 5 | Status bar | "SQL BLOCKED by L6 — DDL_FORBIDDEN" |
| 6 | L7 | Not called — execution never reaches database |

**Pass criteria:** L6 BLOCKED. No database change occurs.

---

### TC-SEC-02: UNION Injection Attempt (Frontend)

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Login as any user | Authenticated |
| 2 | Type: `Show patients UNION SELECT username password FROM admin_users` | Query entered |
| 3 | Click **▶ Run** | Pipeline runs |
| 4 | L6 | Detects UNION across non-permitted tables — **BLOCKED** |
| 5 | Violation code | `UNION_INJECTION` |

**Pass criteria:** L6 BLOCKED. Admin credentials never exposed.

---

### TC-SEC-03: PII Masking — Nurse vs Physician

Demonstrates column-level data masking based on role clearance.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Login as Dr. Rajesh Patel | Physician authenticated |
| 2 | Type: `Show patient contact details including phone numbers` | Query entered |
| 3 | Note phone column values in result | Values may appear as `+91-XXXXX-XXXXX` (partially masked per HIPAA) |
| 4 | Logout → Login as Anita Kumar (nurse) | Lower clearance |
| 5 | Run same query | Phone column values show as `****` (fully masked for clearance 2) |

**Pass criteria:** Nurse sees more masking than physician. Demonstrates clearance-level column masking.

---

### TC-SEC-04: Unauthenticated Access Attempt

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Ensure you are logged out (auth badge red) | Not authenticated |
| 2 | Click **▶ Run** without logging in | Immediate client-side block |
| 3 | Toast message | "Please login first" |
| 4 | L1 layer | Never called |

**Pass criteria:** No pipeline call made without valid session.

---

### TC-SEC-05: Row Limit Enforcement

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Login as Dr. Rajesh Patel | Authenticated |
| 2 | Type: `Show all patients ever admitted to Apollo Hospitals` | Very broad query |
| 3 | Click **▶ Run** | Pipeline runs |
| 4 | L7 result | Row count capped (max 1000 rows by default config) |
| 5 | Result metadata | `truncated: true` if source has more rows |

**Pass criteria:** Row count ≤ configured max. Prevents bulk data exfiltration.

---

## 6. Layer-by-Layer API Tests (curl)

### 6.1 L1 — Identity & Context

#### TC-L1-01: Generate Mock JWT — Physician
```bash
export JWT=$(curl -s -X POST \
  "http://localhost:8001/mock/token?oid=oid-dr-patel-4521&name=Dr.+Rajesh+Patel&email=dr.patel%40apollohospitals.com&include_mfa=true" \
  -H "Content-Type: application/json" \
  -d '{"roles": ["ATTENDING_PHYSICIAN"], "groups": ["clinical-cardiology"]}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
echo "JWT acquired: ${JWT:0:40}..."
```

#### TC-L1-02: Generate Mock JWT — Nurse
```bash
export JWT_NURSE=$(curl -s -X POST \
  "http://localhost:8001/mock/token?oid=oid-nurse-kumar-2847&name=Anita+Kumar&email=anita.kumar%40apollohospitals.com&include_mfa=true" \
  -H "Content-Type: application/json" \
  -d '{"roles": ["REGISTERED_NURSE"], "groups": ["clinical-cardiology"]}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
```

#### TC-L1-03: Generate Mock JWT — Billing Clerk
```bash
export JWT_BILLING=$(curl -s -X POST \
  "http://localhost:8001/mock/token?oid=oid-bill-maria-5521&name=Maria+Fernandes&email=maria.fernandes%40apollohospitals.com&include_mfa=true" \
  -H "Content-Type: application/json" \
  -d '{"roles": ["BILLING_CLERK"], "groups": ["billing-ops"]}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
```

#### TC-L1-04: Resolve Security Context
```bash
curl -s -X POST http://localhost:8001/api/identity/resolve \
  -H "Authorization: Bearer $JWT" \
  | python3 -m json.tool
```

**Expected response:**
```json
{
  "context_token_id": "ctx-...",
  "user_id": "oid-dr-patel-4521",
  "effective_roles": ["ATTENDING_PHYSICIAN", "CLINICIAN", "EMPLOYEE", "HEALTHCARE_PROVIDER", "HIPAA_COVERED_ENTITY", "SENIOR_CLINICIAN"],
  "max_clearance_level": 4,
  "ttl_seconds": 3600,
  "signature": "..."
}
```

Save the context token:
```bash
export CTX=$(curl -s -X POST http://localhost:8001/api/identity/resolve \
  -H "Authorization: Bearer $JWT" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['context_token_id'])")
echo "Context token: $CTX"
```

#### TC-L1-05: Verify Context (Downstream Layers Call This)
```bash
curl -s http://localhost:8001/api/identity/verify/$CTX | python3 -m json.tool
```
**Expected:** Full SecurityContext with `identity`, `authorization`, `org_context`, `request_metadata` blocks.

#### TC-L1-06: Health Check
```bash
curl -s http://localhost:8001/health | python3 -m json.tool
```
**Expected:** `{ "status": "healthy", "mock_idp_enabled": true, "redis_connected": true }`

---

### 6.2 L2 — Knowledge Graph

#### TC-L2-01: Get Clinical Tables
```bash
curl -s "http://localhost:8002/api/v1/graph/tables/by-domain?domain=clinical&limit=10" \
  | python3 -m json.tool
```
**Expected:** List of clinical tables (admissions, encounters, patients, diagnoses, lab_results, etc.)

#### TC-L2-02: Get Financial Tables
```bash
curl -s "http://localhost:8002/api/v1/graph/tables/by-domain?domain=financial&limit=10" \
  | python3 -m json.tool
```
**Expected:** Billing, claims, insurance tables — different set from clinical.

#### TC-L2-03: Search Tables by Keyword
```bash
curl -s "http://localhost:8002/api/v1/graph/search/tables?q=patient&limit=5" \
  | python3 -m json.tool
```
**Expected:** Tables with "patient" in name or description.

#### TC-L2-04: Get PII Masking Rules
```bash
curl -s "http://localhost:8002/api/v1/graph/classifications/masking-rules/ApolloHIS.clinical.patients" \
  | python3 -m json.tool
```
**Expected:** Masking rules for PII columns (full_name → partial, phone → redact, DOB → year only, etc.)

---

### 6.3 L3 — Intelligent Retrieval

**Note:** L3 calls L2 and L4 internally. All three must be running.

Build a security context first (reuse TC-L1-04):
```bash
export SC=$(curl -s -X POST http://localhost:8001/api/identity/resolve \
  -H "Authorization: Bearer $JWT")
echo $SC | python3 -m json.tool
```

#### TC-L3-01: Retrieve Schema — Physician Query
```bash
echo $SC | python3 -c "
import sys, json
sc = json.load(sys.stdin)
body = {
  'question': 'Show all patients admitted this month with cardiac diagnosis',
  'security_context': sc,
  'request_id': 'test-l3-physician-001',
  'max_tables': 5
}
print(json.dumps(body))
" | curl -s -X POST http://localhost:8300/api/v1/retrieval/resolve \
  -H "Content-Type: application/json" \
  -d @- | python3 -m json.tool
```

**Expected (key fields):**
```json
{
  "filtered_schema": { "tables": [ ... 3-5 clinical tables ... ], "join_graph": [...] },
  "permission_envelope": { "table_permissions": [...], "signature": "..." },
  "metadata": { "tables_retrieved": 4, "intent": "DATA_LOOKUP" }
}
```

#### TC-L3-02: Retrieve Schema — Billing Clerk Query (Restricted)
```bash
export SC_BILLING=$(curl -s -X POST http://localhost:8001/api/identity/resolve \
  -H "Authorization: Bearer $JWT_BILLING")

echo $SC_BILLING | python3 -c "
import sys, json
sc = json.load(sys.stdin)
body = {
  'question': 'Show patient diagnoses and lab results',
  'security_context': sc,
  'request_id': 'test-l3-billing-001',
  'max_tables': 5
}
print(json.dumps(body))
" | curl -s -X POST http://localhost:8300/api/v1/retrieval/resolve \
  -H "Content-Type: application/json" \
  -d @- | python3 -m json.tool
```

**Expected:** Clinical tables denied in permission_envelope; `filtered_schema.tables` is empty or billing-only. Compare to TC-L3-01 to see the difference in schema returned per role.

---

### 6.4 L5 — SQL Generation

#### TC-L5-01: Generate SQL from Physician Schema
```bash
curl -s -X POST http://localhost:8500/api/v1/generate/sql \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "test-l5-001",
    "user_question": "Show all patients admitted this month with a cardiac diagnosis",
    "permission_envelope": {
      "user_id": "oid-dr-patel-4521", "session_id": "sess-001",
      "issued_at": "2026-03-07T00:00:00Z", "expires_at": "2026-03-07T01:00:00Z",
      "signature": "",
      "table_permissions": [
        {"table_fqn": "ApolloHIS.clinical.admissions", "access": "SELECT", "columns": [], "row_filters": []},
        {"table_fqn": "ApolloHIS.clinical.diagnoses",  "access": "SELECT", "columns": [], "row_filters": []}
      ]
    },
    "filtered_schema": {
      "tables": [
        {"fqn": "ApolloHIS.clinical.admissions", "columns": [
          {"name":"patient_id","type":"VARCHAR"},{"name":"admission_date","type":"DATE"},{"name":"ward","type":"VARCHAR"}
        ], "row_filters": []},
        {"fqn": "ApolloHIS.clinical.diagnoses", "columns": [
          {"name":"patient_id","type":"VARCHAR"},{"name":"icd_code","type":"VARCHAR"},{"name":"diagnosis_text","type":"VARCHAR"}
        ], "row_filters": []}
      ],
      "join_graph": [{"left": "admissions", "right": "diagnoses", "on": "patient_id"}]
    },
    "dialect": "postgresql",
    "security_context": {"user_id": "oid-dr-patel-4521", "roles": ["ATTENDING_PHYSICIAN"]}
  }' | python3 -m json.tool
```

**Expected:**
```json
{ "raw_sql": "SELECT a.patient_id, a.admission_date, d.icd_code, d.diagnosis_text FROM ApolloHIS.clinical.admissions a JOIN ApolloHIS.clinical.diagnoses d ON a.patient_id = d.patient_id WHERE a.admission_date >= DATE_TRUNC('month', CURRENT_DATE)", ... }
```

---

### 6.5 L6 — Multi-Gate Validation

#### TC-L6-01: Approve a Safe Query
```bash
curl -s -X POST http://localhost:8600/api/v1/validate/sql \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "test-l6-001",
    "raw_sql": "SELECT patient_id, admission_date, ward FROM admissions WHERE admission_date >= CURRENT_DATE - INTERVAL '\''30 days'\''",
    "dialect": "postgresql",
    "permission_envelope": {
      "user_id": "oid-dr-patel-4521", "session_id": "sess-001",
      "issued_at": "2026-03-07T00:00:00Z", "expires_at": "2026-03-07T01:00:00Z",
      "signature": "",
      "table_permissions": [{"table_fqn": "admissions", "access": "SELECT", "columns": [], "row_filters": []}]
    }
  }' | python3 -m json.tool
```
**Expected:** `{ "decision": "APPROVED", "gate_results": { "gate1": {"decision":"PASS"}, "gate2": {"decision":"PASS"}, "gate3": {"decision":"PASS"} } }`

#### TC-L6-02: Block DROP TABLE
```bash
curl -s -X POST http://localhost:8600/api/v1/validate/sql \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "test-l6-002",
    "raw_sql": "DROP TABLE patients",
    "dialect": "postgresql",
    "permission_envelope": {
      "user_id": "attacker", "session_id": "sess", "issued_at": "2026-03-07T00:00:00Z",
      "expires_at": "2026-03-07T01:00:00Z", "signature": "", "table_permissions": []
    }
  }' | python3 -m json.tool
```
**Expected:** `{ "decision": "BLOCKED", "violations": [{ "code": "DDL_FORBIDDEN", "severity": "CRITICAL" }] }`

#### TC-L6-03: Block UNION Injection
```bash
curl -s -X POST http://localhost:8600/api/v1/validate/sql \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "test-l6-003",
    "raw_sql": "SELECT * FROM admissions UNION SELECT username, password, null FROM admin_users",
    "dialect": "postgresql",
    "permission_envelope": {
      "user_id": "attacker", "session_id": "sess", "issued_at": "2026-03-07T00:00:00Z",
      "expires_at": "2026-03-07T01:00:00Z", "signature": "",
      "table_permissions": [{"table_fqn": "admissions", "access": "SELECT", "columns": [], "row_filters": []}]
    }
  }' | python3 -m json.tool
```
**Expected:** `{ "decision": "BLOCKED", "violations": [{ "code": "UNION_INJECTION", "severity": "CRITICAL" }] }`

#### TC-L6-04: Block System Table Access
```bash
curl -s -X POST http://localhost:8600/api/v1/validate/sql \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "test-l6-004",
    "raw_sql": "SELECT * FROM information_schema.tables",
    "dialect": "postgresql",
    "permission_envelope": {
      "user_id": "attacker", "session_id": "sess", "issued_at": "2026-03-07T00:00:00Z",
      "expires_at": "2026-03-07T01:00:00Z", "signature": "", "table_permissions": []
    }
  }' | python3 -m json.tool
```
**Expected:** `{ "decision": "BLOCKED", "violations": [{ "code": "SYSTEM_TABLE_ACCESS" }] }`

#### TC-L6-05: Block Stored Procedure Execution
```bash
curl -s -X POST http://localhost:8600/api/v1/validate/sql \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "test-l6-005",
    "raw_sql": "EXEC xp_cmdshell '\''dir'\''",
    "dialect": "mssql",
    "permission_envelope": {
      "user_id": "attacker", "session_id": "sess", "issued_at": "2026-03-07T00:00:00Z",
      "expires_at": "2026-03-07T01:00:00Z", "signature": "", "table_permissions": []
    }
  }' | python3 -m json.tool
```
**Expected:** `{ "decision": "BLOCKED", "violations": [{ "code": "STORED_PROC_FORBIDDEN" }] }`

---

### 6.6 L7 — Secure Execution

#### TC-L7-01: Execute Safe Query
```bash
curl -s -X POST http://localhost:8700/api/v1/execute/sql \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "test-l7-001",
    "validated_sql": "SELECT patient_id, admission_date FROM admissions LIMIT 10",
    "dialect": "postgresql",
    "target_database": "mock",
    "permission_envelope": {
      "user_id": "oid-dr-patel-4521", "session_id": "sess-001",
      "issued_at": "2026-03-07T00:00:00Z", "expires_at": "2026-03-07T01:00:00Z",
      "signature": "",
      "table_permissions": [{"table_fqn": "admissions", "access": "SELECT", "columns": [], "row_filters": []}]
    },
    "security_context": { "user_id": "oid-dr-patel-4521", "session_id": "sess-001" }
  }' | python3 -m json.tool
```

**Expected:**
```json
{
  "status": "SUCCESS",
  "columns": [{"name": "patient_id"}, {"name": "admission_date"}],
  "rows": [["MRN-001234", "2026-01-15"], ...],
  "row_count": 10,
  "execution_metadata": { "database": "mock", "execution_time_ms": 52.3, "btg_active": false }
}
```

#### TC-L7-02: Execute Query with Column Masking (Nurse)
```bash
curl -s -X POST http://localhost:8700/api/v1/execute/sql \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "test-l7-002",
    "validated_sql": "SELECT patient_id, phone FROM patients LIMIT 5",
    "dialect": "postgresql",
    "target_database": "mock",
    "permission_envelope": {
      "user_id": "oid-nurse-kumar-2847", "session_id": "sess-002",
      "issued_at": "2026-03-07T00:00:00Z", "expires_at": "2026-03-07T01:00:00Z",
      "signature": "",
      "table_permissions": [{
        "table_fqn": "patients", "access": "SELECT",
        "columns": [{"column_name": "phone", "visibility": "MASKED", "masking_expression": null}],
        "row_filters": []
      }]
    },
    "security_context": { "user_id": "oid-nurse-kumar-2847", "session_id": "sess-002" }
  }' | python3 -m json.tool
```
**Expected:** `phone` column values shown as `****`. Demonstrates column-level masking for clearance-2 role.

#### TC-L7-03: Circuit Breaker Health
```bash
curl -s http://localhost:8700/api/v1/execute/health | python3 -m json.tool
```
**Expected:** `{ "status": "ok", "circuit_breakers": { "mock": "CLOSED" } }`

---

### 6.7 L8 — Audit & Anomaly Detection

#### TC-L8-01: Ingest Execution Event
```bash
curl -s -X POST http://localhost:8800/api/v1/audit/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "evt-manual-test-001",
    "event_type": "EXECUTION_COMPLETE",
    "source_layer": "L7",
    "timestamp": "2026-03-07T10:00:00Z",
    "request_id": "req-manual-001",
    "user_id": "oid-dr-patel-4521",
    "session_id": "sess-test",
    "severity": "INFO",
    "btg_active": false,
    "payload": { "rows_returned": 25, "execution_time_ms": 120, "database": "mock" }
  }' | python3 -m json.tool
```
**Expected:** HTTP 201, event stored with `chain_hash` field.

#### TC-L8-02: Query Audit Log for User
```bash
curl -s -X POST http://localhost:8800/api/v1/audit/query \
  -H "Content-Type: application/json" \
  -d '{ "filters": { "user_id": "oid-dr-patel-4521" }, "pagination": { "offset": 0, "limit": 10 } }' \
  | python3 -m json.tool
```
**Expected:** Events list for Dr. Patel with `total` count.

#### TC-L8-03: Verify Hash Chain Integrity
```bash
curl -s http://localhost:8800/api/v1/audit/integrity/L7 | python3 -m json.tool
```
**Expected:** `{ "valid": true, "detail": "Hash chain valid — N events verified" }`

#### TC-L8-04: Replay Pipeline for a Request
```bash
curl -s http://localhost:8800/api/v1/audit/replay/req-manual-001 | python3 -m json.tool
```
**Expected:** All audit events for `req-manual-001` in chronological order, showing the full pipeline trace.

#### TC-L8-05: List Active Alerts
```bash
curl -s "http://localhost:8800/api/v1/alerts?limit=20" | python3 -m json.tool
```

---

## 7. Audit & Anomaly Detection Tests

### TC-AUD-01: Volume Anomaly — Burst of Queries

Simulates a user running an unusually high number of queries in a short window:

```bash
for i in $(seq 1 30); do
  curl -s -X POST http://localhost:8800/api/v1/audit/ingest \
    -H "Content-Type: application/json" \
    -d "{
      \"event_id\": \"evt-vol-$i\",
      \"event_type\": \"EXECUTION_COMPLETE\",
      \"source_layer\": \"L7\",
      \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
      \"request_id\": \"req-vol-$i\",
      \"user_id\": \"anomaly-test-user\",
      \"severity\": \"INFO\",
      \"payload\": { \"rows_returned\": 100 }
    }" > /dev/null
done
echo "30 burst events sent"

# Check for volume alert
curl -s "http://localhost:8800/api/v1/alerts?limit=10" | python3 -m json.tool
```
**Expected:** `VOLUME` type alert with `WARNING` or `HIGH` severity after the burst exceeds z-score threshold.

---

### TC-AUD-02: Temporal Anomaly — Off-Hours Access

```bash
curl -s -X POST http://localhost:8800/api/v1/audit/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "evt-temporal-001",
    "event_type": "EXECUTION_COMPLETE",
    "source_layer": "L7",
    "timestamp": "2026-03-07T03:00:00Z",
    "request_id": "req-temporal-001",
    "user_id": "oid-bill-maria-5521",
    "severity": "INFO",
    "btg_active": false,
    "payload": { "rows_returned": 50 }
  }' | python3 -m json.tool

curl -s "http://localhost:8800/api/v1/alerts?limit=10" | python3 -m json.tool
```
**Expected:** `TEMPORAL` alert — billing clerk accessing data at 3:00 AM is flagged as suspicious.

---

### TC-AUD-03: Validation Block Spike — Repeated Injection Attempts

```bash
for i in 1 2 3; do
  curl -s -X POST http://localhost:8800/api/v1/audit/ingest \
    -H "Content-Type: application/json" \
    -d "{
      \"event_id\": \"evt-block-$i\",
      \"event_type\": \"VALIDATION_BLOCK\",
      \"source_layer\": \"L6\",
      \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
      \"request_id\": \"req-block-$i\",
      \"user_id\": \"suspicious-user\",
      \"severity\": \"HIGH\",
      \"payload\": { \"violations\": [{\"code\": \"UNION_INJECTION\"}] }
    }" > /dev/null
done

curl -s "http://localhost:8800/api/v1/alerts?limit=10" | python3 -m json.tool
```
**Expected:** `VALIDATION_BLOCK_SPIKE` alert — 3 injection attempts by same user triggers HIGH severity alert.

---

### TC-AUD-04: Acknowledge and Resolve an Alert

```bash
# 1. Get an open alert ID
ALERT_ID=$(curl -s "http://localhost:8800/api/v1/alerts?alert_status=OPEN&limit=1" \
  | python3 -c "import sys,json; a=json.load(sys.stdin); print(a[0]['alert_id'] if a else 'none')")
echo "Alert: $ALERT_ID"

# 2. Acknowledge
curl -s -X POST "http://localhost:8800/api/v1/alerts/${ALERT_ID}/acknowledge" \
  -H "Content-Type: application/json" \
  -d '{"notes": "Reviewed — on-call physician confirmed legitimate off-hours access"}' \
  | python3 -m json.tool

# 3. Resolve
curl -s -X POST "http://localhost:8800/api/v1/alerts/${ALERT_ID}/resolve" \
  | python3 -m json.tool
```
**Expected:** Status transitions `OPEN → ACKNOWLEDGED → RESOLVED`.

---

### TC-AUD-05: Hash Chain Integrity — Tamper Evidence

```bash
# Ingest 5 events
for i in 1 2 3 4 5; do
  curl -s -X POST http://localhost:8800/api/v1/audit/ingest \
    -H "Content-Type: application/json" \
    -d "{
      \"event_id\": \"evt-chain-$i\",
      \"event_type\": \"EXECUTION_COMPLETE\",
      \"source_layer\": \"L7\",
      \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
      \"request_id\": \"req-chain-$i\",
      \"user_id\": \"chain-test-user\",
      \"severity\": \"INFO\",
      \"payload\": {}
    }" > /dev/null
done

# Verify chain is intact
curl -s http://localhost:8800/api/v1/audit/integrity/L7 | python3 -m json.tool
```
**Expected:** `{ "valid": true }` — the SHA-256 hash chain across all events is intact. Any tampered record would break the chain and return `valid: false`.

---

## 8. Compliance Report Tests

### TC-RPT-01: Daily Summary Report
```bash
curl -s -X POST http://localhost:8800/api/v1/audit/reports/generate \
  -H "Content-Type: application/json" \
  -d '{ "report_type": "daily_summary" }' \
  | python3 -m json.tool
```
**Expected fields:**
- `total_events` — total audit events today
- `unique_users` — distinct users who ran queries
- `btg_activations` — Break-the-Glass activations (should be 0 in normal operation)
- `validation_blocks` — number of SQL queries blocked by L6
- `denial_rate` — fraction of requests that were denied
- `anomaly_alerts` — breakdown of INFO / WARNING / HIGH / CRITICAL alerts

---

### TC-RPT-02: Breach Investigation Report
```bash
curl -s -X POST http://localhost:8800/api/v1/audit/reports/generate \
  -H "Content-Type: application/json" \
  -d '{
    "report_type": "breach_investigation",
    "filters": { "request_id": "req-manual-001" }
  }' | python3 -m json.tool
```
**Expected:** All audit events for `req-manual-001` with cross-layer chain (L1→L3→L5→L6→L7→L8), useful for forensic investigation.

---

### TC-RPT-03: BTG Justification Report
```bash
curl -s -X POST http://localhost:8800/api/v1/audit/reports/generate \
  -H "Content-Type: application/json" \
  -d '{ "report_type": "btg_justification", "filters": {} }' \
  | python3 -m json.tool
```
**Expected:** List of all Break-the-Glass activations with user, reason, patient_id, timestamp. Supports HIPAA audit obligations.

---

### TC-RPT-04: Monthly HIPAA Compliance Report
```bash
curl -s -X POST http://localhost:8800/api/v1/audit/reports/generate \
  -H "Content-Type: application/json" \
  -d '{ "report_type": "monthly_compliance" }' \
  | python3 -m json.tool
```
**Expected fields:**
- `minimum_necessary_compliance.score` — float; lower is better
- `minimum_necessary_compliance.compliance_level` — `"excellent"` / `"acceptable"` / `"needs_review"`
- `hipaa_requirements_addressed` — list of 8 HIPAA citations covered by the pipeline

---

## 9. Expected Results Reference

### Service URLs

| Layer | Port | Swagger UI | Health Check |
|-------|------|-----------|--------------|
| L1 Identity | 8001 | http://localhost:8001/docs | http://localhost:8001/health |
| L2 Knowledge Graph | 8002 | http://localhost:8002/docs | http://localhost:8002/health |
| L3 Retrieval | 8300 | http://localhost:8300/docs | http://localhost:8300/api/v1/retrieval/health |
| L4 Policy | 8400 | http://localhost:8400/docs | http://localhost:8400/health |
| L5 SQL Generation | 8500 | http://localhost:8500/docs | http://localhost:8500/health |
| L6 Validation | 8600 | http://localhost:8600/docs | http://localhost:8600/health |
| L7 Execution | 8700 | http://localhost:8700/docs | http://localhost:8700/api/v1/execute/health |
| L8 Audit | 8800 | http://localhost:8800/docs | http://localhost:8800/health |
| Frontend | 3000 | — | http://localhost:3000 |

---

### Test Users — Quick Reference

| User | OID | Role | Clearance | Domain | Key Access |
|------|-----|------|-----------|--------|------------|
| Dr. Rajesh Patel | `oid-dr-patel-4521` | ATTENDING_PHYSICIAN | **4** | Clinical | Full clinical patient data |
| Anita Kumar | `oid-nurse-kumar-2847` | REGISTERED_NURSE | **2** | Clinical | Ward patient list, vitals |
| Maria Fernandes | `oid-bill-maria-5521` | BILLING_CLERK | **2** | Financial | Claims, invoices, revenue |
| Vikram Joshi | `oid-it-admin-7801` | IT_ADMINISTRATOR | **2** | IT Ops | System/audit logs |
| Priya Mehta | `oid-hr-priya-7701` | HR_MANAGER | **3** | Administrative | Employee HR records |

---

### Access Control Matrix

| Data Type | Physician (4) | Nurse (2) | Billing (2) | IT Admin (2) | HR Mgr (3) |
|-----------|:---:|:---:|:---:|:---:|:---:|
| Patient admissions | ✓ Full | ✓ Unit-only | ✗ | ✗ | ✗ |
| Lab results | ✓ Full | ✓ Limited | ✗ | ✗ | ✗ |
| Diagnoses | ✓ Full | ✓ Ward-level | ✗ | ✗ | ✗ |
| Psychiatric notes | ✓ (clearance 4) | ✗ | ✗ | ✗ | ✗ |
| Claims / invoices | ✗ | ✗ | ✓ Full | ✗ | ✗ |
| Revenue reports | ✗ | ✗ | ✓ Full | ✗ | ✗ |
| Employee records | ✗ | ✗ | ✗ | ✗ | ✓ Full |
| System audit logs | ✗ | ✗ | ✗ | ✓ Full | ✗ |
| Phone / PII (patients) | Partial mask | Full mask | N/A | N/A | N/A |

---

### SQL Patterns Blocked by L6

| Pattern | Violation Code | Severity |
|---------|---------------|----------|
| `DROP TABLE ...` | `DDL_FORBIDDEN` | CRITICAL |
| `TRUNCATE TABLE ...` | `DDL_FORBIDDEN` | CRITICAL |
| `DELETE FROM ...` | `DML_FORBIDDEN` | CRITICAL |
| `... UNION SELECT ...` | `UNION_INJECTION` | CRITICAL |
| `EXEC xp_cmdshell ...` | `STORED_PROC_FORBIDDEN` | CRITICAL |
| `SELECT * FROM information_schema...` | `SYSTEM_TABLE_ACCESS` | CRITICAL |
| `SELECT * FROM sys.tables` | `SYSTEM_TABLE_ACCESS` | CRITICAL |

---

### Shared Dev Keys

| Key | Value |
|-----|-------|
| Envelope signing key | `dev-context-signing-key-32-chars-min` |
| Service token secret | `dev-secret-change-in-production-min-32-chars-xx` |

---

## 10. Troubleshooting

### Service Won't Start
```bash
# Check if port is already in use
lsof -i tcp:8001   # replace with relevant port

# Kill process on that port
lsof -ti tcp:8001 | xargs kill -9
```

### L1 Returns 401 / Login Button Does Nothing
```bash
curl -s http://localhost:8001/health | python3 -m json.tool
# Check: "mock_idp_enabled": true
```
If `false`, start L1 with: `L1_MOCK_IDP_ENABLED=true venv/bin/uvicorn app.main:app --port 8001`

### Login Succeeds But Logout Breaks Login Button
Hard refresh the page (`Cmd+Shift+R` on Mac) to reload the JS. This is fixed in v2.0 of the frontend.

### L3 Times Out (> 30s)
L3 calls Azure OpenAI for embeddings. If not configured, embedding calls will fail or time out. Check:
```bash
cat l3-intelligent-retrieval/config/settings.yaml | grep -E "azure|embedding|timeout"
```
Ensure `AZURE_OPENAI_API_KEY` and `AZURE_OPENAI_ENDPOINT` are set in environment.

### All Users Get "Access Denied" / CANNOT_ANSWER
Verify L4 (policy resolution) is running:
```bash
curl -s http://localhost:8400/health
```
L3 calls L4 internally. If L4 is offline, all tables will be denied.

### Frontend Shows "OFFLINE" for a Layer
```bash
./start_all.sh          # restarts all layers
tail -f logs/L3-retrieval.log   # check layer-specific logs
```

### L8 Hash Chain Returns `valid: false`
The audit SQLite database may be corrupted (dev-mode limitation). Reset:
```bash
rm l8-audit-anomaly/audit.db
# Restart L8 — it will recreate the DB and tables
```

### L5 Returns CANNOT_ANSWER Unexpectedly
This occurs when:
- The user's question asks for data not in L3's retrieved schema
- L4 denied all candidate tables for this role
- The question intent was misclassified (e.g., "last 3 months" → classified as TREND, not DATA_LOOKUP)

Try rephrasing: instead of *"over the last few months"*, use *"this week"* or *"today"*.

---

*End of Manual Test Guide*
*Version 2.0 | Generated: 2026-03-07 | Apollo Hospitals Zero Trust NL-to-SQL Pipeline*
