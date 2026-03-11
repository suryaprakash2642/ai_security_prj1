#!/usr/bin/env python3
"""
Role-based query test suite for Apollo Hospitals Zero Trust Pipeline.
Tests L1 → L3 (with L2 + L4) for 5 users across their domains.
"""

import hmac, hashlib, time, requests, sys

# ── Config ────────────────────────────────────────────────────────────────────
L1  = "http://localhost:8001"
L3  = "http://localhost:8300"
L3_SECRET = "dev-secret-change-in-production-min-32-chars-xx"

USERS = {
    "dr_patel": {
        "oid": "oid-dr-patel-4521", "name": "Dr. Rajesh Patel",
        "email": "rajesh.patel@apollohospitals.com",
        "roles": ["ATTENDING_PHYSICIAN"], "groups": ["physicians-cardiology"],
        "expected_clearance": 4,
    },
    "anita_kumar": {
        "oid": "oid-nurse-kumar-2847", "name": "Anita Kumar",
        "email": "anita.kumar@apollohospitals.com",
        "roles": ["REGISTERED_NURSE"], "groups": ["nursing-cardiology"],
        "expected_clearance": 2,
    },
    "maria_fernandes": {
        "oid": "oid-bill-maria-5521", "name": "Maria Fernandes",
        "email": "maria.fernandes@apollohospitals.com",
        "roles": ["billing_staff"], "groups": ["billing-team"],
        "expected_clearance": 2,
    },
    "vikram_joshi": {
        "oid": "oid-it-admin-7801", "name": "Vikram Joshi",
        "email": "vikram.joshi@apollohospitals.com",
        "roles": ["admin"], "groups": ["it-team"],
        "expected_clearance": 2,
    },
    "priya_mehta": {
        "oid": "oid-hr-priya-7701", "name": "Priya Mehta",
        "email": "priya.mehta@apollohospitals.com",
        "roles": ["hr_staff"], "groups": ["hr-team"],
        "expected_clearance": 3,
    },
}

# ── Test Cases ─────────────────────────────────────────────────────────────────
# Format: (description, natural_language_query, checks)
# checks: list of (check_type, value)
#   "has_table"       → table name appears in filtered_schema
#   "no_table"        → table NOT in filtered_schema
#   "table_has_hidden"→ specific table has hidden_column_count >= 1
#   "denied"          → expect 403/404 (no tables returned)
#   "not_denied"      → expect at least 1 table returned

