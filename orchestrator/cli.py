"""CLI com Click + Rich output."""
from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from orchestrator.engine import WorkflowEngine
from orchestrator.loader import load_yaml
from orchestrator.models import ExecutionRecord, NodeStatus

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Workflow Orchestrator — DAG engine para automacoes."""
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


@cli.command("run")
@click.argument("workflow_file", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Salvar resultado em JSON")
def run(workflow_file, output):
    """Executa um workflow definido em YAML."""
    console.print(f"[blue]Carregando workflow:[/blue] {workflow_file}")
    try:
        workflow = load_yaml(workflow_file)
    except Exception as exc:
        console.print(f"[red]Erro ao carregar: {exc}[/red]")
        sys.exit(1)

    console.print(f"  → [bold]{workflow.name}[/bold]: {workflow.description or '(sem descrição)'}")
    console.print(f"  → {len(workflow.nodes)} nodes")

    engine = WorkflowEngine()
    record = asyncio.run(engine.execute(workflow))

    # ── Renderiza resultado ────────────────────────────────────────────
    render_execution(record)

    # Salva em JSON se pedido
    if output:
        record_dict = {
            "workflow": record.workflow_name,
            "status": record.status.value,
            "duration_s": record.duration_s,
            "started_at": record.started_at.isoformat(),
            "finished_at": record.finished_at.isoformat() if record.finished_at else None,
            "nodes": {
                nid: {
                    "status": r.status.value,
                    "duration_ms": r.duration_ms,
                    "attempts": r.attempts,
                    "output": r.output if r.output else None,
                    "error": r.error,
                }
                for nid, r in record.node_results.items()
            },
        }
        with open(output, "w") as f:
            json.dump(record_dict, f, indent=2, default=str, ensure_ascii=False)
        console.print(f"[green]✅ Resultado salvo em {output}[/green]")

    if record.status.value == "FAILED":
        sys.exit(1)


@cli.command("validate")
@click.argument("workflow_file", type=click.Path(exists=True))
def validate(workflow_file):
    """Valida um workflow sem executar."""
    from orchestrator.dag import validate_dag
    try:
        workflow = load_yaml(workflow_file)
        warnings = validate_dag(workflow)
        console.print(f"[green]✅ Workflow '{workflow.name}' válido[/green]")
        console.print(f"  → {len(workflow.nodes)} nodes")
        for w in warnings:
            console.print(f"  [yellow]⚠ {w}[/yellow]")
    except Exception as exc:
        console.print(f"[red]❌ {exc}[/red]")
        sys.exit(1)


def render_execution(record: ExecutionRecord) -> None:
    """Renderiza o resultado de uma execucao com Rich."""
    status_emoji = {
        "COMPLETED": "✅",
        "FAILED": "❌",
        "RUNNING": "🔄",
    }
    panel_text = (
        f"[bold]Workflow:[/bold] {record.workflow_name}\n"
        f"[bold]Status:[/bold] {status_emoji.get(record.status.value, '?')} {record.status.value}\n"
        f"[bold]Duração:[/bold] {record.duration_s:.2f}s\n"
        f"[bold]Nodes:[/bold] {len(record.node_results)}\n"
    )
    console.print(Panel(panel_text, title="[bold]Execução[/bold]", expand=False))

    # Tabela de nodes
    table = Table(show_lines=True)
    table.add_column("Node", style="bold")
    table.add_column("Status")
    table.add_column("Duration")
    table.add_column("Attempts")
    table.add_column("Detail")

    status_style = {
        NodeStatus.DONE: "[green]DONE[/green]",
        NodeStatus.FAILED: "[red]FAILED[/red]",
        NodeStatus.SKIPPED: "[yellow]SKIPPED[/yellow]",
        NodeStatus.RUNNING: "[blue]RUNNING[/blue]",
        NodeStatus.PENDING: "[dim]PENDING[/dim]",
    }
    for nid, r in record.node_results.items():
        dur = f"{r.duration_ms:.0f}ms" if r.duration_ms else "-"
        detail = r.error or (str(r.output)[:60] if r.output else "")
        table.add_row(nid, status_style.get(r.status, r.status.value), dur, str(r.attempts), detail)
    console.print(table)


if __name__ == "__main__":
    cli()
