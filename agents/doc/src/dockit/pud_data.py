"""Plan and outcome data for the Volve PDO comparison.

The plan comes from the PDO (``dockit.pud_facts`` and the digitised plot data);
the outcome from the Sodir snapshot, the production workbook and the public
price series. Everything is returned in plain structures so that the report
and the analysis use the same numbers.
"""

from __future__ import annotations

import csv
import datetime as dt
from dataclasses import dataclass

import numpy as np

from dockit import pud_facts
from syskit import public, sodir
from syskit.paths import data_dir, volve_data

FIELD = "VOLVE"
PLAN_FIRST_OIL = dt.date(2007, 3, 6)  # "Produksjons start 06.03.2007", Figure 12.1 and Table 4.6
DAYS_PER_YEAR = 365.25
FIGS = "volve/reports/figs"


@dataclass(frozen=True)
class Outcome:
    oil_per_year: dict[int, float]  # million Sm3, Sodir
    gas_sales_per_year: dict[int, float]  # billion Sm3, Sodir (net)
    monthly_oil: list[tuple[dt.date, float]]  # month start, million Sm3, Sodir
    investments: dict[int, float]  # million NOK nominal, Sodir
    recoverable_estimate: dict[int, float]  # year-end -> million Sm3, Sodir
    in_place: float  # million Sm3, Sodir
    workbook_per_year: dict[int, dict[str, float]]  # oil, gas, water, injection; million Sm3
    first_oil: dt.date
    last_oil: dt.date
    wellbores: list[dict[str, str]]
    snapshot: str


def _float(text: str) -> float:
    return float(text) if text else 0.0


def outcome() -> Outcome:
    """What happened, from the Sodir snapshot and the production workbook."""
    import pandas as pd  # only needed here

    snapshot = sodir.latest(data_dir() / "sodir")
    yearly = [
        r
        for r in sodir.read_table("field_production_yearly", snapshot)
        if r["prfInformationCarrier"] == FIELD
    ]
    monthly = [
        r
        for r in sodir.read_table("field_production_monthly", snapshot)
        if r["prfInformationCarrier"] == FIELD
    ]
    invest = [
        r
        for r in sodir.read_table("field_investment_yearly", snapshot)
        if r["prfInformationCarrier"] == FIELD
    ]
    reserves = [r for r in sodir.read_table("field_reserves", snapshot) if r["fldName"] == FIELD]
    in_place = [
        r for r in sodir.read_table("field_in_place_volumes", snapshot) if r["fldName"] == FIELD
    ]
    wells = [
        r
        for r in sodir.read_table("wellbore_development_all", snapshot)
        if r.get("wlbField") == FIELD
    ]

    book = pd.read_excel(volve_data() / "production_data" / "Volve production data.xlsx")
    columns = {
        "BORE_OIL_VOL": "oil",
        "BORE_GAS_VOL": "gas",
        "BORE_WAT_VOL": "water",
        "BORE_WI_VOL": "injection",
    }
    per_year = book.groupby(book["DATEPRD"].dt.year)[list(columns)].sum() / 1e6
    producing = book[book["BORE_OIL_VOL"] > 0]["DATEPRD"]
    return Outcome(
        oil_per_year={int(r["prfYear"]): _float(r["prfPrdOilNetMillSm3"]) for r in yearly},
        gas_sales_per_year={int(r["prfYear"]): _float(r["prfPrdGasNetBillSm3"]) for r in yearly},
        monthly_oil=sorted(
            (dt.date(int(r["prfYear"]), int(r["prfMonth"]), 1), _float(r["prfPrdOilNetMillSm3"]))
            for r in monthly
        ),
        investments={int(r["prfYear"]): _float(r["prfInvestmentsMillNOK"]) for r in invest},
        recoverable_estimate={
            int(r["fldVersion"]): _float(r["fldRecoverableOil"]) for r in reserves
        },
        in_place=_float(in_place[0]["fldInplaceOil"]),
        workbook_per_year={
            int(year): {name: float(row[column]) for column, name in columns.items()}
            for year, row in per_year.iterrows()
        },
        first_oil=producing.min().date(),
        last_oil=producing.max().date(),
        wellbores=wells,
        snapshot=snapshot.name,
    )


