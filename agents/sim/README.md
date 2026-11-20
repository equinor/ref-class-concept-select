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

## The deck under OPM Flow

The released deck does not run in OPM Flow. `VOLVE_2016_FLOW.DATA` is the
version that does, with only the changes Flow needs; it and three modified
include files are generated beside the originals by `make flow-deck`. The
changes, the verification against the Eclipse results and the known
differences are in `out/volve_2016_flow/README.md`.

In short (Flow 2026.04, checked 2026-11-20):

- Three input errors that Eclipse tolerated as "spurious data" are disabled,
  two equilibration options and `PRIORITY` are removed, and the `ADDZCORN`
  corner shifts are applied in the grid file.
- The static model is identical to Eclipse's in every active cell, except
  for transmissibilities in under 1 % of the cells in each direction.
- The full history run takes 11 minutes on 8 processes and ends within 0.6 %
  of Eclipse on cumulative oil, water and gas and 0.1 % on field pressure.

Two lessons from the port, to keep in mind for any deck:

- A lenient parse (for instance the OPM Python parser with errors set to
  "ignore") skips defective records without a message. Use it for inspection
  only. The Eclipse `.LOG` shows what Eclipse itself ignored.
- Check the material balance of every run (`make flow-compare`). A trial
  change that made the transmissibilities closer to Eclipse's produced a run
  that lost mass; agreement on volumes alone would have hidden that.

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
`data/facts/sim2016.csv`. Modified decks are produced by a script from the
originals (`src/simkit/flow_deck.py`); the originals are never edited, and
simulation output goes to `work/`.

## Code

| Module | Purpose |
|---|---|
| `src/simkit/flow_deck.py` | Build the `_FLOW` deck files (`make flow-deck`) |
| `src/simkit/compare.py` | Compare a Flow run with the Eclipse results: static arrays, summary vectors, material balance (`make flow-compare`) |

## Quality checks

`agents/sys/GUIDELINES.md` §7, simulation result.

## First step

Defined in `docs/startup-assessment.md` §7. The port to OPM Flow is done.
Still to do: the read-only analysis of the shipped results (field and well
profiles, in-place volumes by region, history-match quality against the
production workbook) and the reconciliation of the model's in-place volume
with Sodir's.
