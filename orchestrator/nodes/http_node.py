"""Node: HTTP request (GET/POST)."""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from orchestrator.models import NodeDef, NodeResult, NodeStatus
from orchestrator.nodes.base import BaseNode, NodeError

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


class HTTPNode(BaseNode):
    """Faz request HTTP — GET, POST, PUT, DELETE."""

    type_name = "http"

    async def execute(self) -> NodeResult:
        started = datetime.utcnow()

        if not HAS_HTTPX:
            return NodeResult(
                node_id=self.definition.id,
                status=NodeStatus.FAILED,
                error="httpx nao instalado — pip install httpx",
                started_at=started,
                finished_at=datetime.utcnow(),
            )

        url = self.definition.config.get("url", "")
        method = self.definition.config.get("method", "GET").upper()
        headers = self.definition.config.get("headers", {})
        body = self.definition.config.get("body")
        timeout = self.definition.config.get("timeout", 30)

        # Resolve templates
        if "{{" in url:
            url = self.resolve_template(url)
        if body and "{{" in str(body):
            body = self.resolve_template(body)

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                resp = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=body if method != "GET" else None,
                    params=self.definition.config.get("params"),
                )
                try:
                    resp_json = resp.json()
                except Exception:
                    resp_json = {"_raw": resp.text[:500]}

                return NodeResult(
                    node_id=self.definition.id,
                    status=NodeStatus.DONE if resp.status_code < 500 else NodeStatus.FAILED,
                    output={
                        "status_code": resp.status_code,
                        "body": resp_json,
                        "headers": dict(resp.headers),
                    },
                    error=None if resp.status_code < 500 else f"HTTP {resp.status_code}",
                    started_at=started,
                    finished_at=datetime.utcnow(),
                    metadata={"url": url[:100], "method": method},
                )
            except httpx.TimeoutException:
                return NodeResult(
                    node_id=self.definition.id,
                    status=NodeStatus.FAILED,
                    error=f"Timeout ({timeout}s) em {method} {url}",
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