TEST_CASES = {
    # ── ATTENDING PHYSICIAN ──────────────────────────────────────────────────
    "dr_patel": [
        (
            "Patient diagnoses in cardiology",
            "Show me all diagnoses for cardiology patients this week",
            [("has_table", "diagnoses"), ("not_denied", None)]
        ),
        (
            "Lab results for a patient",
            "Get lab results for patient P001 including all test values",
            [("has_table", "lab_results"), ("not_denied", None)]
        ),
        (
            "Prescriptions by physician",
            "List all prescriptions I ordered last month",
            [("has_table", "prescriptions"), ("not_denied", None)]
        ),
        (
            "Patient admissions",
            "Show active admissions in cardiology ward",
            [("has_table", "admissions"), ("not_denied", None)]
        ),
        (
            "HIV status must be hidden (PHI)",
            "Get lab results including HIV test status for all patients",
            [("has_table", "lab_results"), ("table_has_hidden", "lab_results")]
        ),
        (
            "CROSS-DOMAIN: Billing data must be denied",
            "Show insurance claims and billing for cardiology patients",
            [("no_table", "claims")]
        ),
        (
            "CROSS-DOMAIN: HR data must be denied",
            "List staff attendance records for cardiology department",
            [("no_table", "attendance")]
        ),
    ],

    # ── REGISTERED NURSE ─────────────────────────────────────────────────────
    "anita_kumar": [
        (
            "Nursing assessments",
            "Show nursing assessments for patients in ward B this morning",
            [("has_table", "nursing_assessments"), ("not_denied", None)]
        ),
        (
            "Patient vitals",
            "Get vital signs recorded in last 6 hours for cardiology patients",
            [("has_table", "vital_signs"), ("not_denied", None)]
        ),
        (
            "Medication and prescriptions",
            "Show prescriptions and medication orders for today",
            [("has_table", "prescriptions"), ("not_denied", None)]
        ),
        (
            "HIV status must be hidden (PHI)",
            "Show patient lab results including hiv status",
            [("has_table", "lab_results"), ("table_has_hidden", "lab_results")]
        ),
        (
            "CROSS-DOMAIN: Cannot access billing claims",
            "Show billing claims for nurse shifts",
            [("no_table", "claims"), ("no_table", "revenue_analytics")]
        ),
        (
            "CROSS-DOMAIN: Cannot access HR attendance",
            "Get attendance records for nursing staff",
            [("no_table", "attendance")]
        ),
    ],

    # ── BILLING STAFF ─────────────────────────────────────────────────────────
    "maria_fernandes": [
        (
            "Insurance claims lookup",
            "Show all pending insurance claims submitted this month",
            [("has_table", "claims"), ("not_denied", None)]
        ),
        (
            "Revenue analytics",
            "Get revenue breakdown by department for Q1",
            [("has_table", "revenue_analytics"), ("not_denied", None)]
        ),
        (
            "Accounts receivable",
            "List outstanding accounts receivable older than 30 days",
            [("has_table", "accounts_receivable"), ("not_denied", None)]
        ),
        (
            "CROSS-DOMAIN: Cannot view patient diagnoses",
            "Show patient diagnoses to verify billing codes",
            [("no_table", "diagnoses"), ("no_table", "admissions")]
        ),
        (
            "CROSS-DOMAIN: Cannot view lab results",
            "Get lab results for billing audit",
            [("no_table", "lab_results")]
        ),
        (
            "CROSS-DOMAIN: Cannot access HR data",
            "Show employee salary for payroll billing",
            [("no_table", "benefits"), ("no_table", "attendance")]
        ),
    ],

    # ── IT ADMINISTRATOR ─────────────────────────────────────────────────────
    "vikram_joshi": [
        (
            "Department KPIs",
            "Show department performance KPIs for Q1 this year",
            [("has_table", "department_kpis"), ("not_denied", None)]
        ),
        (
            "Cost centers",
            "List all cost centers and their allocated budgets",
            [("has_table", "cost_centers"), ("not_denied", None)]
        ),
        (
            "Vendor master",
            "Get active vendor contracts expiring this quarter",
            [("has_table", "vendor_master"), ("not_denied", None)]
        ),
        (
            "HARD DENY: Cannot access patient records",
            "Show patient records for system audit",
            [("no_table", "admissions"), ("no_table", "diagnoses"),
             ("no_table", "lab_results"), ("no_table", "prescriptions")]
        ),
        (
            "HARD DENY: Cannot access nursing data",
            "Get nursing assessment data for system testing",
            [("no_table", "nursing_assessments"), ("no_table", "vitals")]
        ),
        (
            "CROSS-DOMAIN: Cannot access billing claims",
            "Show billing claims for IT audit",
            [("no_table", "claims")]
        ),
        (
            "CROSS-DOMAIN: Cannot access HR records",
            "List all employee attendance records",
            [("no_table", "attendance"), ("no_table", "leave_records")]
        ),
    ],

    # ── HR MANAGER ───────────────────────────────────────────────────────────
    "priya_mehta": [
        (
            "Employee attendance",
            "Show attendance report for all employees last month",
            [("has_table", "attendance"), ("not_denied", None)]
        ),
        (
            "Leave records",
            "Get leave applications pending approval",
            [("has_table", "leave_records"), ("not_denied", None)]
        ),
        (
            "Employee benefits",
            "List employee benefits enrollment for Q1",
            [("has_table", "benefits"), ("not_denied", None)]
        ),
        (
            "Department structure",
            "Show department hierarchy and headcount",
            [("has_table", "departments"), ("not_denied", None)]
        ),
        (
            "Training records",
            "Get training completion status for mandatory programs",
            [("has_table", "training_records"), ("not_denied", None)]
        ),
        (
            "CROSS-DOMAIN: Cannot access patient data",
            "Show patient records for HR wellness program",
            [("no_table", "admissions"), ("no_table", "diagnoses")]
        ),
        (
            "CROSS-DOMAIN: Cannot access billing data",
            "Get billing claims for HR cost analysis",
            [("no_table", "claims"), ("no_table", "revenue_analytics")]
        ),
    ],
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_token_and_context(user_key: str):
    """Get L1 JWT + resolve SecurityContext via /identity/resolve + /identity/verify."""
    u = USERS[user_key]
    # Step 1: Get mock JWT
    r = requests.post(
        f"{L1}/mock/token",
        params={"oid": u["oid"], "name": u["name"], "email": u["email"], "include_mfa": "true"},
        json={"roles": u["roles"], "groups": u["groups"]},
        timeout=5
    )
    r.raise_for_status()
    jwt_token = r.json()["token"]

    # Step 2: Resolve SecurityContext → get context_token_id + signature
    r2 = requests.post(
        f"{L1}/identity/resolve",
        headers={"Authorization": f"Bearer {jwt_token}"},
        timeout=5
    )
    r2.raise_for_status()
    resolve = r2.json()
    ctx_id = resolve["context_token_id"]

    # Step 3: Verify → get session_id, department, expiry
    r3 = requests.get(
        f"{L1}/identity/verify/{ctx_id}",
        headers={"Authorization": f"Bearer {jwt_token}"},
        timeout=5
    )
    r3.raise_for_status()
    full = r3.json()

    from datetime import datetime, timezone
    session_id  = full["request_metadata"]["session_id"]
    department  = full["org_context"]["department"]
    facility_id = full["org_context"]["facility_ids"][0] if full["org_context"].get("facility_ids") else "FAC-001"
    clearance   = full["authorization"]["clearance_level"]
    eff_roles   = full["authorization"]["effective_roles"]
    user_id     = full["identity"]["oid"]
    expires_at  = full["expires_at"]
    expiry_ts   = int(datetime.fromisoformat(expires_at.replace("Z", "+00:00")).timestamp())

    sc = {
        "user_id":           user_id,
        "effective_roles":   eff_roles,
        "department":        department,
        "clearance_level":   clearance,
        "session_id":        session_id,
        "context_signature": resolve["context_signature"],  # L1-signed, use directly
        "facility_id":       facility_id,
    }
    return jwt_token, sc, session_id, expiry_ts


def make_service_token():
    service_id = "test-service"
    role = "pipeline_reader"
    issued = str(int(time.time()))
    payload = f"{service_id}|{role}|{issued}"
    sig = hmac.new(L3_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}|{sig}"



def query_l3(user_key: str, nl_query: str):
    """Run a NL query through L3 for a given user."""
    sc, session_id, expiry_ts = None, None, None
    try:
        jwt_token, sc, session_id, expiry_ts = get_token_and_context(user_key)
    except Exception as e:
        return {"error": f"L1 auth failed: {e}"}

    payload = {
        "question": nl_query,
        "security_context": {
            "user_id":           sc["user_id"],
            "effective_roles":   sc["effective_roles"],
            "department":        sc["department"],
            "clearance_level":   sc["clearance_level"],
            "session_id":        session_id,
            "context_signature": sc["context_signature"],  # L1-signed
            "context_expiry":    expiry_ts,
            "facility_id":       sc.get("facility_id", "FAC-001"),
        },
        "request_id": f"test-{user_key}-{int(time.time())}"
    }

    svc_token = make_service_token()
    try:
        r = requests.post(
            f"{L3}/api/v1/retrieval/resolve",
            json=payload,
            headers={"Authorization": f"Bearer {svc_token}"},
            timeout=90
        )
        result = r.json()
        result["_http_status"] = r.status_code
        return result
    except Exception as e:
        return {"error": str(e), "_http_status": 500}


def extract_tables(response: dict) -> list[str]:
    """Extract table names from L3 response."""
    if "error" in response and "_http_status" not in response:
        return []
    inner = response.get("data", response)
    if isinstance(inner, dict):
        inner = inner.get("data", inner)
    schema = inner.get("filtered_schema", [])
    if isinstance(schema, list):
        return [t.get("table_name", "") for t in schema]
    if isinstance(schema, dict):
        return [t.get("table_name", "") for t in schema.get("tables", [])]
    return []


def extract_schema(response: dict) -> list[dict]:
    """Extract filtered_schema list from L3 response."""
    inner = response.get("data", response)
    if isinstance(inner, dict):
        inner = inner.get("data", inner)
    schema = inner.get("filtered_schema", [])
    return schema if isinstance(schema, list) else []


def table_hidden_count(response: dict, table_name: str) -> int:
    """Return hidden_column_count for a specific table in the L3 response."""
    for t in extract_schema(response):
        if table_name in t.get("table_name", ""):
            return t.get("hidden_column_count", 0) or 0
    return 0


# ── Runner ────────────────────────────────────────────────────────────────────

def run_tests():
    total = passed = failed = 0
    failures = []

    print("\n" + "═" * 72)
    print("  APOLLO HOSPITALS — ROLE-BASED QUERY ACCESS TEST SUITE")
    print("═" * 72)

    for user_key, cases in TEST_CASES.items():
        u = USERS[user_key]
        print(f"\n{'─'*72}")
        print(f"  USER: {u['name']}  |  Role: {u['roles'][0]}  |  Clearance: {u['expected_clearance']}")
        print(f"{'─'*72}")

        for desc, query, checks in cases:
            total += 1
            response = query_l3(user_key, query)
            tables   = extract_tables(response)
            http_st  = response.get("_http_status", 0)
            has_err  = response.get("error_code") in ("NO_RELEVANT_TABLES", "RESTRICTED_DATA_REQUEST")

            check_results = []
            test_pass = True

            for check_type, check_val in checks:
                if check_type == "has_table":
                    ok = any(check_val in t for t in tables)
                    check_results.append(("has_table", check_val, ok,
                                         f"wanted '{check_val}' in {tables}"))
                elif check_type == "no_table":
                    ok = not any(check_val in t for t in tables)
                    check_results.append(("no_table", check_val, ok,
                                         f"'{check_val}' should NOT appear in {tables}"))
                elif check_type == "table_has_hidden":
                    cnt = table_hidden_count(response, check_val)
                    ok = cnt >= 1
                    check_results.append(("table_has_hidden", check_val, ok,
                                         f"'{check_val}' hidden_column_count={cnt} (expected ≥1)"))
                elif check_type == "denied":
                    ok = has_err or http_st in (403, 404) or not tables
                    check_results.append(("denied", None, ok,
                                         f"expected denial, got http={http_st} tables={tables}"))
                elif check_type == "not_denied":
                    ok = bool(tables) and not has_err
                    check_results.append(("not_denied", None, ok,
                                         f"expected tables but got http={http_st} err={response.get('error_code')} tables={tables}"))

            if all(r[2] for r in check_results):
                passed += 1
                status = "✅ PASS"
                detail = f"tables=[{', '.join(tables)}]"
            else:
                failed += 1
                test_pass = False
                status = "❌ FAIL"
                failures.append((u["name"], desc, check_results, tables, hidden))
                detail = ""

            print(f"  {status}  {desc}")
            if not test_pass:
                for ct, cv, ok, msg in check_results:
                    if not ok:
                        print(f"         ⚠  [{ct}] {msg}")
            else:
                print(f"         ↳  {detail}")

    print(f"\n{'═'*72}")
    print(f"  RESULTS: {passed}/{total} passed  |  {failed} failed")
    print(f"{'═'*72}\n")

    if failures:
        print("FAILED TESTS SUMMARY:")
        for name, desc, checks, tables, hidden in failures:
            print(f"\n  [{name}] {desc}")
            for ct, cv, ok, msg in checks:
                if not ok:
                    print(f"    ✗ {msg}")

    return passed, total


if __name__ == "__main__":
    passed, total = run_tests()
    sys.exit(0 if passed == total else 1)
