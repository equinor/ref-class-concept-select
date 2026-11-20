"""Development stage: estimates at the investment decision against what fields delivered.

The reference class is built from fields, not from forecasts: for each field
the reserves sanctioned with its first PDO, and what it then produced, month
by month from first production.
"""

from __future__ import annotations

from functools import cache

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

from rcfkit import data, stats

HORIZONS = tuple(range(1, 11))  # years since first production
QUANTILES = (0.10, 0.25, 0.50, 0.75, 0.90)
FIRST_ACCOUNT_YEAR = 1990  # the resource accounts in the study data start here
PRE_APPROVAL_LIMIT = 0.05  # share of sanctioned reserves produced before approval
OIL_SHARE = 0.5  # an oil field has at least this share of oil in its sanctioned reserves


@cache
def candidates() -> pd.DataFrame:
    """Every field with the facts that decide whether it can be in a reference class.

    ``excluded`` gives the first rule a field fails, or is empty.
    """
    table = data.fields().set_index("field_id")
    monthly = data.production_monthly()
    monthly = monthly.assign(oe=monthly["oil"] + monthly["gas"])
    table["approval_month"] = table["approved"].dt.to_period("M")

    starts, before = {}, {}
    for field_id, months in monthly[monthly["oe"] > 0].groupby("field_id"):
        approved = table["approval_month"].get(field_id)
        if approved is None or pd.isna(approved):
            continue
        after = months[months["month"] >= approved]
        if len(after):
            starts[field_id] = after["month"].iloc[0]
        before[field_id] = months.loc[months["month"] < approved, "oe"].sum()
    table["start"] = pd.Series(starts)
    table["produced_before_approval"] = pd.Series(before).reindex(table.index).fillna(0.0)
    table["oil_share"] = table["fid_oil"] / table["fid_oe"]

    def reason(row: pd.Series) -> str:
        if pd.isna(row["approved"]):
            return "no PDO approval recorded"
        if row["first_approval_type"] != "PDO":
            return "first approval is a PDO exemption"
        if row["approved"].year < FIRST_ACCOUNT_YEAR:
            return f"approved before {FIRST_ACCOUNT_YEAR}"
        if pd.isna(row["fid_gap"]):
            return "no reserves estimate within a year of approval"
        if not row["fid_oe"] > 0:
            return "sanctioned reserves are zero"
        if row["produced_before_approval"] > PRE_APPROVAL_LIMIT * row["fid_oe"]:
            return "produced before approval"
        if pd.isna(row["start"]):
            return "not yet producing"
        return ""

    table["excluded"] = table.apply(reason, axis=1)
    return table.reset_index()


@cache
def profiles(basis: str = "oe") -> pd.DataFrame:
    """Cumulative production as a fraction of sanctioned reserves, by year since first production.

    One row per field that passes the inclusion rules; columns 1 to 10 hold
    the fraction after that many 12-month periods and are missing where the
    field's history is shorter. ``basis`` is ``oe`` (oil and gas over
    sanctioned oil and gas) or ``oil`` (oil over sanctioned oil).
    """
    table = candidates()
    table = table[table["excluded"] == ""].copy()
    reserves = table["fid_oe"] if basis == "oe" else table["fid_oil"]
    table = table[reserves > 0]
    monthly = data.production_monthly()
    volume = monthly["oil"] + monthly["gas"] if basis == "oe" else monthly["oil"]
    monthly = monthly.assign(volume=volume)
    end = monthly["month"].max()
    rows = []
    for field in table.itertuples():
        series = monthly[monthly["field_id"] == field.field_id].set_index("month")["volume"]
        sanctioned = field.fid_oe if basis == "oe" else field.fid_oil
        row = {"field_id": field.field_id}
        for years in HORIZONS:
            last = field.start + 12 * years - 1
            if last <= end:
                row[years] = series[(series.index >= field.start) & (series.index <= last)].sum()
                row[years] /= sanctioned
        rows.append(row)
    keep = ["field_id", "field", "status", "approved", "approval_month", "start", "fid_oil"]
    keep += ["fid_gas", "fid_oe", "oil_share", "final_oil", "final_gas", "final_oe"]
    return table[keep].merge(pd.DataFrame(rows), on="field_id")


def select(
    table: pd.DataFrame,
    *,
    oil_only: bool = False,
    exclude: str | None = None,
    known_by: pd.Period | None = None,
    size_near: float | None = None,
    size_factor: float = 4.0,
) -> pd.DataFrame:
    """Apply a reference class definition to the profile table.

    ``known_by`` keeps only what was observable in that month: fields approved
    before it, and each horizon only where the field had completed it.
    ``size_near`` keeps fields whose sanctioned reserves are within
    ``size_factor`` times of that size.
    """
    result = table
    if oil_only:
        result = result[result["oil_share"] >= OIL_SHARE]
    if exclude:
        result = result[result["field"] != exclude]
    if size_near:
        size = result["fid_oe"]
        result = result[(size >= size_near / size_factor) & (size <= size_near * size_factor)]
    if known_by is not None:
        result = result[result["approval_month"] < known_by].copy()
        for years in HORIZONS:
            complete = (result["start"] + 12 * years - 1) < known_by
            result[years] = result[years].where(complete)
    return result


