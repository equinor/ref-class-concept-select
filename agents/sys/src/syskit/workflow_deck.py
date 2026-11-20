"""Slide deck on the workflow of this repository and what it has been used for.

    python -m syskit.workflow_deck build

writes ``agents/sys/out/workflow-deck/index.html`` and its figures. The
diagrams are also written as separate SVG files in ``figs/``; among them the
figure of what the workflow has been used for (``use-case.svg``), the flow
chart of its steps (``flow-chart.svg``) and the comparison of the original
and the modified development plan (``concept-comparison.svg``). Numbers on
the slides are computed from the same code as the reports.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

import numpy as np

from syskit import facts
from syskit.charts import BLUE as CHART_BLUE
from syskit.charts import ORANGE as CHART_ORANGE
from syskit.charts import Chart, Series
from syskit.paths import repo_root
from syskit.report import number, percent
from syskit.slides import Deck
from syskit.svg import BLUE, GREEN, INK, LINE, MUTED, ORANGE, PAPER, PURPLE, SLATE, Svg, tint

OUT = "agents/sys/out/workflow-deck"
AGENT = {"doc": BLUE, "sim": GREEN, "rcf": ORANGE, "dmx": PURPLE, "sys": SLATE}
OIL, WATER, SEA = "#fdba74", "#bfdbfe", "#e0f2fe"


# ---------------------------------------------------------------------------- numbers
def numbers() -> dict:
    """The numbers behind the diagrams of the first use and of the two plans."""
    from dmxkit import volve_basis as vb
    from rcfkit import inplace, volve

    pud, sodir = facts.read("pud2005"), facts.read("sodir")
    plan, outcome = volve.plan(), volve.outcome()
    both = vb.bases()
    ratios = inplace.prognosis_ratios(**vb.CLASSES[vb.PRIMARY])
    return {
        "pdo": vb.pdo(),
        "plan_oil": plan["reserves"]["mean"],
        "actual_oil": outcome["total"],
        "investment_plan": pud["pud2005.costs_nominal.total_investments.total"],
        "investment_actual": sodir["sodir.investment.total"],
        "class_ratio": float(np.median(ratios)),
        "class_low": float(np.quantile(ratios, 0.1)),
        "class_high": float(np.quantile(ratios, 0.9)),
        "class_n": len(ratios),
        "metrics": {name: vb.metrics(basis) for name, basis in both.items()},
        "west": {name: vb.west_decision(basis) for name, basis in both.items()},
        "calibrated": {a: vb.describe(both["Calibrated"][a]) for a in ("west", "closure")},
    }


def results() -> dict:
    """The numbers and charts shown on the slides, from the domains' own code."""
    from dmxkit import volve_basis as vb
    from dmxkit import volve_concept
    from rcfkit import expert, exploration, fields, review, study, volve

    pud, sodir = facts.read("pud2005"), facts.read("sodir")
    outcome = volve.outcome()
    probability = exploration.probability_results()
    volumes = exploration.volume_results()
    sample = exploration.volume_sample("ip")
    prospects = volve.prospect()
    comparison = volve.comparison()
    table = fields.profiles("oe")
    others = fields.select(table, exclude=volve.FIELD)
    monthly = fields.distribution(others, bootstrap=200).set_index("years")
    expert_class = expert.reference_class()
    quantiles = expert_class[list(fields.HORIZONS)].quantile([0.1, 0.5, 0.9])
    volve_row = table.set_index("field").loc[volve.FIELD]
    backtest = fields.backtest(table, horizons=(3,))[3]
    both = vb.bases()
    west = {name: vb.west_decision(basis) for name, basis in both.items()}

    oil_years = list(range(2007, 2017))
    investment_years = list(range(2005, 2017))
    short_years = [f"’{y % 100:02d}" for y in investment_years]
    charts = {
        "doc-oil": Chart(
            "doc-oil", "Oil per year, million Sm3", "", "",
            [
                Series("bar", oil_years, name="Plan (PDO mean)", color=CHART_BLUE,
                       y=[pud.get(f"pud2005.oil_production.mean.{y}", 0.0) for y in oil_years]),
                Series("bar", oil_years, name="Actual", color=CHART_ORANGE,
                       y=[sodir.get(f"sodir.oil_production.{y}", 0.0) for y in oil_years]),
            ],
        ),
        "doc-investment": Chart(
            "doc-investment", "Investments per year, million NOK", "", "",
            [
                Series("bar", short_years, name="Plan (PDO)", color=CHART_BLUE,
                       y=[pud.get(f"pud2005.costs_nominal.total_investments.{y}", 0.0)
                          for y in investment_years]),
                Series("bar", short_years, name="Actual", color=CHART_ORANGE,
                       y=[sodir.get(f"sodir.investment.{y}", 0.0) for y in investment_years]),
            ],
        ),
        "review-probability": replace(
            review.reliability_chart(expert.probability_calibration(), probability),
            title="Chance of discovery: stated against found",
            x_title="Stated probability", y_title="Share that were discoveries",
        ),
        "review-profile": replace(
            review.profile_chart(
                {"low": list(quantiles.loc[0.1]), "median": list(quantiles.loc[0.5]),
                 "high": list(quantiles.loc[0.9])},
                monthly,
                {y: float(volve_row[y]) for y in volve.YEARS},
            ),
            title="Reserves produced, by year of production",
            y_title="Fraction of sanctioned reserves",
        ),
        "study-volume": replace(
            study.volume_chart(sample, prospects[prospects["discovery"] == 1]),
            title="Volume in place: found against prognosed",
            x_title="Prognosed, million Sm3 o.e.", y_title="Found, million Sm3 o.e.",
        ),
        "study-volve": replace(
            study.volve_chart(comparison), title="Volve: cumulative oil, million Sm3", y_title=""
        ),
        "dmx-basis": replace(
            volve_concept.basis_chart(both, vb.pdo()["closure"]),
            title="Oil in place, Volve closure", x_title="Million Sm3",
        ),
        "dmx-west": replace(
            volve_concept.west_chart(both, west["Calibrated"]["break_even_west"]),
            title="Oil in place, West", x_title="Million Sm3",
        ),
    }  # fmt: skip
    break_even = charts["dmx-west"].series[2]
    charts["dmx-west"].series[2] = replace(break_even, name="Two wells break even")
    months_late = (outcome["start"].year - volve.PLAN_FIRST_OIL.year) * 12 + (
        outcome["start"].month - volve.PLAN_FIRST_OIL.month
    )
    return {
        **numbers(),
        "charts": charts,
        "months_late": months_late,
        "expected_discoveries": probability["all"]["expected_discoveries"],
        "discoveries": probability["all"]["discoveries"],
        "volume_median": volumes["ip"]["median"],
        "range_inside": volumes["range"]["stated"]["inside"],
        "backtest_inside": backtest["inside"],
        "backtest_n": backtest["n"],
        "first_year_calendar": float(quantiles.loc[0.5, 1]),
        "first_year_monthly": float(monthly.loc[1, "q50"]),
        "below_low_years": [
            int(y) for y in comparison.loc[comparison["actual"] < comparison["plan_low"], "years"]
        ],
    }


