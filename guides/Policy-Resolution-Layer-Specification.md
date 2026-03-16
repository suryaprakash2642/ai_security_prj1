

**XENDEX AI**

 

PROJECT SPECIFICATION DOCUMENT

**Policy Resolution Layer**

Zero Trust NL-to-SQL Security Pipeline

Apollo Hospitals Enterprise Implementation

| Property | Value |
| :---- | :---- |
| Document ID | XENDEX-ZT-L4-SPEC-001 |
| Layer | Layer 4 — Policy Resolution |
| Pipeline Position | Between Intelligent Retrieval (L3) and Secure Generation (L5) |
| Version | 1.0 |
| Classification | CONFIDENTIAL — Client Restricted |
| Last Updated | February 2026 |
| Author | Xendex AI Engineering |
| Client | Apollo Hospitals Enterprise Limited |

# **Table of Contents**

1\. Executive Summary

2\. Layer Purpose & Scope

3\. Architectural Context & Position

4\. Component Architecture Overview

5\. Policy Data Model

6\. Effective Policy Collector

7\. Conflict Resolution Engine

8\. Condition Aggregator

9\. Permission Envelope Builder

10\. Break-the-Glass Protocol Integration

11\. Apollo Hospitals Policy Catalog

12\. Policy Resolution Scenarios

13\. API Contract

14\. Data Flow

15\. Deterministic Resolution Algorithm

16\. NL Policy Rule Generation

17\. Error Handling & Fallback Strategies

18\. Caching Strategy

19\. Performance Requirements

20\. Integration Contracts

21\. Technology Stack

22\. Testing Strategy

23\. Deployment & Configuration

24\. Acceptance Criteria

# **1\. Executive Summary**

The Policy Resolution Layer is the decision engine of the zero-trust pipeline. It answers one question with absolute certainty: for this specific user, on this specific request, what are they allowed to do with each candidate table and column? The answer is a Permission Envelope — a cryptographically signed, tamper-proof artifact that dictates every downstream action.

This layer receives two inputs: the user’s SecurityContext from Layer 1 (who they are, what roles they hold, what department and facility they belong to), and a set of candidate tables from Layer 3 (what they’re asking about). It then traverses the full policy graph in Neo4j, collecting every policy that applies to the user’s effective roles, resolving conflicts using a deterministic priority-based algorithm, aggregating conditions (row filters, aggregation requirements, join restrictions, masking rules), and producing the final Permission Envelope.

The conflict resolution algorithm is the intellectual core of this layer. Healthcare policy is inherently conflicting: an Attending Physician inherits permissions from Resident, RN, CNA, and Front Desk, but also has specific restrictions that override inherited grants. Federal regulations (42 CFR Part 2\) override organizational policies. Column-level restrictions override table-level grants. The algorithm resolves all of these deterministically using four ordered rules: (1) DENY beats ALLOW at the same scope, (2) higher priority wins among same-effect policies, (3) column-level scope beats table-level scope, (4) absence of any policy \= DENY.

| ZERO TRUST PRINCIPLE Permissions are computed fresh for every request — never cached from a previous session. The Permission Envelope is cryptographically signed (HMAC-SHA256) to prevent tampering between layers. If any downstream layer receives an unsigned or expired envelope, it MUST reject the request. |
| :---- |

# **2\. Layer Purpose & Scope**

## **2.1 What This Layer Does**

* **Effective Policy Collection:** Traverses the role hierarchy graph for the user’s effective\_roles\[\], collecting every Policy node connected via APPLIES\_TO\_ROLE relationships. Includes inherited policies from parent roles.

* **Policy-to-Table Mapping:** For each candidate table from the Retrieval Layer, identifies all policies that target that table (via structured\_rule.tables or APPLIES\_TO\_TABLE relationships), that table’s domain (via APPLIES\_TO\_DOMAIN), or the table’s regulatory tags.

* **Deterministic Conflict Resolution:** When multiple policies apply to the same table or column, resolves conflicts using a fixed, auditable priority algorithm. No ambiguity. No probabilistic decisions. The same inputs always produce the same outputs.

* **Condition Aggregation:** Collects all row filters, aggregation-only requirements, join restrictions, and time-window constraints from applicable policies. Conditions are cumulative (AND logic).

* **Masking Rule Assembly:** For each column with PII classification, determines the masking strategy based on the user’s role and the column’s sensitivity level. Masking rules are compiled into executable expressions.

* **Permission Envelope Construction:** Packages all decisions into a signed Permission Envelope that the downstream layers consume without modification.

* **NL Policy Rule Generation:** Translates the machine-readable permission decisions into human-readable natural language rules that are injected into the LLM prompt by the Secure Generation Layer.

## **2.2 What This Layer Does NOT Do**

* **Does NOT retrieve schema candidates.** That is Layer 3 (Intelligent Retrieval). This layer receives candidates.

* **Does NOT generate SQL.** That is Layer 5 (Secure Generation). This layer provides the rules.

* **Does NOT validate SQL.** That is Layer 6 (Multi-Gate Validation). That layer independently re-verifies using the Permission Envelope.

* **Does NOT create or modify policies.** Policy administration is a separate operational concern with its own admin console and approval workflow.

* **Does NOT authenticate users.** That is Layer 1\. This layer consumes the authenticated SecurityContext.

## **2.3 Scope Boundaries**

| Aspect | In Scope | Out of Scope |
| :---- | :---- | :---- |
| Policy evaluation | Collecting, filtering, and resolving policies for a specific request | Policy creation, editing, approval workflows, versioning |
| Conflict resolution | Deterministic priority-based resolution for ALLOW/DENY/FILTER/MASK conflicts | Policy simulation ('what-if' analysis), impact assessment |
| Condition assembly | Row filters, aggregation rules, join restrictions, masking rules | SQL generation, query rewriting, result post-processing |
| Envelope construction | Signed Permission Envelope with structured \+ NL rules | Envelope caching across sessions, envelope forwarding to external systems |
| Break-the-glass | Evaluating active BTG tokens and applying emergency overrides | BTG initiation, approval, justification collection, retrospective review |

# **3\. Architectural Context & Position**

## **3.1 Pipeline Position**

The Policy Resolution Layer sits at position 4 in the 8-layer pipeline. It is tightly coupled with the Retrieval Layer (L3): the Retrieval Layer calls L4 synchronously during Phase 2 (RBAC pre-filter) and Phase 3 (full policy resolution) of its pipeline. The L3–L4 interaction happens within a single HTTP request lifecycle.

**Architectural significance:** This layer is the single source of truth for access decisions. No other layer makes independent authorization decisions. The Retrieval Layer uses the Permission Envelope to filter schema. The Secure Generation Layer uses it to assemble the LLM prompt. The Multi-Gate Validation Layer uses it to verify the generated SQL. All three consume the same signed envelope — ensuring consistency across the entire pipeline.

## **3.2 Upstream Dependencies**

| Layer | What It Provides | How Policy Resolution Consumes It |
| :---- | :---- | :---- |
| L1: Identity & Context | SecurityContext: user\_id, effective\_roles\[\], department, unit\_id, provider\_id, facility\_id, clearance\_level, session\_id, btg\_token (if active) | Used for role-based policy lookup, row filter parameter injection (provider\_id, unit\_id), clearance-based sensitivity filtering, and BTG token validation |
| L2: Knowledge Graph | Policy graph in Neo4j: Policy nodes with structured\_rule \+ nl\_description, APPLIES\_TO\_ROLE / APPLIES\_TO\_TABLE / APPLIES\_TO\_DOMAIN relationships, role hierarchy with INHERITS\_FROM edges, data classification nodes (sensitivity levels, PII types, masking strategies) | Primary data source. All policy evaluation happens by traversing this graph via Cypher queries. |
| L3: Intelligent Retrieval | Candidate table IDs: the set of semantically relevant tables identified by vector search (5–10 tables after RBAC domain pre-filter) | The scope of policy evaluation. L4 only evaluates policies for candidate tables, not the entire 200-table schema. This keeps resolution fast and focused. |

## **3.3 Downstream Consumers**

| Layer | What It Receives | How It Uses the Envelope |
| :---- | :---- | :---- |
| L3: Intelligent Retrieval | Permission Envelope (table decisions, column classifications, row filters, masking rules) | Applies column-level scoping: strips denied columns, flags masked columns, generates DDL fragments. Constructs filtered join graph. |
| L5: Secure Generation | Permission Envelope (nl\_rules\[\] and structured decisions) | Injects NL policy rules into the LLM prompt. Ensures the LLM is explicitly told what it can and cannot include in the SQL. |
| L6: Multi-Gate Validation | Permission Envelope (full structured decisions) | Independent re-verification: Gate 1 (structural validation) checks every table, column, and join in the generated SQL against the envelope. The validator trusts nothing from upstream. |
| L8: Audit & Anomaly | Permission Envelope (complete, including denied\_tables and denial reasons) | Logs every policy decision for compliance audit trail. Flags anomalies: unexpected denials, BTG activations, sensitivity-5 access attempts. |

