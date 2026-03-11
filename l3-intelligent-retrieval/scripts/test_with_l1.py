import json
import httpx
from datetime import datetime, UTC, timedelta
from app.auth import create_service_token, sign_security_context
from app.models.security import SecurityContext
import os
import argparse

SECRET = os.getenv("L3_SERVICE_TOKEN_SECRET", "test-l3-secret-must-be-at-least-32-characters")
SIGNING_KEY = os.getenv("L3_CONTEXT_SIGNING_KEY", "test-context-signing-key-32-chars-min")
BASE_URL = "http://localhost:8300"

def main():
    parser = argparse.ArgumentParser(description="Test L3 using L1 Context Token")
    parser.add_argument("--question", default="Show me the patient demographics", help="Data to retrieve")
    args = parser.parse_args()

    # The JSON payload pasted by the user from L1
    l1_response = {
        "context_token_id": "ctx_ff053733f5f24748b8c4694c2c4ba589",
        "user_id": "oid-dr-patel-4521",
        "effective_roles": [
            "ATTENDING_PHYSICIAN",
            "CLINICIAN",
            "EMPLOYEE",
            "HEALTHCARE_PROVIDER",
            "HIPAA_COVERED_ENTITY",
            "SENIOR_CLINICIAN"
        ],
        "max_clearance_level": 4,
        "context_type": "NORMAL",
        "ttl_seconds": 900,
        "signature": "67baf8d25460b059ead82eb8f036f3ab9e2bdcc2924d87b4603b67a6c95b7043"
    }

    print("="*60)
    print(f"Mapping L1 Context ({l1_response['context_token_id']}) to L3 SecurityContext...")
    
    # Map L1 summary to L3's flattened SecurityContext
    ctx = SecurityContext(
        user_id=l1_response["user_id"],
        effective_roles=l1_response["effective_roles"],
        department="clinical", # Defaulted, as L1 summary omits this
        clearance_level=l1_response["max_clearance_level"],
        session_id=l1_response["context_token_id"],
        context_signature="placeholder",
        context_expiry=datetime.now(UTC) + timedelta(seconds=l1_response["ttl_seconds"]),
    )
    
    # NOTE: L1 signs the ENTIRE nested context as canonical JSON, 
    # but L3 expects the signature over a customized pipe-delimited payload. 
    # To bypass this integration gap during local testing, we resign it using L3's expected format:
    sig = sign_security_context(ctx.model_dump(), SIGNING_KEY)
    ctx = ctx.model_copy(update={"context_signature": sig})

    service_token = create_service_token("l1-identity", "pipeline_reader", SECRET)
    headers = {"Authorization": f"Bearer {service_token}"}
    
    payload = {
        "question": args.question,
        "security_context": json.loads(ctx.model_dump_json()),
        "request_id": "test-bridge-l1-l3",
        "max_tables": 10,
        "include_ddl": True,
    }

    print("Sending POST /api/v1/retrieval/resolve...")
    try:
        response = httpx.post(
            f"{BASE_URL}/api/v1/retrieval/resolve",
            json=payload,
            headers=headers,
            timeout=10.0
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            result = data.get("data", {})
            intent = result.get("intent", {})
            print(f"✅ Intent: {intent.get('primary_intent')} (Score: {intent.get('confidence', 0):.2f})")
        else:
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
