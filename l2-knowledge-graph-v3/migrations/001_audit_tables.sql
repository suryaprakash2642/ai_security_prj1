-- ============================================================
-- L2 Knowledge Graph — Audit & Versioning Tables
-- PostgreSQL 15+ with pgvector extension
-- ============================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Graph-level version counter
CREATE TABLE IF NOT EXISTS graph_version (
    id              SERIAL PRIMARY KEY,
    version         BIGINT NOT NULL DEFAULT 1,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by      VARCHAR(100) NOT NULL,
    description     TEXT
);
INSERT INTO graph_version (version, updated_by, description)
VALUES (1, 'system', 'Initial graph version')
ON CONFLICT DO NOTHING;

-- Append-only change log for all graph mutations
CREATE TABLE IF NOT EXISTS graph_change_log (
    id              BIGSERIAL PRIMARY KEY,
    graph_version   BIGINT NOT NULL,
    node_type       VARCHAR(50) NOT NULL,
    node_id         VARCHAR(500) NOT NULL,
    action          VARCHAR(20) NOT NULL CHECK (action IN (
        'CREATE', 'UPDATE', 'DEACTIVATE', 'REACTIVATE',
        'ADD_RELATIONSHIP', 'REMOVE_RELATIONSHIP'
    )),
    changed_properties JSONB,
    old_values      JSONB,
    new_values      JSONB,
    changed_by      VARCHAR(100) NOT NULL,
    change_source   VARCHAR(50) NOT NULL DEFAULT 'manual' CHECK (change_source IN (
        'schema_discovery', 'classification_engine', 'policy_admin',
        'manual', 'seed', 'rollback'
    )),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_change_log_node ON graph_change_log (node_type, node_id);
CREATE INDEX idx_change_log_time ON graph_change_log (created_at DESC);
CREATE INDEX idx_change_log_version ON graph_change_log (graph_version);
CREATE INDEX idx_change_log_action ON graph_change_log (action);

-- Policy version history (for rollback support)
CREATE TABLE IF NOT EXISTS policy_versions (
    id              BIGSERIAL PRIMARY KEY,
    policy_id       VARCHAR(50) NOT NULL,
    version         INT NOT NULL,
    policy_type     VARCHAR(20) NOT NULL,
    nl_description  TEXT NOT NULL,
    structured_rule JSONB NOT NULL,
    priority        INT NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_by      VARCHAR(100) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (policy_id, version)
);

CREATE INDEX idx_policy_versions_pid ON policy_versions (policy_id, version DESC);

-- Classification review queue
CREATE TABLE IF NOT EXISTS classification_review_queue (
    id              BIGSERIAL PRIMARY KEY,
    column_fqn      VARCHAR(500) NOT NULL,
    suggested_sensitivity   INT NOT NULL CHECK (suggested_sensitivity BETWEEN 1 AND 5),
    suggested_pii_type      VARCHAR(50),
    suggested_masking       VARCHAR(50),
    confidence      FLOAT NOT NULL CHECK (confidence BETWEEN 0.0 AND 1.0),
    reason          TEXT NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN (
        'pending', 'approved', 'rejected', 'overridden'
    )),
    reviewed_by     VARCHAR(100),
    reviewed_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_review_queue_status ON classification_review_queue (status);
CREATE INDEX idx_review_queue_col ON classification_review_queue (column_fqn);

-- Schema crawl history
CREATE TABLE IF NOT EXISTS crawl_history (
    id              BIGSERIAL PRIMARY KEY,
    database_name   VARCHAR(200) NOT NULL,
    status          VARCHAR(20) NOT NULL CHECK (status IN (
        'running', 'completed', 'failed', 'partial'
    )),
    tables_found    INT DEFAULT 0,
    tables_added    INT DEFAULT 0,
    tables_updated  INT DEFAULT 0,
    tables_deactivated INT DEFAULT 0,
    columns_found   INT DEFAULT 0,
    columns_added   INT DEFAULT 0,
    columns_updated INT DEFAULT 0,
    errors          JSONB,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    triggered_by    VARCHAR(100) NOT NULL
);

CREATE INDEX idx_crawl_history_db ON crawl_history (database_name, started_at DESC);

-- Embedding metadata tracking
CREATE TABLE IF NOT EXISTS embedding_metadata (
    id              BIGSERIAL PRIMARY KEY,
    entity_type     VARCHAR(20) NOT NULL CHECK (entity_type IN ('table', 'column', 'composite')),
    entity_fqn      VARCHAR(500) NOT NULL,
    model_name      VARCHAR(100) NOT NULL,
    model_version   VARCHAR(50) NOT NULL,
    source_text     TEXT NOT NULL,
    source_hash     VARCHAR(64) NOT NULL,
    embedding       vector(1536),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (entity_fqn, model_version)
);

CREATE INDEX idx_embedding_entity ON embedding_metadata (entity_type, entity_fqn);
CREATE INDEX idx_embedding_hash ON embedding_metadata (source_hash);

-- HNSW index for vector similarity search
CREATE INDEX idx_embedding_vector ON embedding_metadata
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- API access audit (lightweight)
CREATE TABLE IF NOT EXISTS api_access_log (
    id              BIGSERIAL PRIMARY KEY,
    service_id      VARCHAR(100) NOT NULL,
    endpoint        VARCHAR(200) NOT NULL,
    method          VARCHAR(10) NOT NULL,
    status_code     INT NOT NULL,
    latency_ms      FLOAT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_api_access_time ON api_access_log (created_at DESC);
CREATE INDEX idx_api_access_service ON api_access_log (service_id);

-- Partitioning helper for large tables (apply in production)
-- ALTER TABLE graph_change_log PARTITION BY RANGE (created_at);
-- ALTER TABLE api_access_log PARTITION BY RANGE (created_at);
