"""
verify_pipeline.py — Terminal verification for the L1 → L2 → L3 pipeline.

Usage:
    # Run against a live L3 (with L2 + L4 also running):
    python scripts/verify_pipeline.py

    # Override the question:
    python scripts/verify_pipeline.py --question "Show ICU patients with sepsis"

    # Override the user:
    python scripts/verify_pipeline.py --user dr-patel-4521 --roles doctor --dept cardiology

    # Point to a different L3 base URL:
    python scripts/verify_pipeline.py --base-url http://localhost:8300

    # Run offline self-test (no live services needed):
    python scripts/verify_pipeline.py --offline
"""

from __future__ import annotations

import argparse
import json
import sys
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Make sure the app package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.auth import create_service_token, sign_security_context
from app.models.security import SecurityContext

# ── Defaults (read from env or fall back to dev secrets) ──────────────────
SECRET       = os.getenv("L3_SERVICE_TOKEN_SECRET",  "dev-secret-change-in-production-min-32-chars-xx")
SIGNING_KEY  = os.getenv("L3_CONTEXT_SIGNING_KEY",   "dev-context-signing-key-32-chars-min")
L3_BASE      = os.getenv("L3_BASE_URL",               "http://localhost:8300")
L2_BASE      = os.getenv("L2_BASE_URL",               "http://localhost:8200")

# ── ANSI colours ─────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg):   print(f"{GREEN}✓ {msg}{RESET}")
def err(msg):  print(f"{RED}✗ {msg}{RESET}")
def info(msg): print(f"{CYAN}  {msg}{RESET}")
def warn(msg): print(f"{YELLOW}⚠ {msg}{RESET}")
def hdr(msg):  print(f"\n{BOLD}{msg}{RESET}")


# ══════════════════════════════════════════════════════════════════════════
# Step 1 — Build a signed SecurityContext (simulating L1 output)
# ══════════════════════════════════════════════════════════════════════════

def build_security_context(
    user_id: str,
    roles: list[str],
    department: str,
    clearance: int,
    facility_id: str = "HOSP_01",
    mfa: bool = True,
) -> SecurityContext:
    """Simulate what L1 Identity & Context produces and signs."""
    expiry = datetime.now(UTC) + timedelta(hours=1)
    ctx_dict = {
        "user_id":         user_id,
        "effective_roles": roles,
        "department":      department,
        "clearance_level": clearance,
        "session_id":      f"sess-verify-{int(datetime.now().timestamp())}",
        "facility_id":     facility_id,
        "mfa_verified":    mfa,
        "context_expiry":  expiry,
        "context_signature": "placeholder",
    }
    sig = sign_security_context(ctx_dict, SIGNING_KEY)
    ctx_dict["context_signature"] = sig
    return SecurityContext(**ctx_dict)


# ══════════════════════════════════════════════════════════════════════════
# Step 2 — Live HTTP checks
# ══════════════════════════════════════════════════════════════════════════

def check_health(base_url: str) -> bool:
    try:
        import httpx
        r = httpx.get(f"{base_url}/health", timeout=3.0)
        if r.status_code == 200:
            data = r.json()
            ok(f"L3 health: {data.get('status', 'ok')} (version {data.get('version', '?')})")
            return True
        err(f"L3 health returned {r.status_code}: {r.text[:200]}")
        return False
    except Exception as e:
        err(f"Cannot reach L3 at {base_url}: {e}")
        return False


def check_l3_dependencies(base_url: str, service_token: str) -> dict:
    """Call /api/v1/retrieval/health and show dependency status."""
    try:
        import httpx
        r = httpx.get(
            f"{base_url}/api/v1/retrieval/health",
            timeout=5.0,
        )
        data = r.json()
        deps = data.get("dependencies", {})
        for name, status in deps.items():
            if status in (True, "ok", "healthy"):
                ok(f"  {name}: up")
            else:
                warn(f"  {name}: {status}")
        return deps
    except Exception as e:
        warn(f"Could not fetch dependency health: {e}")
        return {}


