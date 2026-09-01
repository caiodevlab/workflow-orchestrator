# ⚡ Workflow Orchestrator

> **Engine Python leve para executar DAGs de automacao com retry, idempotencia, logs estruturados e painel CLI. Inspirado no n8n — mas construido do zero, com foco em robustez e testabilidade.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status: Em desenvolvimento](https://img.shields.io/badge/Status-Em%20Desenvolvimento-orange)]()

---

## 📌 O problema

Automações com scripts soltos falham silenciosamente, não têm retry, não guardam estado, e é impossível saber o que rodou e quando.

Ferramentas como n8n são ótimas — mas são **plataformas**. Às vezes você quer só um **motor leve** embeddado no seu código Python.

## 💡 A solução

Um **workflow engine em Python puro** que:

- 📋 Define workflows como DAGs em YAML ou Python
- 🔄 Retry inteligente com backoff exponencial
- ✅ Idempotência — rodar 2x não quebra nada
- 📊 Logs estruturados por step (sucesso, falha, tempo)
- 🖥️ CLI com painel visual do estado do workflow
- 🔌 Nodes plugáveis — você escreve o que cada passo faz

---

## ⚡ Features

- 🔀 **DAG execution** — ordem topológica, detecção de ciclos
- 🔁 **Retry com backoff** — exponencial, com max_attempts e delay
- 💾 **State persistence** — opcional, SQLite ou Redis
- 🛡️ **Idempotency keys** — cada step gera uma key, re-roda não duplica
- 📊 **Execution history** — quem rodou, quanto tempo, quantos retries
- 🖥️ **CLI dashboard** — tabela colorida com status dos workflows
- 🔌 **Node system** — hooks para HTTP, Shell, Python functions, sleep, etc.
- 📝 **YAML + Python DSL** — defina workflows em YAML ou code

---

## 🛠️ Stack

| Camada | Tecnologia |
|---|---|
| **Runtime** | Python 3.10+ |
| **Async** | `asyncio` |
| **CLI** | `click` + `rich` |
| **State** | `SQLAlchemy` (SQLite por padrão) |
| **YAML** | `pyyaml` |
| **Testing** | `pytest`, `pytest-asyncio` |

---

## 📂 Estrutura

```
workflow-orchestrator/
├── orchestrator/
│   ├── __init__.py
│   ├── engine.py         # DAG executor com retry e idempotencia
│   ├── dag.py            # Modelo DAG (nodes, edges, topological sort)
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── base.py       # Node base class
│   │   ├── http.py       # Node: HTTP GET/POST
│   │   ├── shell.py      # Node: executa shell command
│   │   ├── python.py     # Node: executa funcao Python
│   │   └── sleep.py      # Node: delay
│   ├── state.py          # Persistencia de estado (SQLAlchemy)
│   ├── cli.py            # Click CLI
│   └── models.py         # Dataclasses: Workflow, Node, Execution
├── workflows/
│   └── exemplo.yml       # Exemplos de workflows em YAML
├── tests/
│   ├── test_dag.py
│   ├── test_engine.py
│   └── test_nodes.py
├── requirements.txt
└── README.md
```

---

## 🚀 Como usar

### Defina um workflow em YAML

```yaml
# workflows/exemplo-notificacao.yml
name: notificacao-diária
description: Coleta metricas, analisa e envia alerta se threshold excedido

nodes:
  - id: fetch_metrics
    type: http
    config:
      url: "https://api.seuservico.com/metrics"
      method: GET

  - id: check_threshold
    type: python
    input: "{{ fetch_metrics.body }}"
    config:
      code: |
        value = float(data["cpu_usage"])
        return {"alert": value > 80, "value": value}

  - id: send_alert
    type: http
    input: "{{ check_threshold }}"
    condition: "{{ check_threshold.alert }} == true"
    config:
      url: "https://notify.example.com/alert"
      method: POST
      body: "CPU em {{ check_threshold.value }}% — acima do threshold!"
```

### Execute via CLI

```bash
python -m orchestrator.cli run workflows/exemplo-notificacao.yml
```

### Saída:

```
╔══════════════════════════════════════════════════════════════╗
║  Workflow: notificacao-diária        Status: ✅ COMPLETED  ║
╠══════════════════════════════════════════════════════════════╣
║  Step                  Status    Duration  Retries         ║
║  ─────────────────────────────────────────────────────────  ║
║  fetch_metrics         ✅ OK     1.2s      0                ║
║  check_threshold       ✅ OK     0.01s    0                ║
║  send_alert            ✅ OK     0.8s      0                ║
╠══════════════════════════════════════════════════════════════╣
║  Total: 2.01s   Completed: 3/3   Failed: 0                 ║
╚══════════════════════════════════════════════════════════════╝
```

### Painel de status

```bash
# Lista workflows e execucoes
python -m orchestrator.cli list

# Historico de uma execucao
python -m orchestrator.cli history notificacao-diária

# Dashboard ao vivo
python -m orchestrator.cli dashboard
```

---

## 🎯 O que aprendi com este projeto

- **DAGs e grafos** — ordenação topológica, detecção de ciclos
- **Async Python** — asyncio, run_in_executor, concurrent futures
- **Retry com backoff** — exponencial, com jitter
- **Idempotência** — determinismo, dedup keys, safe retry
- **State machines** — modelos de execução (PENDING → RUNNING → DONE/FAILED)
- **SQLAlchemy** — ORM para persistence de estado
- **Arquitetura plugável** — estratégia pattern para nodes
- **CLI testável** — Click com mocks

---

## 📝 Licença

MIT — use, modifique, distribua.

---

<p align="center">
  Feito com ☕ por <a href="https://github.com/caiodevlab">@caiodevlab</a>
</p>
