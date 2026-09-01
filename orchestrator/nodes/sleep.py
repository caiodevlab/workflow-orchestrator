"""Node: delay/sleep."""
from __future__ import annotations

import asyncio
from datetime import datetime

from orchestrator.models import NodeDef, NodeResult, NodeStatus
from orchestrator.nodes.base import BaseNode


class SleepNode(BaseNode):
    """Aguarda um tempo antes de continuar."""

    type_name = "sleep"

    async def execute(self) -> NodeResult:
        delay = self.definition.config.get("seconds", 1)
        started = datetime.utcnow()
        try:
            await asyncio.sleep(delay)
            return NodeResult(
                node_id=self.definition.id,
                status=NodeStatus.DONE,
                output={"slept_seconds": delay},
                started_at=started,
                finished_at=datetime.utcnow(),
            )
        except asyncio.CancelledError:
            return NodeResult(
                node_id=self.definition.id,
                status=NodeStatus.FAILED,
                error="Cancelled",
                started_at=started,
                finished_at=datetime.utcnow(),
            )
