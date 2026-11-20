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
| Read the converted source documents | `data/volve/reports/md/` |

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
  doc/             document conversion, extraction, reports (dockit; skill; out/ has the
                   analyses and the plan-versus-outcome report)
  sim/             reservoir simulation and analysis (simkit; Flow version of the deck)
  dmx/             decision structuring and models
  rcf/             reference class forecasting (rcfkit; skill; lib/ reference papers;
                   study/ the expert's study; out/ the review and the study)
data/              manifest of raw data, Sodir snapshots, fact register,
                   converted documents
docs/              background, data sources, assessment and plan
logs/              user prompt logs, one file per machine
pyproject.toml     environment: one dependency group per domain (uv.lock pins it)
Makefile           setup, check and data commands
```

## Status

The infrastructure is in place, the simulation deck runs in OPM Flow, and the
two source documents are converted and analysed:

- [`agents/doc/out/Volve_PUD_cmt_anlz.md`](agents/doc/out/Volve_PUD_cmt_anlz.md) — the 2005
  development plan: concept selection, production strategy, uncertainties
- [`agents/doc/out/Discovery_report_anlz.md`](agents/doc/out/Discovery_report_anlz.md) — the
  1993 discovery report
- [`agents/doc/out/volve-pdo-vs-actual/index.html`](agents/doc/out/volve-pdo-vs-actual/index.html)
  — the plan against the outcome (open in a browser)

A reference class study of the Norwegian shelf record is done as well:

- [`agents/rcf/out/expert-study-review.md`](agents/rcf/out/expert-study-review.md) — review of
  the expert's study in `agents/rcf/study`
- [`agents/rcf/out/volve-rcf-study.md`](agents/rcf/out/volve-rcf-study.md) — the study redone:
  probability of discovery, volumes, reserves and production against outcomes, and Volve in
  that record (web pages in the folders of the same names)

Next is the first step of dmx; see
[`docs/startup-assessment.md`](docs/startup-assessment.md) §7–8.

## Attribution

Volve data: Equinor ASA and the former Volve licence partners. Field statistics:
Norwegian Offshore Directorate (Sodir).
