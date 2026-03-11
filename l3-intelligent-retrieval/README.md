# L3 — Intelligent Retrieval Layer

**Zero Trust NL-to-SQL Security Pipeline · Layer 3 MVP**

## Overview

The Intelligent Retrieval Layer sits between L2 (Knowledge Graph) and L4 (Policy Resolution), translating natural language questions into **policy-filtered, token-budgeted schema packages** for downstream LLM SQL generation.

**Core security principle:** The LLM only sees the intersection of **intent-relevant** and **policy-permitted** schema. This is a security boundary, not an optimization.

---

## Architecture

```
┌─────────────┐    ┌──────────────────────────────────────────────────┐    ┌─────────────┐
│ L1 Identity  │───▶│              L3 RETRIEVAL PIPELINE               │───▶│ L5 Secure    │
│   Context    │    │                                                  │    │ Generation   │
└─────────────┘    │  ┌──────────┐  ┌─────────┐  ┌───────────────┐   │    └─────────────┘
                   │  │ Embed &  │─▶│ Intent  │─▶│ Multi-Strategy│   │
                   │  │ Preproc  │  │Classify │  │  Retrieval    │   │
                   │  └──────────┘  └─────────┘  └──────┬────────┘   │
                   │                                     │            │
┌─────────────┐   │  ┌──────────┐  ┌─────────┐  ┌──────▼────────┐   │
│ L2 Knowledge│◀──┤  │  Column  │◀─│  RBAC   │◀─│ Domain-Aware  │   │
│    Graph    │───┤  │  Scoping │  │ Filter  │  │   Ranking     │   │
└─────────────┘   │  └────┬─────┘  └────┬────┘  └───────────────┘   │
                   │       │             │                            │
┌─────────────┐   │  ┌────▼─────┐  ┌────▼────┐                      │
│ L4 Policy   │◀──┤  │  Join    │  │  L4     │                      │
│ Resolution  │───┤  │  Graph   │  │ Resolve │                      │
└─────────────┘   │  └────┬─────┘  └─────────┘                      │
                   │       │                                          │
                   │  ┌────▼─────────────────┐                       │
                   │  │  Context Assembly    │──▶ RetrievalResult     │
                   │  │  (Token Budget)      │                       │
                   │  └──────────────────────┘                       │
                   └──────────────────────────────────────────────────┘
```

### Pipeline Stages (9 Steps)

| # | Stage | Description |
|---|-------|-------------|
| 1 | **SecurityContext Validation** | Verify HMAC signature + expiry → 401 if invalid |
| 2 | **Question Embedding** | Preprocess → abbreviation expansion → SHA-256 cache → Voyage/OpenAI |
| 3 | **Intent Classification** | Rule-based → 7 intents + domain hints (no LLM) |
| 4 | **Multi-Strategy Retrieval** | Semantic + Keyword + FK Walk → concurrent fusion |
| 5 | **Domain-Aware Ranking** | Composite scoring with configurable weights |
| 6 | **RBAC + L4 Resolution** | Domain pre-filter → L4 policy resolution → hard deny |
| 7 | **Column-Level Scoping** | VISIBLE / MASKED / HIDDEN / COMPUTED per column |
| 8 | **Join Graph Construction** | FK edges only between allowed tables |
| 9 | **Context Assembly** | Token budget enforcement → RetrievalResult for L5 |

---

## API Surface

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/v1/retrieval/resolve` | Service Token | Primary retrieval pipeline |
| `GET`  | `/api/v1/retrieval/health`  | None | Health check + dependency status |
| `POST` | `/api/v1/retrieval/explain` | Admin only | Pipeline debug trace |
| `POST` | `/api/v1/retrieval/cache/clear` | Admin only | Clear all caches |
| `GET`  | `/api/v1/retrieval/stats` | Service Token | Runtime statistics |

### Example Request

```json
POST /api/v1/retrieval/resolve
Authorization: Bearer <service-hmac-token>

