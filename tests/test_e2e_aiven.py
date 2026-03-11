"""End-to-end test: verify Aiven database integration across the pipeline."""

import asyncio
import httpx
import time
import hmac
import hashlib
import json


BASE = "http://localhost"
L1 = f"{BASE}:8001"
L2 = f"{BASE}:8002"
L3 = f"{BASE}:8300"
L4 = f"{BASE}:8400"
L5 = f"{BASE}:8500"
L6 = f"{BASE}:8600"
L7 = f"{BASE}:8700"
L8 = f"{BASE}:8800"

SERVICE_TOKEN_SECRET = "dev-secret-change-in-production-min-32-chars-xx"
CONTEXT_SIGNING_KEY = "dev-context-signing-key-32-chars-min"


def make_service_token(service_id="l5-generation", role="pipeline_reader"):
    """Generate an L3-compatible service token."""
    issued = str(int(time.time()))
    payload = f"{service_id}|{role}|{issued}"
    sig = hmac.new(SERVICE_TOKEN_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}|{sig}"


def make_context_signature(user_id, roles, department, session_id, expiry, clearance):
    """Sign a security context like L1 does."""
    sorted_roles = ",".join(sorted(roles))
    signable = f"{user_id}|{sorted_roles}|{department}|{session_id}|{expiry}|{clearance}"
    return hmac.new(CONTEXT_SIGNING_KEY.encode(), signable.encode(), hashlib.sha256).hexdigest()


