---
name: reference-class-study
description: "Run or review a reference class study: compare estimates made at a decision (probability of discovery, volume in place, sanctioned reserves, production forecast, cost) with what followed for a class of comparable cases, test the resulting ranges out of sample, and apply them to a case. Use when an estimate is to be challenged with the outside view, or when someone else's reference class study is to be assessed."
---

# Reference class study

The core procedure of the rcf domain. It was worked out on an expert's study
of the Norwegian shelf and Volve (`agents/rcf/study`), its review
(`agents/rcf/out/expert-study-review.md`) and its recalculation
(`agents/rcf/out/volve-rcf-study.md`); these remain the worked examples.

Read first: `agents/rcf/README.md` (charter), `agents/sys/GUIDELINES.md`
(locations, provenance, quality gates), and the reference paper,
`agents/rcf/lib/md/LIB_2022_ENERGY_debiasing_production-forecasts_ENesvold+RBratvold.md`.

## What such a study is for

A forecast built from the particulars of a project (maps, a reservoir model,
a schedule) is an inside view. Inside views of projects are, on the record,
too optimistic and too narrow. A reference class study answers the same
forecasting question from outside: *for cases like this one, how did the
outcome compare with the estimate made at the decision?* It delivers three
things:

1. **Bias**: the typical ratio of outcome to estimate in the class.
2. **Spread**: how far outcomes scatter around that, as a range that holds a
   stated share of them.
3. **A forecast for the case**: the class distribution scaled by the case's
   own estimate, to set beside the inside view and, when it exists, the
   outcome.

It does not explain why estimates miss. Where the data allows, look for the
cause separately (step 8).

## How to think about it

The same six moves at every decision point:

1. Name a quantity that is **estimated when a decision is made and observed
   later**. One decision, one quantity.
2. Find a record that holds **both for many cases**. If the estimate itself is
   not public, choose a stand-in and say what it is and how close it comes.
3. **Normalise**: outcome over estimate, so that cases of different size pool.
4. Describe the pooled ratios: **middle and spread**, with intervals.
5. **Test** that a range built this way would have held for cases not used to
   build it.
6. **Apply** to the case: multiply by its estimate; compare with the inside
   view and the outcome.

Questions to settle before computing anything:

| Question | Why it decides the result |
|---|---|
| What is one case? | The unit must be what the estimate was made for: a prospect, not a well with three prospects; a field's first PDO, not the field with all later projects |
| When was the estimate made? | An "estimate" dated years after the decision contains the outcome. Admit a case only if its estimate dates from the decision |
| When does the clock start? | Calendar years mix fields that start in January and in November. Count from the first month of the outcome |
| What was knowable at the case's decision date? | A method for future use may use everything; a test on a past case may not |
| Is the case in its own class? | It must not be |
| Same units above and below the line? | Oil equivalents with NGL over reserves without it is a different ratio |

## Deliverables

| Deliverable | Location |
|---|---|
| Report, Markdown and web page, built by one script | `agents/rcf/out/<name>.md`, `agents/rcf/out/<name>/index.html` |
| Tables behind it: one row per case, class quantiles, the case comparison | `agents/rcf/out/data/*.csv` |
| Code and tests | `agents/rcf/src/rcfkit/`, `agents/rcf/tests/` |
| A review, if someone else's study is the starting point | `agents/rcf/out/<name>-review.md` and web page |

Reports are written with `syskit.report.Report` and `syskit.charts.Chart`, so
that the Markdown and the web page come from the same blocks and every number
in the text is computed in the script.

## Procedure

### 1. Read the method and the material

Convert reference papers with the doc skill (`analyze-field-document`;
journal papers: `--style journal`, equations in LaTeX). If there is an
existing study, list what it contains — notebook cells, workbooks, figures,
slides — and what each is for, before judging anything.

### 2. Profile the data

For every file: what one row is, the keys, the units, the period, missing
values, text in number columns, duplicates. Look for columns the earlier work
did not use. Compare a source against another source of the same quantity
where one exists (the resource-account file against Sodir's reserves table
showed two year labels exchanged).

### 3. Reproduce before you change

When reviewing a study, rewrite its calculation as functions
(`rcfkit.expert`) and match its printed numbers first. Then change one choice
at a time and record what each does (`rcfkit.expert.steps`). A finding that
cannot be shown as a number is an opinion.

### 4. Write the class down

In the report, before the statistics: which cases, which estimate, which
outcome, which start, and the count of cases left out by each rule
(`rcfkit.fields.candidates` keeps the reason per field). Record this in the
code as named constants, not as filters scattered through a script.

### 5. Measure bias and spread

- Probabilities: reliability table with Wilson intervals; expected against
  actual number of events; Brier score with its decomposition; slope and
  intercept of a recalibration line (`rcfkit.stats`).
- Volumes and other positive quantities: ratio of outcome to estimate —
  median, 10 % and 90 % points, share below the estimate, share within a
  factor of two; the ratio of totals only alongside these.
