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

## Layout

```
AGENTS.md          rules loaded by every agent session
agents/
  sys/             organisation, conventions, integration, QA
  doc/             document conversion, extraction, reports
  sim/             reservoir simulation and analysis
  dmx/             decision structuring and models
  rcf/             reference class forecasting (lib/ holds reference papers)
docs/              background, data sources, assessment and plan
logs/              user prompt logs, one file per machine
```

Source data is not in this repository. It is expected in `../volve_data`
(see `docs/data-sources.md`).

## Status

Foundation stage. The assessment and development plan are awaiting approval;
the environment, tooling and agent profiles described there are not yet built.

## Attribution

Volve data: Equinor ASA and the former Volve licence partners. Field statistics:
Norwegian Offshore Directorate (Sodir).
