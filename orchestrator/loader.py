"""Loaders: YAML e Python DSL para definir workflows."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError

from orchestrator.models import NodeDef, WorkflowDef


class NodeSchema(BaseModel):
    """Schema para nodes vindos do YAML."""
    id: str
    type: str
    config: dict[str, Any] = Field(default_factory=dict)
    input: str | None = None
    condition: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    retry: dict[str, Any] | None = None


class WorkflowSchema(BaseModel):
    """Schema para o YAML de workflow."""
    name: str
    description: str | None = None
    version: str = "1"
    nodes: list[NodeSchema]


def load_yaml(path: str | Path) -> WorkflowDef:
    """Carrega um workflow de um arquivo YAML."""
    with open(path) as f:
        data = yaml.safe_load(f)
    return from_dict(data)


def from_dict(data: dict[str, Any]) -> WorkflowDef:
    """Constrói um WorkflowDef a partir de dict (YAML ou Python DSL)."""
    schema = WorkflowSchema.model_validate(data)
    return WorkflowDef(
        name=schema.name,
        description=schema.description,
        version=schema.version,
        nodes=[
            NodeDef(
                id=n.id,
                type=n.type,
                config=n.config,
                input=n.input,
                condition=n.condition,
                depends_on=n.depends_on,
                retry=n.retry,
            )
            for n in schema.nodes
        ],
    )