# ---------------------------------------------------------------------------- diagrams
def infrastructure() -> Svg:
    s = Svg(1600, 740)
    columns = [(40, 300, "Sources"), (430, 330, "Shared data layer"), (850, 270, "Agents"),
               (1210, 350, "Deliverables")]  # fmt: skip
    for x, w, title in columns:
        s.text(x + w / 2, 42, title, size=30, weight=700, anchor="middle")
    sources = [
        ("Volve data", ["plan, reports, production,", "simulation model"]),
        ("Sodir fact pages", ["all fields on the shelf"]),
        ("Expert study", ["notebook, data, slides"]),
        ("Literature", ["reference paper"]),
    ]
    shared = [
        ("Manifest", ["checksum of every raw file"]),
        ("Snapshots", ["public tables, by date"]),
        ("Converted documents", ["Markdown, page by page"]),
        ("Fact register", ["one number per row:", "value · unit · page · method"]),
    ]
    agents = [("doc", "documents"), ("sim", "reservoir model"), ("rcf", "outside view"),
              ("dmx", "decisions")]  # fmt: skip
    outputs = [
        ("Analyses", ["Markdown"]),
        ("Web reports", ["charts and tables"]),
        ("Tables", ["CSV, for the next agent"]),
        ("Skills", ["procedures that worked"]),
    ]
    for index, (title, rows) in enumerate(sources):
        s.box(40, 70 + index * 132, 300, 114, title, rows, color=SLATE)
    for index, (title, rows) in enumerate(shared):
        s.box(430, 70 + index * 132, 330, 114, title, rows, color=AGENT["sys"])
    for index, (name, role) in enumerate(agents):
        s.box(850, 70 + index * 132, 270, 114, name, [role], color=AGENT[name], title_size=34)
    for index, (title, rows) in enumerate(outputs):
        s.box(1210, 70 + index * 132, 350, 114, title, rows, color=SLATE)
    for x1, x2 in ((348, 422), (768, 842), (1128, 1202)):
        s.arrow(x1, 325, x2, 325, color=INK, width=6)
    s.path("M985 590 C985 640 595 640 595 596", color=MUTED, width=3, dash=True, arrow=True)
    s.note(790, 652, "agents add facts and converted documents", anchor="middle")
    s.note(40, 616, "raw data: outside the repository, read-only", color=MUTED)
    s.rect(40, 672, 1520, 56, fill=tint(SLATE, 0.9), stroke="none", radius=12)
    s.text(800, 709, "sys   ·   guidelines   ·   provenance   ·   quality gates   ·   make check"
           "   ·   git", size=26, weight=600, fill=PAPER, anchor="middle")  # fmt: skip
    return s


