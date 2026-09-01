"""Node: executa funcao Python inline."""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from orchestrator.models import NodeDef, NodeResult, NodeStatus
from orchestrator.nodes.base import BaseNode, NodeError


class PythonNode(BaseNode):
    """Executa código Python inline definido no workflow."""

    type_name = "python"

    async def execute(self) -> NodeResult:
        started = datetime.utcnow()
        code = self.definition.config.get("code", "")

        # Prepara contexto com outputs dos nodes anteriores
        input_data = None
        if self.definition.input:
            raw = self.resolve_template(self.definition.input)
            try:
                import json as _json
                input_data = _json.loads(raw) if isinstance(raw, str) else raw
            except Exception:
                input_data = raw

        # Resolve templates no próprio código
        if "{{" in code:
            code = self.resolve_template(code)

        # Cria namespace de execução
        ns: dict[str, Any] = {"data": input_data}

        try:
            exec(code, ns)
            output = ns.get("result", ns.get("data"))
            return NodeResult(
                node_id=self.definition.id,
                status=NodeStatus.DONE,
                output=output,
                started_at=started,
                finished_at=datetime.utcnow(),
                metadata={"has_code": bool(code)},
            )
        except Exception as exc:
            return NodeResult(
                node_id=self.definition.id,
                status=NodeStatus.FAILED,
                error=f"{type(exc).__name__}: {exc}",
                started_at=started,
                finished_at=datetime.utcnow(),
            )
