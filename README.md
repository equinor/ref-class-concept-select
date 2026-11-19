# ref-class-concept-select

Methodology for analysing petroleum field-development decisions, developed on
the open Volve field dataset. The work identifies the core decisions of a
project, the information and assumptions behind them, structures selected
decisions as decision models, and uses reference class forecasting to challenge
the project's own estimates with an outside view.

The work is carried out by five domain agents, each with its own folder and
charter, coordinated by a common set of guidelines.

## Where to start

| If you want to | Read |
|---|---|
| Understand the plan and its status | [`docs/startup-assessment.md`](docs/startup-assessment.md) |
| Know what data exists and how to get more | [`docs/data-sources.md`](docs/data-sources.md) |
| Know the rules every agent follows | [`AGENTS.md`](AGENTS.md), [`agents/sys/GUIDELINES.md`](agents/sys/GUIDELINES.md) |
| Work in a domain | `agents/<domain>/README.md` |
| Use the shared data | [`data/README.md`](data/README.md) |

## Setup

Requires [`uv`](https://docs.astral.sh/uv/) and the raw Volve data in
`../volve_data` (or wherever `VOLVE_DATA` points; see
[`docs/data-sources.md`](docs/data-sources.md)).

```bash
make setup    # install the environment, all domains
make check    # verify raw data against the manifest, validate facts, test, lint
```

To work as a domain agent in Copilot CLI: `copilot --agent doc` (or `sys`,
`sim`, `dmx`, `rcf`), or `/agent` inside a session.

## Layout

```
AGENTS.md          rules loaded by every agent session
.github/agents/    Copilot CLI profile per domain
agents/
  sys/             organisation, conventions, integration, QA; shared code (syskit)
  doc/             document conversion, extraction, reports
  sim/             reservoir simulation and analysis
  dmx/             decision structuring and models
  rcf/             reference class forecasting (lib/ holds reference papers)
data/              manifest of raw data, Sodir snapshots, fact register,
                   converted documents
docs/              background, data sources, assessment and plan
logs/              user prompt logs, one file per machine
pyproject.toml     environment: one dependency group per domain (uv.lock pins it)
Makefile           setup, check and data commands
```

## Status

The infrastructure (Phase 1 of the plan) is in place. Next are the first steps
in each domain, starting with doc; see
[`docs/startup-assessment.md`](docs/startup-assessment.md) §7–8.

## Attribution

Volve data: Equinor ASA and the former Volve licence partners. Field statistics:
Norwegian Offshore Directorate (Sodir).
