"""Base class para todos os node types."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from orchestrator.models import NodeDef, NodeResult, NodeStatus

logger = logging.getLogger(__name__)


class NodeError(Exception):
    """Erro levantando durante execução de um node."""


class BaseNode(ABC):
    """Classe base abstrata para nodes do workflow engine."""

    type_name: str = "base"

    def __init__(self, definition: NodeDef, context: dict[str, Any]):
        self.definition = definition
        self.context = context  # map de outputs de outros nodes

    def resolve_template(self, template: str) -> Any:
        """
        Resolve templates como '{{ node_id.output_field }}' no contexto.
        Versão simples: suporta {{ node_id.field }} e {{ node_id }}.
        """
        import re
        import json

        def replacer(match):
            key = match.group(1).strip()
            if "." in key:
                node_id, field = key.split(".", 1)
                node_out = self.context.get(node_id)
                if node_out is None:
                    raise NodeError(f"Node '{node_id}' ainda não foi executado")
                return str(node_out.get(field, ""))
            return str(self.context.get(key, match.group(0)))

        result = re.sub(r'\{\{\s*(.*?)\s*\}\}', replacer, str(template))
        # Tenta converter de volta para tipo Python
        try:
            return json.loads(result)
        except (json.JSONDecodeError, TypeError):
            return result

    @abstractmethod
    async def execute(self) -> NodeResult:
        """Executa o node e retorna o resultado."""
        ...

    async def should_run(self) -> bool:
        """Verifica condition — retorna False se o node deve ser pulado."""
        if not self.definition.condition:
            return True
        resolved = self.resolve_template(self.definition.condition)
        # condition pode ser "{{ node.alert }} == true"
        if isinstance(resolved, bool):
            return resolved
        # parse simples: "valor == true/false"
        import re as _re
        m = _re.match(r'^\s*(.+?)\s*([=!<>]+)\s*(.+?)\s*$', str(resolved))
        if m:
            left, op, right = m.group(1).strip(), m.group(2), m.group(3).strip()
            left_v = self.resolve_template("{{ " + left + " }}")
            right_v = right.strip('"\'')
            ops = {"==": lambda a, b: str(a) == b, "!=": lambda a, b: str(a) != b}
            if op in ops:
                return ops[op](left_v, right_v)
        return bool(resolved)