async def main():
    async with httpx.AsyncClient(timeout=120.0) as client:
        print("=" * 60)
        print("E2E Test: Aiven Database Integration")
        print("=" * 60)

        # ── Step 1: Health checks ────────────────────────────────
        print("\n[1/6] Health checks...")
        services = {
            "L1": f"{L1}/health",
            "L2": f"{L2}/health",
            "L3": f"{L3}/api/v1/retrieval/health",
            "L4": f"{L4}/health",
            "L5": f"{L5}/health",
            "L6": f"{L6}/health",
            "L7": f"{L7}/health",
            "L8": f"{L8}/health",
        }
        for name, url in services.items():
            try:
                r = await client.get(url)
                status = "OK" if r.status_code == 200 else f"HTTP {r.status_code}"
                print(f"  ✓ {name}: {status}")
            except Exception as e:
                print(f"  ✗ {name}: {e}")

        # ── Step 2: L1 — Get mock token and resolve identity ─────
        print("\n[2/6] L1 — Authentication...")
        token_resp = await client.post(f"{L1}/mock/token", json={
            "user_id": "dr.sharma",
            "roles": ["doctor", "clinical_staff"],
            "department": "cardiology",
            "facility_id": "APH-HYD-001"
        })
        token_data = token_resp.json()
        jwt_token = token_data["token"]
        print(f"  JWT token obtained (len={len(jwt_token)})")

        resolve_resp = await client.post(
            f"{L1}/identity/resolve",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        resolve_data = resolve_resp.json()
        ctx_id = resolve_data["context_token_id"]
        print(f"  Context ID: {ctx_id}")
        print(f"  Roles: {resolve_data['effective_roles']}")

        # Get full context
        verify_resp = await client.get(f"{L1}/identity/verify/{ctx_id}")
        full_ctx = verify_resp.json()
        print(f"  Session: {full_ctx.get('request_metadata', {}).get('session_id', full_ctx.get('session_id', '?'))}")

        # ── Step 3: L3 — Retrieval with Aiven pgvector ───────────
        print("\n[3/6] L3 — Schema retrieval (Aiven pgvector)...")
        svc_token = make_service_token()

        # Build security context
        user_id = full_ctx.get("user_id", resolve_data.get("user_id", "dr.sharma"))
        roles = full_ctx.get("effective_roles", resolve_data.get("effective_roles", ["ATTENDING_PHYSICIAN"]))
        department = full_ctx.get("department", "cardiology")
        clearance = full_ctx.get("clearance_level") or full_ctx.get("max_clearance_level") or resolve_data.get("max_clearance_level", 4)
        session_id = full_ctx.get("request_metadata", {}).get("session_id", full_ctx.get("session_id", "test-session"))
        facility_id = full_ctx.get("facility_id", "APH-HYD-001")
        expiry = int(time.time()) + 900
        ctx_sig = make_context_signature(user_id, roles, department, session_id, expiry, clearance)

        security_context = {
            "user_id": user_id,
            "effective_roles": roles,
            "department": department,
            "clearance_level": clearance,
            "session_id": session_id,
            "context_signature": ctx_sig,
            "context_expiry": expiry,
            "facility_id": facility_id,
        }

        l3_resp = await client.post(
            f"{L3}/api/v1/retrieval/resolve",
            headers={"Authorization": f"Bearer {svc_token}"},
            json={
                "question": "Show me patient lab results for cardiology",
                "security_context": security_context,
            },
        )
        l3_data = l3_resp.json()
        print(f"  HTTP {l3_resp.status_code}, success={l3_data.get('success')}")

        if l3_data.get("success"):
            data = l3_data.get("data", {})
            fs = data.get("filtered_schema", [])
            print(f"  Tables returned: {len(fs)}")
            for t in fs[:5]:
                print(f"    - {t['table_name']} (score={t.get('relevance_score', '?'):.3f}, cols={len(t.get('visible_columns', []))})")
            intent = data.get("intent", {})
            print(f"  Intent: {intent.get('intent')} (confidence={intent.get('confidence')})")
        else:
            print(f"  Error: {l3_data.get('error', l3_data.get('detail', 'unknown'))}")
            print(f"  Error code: {l3_data.get('error_code', '?')}")

        # ── Step 4: L2 — Knowledge graph search ──────────────────
        print("\n[4/6] L2 — Knowledge graph search...")
        l2_token = make_service_token("l3-retrieval", "pipeline_reader")
        l2_resp = await client.get(
            f"{L2}/api/v1/graph/search/tables",
            headers={"Authorization": f"Bearer {l2_token}"},
            params={"q": "lab results", "limit": 5},
        )
        if l2_resp.status_code == 200:
            l2_data = l2_resp.json()
            tables = l2_data if isinstance(l2_data, list) else l2_data.get("tables", l2_data.get("data", []))
            print(f"  Tables found: {len(tables) if isinstance(tables, list) else '?'}")
            if isinstance(tables, list):
                for t in tables[:3]:
                    name = t.get("name") or t.get("table_name") or t.get("fqn", "?")
                    print(f"    - {name}")
        else:
            print(f"  HTTP {l2_resp.status_code}: {l2_resp.text[:100]}")

        # ── Step 5: Aiven DB connectivity verification ───────────
        print("\n[5/6] Direct Aiven database verification...")
        import asyncpg
        import os

        pg_dsn_analytics = os.environ.get(
            "AIVEN_PG_DSN_ANALYTICS",
            "postgresql://avnadmin:CHANGE_ME@pg-hospital-system-hospital-syatem.k.aivencloud.com:21400/apollo_analytics",
        )
        pg_dsn_financial = os.environ.get(
            "AIVEN_PG_DSN_FINANCIAL",
            "postgresql://avnadmin:CHANGE_ME@pg-hospital-system-hospital-syatem.k.aivencloud.com:21400/apollo_financial",
        )

        # PostgreSQL
        pg_conn = await asyncpg.connect(pg_dsn_analytics, ssl="require")
        embed_count = await pg_conn.fetchval("SELECT COUNT(*) FROM schema_embeddings")
        pg_tables = await pg_conn.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
        await pg_conn.close()
        print(f"  PostgreSQL (apollo_analytics):")
        print(f"    Tables: {[r['table_name'] for r in pg_tables]}")
        print(f"    schema_embeddings rows: {embed_count}")

        pg_conn2 = await asyncpg.connect(pg_dsn_financial, ssl="require")
        pg_tables2 = await pg_conn2.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
        await pg_conn2.close()
        print(f"  PostgreSQL (apollo_financial):")
        print(f"    Tables: {[r['table_name'] for r in pg_tables2]}")

        # ── Step 6: L8 Audit ingest test ─────────────────────────
        print("\n[6/6] L8 — Audit ingest test...")
        import uuid
        audit_resp = await client.post(f"{L8}/api/v1/audit/ingest", json={
            "event_id": str(uuid.uuid4()),
            "request_id": f"e2e-test-{int(time.time())}",
            "source_layer": "L3",
            "event_type": "RETRIEVAL_COMPLETE",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "user_id": user_id,
            "session_id": session_id,
            "payload": {
                "query": "Show me patient lab results for cardiology",
                "tables_returned": 3,
                "database_backend": "aiven",
            },
        })
        print(f"  HTTP {audit_resp.status_code}: {audit_resp.json().get('status', audit_resp.json())}")

        print("\n" + "=" * 60)
        print("E2E Test Complete!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
