"""Testes do DAG — validacao, ciclo, ordenacao."""
import pytest
from orchestrator.dag import DAGValidationError, topological_order, validate_dag
from orchestrator.models import NodeDef, WorkflowDef


def make_wf(nodes_data):
    """Helper: cria WorkflowDef a partir de lista de dicts."""
    nodes = [
        NodeDef(
            id=n["id"],
            type=n.get("type", "shell"),
            config=n.get("config", {}),
            depends_on=n.get("depends_on", []),
        )
        for n in nodes_data
    ]
    return WorkflowDef(name="test", nodes=nodes)


def test_simple_workflow_validates():
    wf = make_wf([
        {"id": "a", "type": "shell", "config": {"command": "echo a"}},
        {"id": "b", "depends_on": ["a"], "type": "shell", "config": {"command": "echo b"}},
    ])
    assert validate_dag(wf) == []


def test_cycle_detected():
    wf = make_wf([
        {"id": "a", "depends_on": ["b"]},
        {"id": "b", "depends_on": ["a"]},
    ])
    with pytest.raises(DAGValidationError) as exc_info:
        validate_dag(wf)
    assert "Ciclo" in str(exc_info.value)


def test_missing_dependency():
    wf = make_wf([
        {"id": "a", "depends_on": ["ghost"]},
    ])
    with pytest.raises(DAGValidationError) as exc_info:
        validate_dag(wf)
    assert "ghost" in str(exc_info.value)


def test_topological_order():
    wf = make_wf([
        {"id": "c", "depends_on": ["a", "b"]},
        {"id": "a"},
        {"id": "b", "depends_on": ["a"]},
    ])
    order = topological_order(wf)
    ids = [n.id for n in order]
    assert ids[0] == "a"  # a vem primeiro
    assert ids[2] == "c"  # c vem por ultimo


def test_self_dependency():
    wf = make_wf([
        {"id": "a", "depends_on": ["a"]},
    ])
    with pytest.raises(DAGValidationError):
        validate_dag(wf)


def test_duplicate_ids():
    wf = WorkflowDef(
        name="test",
        nodes=[
            NodeDef(id="a", type="shell"),
            NodeDef(id="a", type="shell"),
        ],
    )
    with pytest.raises(DAGValidationError):
        validate_dag(wf)
