# Startup assessment and development plan

Status: **approved 2026-11-19; Phase 1 complete** · prepared in the sys role

## 1. Summary

**The work plan is feasible.** Every domain has enough data and mature enough
open tooling to produce a first result. All figures in this document were
measured or retrieved on 2026-11-19; nothing here is taken from memory.

Three findings shape how the work should be done:

1. **The simulation model is hindsight.** The released Eclipse model is the
   history-matched model of 2016, not the model behind the 2005 PDO. What was
   known at each decision has to be reconstructed from the documents; the model
   can only show how things turned out.
2. **The documents contain what a decision model needs.** The PDO gives
   in-place and reserves distributions (mean, P90, P50, P10), contact
   probabilities, cost tables, price and discount assumptions, and a section on
   alternative concepts. How far the alternatives are quantified is not yet
   known.
3. **Reference data for in-place volumes is the weak point.** Public tables
   give a yearly history of recoverable-volume estimates for 145 fields, but
   only the current in-place estimate. Calibrating in-place estimates needs a
   proxy or another source (§4, rcf).

A first cross-check already shows the kind of result the methodology is after
(preliminary; volume scopes not yet reconciled):

| Oil, MSm3 | PDO 2005 (`pud2005`) | Outcome |
|---|---|---|
| In place | Mean 27.5, P90 20.9, P50 26.7 (Table 4.5) | 18.70 (Sodir current estimate); 21.97 in the 2016 model |
| Recoverable | Mean 11.40, P90 9.0, P50 11.35, P10 15.31 (Table 4.5) | 10.17 produced (Sodir) |

P90 is the low case. The in-place outcome is below the PDO's P90; recovery
ended between P90 and P50, after the estimate had fallen to 8.15 in 2010 and a
further 1 640 MNOK was invested in 2012–2014.

**State:** the plan in §8 and the decisions in §9 were approved on 2026-11-19.
Phase 0 (rules, sys specification, charters, data-source guide) and Phase 1
(environment, data manifest, Sodir snapshot, fact register, check command,
agent profiles) are built. Phase 2 starts with the doc task.

## 2. What exists

Detail and measurements are in `docs/data-sources.md` §1.

| Source | Nature | Consequence |
|---|---|---|
| `Volve_PUD.pdf` (53 p, Norwegian, born-digital) | Text layer complete; plots partly vector, partly raster | High-fidelity conversion; needs translation; vector plots should be recoverable from their drawing paths (not yet done) |
| `Volve_PUD_cmt.pdf` | Same plus 77 highlights on 23 pages | Highlights can be transferred to Markdown programmatically |
| `Discovery_report.pdf` (194 p, scan + OCR) | OCR good on prose, unusable on figures | Tables and figures need page-image reading and sample checks |
| Production workbook | Daily and monthly per wellbore, 2007–2016 | Ready to use |
| Eclipse model `VOLVE_2016` | 203 522 active cells, results included | Analysis possible without running anything |

Working environment: WSL2 Ubuntu 24.04, 20 cores, 30 GB RAM, Python 3.12, Docker
29.8, poppler, mutool, qpdf, tesseract, LibreOffice, `uv` 0.13. The project
environment is defined in `pyproject.toml`. OPM Flow is installed separately
(`agents/sim/README.md`).

## 3. Additional public data

`docs/data-sources.md` §2 lists sources and retrieval recipes. In short:

- **Sodir FactPages** offers every table as a CSV download for the whole
  shelf, without authentication. For Volve this gives yearly and monthly
  production, yearly investments, and the recoverable-volume estimate at each
  year-end from 2005. The same tables are the base for a reference class.
- **Equinor's Volve data village** (about 40 000 files) is distributed through
  the Databricks Marketplace. Only reports, production data and the Eclipse
  model are held locally; the rest (wells, logs, seismic, static model) has
  not been inventoried.
- **norskpetroleum.no** repeats Sodir's data with short field descriptions.

