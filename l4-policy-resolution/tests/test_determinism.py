"""Tests proving the determinism of the Policy Resolution engine.

Regardless of memory ordering, array shuffling, or graph fetch order,
the same inputs MUST produce byte-for-byte identical signatures (determinism).
"""

import json
import random
from unittest.mock import AsyncMock, patch

import pytest

from app.models.api_models import PolicyResolveRequest
from app.models.domain_models import ColumnMetadata, PolicyNode, TableMetadata
from app.services.orchestrator import PolicyOrchestrator


@pytest.fixture
def mock_graph_client():
    client = AsyncMock()
    
    # Setup mock returns
    client.get_effective_roles.return_value = {"Doctor", "Employee"}
    
    # We define a complex graph state here so we can shuffle the array
    raw_policies = [
        # Table 1: Allow (Priority 50)
        {"table_id": "db1.schema1.patients", "policy": {"policy_id": "P1", "effect": "ALLOW", "priority": 50}},
        # Table 1: Allow (Priority 100)
        {"table_id": "db1.schema1.patients", "policy": {"policy_id": "P2", "effect": "ALLOW", "priority": 100, "conditions": [{"condition_id": "C1", "condition_type": "ROW_FILTER", "expression": "provider_id = $user_id"}]}},
        # Table 2: Deny (Priority 200)
        {"table_id": "db1.schema1.billing", "policy": {"policy_id": "P3", "effect": "DENY", "priority": 200}},
    ]
    
    raw_col_policies = [
        # Table 1, SSN: Deny (Priority 100)
        {"table_id": "db1.schema1.patients", "column_name": "ssn", "column_id": "c1", "policy": {"policy_id": "PC1", "effect": "DENY", "priority": 100}},
        # Table 1, Name: Mask (Priority 100)
        {"table_id": "db1.schema1.patients", "column_name": "name", "column_id": "c2", "policy": {"policy_id": "PC2", "effect": "MASK", "priority": 100, "conditions": [{"condition_id": "C2", "condition_type": "MASKING_RULE", "expression": "HASH(name)"}]}},
    ]
    
    # We will patch the actual mocked methods in the test to yield shuffled versions
    client._raw_policies = raw_policies
    client._raw_col_policies = raw_col_policies
    
    return client


@pytest.mark.asyncio
@patch('app.services.orchestrator.datetime')
async def test_determinism_table_order_shuffle(mock_dt, mock_graph_client):
    """Proves that candidate table input order does not alter the response signature."""
    
    # Mock time so resolved_at is identical
    mock_dt.now.return_value.isoformat.return_value = "2026-03-04T12:00:00.000000+00:00"
    
    orchestrator = PolicyOrchestrator(mock_graph_client)
    
    # Request 1
    tables_order_1 = ["db1.schema1.patients", "db1.schema1.billing"]
    mock_graph_client.get_table_policies.return_value = mock_graph_client._raw_policies
    mock_graph_client.get_column_policies.return_value = mock_graph_client._raw_col_policies
    
    req1 = PolicyResolveRequest(
        candidate_table_ids=tables_order_1,
        effective_roles=["Doctor"],
        user_context={"user_id": "123"}
    )
    env1 = await orchestrator.resolve(req1)
    
    # Request 2 (Shuffled Tables)
    tables_order_2 = ["db1.schema1.billing", "db1.schema1.patients"]
    
    req2 = PolicyResolveRequest(
        candidate_table_ids=tables_order_2,
        effective_roles=["Doctor"],
        user_context={"user_id": "123"}
    )
    env2 = await orchestrator.resolve(req2)
    
    assert env1.signature == env2.signature


@pytest.mark.asyncio
@patch('app.services.orchestrator.datetime')
async def test_determinism_graph_fetch_order_shuffle(mock_dt, mock_graph_client):
    """Proves that the order Neo4j returns graph nodes does not alter the response signature."""
    mock_dt.now.return_value.isoformat.return_value = "2026-03-04T12:00:00.000000+00:00"

    orchestrator = PolicyOrchestrator(mock_graph_client)
    tables = ["db1.schema1.patients", "db1.schema1.billing"]
    
    # Request 1 (Standard order)
    mock_graph_client.get_table_policies.return_value = list(mock_graph_client._raw_policies)
    mock_graph_client.get_column_policies.return_value = list(mock_graph_client._raw_col_policies)
    
    req1 = PolicyResolveRequest(
        candidate_table_ids=tables,
        effective_roles=["Doctor"],
        user_context={"user_id": "123"}
    )
    env1 = await orchestrator.resolve(req1)
    
    # Request 2 (Shuffled Graph Return Order)
    shuffled_tables = list(mock_graph_client._raw_policies)
    shuffled_cols = list(mock_graph_client._raw_col_policies)
    random.seed(42)
    random.shuffle(shuffled_tables)
    random.shuffle(shuffled_cols)
    
    mock_graph_client.get_table_policies.return_value = shuffled_tables
    mock_graph_client.get_column_policies.return_value = shuffled_cols
    
    req2 = PolicyResolveRequest(
        candidate_table_ids=tables,
        effective_roles=["Doctor"],
        user_context={"user_id": "123"}
    )
    env2 = await orchestrator.resolve(req2)
    
    assert env1.signature == env2.signature