def _read_csv(name: str) -> list[dict[str, str]]:
    with (data_dir() / FIGS / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def plan_profiles() -> dict[str, dict[int, float]]:
    """Annual oil per case before the economic cut-off (digitised from Figure 4.5)."""
    rows = _read_csv("Volve_PUD_cmt_p025_fig4-5.csv")
    names = {"mean": "mean", "P90": "p90", "P50": "p50", "P10": "p10"}
    return {
        case: {
            int(r["year"]): float(r[f"{column} (million Sm3 per year)"])
            for r in rows
            if r[f"{column} (million Sm3 per year)"]
        }
        for case, column in names.items()
    }


def plan_series(name: str) -> tuple[np.ndarray, np.ndarray]:
    """A digitised curve (decimal year, value) from Figures 4.2 to 4.4."""
    rows = _read_csv(name)
    value = next(key for key in rows[0] if key != "year")
    return (
        np.array([float(r["year"]) for r in rows]),
        np.array([float(r[value]) for r in rows]),
    )


def plan_yearly(name: str) -> dict[str, dict[int, float]]:
    """Yearly means of digitised rates (Figures 4.2 to 4.4), by series."""
    rows = _read_csv(name)
    series = [key for key in rows[0] if key != "year"]
    return {s: {int(r["year"]): float(r[s]) for r in rows if r[s]} for s in series}


def decimal_year(day: dt.date) -> float:
    start = dt.date(day.year, 1, 1)
    return day.year + (day - start).days / ((dt.date(day.year + 1, 1, 1) - start).days)


def months_between(first: dt.date, last: dt.date) -> float:
    return (last - first).days / (DAYS_PER_YEAR / 12)


def monthly_rates(result: Outcome) -> list[tuple[float, float]]:
    """Actual oil rate (Sm3/d) by months since first oil, one point per calendar month."""
    points = []
    for month, volume in result.monthly_oil:
        following = dt.date(month.year + month.month // 12, month.month % 12 + 1, 1)
        end = min(following, result.last_oil + dt.timedelta(days=1))
        start = max(month, result.first_oil)
        days = (end - start).days
        if days > 0 and volume > 0:
            middle = start + dt.timedelta(days=days / 2)
            points.append((months_between(result.first_oil, middle), volume * 1e6 / days))
    return points


def plan_volume(years: np.ndarray, rate: np.ndarray, months: float) -> float:
    """Planned oil (million Sm3) in the first ``months`` after planned first oil."""
    start = decimal_year(PLAN_FIRST_OIL)
    grid = np.linspace(start, start + months / 12, 400)
    values = np.interp(grid, years, rate, left=0.0)
    return float(np.trapezoid(values, grid) * DAYS_PER_YEAR / 1e6)


def actual_volume(result: Outcome, months: int) -> float:
    """Oil produced (million Sm3) in the first ``months`` calendar months from first oil."""
    start = dt.date(result.first_oil.year, result.first_oil.month, 1)
    produced = [volume for month, volume in result.monthly_oil if month >= start]
    return float(sum(produced[:months]))


def deflate(per_year: dict[int, float], base_year: int = 2005) -> dict[int, float]:
    """Nominal amounts in money of ``base_year``, using the consumer price index."""
    index = public.read_series("ssb_cpi")
    return {
        year: value * index[base_year] / index[year]
        for year, value in per_year.items()
        if year in index
    }


def plan_investments() -> dict[int, float]:
    per_year, _ = pud_facts.COSTS_NOMINAL["total_investments"]
    return {y: float(v) for y, v in zip(pud_facts.COST_YEARS, per_year, strict=True) if v}


def well_counts(result: Outcome) -> dict[str, list[str]]:
    """Development wellbores that were drilled, by what they were used for."""
    groups: dict[str, list[str]] = {
        "oil producers": [],
        "water injectors": [],
        "water producers (Utsira)": [],
        "observation and pilot wellbores": [],
    }
    for well in result.wellbores:
        if not well["wlbEntryDate"]:
            continue
        label = f"{well['wlbWellboreName'].removeprefix('15/9-')} ({well['wlbEntryDate'][-4:]})"
        if well["wlbPurpose"] == "INJECTION":
            groups["water injectors"].append(label)
        elif well["wlbPurpose"] == "OBSERVATION":
            groups["observation and pilot wellbores"].append(label)
        elif well["wlbContent"] == "WATER":
            groups["water producers (Utsira)"].append(label)
        else:
            groups["oil producers"].append(label)
    return {name: sorted(wells, key=lambda w: (w[-5:-1], w)) for name, wells in groups.items()}
