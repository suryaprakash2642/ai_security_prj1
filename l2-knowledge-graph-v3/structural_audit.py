import asyncio
import json
import os
import uuid
from neo4j import AsyncGraphDatabase
from dotenv import load_dotenv

load_dotenv()

URI = os.getenv("NEO4J_URI", "neo4j+s://5ddec823.databases.neo4j.io")
USER = os.getenv("NEO4J_USER", "5ddec823")
PASSWORD = os.getenv("NEO4J_PASSWORD", "ONSdw4Chill0TWjQSwIhR_0edgqxvNF0JS-4dw7df4nxXeiec")

async def run_audit():
    driver = AsyncGraphDatabase.driver(URI, auth=(USER, PASSWORD))
    results = {
        "verdict": "PASS",
        "critical_issues": [],
        "structural_gaps": [],
        "minor_issues": [],
        "constraints": [],
        "regulatory_report": [],
        "policy_validation": []
    }

    async with driver.session() as session:
        # 1. Constraints & Indexes
        print("Checking Constraints & Indexes...")
        res = await session.run("SHOW CONSTRAINTS")
        constraints = [rec["name"] for rec in await res.data()]
        results["constraints"] = constraints
        
        required_constraints = [
            "d.database_id IS UNIQUE",
            "t.table_id IS UNIQUE",
            "p.policy_id IS UNIQUE"
        ]
        # Note: Cypher 'SHOW CONSTRAINTS' output varies by version, we'll check substrings
        const_text = str(await (await session.run("SHOW CONSTRAINTS")).data())
        for rc in required_constraints:
            if rc.split(" ")[0].split(".")[0] not in const_text:
                 results["critical_issues"].append({"level": "P0", "issue": f"Missing constraint: {rc}"})

        # 2. Node Property Validation (Database)
        print("Validating Database nodes...")
        res = await session.run("MATCH (d:Database) RETURN d LIMIT 5")
        async for rec in res:
            d = rec["d"]
            for prop in ["database_id", "name", "engine", "host", "port", "description", "table_count", "last_crawled_at", "is_active", "version"]:
                if prop not in d:
                    results["structural_gaps"].append({"node": "Database", "prop": prop, "issue": "Missing required property"})
            
            if d.get("engine") not in ["SQLSERVER", "ORACLE", "POSTGRESQL", "MONGODB", "postgresql"]:
                results["minor_issues"].append({"node": "Database", "prop": "engine", "issue": f"Non-standard engine value: {d.get('engine')}"})

        # 3. Node Property Validation (Table)
        print("Validating Table nodes...")
        res = await session.run("MATCH (t:Table) RETURN t LIMIT 10")
        async for rec in res:
            t = rec["t"]
            for prop in ["table_id", "name", "schema_name", "database_id", "description", "sensitivity_level", "domain_tags", "column_count", "has_pii", "primary_key_columns", "is_active", "last_crawled_at", "version"]:
                if prop not in t:
                    results["structural_gaps"].append({"node": "Table", "prop": prop, "issue": "Missing required property"})
            
            # Sensitivity consistency
            res_c = await session.run("MATCH (t:Table {table_id: $tid})-[:HAS_COLUMN]->(c) RETURN max(c.sensitivity_level) as max_sens, any(x IN collect(c.is_pii) WHERE x = true) as has_pii", tid=t["table_id"])
            cons = await res_c.single()
            if cons:
                if t.get("sensitivity_level") != cons["max_sens"]:
                    results["critical_issues"].append({"level": "P0", "node": "Table", "name": t["name"], "issue": f"Sensitivity level mismatch. Table: {t.get('sensitivity_level')}, Max Column: {cons['max_sens']}"})
                if t.get("has_pii") != cons["has_pii"]:
                    results["critical_issues"].append({"level": "P0", "node": "Table", "name": t["name"], "issue": f"PII flag mismatch. Table: {t.get('has_pii')}, Columns: {cons['has_pii']}"})

        # 4. Node Property Validation (Column)
        print("Validating Column nodes...")
        res = await session.run("MATCH (c:Column) RETURN c LIMIT 20")
        async for rec in res:
            c = rec["c"]
            for prop in ["column_id", "name", "table_id", "data_type", "sensitivity_level", "is_pii", "masking_strategy", "is_nullable", "is_primary_key", "is_foreign_key", "is_indexed", "is_active"]:
                if prop not in c:
                    results["structural_gaps"].append({"node": "Column", "prop": prop, "issue": "Missing required property"})
            
            if "description" not in c:
                results["structural_gaps"].append({"node": "Column", "prop": "description", "issue": "Missing LLM-generated description"})

        # 5. Dual Representation (Policy)
        print("Validating Policy Dual Representation...")
        res = await session.run("MATCH (p:Policy) RETURN p")
        async for rec in res:
            p = rec["p"]
            if not p.get("nl_description") or not p.get("structured_rule"):
                results["critical_issues"].append({"level": "P0", "node": "Policy", "name": p.get("name"), "issue": "Missing Dual Representation (nl_description or structured_rule)"})
            
            try:
                json.loads(p.get("structured_rule", "{}"))
            except:
                results["critical_issues"].append({"level": "P0", "node": "Policy", "name": p.get("name"), "issue": "structured_rule is not valid JSON"})

        # 6. Domain Sensitivity Floor
        print("Validating Domain constraints...")
        res = await session.run("MATCH (t:Table)-[:BELONGS_TO_DOMAIN]->(d:Domain) WHERE t.sensitivity_level < d.sensitivity_floor RETURN t.name, d.name, t.sensitivity_level, d.sensitivity_floor")
        async for rec in res:
             results["critical_issues"].append({"level": "P0", "issue": f"Domain Sensitivity Floor Violation: Table {rec['t.name']} (SL:{rec['t.sensitivity_level']}) in Domain {rec['d.name']} (Floor:{rec['d.sensitivity_floor']})"})

    await driver.close()
    
    if results["critical_issues"]:
        results["verdict"] = "FAIL"
    elif results["structural_gaps"]:
        results["verdict"] = "PASS WITH GAPS"
    
    print("\n--- AUDIT RESULTS ---")
    print(json.dumps(results, indent=2))
    
    with open("audit_results.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    asyncio.run(run_audit())