## 4. Feasibility by domain

| Domain | Verdict | Evidence | Main risks | Mitigation |
|---|---|---|---|---|
| sys / infrastructure | Feasible, low risk | Plain-file workflow; one maintainer; two machines (inferred from the two prompt logs) | Conventions drifting between sessions and machines | Short always-loaded rules; checksummed data manifest; locked environment |
| doc | Feasible; PDO high fidelity, discovery report medium | Text layer and highlights read programmatically in tests; plot pages contain vector paths | Translation errors in technical terms; scanned tables; digitising raster plots; 182 MB scan | Page anchors back to the original; table-versus-plot cross-checks; sample verification; page-wise processing |
| sim | Analysis feasible now; re-running needs deck work | Results read with `resdata` 7.0; deck loads in the OPM 2026.4 parser after one record is removed and extra records are tolerated | Flow may not reproduce the Eclipse results; run time unknown; model is 2016 hindsight | Analyse shipped results first; port in small steps and compare against shipped vectors; tag everything `as_of 2016` |
| dmx | Feasible for the 2005 concept decision | PDO has distributions, costs, price (22 USD/bbl), discount rate (8 %), break-even (17.50 USD/bbl), and a section on alternatives | Alternatives may be described only qualitatively; earlier and later decisions less documented | Model only what is documented; mark assumptions; start with timeline and framing |
| rcf | Feasible for recoverable volume and cost; limited for in-place | Sodir tables: 145 fields with yearly reserve estimates 2004–2025, 136 with production, 142 with investments | No public history of in-place estimates; no public operator forecast profiles; published dataset not shareable; estimate history starts 2004 | Start with recoverable-volume and investment classes; use published calibration results for production profiles; treat in-place as a research question |

## 5. Findings that shape the method

1. **Hindsight model.** `sim2016` starts 31 Dec 2007 and is matched to 2016.
   Its initial oil in place (21.97 MSm3) differs from both the PDO mean (27.5)
   and Sodir's current figure (18.70). The three need to be reconciled by
   region before any is used as "the" in-place volume.
2. **Estimate history is available.** Sodir's recoverable-oil estimate for
   Volve by year-end: 11.90 (2005), 13.58 (2008), 8.79 (2009), 8.15 (2010),
   9.54 (2013), 10.34 (2015), 10.17 (final). Together with yearly investments
   this dates the points where the view of the field changed.
3. **Candidate decision points**, to be confirmed from the documents:

   | When | Decision | Evidence so far |
   |---|---|---|
   | 1993 | Evaluation after discovery well 15/9-19 SR | `disc1993` |
   | 2005 | Concept selection and PDO | `pud2005`; alternatives in its chapter 7 |
   | 2009–2010 | Response to the downgrade after first production | Sodir estimate 13.58 → 8.15 |
   | 2012–2014 | Additional wells | 1 640 MNOK invested; estimate 8.68 → 10.34 |
   | 2016 | Cessation | Production ends; status history |

4. **Sources disagree, and that is part of the subject.** Examples to resolve:
   - Cumulative oil: 10.17 MSm3 (Sodir), 10.04 (production workbook), 10.06
     (history in the model).
   - `docs/background.txt` states the field delivered about 9.5 million barrels
     more than the PDO expected, which implies an expectation near 8.7 MSm3;
     the PDO's uncertainty study gives a mean of 11.40.
   - Investments: about 2 043 MNOK in the PDO cost table (Table 12.6, to be
     confirmed) against 4 689 MNOK nominal in Sodir. The PDO concept leases the
     rig and storage vessel, so the two are not on the same basis.
5. **Percentile convention.** The documents use P90 as the low case. This is
   fixed in the guidelines because it is easy to invert.

## 6. Infrastructure specification

### 6.1 Required

