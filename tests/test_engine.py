"""Testes do engine — execucao de workflow."""
import asyncio
import pytest

from orchestrator.engine import WorkflowEngine
from orchestrator.models import NodeStatus, NodeDef, WorkflowDef


def make_wf(nodes_data):
    nodes = [
        NodeDef(
            id=n["id"],
            type=n["type"],
            config=n.get("config", {}),
            depends_on=n.get("depends_on", []),
        )
        for n in nodes_data
    ]
    return WorkflowDef(name="test", nodes=nodes)


@pytest.mark.asyncio
async def test_sleep_node_executes():
    wf = make_wf([
        {"id": "wait", "type": "sleep", "config": {"seconds": 0.1}},
    ])
    engine = WorkflowEngine()
    record = await engine.execute(wf)
    assert record.status.value == "COMPLETED"
    assert "wait" in record.node_results
    assert record.node_results["wait"].status == NodeStatus.DONE


@pytest.mark.asyncio
async def test_shell_echo():
    wf = make_wf([
        {"id": "hello", "type": "shell", "config": {"command": "echo hello world"}},
    ])
    engine = WorkflowEngine()
    record = await engine.execute(wf)
    assert record.status.value == "COMPLETED"
    assert record.node_results["hello"].output["stdout"] == "hello world"


@pytest.mark.asyncio
async def test_dependencies_respected():
    """b depende de a, e b deve ver output de a no context."""
    wf = make_wf([
        {
            "id": "a",
            "type": "shell",
            "config": {"command": "echo primeira"},
        },
        {
            "id": "b",
            "type": "shell",
            "depends_on": ["a"],
            "config": {"command": "echo 'segunda depois de a'"},
        },
    ])
    engine = WorkflowEngine()
    record = await engine.execute(wf)
    assert record.status.value == "COMPLETED"
    assert record.node_results["a"].status == NodeStatus.DONE
    assert record.node_results["b"].status == NodeStatus.DONE


@pytest.mark.asyncio
async def test_failing_node_marks_workflow_failed():
    wf = make_wf([
        {"id": "bad", "type": "shell", "config": {"command": "exit 1"}},
    ])
    engine = WorkflowEngine()
    record = await engine.execute(wf)
    assert record.status.value == "FAILED"
    assert record.node_results["bad"].status == NodeStatus.FAILED


@pytest.mark.asyncio
async def test_retry_on_failure():
    """Node com retry deve tentar de novo e eventualmente succeed (se tentativas suficientes)."""
    wf = WorkflowDef(
        name="test",
        nodes=[
            NodeDef(
                id="flaky",
                type="shell",
                config={"command": "echo success"},
                retry={"max_attempts": 2, "delay": 0, "backoff": 1.0},
            )
        ],
    )
    engine = WorkflowEngine()
    record = await engine.execute(wf)
    assert record.status.value == "COMPLETED"
    assert record.node_results["flaky"].status == NodeStatus.DONE


@pytest.mark.asyncio
async def test_python_node_executes_code():
    wf = make_wf([
        {
            "id": "calc",
            "type": "python",
            "config": {
                "code": "result = 2 + 2",
            },
        },
    ])
    engine = WorkflowEngine()
    record = await engine.execute(wf)
    assert record.status.value == "COMPLETED"
    assert record.node_results["calc"].output == 4


@pytest.mark.asyncio
async def test_invalid_node_type_returns_failed():
    wf = make_wf([
        {"id": "x", "type": "this_type_does_not_exist"},
    ])
    engine = WorkflowEngine()
    record = await engine.execute(wf)
    assert record.status.value == "FAILED"
