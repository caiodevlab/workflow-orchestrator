"""Registry de node types — factory pattern."""
from __future__ import annotations

from orchestrator.nodes.base import BaseNode
from orchestrator.nodes.sleep import SleepNode
from orchestrator.nodes.shell import ShellNode
from orchestrator.nodes.python_func import PythonNode
from orchestrator.nodes.http_node import HTTPNode

# Registry global: type_name -> class
NODE_REGISTRY: dict[str, type[BaseNode]] = {
    "sleep": SleepNode,
    "shell": ShellNode,
    "python": PythonNode,
    "http": HTTPNode,
}


def register_node(type_name: str, node_class: type[BaseNode]) -> None:
    """Registra um novo tipo de node (para extensibilidade)."""
    NODE_REGISTRY[type_name] = node_class


def get_node_class(type_name: str) -> type[BaseNode]:
    """Retorna a classe do node pelo type_name. Levanta KeyError."""
    if type_name not in NODE_REGISTRY:
        available = ", ".join(sorted(NODE_REGISTRY.keys()))
        raise KeyError(
            f"Tipo de node desconhecido: '{type_name}'. "
            f"Disponíveis: {available}. "
            f"Registre com orchestrator.register_node()."
        )
    return NODE_REGISTRY[type_name]