def roles() -> Svg:
    s = Svg(1600, 740)
    cards = [
        ("doc", "Documents", ["convert · translate", "extract · report"],
         ["Markdown, figures", "facts, web reports"], "PDO, discovery report, paper"),
        ("sim", "Reservoir model", ["run · compare", "extract"],
         ["volumes, profiles", "sensitivities"], "Eclipse deck runs in OPM Flow"),
        ("rcf", "Outside view", ["build reference classes", "test · calibrate"],
         ["distributions", "calibration factors"], "expert study reviewed, redone"),
        ("dmx", "Decisions", ["frame · model", "solve"],
         ["decision models", "modified plans"], "volume basis; model planned"),
    ]  # fmt: skip
    for index, (name, title, does, delivers, so_far) in enumerate(cards):
        x, color = 40 + index * 390, AGENT[name]
        s.rect(x, 20, 350, 470, fill=tint(color), stroke=color)
        s.rect(x, 20, 350, 92, fill=color, stroke="none")
        s.text(x + 26, 82, name, size=50, weight=750, fill=PAPER)
        s.text(x + 324, 80, title, size=25, weight=600, fill=PAPER, anchor="end")
        s.text(x + 26, 156, "does", size=20, weight=700, fill=color)
        s.lines(x + 26, 190, does, size=25)
        s.text(x + 26, 280, "delivers", size=20, weight=700, fill=color)
        s.lines(x + 26, 314, delivers, size=25)
        s.line(x + 26, 392, x + 324, 392, color=color, width=2)
        s.text(x + 26, 426, "so far", size=20, weight=700, fill=color)
        s.text(x + 26, 460, so_far, size=21, fill=MUTED)
        s.arrow(x + 175, 498, x + 175, 548, color=color, width=5)
        s.arrow(x + 215, 548, x + 215, 498, color=color, width=5)
    s.rect(40, 556, 1520, 62, fill=PAPER, stroke=INK, width=3)
    s.text(800, 597, "hand-offs are files:   fact register   ·   tables   ·   reports",
           size=28, weight=600, anchor="middle")  # fmt: skip
    s.rect(40, 652, 1520, 72, fill=tint(SLATE, 0.9), stroke="none", radius=12)
    s.text(70, 699, "sys", size=42, weight=750, fill=PAPER)
    s.text(800, 698, "rules   ·   shared data   ·   checks   ·   integration", size=28,
           weight=600, fill=PAPER, anchor="middle")  # fmt: skip
    return s


def agent_setup() -> Svg:
    s = Svg(1600, 740)
    steps = [
        ("AGENTS.md", "rules for every agent", SLATE),
        (".github/agents/rcf.agent.md", "who the agent is", SLATE),
        ("agents/rcf/README.md", "charter: role, inputs, outputs", ORANGE),
        ("agents/rcf/skills/…/SKILL.md", "procedure and lessons", ORANGE),
        ("agents/rcf/src · tests", "code for every number", ORANGE),
        ("agents/rcf/out", "reports and tables", ORANGE),
    ]
    for index, (path, meaning, color) in enumerate(steps):
        y = 20 + index * 118
        s.rect(40, y, 600, 86, fill=tint(color), stroke=color)
        s.rect(40, y, 10, 86, fill=color, stroke="none", radius=5)
        s.text(72, y + 54, path, size=30, weight=650)
        s.text(670, y + 54, meaning, size=30, fill=MUTED)
        if index < len(steps) - 1:
            s.arrow(340, y + 90, 340, y + 114, color=MUTED, width=4)
    s.rect(1180, 20, 380, 322, fill=PAPER, stroke=INK, width=3)
    s.text(1210, 70, "one command each", size=26, weight=700)
    s.lines(1210, 120, ["make setup", "make check", "make doc-volve", "make rcf-volve",
                        "make dmx-volve"], size=28, gap=1.5, fill=MUTED)  # fmt: skip
    s.rect(1180, 374, 380, 322, fill=PAPER, stroke=INK, width=3)
    s.text(1210, 424, "before a hand-off", size=26, weight=700)
    s.lines(1210, 474, ["tests pass", "facts validate", "raw data unchanged",
                        "what was not checked", "is written down"], size=28, gap=1.5,
            fill=MUTED)  # fmt: skip
    return s