# **4\. Component Architecture Overview**

The Policy Resolution Layer consists of five internal components that execute in sequence:

| Component | Responsibility | Input | Output | Latency Budget |
| :---- | :---- | :---- | :---- | :---- |
| Effective Policy Collector | Traverse role hierarchy, collect all applicable policies for effective\_roles\[\] scoped to candidate tables | effective\_roles\[\], candidate\_table\_ids\[\] | PolicySet: all matching Policy nodes with their targets and structured\_rules | 5–10ms |
| Conflict Resolution Engine | Apply deterministic priority algorithm to resolve ALLOW/DENY/FILTER/MASK conflicts per table and per column | PolicySet | ResolvedDecisions: per-table effect (ALLOW/DENY), per-column classification (VISIBLE/MASKED/HIDDEN) | 2–5ms |
| Condition Aggregator | Collect and merge all row filters, aggregation requirements, join restrictions, max\_rows, and time constraints | PolicySet \+ ResolvedDecisions | ConditionSet: row\_filters\[\], join\_restrictions\[\], aggregation\_flags{}, max\_rows{} | 1–3ms |
| NL Rule Generator | Convert machine-readable decisions into natural language rules for LLM prompt injection | ResolvedDecisions \+ ConditionSet | nl\_rules\[\]: array of human-readable policy statements | 1–2ms |
| Permission Envelope Builder | Package all decisions, conditions, and rules into a signed, versioned envelope | ResolvedDecisions \+ ConditionSet \+ nl\_rules\[\] | Signed PermissionEnvelope object | 1–2ms |

**Total target latency:** \< 30ms P95 for the complete policy resolution pipeline. This is the latency budget allocated by the Retrieval Layer (L3), which calls L4 synchronously.

| DETERMINISM GUARANTEE The Policy Resolution Engine is 100% deterministic. Given the same SecurityContext, the same candidate tables, and the same policy graph state, it will ALWAYS produce the same Permission Envelope. There is no randomness, no probabilistic logic, and no LLM involvement in policy decisions. This is auditable, reproducible, and legally defensible. |
| :---- |

# **5\. Policy Data Model**

## **5.1 Policy Node Structure**

Every policy in the Knowledge Graph is represented as a Policy node with the following properties:

(:Policy {

  policy\_id: STRING,          // Unique identifier (e.g., 'HIPAA-001')

  name: STRING,               // Human-readable name

  effect: ENUM,               // ALLOW | DENY | FILTER | MASK

  priority: INTEGER,          // 0–300, higher \= stronger

  regulation: STRING | NULL,  // Regulatory source (HIPAA, 42\_CFR\_PART\_2, DEA, etc.)

  nl\_description: TEXT,       // NL explanation for LLM prompt injection

  structured\_rule: JSON,      // Machine-readable rule definition

  is\_active: BOOLEAN,         // Soft delete / deactivation

  effective\_from: DATETIME,   // Policy activation date

  effective\_until: DATETIME | NULL, // Expiry (null \= no expiry)

  created\_by: STRING,         // Admin who created the policy

  version: INTEGER            // Policy version for audit trail

})

## **5.2 Policy Effects**

| Effect | Meaning | Priority Range | Example |
| :---- | :---- | :---- | :---- |
| ALLOW | Grants access to specified tables/columns. This is the only effect that opens access. Without an ALLOW, the table/column is invisible. | 10–70 | BIZ-001: Billing staff can access patient demographics and encounter codes for claims processing |
| DENY | Explicitly blocks access. Overrides ALLOW at the same or lower priority. Used for regulatory hard blocks and security boundaries. | 100–200 | FED-001: 42 CFR Part 2 substance abuse records denied for ALL roles via NL query system |
| FILTER | Restricts the scope of access by requiring mandatory WHERE clauses. The user can access the table but only rows matching the filter expression. | 80–100 | CLIN-001: Physicians can only access records WHERE treating\_provider\_id \= user.provider\_id |
| MASK | Allows column access but requires data transformation before display. Used for PII columns where the user needs partial information. | 40–60 | HIPAA-003: Patient SSN masked to '\*\*\*-\*\*-XXXX' format for billing staff |

## **5.3 Priority Tiers**

Priorities are organized into tiers that reflect the authority of the policy source:

| Tier | Range | Source | Override Behavior | Apollo Examples |
| :---- | :---- | :---- | :---- | :---- |
| Emergency | 300 | Break-the-glass protocol | Overrides everything EXCEPT 42 CFR Part 2 substance abuse records | EMER-001: Emergency clinical access |
| Federal Regulatory | 200 | Federal law (HIPAA, 42 CFR, DEA, HITECH) | Overrides all organizational and business policies | FED-001: 42 CFR Part 2 DENY, HIPAA-005: Psychotherapy notes DENY |
| Security Boundary | 140–160 | Cross-domain security policies | Overrides role-based grants when domains conflict | SEC-001: No Clinical-HR cross join, SEC-002: No Payer-Salary cross join |
| Regulatory Compliance | 80–100 | HIPAA minimum necessary, treatment relationship | Sets constraints on otherwise-allowed access | HIPAA-001: Must-have-WHERE-clause, CLIN-001: Treatment relationship filter |
| Role-Based Grant | 40–70 | Organizational role definitions | Base-level access grants that higher tiers can restrict | BIZ-001: Billing access, CLIN-005: Pharmacist access, CLIN-010: CNA access |
| Default | 0–10 | System defaults | Lowest priority, overridden by everything | SYS-001: Default deny for unmatched tables |

## **5.4 Structured Rule Types**

The structured\_rule JSON field contains machine-readable rule definitions. The Policy Resolution Layer supports six rule types:

| Rule Type | Description | JSON Structure (simplified) |
| :---- | :---- | :---- |
| TABLE\_ALLOW | Grants access to one or more tables, optionally restricting to specific columns | {"type":"TABLE\_ALLOW", "tables":\["prescriptions","dispensing\_records"\], "column\_overrides":{"patients":\["mrn","full\_name","dob"\]}} |
| TABLE\_DENY | Blocks access to one or more tables entirely. No column-level access. | {"type":"TABLE\_DENY", "tables":\["substance\_abuse\_records"\], "exception":"NONE\_VIA\_QUERY\_SYSTEM"} |
| COLUMN\_ALLOW | Grants access to specific columns per table. Columns not listed are denied. | {"type":"COLUMN\_ALLOW", "tables":{"patients":\["mrn","full\_name","dob","insurance\_id"\], "encounters":\["\*"\]}} |
| ROW\_FILTER | Requires mandatory WHERE clause on specified tables using user context parameters | {"type":"ROW\_FILTER", "tables":\["encounters","clinical\_notes"\], "filter":"treating\_provider\_id \= {{user.provider\_id}}"} |
| AGGREGATION\_ONLY | Allows table access but requires GROUP BY with aggregate functions. Denies patient identifiers in SELECT. | {"type":"AGGREGATION\_ONLY", "tables":\["encounters","claims"\], "denied\_in\_select":\["mrn","full\_name","ssn"\]} |
| JOIN\_RESTRICTION | Blocks cross-domain or cross-table joins | {"type":"JOIN\_RESTRICTION", "from\_domain":"Clinical", "to\_domain":"HR", "exception":"NONE"} |

## **5.5 Policy Relationships in Neo4j**

Policies are connected to their targets via typed relationships:

(:Policy)-\[:APPLIES\_TO\_ROLE\]-\>(:Role)

(:Policy)-\[:APPLIES\_TO\_TABLE\]-\>(:Table)    // Direct table targeting

(:Policy)-\[:APPLIES\_TO\_DOMAIN\]-\>(:Domain)  // Domain-wide policies

(:Policy)-\[:APPLIES\_TO\_COLUMN\]-\>(:Column)  // Column-specific masking/deny

(:Policy)-\[:SUPERSEDES\]-\>(:Policy)          // Explicit override chain

(:Policy)-\[:DERIVED\_FROM\]-\>(:Regulation)    // Regulatory source linkage

# **6\. Effective Policy Collector**

## **6.1 Purpose**

The Effective Policy Collector is the first component in the resolution pipeline. It answers: which policies are potentially relevant to this specific request? It casts a wide net, collecting all policies that apply to any of the user’s effective roles and target any of the candidate tables. Filtering and conflict resolution happen downstream.

## **6.2 Collection Algorithm**

1. **Expand role hierarchy:** Starting from the user’s effective\_roles\[\] (already expanded by Layer 1 to include inherited roles), query the Knowledge Graph for all Policy nodes connected via APPLIES\_TO\_ROLE relationships to any of these roles.

