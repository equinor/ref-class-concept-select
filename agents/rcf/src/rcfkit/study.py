"""Reference class study of the Norwegian shelf record, applied to Volve.

    python -m rcfkit.study build

writes the report as Markdown and as a web page, and the tables behind it as
CSV, to ``agents/rcf/out``. The study repeats the expert study in
``agents/rcf/study`` on the same data, with the changes recommended in the
review (``rcfkit.review``).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from rcfkit import data, exploration, fields, stats, volve
from syskit import facts
from syskit.charts import BLUE, GREEN, GREY, INK, ORANGE, Chart, Series
from syskit.paths import repo_root
from syskit.report import Report, number, percent, signed

OUT = "agents/rcf/out"
DISCOUNT = 0.08  # per year, as in Nesvold & Bratvold (2022), Fig. 7


def discounted(cumulative: dict[int, float], years: int) -> float:
    """Volume of the first ``years`` years discounted to first oil, mid-year convention."""
    total, previous = 0.0, 0.0
    for year in range(1, years + 1):
        total += (cumulative[year] - previous) / (1 + DISCOUNT) ** (year - 0.5)
        previous = cumulative[year]
    return total


# ---------------------------------------------------------------------------- charts
def reliability_chart(result: dict) -> Chart:
    bins = result["bins"]
    return Chart(
        "reliability",
        "Stated probability of discovery against the share that were discoveries",
        "Stated probability (mean of the class)",
        "Share that were discoveries",
        [
            Series("line", [0, 1], [0, 1], name="Perfect calibration", color=GREY, dash=True),
            Series(
                "errorbar",
                [b["forecast"] for b in bins],
                [b["observed"] for b in bins],
                name="Prospects, in classes of 0.1",
                low=[b["low"] for b in bins],
                high=[b["high"] for b in bins],
                connect=True,
                labels=[f"n = {b['n']}" for b in bins],
            ),
        ],
        x_range=(0, 1),
        y_range=(0, 1.02),
    )


def era_chart(groups: dict) -> Chart:
    names = [n for n in groups if n.startswith("Spudded")]
    labels = [n.removeprefix("Spudded ") for n in names]
    return Chart(
        "eras",
        "Stated and observed discovery rate by period",
        "Year the well was spudded",
        "Share of prospects",
        [
            Series("bar", labels, [groups[n]["mean_forecast"] for n in names], name="Stated"),
            Series(
                "bar", labels, [groups[n]["observed_rate"] for n in names], name="Found",
                color=ORANGE,
            ),
        ],
        y_range=(0, 0.45),
    )  # fmt: skip


def volume_chart(sample: pd.DataFrame, target: pd.DataFrame) -> Chart:
    span = [0.01, 3000]
    return Chart(
        "volumes",
        "Volume in place found against volume prognosed, discoveries",
        "Prognosed before drilling, million Sm3 o.e.",
        "Recorded after drilling, million Sm3 o.e.",
        [
            Series("line", span, span, name="Found = prognosed", color=GREY),
            Series("line", span, [v / 10 for v in span], name="One tenth", color=GREY, dash=True),
            Series(
                "markers", list(sample["forecast"]), list(sample["outcome"]), name="Prospects",
                opacity=0.55, labels=list(sample["well"] + " " + sample["prospect"]),
            ),
            Series(
                "markers", list(target["ip_oe_prog"]), list(target["ip_oe_res"]),
                name="Volve discovery, 15/9-19 SR", color=ORANGE, size=12,
            ),
        ],
        log_x=True,
        log_y=True,
        x_range=(0.2, 3000),
        y_range=(0.01, 1000),
    )  # fmt: skip


def coverage_chart(result: dict) -> Chart:
    labels = ["Below the low value", "Inside the range", "Above the high value"]
    keys = ("below", "inside", "above")
    return Chart(
        "coverage",
        "Where the volume found fell relative to the prognosed range",
        "",
        "Share of discoveries",
        [
            Series("bar", labels, [0.1, 0.8, 0.1], name="What the range claims", color=GREY),
            Series("bar", labels, [result["stated"][k] for k in keys], name="As stated"),
            Series(
                "bar", labels, [result["from_range"][k] for k in keys], color=GREEN,
                name="After calibration, tested on prospects held back",
            ),
        ],
        y_range=(0, 0.9),
    )  # fmt: skip


def parameter_chart(rows: list[dict]) -> Chart:
    names = [r["parameter"] for r in rows]
    return Chart(
        "parameters",
        "Result over prognosis for the factors of the volume equation",
        "",
        "Median of result / prognosis",
        [
            Series(
                "line",
                names,
                [1] * len(names), color=GREY, dash=True, name="No bias"),
            Series(
                "errorbar", names, [r["median"] for r in rows],
                low=[r["median_low"] for r in rows], high=[r["median_high"] for r in rows],
                name="Median with 90 % interval", labels=[f"n = {r['n']}" for r in rows],
            ),
        ],
        y_range=(0.3, 1.2),
    )  # fmt: skip


def link_chart(link: pd.DataFrame) -> Chart:
    sample = link[(link["well_result"] > 0) & (link["in_place_oe"] > 0)]
    target = sample[sample["field"] == volve.FIELD]
    span = [0.5, 600]
    return Chart(
        "link",
        "Volume in place: the field today against its discovery well",
        "Recorded for the discovery well after drilling, million Sm3 o.e.",
        "Sodir's estimate for the field today, million Sm3 o.e.",
        [
            Series("line", span, span, name="Equal", color=GREY),
            Series(
                "markers", list(sample["well_result"]), list(sample["in_place_oe"]),
                name="Fields", labels=list(sample["field"]), opacity=0.7,
            ),
            Series(
                "markers", list(target["well_result"]), list(target["in_place_oe"]),
                name="Volve", color=ORANGE, size=12,
            ),
        ],
        log_x=True,
        log_y=True,
        x_range=(0.5, 600),
        y_range=(0.5, 600),
    )  # fmt: skip


def growth_chart(table: pd.DataFrame) -> Chart:
    sample = table[(table["final_oe"] > 0)]
    closed = sample[sample["status"] == "Shut down"]
    running = sample[sample["status"] != "Shut down"]
    target = sample[sample["field"] == volve.FIELD]
    span = [0.05, 1500]
    return Chart(
        "growth",
        "Recovery now expected against reserves sanctioned",
        "Oil and gas reserves at PDO approval, million Sm3 o.e.",
        "Latest estimate of ultimate recovery, million Sm3 o.e.",
        [
            Series("line", span, span, name="Equal", color=GREY),
            Series(
                "markers", list(running["fid_oe"]), list(running["final_oe"]), name="Producing",
                labels=list(running["field"]), opacity=0.6,
            ),
            Series(
                "markers", list(closed["fid_oe"]), list(closed["final_oe"]), name="Shut down",
                labels=list(closed["field"]), color=INK, opacity=0.8,
            ),
            Series(
                "markers", list(target["fid_oe"]), list(target["final_oe"]), name="Volve",
                color=ORANGE, size=12,
            ),
        ],
        log_x=True,
        log_y=True,
        x_range=(0.05, 1500),
        y_range=(0.05, 1500),
    )  # fmt: skip


def class_chart(quantiles: pd.DataFrame, target: dict[int, float]) -> Chart:
    q = quantiles.dropna(subset=["q50"])
    years = list(q["years"])
    return Chart(
        "class",
        "Oil produced as a fraction of sanctioned oil reserves",
        "Years since first production",
        "Fraction of sanctioned reserves",
        [
            Series(
                "band", years, low=list(q["q10"]), high=list(q["q90"]),
                name="10–90 % of the class",
            ),
            Series(
                "band", years, low=list(q["q25"]), high=list(q["q75"]),
                name="25–75 % of the class", opacity=1.6,
            ),
            Series("line", years, list(q["q50"]), name="Median of the class"),
            Series(
                "line", list(target), list(target.values()), name="Volve, actual", color=ORANGE,
                width=2.6,
            ),
        ],
        y_range=(0, 2.0),
    )  # fmt: skip


def size_chart(table: pd.DataFrame, years: int = 3) -> Chart:
    sample = table[table[years].notna()]
    oil = sample[sample["oil_share"] >= fields.OIL_SHARE]
    gas = sample[sample["oil_share"] < fields.OIL_SHARE]
    target = sample[sample["field"] == volve.FIELD]
    return Chart(
        "size",
        f"Fraction produced after {years} years against field size",
        "Oil and gas reserves at PDO approval, million Sm3 o.e.",
        "Fraction of sanctioned reserves produced",
        [
            Series(
                "markers", list(oil["fid_oe"]), list(oil[years]), name="Oil fields",
                labels=list(oil["field"]), opacity=0.7,
            ),
            Series(
                "markers", list(gas["fid_oe"]), list(gas[years]), name="Gas fields", color=GREEN,
                labels=list(gas["field"]), opacity=0.7,
            ),
            Series(
                "markers", list(target["fid_oe"]), list(target[years]), name="Volve",
                color=ORANGE, size=12,
            ),
        ],
        log_x=True,
        y_range=(0, 1.6),
    )  # fmt: skip


def backtest_chart(backtest: dict) -> Chart:
    edges = np.linspace(0, 1, 11)
    labels = [f"{int(100 * a)}–{int(100 * b)}" for a, b in zip(edges[:-1], edges[1:], strict=True)]
    series = [Series("line", labels,
            [0.1] * len(labels), color=GREY, dash=True,
                     name="If the ranges are right")]  # fmt: skip
    for years, color in ((3, BLUE), (5, GREEN)):
        counts, _ = np.histogram(backtest[years]["positions"], bins=edges)
        share = counts / counts.sum()
        series.append(
            Series("bar", labels, list(share), color=color,
                   name=f"After {years} years ({backtest[years]['n']} fields)")
        )  # fmt: skip
    return Chart(
        "backtest",
        "Where fields fell in the range the class would have given at their approval",
        "Position in the class distribution, per cent",
        "Share of fields",
        series,
        y_range=(0, 0.3),
    )


def volve_chart(table: pd.DataFrame) -> Chart:
    years = list(table["years"])
    cal = table.dropna(subset=["cal_central"])
    return Chart(
        "volve",
        "Volve: cumulative oil from first production",
        "Years since first oil",
        "Million Sm3",
        [
            Series(
                "band", years, low=list(table["rcf_low"]), high=list(table["rcf_high"]),
                name="Reference class, 10–90 %",
            ),
            Series("line", years, list(table["rcf_median"]), name="Reference class, median"),
            Series(
                "band", years, low=list(table["plan_low"]), high=list(table["plan_high"]),
                color=GREEN, name="PDO, low to high case", opacity=1.5,
            ),
            Series("line", years, list(table["plan_mean"]), name="PDO, mean", color=GREEN),
            Series(
                "line", list(cal["years"]), list(cal["cal_central"]), color=GREY, dash=True,
                name="PDO mean after the paper's calibration",
            ),
            Series("line", years, list(table["actual"]), name="Actual", color=ORANGE, width=2.8),
        ],
        y_range=(0, 22),
    )  # fmt: skip


# ---------------------------------------------------------------------------- tables as files
def write_tables(target: Path, comparison: dict[str, pd.DataFrame]) -> list[Path]:
    """The data behind the report, for other domains to read."""
    target.mkdir(parents=True, exist_ok=True)
    written = []

    def save(frame: pd.DataFrame, name: str) -> None:
        path = target / name
        frame.to_csv(path, index=False, float_format="%.6g", lineterminator="\n")
        written.append(path)

    prospects = data.prospects()
    keep = ["well", "prospect", "spud_year", "prospect_priority", "cases", "p", "discovery"]
    keep += ["surprise", "ip_oe_prog", "ip_oe_res", "rec_oe_prog", "rec_oe_res"]
    save(prospects[keep], "prospects.csv")

    candidates = fields.candidates()
    keep = ["field", "status", "discovery_well", "approved", "first_approval_type", "fid_gap"]
    keep += ["fid_oil", "fid_gas", "start", "produced_before_approval", "final_oil", "final_gas"]
    keep += ["in_place_oil", "in_place_gas", "excluded"]
    save(candidates[keep], "fields.csv")

    parts = []
    for basis in ("oil", "oe"):
        frame = fields.profiles(basis)[["field", "start", "oil_share", *fields.HORIZONS]].copy()
        frame.insert(1, "basis", basis)
        parts.append(frame)
    profiles = pd.concat(parts, ignore_index=True)
    profiles.columns = [f"year_{c}" if isinstance(c, int) else c for c in profiles.columns]
    save(profiles, "production_fractions.csv")

    parts = []
    for name in volve.CLASSES:
        frame = fields.distribution(volve.members(name))
        frame.insert(0, "class", name)
        parts.append(frame)
    save(pd.concat(parts, ignore_index=True), "reference_class_quantiles.csv")

    parts = []
    for name, frame in comparison.items():
        frame = frame.copy()
        frame.insert(0, "class", name)
        parts.append(frame)
    save(pd.concat(parts, ignore_index=True), "volve_forecasts.csv")
    return written


# ---------------------------------------------------------------------------- report
def build_report() -> tuple[Report, dict[str, pd.DataFrame]]:
    prob = exploration.probability_results()
    vol = exploration.volume_results()
    portfolio = exploration.portfolio()
    phase = exploration.phase_results()
    parameters = exploration.parameter_results()
    sample = exploration.volume_sample("ip")
    ranges = exploration.range_sample()
    target_prospects = volve.prospect()
    found = target_prospects[target_prospects["discovery"] == 1].iloc[0]
    dry = target_prospects[target_prospects["discovery"] == 0].iloc[0]
    found_ratio = found["ip_oe_res"] / found["ip_oe_prog"]
    found_position = stats.percentile_of(found_ratio, sample["ratio"].to_numpy())

    link = fields.discovery_link()
    link_ok = link[(link["well_result"] > 0) & (link["in_place_oe"] > 0)]
    link_ratio = (link_ok["in_place_oe"] / link_ok["well_result"]).to_numpy()
    volve_link = link[link["field"] == volve.FIELD].iloc[0]
    volve_link_ratio = volve_link["in_place_oe"] / volve_link["well_result"]

    table = fields.profiles("oe")
    oil_table = fields.profiles("oil")
    candidates = fields.candidates()
    growth = fields.reserves_growth(table)
    others = table[table["field"] != volve.FIELD]
    volve_row = table.set_index("field").loc[volve.FIELD]
    volve_growth = volve_row["final_oe"] / volve_row["fid_oe"]
    closed = others[(others["status"] == "Shut down") & (others["final_oe"] > 0)]
    growth_position = stats.percentile_of(
        volve_growth, (closed["final_oe"] / closed["fid_oe"]).to_numpy()
    )
    with_in_place = candidates[(candidates["excluded"] == "") & (candidates["in_place_oe"] > 0)]
    sanctioned_share = (with_in_place["fid_oe"] / with_in_place["in_place_oe"]).to_numpy()
    volve_share = volve.outcome()["sanctioned_oe"] / volve.outcome()["in_place_oe"]

    effects = {years: fields.class_effects(table, years) for years in (3, 5)}
    backtest = fields.backtest(table)
    comparison = {name: volve.comparison(name) for name in volve.CLASSES}
    main = comparison[volve.PRIMARY]
    quantiles = fields.distribution(volve.members(volve.PRIMARY))
    plan, outcome = volve.plan(), volve.outcome()
    oil_fraction = {y: outcome["cumulative"][y] / outcome["sanctioned_oil"] for y in volve.YEARS}
    scored = main[main["years"] >= 2]
    scores = {k: float(scored[f"{k}_score"].mean()) for k in ("plan", "rcf", "cal")}
    below_low = [int(y) for y in main.loc[main["actual"] < main["plan_low"], "years"]]
    inside_rcf = bool(main["rcf_position"].between(0.1, 0.9).all())
    disc4 = {
        "actual": discounted(outcome["cumulative"], 4),
        "plan": discounted(plan["cumulative"]["mean"], 4),
        "rcf": discounted(dict(zip(main["years"], main["rcf_median"], strict=True)), 4),
    }
    pdo, disc, sim, public = (facts.read(s) for s in ("pud2005", "disc1993", "sim2016", "sodir"))
    known = comparison["Oil fields, as known in January 2005"].set_index("years")
    y5 = main.set_index("years").loc[5]
    n_wells = exploration.probability_sample()["well"].nunique()
    n_oil_fields = int((oil_table["oil_share"] >= fields.OIL_SHARE).sum())
    cal_miss = abs(main["cal_central"].iloc[2] / main["actual"].iloc[2] - 1)
    planned_investment = pdo["pud2005.costs_nominal.total_investments.total"]
    k5 = known.loc[5]
    era = prob["groups"]
    first_era, last_era = "Spudded 1989–1999", "Spudded 2010–2024"

    report = Report(
        "Estimates against outcomes on the Norwegian shelf, and what they say about Volve",
        "A reference class study: how probabilities of discovery, volumes in place, sanctioned "
        "reserves and production build-up have turned out for exploration wells and fields on "
        "the Norwegian continental shelf, and how the Volve plan of 2005 and its outcome sit in "
        "that record. Same data as the expert study in `agents/rcf/study`, recalculated.",
        generator="python -m rcfkit.study build",
    )

    # ------------------------------------------------------------------ summary
    report.section("Summary")
    report.text(
        "The record separates cleanly into what the industry estimates well and what it does "
        "not. The chance of finding hydrocarbons is estimated well. The amount is not: "
        "discoveries hold a third of the volume prognosed, and the ranges given are several "
        "times too narrow. Once a field is sanctioned, its reserves are on the whole "
        "recovered, with the help of later investments, but how fast they are produced varies "
        "between fields by a factor of four to five — far more than a development plan's range "
        "admits.",
        f"For Volve, a forecast made in 2005 from the oil fields then on record, knowing only "
        f"the field's sanctioned reserves, would have put production five years after first "
        f"oil at {k5['rcf_median']:.1f} million Sm3, with a 10–90 % range of "
        f"{k5['rcf_low']:.1f} to {k5['rcf_high']:.1f}. The plan said {y5['plan_mean']:.1f}, "
        f"with a range of {y5['plan_low']:.1f} to {y5['plan_high']:.1f}. The field produced "
        f"{y5['actual']:.1f}. The record to date, with fields of Volve's size only, gives "
        f"{y5['rcf_median']:.1f} ({y5['rcf_low']:.1f} to {y5['rcf_high']:.1f}).",
    )
    report.cards(
        [
            (
                "Discoveries: expected and made",
                f"{prob['all']['expected_discoveries']:.0f} and {prob['all']['discoveries']}",
                f"Sum of stated probabilities over {prob['all']['n']} drilled prospects, and "
                "the number that were discoveries",
            ),
            (
                "Volume in place found, as a share of prognosis",
                f"{vol['ip']['median']:.2f}",
                f"Median of {vol['ip']['n']} discoveries; "
                f"{percent(vol['ip']['share_below_forecast'])} found less than prognosed",
            ),
            (
                "Discoveries inside the prognosed range",
                percent(vol["range"]["stated"]["inside"]),
                f"The range claims 80 %. {percent(vol['range']['stated']['below'])} were below "
                "the low value",
            ),
            (
                "Ultimate recovery over sanctioned reserves",
                f"{growth['All fields']['median']:.2f}",
                f"Median of {growth['All fields']['n']} fields; "
                f"{growth['Shut down']['median']:.2f} for the {growth['Shut down']['n']} that "
                "have shut down",
            ),
            (
                "Sanctioned oil produced after five years",
                f"{quantiles.set_index('years').loc[5, 'q50']:.2f}",
                f"Median of oil fields of Volve's size; one in ten below "
                f"{quantiles.set_index('years').loc[5, 'q10']:.2f}, one in ten above "
                f"{quantiles.set_index('years').loc[5, 'q90']:.2f}",
            ),
            (
                "Volve against its plan after five years",
                f"{y5['attainment']:.2f}",
                f"Below the plan's low case in years {below_low[0]} to {below_low[-1]}; inside "
                "the reference class range in every year",
            ),
        ]
    )

    # ------------------------------------------------------------------ approach
    report.section("Question, data and method", "Approach")
    report.text(
        "Reference class forecasting answers a forecasting question with the record of "
        "comparable cases instead of the details of the case in hand. The study applies it at "
        "the decisions where a volume estimate carries the decision: drilling an exploration "
        "well, and sanctioning a development. At each, it measures two things in the record — "
        "*bias*, the typical ratio of outcome to estimate, and *spread*, how far outcomes "
        "scatter around that — and tests whether a range built from the record would have held "
        "for cases that were not used to build it.",
    )
    report.table(
        ["Stage", "Estimate", "Outcome", "Cases", "Source"],
        [
            [
                "Exploration",
                "Probability of discovery before drilling",
                "Discovery or dry",
                f"{prob['all']['n']} prospects in {n_wells} wells, 1989–2024",
                "Prognosis-and-result file of the expert study",
            ],
            [
                "Exploration",
                "Volume in place prognosed, with low and high values",
                "Volume in place recorded after drilling",
                f"{vol['ip']['n']} discoveries; {len(ranges)} with a P90–P10 range",
                "Same",
            ],
            [
                "Appraisal",
                "Volume in place recorded for the discovery well",
                "Sodir's estimate of volume in place in the field today",
                f"{len(link_ok)} fields",
                "Same, and Sodir field tables",
            ],
            [
                "Development",
                "Oil and gas reserves in the resource account of the year the PDO was approved",
                "Sodir's latest estimate of ultimate recovery",
                f"{growth['All fields']['n']} fields approved 1990–2021",
                "`RCB_reserves.xlsx`, Sodir reserves table",
            ],
            [
                "Development",
                "The same reserves",
                "Production by month from first production",
                f"{len(table)} fields; {n_oil_fields} oil fields",
                "Sodir monthly production, snapshot 19.11.2026",
            ],
        ],
        left=(0, 1, 2, 3, 4),
    )
    report.heading("Conventions")
    report.bullets(
        [
            "*Low* and *high* mean the values with 10 % of outcomes below and 10 % above. The "
            "Volve PDO calls them P90 and P10; the reference paper F10 and F90.",
            "Volumes are in million Sm3 of oil; a billion Sm3 of gas counts as a million Sm3 of "
            "oil equivalent (o.e.).",
            "One case is one prospect: a prospect with an oil case and a gas case gets the sum "
            "of the two probabilities and the probability-weighted volume. The rule and its "
            "exceptions are in `rcfkit.data.discovery_probability`.",
            "Field time is counted in 12-month periods from the first month of production "
            "after PDO approval, so that a late start is not counted as a production shortfall "
            "and the month of start does not matter.",
            "Intervals are 90 % intervals: Wilson for shares, bootstrap (resampling cases) for "
            "medians and quantiles.",
        ]
    )

    # ------------------------------------------------------------------ probability
    report.section("Exploration: is the chance of discovery estimated well?", "Chance")
    a = prob["all"]
    cv = prob["cross_validated"]
    report.text(
        f"Yes. Over {a['n']} drilled prospects the stated probabilities add up to "
        f"{a['expected_discoveries']:.0f} discoveries; {a['discoveries']} were made. Class by "
        "class, the share of discoveries follows the stated probability from 6 % up to about "
        "70 %; above that there are too few prospects to tell.",
    )
    report.chart(
        reliability_chart(prob),
        "Each point is a class of stated probability 0.1 wide; bars are 90 % Wilson intervals; "
        f"hover for the number of prospects. {a['n']} prospects with a stated technical "
        "probability and a recorded result. Data: prognosis-and-result file.",
    )
    report.text(
        f"Two refinements. First, high probabilities are somewhat too high and low ones too "
        f"low: a calibration line fitted to the outcomes has a slope of {a['slope']:.2f} "
        f"(90 % interval {a['slope_ci'][0]:.2f}–{a['slope_ci'][1]:.2f}) where 1 would be "
        "perfect. The effect is small: on prospects held back from the fit, recalibrated "
        f"probabilities score no better than the stated ones (Brier score {cv['recalibrated']:.4f} "
        f"against {cv['stated']:.4f}), and both beat the plain base rate ({cv['base_rate']:.4f}) "
        f"by {percent(cv['skill_stated'])}. The stated probabilities carry real information "
        "and need no correction.",
        f"Second, the overall agreement hides a drift. For wells spudded up to 1999, "
        f"{percent(era[first_era]['mean_forecast'])} was stated and "
        f"{percent(era[first_era]['observed_rate'])} found; from 2010, "
        f"{percent(era[last_era]['mean_forecast'])} stated and "
        f"{percent(era[last_era]['observed_rate'])} found. Explorers were cautious in the "
        "1990s and have been optimistic since 2010; the two cancel in the total.",
    )
    report.chart(
        era_chart(era),
        "Mean stated probability and share of discoveries, by the year the well was spudded: "
        + "; ".join(
            f"{name.removeprefix('Spudded ')}: {era[name]['n']} prospects"
            for name in era
            if name.startswith("Spudded")
        )
        + ".",
    )
    report.table(
        ["Group", "Prospects", "Stated", "Found", "Expected discoveries", "Made", "z"],
        [
            [
                name,
                str(g["n"]),
                percent(g["mean_forecast"], 1),
                percent(g["observed_rate"], 1),
                f"{g['expected_discoveries']:.0f}",
                str(g["discoveries"]),
                signed(g["z"], 1),
            ]
            for name, g in {"All prospects": a, **prob["groups"]}.items()
        ],
        caption="z is the difference between discoveries made and expected, in standard "
        "deviations; beyond ±2 is unlikely to be chance.",
    )
    report.text(
        "Prospects with several prognosis cases are the one group where the count depends on "
        "how the cases are combined; leaving them out changes nothing in the conclusions above."
    )

    # ------------------------------------------------------------------ volume
    report.section("Exploration: is the volume estimated well?", "Volume")
    v = vol["ip"]
    f = vol["range_factors"]
    report.text(
        f"No. For the {v['n']} discoveries with a prognosed and a recorded volume in place, the "
        f"median discovery holds {v['median']:.2f} of what was prognosed (90 % interval "
        f"{v['median_ci'][0]:.2f}–{v['median_ci'][1]:.2f}). {percent(v['share_below_forecast'])} "
        f"hold less than prognosed, and {percent(v['share_below_tenth'])} less than a tenth. "
        f"Only {percent(v['share_within_factor_2'])} are within a factor of two either way.",
    )
    report.chart(
        volume_chart(sample, target_prospects[target_prospects["discovery"] == 1]),
        "One point per discovered prospect; both axes logarithmic; hover for well and prospect. "
        "The orange point is the oil found by 15/9-19 SR in a prospect prognosed as gas. "
        "Data: prognosis-and-result file, in-place columns, oil and gas with associated phases.",
    )
    report.table(
        [
            "",
            "Discoveries",
            "Median",
            "10 % below",
            "10 % above",
            "Ratio of totals",
            "Below prognosis",
        ],
        [
            [
                name,
                str(s["n"]),
                f"{s['median']:.2f}",
                f"{s['q10']:.2f}",
                f"{s['q90']:.2f}",
                f"{s['of_totals']:.2f}",
                percent(s["share_below_forecast"]),
            ]
            for name, s in {
                "Volume in place, all": v,
                **{f"Volume in place, spudded {k}": s for k, s in vol["eras"].items()},
                "Volume in place, central value labelled mean": vol["labelled_mean"],
                "Recoverable volume, all": vol["rec"],
            }.items()
        ],
        caption="Volume recorded after drilling divided by volume prognosed, for discoveries.",
    )
    report.text(
        "The over-estimation has grown: the median was "
        f"{vol['eras']['1989–1999']['median']:.2f} in the 1990s and is "
        f"{vol['eras']['2010–2024']['median']:.2f} for wells since 2010. It is not a matter of "
        "what the central value is called: where the file labels it a mean, the result is the "
        "same or worse.",
    )
    report.heading("The ranges are several times too narrow")
    st = vol["range"]["stated"]
    report.text(
        f"{st['n']} discoveries had a single prognosis with a low (P90) and a high (P10) value "
        "for the phase that was found. Such a range should hold 80 % of outcomes. It held "
        f"{percent(st['inside'])}; {percent(st['below'])} of discoveries were smaller than the "
        f"low value. The typical range spans a factor of {vol['range_width']:.0f} from low to "
        f"high. A range that does hold 80 % — from {f['a_mean']:.2f} to {f['c_mean']:.1f} times "
        f"the central value — spans a factor of {vol['range_width_needed']:.0f}.",
    )
    report.chart(
        coverage_chart(vol["range"]),
        f"{st['n']} discoveries with a P90–P10 range. Green: low and high values multiplied by "
        "factors estimated on nine tenths of the prospects and applied to the remaining tenth, "
        "in turn (ten-fold cross-validation).",
    )
    report.table(
        ["To obtain", "Multiply", "By"],
        [
            ["A median estimate", "the central value", f"{f['b']:.2f}"],
            ["A low value (10 % below)", "the central value", f"{f['a_mean']:.2f}"],
            ["A high value (10 % above)", "the central value", f"{f['c_mean']:.2f}"],
            ["A low value", "the stated low value", f"{f['a_low']:.2f}"],
            ["A high value", "the stated high value", f"{f['c_high']:.2f}"],
        ],
        left=(0, 1),
        caption="Calibration factors for pre-drill volume in place of the main phase, from the "
        f"{st['n']} discoveries with a stated range and the phase as prognosed. Leaving out "
        "discoveries in another phase is why the median factor is higher here than the "
        f"{v['median']:.2f} of all discoveries. The form follows Nesvold and Bratvold (2022), "
        "equations 5 and 6.",
    )
    report.heading("Where the volume goes missing")
    rock = parameters[0]
    report.text(
        "The file holds the factors of the volume equation before and after drilling. The "
        f"shortfall is in the container, not the rock: rock volume comes in at "
        f"{rock['median']:.2f} of prognosis in the median discovery, through a smaller area "
        "and a shorter hydrocarbon column. Porosity and net-to-gross are unbiased, and "
        "saturation nearly so.",
    )
    report.chart(
        parameter_chart(parameters),
        "Median of result over prognosis among discoveries that report the parameter both "
        "times; bars are 90 % bootstrap intervals; hover for the number of prospects.",
    )
    report.heading("Chance and volume together")
    report.text(
        f"Multiplying each prospect's probability by its prognosed volume gives the volume a "
        f"drilling programme expects. Over {portfolio['n']} prospects that is "
        f"{number(portfolio['expected'])} million Sm3 o.e. in place. The discoveries delivered "
        f"{number(portfolio['delivered'])}, or {portfolio['ratio']:.2f} of it (90 % interval "
        f"{portfolio['ratio_ci'][0]:.2f}–{portfolio['ratio_ci'][1]:.2f}). Since the "
        "probabilities are sound, the whole shortfall is volume. In "
        f"{percent(1 - phase['same'])} of {phase['n']} discoveries the main phase found was "
        "not the one prognosed.",
    )

    # ------------------------------------------------------------------ appraisal
    report.section("From discovery to sanction", "Appraisal")
    report.text(
        f"{len(link_ok)} fields have a discovery well in the prognosis file with a recorded "
        "volume, and a volume in place in Sodir's field table today. The field today holds "
        f"{np.median(link_ratio):.1f} times the volume recorded for its discovery well in the "
        f"median case; a quarter hold less than {np.quantile(link_ratio, 0.25):.1f} times, a "
        f"quarter more than {np.quantile(link_ratio, 0.75):.1f} times.",
        "This is the reverse of the pre-drill picture. A volume recorded straight after a "
        "discovery well describes what the well has proven; appraisal, neighbouring segments "
        "and later discoveries tied into the same field add to it. The comparison cannot say "
        "how much of the growth is revision and how much is addition, because Sodir publishes "
        "today's volume in place only, not its history.",
    )
    report.chart(
        link_chart(link),
        "One point per field; hover for the name. Horizontal: oil equivalents in place "
        "recorded in the result rows of the field's discovery well. Vertical: Sodir's current "
        "figure for the field (oil, associated liquid, associated and free gas).",
    )
    report.text(
        "How much of what is in place a plan promises to recover can be put beside the same "
        f"field table. For the {len(sanctioned_share)} fields of the production class, "
        "sanctioned reserves are "
        f"{np.median(sanctioned_share):.2f} of today's volume in place in the median, and "
        f"above {np.quantile(sanctioned_share, 0.9):.2f} for one field in ten. Oil and gas are "
        "mixed in these numbers, and gas recovers more.",
    )

    # ------------------------------------------------------------------ reserves
    report.section("Development: are sanctioned reserves recovered?", "Reserves")
    g = growth["All fields"]
    report.text(
        f"On the whole, yes, and more. For {g['n']} fields with a PDO approved from 1990 and a "
        "reserves figure from the approval year, the latest estimate of ultimate recovery is "
        f"{g['median']:.2f} times the sanctioned reserves in the median (90 % interval "
        f"{g['median_ci'][0]:.2f}–{g['median_ci'][1]:.2f}). The spread is wide: one field in ten "
        f"ends below {g['q10']:.2f}, one in ten above {g['q90']:.2f}.",
        "The growth is not evidence of cautious plans. It contains everything decided after "
        "the first PDO — infill wells, new phases, tie-ins of other discoveries — and each of "
        "those was a new investment. And it is a view of survivors: the "
        f"{growth['Shut down']['n']} fields that have shut down, whose recovery is final, ended "
        f"at {growth['Shut down']['median']:.2f} of sanctioned reserves in the median, and "
        f"{percent(growth['Shut down']['share_below_forecast'])} of them below 1.",
    )
    report.chart(
        growth_chart(table),
        "One point per field; both axes logarithmic; hover for the name. Reserves: oil and gas "
        "in the resource account of the year of approval (or the year after or before). "
        "Recovery: Sodir's reserves table, version 2025.",
    )
    report.table(
        ["Group", "Fields", "Median", "90 % interval", "10 % below", "10 % above", "Below 1"],
        [
            [
                name,
                str(s["n"]),
                f"{s['median']:.2f}",
                f"{s['median_ci'][0]:.2f}–{s['median_ci'][1]:.2f}",
                f"{s['q10']:.2f}",
                f"{s['q90']:.2f}",
                percent(s["share_below_forecast"]),
            ]
            for name, s in growth.items()
        ],
        caption="Latest estimate of ultimate recovery over reserves sanctioned at the first "
        "PDO, oil and gas.",
    )

    # ------------------------------------------------------------------ production class
    report.section("Development: how fast are sanctioned reserves produced?", "Production")
    report.heading("The reference class")
    excluded = candidates["excluded"].value_counts()
    report.text(
        "The rules of membership were written before the fractions were computed. A field is "
        "a member if:",
    )
    report.bullets(
        [
            "its first approval is a PDO (not an exemption from one), dated 1990 or later — the "
            "resource accounts in the data start in 1990;",
            "the resource account holds oil and gas reserves for it in the year of approval, or "
            "failing that the year after or the year before;",
            f"less than {percent(fields.PRE_APPROVAL_LIMIT)} of those reserves had been "
            "produced before the approval;",
            "it has started to produce.",
        ]
    )
    report.table(
        ["Fields", "Number"],
        [["In the class", str(int(excluded.get("", 0)))]]
        + [[f"Left out: {reason}", str(int(n))] for reason, n in excluded.items() if reason],
        caption=f"All {len(candidates)} fields in Sodir's field list. Year 1 is the first "
        "12 months from the first month of production on or after approval.",
    )
    report.text(
        "For each member the outcome is cumulative production divided by sanctioned reserves "
        "after 1, 2, … 10 years. A horizon is used only where the field has completed it by "
        f"{data.production_monthly()['month'].max().strftime('%B %Y')}, the last month in the "
        "data. Fields that have shut down stay in with their final production.",
    )
    e3 = effects[3]
    report.heading("What the class depends on")
    report.text(
        f"Size matters. Large fields produce their reserves more slowly: the rank correlation "
        f"between sanctioned reserves and the fraction produced after three years is "
        f"{signed(e3['size_rho'], 2)} (p = {e3['size_p']:.4f}; {e3['n']} fields), and "
        f"{signed(effects[5]['size_rho'], 2)} after five. The main product does not: oil fields "
        "and "
        f"gas fields have the same median after three years ({e3['oil_median']:.2f} and "
        f"{e3['gas_median']:.2f}; p = {e3['product_p']:.2f}). Nor does the period: there is no "
        "trend with the year of first production (rank correlation "
        f"{signed(e3['era_rho'], 2)}, "
        f"p = {e3['era_p']:.2f}).",
        "The class used for Volve is therefore narrowed by size: oil fields with sanctioned "
        f"reserves within a factor of {fields.select.__kwdefaults__['size_factor']:.0f} of "
        f"Volve's {outcome['sanctioned_oe']:.1f} million Sm3 o.e. Oil fields are kept apart "
        "because the comparison with the PDO is in oil, not because the product matters.",
    )
    report.chart(
        size_chart(table),
        "One point per field; horizontal axis logarithmic; hover for the name. Oil and gas "
        "produced in the first 36 months over sanctioned oil and gas reserves.",
    )
    report.heading("The distribution")
    q = quantiles.set_index("years")
    report.chart(
        class_chart(quantiles, oil_fraction),
        f"Oil fields with sanctioned reserves of {outcome['sanctioned_oe'] / 4:.1f} to "
        f"{outcome['sanctioned_oe'] * 4:.0f} million Sm3 o.e., Volve left out: "
        f"{int(q.loc[1, 'n'])} fields after one year, {int(q.loc[10, 'n'])} after ten. Oil "
        "produced over sanctioned oil reserves. Orange: Volve, oil over its sanctioned "
        f"{outcome['sanctioned_oil']:.2f} million Sm3.",
    )
    report.table(
        [
            "Years",
            "Fields",
            "10 % below",
            "25 %",
            "Median",
            "75 %",
            "10 % above",
            "Median, 90 % interval",
        ],
        [
            [
                str(int(r["years"])),
                str(int(r["n"])),
                f"{r['q10']:.2f}",
                f"{r['q25']:.2f}",
                f"{r['q50']:.2f}",
                f"{r['q75']:.2f}",
                f"{r['q90']:.2f}",
                f"{r['q50_low']:.2f}–{r['q50_high']:.2f}",
            ]
            for _, r in quantiles.iterrows()
        ],
        caption="Fraction of sanctioned oil reserves produced, oil fields of Volve's size.",
    )
    report.text(
        f"The median field has produced {q.loc[3, 'q50']:.2f} of its sanctioned oil after three "
        f"years and {q.loc[5, 'q50']:.2f} after five. After ten years the median field has "
        f"produced {q.loc[10, 'q50']:.2f} of what was sanctioned, and one in ten "
        f"{q.loc[10, 'q90']:.2f} or more — the later investments again. The 10–90 % range is a "
        f"factor of {q.loc[3, 'q90'] / q.loc[3, 'q10']:.1f} wide after three years and "
        f"{q.loc[5, 'q90'] / q.loc[5, 'q10']:.1f} after five.",
    )
    report.heading("Would these ranges have held?")
    b3, b5 = backtest[3], backtest[5]
    report.text(
        "A range read off past fields is a forecast only if later fields fall in it as often "
        "as it says. To test this, the class was rebuilt for each field as it stood in the "
        "month that field's PDO was approved — only fields approved earlier, and only the "
        "horizons they had completed by then — and the field's later outcome was placed in "
        "that distribution. At least ten earlier fields were required.",
        f"After three years, {percent(b3['inside'])} of {b3['n']} fields fell inside the "
        f"10–90 % range of their class, {percent(b3['below'])} below and "
        f"{percent(b3['above'])} above. After five years: {percent(b5['inside'])} inside, "
        f"{percent(b5['below'])} below, {percent(b5['above'])} above ({b5['n']} fields). The "
        "positions are spread evenly, as they should be (Kolmogorov–Smirnov test of "
        f"uniformity: p = {b3['ks_p']:.2f} and {b5['ks_p']:.2f}). For comparison, Nesvold and "
        "Bratvold found that operators' own low–high ranges held under 30 % of outcomes after "
        "two years and about 50 % after four to ten.",
    )
    report.chart(
        backtest_chart(backtest),
        "Each field's outcome expressed as its position (0–100 %) among the fields known when "
        "its PDO was approved, in ten classes. A calibrated method puts a tenth of the fields "
        "in each class. All fields of the class, oil and gas over sanctioned oil and gas.",
    )

    # ------------------------------------------------------------------ Volve
    report.section("Volve in the record", "Volve")
    report.heading("1993: the discovery")
    report.text(
        f"Well 15/9-19 SR was drilled for two gas prospects. The first, given a "
        f"{percent(dry['p'])} chance, was dry. The second, given {percent(found['p'])} and "
        f"{found['ip_oe_prog']:.2f} billion Sm3 of gas in place, held oil: "
        f"{found['ip_oil_main_res']:.2f} million Sm3 in place according to the result row, "
        f"with {found['ip_gas_assoc_res']:.1f} billion Sm3 of associated gas. That is "
        f"{found_ratio:.1f} times the prognosed volume in oil equivalents, higher than "
        f"{percent(found_position)} of discoveries in the record. Volve began as one of the "
        "rare cases where the drill found more than was prognosed, and in another phase.",
    )
    report.heading("1993 to today: the volume in place")
    report.table(
        ["When", "Source", "Low", "Central", "High"],
        [
            [
                "1993, after the well",
                "Result row of the prognosis file",
                f"{found['ip_oil_min_res']:.2f}",
                f"{found['ip_oil_main_res']:.2f}",
                f"{found['ip_oil_max_res']:.2f}",
            ],
            [
                "December 1993",
                "Discovery evaluation report, Theta Vest (Table 10.1)",
                f"{disc['disc1993.stooip.theta_vest.p90']:.2f}",
                f"{disc['disc1993.stooip.theta_vest.mean']:.2f}",
                f"{disc['disc1993.stooip.theta_vest.p10']:.2f}",
            ],
            [
                "February 2005",
                "PDO, Volve closure (Table 3.4)",
                f"{plan['in_place']['low']:.1f}",
                f"{plan['in_place']['mean']:.1f}",
                f"{plan['in_place']['high']:.1f}",
            ],
            [
                "2016",
                "Simulation model at end of production, all regions",
                "",
                f"{sim['sim2016.oil_in_place.initial.field'] / 1e6:.1f}",
                "",
            ],
            ["Today", "Sodir field table", "", f"{outcome['in_place_oil']:.1f}", ""],
        ],
        left=(0, 1),
        caption="Oil originally in place at Volve, million Sm3, as estimated at different "
        "times. The areas covered are not identical from one estimate to the next.",
    )
    report.text(
        f"The field today is put at {volve_link_ratio:.1f} times the oil equivalents recorded "
        f"for its discovery well, against {np.median(link_ratio):.1f} times for the median "
        f"field — more growth than {percent(stats.percentile_of(volve_link_ratio, link_ratio))} "
        "of fields. All of that growth came before the PDO. Between the PDO and today the "
        f"estimate of oil in place fell from {plan['in_place']['mean']:.1f} to "
        f"{outcome['in_place_oil']:.1f} "
        f"million Sm3, to below the PDO's low value of {plan['in_place']['low']:.1f}. The "
        "public record has no history of in-place estimates for other fields, so how common "
        "such a fall after sanction is cannot be said from this data. What the record does "
        "say is that the PDO promised a high recovery by today's knowledge: its sanctioned "
        f"reserves are {volve_share:.2f} of today's volume in place, where the median field's "
        f"are {np.median(sanctioned_share):.2f} and "
        f"{percent(1 - stats.percentile_of(volve_share, sanctioned_share))} of fields "
        "sanctioned a larger share.",
    )
    report.heading("2005: the production forecast")
    report.text(
        f"The PDO forecast {plan['reserves']['mean']:.1f} million Sm3 of oil (mean), with a low "
        f"case of {plan['reserves']['low']:.1f} and a high case of "
        f"{plan['reserves']['high']:.1f}. The resource account for 2005 carries "
        f"{outcome['sanctioned_oil']:.2f}; the reference class fractions are multiplied by "
        "that figure, since it is the figure they were built on for the other fields. Three "
        "forecasts can then be set beside the outcome, all counted from first oil:",
    )
    report.bullets(
        [
            "the PDO's own low, mean and high cases (Table 4.5), re-counted from the planned "
            "first oil on 6 March 2007;",
            "the reference class forecast: low, median and high fractions of the class times "
            "sanctioned reserves — no knowledge of Volve beyond its size and that it is an "
            "oil field;",
            "the PDO mean after the calibration factors published by Nesvold and Bratvold "
            "(Table B.3) — an outside view built on a different record, the operators' "
            "forecasts for 71 fields.",
        ]
    )
    report.chart(
        volve_chart(main),
        f"Blue: {int(main['n'].iloc[0])} oil fields of Volve's size (the number falls to "
        f"{int(main['n'].iloc[-1])} by year 9). Green: PDO Table 4.5; the three cases are "
        "almost identical for the first two years. Grey: PDO mean times the paper's factor "
        "for each production year. Orange: Sodir monthly production, first oil February 2008.",
    )
    report.table(
        ["Years", "Actual", "PDO low", "PDO mean", "PDO high", "Actual / PDO mean", "Class low",
         "Class median", "Class high", "Actual, position in class", "Calibrated PDO mean"],
        [
            [
                str(int(r["years"])),
                f"{r['actual']:.2f}",
                f"{r['plan_low']:.2f}",
                f"{r['plan_mean']:.2f}",
                f"{r['plan_high']:.2f}",
                f"{r['attainment']:.2f}",
                f"{r['rcf_low']:.1f}",
                f"{r['rcf_median']:.1f}",
                f"{r['rcf_high']:.1f}",
                percent(r["rcf_position"]),
                "" if pd.isna(r["cal_central"]) else f"{r['cal_central']:.2f}",
            ]
            for _, r in main.iterrows()
        ],
        caption="Cumulative oil, million Sm3, by years since first oil.",
    )  # fmt: skip
    report.text(
        f"The plan's range was almost nil at the start — {main['plan_low'].iloc[1]:.2f} to "
        f"{main['plan_high'].iloc[1]:.2f} after two years — and the field fell out of it at "
        f"once: production was below the low case in years {below_low[0]} to {below_low[-1]}. "
        f"Against the mean it reached {main['attainment'].iloc[2]:.2f} after three years and "
        f"{main['attainment'].iloc[4]:.2f} after five, close to the 0.8 the paper reports for "
        "the shelf. Production rose again in 2014 and 2015, after new investments, which took "
        "the field back above the low "
        f"case, and it ended at {main['attainment'].iloc[-1]:.2f} of the plan after more than "
        "twice the planned investment.",
        f"Against the reference class the same history is unremarkable. Volve sat between the "
        f"{percent(main['rcf_position'].min())} and {percent(main['rcf_position'].max())} "
        "points of the class in every year"
        + (" — inside the 10–90 % range throughout" if inside_rcf else "")
        + ": a field that started a little faster than most and then produced like the median. "
        f"The calibrated PDO mean was within {100 * cal_miss:.0f} % "
        "of the outcome after three years and too high after that.",
    )
    report.text(
        f"In the end Volve recovered {volve_growth:.2f} of the oil and gas sanctioned. The "
        f"{len(closed)} other fields that have shut down recovered "
        f"{np.median(closed['final_oe'] / closed['fid_oe']):.2f} in the median, and "
        f"{percent(growth_position)} of them a smaller share than Volve.",
    )
    report.heading("Which forecast was better?")
    report.text(
        "One field cannot rank forecasting methods; the back-test above is the evidence for "
        "the method. For Volve alone, a quantile score (the mean penalty over the low, middle "
        "and high values, lower is better; an approximation of the CRPS used in the paper) "
        f"averaged over years 2 to 9 gives {scores['plan']:.2f} for the PDO, "
        f"{scores['rcf']:.2f} for the reference class and {scores['cal']:.2f} for the "
        "calibrated PDO. The PDO scores best in the first two years, when the field followed "
        "it, and worst from the third, when its narrow range missed.",
        f"In value terms: oil of the first four years, discounted at {percent(DISCOUNT)} a "
        f"year to first oil, came to {disc4['actual']:.2f} million Sm3, which is "
        f"{disc4['actual'] / disc4['plan']:.2f} of the plan's mean and "
        f"{disc4['actual'] / disc4['rcf']:.2f} of the reference class median.",
    )
    report.heading("What could have been known in 2005")
    report.text(
        "The class above uses fields that started after Volve was sanctioned. Restricted to "
        "what was on record in January 2005 — oil fields approved before then, each horizon "
        f"only where completed — it has {int(known.loc[1, 'n'])} fields at one year and "
        f"{int(k5['n'])} at five. Its forecast for Volve after five years is "
        f"{k5['rcf_median']:.1f} million Sm3 with a 10–90 % range of {k5['rcf_low']:.1f} to "
        f"{k5['rcf_high']:.1f}, against {y5['rcf_median']:.1f} ({y5['rcf_low']:.1f} to "
        f"{y5['rcf_high']:.1f}) from the full class. The outside view available at the time "
        "gave much the same answer as hindsight does.",
    )
    report.table(
        ["Reference class", "Fields at 5 years", "Low", "Median", "High", "Actual, position"],
        [
            [
                name,
                str(int(frame.set_index("years").loc[5, "n"])),
                f"{frame.set_index('years').loc[5, 'rcf_low']:.1f}",
                f"{frame.set_index('years').loc[5, 'rcf_median']:.1f}",
                f"{frame.set_index('years').loc[5, 'rcf_high']:.1f}",
                percent(frame.set_index("years").loc[5, "rcf_position"]),
            ]
            for name, frame in comparison.items()
        ],
        caption=f"Forecast of Volve's cumulative oil after five years, million Sm3, from four "
        f"definitions of the class. Actual: {y5['actual']:.2f}; PDO mean: {y5['plan_mean']:.2f}.",
    )
    report.heading("Cost")
    report.text(
        f"The PDO put investments at {number(planned_investment)} "
        f"million NOK in nominal terms; Sodir records {number(public['sodir.investment.total'])}. "
        "A reference class for cost needs the PDO estimates of other fields, which are not in "
        "Sodir's tables. They are probably to be found in the yearly budget propositions to "
        "the Storting; this has not been checked, and nothing has been collected.",
    )

    # ------------------------------------------------------------------ use
    report.section("What this gives a decision analysis", "Use")
    report.table(
        ["Estimate", "What the record supports"],
        [
            [
                "Probability of discovery",
                "Use as stated. Check the recent drift: since 2010 about a third fewer "
                "discoveries than stated",
            ],
            [
                "Pre-drill volume in place",
                f"Median outcome {v['median']:.2f} of the central value; 10–90 % range "
                f"{v['q10']:.2f} to {v['q90']:.1f} times it. The shortfall is in rock "
                "volume",
            ],
            [
                "Volume in place at sanction",
                "No public record of estimates at sanction. Volve's fell by "
                f"{percent(1 - outcome['in_place_oil'] / plan['in_place']['mean'])}, to below "
                "its low value",
            ],
            [
                "Reserves at sanction",
                f"Ultimate recovery {growth['All fields']['median']:.2f} times sanctioned in "
                f"the median, including later investments; {growth['Shut down']['median']:.2f} "
                "for fields that have shut down",
            ],
            [
                "Production in the first years",
                f"Fraction of sanctioned oil after 3 and 5 years: median {q.loc[3, 'q50']:.2f} "
                f"and {q.loc[5, 'q50']:.2f}; 10–90 % range {q.loc[3, 'q10']:.2f}–"
                f"{q.loc[3, 'q90']:.2f} and {q.loc[5, 'q10']:.2f}–{q.loc[5, 'q90']:.2f}. "
                "Condition on field size",
            ],
        ],
        left=(0, 1),
    )
    report.text(
        "The tables behind these numbers are in `agents/rcf/out/data/`: one row per prospect, "
        "one per field, the production fractions, the quantiles of each class, and the Volve "
        "comparison."
    )

    # ------------------------------------------------------------------ limits
    report.section("Limits", "Limits")
    report.bullets(
        [
            "The sanctioned reserves are the resource-account figures, not the PDO documents. "
            f"For Volve the account has {outcome['sanctioned_oil']:.2f} million Sm3 of oil and "
            f"the PDO {plan['reserves']['mean']:.2f}, whose economic cut-off comes earlier. The "
            "paper reports near-perfect agreement "
            "between PDO forecasts and the forecasts reported to the authorities, but this "
            "study has checked it for one field.",
            "No operator forecast profiles are public. The study therefore cannot repeat the "
            "paper's calibration or compare the reference class with operators' forecasts for "
            "any field but Volve.",
            "The origin of the prognosis-and-result file and of `RCB_reserves.xlsx` is taken "
            "on trust from the expert study. In the latter the years 2020 and 2021 are "
            "exchanged; this is corrected in `rcfkit.data.resource_account`.",
            "The recorded result of an exploration well is itself an estimate, made soon after "
            "drilling. The comparison measures prognosis against that estimate, not against "
            "what was finally produced.",
            "Volume in place for fields is Sodir's current figure; there is no public history. "
            "The appraisal comparison mixes revision with additions to the field.",
            "The discoveries with a stated range are those with a single prognosis and the "
            "same phase before and after; discoveries in the wrong phase are counted in the "
            "volume comparison but not in the range test.",
            "The class for Volve has about forty fields, and the as-known-in-2005 class "
            "fifteen at five years. The intervals on the quantiles show what that supports.",
            "Fields are not independent — they share operators, technology and price cycles — "
            "so the bootstrap intervals are somewhat too narrow.",
        ]
    )

    # ------------------------------------------------------------------ how
    report.section("How the study was made", "How")
    report.bullets(
        [
            "Code: the `rcfkit` package in `agents/rcf/src`. `rcfkit.data` reads the files, "
            "`rcfkit.exploration` and `rcfkit.fields` hold the analyses, `rcfkit.volve` the "
            "case, `rcfkit.stats` the statistics. `make rcf-volve` rebuilds everything.",
            "Volve's plan comes from the fact register (`data/facts/pud2005.csv`, PDO Table "
            "4.5 and Table 3.4), its discovery estimate from `data/facts/disc1993.csv`.",
            "Checks: the statistics functions are tested on cases worked by hand; the expert "
            "study's numbers are reproduced before anything is changed "
            "([review](expert-study-review.md)); the PDO's cumulative mean re-counted from first "
            "oil agrees with the integration of the PDO's rate curve used in the doc report "
            f"({plan['cumulative']['mean'][3]:.2f} against 8.15 million Sm3 after 36 months, "
            "the difference being the even spread of each year's volume).",
            "Not done: cost; gas; a class weighted continuously by size as in the paper; the "
            "paper's density score (the metalog fit), for which the three-point quantile score "
            "stands in.",
        ]
    )
    return report, comparison


def build(target_dir: Path) -> list[Path]:
    report, comparison = build_report()
    written = [
        report.write_markdown(target_dir / "volve-rcf-study.md"),
        report.write_html(
            target_dir / "volve-rcf-study" / "index.html",
            plotly="../assets/plotly.min.js",
            link_prefix="../",
        ),
    ]
    return written + write_tables(target_dir / "data", comparison)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("build",))
    parser.parse_args(argv)
    for path in build(repo_root() / OUT):
        print(f"written: {path} ({path.stat().st_size / 1e3:.0f} kB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