def number_travels() -> Svg:
    s = Svg(1600, 740)
    stations = [
        ("Source", "PDO, page 19", ["Tabell 3.4", "Volve lukningen", "27,5"], SLATE),
        ("Markdown", "page marker kept", ["<!-- page 19 -->", "| Volve closure |", "| 27.5 |"],
         BLUE),
        ("Fact", "one row", ["stooip · closure · mean", "27.5 MSm3", "p19 table 3.4 · read"],
         BLUE),
        ("Code", "reads the register", ['facts.read("pud2005")', "", "no number typed"], PURPLE),
        ("Report", "sentence and chart", ["“… 27.5 million Sm3", "of oil in place”", ""], PURPLE),
    ]  # fmt: skip
    checks = [
        "", "digits compared with the PDF text", "unit, source, method validated",
        "tests on hand-worked cases", "rendered and looked at",
    ]  # fmt: skip
    for index, (title, sub, rows, color) in enumerate(stations):
        x = 30 + index * 314
        s.rect(x, 110, 286, 330, fill=tint(color), stroke=color)
        s.rect(x, 110, 286, 76, fill=color, stroke="none")
        s.text(x + 143, 160, title, size=34, weight=700, fill=PAPER, anchor="middle")
        s.text(x + 143, 228, sub, size=22, fill=MUTED, anchor="middle", italic=True)
        s.rect(x + 18, 256, 250, 160, fill=PAPER, stroke=LINE)
        s.lines(x + 34, 302, rows, size=20, gap=1.9)
        if index < len(stations) - 1:
            s.arrow(x + 288, 275, x + 311, 275, color=INK, width=4)
        if checks[index]:
            s.path(f"M{x + 143} 520 L{x + 143} 452", color=ORANGE, width=4, arrow=True)
            s.text(x + 143, 560, "check", size=22, weight=700, fill=ORANGE, anchor="middle")
            words = checks[index].split(" ")
            half = (len(words) + 1) // 2
            s.lines(x + 143, 596, [" ".join(words[:half]), " ".join(words[half:])], size=21,
                    fill=MUTED, anchor="middle")  # fmt: skip
    s.text(800, 60, "Every number can be followed back to a page", size=32, weight=600,
           anchor="middle")  # fmt: skip
    return s


def use_case(r: dict) -> Svg:
    p, m = r["pdo"], r["metrics"]
    cal, west = r["calibrated"], r["west"]["Calibrated"]
    s = Svg(1600, 800, background=PAPER)
    s.text(800, 48, "What the workflow has been used for: one concept selection, Volve 2005",
           size=34, weight=700, anchor="middle")  # fmt: skip
    panels = [
        ("1", "Read the plan", "doc", False),
        ("2", "Calibrate the basis", "rcf", False),
        ("3", "Decide on the new basis", "dmx", True),
    ]
    for index, (digit, title, agent, planned) in enumerate(panels):
        x, color = 30 + index * 530, AGENT[agent]
        s.rect(x, 80, 480, 620, fill=tint(color, 0.07), stroke=color, width=3, dash=planned)
        s.circle(x + 50, 130, 30, fill=color, stroke=color)
        s.text(x + 50, 142, digit, size=34, weight=750, fill=PAPER, anchor="middle")
        s.text(x + 96, 136, title, size=32, weight=700)
        s.text(x + 96, 166, agent, size=22, weight=700, fill=color)
        if index < 2:
            s.arrow(x + 488, 390, x + 523, 390, color=INK, width=5)

    # 1 — the plan
    x = 30
    s.rect(x + 34, 196, 120, 150, fill=PAPER, stroke=BLUE, width=3, radius=6)
    for row in range(5):
        s.line(x + 50, 222 + row * 24, x + 138, 222 + row * 24, color=LINE, width=4)
    s.text(x + 94, 372, "PDO, 53 pages", size=20, fill=MUTED, anchor="middle")
    s.lines(x + 180, 226, ["Concept: leased jack-up,", "storage vessel", "8 alternatives listed,",
                           "none with numbers"], size=23, gap=1.36)  # fmt: skip
    s.line(x + 34, 404, x + 446, 404, color=LINE)
    s.text(x + 34, 446, "Oil in place", size=24, fill=MUTED)
    s.text(x + 34, 506, f"{p['closure']['mean']:.1f}", size=58, weight=750, fill=BLUE)
    s.text(x + 176, 506, f"({p['closure']['p90']:.1f} – {p['closure']['p10']:.1f})", size=30,
           fill=BLUE)  # fmt: skip
    s.text(x + 34, 544, "million Sm3: mean (low – high)", size=20, fill=MUTED)
    s.line(x + 34, 572, x + 446, 572, color=LINE)
    s.text(x + 34, 612, "Plan against outcome", size=24, fill=MUTED)
    s.lines(x + 34, 650, [f"oil {r['plan_oil']:.1f} → {r['actual_oil']:.1f} million Sm3",
                          f"investment {number(r['investment_plan'])} → "
                          f"{number(r['investment_actual'])} million NOK"], size=22)  # fmt: skip

    # 2 — the reference class
    x = 560
    s.text(x + 34, 214, "Record of the shelf", size=24, fill=MUTED)
    s.text(x + 34, 246, f"{r['class_n']} discoveries: found ÷ prognosed", size=22)
    axis_y, left, right = 336, x + 50, x + 440
    s.line(left, axis_y, right, axis_y, color=INK, width=3)

    def at(value: float) -> float:
        return left + (np.log10(value) + 1.5) / 2.0 * (right - left)

    for tick in (0.1, 1.0):
        s.line(at(tick), axis_y - 10, at(tick), axis_y + 10, color=INK, width=3)
        s.text(at(tick), axis_y + 40, f"{tick:g}", size=22, anchor="middle")
    s.rect(at(r["class_low"]), axis_y - 26, at(r["class_high"]) - at(r["class_low"]), 22,
           fill=tint(ORANGE, 0.35), stroke="none", radius=6)  # fmt: skip
    s.line(at(r["class_ratio"]), axis_y - 36, at(r["class_ratio"]), axis_y - 2, color=ORANGE,
           width=7)  # fmt: skip
    s.text(at(r["class_ratio"]), axis_y - 46, f"median {r['class_ratio']:.2f}", size=22,
           weight=700, fill=ORANGE, anchor="middle")  # fmt: skip
    s.arrow(x + 240, 388, x + 240, 420, color=ORANGE, width=5)
    s.lines(x + 34, 452, ["applied to the part of the estimate", "that is as uncertain as a "
                          "prospect"], size=22)  # fmt: skip
    s.line(x + 34, 498, x + 446, 498, color=LINE)
    s.text(x + 34, 534, "Oil in place, calibrated", size=24, fill=MUTED)
    s.text(x + 34, 592, f"{cal['closure']['p50']:.1f}", size=58, weight=750, fill=ORANGE)
    s.text(x + 176, 592, f"({cal['closure']['p90']:.1f} – {cal['closure']['p10']:.1f})", size=30,
           fill=ORANGE)  # fmt: skip
    s.text(x + 34, 626, "million Sm3: central (low – high)", size=20, fill=MUTED)
    s.text(x + 34, 672, f"below the plan's low case: 10 % → "
           f"{percent(m['Calibrated']['below_pdo_low_in_place'])}", size=22)  # fmt: skip

    # 3 — the decision
    x = 1090
    s.rect(x + 40, 300, 34, 34, fill=PURPLE, stroke=PURPLE, radius=4)
    branches = ((230, ["commit all six wells"]), (400, ["appraise the West,", "then decide"]))
    for y, label in branches:
        s.path(f"M{x + 74} 317 L{x + 150} {y}", color=PURPLE, width=4)
        s.circle(x + 166, y, 16, fill=PAPER, stroke=PURPLE, width=4)
        s.lines(x + 200, y + 8 - 14 * (len(label) - 1), label, size=24, weight=600)
    s.note(x + 200, 272, f"West wells fail to pay {percent(west['pair_does_not_pay'])}",
           color=PURPLE)  # fmt: skip
    s.line(x + 34, 496, x + 446, 496, color=LINE)
    s.text(x + 34, 536, "Result", size=24, fill=MUTED)
    s.lines(x + 34, 578, ["Same concept,", "wells for the West decided later"], size=27,
            weight=650, fill=PURPLE)  # fmt: skip
    s.pill(x + 34, 650, "decision model: planned", color=PURPLE, size=20, dash=True)

    s.line(60, 750, 120, 750, color=INK, width=4)
    s.text(134, 758, "done", size=22, fill=MUTED)
    s.line(260, 750, 320, 750, color=INK, width=4, dash=True)
    s.text(334, 758, "first pass done with the plan's own value figures; full decision analysis "
           "planned", size=22, fill=MUTED)  # fmt: skip
    return s