2. **Filter by table targets:** From the collected policies, retain only those whose structured\_rule.tables include at least one of the candidate\_table\_ids. Also retain domain-wide policies (APPLIES\_TO\_DOMAIN) where the domain matches any candidate table’s domain\_tags.

3. **Filter by temporal validity:** Remove policies where effective\_from \> NOW() or effective\_until \< NOW(). Only currently active policies participate in resolution.

4. **Include universal policies:** Add any policies that apply to ALL roles (e.g., FED-001: 42 CFR Part 2 applies universally). These are identified by having APPLIES\_TO\_ROLE edges to every role in the hierarchy or a special 'ALL\_ROLES' flag.

5. **Include regulatory policies:** For each candidate table that has regulatory\_flags (e.g., HIPAA, 42\_CFR\_PART\_2, DEA), include all policies DERIVED\_FROM those regulations, regardless of role linkage.

## **6.3 Primary Cypher Query**

// Collect all policies for user's roles targeting candidate tables

MATCH (p:Policy)-\[:APPLIES\_TO\_ROLE\]-\>(r:Role)

WHERE r.name IN $effective\_roles

  AND p.is\_active \= true

  AND (p.effective\_from IS NULL OR p.effective\_from \<= datetime())

  AND (p.effective\_until IS NULL OR p.effective\_until \>= datetime())

WITH COLLECT(DISTINCT p) AS role\_policies

// Add domain-wide policies

MATCH (p2:Policy)-\[:APPLIES\_TO\_DOMAIN\]-\>(d:Domain)

WHERE d.name IN $candidate\_domains

  AND p2.is\_active \= true

WITH role\_policies \+ COLLECT(DISTINCT p2) AS all\_policies

// Add regulatory policies for flagged tables

MATCH (p3:Policy)-\[:DERIVED\_FROM\]-\>(reg:Regulation)

WHERE reg.name IN $candidate\_regulatory\_flags

  AND p3.is\_active \= true

WITH all\_policies \+ COLLECT(DISTINCT p3) AS final\_policies

UNWIND final\_policies AS pol

RETURN DISTINCT pol.policy\_id, pol.name, pol.effect, pol.priority,

       pol.regulation, pol.nl\_description, pol.structured\_rule

ORDER BY pol.priority DESC

## **6.4 Expected Output**

For a typical request (5–10 candidate tables, user with 3–5 effective roles), the collector returns 10–25 applicable policies. This is the PolicySet that feeds into conflict resolution.

| Metric | Expected Value | Notes |
| :---- | :---- | :---- |
| Policies collected (typical) | 10–25 | Higher for senior clinical roles (more inherited policies) |
| Policies collected (max) | 40–50 | Clinical Director with BTG active \+ cross-domain query |
| Cypher query latency | 5–10ms | Single composite query, not multiple round trips |
| Cache consideration | Role-policy map cached 5 min | Policy changes invalidate cache via Neo4j trigger |

# **7\. Conflict Resolution Engine**

## **7.1 Purpose**

The Conflict Resolution Engine is the intellectual core of the Policy Resolution Layer. When multiple policies target the same table or column with conflicting effects, this engine deterministically resolves the conflict to produce a single, unambiguous decision.

## **7.2 Resolution Rules (Ordered by Precedence)**

The four resolution rules are applied in strict order. Each rule is a complete, unambiguous decision rule:

| Rule \# | Rule Name | Statement | Example |
| :---- | :---- | :---- | :---- |
| 1 | DENY Beats ALLOW (Same Scope) | If both DENY and ALLOW policies target the same table or column at the same scope level, DENY wins. Always. | FED-001 (DENY substance\_abuse\_records, priority 200\) beats any ALLOW policy, even EMER-001 (BTG, priority 300\) — because FED-001 has a special 'no exception' flag for 42 CFR Part 2 |
| 2 | Higher Priority Wins (Same Effect) | Among policies with the same effect (e.g., two ALLOW policies), the one with the higher priority value determines the terms. Lower-priority policies of the same effect are ignored. | CLIN-001 (FILTER, priority 90\) overrides CLIN-010 (ALLOW, priority 40\) for encounter table access. The physician gets filtered access, not CNA’s unrestricted access. |
| 3 | Column Scope Beats Table Scope | A column-specific policy overrides a table-wide policy, regardless of priority (within 20 points). This allows fine-grained exceptions to broad grants. | BIZ-001 (ALLOW patients, priority 50\) grants table access, but HIPAA-003 (MASK patients.ssn, priority 60\) masks the SSN column specifically. Column-level masking applies on top of table-level grant. |
| 4 | No Policy \= DENY | If no policy grants ALLOW for a table or column, it is DENIED by default. There is no implicit access. This is the deny-by-default posture. | A researcher with no clinical role asks about patients table. No policy in their PolicySet grants access to patients. Result: DENIED. |

## **7.3 Resolution Algorithm (Pseudocode)**

function resolve\_table(table\_id, policy\_set):

  // Step 1: Collect all policies targeting this table

  table\_policies \= filter(policy\_set, targets(table\_id))

  // Step 2: Check for hard DENY (priority \>= 200, no exception)

  hard\_denies \= filter(table\_policies,

    effect=DENY AND priority \>= 200 AND exception=NONE)

  if hard\_denies is not empty:

    return DENIED(reason=hard\_denies\[0\].policy\_id)

  // Step 3: Check for BTG override

  if btg\_token is active AND table not in btg\_exclusions:

    return ALLOWED(btg=true, audit\_flag=EMERGENCY)

  // Step 4: Separate DENY and ALLOW policies

  denies \= sort(filter(table\_policies, effect=DENY),

                key=priority, desc)

  allows \= sort(filter(table\_policies, effect=ALLOW),

                key=priority, desc)

  // Step 5: DENY beats ALLOW at same scope

  if denies is not empty:

    if allows is empty OR denies\[0\].priority \>= allows\[0\].priority:

      return DENIED(reason=denies\[0\].policy\_id)

  // Step 6: Apply highest-priority ALLOW

  if allows is not empty:

    winning\_allow \= allows\[0\]

    columns \= resolve\_columns(table\_id, table\_policies)

    filters \= collect\_row\_filters(table\_id, table\_policies)

    return ALLOWED(policy=winning\_allow, columns, filters)

  // Step 7: No policy \= DENY (default)

  return DENIED(reason='NO\_POLICY')

## **7.4 Column-Level Resolution**

After a table-level ALLOW decision, each column is individually resolved:

1. **Column explicitly allowed:** If the winning ALLOW policy’s structured\_rule lists specific columns (COLUMN\_ALLOW), only those columns are VISIBLE. All others are HIDDEN.

2. **Column explicitly denied:** If any DENY policy targets a specific column (e.g., HIPAA-003 denies patients.ssn for billing), that column is HIDDEN regardless of the table-level ALLOW.

3. **Column requires masking:** If a MASK policy targets the column (based on PII type \+ role), the column is MASKED with the specified strategy (FULL, PARTIAL, HASH, YEAR\_ONLY, REDACT).

4. **Wildcard grant:** If the ALLOW policy uses '\*' for a table (e.g., claims: \['\*'\]), all columns are VISIBLE unless individually denied or masked by other policies.

5. **Sensitivity override:** If a column’s sensitivity\_level exceeds the user’s clearance\_level, the column is HIDDEN regardless of policy grants. This is a hard ceiling that no ALLOW can override (except BTG).

# **8\. Condition Aggregator**

## **8.1 Purpose**

The Condition Aggregator collects all non-binary constraints from applicable policies. While the Conflict Resolution Engine handles binary ALLOW/DENY decisions, many policies impose conditions on how data is accessed even when access is granted. These conditions are cumulative — they stack using AND logic.

## **8.2 Condition Types**

| Condition Type | Source Policy Types | How Aggregated | Apollo Example |
| :---- | :---- | :---- | :---- |
| Row Filters | ROW\_FILTER policies | Multiple filters for the same table are combined with AND. Each filter is a SQL WHERE clause fragment with user context variable injection. | CLIN-001: encounters WHERE treating\_provider\_id \= 'DR-4521' AND CLIN-010: vital\_signs WHERE unit\_id \= '3B'. Both filters apply simultaneously. |
| Aggregation Requirements | AGGREGATION\_ONLY policies | If ANY policy for a table specifies aggregation\_only, it applies. Denied-in-SELECT columns from all such policies are merged. | BIZ-010: Revenue Cycle Manager must use GROUP BY on encounters \+ claims. Cannot SELECT mrn, full\_name, ssn, dob. |
| Join Restrictions | JOIN\_RESTRICTION policies | All join restrictions are collected as-is. Any restricted domain pair or table pair is flagged. Restrictions never cancel each other. | SEC-001: Clinical↔HR join blocked. SEC-002: payer\_contracts↔HR join blocked. |
| Maximum Row Limits | QUERY\_SCOPE policies | If multiple max\_rows values apply, the MOST RESTRICTIVE (lowest) wins. | HIPAA-001: Max 1000 unbounded rows. Department policy: Max 500 rows for Front Desk. Front Desk gets 500\. |
| Time Window Constraints | TIME\_SCOPE policies (future) | Restricts data access to records within a time window (e.g., last 12 months only) | Not currently implemented for Apollo. Reserved for future regulatory requirements. |
| Masking Rules | MASK policies \+ Data Classification | Each column’s masking strategy is determined by the most restrictive applicable masking level for the user’s role | patients.full\_name: PARTIAL for RN (first initial \+ last name), FULL for Front Desk ('\*\*\*\*\*'), NONE for Attending |

