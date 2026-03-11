# Layer 2 — Knowledge Graph Layer

**Zero Trust NL-to-SQL Pipeline · Central Security & Metadata Brain**

## Architecture Overview

L2 is the **read-heavy, write-rare metadata graph** at the center of the pipeline.
It stores schema catalogs, access policies, data classifications, role hierarchies,
and regulatory tags — **never** user data, PHI, or query results.

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ L1 Identity  │     │ L3 Retrieval │     │ L4 Policy   │
│   Layer      │     │    Layer     │     │  Resolution │
└──────┬───────┘     └──────┬───────┘     └──────┬──────┘
       │  role hierarchy     │  schema/cols       │  policies
       └─────────┬──────────┘──────────┬──────────┘
                 │                     │
          ┌──────▼─────────────────────▼──────┐
          │       L2 Knowledge Graph Layer     │
          │  ┌──────────┐  ┌────────────────┐  │
          │  │  Neo4j    │  │  PostgreSQL    │  │
          │  │  (graph)  │  │  (audit log)   │  │
          │  └──────────┘  └────────────────┘  │
          │  ┌──────────┐  ┌────────────────┐  │
          │  │ pgvector  │  │  FastAPI       │  │
          │  │(embeddings)│  │ (query APIs)  │  │
          │  └──────────┘  └────────────────┘  │
          └────────────────────────────────────┘
                 ▲                     ▲
       ┌─────────┴──────────┐──────────┴──────────┐
       │ Schema Discovery   │ Classification      │
       │ Service (write)    │ Engine (write)       │
       └────────────────────┘─────────────────────┘
```

### Core Principles

| Principle | Enforcement |
|-----------|-------------|
| Deny by default | Unknown roles/tables → DENY |
| Least privilege | Separate read/write Neo4j accounts |
| Metadata only | No PHI/PII data in graph — only schema metadata |
| Zero trust | All API calls authenticated via service tokens |
| No raw Cypher | Downstream layers use parameterized APIs only |
| Write isolation | Only admin/batch services can mutate graph |

### Graph Data Model

**Nodes:** Database → Schema → Table → Column, Domain, Role, Policy, Condition, Regulation

**Key Relationships:**
- `HAS_SCHEMA`, `HAS_TABLE`, `HAS_COLUMN` — structural hierarchy
- `FOREIGN_KEY_TO` — FK references between columns
- `BELONGS_TO_DOMAIN` — domain tagging
- `INHERITS_FROM` — role hierarchy
- `APPLIES_TO_ROLE`, `GOVERNS_TABLE/COLUMN/DOMAIN` — policy bindings
- `HAS_CONDITION`, `RESTRICTS_JOIN` — policy conditions
- `ACCESSES_DOMAIN` — role-domain access
- `REGULATED_BY`, `COLUMN_REGULATED_BY` — regulatory compliance

## Tech Stack

- **Neo4j 5.x** — graph database (metadata store)
- **Python 3.11+** — async backend
- **FastAPI** — API framework
- **neo4j Python driver** — official async driver
- **PostgreSQL 15+** — audit log, versioning, change records
- **pgvector** — embedding storage
- **HashiCorp Vault** — secrets management
- **Redis** — read cache for hot paths

## Folder Structure

```
l2-knowledge-graph/
├── app/
│   ├── main.py                 # FastAPI app factory + lifespan
│   ├── config.py               # Env-based config + Vault integration
│   ├── dependencies.py         # DI container (singleton services)
│   ├── auth.py                 # HMAC service token auth + RBAC
│   ├── models/
│   │   ├── enums.py            # All enumerations (25+ types)
│   │   ├── graph.py            # Graph node/rel Pydantic models
│   │   ├── api.py              # Request/response schemas
│   │   └── audit.py            # Audit record models
│   ├── repositories/
│   │   ├── neo4j_manager.py    # Connection pool + TLS + read/write separation
│   │   ├── graph_read_repo.py  # Read-only parameterized queries (500 lines)
│   │   ├── graph_write_repo.py # Write-only graph mutations (380 lines)
│   │   └── audit_repository.py # PostgreSQL audit log (375 lines)
│   ├── routes/
│   │   ├── schema_routes.py    # Schema query endpoints (6 endpoints)
│   │   ├── policy_routes.py    # Policy query + simulate endpoints
│   │   ├── classification_routes.py  # PII, masking, regulations
│   │   └── admin_routes.py     # Crawl, classify, embed, health, audit
│   └── services/
│       ├── schema_discovery.py # Multi-DB crawler (SQL Server, PG, Oracle, Mongo)
│       ├── classification_engine.py  # 15+ PII patterns, review queue
│       ├── policy_service.py   # CRUD, simulation, version rollback
│       ├── embedding_pipeline.py     # pgvector + hash-based refresh
│       ├── health_check.py     # 8 automated graph integrity checks
│       └── cache.py            # Redis with graceful degradation
├── cypher/
│   ├── 001_constraints_indexes.cypher
│   └── 002_seed_data.cypher    # Apollo Hospitals sample graph
├── migrations/
│   └── 001_audit_tables.sql    # PG audit tables + pgvector
├── scripts/
│   ├── init_graph.py           # Bootstrap constraints + seed + migrations
│   └── run_crawl.py            # Manual crawl trigger CLI
├── seed_data/
│   └── apollo_hospitals.py     # Python seed data loader (7 tables, 9 policies)
├── docs/
│   └── api_examples.md         # Full request/response examples
├── tests/                      # 8 test files, 1541 lines
│   ├── conftest.py             # Fixtures, mocks, sample factories
│   ├── test_graph_repository.py
│   ├── test_classification.py
│   ├── test_policy.py
│   ├── test_health.py
│   ├── test_auth.py
│   ├── test_models.py
│   └── test_api.py
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Neo4j 5.x (or use docker-compose)

