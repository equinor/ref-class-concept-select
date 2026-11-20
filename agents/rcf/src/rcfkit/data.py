"""The data of the reference class study, as tidy tables.

The files are the ones the expert study used (``agents/rcf/study/data``):
exports of Sodir tables synchronised 19.11.2026, the resource-account series
``RCB_reserves.xlsx`` (reserves per field and year, 1990-2021) and the
prognosis-and-result data for exploration wells. Monthly production comes from
the Sodir snapshot of the same date in ``data/sodir``.

Volumes are in million Sm3 of oil and billion Sm3 of gas; one billion Sm3 of
gas counts as one million Sm3 of oil equivalent.
"""

from __future__ import annotations

from functools import cache
from pathlib import Path

import numpy as np
import pandas as pd

from syskit import sodir
from syskit.paths import data_dir, repo_root

PROGNOSIS_FILE = "2026-11 PrognosisResultData_Released.xlsx"

# Column of the prognosis file -> short name. Double spaces are in the file.
VOLUME_COLUMNS = {
    "Oil Main  In-place Mean": "ip_oil_main",
    "Oil Assoc  In-place Mean": "ip_oil_assoc",
    "Gas Main In-place Mean": "ip_gas_main",
    "Gas Assoc  In-place Mean": "ip_gas_assoc",
    "Oil Main In-place Min": "ip_oil_min",
    "Oil Main  In-place Max": "ip_oil_max",
    "Gas Main In-place Min": "ip_gas_min",
    "Gas Main In-place Max": "ip_gas_max",
    "Recoverable Oil Main Mean": "rec_oil_main",
    "Recover Oil Assoc Mean": "rec_oil_assoc",
    "Recoverable Gas Main Mean": "rec_gas_main",
    "Recover Gas Assoc Mean": "rec_gas_assoc",
}
PARAMETER_COLUMNS = {
    "Rock Vol Mean": "rock_volume",
    "Area Mean": "area",
    "Reservoir Thickness Mean": "thickness",
    "HC Column in Prospect Mean": "hc_column",
    "Net Gross Mean": "net_gross",
    "Porosity Mean": "porosity",
    "Water Sat Mean": "water_saturation",
    "Top Reservoir Depth Mean": "top_reservoir_depth",
}


def study_data() -> Path:
    return repo_root() / "agents" / "rcf" / "study" / "data"


def to_number(series: pd.Series) -> pd.Series:
    """Numbers from cells that may hold text with a decimal comma."""
    text = series.astype(str).str.strip().str.replace(",", ".", regex=False)
    return pd.to_numeric(text, errors="coerce")


