"""The expert study's calculations, repeated from its notebook.

Each function follows a cell of ``agents/rcf/study/prognosis analysis.ipynb``
step for step, so that the review can state which of its numbers were
reproduced and measure what each of its choices does to the result.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from rcfkit import data, stats

RECOVERY = {"oil": 0.35, "gas": 0.60}  # the notebook's fixed recovery factors
RECOVERABLE = [
    "Recoverable Gas Main Mean",
    "Recover Oil Assoc Mean",
    "Recoverable Oil Main Mean",
    "Recover Gas Assoc Mean",
]


def _rows(first_year: int = 1980, last_year: int = 2026) -> pd.DataFrame:
    """The prognosis file as the notebook prepares it, including its year filter."""
    table = pd.read_excel(data.study_data() / data.PROGNOSIS_FILE, sheet_name="Data")
    table["well"] = table["Well name"].astype(str).str.strip()
    table["p"] = _numeric(table["Probability Technical Total"])
    table["discovery"] = data.yes_no(table["Discovery?"])
    year = pd.to_numeric(table["Evaluation Year"], errors="coerce")
    table = table[(year >= first_year) & (year <= last_year)].copy()
    table["type"] = table["Prognosis - Result"].astype(str).str.strip().str.upper()
    for column in RECOVERABLE:
        table[column] = _numeric(table[column])
    return table


def _numeric(series: pd.Series) -> pd.Series:
    text = series.astype(str).str.replace(",", ".", regex=False)
    return pd.to_numeric(text.str.replace(r"[^0-9eE+\-.]", "", regex=True), errors="coerce")


def probability_calibration() -> dict:
    """Cell 1: mean probability per well against any discovery in the well."""
    rows = _rows()
    wells = rows.groupby("well").agg(p=("p", "mean"), found=("discovery", "max")).dropna()
    p, y = wells["p"].to_numpy(), wells["found"].to_numpy()
    return {
        "rows": int(len(rows)),
        "wells": int(len(wells)),
        "bins": stats.reliability(p, y, np.linspace(0, 1, 11)),
        "mean_forecast": float(p.mean()),
        "observed_rate": float(y.mean()),
    }


def volumes() -> dict:
    """Cells 3 and 5: summed recoverable means per discovery well, and the same over fixed
    recovery factors as "in place"."""
    rows = _rows()
    found = set(rows.loc[rows["discovery"] == 1, "well"])
    rows = rows[rows["well"].isin(found)].copy()
    rows["recoverable"] = rows[RECOVERABLE].sum(axis=1, min_count=1)
    oil = rows["Recoverable Oil Main Mean"].fillna(0) + rows["Recover Oil Assoc Mean"].fillna(0)
    gas = rows["Recoverable Gas Main Mean"].fillna(0) + rows["Recover Gas Assoc Mean"].fillna(0)
    rows["in_place"] = oil / RECOVERY["oil"] + gas / RECOVERY["gas"]
    result = {}
    for name in ("recoverable", "in_place"):
        table = rows.groupby(["well", "type"])[name].sum().unstack()
        table = table.dropna(subset=["PROGNOSIS", "RESULT"])
        result[f"{name}_wells"] = int(len(table))
        table = table[(table["PROGNOSIS"] > 0) & (table["RESULT"] > 0)]
        result[name] = {
            "n": int(len(table)),
            "prognosis": float(table["PROGNOSIS"].sum()),
            "result": float(table["RESULT"].sum()),
            "correlation": float(table[["PROGNOSIS", "RESULT"]].corr().iloc[0, 1]),
            "log_correlation": float(np.log(table[["PROGNOSIS", "RESULT"]]).corr().iloc[0, 1]),
            "median_ratio": float((table["RESULT"] / table["PROGNOSIS"]).median()),
        }
    return result


def link_file() -> dict:
    """Cell 6: sanctioned reserves against the "discovery in-place" of the link file."""
    table = pd.read_excel(data.study_data() / "fid_reserves_vs_discovery_inplace_total.xlsx")
    x = table["discovery_oil_inplace"] + table["discovery_gas_inplace"]
    y = table["fid_oil_reserves"] + table["fid_gas_reserves"]
    keep = (x > 0) & (y > 0)
    return {
        "rows": int(len(table)),
        "n": int(keep.sum()),
        "log_correlation": float(np.corrcoef(np.log10(x[keep]), np.log10(y[keep]))[0, 1]),
        "median_ratio": float((y[keep] / x[keep]).median()),
        "volve_ratio": float((y / x)[table["Feltnavn"] == "VOLVE"].iloc[0]),
    }


def reference_class(
    years: int = 10,
    *,
    drop: str | None = None,
    contemporary: bool = False,
    oil_and_gas_only: bool = False,
    full_years_only: bool = False,
) -> pd.DataFrame:
    """Cell 7: cumulative production over "FID reserves" per calendar year of production.

    With the defaults this is the notebook's calculation. The switches change
    one choice each: ``drop`` leaves a field out; ``contemporary`` keeps only
    fields whose reserves estimate dates from within a year of the approval
    of a PDO in 1990 or later; ``oil_and_gas_only`` counts oil and gas in the
    production, as the reserves do, instead of all oil equivalents;
    ``full_years_only`` ignores the incomplete last calendar year.

    Returns one row per field with the fractions in columns 1 to ``years``.
    """
    folder = data.study_data()
    production = pd.read_excel(folder / "field_production_yearly.xlsx")
    approvals = pd.read_excel(folder / "field_pdo_hst.xlsx")
    account = pd.read_excel(folder / "RCB_reserves.xlsx")

    approvals["approved"] = pd.to_datetime(approvals["Dato PUD godkjent"], errors="coerce")
    kind = approvals["Type"].astype(str).str.upper().str.strip()
    approvals = approvals[kind.isin(["PDO", "PDO EXEMPTION"])].sort_values("approved")
    approvals = approvals.drop_duplicates("NPDID felt")
    rows = []
    for approval in approvals.itertuples():
        candidates = account[account["field_id"] == approval._6].copy()  # NPDID felt
        if candidates.empty:
            continue
        candidates["gap"] = (candidates["year"] - approval.approved.year).abs()
        best = candidates.sort_values(["gap", "year"]).iloc[0]
        rows.append(
            {
                "field": str(approval.Feltnavn).strip().upper(),
                "approved": approval.approved.year,
                "gap": int(best["gap"]),
                "reserves": best["oil_reserves"] + best["gas_reserves"],
            }
        )
    reserves = pd.DataFrame(rows)
    if contemporary:
        reserves = reserves[(reserves["gap"] <= 1) & (reserves["approved"] >= 1990)]
    if drop:
        reserves = reserves[reserves["field"] != drop]

    production.columns = [c.replace("\n", "") for c in production.columns]
    volume = production["Netto – oljeekvivalenter [mill Sm3]"]
    if oil_and_gas_only:
        volume = production["Netto – olje [mill Sm3]"] + production["Netto – gass [mrd Sm3]"]
    yearly = pd.DataFrame(
        {
            "field": production["Felt (Funn)"].astype(str).str.strip().str.upper(),
            "year": pd.to_numeric(production["År"], errors="coerce"),
            "volume": pd.to_numeric(volume, errors="coerce"),
        }
    )
    yearly = yearly.groupby(["field", "year"], as_index=False)["volume"].sum()
    table = yearly.merge(reserves, on="field")
    table = table[table["reserves"] > 0]
    start = table[table["volume"] > 0].groupby("field")["year"].min().rename("start")
    table = table.merge(start, on="field")
    last = table["year"].max() - (1 if full_years_only else 0)
    table = table[table["start"] + years - 1 <= last]
    table["production_year"] = table["year"] - table["start"] + 1
    table = table[table["production_year"].between(1, years)]
    wide = table.pivot_table(
        index="field", columns="production_year", values="volume", aggfunc="sum"
    )
    wide = wide.reindex(columns=range(1, years + 1)).fillna(0).cumsum(axis=1)
    info = reserves.set_index("field").loc[wide.index]
    fractions = wide.div(info["reserves"], axis=0)
    return fractions.join(info).join(start)


def steps(years: int = 5) -> list[dict]:
    """What each correction does to the notebook's distribution after ``years`` years."""
    switches = [
        ("As in the notebook", {}),
        ("Volve left out", {"drop": "VOLVE"}),
        ("… and only estimates made within a year of a PDO from 1990 on", {"contemporary": True}),
        ("… and production counted as oil and gas, like the reserves", {"oil_and_gas_only": True}),
        ("… and the incomplete year 2026 ignored", {"full_years_only": True}),
    ]
    rows, options = [], {}
    for label, change in switches:
        options |= change
        values = reference_class(**options)[years]
        low, median, high = np.quantile(values, [0.1, 0.5, 0.9])
        rows.append(
            {"step": label, "n": int(len(values)), "low": low, "median": median, "high": high}
        )
    return rows
