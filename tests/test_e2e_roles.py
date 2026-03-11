"""E2E Role-Based Pipeline Tests — 30 queries per role against live L3/L4 services.

Tests the full retrieval pipeline (L3 → L2 vector search → L4 policy resolution)
with proper SecurityContext signing for each role.

Roles tested:
  - doctor (clinical domain access)
  - nurse (clinical with PII masking)
  - billing_staff (billing domain only)
  - researcher (clinical aggregation-only)
  - pharmacist (prescriptions, allergies, patients)
  - hospital_admin (broad access: clinical, billing, hr, analytics, general)
  - revenue_manager (billing, analytics, general; denied clinical)
"""

import asyncio
import hmac
import hashlib
import time
import json
import sys
from dataclasses import dataclass

import httpx

BASE = "http://localhost"
L3 = f"{BASE}:8300"

SERVICE_TOKEN_SECRET = "dev-secret-change-in-production-min-32-chars-xx"
CONTEXT_SIGNING_KEY = "dev-context-signing-key-32-chars-min"


def make_service_token(service_id="l5-generation", role="pipeline_reader"):
    issued = str(int(time.time()))
    payload = f"{service_id}|{role}|{issued}"
    sig = hmac.new(SERVICE_TOKEN_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}|{sig}"


def make_security_context(user_id, roles, department, clearance=4, facility="APH-HYD-001"):
    session_id = f"test-sess-{int(time.time())}"
    expiry = int(time.time()) + 900
    sorted_roles = ",".join(sorted(roles))
    signable = f"{user_id}|{sorted_roles}|{department}|{session_id}|{expiry}|{clearance}"
    sig = hmac.new(CONTEXT_SIGNING_KEY.encode(), signable.encode(), hashlib.sha256).hexdigest()
    return {
        "user_id": user_id,
        "effective_roles": roles,
        "department": department,
        "clearance_level": clearance,
        "session_id": session_id,
        "context_signature": sig,
        "context_expiry": expiry,
        "facility_id": facility,
    }


# ── Query definitions per role ─────────────────────────────────

DOCTOR_QUERIES = [
    "Show me patient lab results for cardiology",
    "List all encounters for today",
    "What are the vital signs for patients in ICU",
    "Find prescriptions written this week",
    "Show patient demographics for admitted patients",
    "List all lab results with abnormal values",
    "Show me encounters by department",
    "What prescriptions were given for diabetes",
    "Find all patients with blood pressure readings above 140",
    "Show encounter summaries for the last month",
    "List vital signs recorded in the emergency department",
    "What are the most common diagnoses this quarter",
    "Show me patient allergies for surgical patients",
    "Find all prescriptions for controlled substances",
    "List all clinical notes for cardiology patients",
    "Show lab results for CBC tests",
    "Find encounters with readmission within 30 days",
    "What medications are prescribed for hypertension",
    "Show patient details for MRN lookup",
    "List all appointments scheduled for tomorrow",
    "Show vital signs trends for a specific patient",
    "Find all encounters with length of stay over 7 days",
    "What are the prescription patterns by department",
    "Show all patients with allergies to penicillin",
    "List clinical notes from the last 48 hours",
    "Show lab results pending review",
    "Find all encounters by treating physician",
    "What are the most common lab tests ordered",
    "Show patient encounter history",
    "List all active prescriptions for a ward",
]

NURSE_QUERIES = [
    "Show me vital signs for my assigned patients",
    "What medications are due for administration",
    "List patient allergies on this ward",
    "Show encounter details for current shift",
    "What are the latest lab results for ward patients",
    "Find patients needing vital sign checks",
    "Show me the patient list for my unit",
    "List all active prescriptions for this floor",
    "What encounters happened during night shift",
    "Show patient clinical notes for handoff",
    "List all allergies flagged as critical",
    "Find patients with abnormal vital signs",
    "Show encounter timeline for patient",
    "What prescriptions need nurse verification",
    "List lab results received in the last hour",
    "Show clinical notes for patient assessment",
    "Find patients admitted today",
    "What vital signs were recorded this shift",
    "Show me encounters pending discharge",
    "List patients with medication allergies",
    "Find all vital sign alerts for my patients",
    "Show appointments for patient follow-up",
    "What lab orders are pending collection",
    "List patients by unit and bed number",
    "Show clinical notes requiring co-signature",
    "Find encounters with nursing assessments due",
    "What prescriptions were modified today",
    "Show patient demographics for admission",
    "List all encounter summaries for handoff report",
    "Show me lab results for blood glucose monitoring",
]

