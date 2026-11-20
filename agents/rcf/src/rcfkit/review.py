"""Review of the expert study in ``agents/rcf/study``: Markdown report and web page.

    python -m rcfkit.review build

Every number is computed here from the study's own data: the expert's
results are first reproduced (``rcfkit.expert``), then compared with the same
analysis done on a sounder basis (``rcfkit.exploration``, ``rcfkit.fields``).
"""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from rcfkit import data, expert, exploration, fields, volve
from syskit.charts import BLUE, GREY, INK, ORANGE, Chart, Series
from syskit.paths import repo_root
from syskit.report import Report, number, percent

OUT = "agents/rcf/out"
STUDY = "agents/rcf/study"
PAPER = "agents/rcf/lib/md/LIB_2022_ENERGY_debiasing_production-forecasts_ENesvold+RBratvold.md"


def slide_pictures(target: Path) -> dict[int, Path]:
    """The charts of slides 4 to 6, which exist only inside the presentation."""
    target.mkdir(parents=True, exist_ok=True)
    result = {}
    with zipfile.ZipFile(repo_root() / STUDY / "presentation" / "rcf_volve.pptx") as deck:
        for slide in (4, 5, 6):
            path = target / f"expert-study-review_slide{slide}.png"
            path.write_bytes(deck.read(f"ppt/media/image{slide}.png"))
            result[slide] = path
    return result


def reliability_chart(well: dict, prospect: dict) -> Chart:
    def series(bins: list[dict], name: str, color: str) -> Series:
        return Series(
            "errorbar",
            [b["forecast"] for b in bins],
            [b["observed"] for b in bins],
            name=name,
            color=color,
            low=[b["low"] for b in bins],
            high=[b["high"] for b in bins],
            connect=True,
            labels=[f"n = {b['n']}" for b in bins],
        )

    return Chart(
        "reliability",
        "Stated probability of discovery against the share that were discoveries",
        "Stated probability (mean of the bin)",
        "Share that were discoveries",
        [
            Series("line", [0, 1], [0, 1], name="Perfect calibration", color=GREY, dash=True),
            series(well["bins"], "Per well, as in the expert study", ORANGE),
            series(prospect["bins"], "Per prospect", BLUE),
        ],
        x_range=(0, 1),
        y_range=(0, 1.02),
    )


def profile_chart(calendar: dict, monthly, target) -> Chart:
    years = list(fields.HORIZONS)
    return Chart(
        "profile",
        "Cumulative production as a fraction of sanctioned reserves",
        "Years of production",
        "Fraction of sanctioned reserves",
        [
            Series(
                "band", years, low=calendar["low"], high=calendar["high"], color=ORANGE,
                name="Expert study, 10–90 % of fields",
            ),
            Series("line", years, calendar["median"], name="Expert study, median", color=ORANGE),
            Series(
                "band", years, low=list(monthly["q10"]), high=list(monthly["q90"]), color=BLUE,
                name="From first production by month, 10–90 %",
            ),
            Series(
                "line", years, list(monthly["q50"]), color=BLUE,
                name="From first production by month, median",
            ),
            Series(
                "line", list(volve.YEARS), [target[y] for y in volve.YEARS], color=INK,
                name="Volve, actual", width=2.6,
            ),
        ],
        y_range=(0, 1.8),
    )  # fmt: skip


