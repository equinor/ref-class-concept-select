# AGENTS.md

Instructions for any LLM agent working in this repository. Keep this file short;
detail lives in the files it points to.

## Mission

Build a methodology for analysing petroleum field-development projects as a
sequence of decisions: what was decided, when, on which information and
assumptions, and how well the estimates held up. The open Volve field data is
the test case. Decisions are structured as decision models (decision trees,
influence diagrams); reference class forecasting supplies the outside view.

## Domains

Each domain has a folder, a charter and one responsible agent. Read the charter
before working in a domain.

| Domain | Folder | Responsibility | Charter |
|---|---|---|---|
| sys | `agents/sys/` | Organisation, conventions, integration, QA | `agents/sys/README.md` |
| doc | `agents/doc/` | Document conversion, data extraction, reports | `agents/doc/README.md` |
| sim | `agents/sim/` | Reservoir simulation runs and analysis | `agents/sim/README.md` |
| dmx | `agents/dmx/` | Decision structuring and decision models | `agents/dmx/README.md` |
| rcf | `agents/rcf/` | Reference class forecasting | `agents/rcf/README.md` |

Anything about layout, naming, hand-offs, provenance or quality checks is
governed by `agents/sys/GUIDELINES.md`. If it does not cover your case, follow
its "when the guidelines are silent" procedure rather than inventing a local rule.

## Rules that always apply

1. **Raw data is read-only.** Source data lives outside the repo in
   `../volve_data` (override with the `VOLVE_DATA` environment variable). Never
   modify, move or delete anything there. The only files added there are the
   generated `_FLOW` deck files (guidelines §3). Converted documents go in the
   repository under `data/volve/`.
2. **Every number has a source.** A value taken from a document, a simulation
   or a public table is recorded as a fact in `data/facts/` with where it came
   from (file, page or table/figure or vector name), its unit, and how it was
   obtained. Values that are assumed or inferred are labelled so and are not
   facts.
3. **Report what the source says.** Do not fill gaps with plausible values. If
   a document gives no alternatives, pros/cons or probabilities, say so.
4. **Stay in your lane when writing.** Read anywhere; write only in your own
   domain folder and in the shared locations the guidelines assign to you.
5. **Estimates are time-stamped.** Always state the date of the knowledge an
   estimate reflects (e.g. PDO 2005 vs. history-matched model 2016). Never use
   later information to describe what was known at an earlier decision.
6. **`logs/` belongs to the user.** Do not edit the prompt logs.
7. **Check before you claim.** State what was verified and how; flag what was
   not. `make check` must pass before a commit.

## Commands

| Command | Effect |
|---|---|
| `make setup` | Install the environment (all domains); `uv sync --group <domain>` for one |
| `make check` | Verify raw data against the manifest, validate facts, run tests and lint |
| `uv run <command>` | Run anything inside the environment |

## Key documents

- `docs/background.txt` — the Volve field and the local dataset.
- `docs/data-sources.md` — local data inventory and public sources, with
  retrieval recipes.
- `data/README.md` — the shared data: manifest, sources, Sodir snapshots, fact
  register, converted documents.
- `docs/startup-assessment.md` — feasibility assessment, infrastructure
  specification and development plan.