| # | Element | Specification | Status |
|---|---|---|---|
| R1 | Always-loaded rules | `AGENTS.md` at the root (read automatically by Copilot CLI); short, pointing to charters | Done |
| R2 | sys operating specification | `agents/sys/README.md`, `agents/sys/GUIDELINES.md`: layout, ownership, data handling, naming, provenance, hand-offs, quality gates, change control | Done |
| R3 | Domain charters | `agents/<domain>/README.md`: role, inputs, outputs, method, checks | Done |
| R4 | Data location and integrity | Raw data outside the repo via `VOLVE_DATA`; `data/manifest.csv` with size and SHA-256; verification command | Done: 74 files, `make manifest-verify` |
| R5 | Reproducible environment | One `pyproject.toml` with lock file; dependency group per domain so heavy stacks install only when needed | Done: `make setup` |
| R6 | Provenance | Fields in guidelines §5; fact register `data/facts/<source-id>.csv`; validator | Done: 182 Sodir facts for Volve, `make facts-validate` |
| R7 | Public-data snapshots | Script that downloads the Sodir tables to dated files | Done: `data/sodir/20261119/`, `make sodir` |
| R8 | One check command | `make check`: manifest verification, validators, tests, lint | Done |

### 6.2 Recommended

| # | Element | Why | When |
|---|---|---|---|
| S1 | Copilot CLI agent profiles in `.github/agents/`, one per domain, pointing to the charter | Lets a session start as a domain agent (`--agent`, `/agent`) and lets one agent delegate to another | Done; all five are listed by the CLI |
| S2 | Skills for repeatable procedures (`.github/skills/`) | Turns a proven procedure into something reusable on the next batch | After a procedure has been run once |
| S3 | Continuous integration running `make check` | Catches breakage between the two machines | Optional; local check is enough for one maintainer |
| S4 | Decision log | Already in guidelines §10 | Done |

### 6.3 Deliberately left out

Database, workflow orchestrator, data-versioning service, container for the
whole project. Each adds something to maintain; plain files, a lock file and a
manifest cover the need for one person. Revisit only if a concrete task
requires it.

### 6.4 Tooling candidates

Versions are those available on 2026-11-19. Choices marked *evaluate* are
settled by a small trial in the first step of the domain, not in advance.

| Purpose | Candidate | Note |
|---|---|---|
| Environment | `uv` 0.13 with lock file | In use |
| PDF text, annotations, vector paths | PyMuPDF 2.1 | Used in the probes; reads highlights and drawing paths |
| PDF layout and tables | Docling 2.x, Marker 2.x, PyMuPDF4LLM | *Evaluate* on a few PDO pages |
| Scanned tables, figures, translation | LLM with page images | Checked per guidelines §7 |
| Eclipse results | `resdata` 7.0, `res2df` 1.4 | `resdata` verified on the Volve results |
| Simulator | OPM Flow 2026.04 | Ubuntu package (`ppa:opm/ppa`) or container; Python bindings `opm` 2026.4 |
| Influence diagrams | pyAgrum 3.3 | *Evaluate*; alternative PyCID 0.8 |
| Decision trees | Small in-repo solver over a text specification | Transparent and auditable; trees here are small |
| Statistics for rcf | pandas, SciPy | |
| Reports | Static HTML with embedded charts | No server |

## 7. First step in each domain

| Domain | First step | Result | Depends on |
|---|---|---|---|
| doc | Convert `Volve_PUD_cmt.pdf`: Markdown in English with page anchors and highlights in bold; figure cut-outs; plot data to Excel; begin with a three-page trial of the extraction tools | `data/volve/reports/md/`, `figs/`, workbook, facts, and a written procedure | Your task specification |
| sim | Read-only analysis of the shipped results: field and well profiles, in-place by region, history-match quality against the production workbook; reconcile the model's in-place volume with Sodir's. Then port the deck to OPM Flow | CSV tables and a note; later a patch set for the deck | Nothing for the analysis; OPM Flow installed for the port |
| rcf | Build the reference dataset from the Sodir snapshot: per field, the recoverable estimate at approval and at each later year, final recovery, investments. Write the class definition before computing statistics. Summarise the method of Nesvold & Bratvold (2022) | Dataset, class definition, method note | Nothing |
| dmx | Decision timeline and framing of the 2005 concept decision from doc's facts; influence-diagram skeleton without numbers | Timeline, frame, diagram | doc first step |

