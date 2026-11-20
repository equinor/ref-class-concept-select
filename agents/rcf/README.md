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
5. **Test** that ranges built this way would have held for cases not used to
   build them.
6. **Position the case** in that distribution and derive an adjusted estimate
   and range. The case is never a member of its own class.
7. **Report** sample size, exclusions, and how sensitive the result is to the
   class definition.

## Skill

The procedure for running or reviewing a reference class study is the skill
[`skills/reference-class-study/SKILL.md`](skills/reference-class-study/SKILL.md),
linked from `.github/skills/` so Copilot CLI loads it. Start from it, and add
to it what the next study teaches.

## Data

| Data | Location | Use |
|---|---|---|
| Expert study: notebook, workbooks, figures, presentation | `study/` — kept as delivered; nothing in it is edited or reformatted | The starting point; reviewed in `out/expert-study-review.md` |
| Exploration prognoses and results, 629 wells spudded 1989–2024 | `study/data/2026-11 PrognosisResultData_Released.xlsx`; tidy table: `rcfkit.data.prospects()` | Probability of discovery; volumes and volume factors before and after drilling |
| Reserves per field and year, 1990–2021 (1996 missing) | `study/data/RCB_reserves.xlsx`; `rcfkit.data.resource_account()` | The estimate at PDO approval. The labels 2020 and 2021 are exchanged in the file and put right by the reader |
| Sodir tables, all fields | `study/data/` (the expert's exports) and `data/sodir/<date>/` (`syskit.sodir.read_table`) | Outcomes: production by month, reserves by year from 2004, volume in place today, PDO approvals, investments |
| Volve plan and discovery estimates | `data/facts/pud2005.csv`, `data/facts/disc1993.csv` (`syskit.facts.read`) | The inside view |

Limits to keep in mind:

- Operators' forecast profiles are confidential (Nesvold & Bratvold, 2022),
  so a class is built from outcomes relative to sanctioned reserves, not from
  forecasts.
- There is no public history of in-place estimates per field, and no public
  table of PDO cost estimates.
- The origin of the prognosis file and of `RCB_reserves.xlsx` is not verified;
  both came with the expert study.

## Library

`lib/` holds reference papers; converted copies are in `lib/md/`, their
figures in `lib/figs/`.

- Nesvold, E. & Bratvold, R.B. (2022). Debiasing probabilistic oil production
  forecasts. *Energy* 258, 124744. doi:10.1016/j.energy.2022.124744. Open
  access, CC BY 4.0. Converted:
  `lib/md/LIB_2022_ENERGY_debiasing_production-forecasts_ENesvold+RBratvold.md`.

To be obtained and verified:

- Kahneman, D. & Tversky, A. (1979). Intuitive prediction: biases and
  corrective procedures.
- Flyvbjerg, B. (2006). From Nobel Prize to project management: getting risks
  right. *Project Management Journal* 37(3).
- Bratvold, R.B., Mohus, E., Petutschnig, D. & Bickel, E. (2020). Production
  forecasting: optimistic and overconfident — over and over again. *SPE
  Reservoir Evaluation & Engineering* 23(3).

## Code

The `rcfkit` package in `src/`.

| Module | Purpose |
|---|---|
| `rcfkit.data` | The study's files as tidy tables: prospects, fields, resource account, production |
| `rcfkit.stats` | Reliability, Brier score, recalibration, bootstrap, coverage, quantile score |
| `rcfkit.exploration` | Probability of discovery and volumes, prognosis against result |
| `rcfkit.fields` | Reference class of fields: membership rules, production fractions, back-test, reserves growth, discovery link |
| `rcfkit.volve` | The Volve case: PDO forecast, reference class forecast, outcome |
| `rcfkit.expert` | The expert study's calculations, reproduced |
| `rcfkit.review`, `rcfkit.study` | The two reports |

`make rcf-volve` rebuilds both reports and the tables.

## Results so far

| Output | Content |
|---|---|
| `out/expert-study-review.md`, `out/expert-study-review/index.html` | Review of the expert study: purpose, method, reproduction, findings, recommendations |
| `out/volve-rcf-study.md`, `out/volve-rcf-study/index.html` | The study redone: exploration, appraisal, reserves, production class, Volve |
| `out/data/prospects.csv` | One row per drilled prospect: probability, outcome, volumes |
| `out/data/fields.csv` | One row per field: approval, sanctioned reserves, start, latest estimates, reason if left out of the class |
| `out/data/production_fractions.csv` | Fraction of sanctioned reserves produced after 1–10 years, per field |
| `out/data/reference_class_quantiles.csv` | Quantiles per class and year, with intervals |
| `out/data/volve_forecasts.csv` | Volve: PDO cases, class forecast, calibrated PDO, outcome |

## Environment

`uv sync --group rcf` installs pandas, SciPy, openpyxl, matplotlib and plotly.

## Quality checks

`agents/sys/GUIDELINES.md` §7, reference class.

## Open points

- Cost: no reference class; the PDO estimates of other fields are not
  collected.
- In-place at sanction: no public record to build a class from.
- The paper's density score (metalog fit and CRPS) is not implemented; a
  three-point quantile score stands in.
- The class is conditioned on size by a cut (within a factor of four), not by
  continuous weights as in the paper.