def call_resolve(
    base_url: str,
    service_token: str,
    ctx: SecurityContext,
    question: str,
    max_tables: int = 10,
) -> dict | None:
    try:
        import httpx
        payload = {
            "question":         question,
            "security_context": json.loads(ctx.model_dump_json()),
            "max_tables":       max_tables,
        }
        r = httpx.post(
            f"{base_url}/api/v1/retrieval/resolve",
            json=payload,
            headers={"Authorization": f"Bearer {service_token}"},
            timeout=15.0,
        )
        if r.status_code == 200:
            return r.json().get("data", {})
        err(f"Resolve returned HTTP {r.status_code}")
        try:
            body = r.json()
            err(f"  error: {body.get('error', r.text[:300])}")
        except Exception:
            err(f"  body: {r.text[:300]}")
        return None
    except Exception as e:
        err(f"Request failed: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════
# Step 3 — Offline self-test (no live services)
# ══════════════════════════════════════════════════════════════════════════

def offline_self_test(questions: list[str], user_id: str, roles: list[str], dept: str, clearance: int):
    """Run the full L3 pipeline in-process using mocked L2/L4 clients."""
    from unittest.mock import AsyncMock, MagicMock
    from app.config import Settings
    from app.models.enums import ColumnVisibility, TableDecision
    from app.models.l2_models import L2ColumnInfo, L2ForeignKey, L2TableInfo
    from app.models.l4_models import ColumnDecision, PermissionEnvelope, TablePermission
    from app.models.api import RetrievalRequest
    from app.services.orchestrator import RetrievalOrchestrator, RetrievalError
    from app.services.embedding_engine import EmbeddingEngine
    from app.services.intent_classifier import IntentClassifier
    from app.services.retrieval_pipeline import RetrievalPipeline
    from app.services.ranking_engine import RankingEngine
    from app.services.rbac_filter import RBACFilter
    from app.services.column_scoper import ColumnScoper
    from app.services.join_graph import JoinGraphBuilder
    from app.services.context_assembler import ContextAssembler
    import asyncio

    hdr("OFFLINE MODE — Pipeline runs in-process with mocked L2/L4")
    print("  (No live services required)\n")

    settings = Settings(
        service_token_secret=SECRET,
        context_signing_key=SIGNING_KEY,
    )

    # ── Realistic Apollo Hospitals L2 mock ───────────────────────────────
    TABLES = [
        L2TableInfo(fqn="apollo_his.clinical.patients",    name="patients",     domain="clinical",  sensitivity_level=3, description="Patient demographics"),
        L2TableInfo(fqn="apollo_his.clinical.encounters",  name="encounters",   domain="clinical",  sensitivity_level=2, description="Hospital encounters"),
        L2TableInfo(fqn="apollo_his.clinical.diagnoses",   name="diagnoses",    domain="clinical",  sensitivity_level=3, description="ICD-10 diagnoses"),
        L2TableInfo(fqn="apollo_his.clinical.lab_results", name="lab_results",  domain="clinical",  sensitivity_level=3, description="Lab test results"),
        L2TableInfo(fqn="apollo_his.clinical.vital_signs", name="vital_signs",  domain="clinical",  sensitivity_level=2, description="Vital signs"),
        L2TableInfo(fqn="apollo_his.billing.claims",       name="claims",       domain="billing",   sensitivity_level=3, description="Insurance claims"),
        L2TableInfo(fqn="apollo_his.pharmacy.rx",          name="prescriptions",domain="pharmacy",  sensitivity_level=3, description="Prescriptions"),
        L2TableInfo(fqn="apollo_his.behavioral_health.substance_abuse_records",
                        name="substance_abuse_records", domain="behavioral_health", sensitivity_level=5,
                        description="42 CFR Part 2 substance use records"),
    ]
    ALLOWED = {
        "doctor":       {"apollo_his.clinical.patients","apollo_his.clinical.encounters","apollo_his.clinical.diagnoses","apollo_his.clinical.lab_results","apollo_his.clinical.vital_signs","apollo_his.pharmacy.rx"},
        "nurse":        {"apollo_his.clinical.patients","apollo_his.clinical.encounters","apollo_his.clinical.vital_signs"},
        "billing_staff":{"apollo_his.billing.claims"},
        "pharmacist":   {"apollo_his.pharmacy.rx"},
    }
    allowed_set = set()
    for role in roles:
        allowed_set |= ALLOWED.get(role, set())

    COLS = {
        "apollo_his.clinical.patients": [
            L2ColumnInfo(fqn="...patient_id", name="patient_id", data_type="integer", is_pii=False, sensitivity_level=1),
            L2ColumnInfo(fqn="...name",       name="name",       data_type="varchar(100)", is_pii=True, sensitivity_level=3),
            L2ColumnInfo(fqn="...mrn",        name="mrn",        data_type="varchar(20)",  is_pii=True, sensitivity_level=3),
            L2ColumnInfo(fqn="...dob",        name="dob",        data_type="date",         is_pii=True, sensitivity_level=3),
            L2ColumnInfo(fqn="...ssn",        name="ssn",        data_type="varchar(11)",  is_pii=True, sensitivity_level=5),
            L2ColumnInfo(fqn="...facility_id",name="facility_id",data_type="varchar(20)",  is_pii=False,sensitivity_level=1),
        ],
        "apollo_his.clinical.encounters": [
            L2ColumnInfo(fqn="...encounter_id",   name="encounter_id",   data_type="integer",     is_pii=False, sensitivity_level=1),
            L2ColumnInfo(fqn="...patient_id",     name="patient_id",     data_type="integer",     is_pii=False, sensitivity_level=1),
            L2ColumnInfo(fqn="...admit_date",     name="admit_date",     data_type="date",        is_pii=False, sensitivity_level=1),
            L2ColumnInfo(fqn="...discharge_date", name="discharge_date", data_type="date",        is_pii=False, sensitivity_level=1),
            L2ColumnInfo(fqn="...encounter_type", name="encounter_type", data_type="varchar(50)", is_pii=False, sensitivity_level=1),
            L2ColumnInfo(fqn="...facility_id",    name="facility_id",    data_type="varchar(20)", is_pii=False, sensitivity_level=1),
        ],
    }

    FK_MAP = {
        "apollo_his.clinical.encounters": [
            L2ForeignKey(source_column="patient_id", target_table="patients",
                         target_column="patient_id", target_table_fqn="apollo_his.clinical.patients"),
        ],
        "apollo_his.clinical.diagnoses": [
            L2ForeignKey(source_column="patient_id",   target_table="patients",
                         target_column="patient_id",   target_table_fqn="apollo_his.clinical.patients"),
            L2ForeignKey(source_column="encounter_id", target_table="encounters",
                         target_column="encounter_id", target_table_fqn="apollo_his.clinical.encounters"),
        ],
    }

    def _l4_resolve(candidate_table_ids=None, **_kw) -> PermissionEnvelope:
        perms = []
        for tid in (candidate_table_ids or []):
            if tid in allowed_set:
                cols_data = COLS.get(tid, [])
                col_decisions = []
                for c in cols_data:
                    if c.sensitivity_level >= 5:   vis = ColumnVisibility.HIDDEN
                    elif c.is_pii:                 vis = ColumnVisibility.MASKED
                    else:                          vis = ColumnVisibility.VISIBLE
                    col_decisions.append(ColumnDecision(column_name=c.name, visibility=vis,
                        masking_expression=f"MASKED({c.name})" if vis == ColumnVisibility.MASKED else None))
                perms.append(TablePermission(table_id=tid, decision=TableDecision.ALLOW,
                    columns=col_decisions, row_filters=["facility_id = 'HOSP_01'"]))
            else:
                perms.append(TablePermission(table_id=tid, decision=TableDecision.DENY,
                    reason="No permission entry"))
        return PermissionEnvelope(
            table_permissions=perms,
            global_nl_rules=["Only return data for the user's assigned facility (HOSP_01)"],
        )

    mock_l2 = AsyncMock()
    mock_l2.search_tables = AsyncMock(side_effect=lambda q, **_: [
        t for t in TABLES if any(w in t.name.lower() or w in t.description.lower() for w in q.lower().split())
    ] or TABLES[:3])
    mock_l2.get_tables_by_domain = AsyncMock(side_effect=lambda d, **_: [t for t in TABLES if t.domain == d])
    mock_l2.get_table_columns = AsyncMock(side_effect=lambda fqn, **_: COLS.get(fqn, []))
    mock_l2.get_foreign_keys = AsyncMock(side_effect=lambda fqn, **_: FK_MAP.get(fqn, []))
    mock_l2.get_role_domain_access = AsyncMock(return_value={r: ["clinical","pharmacy"] for r in roles})
    mock_l2.health_check = AsyncMock(return_value=True)

    mock_l4 = AsyncMock()
    mock_l4.resolve_policies = AsyncMock(side_effect=_l4_resolve)
    mock_l4.health_check = AsyncMock(return_value=True)

    mock_embed = AsyncMock()
    mock_embed.embed = AsyncMock(return_value=[0.1] * 1536)
    mock_embed.health_check = AsyncMock(return_value=True)

    mock_vector = AsyncMock()
    mock_vector.search_similar = AsyncMock(return_value=[])
    mock_vector.health_check = AsyncMock(return_value=True)

    mock_cache = AsyncMock()
    mock_cache.get_embedding = AsyncMock(return_value=None)
    mock_cache.set_embedding = AsyncMock()
    mock_cache.get_role_domains = AsyncMock(return_value=None)
    mock_cache.set_role_domains = AsyncMock()
    mock_cache.get_vector_results = AsyncMock(return_value=None)
    mock_cache.set_vector_results = AsyncMock()
    mock_cache.get_schema_fragment = AsyncMock(return_value=None)
    mock_cache.set_schema_fragment = AsyncMock()
    mock_cache.get_columns_local = MagicMock(return_value=None)
    mock_cache.set_columns_local = MagicMock()
    mock_cache.get_fk_local = MagicMock(return_value=None)
    mock_cache.set_fk_local = MagicMock()
    mock_cache.stats = {"hits": 0, "misses": 0}

    orchestrator = RetrievalOrchestrator(
        settings=settings,
        embedding_engine=EmbeddingEngine(settings, mock_embed, mock_cache),
        intent_classifier=IntentClassifier(),
        retrieval_pipeline=RetrievalPipeline(settings, mock_l2, mock_vector, mock_cache),
        ranking_engine=RankingEngine(),
        rbac_filter=RBACFilter(mock_l2, mock_l4, mock_cache),
        column_scoper=ColumnScoper(mock_l2, mock_cache),
        join_graph_builder=JoinGraphBuilder(mock_l2, mock_cache),
        context_assembler=ContextAssembler(),
    )

    ctx = build_security_context(user_id, roles, dept, clearance)

    async def _run():
        for q in questions:
            print(f"\n{'─'*60}")
            print(f"  Question : {BOLD}{q}{RESET}")
            print(f"  User     : {user_id}  roles={roles}  dept={dept}  clearance={clearance}")
            try:
                req = RetrievalRequest(question=q, security_context=ctx)
                result = await orchestrator.resolve(req)
                _print_result(result)
            except RetrievalError as e:
                err(f"Pipeline error [{e.code.value}] HTTP {e.status}: {e.message}")

    asyncio.run(_run())


# ══════════════════════════════════════════════════════════════════════════
# Result printer
# ══════════════════════════════════════════════════════════════════════════

def _print_result(result):
    intent = result.intent
    ok(f"Intent   : {intent.intent.value}  (confidence {intent.confidence:.2f})")
    if intent.domain_hints:
        info(f"Domains  : {[d.value for d in intent.domain_hints]}")
    if intent.matched_keywords:
        info(f"Keywords : {intent.matched_keywords[:5]}")

    tables = result.filtered_schema
    ok(f"Tables   : {len(tables)} returned  |  {result.denied_tables_count} denied by RBAC/L4")
    for t in tables:
        vis_cols  = [c.name for c in t.visible_columns]
        mask_cols = [c.name for c in t.masked_columns]
        hid_cnt   = t.hidden_column_count
        print(f"\n  {BOLD}{t.table_name}{RESET}  ({t.table_id})")
        print(f"    Score   : {t.relevance_score:.3f}")
        print(f"    Visible : {vis_cols}")
        if mask_cols:
            print(f"    Masked  : {YELLOW}{mask_cols}{RESET}")
        if hid_cnt:
            print(f"    Hidden  : {RED}{hid_cnt} column(s) redacted{RESET}")
        if t.row_filters:
            print(f"    Filters : {t.row_filters}")
        if t.aggregation_only:
            print(f"    {YELLOW}⚠ AGGREGATION ONLY — no row-level access{RESET}")

    if result.join_graph.edges:
        ok(f"Join edges : {len(result.join_graph.edges)}")
        for e in result.join_graph.edges[:3]:
            info(f"  {e.source_table} → {e.target_table}  via {e.source_column}")

    if result.nl_policy_rules:
        ok(f"NL rules  : {result.nl_policy_rules[0][:80]}")

    meta = result.retrieval_metadata
    info(f"Perf     : {meta.total_latency_ms:.1f} ms total  |  {meta.token_count} tokens  |  candidates={meta.total_candidates_found}")
    if meta.embedding_cache_hit:
        info("Embedding cache: HIT")


# ══════════════════════════════════════════════════════════════════════════
# Live mode
# ══════════════════════════════════════════════════════════════════════════

def live_test(base_url: str, questions: list[str], user_id: str, roles: list[str], dept: str, clearance: int):
    hdr(f"LIVE MODE — calling L3 at {base_url}")

    if not check_health(base_url):
        print(f"\n{RED}Cannot reach L3. Start it first:{RESET}")
        print(f"  cd l3-intelligent-retrieval")
        print(f"  source .venv/bin/activate")
        print(f"  uvicorn app.main:app --port 8300 --reload")
        sys.exit(1)

    hdr("Dependency health")
    service_token = create_service_token("l5-generation", "pipeline_reader", SECRET)
    check_l3_dependencies(base_url, service_token)

    ctx = build_security_context(user_id, roles, dept, clearance)
    hdr("SecurityContext (from L1 simulator)")
    info(f"user_id          : {ctx.user_id}")
    info(f"effective_roles  : {ctx.effective_roles}")
    info(f"department       : {ctx.department}")
    info(f"clearance_level  : {ctx.clearance_level}")
    info(f"session_id       : {ctx.session_id}")
    info(f"context_expiry   : {ctx.context_expiry.isoformat()}")
    info(f"context_signature: {ctx.context_signature[:16]}…")

    for q in questions:
        hdr(f"POST /api/v1/retrieval/resolve")
        print(f"  Question : {BOLD}{q}{RESET}")
        data = call_resolve(base_url, service_token, ctx, q)
        if data:
            _print_result_live(data)


def _print_result_live(data: dict):
    intent = data.get("intent", {})
    ok(f"Intent   : {intent.get('intent')}  (confidence {intent.get('confidence', 0):.2f})")
    domains = intent.get("domain_hints", [])
    if domains:
        info(f"Domains  : {domains}")

    tables = data.get("filtered_schema", [])
    denied = data.get("denied_tables_count", 0)
    ok(f"Tables   : {len(tables)} returned  |  {denied} denied by RBAC/L4")
    for t in tables:
        print(f"\n  {BOLD}{t.get('table_name')}{RESET}  ({t.get('table_id')})")
        print(f"    Score   : {t.get('relevance_score', 0):.3f}")
        vis  = [c["name"] for c in t.get("visible_columns", [])]
        mask = [c["name"] for c in t.get("masked_columns", [])]
        hid  = t.get("hidden_column_count", 0)
        print(f"    Visible : {vis}")
        if mask:
            print(f"    Masked  : {YELLOW}{mask}{RESET}")
        if hid:
            print(f"    Hidden  : {RED}{hid} column(s) redacted{RESET}")
        filters = t.get("row_filters", [])
        if filters:
            print(f"    Filters : {filters}")
        if t.get("aggregation_only"):
            print(f"    {YELLOW}⚠ AGGREGATION ONLY{RESET}")

    jg = data.get("join_graph", {})
    edges = jg.get("edges", []) if jg else []
    if edges:
        ok(f"Join edges : {len(edges)}")
        for e in edges[:3]:
            info(f"  {e.get('source_table')} → {e.get('target_table')}  via {e.get('source_column')}")

    rules = data.get("nl_policy_rules", [])
    if rules:
        ok(f"NL rules  : {rules[0][:80]}")

    meta = data.get("retrieval_metadata", {})
    info(f"Perf     : {meta.get('total_latency_ms', 0):.1f} ms  |  {meta.get('token_count', 0)} tokens  |  candidates={meta.get('total_candidates_found', 0)}")


# ══════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Verify the L1→L2→L3 pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--offline",   action="store_true", help="Run in-process without any live services")
    parser.add_argument("--base-url",  default=L3_BASE,     help=f"L3 base URL (default: {L3_BASE})")
    parser.add_argument("--question",  default=None,        help="Custom question to test")
    parser.add_argument("--user",      default="dr-patel-4521")
    parser.add_argument("--roles",     default="doctor",    help="Comma-separated roles")
    parser.add_argument("--dept",      default="cardiology")
    parser.add_argument("--clearance", default=3, type=int)
    args = parser.parse_args()

    roles = [r.strip() for r in args.roles.split(",") if r.strip()]

    default_questions = [
        "Show all patients currently diagnosed with diabetes",
        "How many patients were admitted this week?",
        "Join patients with their lab results for ICU admissions",
    ]
    questions = [args.question] if args.question else default_questions

    print(f"\n{BOLD}{'═'*60}")
    print(f"  L1 → L2 → L3 Pipeline Verification")
    print(f"{'═'*60}{RESET}")
    print(f"  User      : {args.user}")
    print(f"  Roles     : {roles}")
    print(f"  Dept      : {args.dept}")
    print(f"  Clearance : {args.clearance}")
    print(f"  Questions : {len(questions)}")

    if args.offline:
        offline_self_test(questions, args.user, roles, args.dept, args.clearance)
    else:
        live_test(args.base_url, questions, args.user, roles, args.dept, args.clearance)

    print(f"\n{BOLD}{'═'*60}{RESET}\n")


if __name__ == "__main__":
    main()