def yes_no(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.upper().map({"YES": 1.0, "NO": 0.0})


@cache
def prognosis_rows() -> pd.DataFrame:
    """The prognosis file, one row per prognosis or result, with cleaned keys and numbers."""
    raw = pd.read_excel(study_data() / PROGNOSIS_FILE, sheet_name="Data").iloc[1:]
    rows = pd.DataFrame(
        {
            "well": raw["Well name"].astype(str).str.strip(),
            "prospect": raw["Prospect name"].astype(str).str.split().str.join(" ").str.upper(),
            "kind": raw["Prognosis - Result"].astype(str).str.strip().str.upper(),
            "case": raw["Prognosis ID"].astype(str).str.strip(),
            "case_priority": to_number(raw["Prognosis Priority"]),
            "prospect_priority": to_number(raw["Prospect Priority if several in well"]),
            "spud_year": to_number(raw["Spud date"]) // 10000,
            "p": to_number(raw["Probability Technical Total"]),
            "phase": raw["Main Phase"].astype(str).str.strip().str.upper(),
            "fractile_min": to_number(raw["Fractile Resource Min"]),
            "fractile_max": to_number(raw["Fractile Resource Max"]),
            "central": raw["Fractile Resource Mean"].astype(str).str.strip().str.upper(),
            "discovery": yes_no(raw["Discovery?"]),
            "surprise": yes_no(raw["Surprise Discovery?"]),
        }
    )
    for column, name in {**VOLUME_COLUMNS, **PARAMETER_COLUMNS}.items():
        rows[name] = to_number(raw[column])
    return rows.reset_index(drop=True)


def discovery_probability(p: np.ndarray) -> float:
    """Probability of discovery for a prospect from the probabilities of its prognosis cases.

    Cases with different probabilities that sum to at most one are alternative
    outcomes (an oil case and a gas case), so the probabilities add. Cases
    that all carry the same probability describe one chance of discovery. A
    sum above one cannot be a probability; the largest case is used.
    """
    p = p[~np.isnan(p)]
    if p.size == 0:
        return float("nan")
    if p.size == 1 or np.ptp(p) == 0:
        return float(p[0])
    total = float(p.sum())
    return total if total <= 1.0 else float(p.max())


def _weighted(values: pd.Series, weights: pd.Series) -> float:
    """Mean of ``values`` over the cases, weighted by case probability where given."""
    known = values.notna()
    if not known.any():
        return float("nan")
    w = weights[known].fillna(0.0).to_numpy()
    v = values[known].to_numpy()
    return float(np.average(v, weights=w)) if w.sum() > 0 else float(v.mean())


def _oe(frame: pd.DataFrame, prefix: str) -> pd.Series:
    """Oil equivalents of the four volume columns; missing if none is given."""
    parts = [
        f"{prefix}_oil_main",
        f"{prefix}_oil_assoc",
        f"{prefix}_gas_main",
        f"{prefix}_gas_assoc",
    ]
    return frame[parts].sum(axis=1, min_count=1)


@cache
def prospects() -> pd.DataFrame:
    """One row per drilled prospect: the pre-drill prognosis beside the result.

    Prognosis volumes and parameters are probability-weighted means over the
    cases of the prospect. The low-high range is kept only for prospects with
    a single case. Columns ending ``_prog`` are pre-drill, ``_res`` post-drill.
    """
    rows = prognosis_rows()
    numeric = list(VOLUME_COLUMNS.values()) + list(PARAMETER_COLUMNS.values())
    prognosis = rows[rows["kind"] == "PROGNOSIS"]
    has_content = prognosis[["p", *numeric]].notna().any(axis=1)
    prognosis = prognosis[has_content]
    result = rows[rows["kind"] == "RESULT"].set_index(["well", "prospect"])

    records = []
    for (well, prospect), cases in prognosis.groupby(["well", "prospect"], sort=False):
        p = cases["p"].to_numpy(dtype=float)
        first = cases.sort_values("case_priority", na_position="last").iloc[0]
        record = {
            "well": well,
            "prospect": prospect,
            "spud_year": first["spud_year"],
            "prospect_priority": first["prospect_priority"],
            "cases": len(cases),
            "p": discovery_probability(p),
            "p_first_case": first["p"],
            "p_max": np.nanmax(p) if np.isfinite(p).any() else np.nan,
            "phase_prog": first["phase"],
            "fractile_min": first["fractile_min"] if len(cases) == 1 else np.nan,
            "fractile_max": first["fractile_max"] if len(cases) == 1 else np.nan,
            "central": first["central"],
        }
        for name in numeric:
            record[f"{name}_prog"] = _weighted(cases[name], cases["p"])
        records.append(record)
    table = pd.DataFrame(records).set_index(["well", "prospect"])

    outcome = result[["discovery", "surprise", "phase", *numeric]].rename(
        columns={"phase": "phase_res", **{name: f"{name}_res" for name in numeric}}
    )
    table = table.join(outcome, how="left").reset_index()
    for stage in ("prog", "res"):
        for prefix in ("ip", "rec"):
            frame = table[[c for c in table.columns if c.endswith(f"_{stage}")]]
            frame.columns = [c.removesuffix(f"_{stage}") for c in frame.columns]
            table[f"{prefix}_oe_{stage}"] = _oe(frame, prefix)
    return table


@cache
def resource_account() -> pd.DataFrame:
    """Reserves per field and year from ``RCB_reserves.xlsx``, 1990-2021 (1996 is missing).

    Oil and gas originally recoverable, as in the year-end resource accounts.
    The rows labelled 2020 and 2021 are exchanged in the file: for 2004-2019
    its values equal Sodir's ``field_reserves`` of the same year, while its
    2020 rows equal Sodir's 2021 and its 2021 rows Sodir's 2020. The labels
    are put right here.
    """
    account = pd.read_excel(study_data() / "RCB_reserves.xlsx")
    account["year"] = account["year"].replace({2020: 2021, 2021: 2020})
    return account


def sodir_reserves() -> pd.DataFrame:
    """Sodir's ``field_reserves`` as exported for the expert study: one row per field and year."""
    table = pd.read_excel(study_data() / "field_reserves (1).xlsx")
    table.columns = [c.replace("\n", "") for c in table.columns]
    return pd.DataFrame(
        {
            "field_id": table["NPDID for felt"],
            "year": table["Versjon"],
            "oil": table["Oppr. utvinnbar olje [mill Sm3]"],
            "gas": table["Oppr. utvinnbar gass [mrd Sm3]"],
            "oe": table["Oppr. utvinnbar ekv. [mill Sm3 o.e]"],
        }
    )


@cache
def fields() -> pd.DataFrame:
    """One row per field: status, discovery wellbore, first PDO, estimates and outcome.

    ``fid_*`` is the reserves estimate of the resource account for the year the
    first PDO was approved (the year after, or the year before, if that year
    is missing); ``fid_gap`` is that year minus the approval year and is
    missing when no account lies within one year. ``final_*`` is the latest
    Sodir estimate of what is originally recoverable, and ``in_place_*`` the
    latest Sodir estimate of volumes originally in place.
    """
    folder = study_data()
    master = pd.read_excel(folder / "2026_npd_field.xlsx")
    table = pd.DataFrame(
        {
            "field_id": master["NPDID for felt"],
            "field": master["Feltnavn"].astype(str).str.strip(),
            "status": master["Dagens status"],
            "discovery_well": master["Funnbrønnbane"].astype(str).str.strip(),
            "area": master["Hovedområde"],
        }
    ).set_index("field_id")

    pdo = pd.read_excel(folder / "field_pdo_hst.xlsx")
    pdo["approved"] = pd.to_datetime(pdo["Dato PUD godkjent"], errors="coerce")
    pdo["type"] = pdo["Type"].astype(str).str.strip()
    first = pdo.sort_values("approved").drop_duplicates("NPDID felt").set_index("NPDID felt")
    table["approved"] = first["approved"]
    table["first_approval_type"] = first["type"]

    account = resource_account()
    estimates = []
    for field_id, approved in table["approved"].dropna().items():
        years = account[account["field_id"] == field_id].set_index("year")
        for gap in (0, 1, -1):
            year = approved.year + gap
            if year in years.index:
                row = years.loc[year]
                estimates.append((field_id, gap, row["oil_reserves"], row["gas_reserves"]))
                break
    fid = pd.DataFrame(estimates, columns=["field_id", "fid_gap", "fid_oil", "fid_gas"])
    table = table.join(fid.set_index("field_id"))
    table["fid_oe"] = table["fid_oil"] + table["fid_gas"]

    reserves = sodir_reserves()
    latest = reserves.sort_values("year").drop_duplicates("field_id", keep="last")
    latest = latest.set_index("field_id")
    table["final_oil"] = latest["oil"]
    table["final_gas"] = latest["gas"]
    table["final_oe"] = table["final_oil"] + table["final_gas"]
    table["final_version"] = latest["year"]

    in_place = pd.read_excel(folder / "field_in_place_volumes.xlsx")
    in_place.columns = [c.replace("\n", "") for c in in_place.columns]
    in_place = in_place.set_index("NPDID for felt")
    table["in_place_oil"] = (
        in_place["Oppr. tilst. olje [mill Sm3]"] + in_place["Oppr. tilst. ass. væske [mill Sm3]"]
    )
    table["in_place_gas"] = (
        in_place["Oppr. tilst. ass. gass [mrd Sm3]"] + in_place["Oppr. tilst. fri gass [mrd Sm3]"]
    )
    table["in_place_oe"] = table["in_place_oil"] + table["in_place_gas"]
    return table.reset_index()


@cache
def production_yearly() -> pd.DataFrame:
    """Net production per field and calendar year (the expert's export)."""
    raw = pd.read_excel(study_data() / "field_production_yearly.xlsx")
    raw.columns = [c.replace("\n", "") for c in raw.columns]
    return pd.DataFrame(
        {
            "field_id": raw["NPDID informasjons bærer"],
            "field": raw["Felt (Funn)"].astype(str).str.strip().str.upper(),
            "year": raw["År"].astype(int),
            "oil": raw["Netto – olje [mill Sm3]"],
            "gas": raw["Netto – gass [mrd Sm3]"],
            "oe": raw["Netto – oljeekvivalenter [mill Sm3]"],
        }
    )


@cache
def production_monthly() -> pd.DataFrame:
    """Net production per field and month, from the Sodir snapshot of the same date.

    A few months are slightly negative (later corrections booked by Sodir), so a
    field's cumulative production can dip.
    """
    snapshot = sodir.latest(data_dir() / "sodir")
    rows = sodir.read_table("field_production_monthly", snapshot)
    table = pd.DataFrame(rows)
    return pd.DataFrame(
        {
            "field_id": table["prfNpdidInformationCarrier"].astype(int),
            "month": pd.PeriodIndex.from_fields(
                year=table["prfYear"].astype(int), month=table["prfMonth"].astype(int), freq="M"
            ),
            "oil": table["prfPrdOilNetMillSm3"].astype(float),
            "gas": table["prfPrdGasNetBillSm3"].astype(float),
        }
    ).sort_values(["field_id", "month"], ignore_index=True)
