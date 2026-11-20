# Guidelines for all agents

Maintained by sys. These rules exist so that one person can run, audit and
resume the whole workflow without relying on memory.

## 1. Principles

1. **Traceable.** Any number in a deliverable can be followed back to a page,
   a table, a simulation vector or a public record.
2. **Reproducible.** A derived artifact can be regenerated from raw data, a
   script or documented procedure, and pinned tool versions.
3. **Time-aware.** Information is tagged with the date of the knowledge it
   represents, so a decision is only ever evaluated against what was known then.
4. **Plain files.** Markdown, CSV, YAML, XLSX, PNG. No databases or services to
   maintain.
5. **Small surface.** Add a tool, folder or convention only when a task needs
   it.

## 2. Layout and ownership

| Location | Writes | Content |
|---|---|---|
| `AGENTS.md`, `README.md`, `docs/`, `.github/`, `pyproject.toml`, `uv.lock`, `Makefile` | sys | Rules, overview, plan, agent profiles, environment |
| `agents/<domain>/` | that domain | Charter, procedures, code, deliverables |
| `data/manifest.csv`, `data/sources.csv`, `data/sodir/`, `data/npd_archive/`, `data/public/` | sys | Raw-data inventory, source catalogue, public snapshots, archived web captures |
| `data/volve/` | doc | Converted documents and figure cut-outs |
| `data/facts/<source-id>.csv` | the domain that reads that source: doc for documents, sim for `sim2016`, sys for `sodir` and `npd_archive` | Fact register |
| `logs/` | user | Prompt logs; agents do not edit |
| `$VOLVE_DATA` (default `../volve_data`) | user; sim for `_FLOW` deck files (§3) | Raw data, read-only; generated deck files |

Agents read anywhere and write only where this table lets them.

Inside a domain folder:

| Path | Versioned | Content |
|---|---|---|
| `README.md` | yes | Charter: role, inputs, outputs, procedures |
| `GUIDELINE_<topic>.md` | yes | Procedures learned from completed work |
| `src/` | yes | Scripts and modules |
| `tests/` | yes | Tests for `src/` |
| `out/` | yes | Deliverables |
| `work/` | no | Scratch; safe to delete at any time |
| `lib/` | yes | Reference literature; converted copies in `lib/md/`, their figures in `lib/figs/` |
| `study/` | yes | Work delivered by others, kept as delivered: read, never edited or reformatted |
| `skills/<name>/` | yes | A procedure packaged as a skill (`SKILL.md` and its reference files) |

A skill is linked from `.github/skills/<name>` so that Copilot CLI finds it;
the files stay in the domain folder. `copilot skill list` shows what is found.

## 3. Data

- **Raw data** stays in `$VOLVE_DATA`, unmodified. Code gets the location
  from `syskit.paths.volve_data()`, which reads the `VOLVE_DATA` environment
  variable and falls back to `../volve_data` relative to the repository root.
  No absolute paths in versioned files.
- **Generated deck files** are the one thing written to `$VOLVE_DATA`: new
  versions of simulation input files, placed beside the originals so that the
  unchanged include files are shared. They carry `_FLOW` before the extension,
  are written only by `simkit.flow_deck` (`make flow-deck`), never by hand, and
  never replace an original. Simulation output does not go there; it goes to
  `agents/sim/work/`.
- **Manifest.** `data/manifest.csv` lists every file in `$VOLVE_DATA` with
  size and SHA-256: the raw files and the generated `_FLOW` files. `make
  manifest-verify` confirms a machine holds the same files. On a machine where
  the `_FLOW` files are reported missing, run `make flow-deck`; it reproduces
  them exactly. After changing `simkit.flow_deck`, run `make flow-deck` and
  `make manifest`.
- **Adding a raw source:** put the file in `$VOLVE_DATA`, give it an ID in
  `data/sources.csv` (§4), run `make manifest`, commit both files.
- **Converted documents** live in the repository under `data/volve/`, which
  mirrors the folder structure of `$VOLVE_DATA`. The Markdown version of a
  source goes in an `md/` folder at the mirrored location of the original, with
  the same file name; figure cut-outs go in a `figs/` folder there:

  ```
  $VOLVE_DATA/reports/Volve_PUD_cmt.pdf      (raw, outside the repository)
  data/volve/reports/md/Volve_PUD_cmt.md     (converted, versioned)
  data/volve/reports/figs/Volve_PUD_cmt_…    (cut-outs and plot data, versioned)
  ```

  Details in `agents/doc/README.md`.