BILLING_QUERIES = [
    "Show all claims submitted this month",
    "List unpaid patient billing records",
    "What insurance plans are most common",
    "Show claim line items for rejected claims",
    "Find payments received this week",
    "List all payer contracts expiring soon",
    "Show patient billing by department",
    "What claims are pending approval",
    "Find insurance plans with high rejection rates",
    "Show payment history for a specific claim",
    "List all claims by insurance provider",
    "What is the total revenue this quarter",
    "Show claim line items for cardiology",
    "Find billing records with outstanding balance",
    "List payer contract terms",
    "Show payments by payment method",
    "What claims were denied in the last month",
    "Find insurance plans covering cardiology",
    "Show billing summary by facility",
    "List all claim adjustments",
    "What is the average payment per claim",
    "Show payer contracts by insurance type",
    "Find claims with coding errors",
    "List patient copay amounts",
    "Show payment reconciliation for the month",
    "What insurance plans have the best coverage",
    "Find billing records for outpatient visits",
    "Show claims submitted to Medicare",
    "List all credit notes issued",
    "Show payment trends over the last year",
]

RESEARCHER_QUERIES = [
    "How many patients were diagnosed with diabetes this year",
    "Show aggregate encounter counts by department",
    "What is the average length of stay by diagnosis",
    "Count lab results by test type",
    "Show population health metrics by region",
    "How many prescriptions were written per month",
    "What are the readmission rates by department",
    "Count patients by age group",
    "Show quality metrics for hospital performance",
    "How many encounters per facility this quarter",
    "What is the distribution of lab test results",
    "Count vital sign recordings by type",
    "Show research cohort demographics",
    "How many patients have multiple allergies",
    "What is the average number of prescriptions per patient",
    "Count encounters by encounter type",
    "Show mortality rates by department",
    "How many clinical notes were created per day",
    "What are the most common allergies",
    "Count patients by insurance type",
    "Show admission trends over the past year",
    "How many lab tests were ordered per encounter",
    "What is the bed occupancy rate by unit",
    "Count prescriptions by drug category",
    "Show encounter summaries aggregated by month",
    "How many patients in each research cohort",
    "What are the quality metric trends",
    "Count appointments by department and status",
    "Show population health statistics",
    "How many unique patients visited last quarter",
]

PHARMACIST_QUERIES = [
    "Show all prescriptions for today",
    "List patient allergies to medications",
    "What prescriptions are pending dispensing",
    "Show patient drug interaction risks",
    "Find prescriptions for controlled substances",
    "List all active medication orders",
    "Show patient allergy history",
    "What medications are prescribed most frequently",
    "Find prescriptions requiring pharmacist review",
    "Show drug allergy alerts for patients",
    "List prescriptions by prescribing physician",
    "What patients have penicillin allergies",
    "Show prescription fill history",
    "Find expired prescriptions",
    "List medication orders by ward",
    "Show patient medication profiles",
    "What prescriptions need dose verification",
    "Find patients with multiple drug allergies",
    "Show prescription trends by department",
    "List all new medication orders today",
    "What are the most common drug allergies",
    "Show prescriptions for specific drug class",
    "Find allergy cross-reactivity risks",
    "List patients on high-alert medications",
    "Show prescription refill requests",
    "What medications require therapeutic monitoring",
    "Find prescription errors flagged for review",
    "Show patient allergy severity levels",
    "List prescriptions ordered STAT",
    "Show drug formulary utilization",
]

