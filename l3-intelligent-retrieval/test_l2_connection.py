import httpx
import json

L2_URL = "http://localhost:8303"

def main():
    print(f"Testing L2 Knowledge Graph at {L2_URL}...")
    
    # 1. Health check
    try:
        r = httpx.get(f"{L2_URL}/api/v1/health")
        print(f"Health check: {r.status_code}")
        print(r.json())
    except Exception as e:
        print(f"Health check failed: {e}")

    # 2. Test schema sub-graph retrieval directly (which L3 calls)
    print("\nRequesting schema subgraph for Attending_Physician...")
    
    payload = {
        "roles": ["Attending_Physician"],
        "clearance_level": 4,
        "department": "Cardiology"
    }
    
    # Needs service token to auth against L2
    from app.auth import create_service_token
    import os
    # Assuming L2 uses the same shared secret or we can check its .env
    token = create_service_token("l3-retrieval", "pipeline_reader", "dev-secret-change-in-production-min-32-chars-xx")
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        r = httpx.post(
            f"{L2_URL}/api/v1/schema/subgraph", 
            json=payload,
            headers=headers
        )
        print(f"Schema subgraph status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            nodes = data.get("data", {}).get("nodes", [])
            print(f"Returned nodes: {len(nodes)}")
            for n in nodes[:5]:
                print(f" - {n.get('id')} ({n.get('labels')})")
        else:
            print(r.text)
    except Exception as e:
        print(f"Schema request failed: {e}")

if __name__ == '__main__':
    main()