## **8.3 Row Filter Variable Injection**

Row filters contain template variables (e.g., {{user.provider\_id}}) that must be resolved with values from the SecurityContext before inclusion in the Permission Envelope. The resolution is strict:

* **Supported variables:** {{user.provider\_id}}, {{user.unit\_id}}, {{user.department}}, {{user.facility\_id}}, {{user.user\_id}}. These are the ONLY variables allowed in row filter templates.

* **Unsupported variables:** Any template variable not in the supported list is treated as a policy error. The filter is invalidated, and the table access is DENIED (fail-secure).

* **SQL injection prevention:** Injected values are ALWAYS parameterized. The row filter template is converted to a prepared statement pattern, not string-concatenated. Example: 'treating\_provider\_id \= {{user.provider\_id}}' becomes 'treating\_provider\_id \= $1' with $1 \= 'DR-4521'.

## **8.4 Masking Strategy Resolution**

| Strategy | Description | SQL Rewrite Pattern | Example Output |
| :---- | :---- | :---- | :---- |
| NONE | Column displayed as-is. No masking. | No rewrite | Srinivasan Krishnan |
| PARTIAL | First character(s) visible, rest masked. | LEFT(col, 1\) || '.' || ' ' || SPLIT\_PART(col, ' ', \-1) | S. Krishnan |
| FULL | Entire value replaced with mask string. | '\[REDACTED\]' AS col\_name | \[REDACTED\] |
| HASH | Value replaced with irreversible hash (for linkage without disclosure). | MD5(col) AS col\_name | a1b2c3d4e5f6... |
| YEAR\_ONLY | For dates, extract only the year. | EXTRACT(YEAR FROM col) AS col\_name | 1985 |
| LAST\_4 | Show only last 4 characters (for IDs, phone numbers). | REGEXP\_REPLACE(col, '.(?=.{4})', '\*') AS col\_name | \*\*\*\*5678 |
| REDACT | Column exists in schema but value is always NULL in results. | NULL::col\_type AS col\_name | NULL |

# **9\. Permission Envelope Builder**

## **9.1 Purpose**

The Permission Envelope Builder is the final assembly step. It packages all resolved decisions, aggregated conditions, and generated NL rules into a single, signed object that downstream layers consume without modification. The envelope is immutable after construction — no layer may alter it.

## **9.2 Complete Envelope Structure**

PermissionEnvelope {

  // ── Metadata ──

  envelope\_id: UUID,

  request\_id: UUID,          // Links to the parent request

  user\_id: STRING,

  effective\_roles: STRING\[\],

  computed\_at: TIMESTAMP,    // ISO 8601

  expires\_at: TIMESTAMP,     // computed\_at \+ 60 seconds

  policy\_graph\_version: STRING, // Neo4j graph version hash

  btg\_active: BOOLEAN,

  signature: STRING,          // HMAC-SHA256 of envelope contents

  // ── Table Decisions ──

  table\_decisions: {

    \[table\_id: UUID\]: {

      effect: ALLOW | DENY,

      decided\_by: STRING,    // policy\_id that made the decision

      policies\_considered: STRING\[\], // all policy\_ids evaluated

      allowed\_columns: ColumnDef\[\],

      denied\_columns: STRING\[\],  // column names only, for audit

      masked\_columns: {

        \[column\_name\]: {

          strategy: NONE|PARTIAL|FULL|HASH|YEAR\_ONLY|LAST\_4|REDACT,

          sql\_rewrite: STRING,  // Prepared SQL expression

          display\_format: STRING // Human-readable description

        }

      },

      row\_filters: STRING\[\],    // Parameterized WHERE clauses

      aggregation\_only: BOOLEAN,

      denied\_in\_select: STRING\[\], // Columns banned from SELECT

      max\_rows: INTEGER | NULL

    }

  },

  // ── Join Restrictions ──

  join\_restrictions: \[

    {from\_domain, to\_domain, policy\_id, reason}

  \],

  // ── Natural Language Rules ──

  nl\_rules: STRING\[\],         // Injected into LLM prompt by L5

  // ── Audit Fields ──

  total\_policies\_evaluated: INTEGER,

  total\_tables\_allowed: INTEGER,

  total\_tables\_denied: INTEGER,

  resolution\_latency\_ms: FLOAT

}

## **9.3 Envelope Signing**

* **Algorithm:** HMAC-SHA256

* **Key:** 256-bit symmetric key stored in HashiCorp Vault. Rotated monthly. Key ID embedded in envelope for rotation support.

* **Signed payload:** JSON-serialized envelope contents (excluding the signature field itself). Canonical JSON serialization (sorted keys, no whitespace) ensures deterministic hashing.

* **Verification:** Every downstream layer (L5, L6, L8) verifies the signature before using the envelope. Verification failure \= immediate request rejection with HTTP 403 and TAMPERED\_ENVELOPE audit event.

* **Expiry:** Envelopes expire 60 seconds after creation. This prevents replay attacks where a cached envelope from a previous request is reused after policy changes.

# **10\. Break-the-Glass Protocol Integration**

## **10.1 Overview**

Healthcare has a unique requirement: emergency access. A physician in a clinical emergency may need records outside their normal scope — a patient transferring from another unit, an unconscious patient with unknown allergies, a drug interaction emergency requiring full medication history. The Break-the-Glass (BTG) protocol grants temporary elevated access with extreme auditing.

## **10.2 BTG Token Structure**

BreakTheGlassToken {

  token\_id: UUID,

  user\_id: STRING,

  patient\_mrn: STRING,          // Specific patient (if applicable)

  reason: STRING,               // Free text justification

  emergency\_level: ENUM,        // CLINICAL\_EMERGENCY | SAFETY\_CONCERN | ADMINISTRATIVE

  granted\_at: TIMESTAMP,

  expires\_at: TIMESTAMP,        // granted\_at \+ 4 hours

  granted\_by: STRING,           // Supervisor or self (with post-hoc review)

  still\_denied: STRING\[\],       // Tables that remain denied even under BTG

  signature: HMAC-SHA256

}

## **10.3 BTG Resolution Rules**

* **BTG overrides normal DENY:** When a BTG token is active and valid, all DENY policies with priority \< 200 are overridden. The user gains elevated access to clinical tables they would normally be denied.

* **42 CFR Part 2 is NEVER overridden:** Substance abuse records (FED-001, priority 200, exception=NONE) remain DENIED even under BTG. This is federal law with no emergency exception via electronic query systems.

* **BTG tables are flagged:** Tables accessed under BTG are marked with btg\_access=true in the Permission Envelope. The Audit Layer logs these with EMERGENCY\_ACCESS flag and triggers immediate HIPAA Officer notification.

* **BTG is time-limited:** The token expires 4 hours after issuance. The physician must provide written justification within 24 hours. A retrospective review is automatically scheduled.

* **BTG scope:** If the BTG token specifies a patient\_mrn, the elevated access applies only to records for that patient. The row filter becomes: 'mrn \= $btg\_patient\_mrn'. If no patient is specified, the elevated access is broader but heavily audited.

## **10.4 Policy Resolution with BTG Active**

| Normal Decision | BTG Override | Result |
| :---- | :---- | :---- |
| encounters DENIED (wrong unit) | BTG overrides DENY | ALLOWED with btg\_access=true, EMERGENCY audit flag |
| clinical\_notes DENIED (billing role) | BTG overrides DENY | ALLOWED with btg\_access=true (only if user has clinical license) |
| substance\_abuse\_records DENIED (FED-001) | BTG CANNOT override FED-001 | DENIED. Federal law. No exception. |
| patients ALLOWED (normal access) | BTG does not change ALLOW | ALLOWED (normal). BTG flag not set. |
| mental\_health\_records DENIED (priority 200\) | BTG overrides if user has behavioral health credential | CONDITIONALLY ALLOWED based on credential check |

# **11\. Apollo Hospitals Policy Catalog**

The following is the complete policy catalog for the Apollo Hospitals implementation, organized by regulation source:

## **11.1 Federal Regulatory Policies (Priority 200\)**

