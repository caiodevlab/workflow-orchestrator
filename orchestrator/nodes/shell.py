"""Node: executa comando shell."""
from __future__ import annotations

import asyncio
import shlex
from datetime import datetime
from typing import Any

from orchestrator.models import NodeDef, NodeResult, NodeStatus
from orchestrator.nodes.base import BaseNode, NodeError


class ShellNode(BaseNode):
    """Executa um comando shell via subprocess."""

    type_name = "shell"

    async def execute(self) -> NodeResult:
        started = datetime.utcnow()
        cmd = self.definition.config.get("command", "")
        timeout = self.definition.config.get("timeout", 300)

        # Resolve templates no comando
        if "{{" in cmd:
            cmd = self.resolve_template(cmd)

        cwd = self.definition.config.get("cwd")

        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
            stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
            stderr = stderr_bytes.decode("utf-8", errors="replace").strip()
            return NodeResult(
                node_id=self.definition.id,
                status=NodeStatus.DONE if proc.returncode == 0 else NodeStatus.FAILED,
                output={"stdout": stdout, "stderr": stderr, "exit_code": proc.returncode},
                error=None if proc.returncode == 0 else stderr or "Exit code non-zero",
                started_at=started,
                finished_at=datetime.utcnow(),
                metadata={"command": cmd[:200]},
            )
        except asyncio.TimeoutError:
            return NodeResult(
                node_id=self.definition.id,
                status=NodeStatus.FAILED,
                error=f"Timeout after {timeout}s",
                started_at=started,
                finished_at=datetime.utcnow(),
            )
        except Exception as exc:
            return NodeResult(
                node_id=self.definition.id,
                status=NodeStatus.FAILED,
                error=str(exc),
                started_at=started,
                finished_at=datetime.utcnow(),
            )
