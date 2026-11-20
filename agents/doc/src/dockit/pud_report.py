"""Web report: the Volve development plan of 2005 against the outcome.

    python -m dockit.pud_report build

writes ``agents/doc/out/volve-pdo-vs-actual/index.html`` with its chart
library in ``assets/``. The page needs no network connection. Every number in
it is computed here from ``dockit.pud_data`` and ``dockit.pud_facts``.
"""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
from plotly.offline import get_plotlyjs

from dockit import pud_data, pud_facts
from syskit import public
from syskit.paths import repo_root
from syskit.report import CSS

PLAN, ACTUAL, MUTED = "#1d4ed8", "#c2410c", "#64748b"
BAND = "rgba(29, 78, 216, 0.14)"
OUT = "agents/doc/out/volve-pdo-vs-actual"
YEARS = list(range(2007, 2018))


def integrate_year(years: np.ndarray, values: np.ndarray, year: int) -> float:
    """Volume in one calendar year from a rate per day given over decimal years."""
    grid = np.linspace(year, year + 1, 200)
    rate = np.interp(grid, years, values, left=0.0, right=0.0)
    return float(np.trapezoid(rate, grid) * pud_data.DAYS_PER_YEAR)


def cumulative(per_year: dict[int, float]) -> dict[int, float]:
    total, result = 0.0, {}
    for year in sorted(per_year):
        total += per_year[year]
        result[year] = total
    return result


def figure(title: str, y_title: str, x_title: str = "") -> go.Figure:
    chart = go.Figure()
    chart.update_layout(
        title={"text": title, "font": {"size": 16}, "x": 0, "xanchor": "left"},
        template="plotly_white",
        font={"family": "system-ui, -apple-system, Segoe UI, Roboto, sans-serif", "size": 13},
        margin={"l": 64, "r": 24, "t": 48, "b": 110},
        height=460,
        legend={"orientation": "h", "y": -0.16, "yanchor": "top", "x": 0, "xanchor": "left"},
        hovermode="x unified",
        xaxis={"title": x_title},
        yaxis={"title": y_title, "rangemode": "tozero"},
        bargap=0.25,
    )
    return chart


def chart_html(chart: go.Figure, name: str) -> str:
    config = {"displaylogo": False, "responsive": True, "modeBarButtonsToRemove": ["lasso2d"]}
    # The prefix keeps chart ids apart from the ids of the page sections.
    div = f"chart-{name}"
    return chart.to_html(full_html=False, include_plotlyjs=False, div_id=div, config=config)


