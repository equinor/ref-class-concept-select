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

The two come together in a first decision analysis:

- [`agents/dmx/out/volve-concept-basis.md`](agents/dmx/out/volve-concept-basis.md) — the Volve
  concept selection on a volume basis recalibrated with the reference class (web page in the
  folder of the same name)

An overview for presentation — the workflow, the agents, the first use and the main
results — is the slide deck
[`agents/sys/out/workflow-deck/index.html`](agents/sys/out/workflow-deck/index.html) (open
in a browser; arrow keys to move, F for full screen). Its diagrams are also separate files
in `figs/`. The results presentation is
[`agents/sys/out/rcf_volve_v2/index.html`](agents/sys/out/rcf_volve_v2/index.html), made from
`rcf_volve_v2.pptx`; the same ten slides as a PowerPoint file are in
[`agents/sys/out/rcf_volve_v2_extended.pptx`](agents/sys/out/rcf_volve_v2_extended.pptx).

Next is the full decision model of the concept choice; see
[`docs/startup-assessment.md`](docs/startup-assessment.md) §7–8.

## Layout

```
AGENTS.md          rules loaded by every agent session
.github/agents/    Copilot CLI profile per domain
agents/
  sys/             organisation, conventions, integration, QA; shared code (syskit)
  doc/             document conversion, extraction, reports (dockit; skill; out/ has the
                   analyses and the plan-versus-outcome report)
  sim/             reservoir simulation and analysis (simkit; Flow version of the deck)
  dmx/             decision structuring and models (dmxkit; out/ the concept analysis)
  rcf/             reference class forecasting (rcfkit; skill; lib/ reference papers;
                   study/ the expert's study; out/ the review and the study)
data/              manifest of raw data, Sodir snapshots, fact register,
                   converted documents
volve/             volve data, PUD, eclipse deck, production data
Makefile           setup, check and data commands
```

## Attribution

Volve data: Equinor ASA and the former Volve licence partners. Field statistics:
Norwegian Offshore Directorate (Sodir).
