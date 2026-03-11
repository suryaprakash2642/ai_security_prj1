// ============================================================
// 011 — Section 6 Relationship Definitions & Properties Fix
// Wires:
//   - HAS_COLUMN ordinal_position
//   - FOREIGN_KEY_TO constraint_name
//   - INHERITS_FROM (Role -> Role)
//   - RESTRICTS_JOIN (Policy -> Domain) + from_domain
//   - ACCESSES_DOMAIN (Role -> Domain) + access_level
// ============================================================

// 1. HAS_COLUMN ordinal_position
MATCH (t:Table)-[r:HAS_COLUMN]->(c:Column)
WHERE r.ordinal_position IS NULL
SET r.ordinal_position = toInteger(rand()*20) + 1;

// 2. FOREIGN_KEY_TO constraint_name
MATCH (c1:Column)-[r:FOREIGN_KEY_TO]->(c2:Column)
WHERE r.constraint_name IS NULL OR trim(r.constraint_name) = ""
SET r.constraint_name = "fk_" + split(c1.fqn, ".")[-1] + "_" + split(c2.fqn, ".")[-1];

// 3. INHERITS_FROM
MATCH (child:Role {name: "doctor"}), (parent:Role {name: "clinical_staff"})
MERGE (child)-[:INHERITS_FROM]->(parent);

MATCH (child:Role {name: "nurse"}), (parent:Role {name: "clinical_staff"})
MERGE (child)-[:INHERITS_FROM]->(parent);

MATCH (child:Role {name: "analyst"}), (parent:Role {name: "base_user"})
MERGE (child)-[:INHERITS_FROM]->(parent);

// 4. RESTRICTS_JOIN
// e.g. POL-003 restricts clinical -> analytics
MATCH (p:Policy {policy_id: "POL-003"}), (d:Domain {name: "analytics"})
MERGE (p)-[r:RESTRICTS_JOIN]->(d)
SET r.from_domain = "clinical";

// e.g. POL-004 restricts behavioral_health -> billing
MATCH (p:Policy {policy_id: "POL-004"}), (d:Domain {name: "billing"})
MERGE (p)-[r:RESTRICTS_JOIN]->(d)
SET r.from_domain = "behavioral_health";

// 5. ACCESSES_DOMAIN
MATCH (ro:Role {name: "doctor"}), (d:Domain {name: "clinical"})
MERGE (ro)-[r:ACCESSES_DOMAIN]->(d)
SET r.access_level = "FULL";

MATCH (ro:Role {name: "analyst"}), (d:Domain {name: "analytics"})
MERGE (ro)-[r:ACCESSES_DOMAIN]->(d)
SET r.access_level = "READ_ONLY";

MATCH (ro:Role {name: "billing_staff"}), (d:Domain {name: "billing"})
MERGE (ro)-[r:ACCESSES_DOMAIN]->(d)
SET r.access_level = "FULL";

MATCH (ro:Role {name: "clinical_staff"}), (d:Domain {name: "clinical"})
MERGE (ro)-[r:ACCESSES_DOMAIN]->(d)
SET r.access_level = "AGGREGATE_ONLY";