def flow_chart() -> Svg:
    s = Svg(1600, 760, background=PAPER)

    def step(x, y, rows, agent, planned=False, w=262, h=96):
        color = AGENT[agent]
        s.rect(x, y, w, h, fill=PAPER if planned else tint(color), stroke=color, width=3,
               dash=planned)  # fmt: skip
        top = y + h / 2 + 9 - (len(rows) - 1) * 15
        s.lines(x + w / 2, top, rows, size=23, gap=1.3, anchor="middle", weight=600)

    def source(x, y, rows):
        s.polygon([(x + 24, y), (x + 250, y), (x + 226, y + 96), (x, y + 96)], fill=tint(SLATE),
                  stroke=SLATE, width=3)  # fmt: skip
        s.lines(x + 125, y + 44, rows, size=23, gap=1.3, anchor="middle", weight=600)

    for label, y, agent in (("doc", 70, "doc"), ("rcf", 290, "rcf"), ("dmx", 530, "dmx")):
        s.text(26, y + 58, label, size=34, weight=750, fill=AGENT[agent])
    source(110, 70, ["Development", "plan (PDO)"])
    source(110, 290, ["Public record", "of the shelf"])
    step(410, 70, ["Convert,", "extract facts"], "doc")
    step(722, 70, ["Concept, strategy,", "volume basis"], "doc")
    step(1034, 70, ["Plan against", "outcome"], "doc")
    step(410, 290, ["Build", "reference classes"], "rcf")
    step(722, 290, ["Test them on", "fields held back"], "rcf")
    step(1034, 290, ["Calibrate the basis,", "part by part"], "rcf")
    for x1, x2, y in ((338, 404, 118), (672, 716, 118), (984, 1028, 118), (338, 404, 338),
                      (672, 716, 338), (984, 1028, 338)):  # fmt: skip
        s.arrow(x1, y, x2, y, color=INK, width=5)
    s.path("M853 166 L853 230 L1165 230 L1165 284", color=INK, width=5, arrow=True)
    s.note(1180, 222, "volume basis")

    # decision
    cx, cy = 1165, 578
    s.polygon([(cx, cy - 92), (cx + 190, cy), (cx, cy + 92), (cx - 190, cy)], fill=tint(PURPLE),
              stroke=PURPLE, width=3)  # fmt: skip
    s.lines(cx, cy - 10, ["Enough for", "another concept?"], size=23, gap=1.3, anchor="middle",
            weight=600)  # fmt: skip
    s.arrow(1165, 386, 1165, 480, color=INK, width=5)
    s.arrow(1355, 578, 1392, 578, color=INK, width=5, dash=True)
    s.text(1370, 560, "yes", size=22, fill=MUTED, anchor="middle")
    step(1398, 530, ["Value the", "alternatives"], "dmx", planned=True, w=186)
    s.note(1491, 660, "needs their costs:", anchor="middle", color=MUTED)
    s.note(1491, 686, "not in the data", anchor="middle", color=MUTED)
    s.arrow(975, 578, 938, 578, color=INK, width=5)
    s.text(958, 560, "no", size=22, fill=MUTED, anchor="middle")
    step(670, 530, ["Modify the plan", "within the concept"], "dmx")
    s.arrow(664, 578, 628, 578, color=INK, width=5, dash=True)
    step(360, 530, ["Decision model:", "price, cost, options"], "dmx", planned=True)
    s.arrow(354, 578, 318, 578, color=INK, width=5, dash=True)
    s.rect(110, 530, 202, 96, fill=INK, stroke=INK, radius=48)
    s.lines(211, 570, ["Modified", "concept"], size=23, gap=1.3, anchor="middle", weight=700,
            fill=PAPER)  # fmt: skip

    s.rect(110, 700, 46, 30, fill=tint(SLATE), stroke=SLATE, width=3, radius=6)
    s.text(170, 724, "done", size=22, fill=MUTED)
    s.rect(270, 700, 46, 30, fill=PAPER, stroke=SLATE, width=3, radius=6, dash=True)
    s.text(330, 724, "planned", size=22, fill=MUTED)
    return s