- **Public data** is read from a dated snapshot, never live inside an
  analysis. Sodir tables are in `data/sodir/<YYYYMMDD>/` with an `index.csv`
  (retrieval time, size, rows, SHA-256, URL). `make sodir` takes a new
  snapshot; each is about 8 MB, so take one only when newer data is needed.
  Historical values that the live tables no longer show are taken from
  Internet Archive captures, saved unchanged in `data/npd_archive/` with an
  `index.csv` (capture timestamp, original URL, SHA-256). Other public series
  (consumer price index, Brent price) are in `data/public/`; `make public`
  takes new snapshots.
- **Size.** Nothing larger than 10 MB is committed. Simulation output is never
  committed; commit the deck changes and the script that produces it.

## 4. Naming

- Lower-case with hyphens for new files and folders: `data-sources.md`.
  Derived files keep the stem of their source: `Volve_PUD_cmt.pdf` →
  `Volve_PUD_cmt.md`.
- Suffix tags on a stem, in the user's convention: `_cmt` (source carries the
  user's highlights), `_anlz` (analysis of that source).
- Dates are ISO 8601: `2026-11-19`; in file names `20261119`.
- Source identifiers are short and stable, and are defined in
  `data/sources.csv`. A new source gets an ID there before first use.

| ID | Source |
|---|---|
| `pud2005` | `reports/Volve_PUD.pdf` (and `_cmt` copy) |
| `disc1993` | `reports/Discovery_report.pdf` |
| `prod` | `production_data/Volve production data.xlsx` |
| `sim2016` | `eclipse_model/sim_model_PPA-eclipse/VOLVE_2016.*` |
| `sodir` | Sodir FactPages tables; always with the snapshot date |
| `npd_archive` | Archived captures of the NPD FactPages; always with the capture timestamp |
| `ssb_cpi`, `fred_brent` | Consumer price index (Statistics Norway) and Brent price (FRED) in `data/public/` |

## 5. Quantities and provenance

Every extracted or computed quantity is a fact: one row in
`data/facts/<source-id>.csv` with exactly these columns.

| Column | Meaning | Example |
|---|---|---|
| `fact_id` | Unique, `<source-id>.<name>` in lower case | `pud2005.recoverable_oil.mean` |
| `quantity` | What it is | `recoverable_oil` |
| `value`, `unit` | Value in the source's unit; unit `text` for non-numeric facts | `11.40`, `MSm3` |
| `basis` | Statistical or scenario basis | `mean`, `P90`, `base`, `estimate`, `actual` |
| `as_of` | Date of the knowledge (`YYYY`, `YYYY-MM` or `YYYY-MM-DD`); for actuals, the period the value refers to | `2005-02` |
| `subject` | Field, segment or well | `Volve` |
| `source` | Source ID; equals the file name | `pud2005` |
| `locator` | Place in the source | `p25 table 4.5` |
| `method` | How the value was obtained (below) | `read` |
| `confidence` | `high`, `medium`, `low` | `high` |
| `note` | Caveats, assumptions; may be empty | |

| `method` | Meaning |
|---|---|
| `read` | Parsed from a text layer or data file |
| `vision` | Read from a page image by OCR or an LLM |
| `digitised` | Measured from a plot |
| `computed` | Calculated from other facts; say how in `note` |
| `translated` | Text rendered from another language |

`make facts-validate` checks the register. Downstream agents read the
register, not the PDFs. `data/facts/sodir.csv` is generated (`make facts`) and
is not edited by hand.

Rules:

- **Units.** Keep the source unit and state it. Volumes at standard conditions
  are written `Sm3` (`MSm3` = 10⁶, `GSm3` = 10⁹); `MSm3oe` for oil
  equivalents; `Mt` for million tonnes. Convert only in a separate, labelled
  quantity.
- **Percentiles.** The Volve documents use the exceedance convention: P90 is
  the low case, P10 the high case. State the convention whenever percentiles
  are quoted and never mix conventions in one table.
- **Money.** State currency, nominal or real, and base year (`MNOK-2005`,
  `MNOK nominal`). Never compare amounts on different bases without saying so.
- **Language.** Translated text keeps a reference to the original page so the
  Norwegian wording can be checked.
- **Digitised values** are never presented as read values. Where the same
  quantity exists in a table, the table wins and the digitised curve is checked
  against it.