def build_charts(result: pud_data.Outcome) -> dict[str, str]:
    profiles = pud_data.plan_profiles()
    charts = {}

    # Oil per calendar year
    chart = figure("Oil production per calendar year", "million Sm3 per year")
    chart.add_trace(
        go.Scatter(
            x=YEARS,
            y=[profiles["P10"].get(y) for y in YEARS],
            mode="lines",
            line={"width": 0},
            showlegend=False,
            hoverinfo="skip",
        )
    )
    chart.add_trace(
        go.Scatter(
            x=YEARS,
            y=[profiles["P90"].get(y) for y in YEARS],
            mode="lines",
            line={"width": 0},
            fill="tonexty",
            fillcolor=BAND,
            name="Plan, P90 to P10 before cut-off (Figure 4.5)",
            hoverinfo="skip",
        )
    )
    chart.add_trace(
        go.Scatter(
            x=YEARS,
            y=[profiles["mean"].get(y) for y in YEARS],
            mode="lines",
            line={"color": PLAN, "dash": "dot", "width": 1.5},
            name="Plan, mean before cut-off (Figure 4.5)",
        )
    )
    stated = pud_facts.OIL_PER_YEAR["mean"]
    chart.add_trace(
        go.Scatter(
            x=list(stated),
            y=list(stated.values()),
            mode="lines+markers",
            line={"color": PLAN, "width": 2.5},
            marker={"size": 8},
            name="Plan, mean to economic cut-off (Table 4.5)",
        )
    )
    chart.add_trace(
        go.Bar(
            x=list(result.oil_per_year),
            y=list(result.oil_per_year.values()),
            marker={"color": ACTUAL},
            opacity=0.85,
            name="Outcome (Sodir)",
        )
    )
    chart.update_xaxes(dtick=1)
    charts["oil_year"] = chart_html(chart, "oil_year")

    # Oil rate from first oil
    years, rate = pud_data.plan_series("Volve_PUD_cmt_p023_fig4-2_oil-rate.csv")
    start = pud_data.decimal_year(pud_data.PLAN_FIRST_OIL)
    chart = figure("Oil rate counted from first oil", "Sm3 per day", "months since first oil")
    chart.add_trace(
        go.Scatter(
            x=(years - start) * 12,
            y=rate,
            mode="lines",
            line={"color": PLAN, "width": 2.5},
            name="Plan, mean (Figure 4.2, digitised)",
        )
    )
    actual = pud_data.monthly_rates(result)
    chart.add_trace(
        go.Scatter(
            x=[m for m, _ in actual],
            y=[r for _, r in actual],
            mode="lines+markers",
            line={"color": ACTUAL, "width": 2},
            marker={"size": 4},
            name="Outcome, monthly average (Sodir)",
        )
    )
    minimum = pud_facts.ASSUMPTIONS["minimum_economic_oil_rate"][0]
    chart.add_hline(
        y=minimum,
        line={"color": MUTED, "dash": "dash", "width": 1},
        annotation_text=f"Plan's minimum economic rate, {minimum} Sm3/d",
        annotation_position="top right",
        annotation_bgcolor="rgba(255, 255, 255, 0.85)",
    )
    chart.update_xaxes(dtick=12, range=[0, 110])
    charts["oil_rate"] = chart_html(chart, "oil_rate")

    # Cumulative oil
    chart = figure("Cumulative oil production", "million Sm3")
    for case, dash in (("P10", "dot"), ("mean", "solid"), ("P90", "dot")):
        total = cumulative(pud_facts.OIL_PER_YEAR[case])
        chart.add_trace(
            go.Scatter(
                x=list(total),
                y=list(total.values()),
                mode="lines+markers",
                line={"color": PLAN, "dash": dash, "width": 2},
                marker={"size": 6},
                name=f"Plan, {case} (Table 4.5)",
            )
        )
    total = cumulative(result.oil_per_year)
    chart.add_trace(
        go.Scatter(
            x=list(total),
            y=list(total.values()),
            mode="lines+markers",
            line={"color": ACTUAL, "width": 2.5},
            marker={"size": 7},
            name="Outcome (Sodir)",
        )
    )
    chart.update_xaxes(dtick=1, range=[2006.5, 2016.5])
    charts["oil_cumulative"] = chart_html(chart, "oil_cumulative")

    # Estimate of recoverable oil over time
    estimate = {y: v for y, v in result.recoverable_estimate.items() if 2005 <= y <= 2016}
    chart = figure("Estimate of recoverable oil at each year-end", "million Sm3")
    chart.add_hrect(
        y0=pud_facts.RESERVES["P90"],
        y1=pud_facts.RESERVES["P10"],
        fillcolor=BAND,
        line_width=0,
        annotation_text="Plan, P90 to P10",
        annotation_position="top left",
    )
    chart.add_hline(
        y=pud_facts.RESERVES["mean"],
        line={"color": PLAN, "width": 2},
        annotation_text="Plan, mean 11.40",
        annotation_position="bottom left",
    )
    chart.add_trace(
        go.Scatter(
            x=list(estimate),
            y=list(estimate.values()),
            mode="lines+markers",
            line={"color": ACTUAL, "width": 2.5},
            marker={"size": 7},
            name="Sodir estimate of recoverable oil",
        )
    )
    chart.add_trace(
        go.Scatter(
            x=list(total),
            y=list(total.values()),
            mode="lines",
            line={"color": MUTED, "width": 1.5},
            fill="tozeroy",
            fillcolor="rgba(100, 116, 139, 0.12)",
            name="Produced to date",
        )
    )
    chart.update_xaxes(dtick=1)
    charts["estimate"] = chart_html(chart, "estimate")

    # Water
    chart = figure("Water injected and water produced per year", "million Sm3 per year")
    series = (
        ("Volve_PUD_cmt_p024_fig4-3_water-injection-rate.csv", "injection", "Water injected"),
        ("Volve_PUD_cmt_p024_fig4-3_produced-water-rate.csv", "water", "Water produced"),
    )
    for (name, key, label), dash in zip(series, ("solid", "dot"), strict=True):
        ys, values = pud_data.plan_series(name)
        plan = {y: integrate_year(ys, values, y) / 1e6 for y in range(2007, 2017)}
        chart.add_trace(
            go.Scatter(
                x=list(plan),
                y=list(plan.values()),
                mode="lines+markers",
                line={"color": PLAN, "dash": dash, "width": 2},
                name=f"Plan: {label.lower()} (Figure 4.3, digitised)",
            )
        )
        book = {y: v[key] for y, v in result.workbook_per_year.items() if y >= 2007}
        chart.add_trace(
            go.Scatter(
                x=list(book),
                y=list(book.values()),
                mode="lines+markers",
                line={"color": ACTUAL, "dash": dash, "width": 2},
                name=f"Outcome: {label.lower()} (production workbook)",
            )
        )
    chart.update_xaxes(dtick=1)
    charts["water"] = chart_html(chart, "water")

    # Gas
    ys, values = pud_data.plan_series("Volve_PUD_cmt_p024_fig4-4_gas-rate.csv")
    plan = {y: integrate_year(ys, values, y) for y in range(2007, 2017)}
    chart = figure("Gas per year", "million Sm3 per year")
    chart.add_trace(
        go.Bar(
            x=list(plan),
            y=list(plan.values()),
            marker={"color": PLAN},
            name="Plan: rich gas produced (Figure 4.4, digitised)",
        )
    )
    dry = {y: v[0] for y, v in pud_facts.GAS_PRODUCTS.items()}
    chart.add_trace(
        go.Scatter(
            x=list(dry),
            y=list(dry.values()),
            mode="lines+markers",
            line={"color": PLAN, "dash": "dot"},
            name="Plan: dry gas sold (Table 4.6)",
        )
    )
    gross = {y: v["gas"] for y, v in result.workbook_per_year.items() if y >= 2008}
    chart.add_trace(
        go.Bar(
            x=list(gross),
            y=list(gross.values()),
            marker={"color": ACTUAL},
            opacity=0.85,
            name="Outcome: gas produced (production workbook)",
        )
    )
    sold = {y: v * 1000 for y, v in result.gas_sales_per_year.items()}
    chart.add_trace(
        go.Scatter(
            x=list(sold),
            y=list(sold.values()),
            mode="lines+markers",
            line={"color": ACTUAL, "dash": "dot"},
            name="Outcome: gas sold (Sodir)",
        )
    )
    chart.update_xaxes(dtick=1)
    charts["gas"] = chart_html(chart, "gas")

    # Investments
    plan = pud_data.plan_investments()
    spent = {y: v for y, v in result.investments.items() if y <= 2016}
    chart = figure("Investments per year, nominal", "million NOK")
    chart.add_trace(
        go.Bar(
            x=list(plan), y=list(plan.values()), marker={"color": PLAN}, name="Plan (Table 12.6)"
        )
    )
    chart.add_trace(
        go.Bar(
            x=list(spent),
            y=list(spent.values()),
            marker={"color": ACTUAL},
            opacity=0.85,
            name="Outcome (Sodir)",
        )
    )
    for values, colour, label in (
        (plan, PLAN, "Plan, cumulative"),
        (spent, ACTUAL, "Outcome, cumulative"),
    ):
        total = cumulative(values)
        chart.add_trace(
            go.Scatter(
                x=list(total),
                y=list(total.values()),
                mode="lines",
                line={"color": colour, "dash": "dot", "width": 2},
                name=label,
                yaxis="y2",
            )
        )
    chart.update_layout(
        yaxis2={
            "title": "cumulative, million NOK",
            "overlaying": "y",
            "side": "right",
            "rangemode": "tozero",
            "showgrid": False,
            "range": [0, 5000],
            "dtick": 1000,
        },
        yaxis={"range": [0, 1250], "dtick": 250},
        margin={"r": 70, "b": 130},
    )
    chart.update_xaxes(dtick=1)
    charts["investments"] = chart_html(chart, "investments")

    # Oil price
    brent = {y: v for y, v in public.read_series("fred_brent").items() if 2005 <= y <= 2016}
    chart = figure("Oil price: the plan's assumptions and what followed", "USD per barrel, Brent")
    chart.add_trace(
        go.Bar(
            x=list(brent),
            y=list(brent.values()),
            marker={"color": ACTUAL},
            opacity=0.85,
            name="Annual average (FRED)",
        )
    )
    prices = (
        ("oil_price_brent_forward", "Plan, forward price path", "dot"),
        ("oil_price_brent_expected", "Plan, expected price", "solid"),
        ("oil_price_brent_low", "Plan, low price path", "dash"),
    )
    for key, label, dash in prices:
        value = pud_facts.ASSUMPTIONS[key][0]
        chart.add_trace(
            go.Scatter(
                x=[2004.5, 2016.5],
                y=[value, value],
                mode="lines",
                line={"color": PLAN, "dash": dash, "width": 2},
                name=f"{label}, {value}",
            )
        )
    chart.update_xaxes(dtick=1, range=[2004.5, 2016.5])
    charts["price"] = chart_html(chart, "price")

    # Oil in place
    chart = figure("Estimates of oil originally in place", "", "million Sm3")
    rows = (
        ("Discovery report, 1993<br>(Theta Vest)", 7.22, 10.33, 12.83, MUTED),
        (
            "Development plan, 2005<br>(Volve closure)",
            pud_facts.STOOIP["P90"],
            pud_facts.STOOIP["mean"],
            pud_facts.STOOIP["P10"],
            PLAN,
        ),
    )
    for label, low, mean, high, colour in rows:
        chart.add_trace(
            go.Scatter(
                x=[low, high],
                y=[label, label],
                mode="lines",
                line={"color": colour, "width": 10},
                opacity=0.35,
                showlegend=False,
                hoverinfo="skip",
            )
        )
        chart.add_trace(
            go.Scatter(
                x=[low, mean, high],
                y=[label] * 3,
                mode="markers+text",
                marker={"color": colour, "size": 11},
                text=[f"P90 {low}", f"mean {mean}", f"P10 {high}"],
                textposition=["bottom center", "top center", "bottom center"],
                showlegend=False,
            )
        )
    points = (
        ("Geological model, 2010;<br>Sodir, 2013 to today", result.in_place),
        ("Simulation model, 2016", 21.97),
    )
    for label, value in points:
        chart.add_trace(
            go.Scatter(
                x=[value],
                y=[label],
                mode="markers+text",
                marker={"color": ACTUAL, "size": 13, "symbol": "diamond"},
                text=[f"{value:.2f}"],
                textposition="top center",
                showlegend=False,
            )
        )
    chart.update_layout(hovermode="closest", height=360, margin={"l": 190, "b": 56})
    chart.update_xaxes(range=[0, 40])
    chart.update_yaxes(autorange="reversed", rangemode="normal")
    charts["in_place"] = chart_html(chart, "in_place")
    return charts


