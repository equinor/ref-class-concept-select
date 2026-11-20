"""The Volve case: the PDO forecast, the reference class forecast and the outcome.

Everything is in million Sm3 of oil, counted in 12-month periods from first
oil, so that a delayed start does not count as a production shortfall (the
alignment used by Nesvold & Bratvold, 2022).
"""

from __future__ import annotations

import datetime as dt
from functools import cache

import numpy as np
import pandas as pd

from rcfkit import data, fields, stats
from syskit import facts

FIELD = "VOLVE"
FIELD_ID = 3420717
PLAN_FIRST_OIL = dt.date(2007, 3, 6)  # PDO Figure 12.1: "Produksjons start 06.03.2007"
CASES = {"low": "p90", "mean": "mean", "median": "p50", "high": "p10"}  # PDO: P90 is the low case
YEARS = tuple(range(1, 10))  # Volve produced for eight years and seven months

# Nesvold & Bratvold (2022), Table B.3: median calibration factors by production year.
PAPER_FACTORS = {
    "year": (2, 3, 4, 5, 6, 7, 8, 9, 10),
    "a_mean": (0.291, 0.324, 0.311, 0.282, 0.537, 0.434, 0.549, 0.628, 0.642),
    "b": (0.781, 0.795, 0.793, 0.82, 0.883, 0.917, 0.955, 0.997, 1.048),
    "c_mean": (1.359, 1.186, 1.131, 1.225, 1.314, 1.45, 1.511, 1.57, 1.677),
    "a_low": (0.346, 0.413, 0.424, 0.379, 0.717, 0.545, 0.737, 0.833, 0.855),
    "c_high": (1.2, 1.01, 0.993, 1.00, 1.022, 1.065, 1.164, 1.145, 1.2),
}


def cumulative_since_start(per_year: dict[int, float], start: dt.date) -> dict[int, float]:
    """Cumulative volume after 1, 2, ... years from ``start``, from calendar-year volumes.

    Production is taken as even within each calendar year (within the part of
    the first year that follows ``start``), and as zero after the last year
    given.
    """
    years = sorted(per_year)
    year_start = dt.date(start.year, 1, 1)
    offset = (start - year_start).days / 365.25
    times, totals = [0.0], [0.0]
    for year in years:
        times.append(year + 1 - start.year - offset)
        totals.append(totals[-1] + per_year[year])
    return {k: float(np.interp(k, times, totals)) for k in YEARS}


@cache
def plan() -> dict:
    """The PDO's oil forecast (Table 4.5) by case, and its headline estimates."""
    values = facts.read("pud2005")
    per_year = {
        name: {
            int(key.rsplit(".", 1)[1]): float(value)
            for key, value in values.items()
            if key.startswith(f"pud2005.oil_production.{case}.") and key[-4:].isdigit()
        }
        for name, case in CASES.items()
    }
    return {
        "per_year": per_year,
        "cumulative": {
            name: cumulative_since_start(series, PLAN_FIRST_OIL)
            for name, series in per_year.items()
        },
        "reserves": {
            name: float(values[f"pud2005.recoverable_oil.t45.{case}"])
            for name, case in CASES.items()
        },
        "in_place": {
            name: float(values[f"pud2005.stooip.t34.closure.{case}"])
            for name, case in CASES.items()
        },
    }


@cache
def outcome() -> dict:
    """What Volve produced, by year since first oil, and the public estimates for the field."""
    monthly = data.production_monthly()
    series = monthly[monthly["field_id"] == FIELD_ID].set_index("month")["oil"]
    series = series[series > 0]
    start = series.index[0]
    cumulative = {k: float(series[series.index <= start + 12 * k - 1].sum()) for k in YEARS}
    row = fields.candidates().set_index("field").loc[FIELD]
    return {
        "start": start,
        "end": series.index[-1],
        "cumulative": cumulative,
        "total": float(series.sum()),
        "sanctioned_oil": float(row["fid_oil"]),
        "sanctioned_oe": float(row["fid_oe"]),
        "final_oe": float(row["final_oe"]),
        "in_place_oil": float(data.fields().set_index("field").loc[FIELD, "in_place_oil"]),
        "in_place_oe": float(row["in_place_oe"]),
    }


