# Guidelines for all agents

Maintained by sys. These rules exist so that one person can run, audit and
resume the whole workflow without relying on memory.

Each rule is marked:

- **[active]** — applies now.
- **[planned]** — applies once the tooling in `docs/startup-assessment.md` §8
  (Phase 1) exists. Until then, follow the stated interim practice.

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

## 2. Layout and ownership [active]

| Location | Owner | Content |
|---|---|---|
| `AGENTS.md`, `README.md`, `docs/` | sys | Rules, overview, plan, data sources |
| `agents/<domain>/` | that domain | Charter, procedures, code, deliverables |
| `logs/` | user | Prompt logs; agents do not edit |
| `$VOLVE_DATA` (default `../volve_data`) | user | Raw data, read-only |
| `data/` *[planned]* | sys (structure), producers (content) | Shared, versioned data: manifest, public snapshots, fact register |

Inside a domain folder:

| Path | Versioned | Content |
|---|---|---|
| `README.md` | yes | Charter: role, inputs, outputs, procedures |
| `GUIDELINE_<topic>.md` | yes | Procedures learned from completed work |
| `src/` | yes | Scripts and modules |
| `out/` | yes | Deliverables |
| `work/` | no | Scratch; safe to delete at any time |
| `lib/` | yes | Reference literature |

Agents read anywhere and write only in their own domain folder and the shared
locations assigned to them in §6.

## 3. Data [active]

- **Raw data** stays in `$VOLVE_DATA`, unmodified. Scripts take the location
  from the `VOLVE_DATA` environment variable and fall back to `../volve_data`
  relative to the repository root; no absolute paths in versioned files.
- **Converted documents** follow the user's rule: the Markdown version of a
  source document goes in an `md/` folder beside the original, with the same
  file name; figure cut-outs go in a `figs/` folder beside the original. Details
  in `agents/doc/README.md`.
- **Public data pulled from the internet** is saved as a dated snapshot, never
  read live inside an analysis. Interim practice: save under the pulling
  domain's `out/` with the retrieval date in the file name.
- **Size.** Nothing larger than 10 MB is committed. Simulation output is never
  committed; commit the deck changes and the script that produces it.
- **Manifest** *[planned]*. `data/manifest.csv` lists every raw file with size
  and SHA-256 so that both of the user's machines can verify identical inputs.

## 4. Naming [active]

- Lower-case with hyphens for new files and folders: `data-sources.md`.
  Derived files keep the stem of their source: `Volve_PUD_cmt.pdf` →
  `Volve_PUD_cmt.md`.
- Suffix tags on a stem, in the user's convention: `_cmt` (source carries the
  user's highlights), `_anlz` (analysis of that source).
- Dates are ISO 8601: `2026-11-19`; in file names `20261119`.
- Source identifiers are short and stable; use them in provenance fields:

| ID | Source |
|---|---|
| `pud2005` | `reports/Volve_PUD.pdf` (and `_cmt` copy) |
| `disc1993` | `reports/Discovery_report.pdf` |
| `prod` | `production_data/Volve production data.xlsx` |
| `sim2016` | `eclipse_model/sim_model_PPA-eclipse/VOLVE_2016.*` |
| `sodir` | Sodir FactPages tables; always with retrieval date |

  New sources get an ID here before first use.

## 5. Quantities and provenance [active]

Every extracted or computed quantity carries:

| Field | Meaning | Example |
|---|---|---|
| `quantity` | What it is | `recoverable_oil` |
| `value`, `unit` | Value in the source's unit | `11.40`, `MSm3` |
| `basis` | Statistical or scenario basis | `mean`, `P90`, `base`, `actual` |
| `as_of` | Date of the knowledge | `2005-02` |
| `subject` | Field, segment or well | `Volve` |
| `source`, `locator` | Source ID and place in it | `pud2005`, `p25 table 4.5` |
| `method` | `read`, `digitised`, `computed`, `translated` | `read` |
| `confidence` | `high`, `medium`, `low` | `high` |
| `note` | Caveats, assumptions | |

Rules:

- **Units.** Keep the source unit and state it. Volumes at standard conditions
  are written `Sm3` (`MSm3` = 10⁶, `GSm3` = 10⁹). Convert only in a separate,
  labelled column.
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
- **Fact register** *[planned]*. Facts are stored one per row in
  `data/facts/<source-id>.csv` with the columns above plus a `fact_id`.
  Downstream agents read the register, not the PDFs. Interim practice: put the
  same fields in tables inside the `_anlz` document.