- Stated ranges: share of outcomes below, inside and above. A range from P90
  to P10 claims 80 % inside.
- Profiles over time: the fraction of the estimate reached after 1, 2, … n
  periods from the start; quantiles per period.
- Every statistic with the number of cases and a 90 % interval (Wilson for
  shares, bootstrap for medians and quantiles).

Use medians and logarithmic axes; ratios are skewed, and a few large cases
decide any mean or total.

### 6. Test out of sample

- Calibration factors and recalibrated probabilities: k-fold
  cross-validation; report the score or the coverage on the held-back part.
- Reference class ranges: rebuild the class as it stood at each case's
  decision date and place the case's later outcome in it
  (`rcfkit.fields.backtest`). The positions should be uniform; report the
  shares below 10 %, inside, above 90 %, and a test of uniformity.
- Score forecasts with a proper scoring rule and against a reference with no
  skill (base rate; class median).

### 7. Check what the class depends on

Test the candidates — size, product, period, operator if available — against
the normalised outcome. Condition the class on what matters and say so;
report the answer for each alternative class beside the chosen one, so the
reader sees how much rides on the definition.

### 8. Look for the cause, where the data allows

Compare the components of the estimate before and after (for volumes: rock
volume, area, column, thickness, net-to-gross, porosity, saturation). This is
what a subsurface team can act on.

### 9. Apply to the case

- Give the forecast twice: from what was on record at the decision date, and
  from the full record.
- Put the inside view on the same clock and in the same units.
- Use published calibration factors (Nesvold & Bratvold, Table B.3) on the
  inside-view forecast as a second, independent outside view.
- State where the outcome fell in each forecast. One case ranks nothing; the
  back-test is the evidence for the method.
- Where no class exists for the estimate as a whole (volume in place at
  sanction), calibrate it by component: apply the class of undrilled
  prognoses (`rcfkit.inplace`) to the part whose stated uncertainty is that
  of a prognosis, leave the well-determined part as stated, and show a milder
  treatment beside it. `agents/dmx/out/volve-concept-basis.md` is the worked
  example.

### 10. Report

For a reservoir engineer: the question in plain words, then the answer, then
the evidence. Say *low* and *high*, and state once which percentile names the
sources use. Each chart has a caption saying what is plotted, how many cases,
and from which data. End with what the record supports for each estimate, the
limits, and what was not verified.

### 11. Finish

`make rcf-volve` (or the study's own target), `make check`, add what was
learned to this skill, commit with an `rcf:` subject.

## Things that went wrong in the first study

- **Averaging over the wrong unit.** Mean probability per well against "any
  discovery in the well" made low probabilities look four times too low. Per
  prospect they were right.
- **A stand-in that only rescales.** Recoverable volume over a fixed recovery
  factor is not volume in place; the data had in-place columns.
- **Adding alternatives.** An oil case and a gas case of one prospect are
  alternatives: probabilities add, volumes are weighted, neither is summed
  with the other's.
- **A label that says more than the data.** "Discovery in-place" was the sum
  of pre-drill prognoses.
- **Estimates from after the fact.** The nearest resource-account year was up
  to 23 years after approval.
- **Calendar years.** The median first-year fraction was 0.04 by calendar
  year and 0.09 by 12 months from first production.
- **Opposite percentile names.** The paper's F10 is the low case; the PDO's
  P10 is the high case.
- **Class boundaries in floating point.** 0.3 must fall in 0.3–0.4;
  `numpy.linspace` edges put it below.
- **Negative months.** Sodir books corrections as negative production;
  cumulative series can dip.
- **Formatting tools reach into delivered material.** `ruff format` rewrites
  notebooks; `agents/rcf/study` is excluded in `pyproject.toml`.
- **A premise taken from a label.** "West" was first written up as undrilled;
  the PDO does not say which wells lie in which area, and the discovery well
  is in what an earlier report called the western segment. Classify a
  component by the uncertainty the source states for it, and say what the
  source does not tell.
- **Numbers typed into text.** Every figure in a report comes from the
  script; a sentence that says "the median" must be computed from the same
  sample as the number beside it.

## Data on hand

| Data | Where | Use |
|---|---|---|
| Exploration prognoses and results, 629 wells 1989–2024 | `agents/rcf/study/data/2026-11 PrognosisResultData_Released.xlsx`; tidy: `rcfkit.data.prospects()` | Probability of discovery; volumes and volume factors before and after drilling |
| Reserves per field and year, 1990–2021 | `agents/rcf/study/data/RCB_reserves.xlsx`; `rcfkit.data.resource_account()` | Estimate at PDO approval |
| Sodir field tables (reserves by year from 2004, in place today, production, PDO approvals, investments) | `data/sodir/<date>/`, `agents/rcf/study/data/` | Outcomes |
| Volve plan and discovery estimates | `data/facts/pud2005.csv`, `data/facts/disc1993.csv` | The inside view |

Not available: operators' forecast profiles (confidential); history of
in-place estimates per field; PDO cost estimates per field (probably in the
yearly budget propositions to the Storting; not checked, not collected).
