# dmx — decision structuring and decision models

## Role

dmx identifies and frames the decisions in the project history, and builds and
solves decision models (decision trees, influence diagrams) for the ones
selected for analysis.

## Inputs

- Facts from the register (`data/facts/`): alternatives considered, estimates
  with their ranges, cost and price assumptions, dates, and outcomes from
  Sodir.
- Results from sim: profiles, volumes, sensitivities (hindsight; `as_of 2016`).
- Distributions and adjustment factors from rcf.

dmx does not read numbers out of PDFs itself; a missing input is requested
from the producing domain.

## Method

1. **Timeline.** List the decisions with date, decision maker, alternatives
   and the information available at that date.
2. **Frame.** For a selected decision: what is given, what is being decided,
   what is deferred; objectives and value measure.
3. **Structure.** Influence diagram of decisions, uncertainties and values.
4. **Quantify.** Each probability and value is a fact from a source or is
   marked as an assumption with its reason.
5. **Solve and test.** Expected values, optimal policy, sensitivity, value of
   information where relevant.
6. **Compare views.** Solve with the project's own estimates (inside view) and
   with rcf-adjusted estimates (outside view).

## Outputs

In `agents/dmx/out/`: model specification as a text file (nodes, states,
probabilities, values, each with its source), solution tables, diagrams.

## Code

The `dmxkit` package in `src/`.

| Module | Purpose |
|---|---|
| `dmxkit.volve_basis` | Volve, concept selection 2005: the PDO's volume in place as stated and as recalibrated with the reference class; the PDO's relations from volume to reserves and value; the decision on the western wells |
| `dmxkit.volve_concept` | The report built on it |

`make dmx-volve` rebuilds the report and its tables.

## Results so far

| Output | Content |
|---|---|
| `out/volve-concept-basis.md`, `out/volve-concept-basis/index.html` | Volve concept selection on a recalibrated volume basis: the alternative in-place estimate, what it does to reserves and value, whether it supports another concept, the modified development plan, hindsight, model specification |
| `out/data/volve_in_place_basis.csv` | Oil in place by area and basis: P90, P50, P10, mean |
| `out/data/volve_basis_metrics.csv` | Reserves, value and the western-wells decision under each basis |

## Open points

- No alternative concept can be valued: the concept screening and concept
  selection reports are not in the dataset, and the PDO gives no numbers for
  the alternatives it rejected.
- The link between the PDO's volume areas (East, West) and its wells is not
  stated in the PDO; the decision on the western wells assumes it.
- Price, cost and schedule are not yet in a model; the influence diagram of
  the full concept decision is still to be built.

## Environment

`uv sync --group dmx` installs pyAgrum, pandas, SciPy, matplotlib and plotly.

## Rules specific to dmx

- A model for a decision uses only information dated at or before that
  decision. Later knowledge appears only in a separate, labelled hindsight
  comparison.
- Where the documents do not quantify an alternative, the model says so; values
  are not invented to complete a tree.
- State the percentile convention (P90 is the low case in the Volve documents)
  and the discretisation used to turn ranges into branch probabilities.

## Quality checks

`agents/sys/GUIDELINES.md` §7, decision model.

## First step

Done 2026-11-20 as far as the volume basis goes: see *Results so far*. The
timeline and the influence diagram of `docs/startup-assessment.md` §7 remain.
