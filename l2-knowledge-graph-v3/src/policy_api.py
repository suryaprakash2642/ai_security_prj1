from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import os
import uuid
import datetime
import json
import hashlib
from neo4j import AsyncGraphDatabase
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Policy Administration API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

URI = os.getenv("NEO4J_URI", "neo4j+s://5ddec823.databases.neo4j.io")
USER = os.getenv("NEO4J_USER", "5ddec823")
PASSWORD = os.getenv("NEO4J_PASSWORD", "ONSdw4Chill0TWjQSwIhR_0edgqxvNF0JS-4dw7df4nxXeiec")


class PolicyCreate(BaseModel):
    name: str = Field(..., description="Name of the policy")
    effect: str = Field(..., description="ALLOW, DENY, MASK, or FILTER")
    priority: int = Field(default=100, description="Execution priority (1-999)")
    regulation: Optional[str] = Field(None, description="Regulation ID (e.g. HIPAA)")
    nl_description: str = Field(..., description="Natural language description")
    structured_rule: Dict[str, Any] = Field(..., description="JSON logic for enforcement")
    created_by: str = Field(default="admin", description="Compliance officer ID")
    effective_from: Optional[str] = Field(None, description="ISO 8601 start date")
    effective_until: Optional[str] = Field(None, description="ISO 8601 expiry date")


def _generate_uuid() -> str:
    return str(uuid.uuid4())

def _property_hash(props: dict) -> str:
    canonical = json.dumps(props, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


@app.on_event("startup")
async def startup_event():
    app.state.driver = AsyncGraphDatabase.driver(URI, auth=(USER, PASSWORD))
    async with app.state.driver.session() as session:
        await session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (p:Policy) REQUIRE p.policy_id IS UNIQUE")

@app.on_event("shutdown")
async def shutdown_event():
    await app.state.driver.close()


@app.get("/api/v1/policies")
async def get_active_policies():
    """Returns all currently active policies in the graph."""
    async with app.state.driver.session() as session:
        res = await session.run(
            "MATCH (p:Policy) WHERE p.is_active = true "
            "RETURN p.policy_id AS id, p.name AS name, p.effect AS effect, "
            "p.priority AS priority, p.nl_description AS desc, "
            "p.structured_rule AS rule, p.version AS version, "
            "p.regulation AS reg, p.effective_until AS expiry "
            "ORDER BY p.priority ASC"
        )
        policies = []
        async for r in res:
            try:
                rule = json.loads(r["rule"]) if isinstance(r["rule"], str) else r["rule"]
            except:
                rule = r["rule"]

            policies.append({
                "policy_id": r["id"],
                "name": r["name"],
                "effect": r["effect"],
                "priority": r["priority"],
                "regulation": r["reg"],
                "nl_description": r["desc"],
                "structured_rule": rule,
                "version": r["version"],
                "effective_until": r["expiry"]
            })
        return policies


@app.post("/api/v1/policies")
async def create_or_update_policy(policy: PolicyCreate):
    """
    Creates a new policy or versions an existing one. 
    Matches on 'name'. Soft deletes older versions.
    """
    async with app.state.driver.session() as session:
        # Step 1: Detect existing active policy with same name
        res = await session.run(
            "MATCH (p:Policy {name: $name, is_active: true}) RETURN p.policy_id AS id, p.version AS v",
            name=policy.name
        )
        existing = await res.single()
        
        new_version = 1
        if existing:
            new_version = existing["v"] + 1
            # Step 2: Soft delete the old version
            await session.run(
                "MATCH (p:Policy {name: $name, is_active: true}) "
                "SET p.is_active = false, p.deactivated_at = datetime()",
                name=policy.name
            )

        # Step 3: Insert new version
        new_policy_id = _generate_uuid()
        rule_str = json.dumps(policy.structured_rule)
        
        prop_hash = _property_hash(policy.dict())

        await session.run(
            "CREATE (p:Policy {policy_id: $pid}) "
            "SET p.name = $name, p.effect = $effect, p.priority = $priority, "
            "    p.nl_description = $desc, p.structured_rule = $rule, "
            "    p.version = $ver, p.is_active = true, p.created_at = datetime(), "
            "    p.last_modified_at = datetime(), "
            "    p.regulation = $reg, p.created_by = $author, "
            "    p.effective_from = $from_date, p.effective_until = $to_date, "
            "    p.property_hash = $hash",
            pid=new_policy_id, name=policy.name, effect=policy.effect,
            priority=policy.priority, desc=policy.nl_description, 
            rule=rule_str, ver=new_version, hash=prop_hash,
            reg=policy.regulation, author=policy.created_by,
            from_date=policy.effective_from, to_date=policy.effective_until
        )

        return {"status": "success", "policy_id": new_policy_id, "version": new_version}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("policy_api:app", host="0.0.0.0", port=8000, reload=True)
