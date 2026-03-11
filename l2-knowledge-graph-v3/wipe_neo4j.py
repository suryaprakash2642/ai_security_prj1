import asyncio
from app.config import get_settings
from app.repositories.neo4j_manager import Neo4jManager

async def wipe():
    settings = get_settings()
    neo4j = Neo4jManager(settings)
    await neo4j.connect()
    print("Wiping Neo4j database...")
    await neo4j.execute_write("MATCH (n) DETACH DELETE n;")
    print("Dropping constraints...")
    constraints = await neo4j.execute_read("SHOW CONSTRAINTS YIELD name RETURN name")
    for row in constraints:
        name = row["name"]
        await neo4j.execute_write(f"DROP CONSTRAINT {name}")
    print("Done.")
    await neo4j.close()

if __name__ == "__main__":
    asyncio.run(wipe())
