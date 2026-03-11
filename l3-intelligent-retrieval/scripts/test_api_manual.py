import json
import httpx
from datetime import datetime, UTC, timedelta
from app.auth import create_service_token, sign_security_context
from app.models.security import SecurityContext
import os
import argparse

# Settings - change these if your environment uses different secrets
SECRET = os.getenv("L3_SERVICE_TOKEN_SECRET", "dev-secret-change-in-production-min-32-chars-xx")
SIGNING_KEY = os.getenv("L3_CONTEXT_SIGNING_KEY", "dev-context-signing-key-32-chars-min")
BASE_URL_L3 = "http://localhost:8300"
BASE_URL_L1 = "http://localhost:8000"

def make_request_body(question: str, ctx: SecurityContext) -> dict:
    """Build the correct RetrievalRequest body."""
    # Ensure nested dictionary format
    return {
        "question": question,
        "security_context": json.loads(ctx.model_dump_json()),
        "request_id": "manual-test-01",
        "max_tables": 10,
        "include_ddl": True,
    }

def login_l1(username, password):
    """Log in to the L1 frontend to get the user context."""
    print(f"\n🔐 Authenticating with L1 Identity ({BASE_URL_L1})...")
    try:
        r = httpx.post(
            f"{BASE_URL_L1}/auth/login",
            json={"username": username, "password": password},
            timeout=5.0
        )
        r.raise_for_status()
        data = r.json()
        print(f"✅ Login successful for {data.get('display_name')}!")
        return data
    except httpx.HTTPError as e:
        print(f"❌ Login failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response: {e.response.text}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Test L3 Endpoints E2E")
    # Using hardcoded defaults for the test
    parser.add_argument("--username", default="dr-patel-4521")
    parser.add_argument("--password", default="Apollo@123")
    parser.add_argument("--question", default="Show me patient demographics.", help="Question to resolve")
    args = parser.parse_args()

    print("="*60)
    print(f"Testing Layer 3 API Pipeline E2E")
    print("="*60)

    # 1: Authenticate with L1
    user_data = login_l1(args.username, args.password)
    if not user_data:
        print("Cannot proceed without L1 authentication.")
        return

    # Map clearance string to integer
    clearance_map = {"PUBLIC": 0, "INTERNAL": 1, "CONFIDENTIAL": 2, "SECRET": 3, "TOP_SECRET": 4}
    clearance_str = user_data.get('clearance_level', 'INTERNAL')
    clearance_level = clearance_map.get(clearance_str, 1)
    if isinstance(clearance_str, int):
        clearance_level = clearance_str

    print(f"   User ID:   {user_data.get('user_id')}")
    print(f"   Roles:     {user_data.get('effective_roles')}")
    print(f"   Clearance: {clearance_level} ({clearance_str})")

    # Service token always uses the service role "pipeline_reader"
    service_token = create_service_token("l5-generation", "pipeline_reader", SECRET)
    headers = {"Authorization": f"Bearer {service_token}"}

    # Clinical role and real details go inside the SecurityContext
    ctx = SecurityContext(
        user_id=user_data.get('user_id'),
        effective_roles=user_data.get('effective_roles', ["Attending_Physician"]),
        department=user_data.get('department_label', "clinical"),
        clearance_level=clearance_level,
        session_id="session-manual-e2e",
        context_signature="placeholder",
        context_expiry=datetime.now(UTC) + timedelta(hours=1),
    )
    
    # Sign it cryptographically so L3 accepts it
    sig = sign_security_context(ctx.model_dump(), SIGNING_KEY)
    ctx = ctx.model_copy(update={"context_signature": sig})

    # 2: Resolve (Needs Auth + SecurityContext in body)
    print(f"\n🧠 POST /api/v1/retrieval/resolve ({BASE_URL_L3})")
    print(f"Question: '{args.question}'")
    payload = make_request_body(args.question, ctx)

    try:
        response = httpx.post(
            f"{BASE_URL_L3}/api/v1/retrieval/resolve",
            json=payload,
            headers=headers,
            timeout=10.0
        )
        print(f"L3 Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            result = data.get("data", {}) or {}
            intent = result.get("intent", {}) or {}
            print(f"✅ Intent:  {intent.get('primary_intent')}  (confidence: {intent.get('confidence', 0):.2f})")
            
            tables = result.get("candidates", []) or []
            print(f"📋 Tables retrieved from L2: {len(tables)}")
            for t in tables[:5]:
                print(f"  - {t['table_id']} (score: {t.get('score', 0.0):.3f})")
            if len(tables) > 5:
                print(f"  ... and {len(tables)-5} more")
        else:
            print(f"❌ L3 Error: {response.text}")
    except httpx.ConnectError:
        print(f"ERROR: Connection refused. Is L3 running on {BASE_URL_L3}?")

if __name__ == "__main__":
    main()
