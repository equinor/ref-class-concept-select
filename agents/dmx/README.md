# dmx — decision structuring and decision models

## Role

dmx identifies and frames the decisions in the project history, and builds and
solves decision models (decision trees, influence diagrams) for the ones
selected for analysis.

## Inputs

- Facts from doc: alternatives considered, estimates with their ranges, cost
  and price assumptions, dates.
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

Defined in `docs/startup-assessment.md` §7.
