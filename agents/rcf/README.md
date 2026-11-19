# rcf — reference class forecasting

## Role

rcf holds the knowledge of reference class forecasting and applies it when
another domain needs an estimate challenged with the outside view: how did
comparable estimates in comparable projects turn out?

## Method

1. **Define the forecast variable** and its timing (e.g. recoverable oil as
   estimated at PDO against final recovery).
2. **Define the reference class** with a written inclusion rule, before looking
   at the statistics.
3. **Build the sample** of past cases with estimate and outcome.
4. **Describe the distribution** of outcome relative to estimate (ratio or
   error), including spread, not only the mean.
5. **Position the case** in that distribution and derive an adjusted estimate
   and range.
6. **Report** sample size, exclusions, and how sensitive the result is to the
   class definition.

## Data

Public structured data that supports a reference class for the Norwegian
continental shelf is held as a snapshot in `data/sodir/20261119/` (all fields;
see `docs/data-sources.md`). Read it with `syskit.sodir.read_table`. The Volve
values are also in the fact register, `data/facts/sodir.csv`.

| Sodir table | Coverage | Use |
|---|---|---|
| `field_reserves` | 145 fields, year-end estimate versions 2004–2025 | Evolution of the recoverable-volume estimate per field |
| `field_production_yearly`, `_monthly` | 136 fields | Outcomes |
| `field_investment_yearly` | 142 fields | Cost outcomes (nominal NOK) |
| `field_in_place_volumes` | 139 fields, current estimate only | In-place outcome; no estimate history |

Limits to keep in mind:

- The dataset behind Nesvold & Bratvold (2022) is not shareable (stated in the
  paper), so the reference class has to be rebuilt from public tables.
- Public tables carry no history of in-place estimates, and no operator
  forecast profiles. A reference class for in-place volumes at PDO time needs
  another source or a proxy.
- `field_reserves` versions start in 2004, so estimate-at-approval is only
  available for fields approved from about then.

## Library

`lib/` holds reference papers.

- Nesvold, E. & Bratvold, R.B. (2022). Debiasing probabilistic oil production
  forecasts. *Energy* 258, 124744. doi:10.1016/j.energy.2022.124744 — in `lib/`.

To be obtained and verified:

- Kahneman, D. & Tversky, A. (1979). Intuitive prediction: biases and
  corrective procedures.
- Flyvbjerg, B. (2006). From Nobel Prize to project management: getting risks
  right. *Project Management Journal* 37(3).
- Bratvold, R.B., Mohus, E., Petutschnig, D. & Bickel, E. (2020). Production
  forecasting: optimistic and overconfident — over and over again. *SPE
  Reservoir Evaluation & Engineering* 23(3).

## Environment

`uv sync --group rcf` installs pandas and SciPy.

## Outputs

In `agents/rcf/out/`: the reference dataset (with the snapshot date it was
built from), the class definition, distribution statistics, and adjustment
factors for the requesting domain.

## Quality checks

`agents/sys/GUIDELINES.md` §7, reference class.

## First step

Defined in `docs/startup-assessment.md` §7.