## 6. Hand-offs between domains [active]

A hand-off is a file with a defined location and content, not a conversation.

| From → To | Artifact | Content |
|---|---|---|
| doc → all | Converted documents (`md/`, `figs/`), `_anlz` documents, figure data (XLSX) | Text, tables, plot data, with page references |
| doc → dmx, rcf | Facts (§5) | Estimates, assumptions, alternatives, dates |
| sim → dmx, rcf, doc | `agents/sim/out/` tables (CSV) and notes | Profiles, volumes, sensitivities, with model and vector names |
| rcf → dmx | `agents/rcf/out/` distributions and adjustment factors | Reference class definition, sample, statistics |
| dmx → doc | `agents/dmx/out/` model specifications and results | For reports |
| any → sys | Request for a rule or a reconciliation | See §11 |

The producer states in the artifact what it contains, what it was derived
from, and what was not checked. The consumer does not edit it; problems go
back to the producer.

## 7. Quality gates [active]

Before an artifact is handed off or committed:

| Artifact | Minimum check |
|---|---|
| Converted document | Page count and heading structure match the source; every table and figure caption in the source is present; a sample of numbers compared against the source |
| Extracted table | Row/column totals or internal sums reproduce where the source gives them |
| Digitised plot | Compared against any table of the same data; axis calibration points recorded |
| Translation | Numbers, units and proper names unchanged; uncertain terms flagged |
| Simulation result | Deck, simulator version and run log recorded; mass-balance and history-match summary checked |
| Decision model | Probabilities sum to one; every input traced to a fact or marked as assumption; result reproduced by a second calculation path where feasible |
| Reference class | Inclusion rule written before the statistics are computed; sample size and exclusions reported |
| Cross-source value | Same quantity from two sources compared; difference explained or flagged |

Report the outcome of the checks with the deliverable, including what failed
or was skipped.

## 8. Reproducibility

- **[active]** Record tool name and version, and the command or procedure, for
  anything generated. Fix random seeds and record them.
- **[active]** LLM-produced content (translation, reading of scanned tables or
  figures) is recorded as such in `method`, and is checked per §7, because it
  cannot be regenerated identically.
- **[planned]** One Python environment for the repository, defined in
  `pyproject.toml` with a lock file and one optional dependency group per
  domain. One command (`make check`) runs the manifest verification, tests and
  linters.

## 9. Git [active]

- Single branch `main`; small commits that each leave the repository
  consistent.
- Commit subject starts with the domain: `doc: convert Volve_PUD_cmt to md`.
- Never commit raw data, simulation output, credentials or anything in `work/`.
- Do not commit changes to `logs/` on the user's behalf.

## 10. Decision log [active]

Structural decisions are recorded here, newest first: date, decision, reason.

| Date | Decision | Reason |
|---|---|---|
| 2026-11-19 | Raw data stays outside the repository in `$VOLVE_DATA`; converted documents go beside their originals in `md/` and `figs/` | User's specification |
| 2026-11-19 | `AGENTS.md` plus per-domain charters are the source of truth for agent behaviour; tool-specific agent profiles only point to them | Keeps the setup independent of any one agent tool |
| 2026-11-19 | Plain-file hand-offs with provenance fields (§5, §6) | Auditable by one person; no services to maintain |

## 11. When the guidelines are silent [active]

1. Check whether an existing rule covers the case by analogy; if so, apply it
   and say so in your result.
2. Otherwise choose the simplest option consistent with §1, apply it only
   within your own folder, and state it in your result as a proposal.
3. sys reviews the proposal, and either adopts it here (with a decision-log
   entry) or replaces it.
4. Anything that would move, rename or restructure existing deliverables or
   the user's data waits for the user's approval.

## 12. Session checklist [active]

Start:

- Read `AGENTS.md`, your charter, and any `GUIDELINE_*.md` in your folder.
- Check `git status`; do not build on uncommitted work you did not create
  without asking.

Finish:

- Checks in §7 done and reported.
- Deliverables in `out/` (or beside the source, for converted documents);
  scratch left only in `work/`.
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