def key_figures(result: pud_data.Outcome) -> dict[str, float]:
    """The numbers quoted in the text, computed once."""
    years, rate = pud_data.plan_series("Volve_PUD_cmt_p023_fig4-2_oil-rate.csv")
    spent = {y: v for y, v in result.investments.items() if y <= 2016}
    real = pud_data.deflate(spent)
    plan_real = pud_data.deflate(pud_data.plan_investments())
    oil = sum(result.oil_per_year.values())
    months = pud_facts.ASSUMPTIONS["economic_production_period"][0]
    injection_plan = pud_data.plan_series("Volve_PUD_cmt_p024_fig4-3_water-injection-rate.csv")
    return {
        "oil": oil,
        "oil_plan": pud_facts.RESERVES["mean"],
        "oil_diff": 100 * (oil / pud_facts.RESERVES["mean"] - 1),
        "delay": pud_data.months_between(pud_data.PLAN_FIRST_OIL, result.first_oil),
        "life": pud_data.months_between(result.first_oil, result.last_oil),
        "life_plan": months,
        "plan36": pud_data.plan_volume(years, rate, 36),
        "actual36": pud_data.actual_volume(result, 36),
        "plan60": pud_data.plan_volume(years, rate, 60),
        "actual60": pud_data.actual_volume(result, 60),
        "after_plan_life": oil - pud_data.actual_volume(result, months),
        "peak_plan": max(pud_facts.OIL_PER_YEAR["mean"].values()),
        "peak": max(result.oil_per_year.values()),
        "peak_year": max(result.oil_per_year, key=result.oil_per_year.get),
        "peak_month_rate": max(r for _, r in pud_data.monthly_rates(result)),
        "inv_plan": sum(pud_data.plan_investments().values()),
        "inv_plan_2005": pud_facts.INVESTMENTS_2005["total"],
        "inv_plan_real": sum(plan_real.values()),
        "inv": sum(spent.values()),
        "inv_first": sum(v for y, v in spent.items() if y <= 2009),
        "inv_second": sum(v for y, v in spent.items() if 2012 <= y <= 2014),
        "inv_real": sum(real.values()),
        "inv_first_real": sum(v for y, v in real.items() if y <= 2009),
        "in_place": result.in_place,
        "in_place_plan": pud_facts.STOOIP["mean"],
        "recovery": 100 * oil / result.in_place,
        "recovery_plan": 100 * pud_facts.RESERVES["mean"] / pud_facts.STOOIP["mean"],
        "gas_plan": pud_facts.ASSUMPTIONS["rich_gas_cumulative"][0],
        "gas": sum(v["gas"] for v in result.workbook_per_year.values()) / 1000,
        "gas_sold": sum(result.gas_sales_per_year.values()),
        "gas_sold_plan": pud_facts.GAS_PRODUCTS_TOTAL[0] / 1000,
        "injected": sum(v["injection"] for v in result.workbook_per_year.values()),
        "injected_to_2012": sum(
            v["injection"] for y, v in result.workbook_per_year.items() if y <= 2012
        ),
        "injected_plan": sum(integrate_year(*injection_plan, y) for y in range(2007, 2013)) / 1e6,
        "water": sum(v["water"] for v in result.workbook_per_year.values()),
    }