| Policy ID | Name | Effect | Scope | Key Rule |
| :---- | :---- | :---- | :---- | :---- |
| FED-001 | 42 CFR Part 2 Substance Abuse Protection | DENY | substance\_abuse\_records table; columns tagged substance\_abuse | TABLE\_DENY. Applies to ALL roles. Exception: NONE\_VIA\_QUERY\_SYSTEM. Requires explicit written patient consent per disclosure. |
| HIPAA-005 | Psychotherapy Notes Protection | DENY | mental\_health\_records WHERE note\_type \= PSYCHOTHERAPY | TABLE\_DENY with column filter. Exception: AUTHORING\_PROVIDER\_ONLY (handled by separate EMR module, not NL query). |

## **11.2 Security Boundary Policies (Priority 140–160)**

| Policy ID | Name | Effect | Scope | Key Rule |
| :---- | :---- | :---- | :---- | :---- |
| SEC-001 | No Clinical-HR Cross Join | DENY | JOIN between Clinical and HR domains | JOIN\_RESTRICTION. Prevents correlation of patient outcomes with staff performance. Exception: NONE. |
| SEC-002 | No Payer Contract-Salary Cross Join | DENY | JOIN between payer\_contracts and HR domain | JOIN\_RESTRICTION. Prevents exposure of negotiated rates alongside compensation. Exception: NONE. |
| SEC-003 | No Genetic-Insurance Cross Join | DENY | JOIN between genetic\_records and Billing/Insurance domain | JOIN\_RESTRICTION. GINA compliance. Prevents genetic information disclosure to insurers. |

## **11.3 HIPAA Compliance Policies (Priority 80–100)**

| Policy ID | Name | Effect | Priority | Key Rule |
| :---- | :---- | :---- | :---- | :---- |
| HIPAA-001 | Minimum Necessary Standard | FILTER | 100 | QUERY\_SCOPE: Must have WHERE clause. Max 1000 unbounded rows. Applies to all roles. |
| CLIN-001 | Treatment Relationship Required | FILTER | 90 | ROW\_FILTER: encounters, clinical\_notes, vital\_signs, lab\_results WHERE treating\_provider\_id \= user.provider\_id OR unit\_id \= user.unit\_id. Applies to physicians and nurses. |
| HIPAA-003 | SSN Protection | MASK | 90 | Column MASK: patients.ssn, employees.ssn. Strategy: FULL for all roles (SSN never displayed in NL query results). |
| HIPAA-004 | PII Default Masking | MASK | 80 | Column MASK: Applies masking strategies based on column PII type and user role. Phone: LAST\_4. Email: PARTIAL. Address: REDACT. DOB: YEAR\_ONLY (for non-clinical roles). |

## **11.4 Role-Based Access Policies (Priority 40–70)**

| Policy ID | Name | Effect | Roles | Key Rule |
| :---- | :---- | :---- | :---- | :---- |
| BIZ-001 | Billing Minimum Clinical Access | ALLOW | Billing\_Staff | COLUMN\_ALLOW: patients(mrn, full\_name, dob, insurance\_id, insurance\_group), encounters(encounter\_id, mrn, date\_of\_service, discharge\_date, facility\_id), claims(\*), patient\_billing(\*). Denies: clinical\_notes, vital\_signs, lab\_results, prescriptions, imaging\_results. |
| BIZ-002 | Front Desk Limited Access | ALLOW | Front\_Desk | COLUMN\_ALLOW: patients(mrn, full\_name, phone, email, insurance\_id), appointments(\*), staff\_schedules(\*). No clinical, billing dollar, or medication access. |
| CLIN-005 | Pharmacist Medication Access | ALLOW | Pharmacist | TABLE\_ALLOW: prescriptions, dispensing\_records, drug\_interactions, controlled\_substances, medication\_inventory, allergies, patients(mrn, full\_name, dob). No clinical notes, lab results, or billing. |
| CLIN-010 | CNA Limited Clinical Access | ALLOW | CNA | TABLE\_ALLOW: patients(mrn, full\_name, room\_number), vital\_signs(\*), care\_plans(task\_description, schedule). ROW\_FILTER: unit\_id \= user.unit\_id. |
| BIZ-010 | Revenue Cycle Aggregate Only | ALLOW | Revenue\_Cycle\_Manager | AGGREGATION\_ONLY: encounters, claims, payments. Required: GROUP BY. Denied in SELECT: mrn, full\_name, ssn, dob. |

## **11.5 Emergency Policies (Priority 300\)**

| Policy ID | Name | Effect | Duration | Key Rule |
| :---- | :---- | :---- | :---- | :---- |
| EMER-001 | Break-the-Glass Emergency Access | ALLOW | 4 hours | EMERGENCY\_OVERRIDE: Overrides all DENY policies with priority \< 200\. Still denied: substance\_abuse\_records. Requires: reason, patient\_id. Triggers: HIPAA\_OFFICER\_NOTIFICATION, RETROSPECTIVE\_REVIEW. |

# **12\. Policy Resolution Scenarios**

## **Scenario 1: Attending Physician — Normal Clinical Query**

**User:** Dr. Patel (Attending\_Physician, Cardiology, Unit 3B)

**Effective roles:** \[Attending\_Physician, Resident\_Physician, RN, CNA, Front\_Desk\]

**Candidate tables:** \[encounters, patients, discharge\_summaries, clinical\_notes, vital\_signs\]

**Policies collected (18):** HIPAA-001, CLIN-001, HIPAA-003, HIPAA-004, BIZ-001 (inherited via CNA→Front\_Desk), BIZ-002 (inherited via Front\_Desk), CLIN-005 (not applicable — no Pharmacist role), CLIN-010 (inherited via CNA), plus domain and regulatory policies

**Resolution per table:**

* **encounters:** ALLOWED (CLIN-001 grants clinical access, priority 90). ROW\_FILTER: treating\_provider\_id \= 'DR-4521' OR unit\_id \= '3B'. Columns: all clinical columns visible. SSN hidden (HIPAA-003).

* **patients:** ALLOWED (inherited from CNA \> Front\_Desk grants). 12 columns visible including clinical demographics. SSN: HIDDEN (HIPAA-003 MASK=FULL). Phone: LAST\_4. Email: PARTIAL.

* **discharge\_summaries:** ALLOWED. ROW\_FILTER: treating\_provider\_id \= 'DR-4521'.

* **clinical\_notes:** ALLOWED (Attending has clinical access). ROW\_FILTER: treating\_provider\_id \= 'DR-4521'. Note: Psychotherapy notes excluded (HIPAA-005).

* **vital\_signs:** ALLOWED. ROW\_FILTER: treating\_provider\_id \= 'DR-4521' OR unit\_id \= '3B'.

## **Scenario 2: Billing Staff — Denied Clinical Access**

**User:** Maria (Billing\_Staff, Revenue Cycle)

**Effective roles:** \[Billing\_Staff\]

**Candidate tables:** \[clinical\_notes, encounters, patients, claims, claim\_line\_items\]

**Resolution per table:**

* **clinical\_notes:** DENIED. BIZ-001 explicitly lists clinical\_notes in denied\_tables. No ALLOW policy exists for Billing\_Staff on this table. Rule 4: no policy \= DENY.

* **encounters:** ALLOWED (BIZ-001, priority 50\) but COLUMN\_RESTRICTED: only encounter\_id, mrn, date\_of\_service, discharge\_date, facility\_id. Clinical narrative columns hidden.

* **patients:** ALLOWED (BIZ-001) but COLUMN\_RESTRICTED: mrn, full\_name, dob, insurance\_id, insurance\_group. SSN: HIDDEN. Address: HIDDEN. Phone: HIDDEN.

* **claims:** ALLOWED (BIZ-001, wildcard). All columns visible.

* **claim\_line\_items:** ALLOWED (BIZ-001, via parent\_billing domain). All columns visible.

**NL rules generated:** *'Billing staff cannot access clinical notes, vital signs, lab results, or narrative clinical documentation. Use diagnosis codes (ICD-10) and procedure codes (CPT) from encounter records for coding purposes.'*

## **Scenario 3: Revenue Cycle Manager — Aggregate-Only**

**User:** James (Revenue\_Cycle\_Manager)

**Candidate tables:** \[encounters, claims, payments\]

**Resolution:**

* **encounters, claims, payments:** All ALLOWED by BIZ-010, but AGGREGATION\_ONLY \= true. Must use GROUP BY. Denied in SELECT: mrn, full\_name, ssn, dob. NL rule: 'Results must be summary-level only. Individual patient records must never appear in results.'

## **Scenario 4: Cross-Domain Join Attempt**

**User:** Department Head (Clinical)

**Question intent:** Correlate patient outcomes with staff assignments

**Candidate tables:** \[encounters, patient\_medical\_records, staff\_schedules, employees\]