def _field(s: Svg, ox: float, modified: bool, r: dict) -> None:
    """One panel of the concept comparison: facilities, reservoir and wells."""
    p, cal = r["pdo"], r["calibrated"]
    s.rect(ox, 70, 760, 240, fill=SEA, stroke="none", radius=0)
    s.path(f"M{ox} 138 q 19 -12 38 0 t 38 0 t 38 0 t 38 0 t 38 0 t 38 0 t 38 0 t 38 0 t 38 0 "
           "t 38 0 t 38 0 t 38 0 t 38 0 t 38 0 t 38 0 t 38 0 t 38 0 t 38 0 t 38 0 t 38 0",
           color="#38bdf8", width=3)  # fmt: skip
    s.rect(ox, 310, 760, 330, fill="#f1f5f9", stroke="none", radius=0)
    s.line(ox, 310, ox + 760, 310, color="#94a3b8", width=4)
    # jack-up
    for leg in (316, 372, 428):
        s.line(ox + leg, 96, ox + leg, 310, color=INK, width=7)
    s.rect(ox + 296, 104, 152, 30, fill=INK, stroke=INK, radius=4)
    s.polygon([(ox + 352, 104), (ox + 372, 44), (ox + 392, 104)], fill=PAPER, stroke=INK, width=4)
    s.lines(ox + 280, 96, ["leased jack-up:", "process plant + rig"], size=21, anchor="end",
            weight=600)  # fmt: skip
    # storage vessel and gas export
    s.polygon([(ox + 560, 122), (ox + 730, 122), (ox + 708, 152), (ox + 580, 152)], fill=INK,
              stroke=INK)  # fmt: skip
    s.text(ox + 645, 106, "storage vessel", size=21, anchor="middle", weight=600)
    s.path(f"M{ox + 448} 124 C{ox + 490} 190 {ox + 530} 190 {ox + 566} 150", color=ORANGE, width=4)
    s.text(ox + 506, 214, "oil", size=20, fill=ORANGE, anchor="middle")
    s.path(f"M{ox + 300} 300 L{ox + 60} 300", color=GREEN, width=4, arrow=True)
    s.text(ox + 30, 284, "gas to Sleipner A", size=20, fill=GREEN)
    # reservoir: West and East
    crest, base = 468, 610
    west = [(ox + 70, 566), (ox + 300, crest + 18), (ox + 300, base), (ox + 70, base)]
    east = [(ox + 300, crest + 18), (ox + 420, crest), (ox + 700, 572), (ox + 700, base),
            (ox + 300, base)]  # fmt: skip
    s.polygon(east, fill=OIL, stroke=INK, width=3)
    s.polygon(west, fill=tint(ORANGE, 0.16 if modified else 0.5), stroke=INK, width=3,
              dash=modified)  # fmt: skip
    s.text(ox + 500, 578, f"East  {p['east']['mean']:.1f}", size=27, weight=700, anchor="middle")
    west_label = (f"{r['calibrated']['west']['p90']:.1f} – {cal['west']['p10']:.1f}"
                  if modified else f"{p['west']['mean']:.1f}")  # fmt: skip
    s.text(ox + 185, 592, f"West  {west_label}", size=25, weight=700, anchor="middle")
    # wells
    top = (ox + 372, 310)
    committed = [
        ("producer", [(ox + 420, 474)]), ("producer", [(ox + 520, 506)]),
        ("injector", [(ox + 672, 590)]), ("injector", [(ox + 600, 598)]),
    ]  # fmt: skip
    western = [("producer", [(ox + 290, 500), (ox + 150, 548)]), ("injector", [(ox + 96, 596)])]
    colors = {"producer": GREEN, "injector": BLUE}
    for kind, points in committed:
        s.path(f"M{top[0]} {top[1]} L" + " L".join(f"{x} {y}" for x, y in points),
               color=colors[kind], width=5)  # fmt: skip
        s.circle(*points[-1], 7, fill=colors[kind], stroke=colors[kind])
    for kind, points in western:
        color = "#94a3b8" if modified else colors[kind]
        s.path(f"M{top[0]} {top[1]} L" + " L".join(f"{x} {y}" for x, y in points), color=color,
               width=5, dash=modified)  # fmt: skip
        s.circle(*points[-1], 7, fill=color, stroke=color)
    if modified:
        s.path(f"M{top[0]} {top[1]} L{ox + 236} 540", color=ORANGE, width=5)
        s.circle(ox + 236, 540, 9, fill=ORANGE, stroke=ORANGE)
        s.text(ox + 196, 410, "pilot first", size=23, weight=700, fill=ORANGE, anchor="end")
        s.text(ox + 196, 440, "West pair: decide after", size=21, fill=MUTED, anchor="end")