def table(headers: list[str], rows: list[list], *, left: tuple[int, ...] = (0,)) -> str:
    """An HTML table; the columns listed in ``left`` hold text and are left-aligned."""

    def cell(value, tag: str, index: int) -> str:
        side = "l" if index in left else "r"
        text = value if isinstance(value, str) else f"{value:,.2f}".replace(",", " ")
        return f'<{tag} class="{side}">{text}</{tag}>'

    head = "".join(cell(h, "th", i) for i, h in enumerate(headers))
    body = "".join(
        "<tr>" + "".join(cell(v, "td", i) for i, v in enumerate(row)) + "</tr>" for row in rows
    )
    return (
        f'<div class="scroll"><table><thead><tr>{head}</tr></thead>'
        f"<tbody>{body}</tbody></table></div>"
    )


def number(value: float, digits: int = 0) -> str:
    return f"{value:,.{digits}f}".replace(",", " ")


def signed(value: float, digits: int = 0) -> str:
    return f"{value:+,.{digits}f}".replace(",", " ").replace("-", "−")


def build_tables(result: pud_data.Outcome, k: dict[str, float]) -> dict[str, str]:
    tables = {}
    stated = pud_facts.OIL_PER_YEAR
    rows = []
    for year in range(2007, 2017):
        plan = [stated[c].get(year) for c in ("mean", "P90", "P10")]
        actual = result.oil_per_year.get(year)
        difference = (
            signed(actual - plan[0], 2) if actual is not None and plan[0] is not None else "–"
        )
        cells = [number(v, 2) if v is not None else "–" for v in (*plan, actual)]
        rows.append([str(year), *cells, difference])
    totals = [pud_facts.RESERVES[c] for c in ("mean", "P90", "P10")]
    rows.append(
        ["Total", *(number(v, 2) for v in (*totals, k["oil"])), signed(k["oil"] - totals[0], 2)]
    )
    tables["oil"] = table(
        ["Year", "Plan, mean", "Plan, P90", "Plan, P10", "Outcome", "Outcome minus plan mean"],
        rows,
    )

    plan = pud_data.plan_investments()
    spent = {y: v for y, v in result.investments.items() if y <= 2016}
    real = pud_data.deflate(spent)
    rows = [
        [str(y), number(plan[y]) if y in plan else "–", number(spent.get(y, 0)), number(real[y])]
        for y in range(2005, 2017)
    ]
    rows.append(["Total", number(k["inv_plan"]), number(k["inv"]), number(k["inv_real"])])
    tables["investments"] = table(
        ["Year", "Plan, nominal", "Outcome, nominal", "Outcome in 2005 money (CPI)"], rows
    )

    labels = {
        "wells": "Wells (drilling and completion)",
        "mobilisation_subsea_project_management": (
            "Mobilisation, subsea equipment, project management"
        ),
        "unforeseen": "Unforeseen costs",
        "total_investments": "<b>Total investments</b>",
        "lease_investment_element_and_tariff": (
            "Lease of platform and storage vessel: capital element and process tariff"
        ),
        "lease_operation_and_maintenance": (
            "Lease of platform and storage vessel: operation and maintenance"
        ),
        "operator_operating_costs": "Operator's operating costs and onshore support",
        "decommissioning": "Decommissioning",
        "plugging_of_wells": "Plugging of wells",
        "total_operating_costs": "<b>Total operating costs</b>",
        "total_costs": "<b>Total costs, 2005 to May 2012</b>",
    }
    rows = [
        [
            labels[key],
            number(total),
            f"{100 * total / pud_facts.COSTS_NOMINAL['total_costs'][1]:.0f} %",
        ]
        for key, (_, total) in pud_facts.COSTS_NOMINAL.items()
    ]
    tables["plan_costs"] = table(["Cost item in the plan", "Million NOK nominal", "Share"], rows)

    wells = pud_data.well_counts(result)
    planned = {
        "oil producers": pud_facts.ASSUMPTIONS["oil_producers_planned"][0],
        "water injectors": pud_facts.ASSUMPTIONS["water_injectors_planned"][0],
        "water producers (Utsira)": pud_facts.ASSUMPTIONS["utsira_water_producers_planned"][0],
        "observation and pilot wellbores": 0,
    }
    rows = [
        [name[0].upper() + name[1:], str(planned[name]), str(len(drilled)), ", ".join(drilled)]
        for name, drilled in wells.items()
    ]
    tables["wells"] = table(
        ["Kind", "Planned", "Drilled", "Wellbores (year drilling began)"], rows, left=(0, 3)
    )
    return tables