- **Assumptions are not facts.** A value that no source states does not go in
  the register; it belongs in the model or analysis that needs it, labelled as
  an assumption.

## 6. Hand-offs between domains

A hand-off is a file with a defined location and content, not a conversation.

| From → To | Artifact | Content |
|---|---|---|
| doc → all | `data/volve/…/md/`, `figs/`, plot data (XLSX); `_anlz` documents in `agents/doc/out/` | Text, tables, plot data, with page references |
| doc → dmx, rcf | `data/facts/pud2005.csv`, `disc1993.csv` | Estimates, assumptions, alternatives, dates |
| sim → dmx, rcf, doc | `agents/sim/out/` tables (CSV) and notes; `data/facts/sim2016.csv` | Profiles, volumes, sensitivities, with model and vector names |
| sys → rcf, dmx | `data/sodir/<date>/`, `data/facts/sodir.csv` | Public tables for all fields; Volve values as facts |
| rcf → dmx | `agents/rcf/out/` distributions and adjustment factors; `rcfkit.inplace` | Reference class definition, sample, statistics |
| dmx → doc | `agents/dmx/out/` model specifications and results | For reports |
| any → sys | Request for a rule or a reconciliation | See §11 |

The producer states in the artifact what it contains, what it was derived
from, and what was not checked. The consumer does not edit it; problems go
back to the producer.

## 7. Quality gates

Before an artifact is handed off or committed:

| Artifact | Minimum check |
|---|---|
| Converted document | Page count and heading structure match the source; every table and figure caption in the source is present; a sample of numbers compared against the source |
| Extracted table | Row/column totals or internal sums reproduce where the source gives them |
| Digitised plot | Compared against any table of the same data; axis calibration points recorded |
| Translation | Numbers, units and proper names unchanged; uncertain terms flagged |
| Simulation result | Deck, simulator version and run log recorded; mass-balance and history-match summary checked |
| Decision model | Probabilities sum to one; every input traced to a fact or marked as assumption; result reproduced by a second calculation path where feasible |
| Reference class | Inclusion rule written before the statistics are computed; sample size and exclusions reported; the case kept out of its own class; ranges tested on cases not used to build them |
| Cross-source value | Same quantity from two sources compared; difference explained or flagged |
| Anything committed | `make check` passes |

Report the outcome of the checks with the deliverable, including what failed
or was skipped.

## 8. Environment and reproducibility

- One Python environment for the repository, defined in `pyproject.toml` and
  pinned in `uv.lock`, with a dependency group per domain.

  | Command | Effect |
  |---|---|
  | `make setup` | Install every group |
  | `uv sync --group <domain>` | Install one domain's dependencies only |
  | `uv run <command>` | Run inside the environment |
  | `uv add --group <domain> <package>` | Add a dependency; commit `pyproject.toml` and `uv.lock` |
  | `make check` | Manifest verification, fact validation, tests, lint |
  | `make flow-deck` | Write the `_FLOW` deck files (sim) |
  | `make flow-run` | Run the Flow deck; output in `agents/sim/work/` (sim) |
  | `make doc-volve` | Rebuild plot data, facts, redrawn charts and the report (doc) |
  | `make rcf-volve` | Rebuild the review of the expert study, the reference class study and its tables (rcf) |
  | `make dmx-volve` | Rebuild the report on the Volve concept selection and its tables (dmx) |
  | `make deck` | Rebuild the slide decks: the workflow deck and the results presentation (sys) |
  | `make format` | Apply lint fixes and formatting |

- Shared code is the `syskit` package in `agents/sys/src/`; sim's code is
  `simkit` in `agents/sim/src/`, doc's is `dockit` in `agents/doc/src/` and
  rcf's is `rcfkit` in `agents/rcf/src/` and dmx's is `dmxkit` in
  `agents/dmx/src/`. A report that is wanted both as
  Markdown and as a web page is written once with `syskit.report.Report` and
  `syskit.charts.Chart`, so that both versions come from the same blocks and
  every number in it is computed in the script. A domain that needs an importable package of
  its own adds its path to `packages` in `pyproject.toml`; tests go in
  `agents/<domain>/tests/`.
- Record tool name and version, and the command or procedure, for anything
  generated. Fix random seeds and record them.
- LLM-produced content (translation, reading of scanned tables or figures) is
  recorded as such in `method`, and is checked per §7, because it cannot be
  regenerated identically. When such work is split among sub-agents, all get
  the same written rules, and their output is checked by a script or by the
  delegating agent, never accepted on their own report.