REVENUE_MANAGER_QUERIES = [
    "Show total revenue by department this quarter",
    "List all outstanding claims over 90 days",
    "What is the average reimbursement rate by payer",
    "Show payment collection trends for the last 6 months",
    "Find claims with the highest denial rates",
    "List payer contracts expiring in the next 60 days",
    "Show revenue breakdown by insurance provider",
    "What is the accounts receivable aging summary",
    "Find underpaid claims compared to contract rates",
    "Show claim submission to payment turnaround times",
    "List top revenue-generating departments",
    "What is the net collection rate by facility",
    "Show denied claims by denial reason category",
    "Find claims pending secondary insurance billing",
    "List all payment adjustments this month",
    "Show revenue per encounter by department",
    "What payer contracts have the lowest reimbursement",
    "Find billing records with write-off amounts",
    "Show insurance plan coverage comparison",
    "List claims requiring resubmission",
    "What is the charge capture rate by department",
    "Show payment variance from expected amounts",
    "Find payer contracts needing renegotiation",
    "List revenue cycle KPIs for this month",
    "Show claim line items by procedure code",
    "What is the bad debt ratio by facility",
    "Find payments received past the filing deadline",
    "Show revenue forecast based on current claims",
    "List all credit balances requiring refund",
    "Show financial performance dashboard metrics",
]

ADMIN_QUERIES = [
    "Show employee records for all departments",
    "List payroll information for this month",
    "What certifications are expiring soon",
    "Show leave records by department",
    "Find employee credentials needing renewal",
    "List all department staffing levels",
    "Show quality metrics for hospital",
    "What are the encounter summaries this quarter",
    "Find employees with expired certifications",
    "Show payroll totals by department",
    "List all insurance claims summary",
    "What is the bed occupancy rate",
    "Show staff scheduling for next week",
    "Find billing records by facility",
    "List employee leave balances",
    "Show credential verification status",
    "What are the revenue trends by department",
    "Find employees hired this year",
    "Show population health metrics",
    "List facility capacity information",
    "What patient billing is overdue",
    "Show research cohort enrollment numbers",
    "Find departments with staffing shortages",
    "Show payer contract renewals needed",
    "List all units and their capacity",
    "What are the appointment volumes by department",
    "Show clinical note completion rates",
    "Find payroll discrepancies",
    "Show employee certification compliance rates",
    "List all active payer contracts",
]


@dataclass
class QueryResult:
    query: str
    status: int
    success: bool
    tables_returned: int
    error: str
    latency_ms: float


ROLE_CONFIGS = {
    "doctor": {
        "user_id": "dr.sharma",
        "roles": ["doctor"],
        "department": "cardiology",
        "clearance": 4,
        "queries": DOCTOR_QUERIES,
    },
    "nurse": {
        "user_id": "nurse.priya",
        "roles": ["nurse"],
        "department": "cardiology",
        "clearance": 3,
        "queries": NURSE_QUERIES,
    },
    "billing_staff": {
        "user_id": "billing.ravi",
        "roles": ["billing_staff"],
        "department": "finance",
        "clearance": 2,
        "queries": BILLING_QUERIES,
    },
    "researcher": {
        "user_id": "researcher.anand",
        "roles": ["researcher"],
        "department": "research",
        "clearance": 3,
        "queries": RESEARCHER_QUERIES,
    },
    "pharmacist": {
        "user_id": "pharma.deepa",
        "roles": ["pharmacist"],
        "department": "pharmacy",
        "clearance": 3,
        "queries": PHARMACIST_QUERIES,
    },
    "hospital_admin": {
        "user_id": "admin.vijay",
        "roles": ["hospital_admin"],
        "department": "administration",
        "clearance": 5,
        "queries": ADMIN_QUERIES,
    },
    "revenue_manager": {
        "user_id": "rev.meera",
        "roles": ["revenue_manager"],
        "department": "finance",
        "clearance": 3,
        "queries": REVENUE_MANAGER_QUERIES,
    },
}


async def test_query(client, svc_token, ctx, query) -> QueryResult:
    start = time.time()
    try:
        resp = await client.post(
            f"{L3}/api/v1/retrieval/resolve",
            headers={"Authorization": f"Bearer {svc_token}"},
            json={"question": query, "security_context": ctx},
        )
        latency = (time.time() - start) * 1000
        data = resp.json()

        if resp.status_code == 200 and data.get("success"):
            tables = data.get("data", {}).get("filtered_schema", [])
            return QueryResult(query, 200, True, len(tables), "", latency)
        else:
            err = data.get("error", data.get("detail", {}))
            if isinstance(err, dict):
                err = err.get("message", err.get("error_code", str(err)))
            return QueryResult(query, resp.status_code, False, 0, str(err)[:80], latency)
    except Exception as e:
        latency = (time.time() - start) * 1000
        return QueryResult(query, 0, False, 0, str(e)[:80], latency)