def card(label: str, plan: str, actual: str, note: str) -> str:
    return (
        f'<div class="card"><div class="label">{label}</div><div class="pair">'
        f'<span class="plan">{plan}</span><span class="arrow">→</span>'
        f'<span class="actual">{actual}</span></div><div class="note">{note}</div></div>'
    )


def fig(chart: str, caption: str) -> str:
    return f"<figure>{chart}<figcaption>{caption}</figcaption></figure>"


def page(result: pud_data.Outcome) -> str:
    k = key_figures(result)
    charts = build_charts(result)
    tables = build_tables(result, k)
    first, last = result.first_oil, result.last_oil
    cards = "".join(
        (
            card(
                "Oil recovered, million Sm3",
                f"{k['oil_plan']:.2f}",
                f"{k['oil']:.2f}",
                f"{signed(k['oil_diff'])} % against the plan's mean; between its P90 (9.0) "
                "and P50 (11.35)",
            ),
            card(
                "First oil",
                "6 March 2007",
                f"{first:%-d %B %Y}",
                f"{k['delay']:.0f} months later than planned",
            ),
            card(
                "Producing life, months",
                f"{k['life_plan']:.0f}",
                f"{k['life']:.0f}",
                f"last oil {last:%-d %B %Y}; the plan stopped in May 2012",
            ),
            card(
                "Oil in the first 36 months, million Sm3",
                f"{k['plan36']:.1f}",
                f"{k['actual36']:.1f}",
                f"{signed(100 * (k['actual36'] / k['plan36'] - 1))} %; counted from first oil",
            ),
            card(
                "Investments, million NOK nominal",
                number(k["inv_plan"]),
                number(k["inv"]),
                f"{number(k['inv_first'])} by 2009; {number(k['inv_second'])} more in 2012–2014",
            ),
            card(
                "Oil in place, million Sm3",
                f"{k['in_place_plan']:.1f}",
                f"{k['in_place']:.1f}",
                "below the plan's P90 of 20.9",
            ),
        )
    )
    generated = dt.date.today().isoformat()
    body = f"""
<header class="top"><div class="wrap">
<h1>Volve: the 2005 development plan against the outcome</h1>
<p>What the plan for development and operation forecast for production and cost, and what
public records show happened between first oil in {first:%Y} and shut-down in {last:%Y}.</p>
</div></header>
<nav><div class="wrap">
<a href="#glance">At a glance</a><a href="#oil">Oil</a><a href="#estimate">Estimates</a>
<a href="#water-gas">Water and gas</a><a href="#cost">Cost</a><a href="#wells">Wells</a>
<a href="#context">Context</a><a href="#limits">Limits</a><a href="#sources">Sources</a>
</div></nav>
<main>

<section id="glance">
<h2>At a glance</h2>
<p class="lead">The field recovered {abs(k["oil_diff"]):.0f} % less oil than the plan's mean,
started {k["delay"]:.0f} months late, and produced for {k["life"]:.0f} months instead of
{k["life_plan"]:.0f}. Reaching that recovery took more than twice the planned investment.</p>
<div class="legend-key"><span class="p">Plan (PDO, February 2005)</span>
<span class="a">Outcome</span></div>
<div class="cards">{cards}</div>
<p>The plan's percentiles follow the Norwegian convention: P90 is the low case (a 90 % chance of
exceeding it) and P10 the high case.</p>
</section>

<section id="oil">
<h2>Oil production</h2>
<p class="lead">The plan expected a year of build-up, {pud_facts.ASSUMPTIONS["plateau_duration"][0]}
months at a plateau of {
        number(pud_facts.ASSUMPTIONS["plateau_oil_rate"][0])
    } Sm3/d, and a decline to
the economic limit in May 2012.</p>
{
        fig(
            charts["oil_year"],
            "Plan and outcome by calendar year. The band and the dotted line are the "
            "plan's profiles before its economic cut-off, read from Figure 4.5; the solid line is "
            "Table 4.5, which stops at the cut-off.",
        )
    }
<ul>
<li><b>Later.</b> First oil came on {first:%-d %B %Y}, not 6 March 2007. The plan itself warned
that weather during tow-out could delay the start.</li>
<li><b>Lower early on.</b> The best calendar year gave {k["peak"]:.2f} million Sm3
({k["peak_year"]}) against {k["peak_plan"]:.2f} planned. The highest monthly average was
{number(k["peak_month_rate"])} Sm3/d, close to the plateau rate, but it was not sustained.</li>
<li><b>Longer.</b> {k["after_plan_life"]:.1f} million Sm3 was produced after month
{k["life_plan"]:.0f} of production, the point at which the plan expected to stop.</li>
</ul>
{
        fig(
            charts["oil_rate"],
            "The same comparison with both curves starting at first oil, which removes "
            "the late start. The plan curve is digitised from Figure 4.2 and has a resolution of "
            "about 60 Sm3/d.",
        )
    }
<div class="callout">Counted from first oil, production was {k["actual36"]:.1f} million Sm3 in
the first 36 months against {k["plan36"]:.1f} planned
({signed(100 * (k["actual36"] / k["plan36"] - 1))} %), and {k["actual60"]:.1f} against
{k["plan60"]:.1f} in the first 60 months
({signed(100 * (k["actual60"] / k["plan60"] - 1))} %).</div>
{
        fig(
            charts["oil_cumulative"],
            "Cumulative oil. Each plan case ends where Table 4.5 ends it: "
            "9.00 (P90), 11.40 (mean) and 15.31 (P10) million Sm3.",
        )
    }
<details><summary>Oil per year, million Sm3</summary>{tables["oil"]}
<p>Plan: Table 4.5 of the PDO; 2007 is from March. Outcome: Sodir, net oil.</p></details>
</section>

<section id="estimate">
<h2>How the estimate of recoverable oil moved</h2>
<p class="lead">Sodir publishes an estimate of recoverable oil for every field at each
year-end. For Volve it rose before first oil, fell below the plan's low case after two years of
production, and recovered after the second drilling campaign.</p>
{
        fig(
            charts["estimate"],
            "Sodir's estimate of recoverable oil against the plan's range. The "
            "estimate was 8.15 million Sm3 at the end of 2010, below the plan's P90 of 9.0.",
        )
    }
</section>

<section id="water-gas">
<h2>Water and gas</h2>
<p class="lead">The plan relied on water injection to hold the reservoir pressure above the
bubble point, so that all gas would come out of solution at the surface, not in the
reservoir.</p>
{
        fig(
            charts["water"],
            "Water volumes per year. Plan values are integrated from the rates "
            "digitised from Figure 4.3; the document has no table of them. The figure runs "
            "to 2017, beyond the plan's own economic cut-off in 2012.",
        )
    }
<p>Over the field's life {k["injected"]:.1f} million Sm3 of water was injected and
{k["water"]:.1f} million Sm3 produced. In the plan's producing years, 2007 to 2012, the
digitised plan curve amounts to {k["injected_plan"]:.1f} million Sm3 injected; the outcome for
2008 to 2012 was {k["injected_to_2012"]:.1f}.</p>
{
        fig(
            charts["gas"],
            "Gas per year. The plan's rich gas is integrated from the rate digitised "
            "from Figure 4.4; dry gas sold is Table 4.6.",
        )
    }
<p>Gas produced was {k["gas"]:.2f} billion Sm3 against {k["gas_plan"]:.1f} planned. Gas sold was
{k["gas_sold"]:.2f} billion Sm3 against {k["gas_sold_plan"]:.2f} planned as dry gas; the two
sales figures may not be defined alike.</p>
</section>

<section id="cost">
<h2>Cost</h2>
<p class="lead">Only investments can be compared: Sodir publishes investments per field and
year, and no operating or lease costs. In the plan, investments were about a quarter of the
total cost, because the platform and the storage vessel were leased.</p>
{
        fig(
            charts["investments"],
            "Investments per year in nominal money. The plan's investments end "
            "in 2008; the outcome has a second period of spending in 2012 to 2014.",
        )
    }
<ul>
<li><b>Initial development.</b> {number(k["inv_first"])} million NOK was invested from 2005 to
2009 against {number(k["inv_plan"])} planned
({signed(100 * (k["inv_first"] / k["inv_plan"] - 1))} %).</li>
<li><b>Second campaign.</b> A further {number(k["inv_second"])} million NOK was invested in 2012
to 2014, when new wells were drilled. The plan contained no such campaign; it listed new wells
as a possible way to increase recovery.</li>
<li><b>In 2005 money.</b> Deflated with the consumer price index, the outcome is
{number(k["inv_real"])} million NOK against {number(k["inv_plan_2005"])} in the plan
({signed(100 * (k["inv_real"] / k["inv_plan_2005"] - 1))} %). The index is a general one, not a
cost index for the oil industry, so this is indicative.</li>
</ul>
<details><summary>Investments per year, million NOK</summary>{tables["investments"]}
<p>Plan: Table 12.6 of the PDO. Outcome: Sodir. Deflator: Statistics Norway, consumer price
index.</p></details>
<h3>What the plan expected to spend in total</h3>
{tables["plan_costs"]}
<p>Source: Table 12.6 of the PDO, nominal money, covering 2005 to May 2012. The plan gives total
investments as {number(k["inv_plan_2005"])} million NOK in 2005 money (Table 12.1) and
{number(k["inv_plan"])} in nominal money.</p>
</section>

<section id="wells">
<h2>Wells</h2>
<p class="lead">The platform could take 13 wells. The plan used eight of the slots.</p>
{tables["wells"]}
<p>Source for drilled wellbores: Sodir, development wellbores for Volve. Three producers, two
injectors and the water wells were drilled from 2007 to 2009; three more producers and one
injector followed in 2013 and 2014.</p>
</section>

<section id="context">
<h2>Context</h2>
<h3>Oil price</h3>
<p>The plan's economic limit, and with it the field's planned life, was set by an expected Brent
price of {pud_facts.ASSUMPTIONS["oil_price_brent_expected"][0]} USD per barrel. Its break-even
price was {pud_facts.ASSUMPTIONS["break_even_price_brent"][0]:.2f} USD per barrel.</p>
{
        fig(
            charts["price"],
            "Annual average Brent price against the three price paths in the plan. "
            "The plan's prices are in 2004 money or nominal, as stated in its Table 12.7.",
        )
    }
<h3>Oil in place</h3>
<p>The volume the plan was built on was later revised down by about a third. The recovery
factor moved the other way: {k["recovery_plan"]:.0f} % in the plan's mean case,
{k["recovery"]:.0f} % in Sodir's final figures.</p>
{
        fig(
            charts["in_place"],
            "Estimates of oil originally in place. The discovery report covers the "
            "Theta Vest structure as mapped in 1993; whether the later estimates cover exactly the "
            "same area has not been established.",
        )
    }
</section>

<section id="limits">
<h2>What this comparison does not show</h2>
<ul>
<li><b>Operating and lease costs.</b> No public source for the actual figures was found, so
about three quarters of the planned cost has no counterpart here.</li>
<li><b>Like-for-like investments.</b> It is not established that Sodir's investment figures
cover the same items as the plan's. The plan treats the capital element of the leases as an
operating cost.</li>
<li><b>Causes.</b> The comparison shows what differed, not why. The reasons for the lower early
production are not taken from any document read for this report.</li>
<li><b>Precision of the plan curves.</b> Rates for oil, water and gas are digitised from small
pictures in the PDO. Annual oil is checked against the plan's Table 4.5 and agrees within about
1 %, except 2010 (5 %).</li>
<li><b>Two production records.</b> Sodir gives {k["oil"]:.2f} million Sm3 of oil; the released
production workbook sums to
{sum(v["oil"] for v in result.workbook_per_year.values()):.2f}. The difference is not
explained.</li>
</ul>
</section>

<section id="sources">
<h2>Sources and method</h2>
{
        table(
            ["What", "Source", "How it was obtained"],
            left=(0, 1, 2),
            rows=[
                [
                    "Plan: reserves, annual oil, costs, assumptions",
                    "PDO for Volve, February 2005: Tables 4.3, 4.5, 4.6, 12.1, 12.6, 12.7",
                    "Read from the text of the PDF; in the fact register "
                    "<code>data/facts/pud2005.csv</code>",
                ],
                [
                    "Plan: rates of oil, water and gas; profiles before cut-off",
                    "PDO Figures 4.2 to 4.5",
                    "Digitised; data in <code>data/volve/reports/md/Volve_PUD_cmt.xlsx</code>",
                ],
                [
                    "Outcome: oil, gas sold, investments, estimates, wellbores",
                    f"Sodir FactPages, snapshot {result.snapshot}",
                    "Downloaded tables in <code>data/sodir/</code>",
                ],
                [
                    "Outcome: water, injection, gas produced, first and last oil",
                    "Volve production data workbook (Equinor Volve data release)",
                    "Summed per year",
                ],
                [
                    "Brent price",
                    "FRED series DCOILBRENTEU, annual average",
                    "Snapshot in <code>data/public/</code>",
                ],
                [
                    "Consumer price index",
                    "Statistics Norway, table 03014",
                    "Snapshot in <code>data/public/</code>",
                ],
                [
                    "Oil in place, 1993",
                    "Discovery evaluation report, well 15/9-19 SR, Table 10.1",
                    "Read from the scanned page and checked against it",
                ],
            ],
        )
    }
<footer>Generated {generated} by <code>python -m dockit.pud_report build</code>. Volve data:
Equinor ASA and the former Volve licence partners. Field statistics: Norwegian Offshore
Directorate (Sodir).</footer>
</section>
</main>
"""
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Volve: the 2005 development plan against the outcome</title>"
        f'<style>{CSS}</style><script src="assets/plotly.min.js"></script></head>'
        f"<body>{body}</body></html>"
    )


def build(target_dir: Path) -> Path:
    (target_dir / "assets").mkdir(parents=True, exist_ok=True)
    (target_dir / "assets" / "plotly.min.js").write_text(get_plotlyjs(), encoding="utf-8")
    target = target_dir / "index.html"
    target.write_text(page(pud_data.outcome()), encoding="utf-8")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("build",))
    parser.parse_args(argv)
    target = build(repo_root() / OUT)
    print(f"written: {target} ({target.stat().st_size / 1e3:.0f} kB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