**Resolution:** SEC-001 (priority 150\) fires: Clinical↔HR join restriction. encounters and patient\_medical\_records are Clinical domain. staff\_schedules and employees are HR domain. The join\_restrictions array in the Permission Envelope contains: {from\_domain: Clinical, to\_domain: HR, policy\_id: SEC-001, reason: 'Prevents correlation of patient outcomes with staff performance'}. The LLM is instructed: 'Do NOT join clinical tables with HR/employee tables.'

## **Scenario 5: Break-the-Glass Emergency**

**User:** Dr. Patel (with active BTG token for patient MRN-78234)

**Candidate tables:** \[encounters, patients, lab\_results, prescriptions, mental\_health\_records, substance\_abuse\_records\]

**Resolution:**

* **encounters, patients, lab\_results, prescriptions:** All ALLOWED with btg\_access=true. Row filters relaxed to mrn \= 'MRN-78234' (BTG patient scope). EMERGENCY audit flag set.

* **mental\_health\_records:** CONDITIONALLY ALLOWED. BTG overrides the normal DENY (priority 200), but ONLY because Dr. Patel has a clinical credential. btg\_access=true, EMERGENCY flag, HIPAA\_OFFICER\_NOTIFICATION triggered.

* **substance\_abuse\_records:** DENIED. FED-001 (42 CFR Part 2\) has exception=NONE. BTG cannot override. Federal law. Response: 'Contact Behavioral Health department directly.'

# **13\. API Contract**

## **13.1 Primary Endpoint**

POST /api/v1/policy/resolve

**Description:** Resolves the complete Permission Envelope for a given user \+ candidate tables.

### **Request Body**

{

  "request\_id": "uuid-v4",

  "security\_context": {

    "user\_id": "USR-4521",

    "effective\_roles": \["Attending\_Physician", "Resident\_Physician",

                        "RN", "CNA", "Front\_Desk"\],

    "department": "Cardiology",

    "unit\_id": "3B",

    "provider\_id": "DR-4521",

    "facility\_id": "APOLLO-CHN-001",

    "clearance\_level": 4,

    "btg\_token": null

  },

  "candidate\_table\_ids": \["tbl-001", "tbl-002", "tbl-003"\],

  "candidate\_domains": \["Clinical", "Billing"\]

}

### **Response Body (200 OK)**

Returns the full PermissionEnvelope object as defined in Section 9.2.

### **Error Responses**

| Status | Code | Meaning |
| :---- | :---- | :---- |
| 400 | INVALID\_REQUEST | Missing or malformed candidate\_table\_ids, effective\_roles, or security\_context |
| 401 | INVALID\_SECURITY\_CONTEXT | SecurityContext signature invalid or expired |
| 500 | POLICY\_GRAPH\_UNAVAILABLE | Neo4j is unreachable. Cannot resolve policies. Returns 503 with retry-after. |
| 500 | RESOLUTION\_ERROR | Unexpected error during conflict resolution (e.g., malformed structured\_rule JSON). Fail-secure: return DENY-all envelope. |

## **13.2 Supporting Endpoints**

| Endpoint | Method | Purpose |
| :---- | :---- | :---- |
| /api/v1/policy/health | GET | Health check. Returns Neo4j connectivity, signing key status, cache state. |
| /api/v1/policy/explain | POST | Debug endpoint (ADMIN ONLY). Same input as /resolve but returns full resolution trace: all policies considered, conflict resolution steps, and why each decision was made. |
| /api/v1/policy/simulate | POST | Simulation endpoint (ADMIN ONLY). Tests 'what-if' scenarios: given a hypothetical user \+ tables, what would the envelope look like? Used for policy change impact assessment. |
| /api/v1/policy/cache/clear | POST | Clear role-policy cache. Used after policy changes in Neo4j. |
| /api/v1/policy/stats | GET | Resolution statistics: avg latency, policies evaluated per request, denial rates by role, most-triggered policies. |

# **14\. Data Flow**

## **14.1 Request Processing Pipeline (8 Steps)**

1. **Receive resolution request:** L3 (Retrieval Layer) calls POST /api/v1/policy/resolve with SecurityContext \+ candidate table IDs.

2. **Validate security context:** Verify HMAC-SHA256 signature on SecurityContext. Check expiry. Extract effective\_roles, provider\_id, unit\_id, clearance\_level, btg\_token.

3. **Collect effective policies:** Execute Cypher query against Neo4j. Traverse role hierarchy. Collect all policies targeting candidate tables, their domains, and their regulatory tags. Return PolicySet (10–25 policies typically).

4. **Resolve conflicts per table:** For each candidate table, apply the 4-rule conflict resolution algorithm. Determine ALLOW/DENY. For ALLOWED tables, resolve column-level access. Check BTG overrides.

5. **Aggregate conditions:** Collect row filters, aggregation requirements, join restrictions, max\_rows, and masking rules from all applicable policies. Resolve filter variable templates with SecurityContext values.

6. **Generate NL rules:** Convert machine-readable decisions into human-readable natural language rules for LLM prompt injection. One rule per significant constraint.

7. **Build Permission Envelope:** Package all decisions, conditions, NL rules, and metadata into the PermissionEnvelope structure. Compute HMAC-SHA256 signature. Set 60-second expiry.

8. **Return to caller:** Return signed PermissionEnvelope to L3. Log resolution metrics (latency, policies evaluated, tables allowed/denied) to audit system.

# **15\. Deterministic Resolution Algorithm**

## **15.1 Formal Algorithm Specification**

The resolution algorithm guarantees that for any given input (SecurityContext, candidate\_tables, policy\_graph\_state), the output PermissionEnvelope is identical. This section specifies the algorithm formally for audit and compliance documentation.

## **15.2 Input Normalization**

* **Role deduplication:** effective\_roles\[\] is sorted alphabetically and deduplicated before processing. This ensures that role order does not affect the result.

* **Table ordering:** candidate\_table\_ids\[\] is sorted by table\_id UUID. Resolution processes tables in this deterministic order.

* **Policy ordering:** Collected policies are sorted by (priority DESC, policy\_id ASC). When two policies have the same priority, the lexicographically first policy\_id wins. This eliminates any non-determinism.

## **15.3 Conflict Resolution Truth Table**

The following truth table shows the resolution outcome for every combination of inputs:

| ALLOW Present? | DENY Present? | BTG Active? | Hard DENY (\>=200)? | Resolution |
| :---- | :---- | :---- | :---- | :---- |
| No | No | No | No | DENIED (Rule 4: No policy \= DENY) |
| Yes | No | No | No | ALLOWED (winning ALLOW policy) |
| No | Yes | No | No | DENIED (DENY policy) |
| Yes | Yes | No | No | DENIED if DENY priority \>= ALLOW priority. ALLOWED if ALLOW priority \> DENY priority. |
| No | No | Yes | No | ALLOWED (BTG override, btg\_access=true) |
| No | Yes | Yes | No | ALLOWED (BTG overrides DENY \< 200, btg\_access=true) |
| Yes | Yes | Yes | No | ALLOWED (BTG overrides conflict, btg\_access=true) |
| Any | Any | Yes | Yes | DENIED (Hard DENY \>= 200 is never overridden, even by BTG) |
| Any | Any | No | Yes | DENIED (Hard DENY \>= 200 always wins) |

## **15.4 Edge Cases**

* **Multiple ALLOW policies with different column sets:** Column sets are UNIONED. If ALLOW-A permits columns \[a, b, c\] and ALLOW-B permits \[c, d, e\], the user sees \[a, b, c, d, e\]. This is the most permissive column union across all applicable ALLOW policies.

* **FILTER \+ AGGREGATION\_ONLY on same table:** Both conditions apply. The table is ALLOWED but with both the row filter AND the aggregation requirement. All conditions are cumulative (AND logic).

* **Role inheriting conflicting policies:** An Attending Physician inherits CNA access (CLIN-010, limited columns) but also has their own clinical access (via CLIN-001). The higher-priority policy wins: CLIN-001 at priority 90 overrides CLIN-010 at priority 40\. The physician sees more columns than the CNA.

* **Policy cycle detection:** If the policy graph contains cycles (A SUPERSEDES B SUPERSEDES A), the system detects this during collection and treats it as a configuration error. Resolution falls back to priority-only ordering. Alert sent to admin.

# **16\. NL Policy Rule Generation**

## **16.1 Purpose**

The NL Rule Generator converts machine-readable permission decisions into natural language statements that are injected into the LLM prompt by the Secure Generation Layer (L5). These rules tell the LLM what constraints to follow when generating SQL. The NL rules are a secondary enforcement mechanism — the primary enforcement is the deterministic validation in L6.

## **16.2 Rule Templates**

