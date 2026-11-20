"""Volve concept selection on a recalibrated volume basis: Markdown report and web page.

    python -m dmxkit.volve_concept build

The report sets the PDO's estimate of oil in place beside the same estimate
after a reference class calibration, carries both through the PDO's own
figures for reserves and value, and asks what in the chosen development
solution the difference would change.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from dmxkit import volve_basis as vb
from rcfkit import exploration, fields, inplace, volve
from syskit import facts, sodir
from syskit.charts import BLUE, GREY, INK, ORANGE, Chart, Series
from syskit.paths import data_dir, repo_root
from syskit.report import Report, number, percent, signed

OUT = "agents/dmx/out"
GRID = np.linspace(0.01, 0.99, 99)


def cdf(values: np.ndarray) -> tuple[list[float], list[float]]:
    return list(np.quantile(values, GRID)), list(GRID)


def basis_chart(both: dict, stated: dict, outcomes: dict[str, float] | None = None) -> Chart:
    name = "hindsight" if outcomes else "basis"
    series = [
        Series("line", *cdf(both["PDO"]["closure"]), name="PDO basis", color=BLUE),
        Series("line", *cdf(both["Calibrated"]["closure"]), name="Calibrated basis", color=ORANGE),
        Series(
            "markers",
            [stated["p90"], stated["p50"], stated["p10"]],
            [0.1, 0.5, 0.9],
            name="PDO Table 3.4: P90, P50, P10",
            color=BLUE,
            size=9,
        ),
    ]
    if outcomes:
        for label, volume in outcomes.items():
            series.append(
                Series("line", [volume, volume], [0, 1], name=label, color=INK, dash=True)
            )
    return Chart(
        name,
        "Oil in place in the Volve closure: probability of ending below a volume",
        "Oil in place, million Sm3",
        "Probability of less",
        series,
        x_range=(10, 45),
        y_range=(0, 1),
    )


def west_chart(both: dict, break_even: float) -> Chart:
    return Chart(
        "west",
        "Oil in place in the West: probability of ending below a volume",
        "Oil in place in the West, million Sm3",
        "Probability of less",
        [
            Series("line", *cdf(both["PDO"]["west"]), name="PDO basis", color=BLUE),
            Series("line", *cdf(both["Calibrated"]["west"]), name="Calibrated basis", color=ORANGE),
            Series(
                "line",
                [break_even, break_even],
                [0, 1],
                name="Volume at which two wells pay for themselves",
                color=GREY,
                dash=True,
            ),
        ],
        x_range=(0, 20),
        y_range=(0, 1),
    )


def value_chart(both: dict) -> Chart:
    series = []
    for name, color in (("PDO", BLUE), ("Calibrated", ORANGE)):
        npv = vb.value(vb.reserves(both[name]["closure"]))
        series.append(Series("line", *cdf(npv), name=f"{name} basis", color=color))
    series.append(Series("line", [0, 0], [0, 1], name="Break-even", color=GREY, dash=True))
    return Chart(
        "value",
        "Net present value after tax with all planned wells: probability of less",
        "Million NOK of 2005, after tax at 8 %, oil at 22 USD per barrel",
        "Probability of less",
        series,
        x_range=(-200, 1000),
        y_range=(0, 1),
    )


def write_tables(target: Path, results: dict) -> list[Path]:
    target.mkdir(parents=True, exist_ok=True)
    rows = []
    for basis, areas in results["bases"].items():
        for area in ("east", "west", "closure"):
            rows.append({"basis": basis, "area": area, **vb.describe(areas[area])})
    first = target / "volve_in_place_basis.csv"
    pd.DataFrame(rows).to_csv(first, index=False, float_format="%.4g", lineterminator="\n")
    rows = []
    for basis in ("PDO", "Calibrated"):
        row = {"basis": basis, **results["metrics"][basis]}
        row |= {f"west_{k}": v for k, v in results["west"][basis].items()}
        rows.append(row)
    second = target / "volve_basis_metrics.csv"
    pd.DataFrame(rows).to_csv(second, index=False, float_format="%.4g", lineterminator="\n")
    return [first, second]


def wellbores() -> dict[str, dict[str, int]]:
    """Wellbores drilled into the reservoir at Volve, by phase and purpose (Sodir)."""
    table = sodir.read_table("wellbore_development_all", sodir.latest(data_dir() / "sodir"))
    counts = {"2007–2009": {}, "2013–2014": {}}
    for row in table:
        if row.get("wlbField") != volve.FIELD or not row["wlbEntryDate"]:
            continue
        if row["wlbContent"] == "WATER" and row["wlbPurpose"] == "PRODUCTION":
            continue  # water supply wells in the Utsira formation
        phase = "2007–2009" if int(row["wlbEntryDate"][-4:]) <= 2009 else "2013–2014"
        purpose = row["wlbPurpose"].lower()
        counts[phase][purpose] = counts[phase].get(purpose, 0) + 1
    return counts


def compute() -> dict:
    both = vb.bases()
    return {
        "bases": both,
        "metrics": {name: vb.metrics(basis) for name, basis in both.items()},
        "west": {name: vb.west_decision(basis) for name, basis in both.items()},
        "interval": vb.class_interval(),
        "classes": {
            name: {
                "n": len(inplace.prognosis_ratios(**vb.CLASSES[name])) if name in vb.CLASSES else 0,
                "closure": vb.describe(vb.bases(name)["Calibrated"]["closure"]),
                "west": vb.describe(vb.bases(name)["Calibrated"]["west"]),
                "decision": vb.west_decision(vb.bases(name)["Calibrated"]),
            }
            for name in (*vb.CLASSES, vb.BASE_MODEL)
        },
        "ratios": inplace.prognosis_ratios(**vb.CLASSES[vb.PRIMARY]),
    }


def build_report(results: dict) -> Report:
    p = vb.pdo()
    both, m, w = results["bases"], results["metrics"], results["west"]
    mp, mc = m["PDO"], m["Calibrated"]
    wp, wc = w["PDO"], w["Calibrated"]
    primary = results["classes"][vb.PRIMARY]
    ratios = results["ratios"]
    mild = results["classes"][vb.BASE_MODEL]
    drilled = wellbores()
    range_width = exploration.volume_results()["range_width"]
    plan = volve.plan()
    produced_in_three = plan["cumulative"]["mean"][3] / p["reserves"]["mean"]
    value_gap = abs(mp["npv_mean"] - p["npv"]["expected_price"])
    below_low = mc["below_pdo_low_in_place"]
    sw, cw = vb.describe(both["PDO"]["west"]), vb.describe(both["Calibrated"]["west"])
    east, west, closure = p["east"], p["west"], p["closure"]
    cal = {area: vb.describe(both["Calibrated"][area]) for area in ("east", "west", "closure")}
    interval = results["interval"]
    parameters = {r["parameter"]: r for r in exploration.parameter_results()}
    ranges = exploration.volume_results()["range"]["stated"]
    others = fields.select(fields.profiles("oe"), exclude=volve.FIELD)
    growth = fields.reserves_growth(others)["Shut down"]
    upside = vb.prospects(ratios)
    pud, sodir_facts, sim = (facts.read(s) for s in ("pud2005", "sodir", "sim2016"))
    today = sodir_facts["sodir.in_place_oil"]
    model = sim["sim2016.oil_in_place.initial.field"] / 1e6
    regions = {k: sim[f"sim2016.oil_in_place.initial.region{k}"] / 1e6 for k in (1, 8)}
    reserves_2010 = sodir_facts["sodir.recoverable_oil.2010"]
    final = sodir_facts["sodir.oil_production.total"]
    reserves_position = {
        name: float(np.mean(vb.reserves(both[name]["closure"]) < reserves_2010)) for name in both
    }
    lease = sum(
        pud[f"pud2005.costs_nominal.{item}.{year}"]
        for item in ("lease_investment_element_and_tariff", "lease_operation_and_maintenance")
        for year in (2007, 2008, 2009)
    )
    investments = pud["pud2005.costs_nominal.total_investments.total"]
    total_cost = pud["pud2005.costs_nominal.total_costs.total"]
    east_only_reserves = float(vb.reserves(east["mean"]))
    position = {
        name: {
            "today": float(np.mean(both[name]["closure"] < today)),
            "model": float(np.mean(both[name]["closure"] < model)),
        }
        for name in both
    }
    shift = cal["closure"]["p50"] / mp["in_place_p50"] - 1

    report = Report(
        "Volve concept selection on a recalibrated volume basis",
        "The development solution chosen for Volve in 2005 rested on an estimate of 27.5 million "
        "Sm3 of oil in place. This report rebuilds that estimate from the outside view — the "
        "record of how such estimates have turned out on the Norwegian shelf — and asks what a "
        "decision-maker should have changed in the concept with the recalibrated numbers in "
        "hand.",
        generator="python -m dmxkit.volve_concept build",
    )

    # ------------------------------------------------------------------ summary
    report.section("Summary")
    report.text(
        f"Recalibrated, the central estimate of oil in place falls from {mp['in_place_p50']:.1f} "
        f"to {cal['closure']['p50']:.1f} million Sm3 ({signed(100 * shift)} %) and the low case "
        f"from {mp['in_place_p90']:.1f} to {cal['closure']['p90']:.1f}. The high case hardly "
        "moves. "
        f"The chance of ending below the PDO's own low case is {percent(below_low)}, not 10 %.",
        "The whole difference lies in one place. The PDO's volume has two parts: an East, "
        "mapped with little uncertainty, and a West whose stated range spans a factor of four, "
        "whose expected volume is nearly twice its base model, and which carried "
        f"{percent(mp['west_share_of_mean'])} of the expected volume. The West is uncertain in "
        "the way an undrilled prospect is, and the record of such estimates is clear: on the "
        "shelf they have come in at less than half, with a spread several times wider than "
        "stated. For the East there is no record to hold it against, and it is left as stated.",
        "This is not enough to support a different concept. The East alone carries the "
        f"project — about {number(wc['east_only'])} million NOK after tax at the PDO's oil "
        "price, the same as the PDO's low case — and a smaller, less certain volume speaks for "
        "leased facilities with their own drilling rig even more than the PDO's basis did. It "
        "is enough to support a different development plan within that concept: build on the "
        "East, and make the wells for the West a decision to be taken after the West has been "
        "appraised from the platform. How strongly depends on how the West is treated: as a "
        f"prospect, its wells fail to pay {percent(wc['pair_does_not_pay'])} of the time; with "
        "only the PDO's uplift over its base model taken back, "
        f"{percent(mild['decision']['pair_does_not_pay'])}.",
    )
    report.cards(
        [
            (
                "Oil in place, central estimate",
                f"{mp['in_place_p50']:.1f} → {cal['closure']['p50']:.1f}",
                f"Million Sm3; PDO basis and calibrated basis. Low case {mp['in_place_p90']:.1f} "
                f"→ {cal['closure']['p90']:.1f}, high case {mp['in_place_p10']:.1f} → "
                f"{cal['closure']['p10']:.1f}",
            ),
            (
                "Chance of less than the PDO's low case",
                f"10 % → {percent(mc['below_pdo_low_in_place'])}",
                f"Less than {closure['p90']:.1f} million Sm3 in place",
            ),
            (
                "Oil in the West, central estimate",
                f"{vb.describe(both['PDO']['west'])['p50']:.1f} → {cal['west']['p50']:.1f}",
                f"Million Sm3; the 10–90 % range widens from {west['p90']:.1f}–{west['p10']:.1f} "
                f"to {cal['west']['p90']:.1f}–{cal['west']['p10']:.1f}",
            ),
            (
                "Chance that the West well pair does not pay",
                f"{percent(wp['pair_does_not_pay'])} → {percent(wc['pair_does_not_pay'])}",
                f"West below {wc['break_even_west']:.1f} million Sm3 in place",
            ),
            (
                "Expected value, all wells committed",
                f"{number(mp['npv_mean'])} → {number(mc['npv_mean'])}",
                "Million NOK 2005 after tax at 8 %, oil at 22 USD per barrel",
            ),
            (
                "Value in the low case",
                f"{number(mp['npv_p90'])} → {number(mc['npv_p90'])}",
                f"Chance of a loss {percent(mp['loss'], 1)} → {percent(mc['loss'], 1)}",
            ),
        ]
    )
    report.note(
        "Percentiles are named as in the PDO: P90 is the low case (a 90 % chance of more), P10 "
        "the high case. Everything up to the section *Hindsight* uses only what was on record "
        "when the concept was chosen."
    )

    # ------------------------------------------------------------------ decision
    report.section("The decision and its volume basis", "Decision")
    report.table(
        ["When", "What"],
        [
            ["1993", "Well 15/9-19 SR finds oil: 18 m of Hugin sandstone, tested"],
            ["1996", "Sidetrack 15/9-19 A: 88 m of oil-filled reservoir, deeper than expected; "
                     "oil down to 3 101 m, no oil-water contact"],
            ["1997", "15/9-19 B in the saddle to the south-east: water; sealed from Volve, so "
                     "it limits the structure to the east"],
            ["2002", "Ocean-bottom seismic acquired; basis for the mapping in the PDO"],
            ["November 2003", "Concept screening report (not in the dataset)"],
            ["November 2004", "Concept selection report (not in the dataset)"],
            ["February 2005", "PDO delivered; approved 22 April 2005"],
        ],
        left=(0, 1),
        caption="The decision in time (PDO p11–12, p34; Sodir).",
    )  # fmt: skip
    report.text(
        "The concept selection report is not available, so the volume basis is taken from the "
        "PDO, delivered three months later. What was chosen: a leased jack-up rig, Mærsk "
        "Inspirer, fitted with a process plant and used as production platform; wells drilled "
        f"from it, with {p['well_slots']} slots; oil to a leased storage vessel and on by "
        "shuttle tanker; gas to Sleipner A. Of the eight facility alternatives the PDO lists, "
        "two were taken to tender: this one, and a leased production vessel with subsea wells.",
    )
    report.table(
        ["Element of the solution", "PDO", "Depends on the volume through"],
        [
            [
                "Oil in place, Volve closure",
                f"Mean {closure['mean']:.1f}; P90 {closure['p90']:.1f}, P10 {closure['p10']:.1f}",
                "—",
            ],
            [
                "Reserves",
                f"Mean {p['reserves']['mean']:.1f}; P90 {p['reserves']['p90']:.1f}, P10 "
                f"{p['reserves']['p10']:.1f}",
                "Oil in place and permeability are the two largest factors (PDO 4.6)",
            ],
            [
                "Wells",
                f"{p['producers']} producers high on the structure, {p['injectors']} water "
                "injectors on the flanks; a near-horizontal producer and an injector in the "
                "west",
                "Where the oil is: each part of the field has its own wells",
            ],
            [
                "Capacity",
                f"Oil {number(p['capacity_oil'])} Sm3/d; three producers at 2 500–4 500 Sm3/d "
                "each; plateau 19 months",
                "Length of plateau, not its height",
            ],
            [
                "Field life",
                f"{p['life_months']:.0f} months to an economic cut-off; lease for "
                f"{p['lease_years']:.0f} years, then six months' notice",
                "Reserves; the leases are 58 % of all cost and run with time",
            ],
            [
                "Value",
                f"{number(p['npv']['expected_price'])} million NOK after tax; "
                f"{number(p['npv']['p90_profile'])} with the P90 profile, "
                f"{number(p['npv']['p10_profile'])} with the P10 profile",
                "Reserves",
            ],
            [
                "Reason for the choice",
                "Best profitability; “positive economics at low reserves (P90)”; much of it "
                "already built; own drilling rig throughout; a base for the prospects nearby",
                "The low case, and the upside in the area",
            ],
        ],
        left=(0, 1, 2),
    )
    report.text(
        f"Two things about the cost structure matter for what follows. Investments are "
        f"{number(investments)} million NOK of a total cost of {number(total_cost)}; the rest "
        "is paid as the field produces. And the right to end the lease begins after three "
        f"years, by which time {number(investments + lease)} million NOK — investments and "
        "three years of lease — are committed and, in the PDO's mean case, "
        f"{percent(produced_in_three)} of the oil has been produced. The concept limits what "
        "is sunk before production starts; it does not make the commitment small.",
    )

    # ------------------------------------------------------------------ inside view
    report.section("How the PDO's volume is built", "Inside view")
    report.table(
        ["Area", "Base model", "Mean", "P90", "P50", "P10", "Coefficient of variation"],
        [
            [name, f"{a['base']:.1f}", f"{a['mean']:.1f}", f"{a['p90']:.1f}", f"{a['p50']:.1f}",
             f"{a['p10']:.1f}", percent(a["sd"] / a["mean"])]
            for name, a in (("East", east), ("West", west), ("Volve closure", closure))
        ],
        caption="Oil in place, million Sm3 (PDO Table 3.4). The base model uses the most likely "
        "contact, 3 120 m.",
    )  # fmt: skip
    report.text(
        "The PDO divides the field into areas that “differ particularly in the seismic "
        "uncertainty”, and sums them into an East and a West. It does not say where the "
        "boundary runs or which wells lie in which area."
    )
    report.bullets(
        [
            f"*The East is well determined.* Its P90–P10 range is {east['p90']:.1f} to "
            f"{east['p10']:.1f}, a factor of {east['p10'] / east['p90']:.1f}; its mean "
            f"({east['mean']:.1f}) is slightly below its base model ({east['base']:.1f}).",
            f"*The West is not.* Its range is {west['p90']:.1f} to {west['p10']:.1f}, a factor "
            f"of {west['p10'] / west['p90']:.1f}. The PDO calls the interpretation uncertainty "
            f"on the western flank “considerable”. Its base model holds {west['base']:.1f}; "
            f"the uncertainty study nearly doubles that to a mean of {west['mean']:.1f}, "
            "because a deeper oil-water contact is judged more likely than a shallower one "
            "(Table 3.5: 55 % for a contact below the base model's 3 120 m, 24 % above it).",
            f"*The closure's mean exceeds its base model by "
            f"{closure['mean'] - closure['base']:.1f}, and all of that is in the West.* The "
            "plan's expected reserves, value and wells are built on the mean.",
            "*No contact had been found.* Neither oil well reached the oil-water contact; oil "
            "is proven down to 3 101 m. Whatever lies below that depth is a prognosis in the "
            "same sense as a prospect's, and it is this that lifts the mean above the base "
            "model.",
        ]
    )

    # ------------------------------------------------------------------ outside view
    report.section("What the record says about such estimates", "Outside view")
    rock, column = parameters["Rock volume"], parameters["Hydrocarbon column"]
    report.text(
        "The reference class study (`agents/rcf/out/volve-rcf-study.md`) compared estimates "
        "with outcomes at each stage on the Norwegian shelf. Three of its results bear on a "
        "volume in place estimated at sanction:",
    )
    report.table(
        ["Record", "Result", "Bearing on the Volve estimate"],
        [
            [
                "Volume in place prognosed without a well, against the volume recorded after "
                f"drilling; {primary['n']} discoveries from wells spudded before 2005",
                f"Median outcome {np.median(ratios):.2f} of the prognosis; one in ten below "
                f"{np.quantile(ratios, 0.1):.2f}, one in ten above {np.quantile(ratios, 0.9):.1f}",
                "Applies to a volume whose estimate rests on mapping, as the West's does",
            ],
            [
                "The factors of the volume equation, before and after drilling",
                f"Rock volume {rock['median']:.2f} and hydrocarbon column {column['median']:.2f} "
                "of prognosis in the median; porosity, net-to-gross and saturation unbiased",
                "The PDO's uplift from base model to mean comes from a deeper contact — a "
                "longer column. The record's columns come in shorter. Its low uncertainty on "
                "petrophysics agrees with the record",
            ],
            [
                "Stated P90–P10 ranges of volume in place",
                f"Held {percent(ranges['inside'])} of outcomes instead of 80 %; "
                f"{percent(ranges['below'])} fell below the low value",
                f"A typical prognosis range spans a factor of {range_width:.0f}; the West's "
                f"spans {west['p10'] / west['p90']:.1f} and the East's "
                f"{east['p10'] / east['p90']:.1f}. By its own stated uncertainty the West is a "
                "prognosis and the East is not",
            ],
            [
                f"Reserves at sanction against final recovery, {growth['n']} other fields that "
                "have shut down",
                f"Median {growth['median']:.2f}",
                "No class of in-place estimates at sanction exists in public data; this is the "
                "nearest check on the centre of the result below",
            ],
        ],
        left=(0, 1, 2),
    )
    report.text(
        "The rule used here follows from the first and third rows: *calibrate the part of an "
        "estimate that is as uncertain as an undrilled prognosis with the record of undrilled "
        "prognoses, and leave the well-determined part as stated.* The parts are told apart "
        "by the uncertainty the PDO itself states for them. For the well-determined part "
        "there is no public record to calibrate against, and the paper's finding that "
        "operators' ranges are too narrow concerns production, not volume in place. Leaving "
        "the East untouched makes the recalibration as small as the evidence allows.",
    )

    # ------------------------------------------------------------------ alternative basis
    report.section("The alternative basis", "Alternative basis")
    report.heading("Method")
    report.bullets(
        [
            f"East: as in the PDO — a lognormal distribution through its P90 and P10 "
            f"({east['p90']:.1f} and {east['p10']:.1f}).",
            f"West: the PDO's mean, {west['mean']:.1f}, multiplied by the ratio of result to "
            f"prognosis of a discovery drawn from the class ({primary['n']} discoveries on "
            "record at the end of 2004). The class is conditional on there being a discovery, "
            "which is granted to the West: it is not given a chance of holding no oil.",
            f"Closure: the sum, over {number(vb.DRAWS)} draws. Under the PDO basis East and "
            f"West are drawn with a correlation of {vb.correlation():.1f}, which reproduces "
            f"the PDO's closure percentiles ({mp['in_place_p90']:.1f}, {mp['in_place_p50']:.1f}, "
            f"{mp['in_place_p10']:.1f} against {closure['p90']:.1f}, {closure['p50']:.1f}, "
            f"{closure['p10']:.1f}); under the calibrated basis the West is drawn independently.",
        ]
    )
    report.heading("Result")
    stated = {area: vb.describe(both["PDO"][area]) for area in ("east", "west", "closure")}
    report.table(
        ["Area", "Basis", "P90 (low)", "P50", "Mean", "P10 (high)"],
        [
            [label, basis, *(f"{d[k]:.1f}" for k in ("p90", "p50", "mean", "p10"))]
            for label, area in (("East", "east"), ("West", "west"), ("Volve closure", "closure"))
            for basis, d in (("PDO", stated[area]), ("Calibrated", cal[area]))
        ],
        left=(0, 1),
        caption="Oil in place, million Sm3. The PDO rows are the reconstruction used here; they "
        "agree with Table 3.4 to within 0.5.",
    )  # fmt: skip
    report.chart(
        basis_chart(both, closure),
        "Read across at 0.5 for the central estimate, at 0.1 for the low case. Blue: the PDO's "
        "distribution as reconstructed, with its published percentiles as points. Orange: the "
        "same East with the West recalibrated. The two curves meet at the high end: the record "
        "has a long upper tail as well.",
    )
    report.text(
        f"The calibrated mean, {cal['closure']['mean']:.1f}, is close to the PDO's base model, "
        f"{closure['base']:.1f}: the outside view takes back most of what the uncertainty study "
        "added to the West. The centre moves more than the mean, because the class is skewed: "
        f"most undrilled volumes come in well under their prognosis, a few far over. The "
        f"calibrated median is {cal['closure']['p50'] / closure['mean']:.2f} of the PDO mean; "
        f"reserves at sanction ended at {growth['median']:.2f} of plan in the median field that "
        "has shut down, and the paper finds production at about 0.8 of the mean forecast in a "
        "field's first years. Three separate records point the same way.",
    )
    report.heading("How firm is it?")
    report.table(
        ["Treatment of the West", "Discoveries", "West P50", "Closure P90", "Closure P50",
         "Closure mean", "Closure P10", "West pair does not pay"],
        [
            [
                f"Class: {name[0].lower()}{name[1:]}" if c["n"] else name,
                str(c["n"]) if c["n"] else "—",
                f"{c['west']['p50']:.1f}",
                f"{c['closure']['p90']:.1f}",
                f"{c['closure']['p50']:.1f}",
                f"{c['closure']['mean']:.1f}",
                f"{c['closure']['p10']:.1f}",
                percent(c["decision"]["pair_does_not_pay"]),
            ]
            for name, c in results["classes"].items()
        ],
        caption="The result under three definitions of the class, and with no class at all: "
        "the PDO's own distribution for the West, scaled so that its mean is the base model's "
        f"{west['base']:.1f}. The first row is the one used: it holds only what was on record "
        "when the concept was chosen. The last column is explained under *Modification*.",
    )  # fmt: skip
    report.text(
        f"Resampling the {primary['n']} discoveries puts the calibrated P50 between "
        f"{interval['p50'][0]:.1f} and {interval['p50'][1]:.1f} and the P90 between "
        f"{interval['p90'][0]:.1f} and {interval['p90'][1]:.1f} (90 % intervals). The P10 is "
        f"loose, {interval['p10'][0]:.0f} to {interval['p10'][1]:.0f}: it hangs on a handful of "
        "discoveries that came in several times above prognosis. The low and central "
        "estimates do not depend on which class is used. Nor does the central estimate depend "
        "on using a class at all: taking back only the uplift that the uncertainty study added "
        f"to the West gives a closure P50 of {mild['closure']['p50']:.1f}. What the class adds "
        "is the width of the West's range, at both ends.",
    )

    # ------------------------------------------------------------------ consequences
    report.section("What the alternative basis does to reserves and value", "Consequences")
    report.text(
        "Both bases are put through the PDO's own figures: its three pairs of in-place and "
        "reserves percentiles give reserves for a volume in place (a recovery of about 43 %), "
        "and its three profile cases give value for reserves (Table 12.9). With the PDO basis "
        f"this returns an expected value of {number(mp['npv_mean'])} million NOK against the "
        f"PDO's {number(p['npv']['expected_price'])}.",
    )
    report.table(
        ["", "PDO basis", "Calibrated basis"],
        [
            ["Oil in place: P90 / P50 / P10",
             f"{mp['in_place_p90']:.1f} / {mp['in_place_p50']:.1f} / {mp['in_place_p10']:.1f}",
             f"{mc['in_place_p90']:.1f} / {mc['in_place_p50']:.1f} / {mc['in_place_p10']:.1f}"],
            ["Reserves: P90 / P50 / P10",
             f"{mp['reserves_p90']:.1f} / {mp['reserves_p50']:.1f} / {mp['reserves_p10']:.1f}",
             f"{mc['reserves_p90']:.1f} / {mc['reserves_p50']:.1f} / {mc['reserves_p10']:.1f}"],
            ["Chance of reserves below the PDO's P90", percent(mp["below_pdo_low_reserves"]),
             percent(mc["below_pdo_low_reserves"])],
            ["Value after tax: P90 / P50 / P10",
             f"{number(mp['npv_p90'])} / {number(mp['npv_p50'])} / {number(mp['npv_p10'])}",
             f"{number(mc['npv_p90'])} / {number(mc['npv_p50'])} / {number(mc['npv_p10'])}"],
            ["Expected value after tax", number(mp["npv_mean"]), number(mc["npv_mean"])],
            ["Chance of a loss", percent(mp["loss"], 1), percent(mc["loss"], 1)],
        ],
        left=(0,),
        caption="Volumes in million Sm3; value in million NOK of 2005 after tax at 8 %, oil at "
        "22 USD per barrel, all planned wells drilled.",
    )  # fmt: skip
    report.chart(
        value_chart(both),
        "The project loses money only below about "
        f"{mp['break_even_reserves']:.0f} million Sm3 of reserves, which the East nearly rules "
        "out by itself. The calibrated basis moves the middle of the curve, not its foot.",
    )
    report.text(
        f"The project stays sound: the chance of a loss rises from {percent(mp['loss'], 1)} to "
        f"{percent(mc['loss'], 1)}. What changes is the margin. The PDO's argument that the "
        f"concept has “positive economics at low reserves” rested on {number(mp['npv_p90'])} "
        f"million NOK in the low case; the calibrated low case leaves {number(mc['npv_p90'])}. "
        f"The expected value falls by {number(mp['npv_mean'] - mc['npv_mean'])}, a sixth. Oil "
        "price, which the PDO shows to matter more than volume (−233 at 15 USD per barrel), is "
        "outside this report.",
    )

    # ------------------------------------------------------------------ concept
    report.section("Does the alternative basis support a different concept?", "Concept")
    report.text(
        "No, on the evidence available. The PDO gives no cost, production or value for any "
        "alternative it rejected, so none can be evaluated on either basis. What can be said "
        "is which way a smaller and less certain volume pushes:"
    )
    report.table(
        ["Alternative in the PDO", "Effect of the calibrated basis", "Basis for saying so"],
        [
            [
                "Owned facilities: a fixed platform at Volve, in three variants",
                "Against. More is sunk before production, for facilities that outlive the field",
                "The PDO's own reasons for leasing; no numbers for these alternatives",
            ],
            [
                "Tie-in to Sleipner A: subsea wells, or modification of Sleipner A",
                "Cannot be said",
                "The PDO states that no concept using existing infrastructure for the oil was "
                "shown to be economic; it does not say why",
            ],
            [
                "Leased production vessel with subsea wells (the other tendered concept)",
                "Against. Subsea wells are drilled before or apart from production; the "
                f"calibrated basis makes two of the six wells a decision with a "
                f"{percent(wc['pair_does_not_pay'])} chance of not paying, and calls for "
                "appraisal while producing",
                "Section below; the PDO names the rig on the platform a key element",
            ],
            [
                "Leased jack-up with process plant and own rig (chosen)",
                "For. Low sunk cost; wells can be added, moved or dropped as the West is tested",
                f"The East alone is worth {number(wc['east_only'])} million NOK",
            ],
        ],
        left=(0, 1, 2),
    )
    report.text(
        "The middle column is reasoning from the cost structure and from the well decision "
        "below; it is not a valuation.",
        "The estimates are, in the terms of the task, too similar to the original basis to "
        "overturn the concept: the East is unchanged, and the East decides. They are different "
        "enough to change the reason for the concept and the plan built on it. Under the PDO "
        "basis the jack-up wins on cost and the West's wells are a matter of course. Under the "
        "calibrated basis it wins on the freedom to decide the West later, and that freedom "
        "should be used.",
    )

    # ------------------------------------------------------------------ modification
    report.section("The modification: build on the East, decide the West later", "Modification")
    report.heading("The West well pair as a decision")
    report.text(
        f"Each million Sm3 in place is worth about {wc['value_per_volume']:.0f} million NOK "
        f"after tax by the PDO's figures, and the PDO puts the effect of two wells at "
        f"{p['two_wells']:.0f} million NOK. A producer and an injector for the West therefore "
        f"pay for themselves if the West holds more than {wc['break_even_west']:.1f} million "
        "Sm3.",
    )
    report.chart(
        west_chart(both, wc["break_even_west"]),
        "Blue: the PDO's West, lognormal through its P90 and P10. Orange: the PDO's mean for "
        "the West times the class ratio. Dashed: the volume at which a producer and an "
        "injector pay for themselves. Where each curve crosses the dashed line is the chance "
        "that the pair does not pay. The steps in the orange curve are the "
        f"{primary['n']} discoveries of the class.",
    )
    report.table(
        ["", "PDO basis", "Calibrated basis"],
        [
            ["West oil in place: P90 / P50 / P10",
             f"{sw['p90']:.1f} / {sw['p50']:.1f} / {sw['p10']:.1f}",
             f"{cw['p90']:.1f} / {cw['p50']:.1f} / {cw['p10']:.1f}"],
            ["Chance that the pair does not pay", percent(wp["pair_does_not_pay"], 1),
             percent(wc["pair_does_not_pay"])],
            ["Expected gain from the pair", number(wp["mean_gain"]), number(wc["mean_gain"])],
            ["Median gain from the pair", number(wp["median_gain"]), number(wc["median_gain"])],
            ["A: commit all six wells", number(wp["commit"]), number(wc["commit"])],
            ["B: East wells only", number(wp["east_only"]), number(wc["east_only"])],
            ["C: East first, West pair if appraisal supports it", number(wp["staged"]),
             number(wc["staged"])],
            ["Most an appraisal of the West is worth (C less the better of A and B)",
             number(wp["information"]), number(wc["information"])],
        ],
        left=(0,),
        caption="Expected value in million NOK of 2005 after tax. C assumes the appraisal "
        "settles the West's volume and leaves out its cost, which the PDO does not give.",
    )  # fmt: skip
    report.text(
        "It is assumed here that the near-horizontal producer and the injector that the PDO "
        "places in the western part of the field are the wells that drain the West of Table "
        "3.4; the PDO does not link wells to volume areas.",
        f"Under the PDO basis there is nothing to decide: the pair fails to pay in "
        f"{percent(wp['pair_does_not_pay'], 1)} of cases and an appraisal is worth nothing. "
        f"Under the calibrated basis the pair still has a positive expected gain, but it fails "
        f"to pay about one time in three, and its median gain is {number(wc['median_gain'])}, "
        f"not {number(wp['median_gain'])}. Knowing the West's volume first is worth up to "
        f"{number(wc['information'])} million NOK after tax — about a third of what the PDO "
        "implies for one well. That is small against the project, and it is cheap to obtain "
        "on this concept: the rig is on the platform, and the PDO already plans a sidetrack "
        "from the western injector to test prospects further west. With the milder treatment "
        f"of the West the pair fails to pay {percent(mild['decision']['pair_does_not_pay'])} of "
        f"the time and the information is worth {number(mild['decision']['information'])} "
        "million NOK: the case for appraising first rests on taking the record of prognoses "
        "seriously for the West.",
    )
    report.heading("The modified solution")
    report.table(
        ["Element", "PDO", "Modified", "Reason in the volumes"],
        [
            [
                "Concept",
                "Leased jack-up with process plant, storage vessel, gas to Sleipner A",
                "Unchanged",
                "The East alone carries it; a wider range favours its low sunk cost and own rig",
            ],
            [
                "Volume the plan is built on",
                f"Closure mean, {closure['mean']:.1f}",
                f"East, {east['mean']:.1f}, as the committed case; West as an option valued at "
                f"its calibrated range, {cal['west']['p90']:.1f}–{cal['west']['p10']:.1f}",
                "The West is as uncertain as an undrilled prospect",
            ],
            [
                "Wells committed at sanction",
                "Three producers, three injectors",
                "Two producers and two injectors. The near-horizontal producer and the "
                "injector that the PDO places in the western part held back",
                f"{percent(wc['pair_does_not_pay'])} chance that they do not pay",
            ],
            [
                "Appraisal of the West",
                "A sidetrack from the western injector, for the prospects beyond",
                "A pilot into the West from the platform, early in the drilling "
                "sequence, with a stated criterion: drill the pair if the West holds more than "
                f"about {wc['break_even_west']:.0f} million Sm3",
                f"Worth up to {number(wc['information'])} million NOK; decides two wells",
            ],
            [
                "Capacity",
                f"{number(p['capacity_oil'])} Sm3/d oil",
                "Unchanged",
                "Two producers at up to 4 500 Sm3/d each fill it; lease cost runs with time, "
                "so a lower rate would cost more than it saves",
            ],
            [
                "Expectations given to owners and authorities",
                f"Reserves {p['reserves']['mean']:.1f}; value {number(p['npv']['expected_price'])}",
                f"Reserves about {mc['reserves_p50']:.0f} with a low case of "
                f"{mc['reserves_p90']:.1f}; value {number(mc['npv_p50'])} in the central case",
                f"{percent(mc['below_pdo_low_reserves'])} chance of less than the PDO's P90",
            ],
            [
                "Value put on prospects near Volve",
                f"{upside['stated']:.1f} million Sm3 in place, risked (Table 13.1)",
                f"{upside['with_median_ratio']:.0f} to {upside['with_mean_ratio']:.0f}",
                "Chances of discovery are sound in the record; volumes are "
                f"{np.median(ratios):.2f} (median) to {ratios.mean():.2f} (mean) of prognosis",
            ],
        ],
        left=(0, 1, 2, 3),
    )
    report.text(
        f"With the West held back, the committed plan stands on {east_only_reserves:.1f} "
        f"million Sm3 of reserves and {number(wc['east_only'])} million NOK — the level of the "
        "PDO's own low case, reached here without relying on the part of the volume that the "
        "PDO itself marks as poorly determined."
    )

    # ------------------------------------------------------------------ hindsight
    report.section("Hindsight: what happened", "Hindsight")
    report.note(
        "Nothing in this section was known in 2005, and none of it was used above. It shows "
        "how the two bases compare with the outcome."
    )
    report.chart(
        basis_chart(
            both,
            closure,
            {
                f"Sodir, field today: {today:.1f}": today,
                f"Simulation model, 2016: {model:.1f}": model,
            },
        ),
        "The same curves as before, with the two later estimates of oil in place: Sodir's "
        "figure for the field, which is the operator's geological model of 2010, and the "
        "history-matched simulation model of 2016.",
    )
    report.table(
        ["Outcome", "Oil in place", "Chance of less, PDO basis", "Chance of less, calibrated"],
        [
            ["Sodir field table", f"{today:.1f}", percent(position["PDO"]["today"]),
             percent(position["Calibrated"]["today"])],
            ["Simulation model, 2016", f"{model:.1f}", percent(position["PDO"]["model"]),
             percent(position["Calibrated"]["model"])],
        ],
        caption="Where the outcome falls in each distribution. An outcome near 50 % is one "
        "the basis saw as typical; one below 10 % it saw as a low case.",
    )  # fmt: skip
    first, second = drilled["2007–2009"], drilled["2013–2014"]
    total_wellbores = sum(first.values()) + sum(second.values())
    report.bullets(
        [
            f"The field's oil in place today, {today:.1f} million Sm3, is below what the PDO "
            f"carried for the East alone ({east['mean']:.1f}). How the outcome divides between "
            "the PDO's East and West is not known.",
            "In the 2016 simulation model the main structure has a region labelled north-west "
            f"with {regions[1]:.2f} million Sm3, one labelled south-west with "
            f"{regions[8]:.2f}, and one labelled “aquifer west” that holds water. How these "
            "map onto the PDO's West has not been established.",
            f"At the end of 2010 recoverable oil was put at {reserves_2010:.2f} million Sm3: "
            f"an outcome the PDO basis gave a {percent(reserves_position['PDO'])} chance of "
            f"falling below, the calibrated basis {percent(reserves_position['Calibrated'])}.",
            f"Wells: the first phase (2007–2009) gave {first['production']} producers, "
            f"{first['injection']} injectors and {first['observation']} observation wellbores; "
            "the third producer, F-15 C, followed three observation wellbores from the same "
            f"slot. A second phase in 2013–2014 added {second['production']} producers, "
            f"{second['injection']} injector and {second['observation']} more observation "
            f"wellbores: {total_wellbores} wellbores in all, against "
            f"{p['producers'] + p['injectors']} planned.",
            f"Final recovery was {final:.2f} million Sm3, after the second phase and more than "
            "twice the planned investment.",
        ]
    )
    report.text(
        "By Sodir's figure the outcome lies near the calibrated basis's low case; by the "
        "simulation model's, a little under its centre. On the PDO basis both are low cases. "
        "The development that took place — observation wellbores from the platform, then "
        "each producer — resembles the modified plan, arrived at after sanction instead of "
        "before it. One field proves nothing about a method; the support for the method is "
        "the record it is built on.",
    )

    # ------------------------------------------------------------------ model
    report.section("Model specification", "Model")
    report.table(
        ["Element", "Value", "Source"],
        [
            ["Decision", "Volume basis for the concept; within the concept, when to commit the "
                         "western producer and injector", "This report"],
            ["Alternatives for the West", "A: commit with the others. B: never. C: appraise, "
                                          "then decide", "This report"],
            ["Uncertainty: oil in place, East",
             f"Lognormal, P90 {east['p90']:.1f}, P10 {east['p10']:.1f}", "PDO Table 3.4, p19"],
            ["Uncertainty: oil in place, West, PDO basis",
             f"Lognormal, P90 {west['p90']:.1f}, P10 {west['p10']:.1f}; correlation with East "
             f"{vb.correlation():.1f}", "PDO Table 3.4; correlation fitted to the closure row"],
            ["Uncertainty: oil in place, West, calibrated basis",
             f"{west['mean']:.1f} × ratio drawn from {primary['n']} discoveries, wells spudded "
             "before 2005", "PDO Table 3.4; `rcfkit.inplace.prognosis_ratios`"],
            ["Reserves from oil in place",
             f"Lines through ({closure['p90']:.1f}, {p['reserves']['p90']:.1f}), "
             f"({closure['p50']:.1f}, {p['reserves']['p50']:.2f}), ({closure['p10']:.1f}, "
             f"{p['reserves']['p10']:.2f}), continued outside", "PDO Tables 3.4 and 4.5"],
            ["Value from reserves",
             f"Lines through ({p['reserves']['p90']:.1f}, {number(p['npv']['p90_profile'])}), "
             f"({p['reserves']['mean']:.1f}, {number(p['npv']['expected_price'])}), "
             f"({p['reserves']['p10']:.2f}, {number(p['npv']['p10_profile'])}), continued "
             "outside", "PDO Tables 4.5 and 12.9"],
            ["Two wells", f"{p['two_wells']:.0f} million NOK after tax "
                          f"({p['two_wells_before_tax']:.0f} before tax)",
             "PDO Table 12.9, “two extra wells”"],
            ["Value measure", "Net present value after tax at 8 %, million NOK of 2005, oil at "
                              "22 USD per barrel Brent", "PDO Table 12.7"],
            ["Calculation", f"{number(vb.DRAWS)} Monte Carlo draws, seed {vb.SEED}",
             "`dmxkit.volve_basis`"],
        ],
        left=(0, 1, 2),
    )  # fmt: skip

    # ------------------------------------------------------------------ limits
    report.section("Assumptions and limits", "Limits")
    report.bullets(
        [
            "The West is treated as an undrilled prognosis because its stated uncertainty is "
            "that of one. The PDO does not say whether a well lies in it; the discovery well "
            "was drilled in what the 1993 report called the western segment of the structure. "
            "It is also part of a proven accumulation mapped on new seismic. If the class is "
            "too harsh for it, the truth lies between the two bases; the table of treatments "
            "shows a milder one.",
            "The East is left as stated. If its range is too narrow as well, the low case is "
            "lower than shown here and the conclusions on the concept are unchanged.",
            "The class compares prognosis with the volume recorded soon after drilling, not "
            "with the volume finally established.",
            "Reserves and value are read off straight lines through three PDO cases each and "
            "continued beyond them. Below the PDO's low case the true value may fall faster "
            "(fixed costs) or slower (earlier stop); the PDO gives no case there.",
            "The West's oil is assumed to be produced only by the two wells the PDO places "
            "in the western part, and those wells to produce nothing else; the "
            "effect of removing two wells is taken as the reverse of the PDO's effect of "
            "adding two. A near-horizontal producer is likely to cost more than an average "
            "well, which would raise the break-even volume.",
            "The appraisal is assumed to settle the West's volume. A real pilot narrows it.",
            "Price, cost and schedule uncertainty are left out on purpose: the question here "
            "is what the volume basis alone changes.",
            "No alternative concept can be valued. The concept screening and concept selection "
            "reports, which held the comparison, are not in the dataset.",
        ]
    )
    report.section("How this was made", "How")
    report.bullets(
        [
            "Inputs: the fact register (`data/facts/pud2005.csv`, `sodir.csv`, `sim2016.csv`) "
            "and the reference class tables of `rcfkit`. No number was read from a document "
            "for this report.",
            "Code: `dmxkit.volve_basis` (distributions, relations, decision) and "
            "`dmxkit.volve_concept` (this report); `make dmx-volve` rebuilds it. Tables: "
            "`agents/dmx/out/data/`.",
            f"Checks: the reconstruction returns the PDO's closure percentiles within 0.5 "
            f"million Sm3 and its expected value within {value_gap:.0f} "
            "million NOK; the calibrated result is shown for three class definitions and with "
            "a resampling interval.",
            "Not done: a simulation of an East-only development; a decision model with price "
            "and cost; a valuation of the rejected concepts.",
        ]
    )
    return report


def build(target_dir: Path) -> list[Path]:
    results = compute()
    report = build_report(results)
    written = [
        report.write_markdown(target_dir / "volve-concept-basis.md"),
        report.write_html(
            target_dir / "volve-concept-basis" / "index.html",
            plotly="../assets/plotly.min.js",
            link_prefix="../",
        ),
    ]
    return written + write_tables(target_dir / "data", results)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("build",))
    parser.parse_args(argv)
    for path in build(repo_root() / OUT):
        print(f"written: {path} ({path.stat().st_size / 1e3:.0f} kB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
