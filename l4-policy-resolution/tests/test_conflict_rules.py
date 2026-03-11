"""Tests proving the deterministic conflict resolution rules.

Rule 1: DENY beats ALLOW (if same priority).
Rule 2: Higher priority beats lower priority.
Rule 3: Column policy specifies visibility within an allowed table.
Rule 4: Default DENY if no policy exists.
"""

from unittest.mock import AsyncMock

import pytest

from app.models.api_models import PolicyResolveRequest
from app.models.enums import ColumnVisibility, TableDecision
from app.services.orchestrator import PolicyOrchestrator


@pytest.fixture
def mock_graph_client():
    client = AsyncMock()
    client.get_effective_roles.return_value = {"Doctor"}
    client.get_column_policies.return_value = []
    # By default, return empty policies so we can override in tests
    client.get_table_policies.return_value = []
    return client


@pytest.mark.asyncio
async def test_rule_1_deny_beats_allow_same_priority(mock_graph_client):
    """If an ALLOW and DENY have the exact same priority, DENY wins."""
    orchestrator = PolicyOrchestrator(mock_graph_client)
    
    mock_graph_client.get_table_policies.return_value = [
        {"table_id": "t1", "policy": {"policy_id": "P1", "effect": "ALLOW", "priority": 100}},
        {"table_id": "t1", "policy": {"policy_id": "P2", "effect": "DENY", "priority": 100}},
    ]
    
    req = PolicyResolveRequest(candidate_table_ids=["t1"], effective_roles=["Doctor"])
    env = await orchestrator.resolve(req)
    
    assert env.get_table_permission("t1").decision == TableDecision.DENY
    assert "Hard DENY applied" in env.get_table_permission("t1").reason


@pytest.mark.asyncio
async def test_rule_2_higher_priority_wins(mock_graph_client):
    """Priority 200 ALLOW beats a Priority 100 DENY."""
    orchestrator = PolicyOrchestrator(mock_graph_client)
    
    mock_graph_client.get_table_policies.return_value = [
        {"table_id": "t1", "policy": {"policy_id": "P1", "effect": "ALLOW", "priority": 200}},
        {"table_id": "t1", "policy": {"policy_id": "P2", "effect": "DENY", "priority": 100}},
    ]
    
    req = PolicyResolveRequest(candidate_table_ids=["t1"], effective_roles=["Doctor"])
    env = await orchestrator.resolve(req)
    
    assert env.get_table_permission("t1").decision == TableDecision.ALLOW


@pytest.mark.asyncio
async def test_rule_3_column_beats_table(mock_graph_client):
    """Table is ALLOWED, but specific column is DENIED."""
    orchestrator = PolicyOrchestrator(mock_graph_client)
    
    # Table allowed
    mock_graph_client.get_table_policies.return_value = [
        {"table_id": "patients", "policy": {"policy_id": "P1", "effect": "ALLOW", "priority": 100}},
    ]
    # Column SSN denied
    mock_graph_client.get_column_policies.return_value = [
        {"table_id": "patients", "column_name": "patient_name", "column_id": "c1", "policy": {}}, # No explicit policy = fallback to table = ALLOW
        {"table_id": "patients", "column_name": "ssn", "column_id": "c2", "policy": {"policy_id": "PC1", "effect": "DENY", "priority": 100}},
    ]
    
    req = PolicyResolveRequest(candidate_table_ids=["patients"], effective_roles=["Doctor"])
    env = await orchestrator.resolve(req)
    
    tp = env.get_table_permission("patients")
    assert tp.decision == TableDecision.ALLOW
    
    cols = {c.column_name: c.visibility for c in tp.columns}
    assert cols["patient_name"] == ColumnVisibility.VISIBLE
    assert cols["ssn"] == ColumnVisibility.HIDDEN


@pytest.mark.asyncio
async def test_rule_4_default_deny(mock_graph_client):
    """If no policies apply, the table is DENIED."""
    orchestrator = PolicyOrchestrator(mock_graph_client)
    
    mock_graph_client.get_table_policies.return_value = [] # Empty graph response
    
    req = PolicyResolveRequest(candidate_table_ids=["t1"], effective_roles=["Doctor"])
    env = await orchestrator.resolve(req)
    
    assert env.get_table_permission("t1").decision == TableDecision.DENY
    assert "No policies apply" in env.get_table_permission("t1").reason


@pytest.mark.asyncio
async def test_condition_aggregation(mock_graph_client):
    """Tests that row filters are aggregated and context parameters injected."""
    orchestrator = PolicyOrchestrator(mock_graph_client)
    
    mock_graph_client.get_table_policies.return_value = [
        {"table_id": "t1", "policy": {
            "policy_id": "P1", "effect": "ALLOW", "priority": 100,
            "conditions": [
                {"condition_id": "C1", "condition_type": "ROW_FILTER", "expression": "provider_id = $uid"}
            ]
        }},
        {"table_id": "t1", "policy": {
            "policy_id": "P2", "effect": "ALLOW", "priority": 100,
            "conditions": [
                {"condition_id": "C2", "condition_type": "ROW_FILTER", "expression": "department = 'Cardiology'"}
            ]
        }},
    ]
    
    req = PolicyResolveRequest(candidate_table_ids=["t1"], effective_roles=["Doctor"], user_context={"uid": "usr-999"})
    env = await orchestrator.resolve(req)
    
    tp = env.get_table_permission("t1")
    assert tp.decision == TableDecision.ALLOW
    
    # Both filters must be applied due to cumulative rules
    assert len(tp.row_filters) == 2
    # Check that $uid was replaced
    assert "(provider_id = 'usr-999')" in tp.row_filters
    assert "(department = 'Cardiology')" in tp.row_filters

    nl_text = "\n".join(tp.nl_rules)
    assert "MANDATORY" in nl_text
    assert "(provider_id = 'usr-999')" in nl_text