| Condition | Template | Example Output |
| :---- | :---- | :---- |
| Row filter active | "Filter {table} to only include rows where {filter\_expression}." | "Filter encounters to only include rows where treating\_provider\_id \= 'DR-4521' OR unit\_id \= '3B'." |
| Columns hidden | "Do not include {hidden\_columns} from {table} in any query." | "Do not include ssn, aadhaar\_number, pan\_number from patients in any query." |
| Columns masked | "When selecting {column} from {table}, apply {masking\_description}." | "When selecting full\_name from patients, show first initial \+ last name only (e.g., 'S. Krishnan')." |
| Aggregation required | "Access to {table} requires aggregate functions (COUNT, SUM, AVG, etc.) with GROUP BY. Do not include {denied\_columns} in SELECT." | "Access to encounters requires aggregate functions with GROUP BY. Do not include mrn, full\_name, ssn, dob in SELECT." |
| Join restriction | "Do NOT join tables from {domain\_a} with tables from {domain\_b}." | "Do NOT join clinical tables (encounters, patients) with HR tables (employees, staff\_schedules)." |
| Max rows | "Limit results to a maximum of {max\_rows} rows." | "Limit results to a maximum of 500 rows." |
| Table denied | Not generated. Denied tables don’t appear in the LLM’s context at all. | N/A — the LLM never learns these tables exist |

## **16.3 Rule Ordering**

NL rules are ordered by importance (highest priority first) to ensure the LLM processes the most critical constraints first:

1. **Join restrictions** (SEC-xxx policies)

2. **Aggregation requirements** (BIZ-010 and similar)

3. **Row filters** (CLIN-001, CLIN-010)

4. **Column restrictions** (hidden and masked columns)

5. **Row limits** (HIPAA-001 maximum rows)

# **17\. Error Handling & Fallback Strategies**

| Failure Scenario | Impact | Fallback | User Experience |
| :---- | :---- | :---- | :---- |
| Neo4j down | Cannot collect policies | Return DENY-ALL envelope for all candidate tables. Log POLICY\_GRAPH\_UNAVAILABLE. No degraded mode. | "System cannot verify your permissions at this time. Please try again." |
| Malformed structured\_rule | Cannot parse one policy’s rule JSON | Skip the malformed policy. If it was the winning ALLOW, table is DENIED (fail-secure). Log MALFORMED\_POLICY alert. | Transparent — user sees fewer tables if an ALLOW was skipped |
| HMAC signing key unavailable | Cannot sign the envelope | Return 500\. Do NOT return unsigned envelopes. Downstream layers will reject unsigned envelopes. | "System error. Please try again." |
| Row filter variable resolution failure | Template variable not found in SecurityContext | DENY the table with that filter. Log FILTER\_RESOLUTION\_ERROR. | Table excluded from results with no information leakage |
| BTG token expired during resolution | BTG was active at request start but expired during processing | Treat as no-BTG. Apply normal resolution rules. Log BTG\_EXPIRY\_DURING\_RESOLUTION. | Normal access (reduced scope from what BTG would have granted) |
| Policy cycle detected | Circular SUPERSEDES relationships | Fall back to priority-only ordering (ignore SUPERSEDES edges). Alert admin. Log POLICY\_CYCLE\_DETECTED. | Transparent — resolution proceeds with reduced sophistication |
| Clearance level missing | SecurityContext has null clearance\_level | Default to clearance\_level \= 0 (most restrictive). Only sensitivity-1 columns visible. | Highly restricted results until clearance is resolved |
| Excessive policy count (\>100) | Performance degradation risk | Apply timeout (15ms). If resolution exceeds timeout, return DENY-ALL with TIMEOUT flag. Log RESOLUTION\_TIMEOUT. | "Unable to process your request. Contact IT support." |
| **FAIL-SECURE GUARANTEE** Every error path in the Policy Resolution Layer results in MORE restrictive access, never less. There is no failure mode that accidentally grants access. Neo4j down? DENY all. Malformed policy? Skip it (DENY if it was the grant). Signing key unavailable? Reject the request. The user never benefits from a system failure. |  |  |  |

# **18\. Caching Strategy**

**Critical architectural decision:** Permission Envelopes are NEVER cached across requests. Each request gets a fresh envelope computed from the current policy graph state. However, intermediate data used to build the envelope can be cached for performance.

| Cache Layer | Store | Key | TTL | Invalidation | Safety |
| :---- | :---- | :---- | :---- | :---- | :---- |
| Role-policy index | Redis | role\_policies:{role\_name} | 5 min | Neo4j policy change event | Caches which policies apply to which roles, not the resolution results. Safe because resolution is still computed per-request. |
| Role hierarchy map | Local | role\_hierarchy:global | 10 min | Neo4j role change event | Caches the expanded role hierarchy tree. Changes are rare (role additions/removals). |
| Column metadata | Local | col\_meta:{table\_id} | 10 min | Schema crawl event | Column definitions, sensitivity levels, PII types. Changes only when schema is re-crawled. |
| Signing key | Local | signing\_key:current | 1 hour | Vault key rotation event | The HMAC-SHA256 key used for envelope signing. Cached locally to avoid Vault round-trip per request. |
| Regulatory tag map | Redis | reg\_tags:{table\_id} | 30 min | Schema crawl event | Which regulatory flags apply to which tables. Very stable data. |
| **ENVELOPE FRESHNESS GUARANTEE** The PermissionEnvelope is NEVER cached. It is always computed from the current policy graph state (with cached intermediate data that has short TTLs). The 5-minute cache on role-policy index means a policy change is reflected within 5 minutes at most. Active invalidation via Neo4j change events reduces this to \< 10 seconds in practice. |  |  |  |  |  |

# **19\. Performance Requirements**

| Metric | Target | Measurement | Breach Action |
| :---- | :---- | :---- | :---- |
| Total resolution latency (P50) | \< 15ms | End-to-end from request receipt to signed envelope return | Investigate cache miss rate |
| Total resolution latency (P95) | \< 30ms | Same | Alert team; check Neo4j query performance |
| Total resolution latency (P99) | \< 60ms | Same | Escalate; likely Neo4j degradation or excessive policy count |
| Cypher query execution | \< 10ms | Neo4j query time for policy collection | Check Neo4j indexes; may need query optimization |
| Conflict resolution (in-memory) | \< 5ms | CPU time for algorithm execution on PolicySet | Review algorithm efficiency; check for excessive policy count |
| Envelope signing | \< 2ms | HMAC-SHA256 computation | Check key cache; Vault round-trip would be 10–50ms |
| Concurrent throughput | \> 500 req/sec sustained | Load test with realistic role mix | Scale horizontally; add L4 instances |
| Policy count per request (avg) | 10–25 policies | Count of policies in PolicySet | Informational; higher counts may indicate policy bloat |

# **20\. Integration Contracts**

## **20.1 With Layer 3 (Intelligent Retrieval)**

**Interaction model:** Synchronous request-response. L3 calls L4 during Phase 3 of its retrieval pipeline. L4 must respond within 30ms P95 for L3 to meet its 50ms total target.

**Contract:** L3 sends candidate\_table\_ids (5–10 tables) \+ SecurityContext. L4 returns a signed PermissionEnvelope. L3 applies the envelope for column scoping and schema fragment generation.

## **20.2 With Layer 5 (Secure Generation)**

**Interaction model:** Pass-through. The PermissionEnvelope travels from L3 to L5 within the same request lifecycle. L5 reads the nl\_rules\[\] array and filtered schema from the envelope to assemble the LLM prompt.

**Contract:** L5 MUST verify the envelope signature before use. L5 MUST include all nl\_rules\[\] in the LLM prompt verbatim. L5 MUST NOT augment the schema with tables or columns not present in the envelope.

## **20.3 With Layer 6 (Multi-Gate Validation)**

**Interaction model:** Independent verification. L6 receives the same PermissionEnvelope and the generated SQL. It re-validates every table, column, and join in the SQL against the envelope.

**Contract:** L6 MUST verify the envelope signature independently. L6 MUST reject any SQL that references tables, columns, or joins not permitted by the envelope. L6 does NOT re-resolve policies — it trusts the signed envelope as the single source of truth.

## **20.4 With Layer 8 (Audit & Anomaly)**

**Interaction model:** Async log emission. The complete PermissionEnvelope (including denied\_tables and denial reasons) is logged to the audit system after the request completes.

**Contract:** The audit system receives the full envelope, including all policies\_considered and the resolution trace. This enables retrospective compliance analysis: for any historical query, auditors can see exactly which policies were evaluated and why each decision was made.

# **21\. Technology Stack**