doc, rcf and sim's analysis step can run in parallel; dmx follows doc.

## 8. Development plan

### Phase 0 — foundation documents (done)

Assessment, data-source guide, `AGENTS.md`, sys specification, domain
charters, `.gitignore`.

### Phase 1 — infrastructure (done 2026-11-19)

| # | Task | Result |
|---|---|---|
| 1.1 | Environment: `pyproject.toml`, lock file, dependency groups `doc`, `sim`, `dmx`, `rcf`, `dev` | All groups resolve into one lock file and install with `make setup` on this machine. Not yet run on the second machine |
| 1.2 | Data manifest: `syskit.manifest` creates and verifies `data/manifest.csv`; `VOLVE_DATA` resolved in `syskit.paths` | 74 files, 2.48 GB; verification passes; missing, changed and extra files are reported (tested) |
| 1.3 | Sodir snapshot: `syskit.sodir` | `data/sodir/20261119/`, nine tables with index; the Volve values in this document are reproduced by a test |
| 1.4 | Fact register: columns in guidelines §5, validator `syskit.facts`, `data/facts/sodir.csv` | 182 facts; rows without source, unit or locator are rejected (tested) |
| 1.5 | `Makefile` | `make check` runs manifest verification, fact validation, 32 tests and lint; passes |
| 1.6 | Copilot CLI agent profiles in `.github/agents/` | All five listed by the CLI; `rcf` run once and found its charter. The other four were not run individually |
| 1.7 | Guidelines, charters and README brought in line with what exists | Done |

Still open from Phase 1: OPM Flow is not installed on this machine (command in
`agents/sim/README.md`; it needs `sudo`), and nothing has been checked on the
second machine.

### Phase 2 — first step per domain

As in §7. doc's task is specified by you. Each first step ends by writing its
procedure into a `GUIDELINE_<topic>.md` in the domain folder.

### Phase 3 — integration

First end-to-end pass on the 2005 concept decision: doc facts → rcf adjustment
→ dmx model solved with inside and outside view → hindsight comparison from
sim and Sodir → doc report. sys reconciles cross-source differences (§5.4)
along the way.

## 9. Decisions

All approved by the user on 2026-11-19; recorded in the decision log
(`agents/sys/GUIDELINES.md` §10).

| # | Question | Decision |
|---|---|---|
| D1 | Where do converted documents live? | In the repository under `data/volve/`, in `md/` and `figs/` folders mirroring the location of the original; versioned. Nothing is written to `../volve_data` |
| D2 | Install `uv`? | Yes; installed in `~/.local/bin` |
| D3 | How to install OPM Flow? | Ubuntu package from `ppa:opm/ppa`, installed by the user with `sudo` |
| D4 | Phase 1 | Approved and built |

## Appendix — how the measurements were made

- PDFs: `pdfinfo`, `pdftotext`, `pdfimages`, `qpdf --json`; PyMuPDF for
  annotations, images and drawing paths per page.
- Production workbook: `openpyxl` and `pandas`.
- Simulation results: `resdata` 7.0 on `VOLVE_2016.UNSMRY` and `.INIT`.
- Deck: `opm` 2026.4 Python parser on a copy with line 620 of
  `VOLVE_2016.DATA` removed and extra records ignored; grid and schedule
  objects built. No simulation was run.
- Sodir: CSV downloads with `curl` from the endpoints in
  `docs/data-sources.md`.
- Tools were installed in a temporary environment that has been removed. The
  raw data was not modified.