CLASSES = {
    "Oil fields of similar size": {"oil_only": True, "size_near": True},
    "All oil fields": {"oil_only": True},
    "All fields": {},
    "Oil fields, as known in January 2005": {"oil_only": True, "known_by": pd.Period("2005-01")},
}
PRIMARY = "Oil fields of similar size"


def members(name: str) -> pd.DataFrame:
    """Members of one of the reference classes for Volve; Volve itself is never a member."""
    rule = dict(CLASSES[name])
    if rule.pop("size_near", False):
        rule["size_near"] = outcome()["sanctioned_oe"]
    return fields.select(fields.profiles("oil"), exclude=FIELD, **rule)


@cache
def reference_forecast(name: str = PRIMARY) -> pd.DataFrame:
    """Reference class forecast of cumulative oil: class fractions times sanctioned reserves."""
    table = fields.distribution(members(name))
    table = table[table["years"].isin(YEARS)].copy()
    scale = outcome()["sanctioned_oil"]
    columns = [c for c in table.columns if c.startswith("q") or c == "mean"]
    table[columns] = table[columns] * scale
    return table


def calibrated_plan() -> pd.DataFrame:
    """The PDO forecast after the calibration factors of Nesvold & Bratvold (2022).

    The paper's production year k is taken as k years after first oil.
    ``mean_*`` uses the PDO mean only (Eq. 5), ``triplet_*`` scales the PDO's
    own low and high cases (Eq. 6).
    """
    factors = pd.DataFrame(PAPER_FACTORS).set_index("year")
    cumulative = plan()["cumulative"]
    rows = []
    for year in YEARS:
        if year not in factors.index:
            continue
        f = factors.loc[year]
        mean = cumulative["mean"][year]
        rows.append(
            {
                "years": year,
                "mean_low": f["a_mean"] * mean,
                "central": f["b"] * mean,
                "mean_high": f["c_mean"] * mean,
                "triplet_low": f["a_low"] * cumulative["low"][year],
                "triplet_high": f["c_high"] * cumulative["high"][year],
            }
        )
    return pd.DataFrame(rows)


def comparison(name: str = PRIMARY) -> pd.DataFrame:
    """Per year since first oil: the forecasts, the outcome, and how each forecast fared."""
    cumulative, actual = plan()["cumulative"], outcome()["cumulative"]
    reference = reference_forecast(name).set_index("years")
    calibrated = calibrated_plan().set_index("years")
    class_members = members(name)
    scale = outcome()["sanctioned_oil"]
    rows = []
    for year in YEARS:
        value = actual[year]
        row = {
            "years": year,
            "actual": value,
            "plan_low": cumulative["low"][year],
            "plan_mean": cumulative["mean"][year],
            "plan_median": cumulative["median"][year],
            "plan_high": cumulative["high"][year],
            "attainment": value / cumulative["mean"][year],
        }
        if year in reference.index and "q50" in reference.columns:
            r = reference.loc[year]
            row |= {"rcf_low": r["q10"], "rcf_median": r["q50"], "rcf_high": r["q90"], "n": r["n"]}
            sample = class_members[year].dropna().to_numpy() * scale
            row["rcf_position"] = stats.percentile_of(value, sample)
            row["rcf_score"] = stats.pinball({0.1: r["q10"], 0.5: r["q50"], 0.9: r["q90"]}, value)
        row["plan_score"] = stats.pinball(
            {0.1: row["plan_low"], 0.5: row["plan_median"], 0.9: row["plan_high"]}, value
        )
        if year in calibrated.index:
            c = calibrated.loc[year]
            row |= {"cal_low": c["mean_low"], "cal_central": c["central"]}
            row |= {"cal_high": c["mean_high"]}
            row["cal_score"] = stats.pinball(
                {0.1: c["mean_low"], 0.5: c["central"], 0.9: c["mean_high"]}, value
            )
        rows.append(row)
    return pd.DataFrame(rows)


def prospect() -> pd.DataFrame:
    """The two prospects of the Volve discovery well, 15/9-19 SR, in the prognosis data."""
    table = data.prospects()
    return table[table["well"] == "15/9-19 SR"].reset_index(drop=True)