{
  "question": "Show all patients with diabetes diagnosed in the last 6 months",
  "security_context": {
    "user_id": "dr.jones",
    "effective_roles": ["doctor"],
    "department": "endocrinology",
    "clearance_level": 3,
    "session_id": "sess-abc123",
    "context_signature": "<hmac-sha256>",
    "context_expiry": "2026-03-01T15:00:00Z"
  },
  "max_tables": 10
}
```

### Example Response

```json
{
  "success": true,
  "data": {
    "request_id": "req-abc-123",
    "user_id": "dr.jones",
    "original_question": "Show all patients with diabetes...",
    "preprocessed_question": "Show all patients with diabetes... [department:endocrinology role:doctor]",
    "intent": {
      "intent": "DATA_LOOKUP",
      "confidence": 0.82,
      "matched_keywords": ["show", "patient"],
      "domain_hints": ["clinical"],
      "used_fallback": false
    },
    "filtered_schema": [
      {
        "table_id": "apollo_his.clinical.patients",
        "table_name": "patients",
        "relevance_score": 0.87,
        "ddl_fragment": "-- Table: apollo_his.clinical.patients\n-- REQUIRED FILTER: facility_id = 'HOSP_01'\nCREATE TABLE patients (\n  patient_id integer PRIMARY KEY,\n  name varchar(100) -- MASKED: use LEFT(name, 1) || '***'\n);",
        "visible_columns": [...],
        "masked_columns": [...],
        "hidden_column_count": 2,
        "row_filters": ["facility_id = 'HOSP_01'"],
        "aggregation_only": false
      }
    ],
    "join_graph": { "edges": [...], "restricted_joins": [] },
    "nl_policy_rules": ["Only return data for the user's assigned facility"],
    "denied_tables_count": 3,
    "retrieval_metadata": {
      "total_candidates_found": 8,
      "candidates_after_rbac": 5,
      "semantic_search_ms": 4.2,
      "total_latency_ms": 28.5,
      "token_count": 1847
    }
  }
}
```

---

## Security Model

### Zero-Trust Controls

| Control | Enforcement |
|---------|-------------|
| SecurityContext validation | HMAC-SHA256 signature + UTC expiry check on every request |
| Inter-service auth | Bearer HMAC tokens with service ID allow-list |
| Deny by default | No L4 permission entry → table excluded |
| Hard DENY override | L4 DENY overrides any ALLOW |
| No full schema | LLM never sees unfiltered schema |
| No table existence disclosure | Denied tables produce no hints in responses |
| No denied column disclosure | HIDDEN columns counted, never named |
| Sensitivity-5 exclusion | `substance_abuse_records` permanently excluded |
| Fail-secure | Any dependency failure → structured error, never raw schema |
| Cache isolation | role_set_hash in cache keys prevents cross-role poisoning |

---

## Project Structure

```
l3-intelligent-retrieval/
├── app/
│   ├── __init__.py
│   ├── main.py                   # FastAPI app factory + lifespan
│   ├── config.py                 # Settings from YAML + env overrides
│   ├── auth.py                   # HMAC token + SecurityContext verification
│   ├── dependencies.py           # DI container
│   ├── models/
│   │   ├── api.py                # Request/response models
│   │   ├── enums.py              # Intent, domain, visibility enums
│   │   ├── l2_models.py          # L2 API response types
│   │   ├── l4_models.py          # L4 permission models
│   │   ├── retrieval.py          # Core pipeline models + RetrievalResult
│   │   └── security.py           # SecurityContext + ServiceIdentity
│   ├── services/
│   │   ├── orchestrator.py       # 9-stage pipeline coordinator
│   │   ├── embedding_engine.py   # Preprocess + embed + cache
│   │   ├── intent_classifier.py  # Rule-based classifier (no LLM)
│   │   ├── retrieval_pipeline.py # 3-strategy fusion
│   │   ├── ranking_engine.py     # Composite scoring
│   │   ├── rbac_filter.py        # Domain pre-filter + L4 resolution
│   │   ├── column_scoper.py      # Column visibility + DDL generation
│   │   ├── join_graph.py         # Filtered FK graph
│   │   └── context_assembler.py  # Token budget + final assembly
│   ├── clients/
│   │   ├── embedding_client.py   # Voyage + OpenAI with failover
│   │   ├── l2_client.py          # L2 Knowledge Graph HTTP client
│   │   ├── l4_client.py          # L4 Policy Resolution HTTP client
│   │   └── vector_search.py      # pgvector similarity search
│   ├── cache/
│   │   └── cache_service.py      # Redis + local LRU caches
│   ├── routes/
│   │   └── retrieval_routes.py   # API endpoints
│   └── middleware/
├── config/
│   ├── settings.yaml             # Main configuration
│   ├── abbreviations.yaml        # 80+ healthcare abbreviation expansions
│   └── ranking_weights.yaml      # Scoring weights + retrieval config
├── tests/
│   ├── conftest.py               # Fixtures, mocks, helpers (336 lines)
│   ├── test_preprocessing.py     # Whitespace, abbreviations, hashing
│   ├── test_intent.py            # All 7 intents + domain extraction
│   ├── test_scoring.py           # Composite scoring, anchors, demotion
│   ├── test_column_scoping.py    # VISIBLE/MASKED/HIDDEN/COMPUTED + DDL
│   ├── test_fk_graph.py          # Bridge detection, join construction
│   ├── test_token_budget.py      # Budget enforcement, policy priority
│   ├── test_security.py          # RBAC, cache poisoning, sensitivity-5
│   ├── test_integration.py       # Full pipeline with healthcare Qs
│   └── test_api.py               # Route auth, validation, errors
├── requirements.txt
├── pytest.ini
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Redis (for caching)
- PostgreSQL with pgvector (for semantic search)
- L2 Knowledge Graph running on :8200
- L4 Policy Resolution running on :8400

