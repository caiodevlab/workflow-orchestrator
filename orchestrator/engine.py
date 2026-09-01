"""
Engine principal — executa um workflow respeitando dependências,
com retry/backoff, idempotência e logging estruturado.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

from orchestrator.dag import DAGValidationError, topological_order
from orchestrator.models import (
    ExecutionRecord,
    ExecutionStatus,
    NodeDef,
    NodeResult,
    NodeStatus,
    WorkflowDef,
)
from orchestrator.nodes.base import BaseNode, NodeError
from orchestrator.nodes.registry import get_node_class

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """Motor que executa um workflow."""

    def __init__(self, max_concurrent: int = 1):
        self.max_concurrent = max_concurrent
        self.context: dict[str, Any] = {}  # node_id -> output

    async def execute(self, workflow: WorkflowDef) -> ExecutionRecord:
        """Executa o workflow e retorna o registro completo."""
        # ── Valida DAG ─────────────────────────────────────────────
        try:
            order = topological_order(workflow)
        except DAGValidationError as exc:
            return ExecutionRecord(
                workflow_name=workflow.name,
                status=ExecutionStatus.FAILED,
                started_at=datetime.utcnow(),
                finished_at=datetime.utcnow(),
                metadata={"error": str(exc)},
            )

        record = ExecutionRecord(
            workflow_name=workflow.name,
            status=ExecutionStatus.RUNNING,
            started_at=datetime.utcnow(),
        )

        logger.info(f"[{workflow.name}] Iniciando — {len(order)} nodes")

        # ── Executa nodes em ordem topológica ───────────────────────
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def run_node(node_def: NodeDef) -> None:
            async with semaphore:
                await self._run_with_retry(node_def, record)

        # Em vez de executar em paralelo por padrão (max_concurrent=1),
        # respeitamos ordem topológica para garantir dependencias.
        if self.max_concurrent == 1:
            for node_def in order:
                await self._run_with_retry(node_def, record)
        else:
            # Parallel: agrupa por nivel topologico
            await self._run_parallel(order, semaphore, record)

        # ── Status final ────────────────────────────────────────────
        if any(r.status == NodeStatus.FAILED for r in record.node_results.values()):
            record.status = ExecutionStatus.FAILED
        else:
            record.status = ExecutionStatus.COMPLETED
        record.finished_at = datetime.utcnow()

        logger.info(
            f"[{workflow.name}] Finalizado — status={record.status.value}, "
            f"duracao={record.duration_s:.2f}s"
        )
        return record

    async def _run_with_retry(
        self, node_def: NodeDef, record: ExecutionRecord
    ) -> None:
        """Executa um node com retry e backoff."""
        max_attempts = 1
        delay = 0
        backoff = 1.0
        if node_def.retry:
            max_attempts = node_def.retry.get("max_attempts", 1)
            delay = node_def.retry.get("delay", 0)
            backoff = node_def.retry.get("backoff", 1.0)

        attempts = 0
        result: NodeResult | None = None

        while attempts < max_attempts:
            attempts += 1
            try:
                node_class = get_node_class(node_def.type)
                node: BaseNode = node_class(node_def, self.context)
            except KeyError as exc:
                result = NodeResult(
                    node_id=node_def.id,
                    status=NodeStatus.FAILED,
                    error=str(exc),
                    attempts=attempts,
                )
                break

            # Verifica condition
            try:
                should = await node.should_run()
            except Exception as exc:
                result = NodeResult(
                    node_id=node_def.id,
                    status=NodeStatus.FAILED,
                    error=f"Condition evaluation failed: {exc}",
                    attempts=attempts,
                )
                break

            if not should:
                result = NodeResult(
                    node_id=node_def.id,
                    status=NodeStatus.SKIPPED,
                    error="condition=false",
                    attempts=attempts,
                )
                break

            # Executa
            try:
                result = await node.execute()
                result.attempts = attempts
            except Exception as exc:
                result = NodeResult(
                    node_id=node_def.id,
                    status=NodeStatus.FAILED,
                    error=f"{type(exc).__name__}: {exc}",
                    attempts=attempts,
                )

            if result.status == NodeStatus.DONE:
                self.context[node_def.id] = result.output
                break

            # Falhou — retry?
            if attempts >= max_attempts:
                break

            if delay > 0:
                await asyncio.sleep(delay)
            delay = int(delay * backoff) if backoff > 1 else delay
            logger.warning(
                f"[{node_def.id}] tentativa {attempts}/{max_attempts} falhou, "
                f"retry em {delay}s"
            )

        assert result is not None
        record.node_results[node_def.id] = result

    async def _run_parallel(
        self,
        order: list[NodeDef],
        semaphore: asyncio.Semaphore,
        record: ExecutionRecord,
    ) -> None:
        """Executa nodes em paralelo respeitando topological order."""
        remaining = list(order)
        in_progress: set[asyncio.Task] = set()

        while remaining or in_progress:
            # Pega nodes cujas dependências já terminaram
            done_ids = {n.id for n in order if n.id in record.node_results}
            ready = [
                n for n in remaining
                if all(dep in done_ids for dep in n.depends_on)
            ]
            for node in ready:
                task = asyncio.create_task(self._run_with_retry(node, record))
                in_progress.add(task)

            # Remove tasks que terminaram
            if in_progress:
                done, _pending = await asyncio.wait(
                    in_progress, return_when=asyncio.FIRST_COMPLETED
                )
                in_progress -= done

            # Remove dos remaining os que tem record
            completed_ids = {n.id for n in order if n.id in record.node_results}
            remaining = [n for n in remaining if n.id not in completed_ids]