def concept_comparison(r: dict) -> Svg:
    p, west, m = r["pdo"], r["west"], r["metrics"]
    s = Svg(1600, 800, background=PAPER)
    s.text(6, 46, "2005 plan (PDO)", size=36, weight=750, fill=BLUE)
    s.text(846, 46, "Modified plan", size=36, weight=750, fill=ORANGE)
    _field(s, 0, False, r)
    _field(s, 840, True, r)
    s.arrow(770, 360, 830, 360, color=INK, width=6)
    rows = [
        ("Volume the plan stands on", f"{p['closure']['mean']:.1f}  (mean of East + West)",
         f"{p['east']['mean']:.1f}  (East);  West as an option"),
        ("Wells committed", f"{p['producers']} producers, {p['injectors']} injectors",
         "2 producers, 2 injectors; West pair after a pilot"),
        ("Value, million NOK", f"{number(p['npv']['expected_price'])} expected",
         f"{number(west['Calibrated']['east_only'])} from the East; "
         f"{number(west['Calibrated']['staged'])} expected"),
        ("Chance West wells do not pay", percent(west["PDO"]["pair_does_not_pay"], 1),
         percent(west["Calibrated"]["pair_does_not_pay"])),
    ]  # fmt: skip
    for index, (label, before, after) in enumerate(rows):
        y = 674 + index * 30
        s.text(800, y, label, size=20, fill=MUTED, anchor="middle", italic=True)
        s.text(660, y, before, size=22, weight=600, anchor="end")
        s.text(940, y, after, size=22, weight=600, fill=ORANGE)
    s.line(60, 786, 100, 786, color=GREEN, width=5)
    s.text(110, 793, "producer", size=19, fill=MUTED)
    s.line(220, 786, 260, 786, color=BLUE, width=5)
    s.text(270, 793, "injector", size=19, fill=MUTED)
    s.text(1560, 793, "Schematic, not to scale. Which wells drain which area is assumed. Oil in "
           f"place in million Sm3; calibrated closure {m['Calibrated']['in_place_p50']:.1f}.",
           size=19, fill=MUTED, anchor="end")  # fmt: skip
    return s


def changes_slide(deck: Deck, r: dict) -> None:
    """The slide that sets the 2005 plan beside the modified plan, element by element."""
    p, m, w = r["pdo"], r["metrics"], r["west"]
    rows = [
        ("Concept", "Leased jack-up, storage vessel, gas to Sleipner A", "Unchanged"),
        ("Volume basis", f"{p['closure']['mean']:.1f} million Sm3 (mean)",
         f"East {p['east']['mean']:.1f} committed; West "
         f"{r['calibrated']['west']['p90']:.1f}–{r['calibrated']['west']['p10']:.1f} as an option"),
        ("Wells at sanction", "3 producers, 3 injectors", "2 + 2; western pair held back"),
        ("West", "Drilled with the rest", "Pilot first; drill the pair above "
         f"{w['Calibrated']['break_even_west']:.1f} million Sm3"),
        ("Capacity", f"{number(p['capacity_oil'])} Sm3/d", "Unchanged"),
        ("Reserves told to owners", f"{p['reserves']['mean']:.1f}",
         f"about {m['Calibrated']['reserves_p50']:.0f}, low case "
         f"{m['Calibrated']['reserves_p90']:.1f}"),
    ]  # fmt: skip
    body = "".join(f'<tr><td>{a}</td><td>{b}</td><td class="new">{c}</td></tr>' for a, b, c in rows)
    deck.slide(
        "What changes",
        '<table class="big"><thead><tr><th></th><th>2005 plan</th><th>Modified plan</th></tr>'
        f"</thead><tbody>{body}</tbody></table>",
    )


