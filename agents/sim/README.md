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
| Grid | 108 × 100 × 63 = 680 400 cells, 203 522 active |
| Period | 31 Dec 2007 to 1 Oct 2016, 340 report steps, producers under history control (`WCONHIST`) |
| Results shipped | `UNSMRY`/`SMSPEC` (3 123 vectors, 13 wells), `UNRST` (812 MB), `INIT`, `RFT`, `PRT` |
| Key values | FOPT 9.98 MSm3 against FOPTH 10.06 MSm3; FOIP at start 21.97 MSm3 |
| Also present | Three schedule variants (`SCH_151215`, `SCH_190516`, `SCH_010916`), `Volve Sim model and HM per jan-16.pptx` |

**This is the history-matched model as of 2016, not the model behind the 2005
PDO.** It represents hindsight. Anything derived from it is tagged
`as_of 2016` and is not used to describe what was known at earlier decisions.

## Known issues with the deck under OPM

Tested with the OPM Python parser 2026.4 on a patched copy:

- `ROCK` has a 13th record with trailing text (`/ #13`) while `TABDIMS`
  declares 12 PVT regions; the strict parser stops there.
- `RSVD` has more records than declared.
- `GRIDFILE` output of `.GRID` is not supported (EGRID only).

With the trailing `ROCK` record removed and lenient handling of extra records,
the deck parses and the grid and schedule build. A full Flow run has not been
attempted.

## Outputs

Tables (CSV) and notes in `agents/sim/out/`, each stating case, vector or
keyword names, simulator and version. Modified decks are kept as small patch
files or scripts against the original; the original is never edited.

## Quality checks

`agents/sys/GUIDELINES.md` §7, simulation result.

## First step

Defined in `docs/startup-assessment.md` §7: analyse the shipped results before
running anything, then port the deck to OPM Flow.
