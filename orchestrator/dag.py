"""
Validação e ordenação topológica de DAGs.
Detecta ciclos, nodes órfãos e referências quebradas.
"""
from __future__ import annotations

from orchestrator.models import NodeDef, WorkflowDef


class DAGValidationError(Exception):
    """Raised quando o DAG tem problemas estruturais."""


def validate_dag(workflow: WorkflowDef) -> list[str]:
    """
    Valida um workflow e retorna lista de warnings.
    Raises DAGValidationError se encontrar erros fatais.
    """
    errors: list[str] = []
    warnings: list[str] = []

    node_ids = {n.id for n in workflow.nodes}
    node_map = {n.id: n for n in workflow.nodes}

    # ── 1. IDs duplicados ────────────────────────────────────────────────
    if len(node_ids) != len(workflow.nodes):
        seen: set[str] = set()
        for n in workflow.nodes:
            if n.id in seen:
                errors.append(f"ID duplicado: '{n.id}'")
            seen.add(n.id)

    # ── 2. depends_on referencia inexistente ────────────────────────────
    for node in workflow.nodes:
        for dep in node.depends_on:
            if dep not in node_ids:
                errors.append(
                    f"Node '{node.id}' depende de '{dep}' que não existe"
                )

    # ── 3. Auto-dependência ───────────────────────────────────────────
    for node in workflow.nodes:
        if node.id in node.depends_on:
            errors.append(f"Node '{node.id}' depende de si mesmo")

    # ── 4. Ciclo (via DFS) ───────────────────────────────────────────
    cycle = _find_cycle(workflow)
    if cycle:
        errors.append(f"Ciclo detectado: {' -> '.join(cycle)}")

    if errors:
        raise DAGValidationError("\n".join(errors))

    return warnings


def _find_cycle(workflow: WorkflowDef) -> list[str] | None:
    """
    DFS coloração: branco/cinza/preto.
    Retorna a lista de nodes do ciclo, ou None se não há ciclo.
    """
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {n.id: WHITE for n in workflow.nodes}
    parent: dict[str, str | None] = {n.id: None for n in workflow.nodes}

    def dfs(node_id: str) -> list[str] | None:
        color[node_id] = GRAY
        node = next((n for n in workflow.nodes if n.id == node_id), None)
        if node:
            for dep in node.depends_on:
                if color[dep] == GRAY:
                    # Ciclo encontrado — reconstrói o caminho
                    cycle = [dep, node_id]
                    cur = node_id
                    while parent[cur] is not None:
                        p = parent[cur]
                        cycle.append(p)
                        if p == dep:
                            break
                        cur = p
                    return list(reversed(cycle))
                elif color[dep] == WHITE:
                    parent[dep] = node_id
                    result = dfs(dep)
                    if result:
                        return result
        color[node_id] = BLACK
        return None

    for node in workflow.nodes:
        if color[node.id] == WHITE:
            result = dfs(node.id)
            if result:
                return result
    return None


def topological_order(workflow: WorkflowDef) -> list[NodeDef]:
    """
    Retorna nodes em ordem topológica (dependências primeiro).
    Raises se o DAG tem ciclo.
    """
    validate_dag(workflow)

    # Kahn's algorithm
    in_degree: dict[str, int] = {n.id: 0 for n in workflow.nodes}
    dependents: dict[str, list[str]] = {n.id: [] for n in workflow.nodes}

    for node in workflow.nodes:
        for dep in node.depends_on:
            in_degree[node.id] += 1
            dependents[dep].append(node.id)

    # Nodes sem dependências — entrada do grafo
    queue = [n.id for n in workflow.nodes if in_degree[n.id] == 0]
    ordered: list[str] = []

    while queue:
        node_id = queue.pop(0)
        ordered.append(node_id)
        for dependent in dependents[node_id]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

    if len(ordered) != len(workflow.nodes):
        raise DAGValidationError("Não foi possível ordernar — grafo tem ciclo residual")

    node_map = {n.id: n for n in workflow.nodes}
    return [node_map[i] for i in ordered]