- The reservoir simulator is installed system-wide, not through `uv`; see
  `agents/sim/README.md`.

## 9. Git

- Single branch `main`; small commits that each leave the repository
  consistent and pass `make check`.
- Commit subject starts with the domain: `doc: convert Volve_PUD_cmt to md`.
- Never commit raw data, simulation output, credentials or anything in `work/`.
- Commit changes to `logs/` only when the user asks; never edit the logs.

## 10. Decision log

Structural decisions are recorded here, newest first: date, decision, reason.

| Date | Decision | Reason |
|---|---|---|
| 2026-11-20 | Reports are written once (`syskit.report`, `syskit.charts`) and rendered as Markdown with PNG charts and as a web page with interactive charts | The user asks for both; one source keeps numbers and charts identical |
| 2026-11-20 | Material delivered by others (`agents/rcf/study`) is kept as delivered and excluded from formatting and linting; corrections to its data are made in the reading code, with the evidence in the docstring | A formatter rewrote the expert's notebook during this work (restored from git); provenance requires the delivered state |
| 2026-11-20 | Reference literature inside the repository is converted beside the original (`lib/md/`, `lib/figs/`) | Same rule as for source documents: the Markdown sits in an `md` folder next to the file |
| 2026-11-20 | A domain's reusable procedure is a skill in `agents/<domain>/skills/`, linked from `.github/skills/` | Asked for by the user; keeps the procedure with its domain and lets the CLI load it |
| 2026-11-20 | Page-by-page translation and transcription is delegated to parallel sub-agents under one rules file and checked by `dockit.assemble` | 247 pages in one pass; consistent output; independent check of digits and highlights |
| 2026-11-20 | Generated `_FLOW` deck files are written beside the original deck in `$VOLVE_DATA` and listed in the manifest. This is the only exception to "nothing is written to `$VOLVE_DATA`" | Approved by the user. A deck that shares the unchanged include files needs only four new files and no path changes |
| 2026-11-19 | Converted documents and figure cut-outs are versioned in the repository under `data/volve/`, mirroring `$VOLVE_DATA`; nothing is written to `$VOLVE_DATA` | Approved by the user. They are costly to regenerate, feed every other domain, and must be the same on both machines |
| 2026-11-19 | Environment managed with `uv`; one lock file, a dependency group per domain | Approved by the user. One command reproduces the environment; heavy stacks install only when needed |
| 2026-11-19 | OPM Flow installed from the Ubuntu package (`ppa:opm/ppa`), not a container | Approved by the user. Simpler to run and to script |
| 2026-11-19 | Facts are CSV rows with fixed columns, one file per source, validated by `syskit.facts` | Diffable, opens in a spreadsheet, no service to maintain |
| 2026-11-19 | Raw data stays outside the repository in `$VOLVE_DATA`, pinned by a checksum manifest | User's specification; 2.5 GB does not belong in git |
| 2026-11-19 | `AGENTS.md` plus per-domain charters are the source of truth for agent behaviour; the profiles in `.github/agents/` only point to them | Keeps the setup independent of any one agent tool |

## 11. When the guidelines are silent

1. Check whether an existing rule covers the case by analogy; if so, apply it
   and say so in your result.
2. Otherwise choose the simplest option consistent with §1, apply it only
   within your own folder, and state it in your result as a proposal.
3. sys reviews the proposal, and either adopts it here (with a decision-log
   entry) or replaces it.
4. Anything that would move, rename or restructure existing deliverables or
   the user's data waits for the user's approval.

## 12. Session checklist

Start:

- Read `AGENTS.md`, your charter, and any `GUIDELINE_*.md` in your folder.
- Check `git status`; do not build on uncommitted work you did not create
  without asking.

Finish:

- Checks in §7 done and reported; `make check` passes.
- Deliverables in the locations of §2; scratch left only in `work/`.
- Anything learned that the next run should reuse is written into a
  `GUIDELINE_<topic>.md` in your folder.
- Commit with a domain-prefixed subject.

## References

- AGENTS.md convention — <https://agents.md>
- Wilson et al. (2017), *Good enough practices in scientific computing*, PLOS
  Computational Biology 13(6): e1005510.
- Wilkinson et al. (2016), *The FAIR Guiding Principles for scientific data
  management and stewardship*, Scientific Data 3: 160018.
- Nygard (2011), *Documenting Architecture Decisions* (basis for §10).
