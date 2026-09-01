"""Modelos de dados: Workflow, Node, Execution."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class NodeStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class ExecutionStatus(str, Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class NodeDef:
    """Definicao de um node no workflow (YAML/Python)."""
    id: str
    type: str
    config: dict[str, Any] = field(default_factory=dict)
    input: str | None = None
    condition: str | None = None  # JMESPath-like ou template "{{ node.field }}"
    depends_on: list[str] = field(default_factory=list)
    retry: dict[str, Any] | None = None  # max_attempts, delay, backoff

    @property
    def has_retry(self) -> bool:
        return self.retry is not None and self.retry.get("max_attempts", 1) > 1


@dataclass
class WorkflowDef:
    """Workflow completo (vindo do YAML ou Python DSL)."""
    name: str
    description: str | None = None
    nodes: list[NodeDef] = field(default_factory=list)
    version: str = "1"


@dataclass
class NodeResult:
    """Resultado da execucao de um node."""
    node_id: str
    status: NodeStatus
    output: Any = None
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    attempts: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float | None:
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds() * 1000
        return None


@dataclass
class ExecutionRecord:
    """Registro de uma execucao completa do workflow."""
    workflow_name: str
    status: ExecutionStatus
    started_at: datetime
    finished_at: datetime | None = None
    node_results: dict[str, NodeResult] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_s(self) -> float | None:
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None
