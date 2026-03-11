import httpx
import json

L2_URL = "http://localhost:8303"

def main():
    print("Testing L2 Knowledge Graph Tables by domain and role-domain-access...")
    
    from app.auth import create_service_token
    import os
    token = create_service_token("l3-retrieval", "pipeline_reader", "dev-secret-change-in-production-min-32-chars-xx")
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Role Domain Access
    try:
        r = httpx.get(
            f"{L2_URL}/api/v1/graph/roles/domain-access", 
            params={"roles": "Attending_Physician"},
            headers=headers
        )
        print(f"\n--- Role domain access (Attending_Physician) - Status: {r.status_code}")
        if r.status_code == 200:
            print(json.dumps(r.json(), indent=2))
        else:
            print(r.text)
    except Exception as e:
        print(f"Role domain request failed: {e}")

    # 2. Search tables
    try:
        r = httpx.get(
            f"{L2_URL}/api/v1/graph/search/tables", 
            params={"q": "demographics", "limit": 10},
            headers=headers
        )
        print(f"\n--- Search tables (demographics) - Status: {r.status_code}")
        if r.status_code == 200:
            print(json.dumps(r.json(), indent=2))
        else:
            print(r.text)
    except Exception as e:
        print(f"Search tables request failed: {e}")

if __name__ == '__main__':
    main()