def build_report() -> Report:
    figures = repo_root() / OUT / "figs"
    slides = slide_pictures(figures)
    study = repo_root() / STUDY

    # Reproductions of the expert's numbers.
    e_prob = expert.probability_calibration()
    e_vol = expert.volumes()
    e_link = expert.link_file()
    e_class = expert.reference_class()
    e_quant = e_class[list(fields.HORIZONS)].quantile([0.1, 0.5, 0.9])
    steps3, steps5 = expert.steps(3), expert.steps(5)

    # The same questions on a sounder basis.
    prob = exploration.probability_results()
    wells = exploration.well_level()
    vol = exploration.volume_results()
    link = fields.discovery_link()
    link_file = pd.read_excel(data.study_data() / "fid_reserves_vs_discovery_inplace_total.xlsx")
    link_check = link.merge(link_file, left_on="field", right_on="Feltnavn")
    same_sum = int(
        np.isclose(
            link_check["rows_prognosis"], link_check["discovery_total_inplace"], atol=0.02
        ).sum()
    )
    table = fields.profiles("oe")
    others = fields.select(table, exclude=volve.FIELD)
    monthly = fields.distribution(others, bootstrap=300).set_index("years")
    effects = fields.class_effects(table, 3)
    backtest = fields.backtest(table)
    volve_row = table.set_index("field").loc[volve.FIELD]
    volve_fraction = {y: float(volve_row[y]) for y in volve.YEARS}
    all_candidates = fields.candidates()
    low_bin_well, low_bin_prospect = e_prob["bins"][0], prob["bins"][0]
    hindsight = int((e_class["gap"] > 1).sum())
    after_2005 = int((e_class["start"] > 2005).sum())
    early_start = int((e_class["start"] < e_class["approved"]).sum())
    gas_fields = int((table["oil_share"] < fields.OIL_SHARE).sum())
    v_prospects = volve.prospect()

    report = Report(
        "Review of the expert's reference class study on Volve",
        "What the study in `agents/rcf/study` set out to do, how it did it, which of its results "
        "hold when the calculations are repeated, and how to make the study more robust. "
        "Written for a reservoir engineer; every number is recomputed from the study's own data.",
        generator="python -m rcfkit.review build",
    )

    # ------------------------------------------------------------------ summary
    report.section("Summary")
    report.text(
        "The study asks one question at four points of a field's life: *how did estimates like "
        "this one turn out before?* It uses public Norwegian shelf data to compare estimates with "
        "outcomes for exploration wells and for field developments, and then forecasts Volve's "
        "production from the record of other fields instead of from a reservoir model.",
        "The idea is sound and the main message survives a recalculation: volumes are "
        "over-estimated before drilling, and the 2005 Volve plan gave a far narrower range than "
        "the record of other fields supports. Several of the individual numbers do not survive, "
        "because of how wells, prospects, years and volumes were counted.",
    )
    report.cards(
        [
            (
                "Chance of discovery, lowest class",
                f"{percent(low_bin_well['observed'])} → {percent(low_bin_prospect['observed'])}",
                f"Share of discoveries where under 10 % was stated: per well (expert) and per "
                f"prospect. Stated: {percent(low_bin_prospect['forecast'])}",
            ),
            (
                "Volume found over volume prognosed",
                f"{e_vol['in_place']['result'] / e_vol['in_place']['prognosis']:.2f} → "
                f"{vol['ip']['of_totals']:.2f}",
                "Ratio of totals for discoveries: expert's sums per well, and prospect by "
                "prospect with the in-place volumes the data holds",
            ),
            (
                "Fraction of reserves produced after 1 year",
                f"{e_quant.loc[0.5, 1]:.2f} → {monthly.loc[1, 'q50']:.2f}",
                "Median of fields: by calendar year (expert), and by 12 months from first "
                "production",
            ),
            (
                "Fields in the production class",
                f"{len(e_class)} → {len(others)}",
                f"{hindsight} of the expert's fields have a reserves figure from two or more "
                "years after approval, up to 23 years",
            ),
        ]
    )
    report.table(
        ["Part of the study", "Expert's result", "Reproduced", "After recalculation"],
        [
            [
                "1. Probability of discovery",
                "Low probabilities are far too low: 30 % discoveries where 7 % was stated",
                "Yes",
                f"Not confirmed. Per prospect the stated probabilities are borne out: "
                f"{prob['all']['expected_discoveries']:.0f} discoveries expected, "
                f"{prob['all']['discoveries']} made",
            ],
            [
                "2. Recoverable volume, discovery wells",
                "Results far below prognoses (figure only)",
                "Yes",
                f"Confirmed in direction. Median result is {vol['rec']['median']:.2f} of the "
                "prognosis",
            ],
            [
                "3. Volume in place, discovery wells",
                f"Results sum to {e_vol['in_place']['result'] / e_vol['in_place']['prognosis']:.2f}"
                " of prognoses; correlation 0.06",
                "Yes",
                f"Confirmed in direction, about half as severe: {vol['ip']['of_totals']:.2f} of "
                f"totals, median {vol['ip']['median']:.2f}",
            ],
            [
                "4. Reserves at sanction against discovery volume in place",
                f"Median ratio {e_link['median_ratio']:.2f}; Volve an outlier at "
                f"{e_link['volve_ratio']:.1f}",
                "Yes",
                "The volume used is the pre-drill prognosis, not the discovery. Volve is an "
                "outlier because the well was drilled for gas prospects",
            ],
            [
                "5. Reference class forecast of production",
                f"Median field has produced {e_quant.loc[0.5, 5]:.2f} of its reserves after "
                "five years; Volve close to the median after nine",
                "Yes",
                f"Median {monthly.loc[5, 'q50']:.2f} after five years when counted from first "
                "production; ranges hold up in a back-test",
            ],
            ["6. Planned against actual capital cost", "Slide without content", "—", "Not done"],
        ],
        left=(0, 1, 2, 3),
    )

    # ------------------------------------------------------------------ method
    report.section("Reference class forecasting, in brief", "Method")
    report.text(
        "A forecast made from the details of a project — maps, a reservoir model, a drilling "
        "schedule — is an *inside view*. Research on judgement, summarised in the reference "
        "paper, finds inside views of projects too optimistic and too sure of themselves. "
        "Reference class forecasting takes the *outside view*: it sets the details aside and asks "
        "how a class of comparable past cases turned out relative to what was forecast for them. "
        "The spread of those outcomes is the forecast range for the new case.",
        f"The reference paper for this work is Nesvold and Bratvold (2022), converted to "
        f"Markdown in [`{PAPER.rsplit('/', 1)[1]}`](../lib/md/{PAPER.rsplit('/', 1)[1]}). "
        "Its content, in the terms used below:",
    )
    report.table(
        ["Element", "In the paper"],
        [
            [
                "Data",
                "71 oil fields on the Norwegian shelf with first production 1995–2020. For each, "
                "the operator's forecast of cumulative oil at the investment decision — a low "
                "case, a mean and a high case per year — and the production that followed. The "
                "forecasts are confidential",
            ],
            [
                "Alignment",
                "Forecast and production are lined up at production start, so a late start does "
                "not count as a shortfall. The first calendar year is left out because fields "
                "start in different months",
            ],
            [
                "Optimism",
                "Production over mean forecast. About 0.8 during the first five years; almost "
                "70 % of fields below the mean after four years",
            ],
            [
                "Overprecision",
                "Share of outcomes inside the low–high range, which should hold 80 %. Under 30 % "
                "after two years, about 50 % later; at least 25 % of fields below the low case "
                "throughout the first ten years",
            ],
            [
                "Reference forecast",
                "A production profile made only from 19 abandoned fields, scaled to the new "
                "field's expected recovery, with low and high set at 0.4 and 1.6 times it",
            ],
            [
                "Calibration",
                "Multipliers per production year that move the operator's forecast to where the "
                "record says it should be: the mean times 0.78–0.82 in years 2–5, a low case of "
                "about 0.3 times the mean, a high case of 1.1–1.4 times the mean (Table B.3)",
            ],
            [
                "Validation",
                "Ten-fold cross-validation; shares below, inside and above the range; a "
                "probability plot with a test of uniformity; a skill score from a proper scoring "
                "rule (CRPS); splits by period and by field size",
            ],
            [
                "Findings",
                "The reference forecast, which uses no knowledge of the field, beats the "
                "operators' forecasts. Calibrated forecasts are only slightly better than the "
                "reference. The low and high cases add nothing to the mean. Bias has not "
                "lessened over time and does not depend on field size",
            ],
        ],
        left=(0, 1),
    )
    report.note(
        "Low and high are named in opposite ways in the sources. The paper writes F10 for the "
        "low case (10 % of outcomes below) and F90 for the high case. Norwegian plans, the Volve "
        "PDO among them, write P90 for the low case (90 % chance of exceeding it) and P10 for "
        "the high case. The expert study follows the paper. This review writes *low* and *high*."
    )

    # ------------------------------------------------------------------ purpose
    report.section("What the study is for, and how the expert reasons", "Purpose")
    report.text(
        "The material is a notebook with four calculations, a workbook, six figures and a "
        "presentation of seven slides. It has no written text, so the purpose is read from the "
        "slide titles, the comments in the notebook and the order of the work.",
        "The study follows a volume estimate through the decisions of a field's life and checks "
        "it against the record at each one:",
    )
    report.table(
        ["Decision", "Estimate made", "Outcome it is checked against", "Slide"],
        [
            [
                "Drill an exploration well",
                "Technical probability of discovery",
                "Whether the well was a discovery",
                "1 Calibration of technical exploration probability",
            ],
            [
                "Drill an exploration well",
                "Volume expected if there is a discovery",
                "Volume reported after drilling",
                "2 Volume calibration",
            ],
            [
                "Sanction a development",
                "Reserves in the plan for development",
                "The volume the exploration data gives for the discovery well",
                "(figure only)",
            ],
            [
                "Sanction a development",
                "Reserves in the plan, and when they will be produced",
                "Production year by year",
                "3 Reference class forecasting; 4–6 Volve",
            ],
            ["Sanction a development", "Capital cost", "Actual cost", "7 (empty)"],
        ],
        left=(0, 1, 2, 3),
    )
    report.text("The reasoning has the same six steps each time:")
    report.bullets(
        [
            "Choose a quantity that is forecast when a decision is made and observed later.",
            "Find a public record that holds both, for many cases. Where the forecast itself is "
            "not public, take a stand-in: the reserves in the resource account of the approval "
            "year for the PDO estimate; recoverable volume over a fixed recovery factor for "
            "volume in place.",
            "Divide outcome by forecast, so that large and small cases can be pooled.",
            "Describe the pooled ratios: where their middle lies (bias) and how wide they spread "
            "(uncertainty). On logarithmic axes against lines of factor 2 and 10, or as the "
            "10 %, 50 % and 90 % points of the fields year by year.",
            "Turn the description into a forecast for a new case by multiplying with that "
            "case's own estimate. For Volve: the fractions of the class times an expected "
            "recovery of 13.7 million Sm3 o.e.",
            "Set this beside the operator's forecast and beside what happened.",
        ],
        numbered=True,
    )
    report.text(
        "Two things distinguish this from the paper. The paper *calibrates forecasts*: it needs "
        "the operators' forecast profiles, which are confidential. The expert *builds the class "
        "from outcomes only* — production relative to sanctioned reserves — which needs no "
        "forecast profile and can be done with open data. And where the paper fixes the range at "
        "0.4 and 1.6 times the reference, the expert reads the range off the fields themselves. "
        "Both are good moves. What the study does not take over from the paper is its testing: "
        "no result is checked on cases held back, and no range carries an uncertainty."
    )

    # ------------------------------------------------------------------ steps
    report.section("The five analyses, one by one", "Analyses")
    report.heading("1. Is the stated probability of discovery borne out?")
    report.text(
        "*Data.* `2026-11 PrognosisResultData_Released.xlsx`: 1 995 rows for 629 exploration "
        "wells spudded 1989–2024. Each prospect a well was to test has one or more *prognosis* "
        "rows (probability of discovery; volumes in place and recoverable with low, central and "
        "high values; rock volume, column height, porosity and the other factors of the volume "
        "equation) and one *result* row (discovery yes or no; the same quantities after "
        "drilling).",
        "*Method.* All rows of a well are merged: the probability is the mean over its prognosis "
        "rows, the outcome is a discovery if any result row says so. Wells are grouped by "
        "probability in steps of 0.1, and the share of discoveries in each group is plotted "
        "against the mean probability, with Wilson intervals. This is a reliability diagram: "
        "of the wells given about 20 %, were about 20 % discoveries?",
        f"*Result.* {e_prob['wells']} wells. Discoveries are more frequent than stated in every "
        f"class below 0.7; where under 10 % was stated, {percent(low_bin_well['observed'])} were "
        "discoveries.",
    )
    report.image(
        study / "figures" / "calibration_plot.png",
        "The expert's figure (slide 1). It was made with different settings from the notebook "
        "as saved: it shows 610 wells, the notebook's output 575.",
    )
    report.heading("2 and 3. Is the prognosed volume found?")
    report.text(
        "*Method.* For wells with a discovery, the four recoverable volumes (oil, gas, and the "
        "liquid and gas associated with each) are added over all prognosis rows, and over all "
        "result rows, of the well. Result is plotted against prognosis on logarithmic axes. For "
        "volume in place, the same recoverable volumes are divided by fixed recovery factors, "
        "0.35 for oil and 0.60 for gas.",
        f"*Result.* {e_vol['in_place']['n']} wells have both sums above zero. Nearly all lie "
        "below the line of equality, many by a factor of ten. The results add up to "
        f"{number(e_vol['in_place']['result'])} against "
        f"{number(e_vol['in_place']['prognosis'])} million Sm3 o.e. prognosed, a ratio of "
        f"{e_vol['in_place']['result'] / e_vol['in_place']['prognosis']:.2f}. The correlation "
        f"is {e_vol['in_place']['correlation']:.2f}.",
    )
    report.image(
        study / "figures" / "inplace_result_vs_prognosis_loglog.png",
        "The expert's figure (slide 2): result against prognosis, per discovery well.",
    )
    report.heading("4. How do sanctioned reserves relate to the volume at discovery?")
    report.text(
        "*Data.* A link file made outside the notebook: 37 fields, their discovery well, a "
        "“discovery in-place” volume from the prognosis data, and the oil and gas reserves in "
        "the resource account (`RCB_reserves.xlsx`) for the year of approval.",
        f"*Result.* {e_link['n']} fields. Reserves at sanction are typically a third of the "
        f"discovery volume (median {e_link['median_ratio']:.2f}), with a scatter of more than "
        f"a factor of ten either way. Volve stands out with reserves {e_link['volve_ratio']:.1f} "
        "times the discovery volume.",
    )
    report.image(
        study / "figures" / "fid_reserves_vs_discovery_inplace_loglog.png",
        "The expert's figure: reserves at sanction against “discovery in-place volume”.",
    )
    report.heading("5. A production forecast from the record of other fields")
    report.text(
        "*Data.* Sodir's yearly production per field, the dates of PDO approvals, and the "
        "resource-account reserves.",
        "*Method.* For each field: the reserves of the account year nearest its first approval; "
        "the first calendar year with production as year 1; cumulative production through "
        "years 1 to 10 divided by those reserves. Across the fields with ten years of history, "
        "the 10 %, 50 % and 90 % points of that fraction are taken year by year. Multiplied by "
        "an expected recovery they are a forecast with a range — for Volve, by 13.7 million "
        "Sm3 o.e.",
        f"*Result.* {len(e_class)} fields. The median field has produced "
        f"{e_quant.loc[0.5, 3]:.2f} of its sanctioned reserves after three years, "
        f"{e_quant.loc[0.5, 5]:.2f} after five and {e_quant.loc[0.5, 10]:.2f} after ten; one "
        f"field in ten has passed {e_quant.loc[0.9, 10]:.2f} after ten years, one in ten has "
        f"not reached {e_quant.loc[0.1, 10]:.2f}.",
        "For Volve the slides show three things. The range from the record is very wide: 3.6 to "
        "20 million Sm3 o.e. after nine years. The PDO's range is a fraction of it and starts "
        "from nothing: the three PDO cases nearly coincide for the first two years. And Volve's "
        "actual "
        "production ran close to the PDO for two years, fell below the PDO's low case from the "
        "third year, and ended near the median of the record.",
    )
    report.image(
        slides[6],
        "The expert's chart (slide 6): cumulative production of Volve in million Sm3 o.e.; the "
        "PDO and its low and high cases in blue, the reference class forecast and its 10 % and "
        "90 % points in red, the outcome in black. The PDO is moved one year so that its first "
        "year falls on the actual first year, 2008.",
    )

    # ------------------------------------------------------------------ findings
    report.section("What the recalculation shows", "Findings")
    report.heading("Probability of discovery: the unit of count decides the result")
    report.text(
        f"{wells['wells_with_several_prospects']} of the {wells['wells']} wells with a stated "
        "probability test more than one prospect, and some prospects have alternative prognoses "
        "(an oil case and a gas case). Averaging the probabilities of a well and counting any "
        "discovery compares two different things: the chance that one given prospect holds "
        "hydrocarbons, and the event that at least one of several does. A well with three "
        "prospects at 10 % each has an average of 10 % and a chance of about 27 % of at least "
        "one discovery. Discoveries in zones that had no prognosis are counted as well.",
        f"Counted per prospect — {prob['all']['n']} prospects with a stated probability and a "
        f"result — the mean stated probability is {percent(prob['all']['mean_forecast'], 1)} "
        f"and {percent(prob['all']['observed_rate'], 1)} were discoveries. In the lowest class "
        f"{percent(low_bin_prospect['forecast'])} was stated and "
        f"{percent(low_bin_prospect['observed'])} found. The expert's conclusion that low "
        "probabilities are much too low is a product of the averaging.",
    )
    report.chart(
        reliability_chart(e_prob, prob),
        "Bars are 90 % Wilson intervals. Orange is the expert study's count as its notebook "
        f"makes it (mean probability per well; a discovery if any result row of the well is "
        f"one; {e_prob['wells']} wells). Blue counts each prospect once ({prob['all']['n']} "
        "prospects). Data: the study's prognosis file.",
    )
    report.text(
        "Smaller points on the same analysis: the intervals are computed with z = 1.645, which "
        "is a 90 % interval, and labelled 95 %. Rows whose evaluation year is written as a "
        "range (“1997/1998”) are dropped by the year filter, prognosis and result independently "
        "of each other. And the figure in the presentation does not match the notebook's saved "
        "output."
    )

    report.heading("Volumes: right direction, wrong size")
    report.bullets(
        [
            "The data has volumes in place for both prognosis and result. The "
            "study instead divides recoverable volumes by fixed recovery factors. That only "
            "rescales the recoverable comparison; it is not a comparison of volumes in place, "
            "and recoverable results are missing for many discoveries.",
            "Alternative prognoses of one prospect are added together, although only one of "
            "them can come true.",
            "The prognoses of a well's dry prospects are included in the well's sum, while the "
            "result holds only what was found.",
            "The headline figures are a ratio of sums, which a handful of large prospects "
            "decide, and a correlation of untransformed volumes "
            f"({e_vol['in_place']['correlation']:.2f}), which says little about data that span "
            f"four orders of magnitude; on logarithms it is "
            f"{e_vol['in_place']['log_correlation']:.2f} for the same wells.",
        ]
    )
    report.text(
        f"Prospect by prospect, using the in-place columns and weighting alternative cases by "
        f"their probabilities, {vol['ip']['n']} discoveries have a prognosed and a resulting "
        f"volume in place. The median result is {vol['ip']['median']:.2f} of the prognosis "
        f"(90 % interval {vol['ip']['median_ci'][0]:.2f}–{vol['ip']['median_ci'][1]:.2f}), "
        f"{percent(vol['ip']['share_below_forecast'])} of results are below the prognosis, and "
        f"the ratio of totals is {vol['ip']['of_totals']:.2f} — against "
        f"{e_vol['in_place']['result'] / e_vol['in_place']['prognosis']:.2f} in the study. The "
        "over-estimation is real and large; it is about half as severe as the study's number "
        "says."
    )

    report.heading("The discovery volume in the link file is a pre-drill prognosis")
    volve_prog = float(v_prospects["ip_oe_prog"].sum())
    volve_res = float(v_prospects.loc[v_prospects["discovery"] == 1, "ip_oe_res"].sum())
    report.text(
        f"For {same_sum} of the 37 fields, the “discovery in-place” volume equals the plain sum "
        "of the in-place volumes over every prognosis row of the discovery well — pre-drill, "
        "including dry prospects and both alternatives where there are two. The notebook "
        "describes the figure as relating post-drill in-place estimates to sanctioned "
        "resources; it relates pre-drill prognoses to them.",
        f"This explains Volve's position. Well 15/9-19 SR was drilled in 1993 for two gas "
        f"prospects with {volve_prog:.2f} billion Sm3 of gas in place between them. The first "
        "was dry. The second held oil, not gas: the result row gives "
        f"{volve_res:.2f} million Sm3 o.e. in place. The reserves of 13.2 million Sm3 o.e. "
        "sanctioned twelve years later belong to an oil accumulation the prognosis did not "
        "describe. Volve is not an outlier of estimation; the comparison does not apply to it.",
    )

    report.heading("The production class: who is in it, and how its years are counted")
    report.table(
        ["Point", "What the study does", "Why it matters"],
        [
            [
                "Reserves “at FID”",
                f"Nearest account year, however far. For {hindsight} fields it is two or more "
                "years after approval; the account starts in 1990, so fields approved in "
                "the 1970s and 1980s get a figure from 1990–1993 (Gyda, approved 1987: from "
                "2010)",
                "For those fields the denominator already contains ten to twenty years of "
                "production experience. It is not an estimate made at the decision",
            ],
            [
                "First year",
                "First calendar year with any production",
                "A field that starts in November has almost nothing in year 1. The median "
                f"fraction after one year is {e_quant.loc[0.5, 1]:.2f}; counted in 12-month "
                f"periods from first production it is {monthly.loc[1, 'q50']:.2f}. For "
                f"{early_start} fields the first year lies before the approval; Balder (1991) "
                "and Grane (1996) have small volumes recorded years before they started up",
            ],
            [
                "Volve",
                "Is itself one of the fields",
                "The case being forecast should not be in its own reference class. The effect "
                f"on the percentiles is small with {len(e_class)} fields",
            ],
            [
                "Hindsight",
                f"{after_2005} of the fields started producing after 2005",
                "Fine for a method to use from now on. As a test of what could have been "
                "forecast for Volve in 2005 it uses knowledge from the future",
            ],
            [
                "Units",
                "Production in all oil equivalents (with NGL and condensate) over reserves of "
                "oil and gas only; Volve scaled with 13.7, which includes NGL and condensate",
                "Numerator and denominator differ. Volve's oil and gas reserves in the same "
                "account are 13.18",
            ],
            [
                "Last year",
                "2026 is in the data with eight months",
                "Fields that started in 2017 get an incomplete tenth year",
            ],
            [
                "Kind of field",
                f"Oil and gas fields of all sizes together; {gas_fields} of "
                f"{len(table)} fields approved since 1990 are mainly gas",
                f"Size matters: larger fields produce their reserves more slowly (rank "
                f"correlation {effects['size_rho']:.2f} between size and fraction after three "
                f"years, p = {effects['size_p']:.4f}). Oil against gas does not "
                f"(p = {effects['product_p']:.2f})",
            ],
            [
                "Uncertainty and testing",
                "None",
                "The 10 % and 90 % points of a hundred fields are themselves uncertain, and "
                "whether such ranges would have held for later fields is not examined",
            ],
            [
                "The PDO curves",
                "Entered in the workbook; source not stated",
                "They follow PDO Table 4.5 year by year but run on past the economic cut-off "
                "the table applies, and total 11.88 million Sm3 of oil where the PDO gives "
                "11.40. The total equals the first resource-account entry for Volve",
            ],
        ],
        left=(0, 1, 2),
    )
    steps_rows = []
    for row3, row5 in zip(steps3, steps5, strict=True):
        steps_rows.append(
            [
                row3["step"],
                str(row3["n"]),
                f"{row3['low']:.2f} / {row3['median']:.2f} / {row3['high']:.2f}",
                f"{row5['low']:.2f} / {row5['median']:.2f} / {row5['high']:.2f}",
            ]
        )
    steps_rows.append(
        [
            "… and time counted in 12-month periods from first production after approval",
            f"{int(monthly.loc[3, 'n'])}",
            f"{monthly.loc[3, 'q10']:.2f} / {monthly.loc[3, 'q50']:.2f} / "
            f"{monthly.loc[3, 'q90']:.2f}",
            f"{monthly.loc[5, 'q10']:.2f} / {monthly.loc[5, 'q50']:.2f} / "
            f"{monthly.loc[5, 'q90']:.2f}",
        ]
    )
    report.table(
        ["Calculation", "Fields", "After 3 years: low / median / high", "After 5 years"],
        steps_rows,
        left=(0,),
        caption="What each correction does to the fraction of sanctioned reserves produced. "
        "Low and high are the 10 % and 90 % points of the fields.",
    )
    report.text(
        "The corrections to membership and units move the result little. The count of years "
        "moves it a great deal in the early years, which are the ones that matter for present "
        "value: the study's median field is about half a year behind a field counted from its "
        "first month. Volve started in February, so against the study's class it looks "
        "ahead of the record by more than it was."
    )
    report.chart(
        profile_chart(
            {
                "low": list(e_quant.loc[0.1]),
                "median": list(e_quant.loc[0.5]),
                "high": list(e_quant.loc[0.9]),
            },
            monthly,
            volve_fraction,
        ),
        f"Orange: the expert study's class ({len(e_class)} fields, calendar years, all oil "
        f"equivalents). Blue: fields with a PDO approved from 1990 and a reserves estimate from "
        f"within a year of approval, Volve left out ({int(monthly.loc[1, 'n'])} fields at one "
        f"year, {int(monthly.loc[10, 'n'])} at ten), oil and gas, 12-month periods from the "
        "first month of production. Black: Volve, oil and gas over its sanctioned 13.18 million "
        "Sm3 o.e. Data: Sodir production by month and the study's resource-account file.",
    )
    report.heading("Data and reproducibility")
    report.bullets(
        [
            "In `RCB_reserves.xlsx` the rows labelled 2020 and 2021 are exchanged: for 2004–2019 "
            "the file agrees with Sodir's reserves table of the same year, for 2020 and 2021 "
            "with the other year. No field in the ten-year class is affected.",
            "The link file of analysis 4 and the charts of slides 4–6 were made outside the "
            "notebook; the charts exist only as pictures in the presentation. The workbook "
            "behind them holds typed-in values without source.",
            "`field_in_place_volumes.xlsx` and `field_reserves (1).xlsx` are in the data folder "
            "and not used. The first holds today's in-place volumes per field, which is the "
            "natural outcome for analysis 4.",
            "The notebook cells depend on being run in order (the second and third reuse "
            "the table filtered by the first), and write figures to two different folders.",
            "The origin of the prognosis file is not stated. Its name and columns point to "
            "Sodir's record of exploration-well prognoses and results; this was not verified.",
        ]
    )

    # ------------------------------------------------------------------ holds
    report.section("What holds", "What holds")
    report.bullets(
        [
            "Explorers on the shelf over-estimate what a discovery will hold, by a wide margin, "
            "and their stated ranges are far too narrow. This is the strongest result in the "
            "data and the study found it.",
            "Reserves at sanction are a poor guide to what a field will have produced after a "
            "given number of years: the 10–90 % range across fields spans a factor of four to "
            "five. The study's way of turning this into a forecast range is sound.",
            f"For Volve, the outcome sat inside the range of the record throughout, and below "
            f"the PDO's low case from the third year. A back-test of the corrected class on "
            f"{backtest[3]['n']} later fields puts {percent(backtest[3]['inside'])} of their "
            "three-year outcomes inside its 10–90 % range; the paper found about 50 % or "
            "less for operators' forecasts.",
            "The step from the paper's method to one that needs only public data is the "
            "study's real contribution, and it is what makes the method usable in this project.",
        ]
    )
    report.text(
        "One conclusion should be dropped: that low discovery probabilities are too low. "
        "And the closeness of Volve's final production to the class median is one field; it "
        "shows that the outcome was unremarkable against the record, not that the median is a "
        "good predictor."
    )

    # ------------------------------------------------------------------ recommendations
    report.section("Recommendations", "Recommendations")
    report.table(
        ["#", "Recommendation", "Reason"],
        [
            [
                "1",
                "Count the case the estimate was made for: the prospect, not the well; one "
                "probability and one volume per prospect, with alternative cases combined by "
                "their probabilities",
                "Removes the mismatch between estimate and outcome in analyses 1–3",
            ],
            [
                "2",
                "Use the quantity the data holds. Volumes in place from the in-place columns; "
                "today's field volumes from `field_in_place_volumes.xlsx`",
                "No fixed recovery factors; more cases",
            ],
            [
                "3",
                "Write the reference class down before computing: which fields, which estimate, "
                "which outcome, which start. Admit a field only if its estimate dates from the "
                "decision",
                "Keeps hindsight out of the denominator and makes the class reviewable",
            ],
            [
                "4",
                "Count time from the first month of production after approval, in 12-month periods",
                "Removes the start-month effect; Sodir publishes production by month",
            ],
            [
                "5",
                "Keep the case out of its own class, and state what was knowable at its "
                "decision date",
                "Separates a method for future use from a test on a past case",
            ],
            [
                "6",
                "Same units above and below the line; oil alone for comparison with an oil "
                "forecast",
                "The PDO's range is given for oil only",
            ],
            [
                "7",
                "Describe both biases with numbers: the middle of outcome over estimate, and "
                "the share of outcomes below, inside and above the stated range",
                "The paper's two measures; the prognosis data states low and high values that "
                "the study does not use",
            ],
            [
                "8",
                "Put an interval on every statistic (bootstrap), and report the number of "
                "cases with it",
                "Shows which differences are within noise",
            ],
            [
                "9",
                "Test out of sample: rebuild the class as it stood at each field's approval "
                "and see where the field then fell. Cross-validate any calibration factor",
                "The only evidence that the ranges mean what they say",
            ],
            [
                "10",
                "Check what the class depends on — size, product, period — and condition on "
                "what matters; report the result for each alternative class",
                "Size shifts the production fractions; product does not",
            ],
            [
                "11",
                "Score forecasts with a proper scoring rule against a no-skill reference",
                "The paper's skill score; shows whether detail adds anything",
            ],
            [
                "12",
                "Use the paper's published calibration factors on the PDO forecast as a second "
                "outside view",
                "Independent of the class built here; needs only Table B.3",
            ],
            [
                "13",
                "Look for the cause where the data allows: compare the factors of the volume "
                "equation before and after drilling",
                "Tells a subsurface team where its estimates go wrong",
            ],
            [
                "14",
                "One script from the data files to every number and figure; no typed-in values; "
                "sources for every series",
                "Lets the next person repeat and extend the study",
            ],
            [
                "15",
                "Complete the cost comparison. Sodir has actual investments per field; the PDO "
                "estimates would have to be collected, probably from the yearly budget "
                "propositions to the Storting (not checked)",
                "Slide 7; the paper cites cost and time overruns in oil and gas projects as "
                "well documented",
            ],
        ],
        left=(0, 1, 2),
    )
    report.text(
        "Recommendations 1–14 are carried out in the companion study, "
        "[`volve-rcf-study.md`](volve-rcf-study.md); number 11 with simpler scores than the "
        "paper's. Recommendation 15 needs data that is not in the repository."
    )

    # ------------------------------------------------------------------ how
    report.section("How this review was made", "How")
    report.bullets(
        [
            "The paper was converted to Markdown page by page and checked against its text "
            "layer; equations and Table 2 were read from the page images.",
            "The notebook's four calculations were rewritten as functions and their outputs "
            "compared with the saved outputs: well counts, class tables, totals, correlation, "
            "medians and all thirty percentiles of the production class agree. One well falls "
            "on the other side of a class boundary in analysis 1.",
            f"Not verified: the origin of the prognosis file and of `RCB_reserves.xlsx`; the "
            f"PDO curves in the workbook; how the 37 fields of the link file were chosen "
            f"({len(link)} fields have a discovery well in the prognosis data, "
            f"{int((all_candidates['excluded'] == '').sum())} fields pass the rules of the "
            "production class).",
            "The slides carry no conclusions in words. Where this review says what the study "
            "concludes, it is read from the figures.",
        ]
    )
    return report


def build(target_dir: Path) -> tuple[Path, Path]:
    report = build_report()
    markdown = report.write_markdown(target_dir / "expert-study-review.md")
    page = report.write_html(
        target_dir / "expert-study-review" / "index.html",
        plotly="../assets/plotly.min.js",
        link_prefix="../",
    )
    return markdown, page


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("build",))
    parser.parse_args(argv)
    for path in build(repo_root() / OUT):
        print(f"written: {path} ({path.stat().st_size / 1e3:.0f} kB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