### 1. Environment Setup

```bash
cp .env.example .env
# Edit .env with your credentials
```

### 2. Start Infrastructure

```bash
docker-compose up -d neo4j postgres redis
```

### 3. Initialize Graph Schema

```bash
python -m scripts.init_graph
```

### 4. Seed Sample Data

```bash
python -m seed_data.apollo_hospitals
```

### 5. Run the API Server

```bash
uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8002 --reload
```

### 6. Run Tests

```bash
pytest tests/ -v --tb=short
```

## API Endpoints

### Schema APIs
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/graph/tables/by-domain?domain=clinical` | Tables by domain |
| GET | `/api/v1/graph/tables/{table_id}/columns` | Columns for table |
| GET | `/api/v1/graph/tables/by-sensitivity?min_level=3` | Tables by sensitivity |
| GET | `/api/v1/graph/foreign-keys/{table_id}` | FK relationships |
| GET | `/api/v1/graph/search/tables?q=patient` | Search tables |

### Policy APIs
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/graph/policies/for-roles?roles=doctor,nurse` | Policies for roles |
| GET | `/api/v1/graph/policies/for-table?table_id=...` | Policies for table |
| GET | `/api/v1/graph/policies/join-restrictions?roles=...` | Join restrictions |
| POST | `/api/v1/graph/policies/simulate` | Simulate policy check |

### Classification APIs
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/graph/columns/pii` | PII columns |
| GET | `/api/v1/graph/tables/regulated-by?regulation=HIPAA` | Regulated tables |
| GET | `/api/v1/graph/masking-rules/{table_id}` | Masking rules |

### Admin APIs (admin role only)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/admin/crawl` | Trigger schema crawl |
| POST | `/api/v1/admin/classify` | Run classification |
| POST | `/api/v1/admin/embed` | Refresh embeddings |
| GET | `/api/v1/admin/health` | Full health check |
| GET | `/api/v1/admin/version` | Graph version info |

## Security Model

- **TLS-only** Neo4j connections
- **Service account** authentication (JWT/token-based)
- **Read/write separation** at Neo4j driver level
- **Vault integration** for all credentials
- **Role-based** API access: `pipeline_reader`, `schema_writer`, `policy_writer`, `admin`
- **Rate limiting** on all endpoints
- **Audit logging** of all write operations to PostgreSQL

## Performance Targets

| Metric | Target |
|--------|--------|
| Schema query P95 | < 10 ms |
| Column query P95 | < 15 ms |
| Policy query P95 | < 30 ms |
| Full crawl (~200 tables) | < 30 min |
| Sustained read throughput | 500 req/sec |

## Known Assumptions

1. Neo4j Enterprise for role-based access; Community edition works with app-level enforcement
2. Vault integration uses `hvac` client; falls back to env vars in dev
3. LLM description generation requires configured OpenAI/Anthropic endpoint
4. Embedding pipeline uses `text-embedding-3-small` by default; configurable
5. Schema discovery requires source DB read-only credentials provisioned separately
6. `substance_abuse_records` → HARD DENY enforced at graph level and API level; no override path
