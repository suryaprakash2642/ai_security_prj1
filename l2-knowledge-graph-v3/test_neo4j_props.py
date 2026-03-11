import asyncio
from neo4j import AsyncGraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()
URI = os.getenv("NEO4J_URI", "neo4j+s://5ddec823.databases.neo4j.io")
USER = os.getenv("NEO4J_USER", "5ddec823")
PASSWORD = os.getenv("NEO4J_PASSWORD", "ONSdw4Chill0TWjQSwIhR_0edgqxvNF0JS-4dw7df4nxXeiec")

async def test_nodes():
    driver = AsyncGraphDatabase.driver(URI, auth=(USER, PASSWORD))
    async with driver.session() as session:
        # Check Database
        print("\n--- DATABASE NODES ---")
        res = await session.run("MATCH (d:Database) RETURN d LIMIT 1")
        rec = await res.single()
        if rec:
            node = rec["d"]
            print(f"ID: {node.get('database_id')}")
            print(f"Name: {node.get('name')}")
            print(f"Engine: {node.get('engine')}")
            print(f"Host: {node.get('host')}")
            print(f"Port: {node.get('port')}")
            print(f"Desc: {node.get('description')}")
            print(f"Tables: {node.get('table_count')}")

        # Check Schema
        print("\n--- SCHEMA NODES ---")
        res = await session.run("MATCH (s:Schema) RETURN s LIMIT 1")
        rec = await res.single()
        if rec:
            node = rec["s"]
            print(f"ID: {node.get('schema_id')}")
            print(f"DB ID: {node.get('database_id')}")
            print(f"Name: {node.get('name')}")
            print(f"Desc: {node.get('description')}")
            print(f"Tables: {node.get('table_count')}")

        # Check Table
        print("\n--- TABLE NODES ---")
        res = await session.run("MATCH (t:Table) RETURN t LIMIT 1")
        rec = await res.single()
        if rec:
            node = rec["t"]
            print(f"ID: {node.get('table_id')}")
            print(f"DB ID: {node.get('database_id')}")
            print(f"Schema: {node.get('schema_name')}")
            print(f"Desc: {node.get('description')}")
            print(f"Cols: {node.get('column_count')}")
            print(f"PKs: {node.get('primary_key_columns')}")

        # Check Column
        print("\n--- COLUMN NODES ---")
        res = await session.run("MATCH (c:Column) RETURN c LIMIT 1")
        rec = await res.single()
        if rec:
            node = rec["c"]
            print(f"ID: {node.get('column_id')}")
            print(f"Table ID: {node.get('table_id')}")
            print(f"Name: {node.get('name')}")
            print(f"Is PK: {node.get('is_primary_key')}")
            print(f"Is FK: {node.get('is_foreign_key')}")
            print(f"Is Idx: {node.get('is_indexed')}")

        # Check Domain
        print("\n--- DOMAIN NODES ---")
        res = await session.run("MATCH (d:Domain) RETURN d LIMIT 1")
        rec = await res.single()
        if rec:
            node = rec["d"]
            print(f"ID: {node.get('domain_id')}")
            print(f"Name: {node.get('name')}")
            print(f"Desc: {node.get('description')}")
            print(f"Tables: {node.get('table_count')}")
            print(f"Sens Floor: {node.get('sensitivity_floor')}")

    await driver.close()

asyncio.run(test_nodes())