| Component | Technology | Version | Purpose |
| :---- | :---- | :---- | :---- |
| Service framework | FastAPI (Python, async) | 0.110+ | Async REST API for policy resolution endpoints |
| Graph database | Neo4j (async driver) | 5.x | Policy graph traversal; role hierarchy; policy-table-domain relationships |
| Graph query language | Cypher | N/A | Complex traversal queries for policy collection across role hierarchies |
| Cache | Redis | 7.x | Role-policy index cache, regulatory tag cache |
| Local cache | Python dict (in-process) | N/A | Role hierarchy map, column metadata, signing key |
| Signing | HMAC-SHA256 (Python hmac) | Built-in | Envelope signing and verification |
| Secret management | HashiCorp Vault | Latest | HMAC signing key storage and rotation |
| JSON processing | orjson | 3.x | Fast canonical JSON serialization for deterministic signing |
| HTTP client | httpx (async) | 0.27+ | Internal service communication (if L4 is deployed separately from L3) |
| Metrics | Prometheus \+ Grafana | Latest | Resolution latency histograms, cache hit rates, policy evaluation counts |
| Testing | pytest \+ hypothesis | Latest | Property-based testing for determinism guarantee |

# **22\. Testing Strategy**

## **22.1 Determinism Tests**

* **Idempotency:** Run the same SecurityContext \+ candidate tables 1,000 times. Verify that every PermissionEnvelope is byte-identical (including signature, when using the same signing key).

* **Role order independence:** Shuffle effective\_roles\[\] in 100 different orderings. Verify identical envelopes for all orderings.

* **Table order independence:** Shuffle candidate\_table\_ids\[\] in 100 orderings. Verify identical envelopes.

* **Policy order independence:** Insert policies in different orders into Neo4j. Verify identical resolution results.

## **22.2 Conflict Resolution Tests**

* **DENY beats ALLOW:** Create ALLOW (priority 50\) and DENY (priority 60\) for the same table. Verify DENIED.

* **Higher priority wins:** Create two ALLOW policies with priority 40 and 60 for the same table with different column sets. Verify the priority-60 policy’s column set is used.

* **Column scope beats table scope:** Create TABLE\_ALLOW for patients (all columns) and COLUMN\_DENY for patients.ssn. Verify SSN is hidden while other columns are visible.

* **No policy \= DENY:** Query a table with no applicable policies. Verify DENIED with reason=NO\_POLICY.

* **Hard DENY is immutable:** Create EMER-001 (BTG, priority 300\) alongside FED-001 (priority 200, exception=NONE). Verify substance\_abuse\_records remains DENIED even with BTG.

## **22.3 Apollo Role Matrix Tests**

For each of the 10+ Apollo roles, resolve policies against the same 20 tables and verify:

* **Attending\_Physician:** Broad clinical access with row filters. 42 columns visible across 8 tables. SSN always hidden.

* **Billing\_Staff:** Restricted to billing \+ coding columns. clinical\_notes DENIED. 15 columns visible across 4 tables.

* **Front\_Desk:** Demographics \+ scheduling only. 10 columns visible across 3 tables.

* **Pharmacist:** Medication tables \+ patient allergies. No clinical notes or lab results. 30 columns across 7 tables.

* **CNA:** Vital signs \+ basic care. Unit-filtered. 8 columns across 3 tables.

* **Revenue\_Cycle\_Manager:** Aggregate-only on encounters \+ claims. No patient identifiers in SELECT.

## **22.4 Performance Tests**

* **Latency benchmarks:** 10,000 resolution requests with realistic policy graph (\~100 policies, \~15 roles). Verify P50 \< 15ms, P95 \< 30ms, P99 \< 60ms.

* **Throughput:** Sustain 500 req/sec for 10 minutes. No errors, no latency degradation.

* **Cold start:** Clear all caches. Run 100 resolutions. Verify graceful degradation (higher latency but no failures).

## **22.5 Security Tests**

* **Envelope tampering:** Modify one byte of a signed envelope. Verify L5/L6 reject it immediately with TAMPERED\_ENVELOPE error.

* **Expired envelope:** Wait 61 seconds after envelope creation. Verify L5/L6 reject it with EXPIRED\_ENVELOPE error.

* **BTG abuse:** Attempt BTG with expired token. Verify normal (non-BTG) resolution applies.

* **Policy privilege escalation:** Test adding a self-referencing APPLIES\_TO\_ROLE to a user-controlled policy. Verify the system prevents unauthorized policy attachment.

# **23\. Deployment & Configuration**

## **23.1 Environment Variables**

| Variable | Example Value | Description |
| :---- | :---- | :---- |
| POLICY\_SERVICE\_PORT | 8004 | HTTP port for policy resolution API |
| NEO4J\_URI | neo4j+s://graph.internal:7687 | Knowledge Graph connection (read-only) |
| NEO4J\_READ\_USER | policy\_resolver | Neo4j read-only service account for policy queries |
| REDIS\_URL | redis://cache.internal:6379/2 | Redis for role-policy index cache |
| VAULT\_ADDR | https://vault.internal:8200 | HashiCorp Vault for signing key |
| VAULT\_SIGNING\_KEY\_PATH | secret/data/policy/hmac\_key | Vault path for HMAC-SHA256 signing key |
| ENVELOPE\_TTL\_SECONDS | 60 | Permission Envelope expiry time |
| ROLE\_POLICY\_CACHE\_TTL | 300 | Role-policy index cache TTL (5 min) |
| ROLE\_HIERARCHY\_CACHE\_TTL | 600 | Role hierarchy map cache TTL (10 min) |
| MAX\_POLICY\_COUNT | 100 | Maximum policies per resolution before timeout |
| RESOLUTION\_TIMEOUT\_MS | 15 | Timeout for resolution algorithm (fail to DENY-ALL) |
| BTG\_DURATION\_HOURS | 4 | Break-the-glass token duration |
| BTG\_STILL\_DENIED | substance\_abuse\_records | Tables that remain denied even under BTG |
| LOG\_LEVEL | INFO | Application log level |
| ENABLE\_RESOLUTION\_TRACE | false | Log full resolution trace for debugging (verbose) |

## **23.2 Deployment Topology**

* **Deployment model:** The Policy Resolution Layer can be deployed as a separate microservice or co-located with the Retrieval Layer (L3) in the same process. Co-location eliminates network overhead for the L3→L4 synchronous call.

* **Recommended:** Co-locate with L3 for Apollo deployment. The L3-L4 interaction is a function call, not an HTTP request. Latency drops from 5–10ms (network) to \< 1ms (in-process).

* **Instances:** Scales with L3 instances (2–4 instances behind load balancer).

* **Memory:** 1–2 GB per instance. Local caches (role hierarchy, column metadata) consume \~100 MB.

* **CPU:** 1–2 vCPU per instance. Resolution is CPU-bound (in-memory algorithm), not I/O-bound.

# **24\. Acceptance Criteria**

The Policy Resolution Layer is accepted when ALL of the following criteria are met:

1. **Deterministic Resolution:** The same SecurityContext \+ candidate tables \+ policy graph state produces identical PermissionEnvelopes in 1,000 consecutive runs. Role order, table order, and policy insertion order do not affect results.

2. **Conflict Resolution:** All 4 resolution rules (DENY beats ALLOW, higher priority wins, column beats table, no policy \= DENY) are correctly implemented and tested with adversarial policy configurations.

3. **Policy Collection:** Cypher query correctly traverses role hierarchy, collects role-targeted policies, domain-wide policies, and regulatory policies. Universal policies (FED-001) included for every request.

4. **Condition Aggregation:** Row filters correctly resolved with SecurityContext variables (parameterized, not string-concatenated). Aggregation requirements, join restrictions, and masking rules correctly merged using AND logic.

5. **Permission Envelope:** Complete, correctly structured, signed with HMAC-SHA256, expires in 60 seconds. Verified by all downstream layers. Tampering detected and rejected.

6. **NL Rule Generation:** Human-readable rules correctly generated for all condition types. Rules ordered by importance. LLM prompt includes all rules verbatim.

7. **Break-the-Glass:** BTG token correctly overrides DENY policies with priority \< 200\. 42 CFR Part 2 (FED-001) remains DENIED under BTG. BTG access logged with EMERGENCY flag. HIPAA Officer notification triggered.

8. **Apollo Policy Catalog:** All 13+ documented policies correctly resolve for all 10+ Apollo roles across all 6 domains. All 5 documented scenarios produce results matching the specification exactly.

9. **Security Guarantees:** Every error path results in DENY or request rejection. No failure mode grants unauthorized access. Envelope tampering detected. Expired envelopes rejected. Row filter variable injection uses parameterized queries.

10. **Performance:** P50 \< 15ms, P95 \< 30ms, P99 \< 60ms. Sustained 500 req/sec for 10 minutes. Cold start degrades gracefully.

11. **Integration:** L3 synchronous call works within 30ms budget. L5 consumes nl\_rules correctly. L6 independently verifies using the same envelope. L8 receives full resolution trace for audit.

12. **Caching:** Role-policy index cached with 5-min TTL. Active invalidation on policy change within 10 seconds. PermissionEnvelope NEVER cached across requests.

*End of Document — Policy Resolution Layer Specification (XENDEX-ZT-L4-SPEC-001)*