async def test_role(client, role_name, config):
    print(f"\n{'=' * 70}")
    print(f"  Role: {role_name} (user={config['user_id']}, dept={config['department']})")
    print(f"{'=' * 70}")

    svc_token = make_service_token()
    ctx = make_security_context(
        config["user_id"], config["roles"], config["department"], config["clearance"]
    )

    results = []
    for i, query in enumerate(config["queries"], 1):
        r = await test_query(client, svc_token, ctx, query)
        results.append(r)

        status_icon = "PASS" if r.success else "DENY" if r.status == 404 else "FAIL"
        tables_info = f"tables={r.tables_returned}" if r.success else r.error[:50]
        print(f"  [{i:2d}/30] {status_icon} ({r.latency_ms:6.0f}ms) {query[:55]}")
        if r.success and r.tables_returned > 0:
            pass  # Clean output
        elif not r.success and r.status in (403, 404):
            pass  # Expected denials
        elif not r.success:
            print(f"         ^ HTTP {r.status}: {r.error[:60]}")

    # Summary
    passed = sum(1 for r in results if r.success)
    denied = sum(1 for r in results if not r.success and r.status in (403, 404))
    failed = sum(1 for r in results if not r.success and r.status not in (403, 404))
    avg_latency = sum(r.latency_ms for r in results) / len(results) if results else 0
    total_tables = sum(r.tables_returned for r in results)

    print(f"\n  Summary for {role_name}:")
    print(f"    Queries: 30 | Passed: {passed} | Denied: {denied} | Failed: {failed}")
    print(f"    Avg latency: {avg_latency:.0f}ms | Total tables returned: {total_tables}")

    return results


async def main():
    # Allow selecting specific roles via command line
    selected_roles = sys.argv[1:] if len(sys.argv) > 1 else list(ROLE_CONFIGS.keys())

    async with httpx.AsyncClient(timeout=120.0) as client:
        print("=" * 70)
        print("E2E Role-Based Pipeline Tests — 30 Queries Per Role")
        print("=" * 70)

        # Quick health check
        try:
            r = await client.get(f"{L3}/api/v1/retrieval/health")
            print(f"\nL3 Health: {'OK' if r.status_code == 200 else 'FAIL'}")
        except Exception as e:
            print(f"\nL3 Health: FAIL ({e})")
            return

        all_results = {}
        for role_name in selected_roles:
            if role_name not in ROLE_CONFIGS:
                print(f"\nUnknown role: {role_name}")
                continue
            results = await test_role(client, role_name, ROLE_CONFIGS[role_name])
            all_results[role_name] = results

        # Final summary
        print(f"\n{'=' * 70}")
        print("OVERALL SUMMARY")
        print(f"{'=' * 70}")
        print(f"{'Role':<20} {'Queries':>8} {'Pass':>6} {'Deny':>6} {'Fail':>6} {'Avg ms':>8} {'Tables':>8}")
        print("-" * 70)

        grand_pass = grand_deny = grand_fail = 0
        for role_name, results in all_results.items():
            passed = sum(1 for r in results if r.success)
            denied = sum(1 for r in results if not r.success and r.status in (403, 404))
            failed = sum(1 for r in results if not r.success and r.status not in (403, 404))
            avg_lat = sum(r.latency_ms for r in results) / len(results)
            total_t = sum(r.tables_returned for r in results)
            grand_pass += passed
            grand_deny += denied
            grand_fail += failed
            print(f"{role_name:<20} {len(results):>8} {passed:>6} {denied:>6} {failed:>6} {avg_lat:>7.0f} {total_t:>8}")

        total = grand_pass + grand_deny + grand_fail
        print("-" * 70)
        print(f"{'TOTAL':<20} {total:>8} {grand_pass:>6} {grand_deny:>6} {grand_fail:>6}")
        print(f"\nPass = tables returned | Deny = 403/404 policy denial | Fail = error")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
