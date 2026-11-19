# sim — reservoir simulation and analysis

## Role

sim analyses reservoir simulation input and output, runs simulations, and
builds reduced, fit-for-purpose decks when a question needs them.

## References

- OPM Flow reference manual (keyword definitions): <https://opm-project.org/?page_id=955>
  — current release 2026-04; PDF on the
  [opm-reference-manual releases page](https://github.com/OPM/opm-reference-manual/releases/latest).
- OPM Python documentation: <https://opm.github.io/opm-python-documentation/index.html>
- `resdata` (reading and writing Eclipse result files): <https://github.com/equinor/resdata>

## Input

`$VOLVE_DATA/eclipse_model/sim_model_PPA-eclipse/` (measured 2026-11-19):

| Item | Value |
|---|---|
| Case | `VOLVE_2016`, Eclipse 100 black oil (oil, water, gas, dissolved gas), metric |
| Grid | 108 × 100 × 63 = 680 400 cells, 183 545 active in the shipped `INIT` |
| Period | 31 Dec 2007 to 1 Oct 2016, 340 report steps, producers under history control (`WCONHIST`) |
| Results shipped | `UNSMRY`/`SMSPEC` (3 123 vectors, 13 wells), `UNRST` (812 MB), `INIT`, `RFT`, `PRT` |
| Key values | FOPT 9.98 MSm3 against FOPTH 10.06 MSm3; FOIP at start 21.97 MSm3 |
| Also present | Three schedule variants (`SCH_151215`, `SCH_190516`, `SCH_010916`), `Volve Sim model and HM per jan-16.pptx` |

**This is the history-matched model as of 2016, not the model behind the 2005
PDO.** It represents hindsight. Anything derived from it is tagged
`as_of 2016` and is not used to describe what was known at earlier decisions.

## State of the deck under OPM Flow

Checked 2026-11-19 with Flow 2026.04 in dry-run mode
(`flow VOLVE_2016.DATA --enable-dry-run=true --output-dir=<dir>`) on a copy of
the deck. No simulation has been run.

**Input errors that stop Flow** — each must be fixed in a copy:

| File, lines | Problem | Fix used in the check |
|---|---|---|
| `VOLVE_2016.DATA`, 620 | `ROCK` has a 13th record with trailing text (`/ #13`); `TABDIMS` declares 12 PVT regions | Line removed |
| `RSVD_input_new_combined_020610_perch_water_2914m.E100`, 235–256 | `RSVD` has a 13th table ("Reg 13"); `EQLDIMS` declares 12 regions | Table removed |
| `SCH_010916_10DAYS.SCH`, 4869–4873 | Five well-control records after `DATES 1 JAN 2015` with no `WCONHIST` keyword ("put data manually") | Lines removed. What Eclipse did with them is not established |

**Keywords Flow does not implement** — Flow stops on these unless run with
`--parsing-strictness=low`, which ignores them:

| Keyword | Where | Consequence of ignoring |
|---|---|---|
| `ADDZCORN` | Four active includes: `FAULT_NW-15NOV13`, `CONTACT_MAIN-NW-AP2014`, `FAULT_MAIN-F14-AP2014`, `FAULT_MAIN-F12-F14-AP2014` | Grid geometry differs from the Eclipse model (see below). Needs a real substitute, e.g. corner depths taken from the shipped `VOLVE_2016.GRID` |
| `EQLOPTS` options `QUIESC`, `MOBILE` | `VOLVE_2016.DATA`, 98 | Initial state may differ; compare with the first shipped restart step |
| `PRIORITY` | `VOLVE_2016.DATA`, 940 | Well prioritisation not applied |
| `GRIDFILE`, `RPTGRID`, `RPTSOL`, `RPTRUNSP`, `NSTACK`, `PARALLEL`, `ECHO`/`NOECHO`, `MESSAGES` options | | Reporting and run control only |
| Summary vectors `FMWWO`, `FMWWT`, `WMCON`, `WTPR2FB`, `WTPT2FB`, `WTPR4FB`, `WTPT4FB` | | Not written |

**With the three fixes and low strictness** the dry run completes in 33 s and
writes `EGRID` and `INIT`. Against the shipped Eclipse `INIT`:

| Quantity | Result |
|---|---|
| Active cells | 183 545 in both, the same cells |
| Total pore volume | Equal to four significant figures (1.1585 × 10⁸ rm³) |
| Porosity, permeability | Identical |
| Cell pore volume | Differs by more than 1 % in 873 cells, at most 4.2 % |
| Cell depth | Differs by more than 0.1 m in 2 862 cells, at most 58.75 m; consistent with the ignored `ADDZCORN`, not checked cell by cell |

Flow also reports 36 connections in inactive cells (ignored) and that
equilibration region 12 has no active cells.

A lenient parse (as with the OPM Python parser and its "ignore" settings)
skips the orphan schedule records without a message. Use it for inspection
only, not to decide that a deck is sound.

## Environment

- `uv sync --group sim` installs `resdata`, `res2df`, the `opm` Python bindings
  and pandas.
- OPM Flow itself is installed system-wide from the OPM package archive
  (2026.04 for Ubuntu 24.04; installed and checked 2026-11-19); `openmpi-bin` provides `mpirun` for parallel runs:

  ```bash
  sudo add-apt-repository -y ppa:opm/ppa && sudo apt-get update && sudo apt-get install -y libopm-simulators-bin openmpi-bin
  flow --version
  ```

## Outputs

Tables (CSV) and notes in `agents/sim/out/`, each stating case, vector or
keyword names, simulator and version. Values other domains rely on also go in
`data/facts/sim2016.csv`. Modified decks are kept as small patch
files or scripts against the original; the original is never edited.

## Quality checks

`agents/sys/GUIDELINES.md` §7, simulation result.

## First step

Defined in `docs/startup-assessment.md` §7: analyse the shipped results before
running anything, then port the deck to OPM Flow. The port starts from the
table above: a script that produces the fixed copy, a substitute for
`ADDZCORN`, then a full run compared against the shipped summary vectors.