### Installation

```bash
cd l3-intelligent-retrieval
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configuration

Environment variables override YAML config:

```bash
export L3_SERVICE_TOKEN_SECRET="your-production-secret-at-least-32-chars"
export L3_CONTEXT_SIGNING_KEY="your-l1-signing-key-at-least-32-chars"
export L3_EMBEDDING_VOYAGE_API_KEY="voyage-api-key"
export L3_EMBEDDING_OPENAI_API_KEY="openai-api-key"
export L3_REDIS_URL="redis://localhost:6379/1"
export L3_L2_BASE_URL="http://localhost:8200"
export L3_L4_BASE_URL="http://localhost:8400"
```

### Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8300 --reload
```

### Run Tests

```bash
pytest tests/ -v --tb=short
pytest tests/ -v --cov=app --cov-report=term-missing
```

---

## Caching Strategy

| Cache | Backend | TTL | Key Isolation |
|-------|---------|-----|---------------|
| Question embeddings | Redis | 15 min | SHA-256(question + model) |
| Role-domain access | Redis | 5 min | role_set_hash |
| Schema fragments | Redis | 5 min | role_set_hash + table_id |
| Column metadata | Local LRU | 10 min | table_id |
| Vector search results | Redis | 60 sec | embedding hash + params |
| FK graph snapshot | Local LRU | 10 min | table_id |

---

## Performance Targets

| Metric | Target |
|--------|--------|
| P50 latency | < 25ms |
| P95 latency | < 50ms |
| P99 latency | < 100ms |
| Vector search | < 10ms |
| RBAC pre-filter | < 5ms |
| Throughput | > 200 req/sec |
| Cache hit rate | > 30% |

---

## Known MVP Limitations

1. **External stubs**: L2, L4, embedding APIs require live services or mock servers
2. **SQL Server crawler**: L2 SQL Server support is stub only
3. **Fallback classifier**: DistilBERT fallback is config-gated, not bundled
4. **Prometheus metrics**: Hooks prepared but not wired to collector
5. **Integration test suite**: Uses mocked dependencies; Docker Compose suite planned
6. **pgvector**: Requires L2-populated embedding table with HNSW index

### What IS production-ready

- Complete 9-stage pipeline with fail-secure semantics
- HMAC-based SecurityContext + inter-service authentication
- Full RBAC domain pre-filter + L4 policy resolution integration contract
- Column-level scoping with VISIBLE/MASKED/HIDDEN/COMPUTED
- Token budget enforcement with priority ordering
- Sensitivity-5 permanent exclusion
- Cache poisoning prevention via role-hash key isolation
- Rule-based intent classifier covering 7 intents + 6 domains
- 80+ healthcare abbreviation expansions
- Comprehensive test suite: unit, integration, security, API