# ---------------------------------------------------------------------------- deck
def build(target_dir: Path) -> Path:
    r = results()
    figures = target_dir / "figs"
    diagrams = {
        "infrastructure": infrastructure(),
        "roles": roles(),
        "agent-setup": agent_setup(),
        "number-travels": number_travels(),
        "use-case": use_case(r),
        "flow-chart": flow_chart(),
        "concept-comparison": concept_comparison(r),
    }
    for name, drawing in diagrams.items():
        drawing.write(figures / f"{name}.svg")
    for name, chart in r["charts"].items():
        chart.svg(figures / f"{name}.svg", scale=1.7, size=(8.4, 6.2))

    m, w = r["metrics"], r["west"]
    deck = Deck("ref-class-concept-select: workflow and first results")
    deck.title_slide(
        "ref-class-concept-select",
        "Reading field-development decisions with the outside view: five agents on the open "
        "Volve data.",
        "Workflow, first use and results · November 2026",
    )
    deck.figure_slide("The workflow", "figs/infrastructure.svg")
    deck.figure_slide("Five agents", "figs/roles.svg")
    deck.figure_slide("How an agent is set up", "figs/agent-setup.svg")
    deck.figure_slide("How a number travels", "figs/number-travels.svg")
    deck.figure_slide("First use", "figs/use-case.svg")
    deck.figure_slide("The steps", "figs/flow-chart.svg")
    deck.pair_slide(
        "Result · the plan against the outcome",
        [
            ("figs/doc-oil.svg", f"Oil <b>{r['plan_oil']:.1f} → {r['actual_oil']:.1f}</b> "
             f"million Sm3; first oil {r['months_late']} months late"),
            ("figs/doc-investment.svg", f"Investments <b>{number(r['investment_plan'])} → "
             f"{number(r['investment_actual'])}</b> million NOK"),
        ],
        lead="doc · agents/doc/out/volve-pdo-vs-actual",
    )  # fmt: skip
    deck.pair_slide(
        "Result · the expert's study, reviewed",
        [
            ("figs/review-probability.svg", "Counted per prospect, the chance of discovery is "
             f"right: <b>{r['expected_discoveries']:.0f} expected, {r['discoveries']} made</b>"),
            ("figs/review-profile.svg", "Counted from first production, the median field has "
             f"produced <b>{r['first_year_monthly']:.2f}</b> of its reserves after a year, not "
             f"{r['first_year_calendar']:.2f}"),
        ],
        lead="rcf · agents/rcf/out/expert-study-review",
    )  # fmt: skip
    deck.pair_slide(
        "Result · the record of the shelf",
        [
            ("figs/study-volume.svg", f"Discoveries hold <b>{r['volume_median']:.2f}</b> of the "
             f"prognosed volume; stated ranges hold {percent(r['range_inside'])}, not 80 %"),
            ("figs/study-volve.svg", "Volve: below the plan's low case in years "
             f"{r['below_low_years'][0]}–{r['below_low_years'][-1]}, <b>inside the class range "
             "every year</b>"),
        ],
        lead="rcf · agents/rcf/out/volve-rcf-study",
    )  # fmt: skip
    deck.pair_slide(
        "Result · a recalibrated volume basis",
        [
            ("figs/dmx-basis.svg", f"Central estimate <b>{m['PDO']['in_place_p50']:.1f} → "
             f"{m['Calibrated']['in_place_p50']:.1f}</b> million Sm3; below the plan's low case "
             f"10 % → {percent(m['Calibrated']['below_pdo_low_in_place'])}"),
            ("figs/dmx-west.svg", "Chance that the West wells do not pay: "
             f"<b>{percent(w['PDO']['pair_does_not_pay'], 1)} → "
             f"{percent(w['Calibrated']['pair_does_not_pay'])}</b>"),
        ],
        lead="dmx · agents/dmx/out/volve-concept-basis",
    )  # fmt: skip
    deck.figure_slide("The 2005 plan and the modified plan", "figs/concept-comparison.svg")
    changes_slide(deck, r)
    deck.slide(
        "Where it stands",
        '<div class="cols">'
        "<div><h3>Done</h3><ul><li>Data layer, rules, checks</li><li>Plan and discovery report "
        "converted and analysed</li><li>Simulation deck runs in OPM Flow</li><li>Reference "
        "classes built and back-tested</li><li>Volume basis recalibrated</li></ul></div>"
        '<div class="started"><h3>Started</h3><ul><li>Modified plan, on the plan\'s own value '
        "figures</li><li>One decision: the wells for the West</li></ul></div>"
        '<div class="next"><h3>Next</h3><ul><li>Decision model with price, cost and options'
        "</li><li>Which wells drain which area</li><li>Cost reference class</li>"
        "<li>Simulation of the modified plan</li></ul></div></div>",
    )
    return deck.write(target_dir / "index.html")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("build",))
    parser.parse_args(argv)
    target = build(repo_root() / OUT)
    print(f"written: {target} ({target.stat().st_size / 1e3:.0f} kB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