def distribution(members: pd.DataFrame, bootstrap: int = 1000) -> pd.DataFrame:
    """Quantiles of the fraction produced, per horizon, with 90 % bootstrap intervals."""
    rows = []
    for years in HORIZONS:
        values = members[years].dropna().to_numpy()
        row = {"years": years, "n": len(values)}
        if len(values) >= 5:
            for q in QUANTILES:
                row[f"q{round(q * 100)}"] = float(np.quantile(values, q))
            low, high = stats.bootstrap(
                lambda v: np.quantile(v, [0.1, 0.5, 0.9]), values, n=bootstrap
            )
            for index, name in enumerate(("q10", "q50", "q90")):
                row[f"{name}_low"], row[f"{name}_high"] = float(low[index]), float(high[index])
            row["mean"] = float(values.mean())
        rows.append(row)
    return pd.DataFrame(rows)


def class_effects(table: pd.DataFrame, years: int = 5) -> dict:
    """Whether field size or main product shifts the fraction produced after ``years``."""
    sample = table[table[years].notna()]
    size = scipy_stats.spearmanr(np.log(sample["fid_oe"]), sample[years])
    oil = sample.loc[sample["oil_share"] >= OIL_SHARE, years]
    gas = sample.loc[sample["oil_share"] < OIL_SHARE, years]
    product = scipy_stats.mannwhitneyu(oil, gas)
    start_year = sample["start"].dt.year
    era = scipy_stats.spearmanr(start_year, sample[years])
    return {
        "years": years,
        "n": int(len(sample)),
        "size_rho": float(size.statistic),
        "size_p": float(size.pvalue),
        "oil_n": int(len(oil)),
        "gas_n": int(len(gas)),
        "oil_median": float(oil.median()),
        "gas_median": float(gas.median()),
        "product_p": float(product.pvalue),
        "era_rho": float(era.statistic),
        "era_p": float(era.pvalue),
    }


def backtest(table: pd.DataFrame, horizons: tuple[int, ...] = (2, 3, 5), minimum: int = 10) -> dict:
    """Would the reference class have given calibrated ranges, field by field, at the time?

    For each field the class is rebuilt from what was observable in the month
    its PDO was approved, and the field's later outcome is placed in that
    distribution. If the method is calibrated the positions are uniform:
    10 % below the class's 10 % quantile, 80 % inside, 10 % above.
    """
    result = {}
    for years in horizons:
        positions, relative, names = [], [], []
        for field in table[table[years].notna()].itertuples():
            known = select(table, known_by=field.approval_month)
            reference = known[years].dropna().to_numpy()
            if len(reference) < minimum:
                continue
            outcome = getattr(field, f"_{table.columns.get_loc(years) + 1}")
            positions.append(stats.percentile_of(outcome, reference))
            relative.append(outcome / np.median(reference))
            names.append(field.field)
        positions = np.array(positions)
        test = scipy_stats.kstest(positions, "uniform")
        result[years] = {
            "n": int(len(positions)),
            "below": float(np.mean(positions < 0.10)),
            "inside": float(np.mean((positions >= 0.10) & (positions <= 0.90))),
            "above": float(np.mean(positions > 0.90)),
            "median_position": float(np.median(positions)),
            "median_relative": float(np.median(relative)),
            "ks_p": float(test.pvalue),
            "positions": positions.tolist(),
            "fields": names,
        }
    return result


def reserves_growth(table: pd.DataFrame) -> dict:
    """Latest estimate of ultimate recovery over the reserves sanctioned at the first PDO."""
    sample = table[(table["final_oe"] > 0) & (table["fid_oe"] > 0)]
    result = {}
    groups = {
        "All fields": sample,
        "Shut down": sample[sample["status"] == "Shut down"],
        "Producing": sample[sample["status"] == "Producing"],
        "Oil fields": sample[sample["oil_share"] >= OIL_SHARE],
        "Gas fields": sample[sample["oil_share"] < OIL_SHARE],
    }
    for name, group in groups.items():
        summary = stats.ratio_summary(group["fid_oe"].to_numpy(), group["final_oe"].to_numpy())
        low, high = stats.bootstrap(
            lambda f, o: np.median(o / f), group["fid_oe"].to_numpy(), group["final_oe"].to_numpy()
        )
        summary["median_ci"] = (float(low), float(high))
        result[name] = summary
    return result


def discovery_link() -> pd.DataFrame:
    """Fields whose discovery well is in the prognosis data: the well's volumes beside the field's.

    ``well_prognosis`` is the pre-drill volume in place prognosed for all the
    well's prospects, ``well_result`` the volume in place recorded after
    drilling for those that were discoveries. ``rows_prognosis`` is the plain
    sum over every prognosis row, which is how the expert study's link file
    was built.
    """
    prospects = data.prospects()
    per_well = prospects.groupby("well").agg(
        well_prognosis=("ip_oe_prog", "sum"),
        well_result=("ip_oe_res", lambda s: s[prospects.loc[s.index, "discovery"] == 1].sum()),
        prospects=("prospect", "size"),
        discoveries=("discovery", "sum"),
    )
    rows = data.prognosis_rows()
    plain = rows[rows["kind"] == "PROGNOSIS"]
    columns = ["ip_oil_main", "ip_oil_assoc", "ip_gas_main", "ip_gas_assoc"]
    per_well["rows_prognosis"] = plain[columns].sum(axis=1).groupby(plain["well"]).sum()
    table = candidates().merge(per_well, left_on="discovery_well", right_index=True, how="inner")
    keep = ["field", "discovery_well", "approved", "status", "prospects", "discoveries"]
    keep += ["rows_prognosis", "well_prognosis", "well_result", "fid_oe", "fid_gap", "final_oe"]
    keep += ["in_place_oe", "excluded"]
    return table[keep].reset_index(drop=True)
