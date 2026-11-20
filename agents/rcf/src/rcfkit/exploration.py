"""Exploration stage: pre-drill prognoses against drilling results.

Two questions per drilled prospect: was the stated probability of discovery
borne out, and how did the volume found compare with the volume prognosed?
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from rcfkit import data, stats

BINS = np.linspace(0.0, 1.0, 11)
ERAS = ((1989, 1999), (2000, 2009), (2010, 2024))
PARAMETERS = {
    "rock_volume": "Rock volume",
    "area": "Area",
    "hc_column": "Hydrocarbon column",
    "thickness": "Reservoir thickness",
    "net_gross": "Net-to-gross",
    "porosity": "Porosity",
    "hc_saturation": "Hydrocarbon saturation",
}


def probability_sample() -> pd.DataFrame:
    """Prospects with a stated probability of discovery and a recorded outcome."""
    table = data.prospects()
    return table[table["p"].notna() & table["discovery"].notna()].reset_index(drop=True)


def _calibration(p: np.ndarray, y: np.ndarray) -> dict:
    a, b = stats.fit_recalibration(p, y)
    variance = float(np.sum(p * (1 - p)))
    return {
        "n": int(len(p)),
        "discoveries": int(y.sum()),
        "mean_forecast": float(p.mean()),
        "observed_rate": float(y.mean()),
        "expected_discoveries": float(p.sum()),
        "z": float((y.sum() - p.sum()) / np.sqrt(variance)),
        "intercept": a,
        "slope": b,
        **stats.brier_decomposition(p, y, BINS),
    }


def cross_validated_brier(p: np.ndarray, y: np.ndarray, k: int = 10, seed: int = 0) -> dict:
    """Out-of-sample Brier scores: as stated, base rate only, and recalibrated."""
    stated = np.empty(len(p))
    base = np.empty(len(p))
    recal = np.empty(len(p))
    for test in stats.folds(len(p), k, seed):
        train = np.setdiff1d(np.arange(len(p)), test)
        a, b = stats.fit_recalibration(p[train], y[train])
        stated[test] = p[test]
        base[test] = y[train].mean()
        recal[test] = stats.recalibrate(p[test], a, b)
    scores = {
        "stated": stats.brier(stated, y),
        "base_rate": stats.brier(base, y),
        "recalibrated": stats.brier(recal, y),
    }
    scores["skill_stated"] = 1 - scores["stated"] / scores["base_rate"]
    scores["skill_recalibrated"] = 1 - scores["recalibrated"] / scores["base_rate"]
    return scores


def probability_results() -> dict:
    """Calibration of the pre-drill probability of discovery, per prospect."""
    sample = probability_sample()
    p, y = sample["p"].to_numpy(), sample["discovery"].to_numpy()
    result = {"all": _calibration(p, y), "bins": stats.reliability(p, y, BINS)}
    low, high = stats.bootstrap(lambda a, b: np.array(stats.fit_recalibration(a, b)), p, y, n=1000)
    result["all"]["intercept_ci"] = (float(low[0]), float(high[0]))
    result["all"]["slope_ci"] = (float(low[1]), float(high[1]))
    result["cross_validated"] = cross_validated_brier(p, y)

    groups = {}
    primary = sample["prospect_priority"].fillna(1) <= 1
    groups["Primary target of the well"] = primary
    groups["Secondary target"] = ~primary
    for first, last in ERAS:
        groups[f"Spudded {first}–{last}"] = sample["spud_year"].between(first, last)
    groups["One prognosis case"] = sample["cases"] == 1
    groups["Several prognosis cases"] = sample["cases"] > 1
    result["groups"] = {
        name: _calibration(p[mask.to_numpy()], y[mask.to_numpy()]) for name, mask in groups.items()
    }
    # How much the rule for prospects with several cases matters.
    result["case_rules"] = {
        name: _calibration(sample[column].to_numpy(), y)
        for name, column in (("first case only", "p_first_case"), ("largest case", "p_max"))
        if sample[column].notna().all()
    }
    return result


def well_level() -> dict:
    """The same data aggregated per well, two ways.

    ``mean`` is the expert study's rule (mean probability of the well's
    prospects against any discovery in the well, surprises included).
    ``any`` uses the probability of at least one discovery, taking the
    prospects as independent, against a discovery in a prognosed prospect.
    """
    rows = data.prognosis_rows()
    any_result = rows[rows["kind"] == "RESULT"].groupby("well")["discovery"].max()
    sample = probability_sample()
    wells = sample.groupby("well").agg(
        prospects=("p", "size"),
        mean=("p", "mean"),
        any=("p", lambda s: 1 - np.prod(1 - s.to_numpy())),
        found=("discovery", "max"),
    )
    wells["found_incl_surprise"] = any_result.reindex(wells.index)
    result = {}
    for name, column, outcome in (
        ("mean", "mean", "found_incl_surprise"),
        ("any", "any", "found"),
    ):
        p, y = wells[column].to_numpy(), wells[outcome].to_numpy()
        result[name] = {**_calibration(p, y), "bins": stats.reliability(p, y, BINS)}
    result["wells_with_several_prospects"] = int((wells["prospects"] > 1).sum())
    result["wells"] = int(len(wells))
    return result


def volume_sample(kind: str = "ip") -> pd.DataFrame:
    """Discovered prospects with a positive prognosed and a positive resulting volume.

    ``kind`` is ``ip`` for volumes in place or ``rec`` for recoverable volumes.
    """
    table = data.prospects()
    prognosis, result = table[f"{kind}_oe_prog"], table[f"{kind}_oe_res"]
    keep = (table["discovery"] == 1) & (prognosis > 0) & (result > 0)
    sample = table[keep].copy()
    sample["forecast"], sample["outcome"] = prognosis[keep], result[keep]
    sample["ratio"] = sample["outcome"] / sample["forecast"]
    return sample.reset_index(drop=True)


def range_sample() -> pd.DataFrame:
    """Discoveries whose prognosis gave a P90-P10 range for the phase that was found.

    Only prospects with one prognosis case and fractiles 0.9 and 0.1 are used,
    so that the stated range is meant to hold the outcome 80 % of the time.
    """
    table = data.prospects()
    table = table[
        (table["discovery"] == 1) & (table["fractile_min"] == 0.9) & (table["fractile_max"] == 0.1)
    ]
    parts = []
    for phase in ("oil", "gas"):
        low, high = table[f"ip_{phase}_min_prog"], table[f"ip_{phase}_max_prog"]
        central = table[f"ip_{phase}_main_prog"]
        outcome = table[f"ip_{phase}_main_res"]
        keep = (low > 0) & (high > low) & (central > 0) & (outcome > 0)
        part = table.loc[keep, ["well", "prospect", "spud_year"]].copy()
        part["phase"] = phase
        part["low"], part["central"], part["high"] = low[keep], central[keep], high[keep]
        part["outcome"] = outcome[keep]
        parts.append(part)
    return pd.concat(parts, ignore_index=True)


def calibration_factors(sample: pd.DataFrame) -> dict[str, float]:
    """Multipliers that make a prognosis range hold 80 % of outcomes (Nesvold & Bratvold, Eq. 5-6).

    ``a_mean`` and ``c_mean`` scale the central estimate into a low and a high
    value; ``a_low`` and ``c_high`` scale the stated low and high values;
    ``b`` scales the central estimate so that the median outcome equals it.
    """
    outcome = sample["outcome"].to_numpy()
    return {
        "a_mean": float(np.quantile(outcome / sample["central"], 0.10)),
        "b": float(np.median(outcome / sample["central"])),
        "c_mean": float(np.quantile(outcome / sample["central"], 0.90)),
        "a_low": float(np.quantile(outcome / sample["low"], 0.10)),
        "c_high": float(np.quantile(outcome / sample["high"], 0.90)),
    }


def cross_validated_coverage(sample: pd.DataFrame, k: int = 10, seed: int = 0) -> dict:
    """Out-of-sample coverage of the range as stated and after the two calibrations."""
    low = np.empty((2, len(sample)))
    high = np.empty((2, len(sample)))
    for test in stats.folds(len(sample), k, seed):
        train = np.setdiff1d(np.arange(len(sample)), test)
        f = calibration_factors(sample.iloc[train])
        part = sample.iloc[test]
        low[0, test], high[0, test] = f["a_mean"] * part["central"], f["c_mean"] * part["central"]
        low[1, test], high[1, test] = f["a_low"] * part["low"], f["c_high"] * part["high"]
    outcome = sample["outcome"].to_numpy()
    return {
        "stated": stats.coverage(sample["low"].to_numpy(), sample["high"].to_numpy(), outcome),
        "from_central": stats.coverage(low[0], high[0], outcome),
        "from_range": stats.coverage(low[1], high[1], outcome),
    }


def volume_results() -> dict:
    """Volumes found against volumes prognosed, for the prospects that were discoveries."""
    result = {}
    for kind in ("ip", "rec"):
        sample = volume_sample(kind)
        f, o = sample["forecast"].to_numpy(), sample["outcome"].to_numpy()
        summary = stats.ratio_summary(f, o)
        low, high = stats.bootstrap(lambda a, b: np.median(b / a), f, o)
        summary["median_ci"] = (float(low), float(high))
        low, high = stats.bootstrap(lambda a, b: b.sum() / a.sum(), f, o)
        summary["of_totals_ci"] = (float(low), float(high))
        result[kind] = summary
    sample = volume_sample("ip")
    result["eras"] = {
        f"{first}–{last}": stats.ratio_summary(
            *(
                sample.loc[sample["spud_year"].between(first, last), c].to_numpy()
                for c in ("forecast", "outcome")
            )
        )
        for first, last in ERAS
    }
    labelled_mean = sample["central"].isin(["MEAN"])
    result["labelled_mean"] = stats.ratio_summary(
        sample.loc[labelled_mean, "forecast"].to_numpy(),
        sample.loc[labelled_mean, "outcome"].to_numpy(),
    )

    ranges = range_sample()
    result["range"] = cross_validated_coverage(ranges)
    result["range_factors"] = calibration_factors(ranges)
    result["range_width"] = float(np.median(ranges["high"] / ranges["low"]))
    width_needed = result["range_factors"]["c_mean"] / result["range_factors"]["a_mean"]
    result["range_width_needed"] = float(width_needed)
    return result


def portfolio() -> dict:
    """Risked prognosis against delivery, summed over all drilled prospects.

    The expected volume of a prospect is its probability of discovery times
    its prognosed volume in place; the delivered volume is what the result
    records for it (zero if dry).
    """
    table = data.prospects()
    table = table[table["p"].notna() & table["discovery"].notna() & (table["ip_oe_prog"] > 0)]
    expected = table["p"] * table["ip_oe_prog"]
    delivered = table["ip_oe_res"].where(table["discovery"] == 1, 0.0).fillna(0.0)
    unknown = int(((table["discovery"] == 1) & table["ip_oe_res"].isna()).sum())
    low, high = stats.bootstrap(
        lambda e, d: d.sum() / e.sum(), expected.to_numpy(), delivered.to_numpy()
    )
    return {
        "n": int(len(table)),
        "expected": float(expected.sum()),
        "delivered": float(delivered.sum()),
        "ratio": float(delivered.sum() / expected.sum()),
        "ratio_ci": (float(low), float(high)),
        "unrisked": float(table["ip_oe_prog"].sum()),
        "discoveries_without_volume": unknown,
    }


def phase_results() -> dict:
    """Whether discoveries held the phase that was prognosed as the main one."""
    table = data.prospects()
    table = table[(table["discovery"] == 1) & (table["cases"] == 1)]

    def main(stage: str) -> pd.Series:
        oil, gas = table[f"ip_oil_main_{stage}"].fillna(0), table[f"ip_gas_main_{stage}"].fillna(0)
        phase = pd.Series("none", index=table.index)
        phase[(oil > 0) & (oil >= gas)] = "oil"
        phase[(gas > 0) & (gas > oil)] = "gas"
        return phase

    prognosed, found = main("prog"), main("res")
    known = (prognosed != "none") & (found != "none")
    cross = pd.crosstab(prognosed[known], found[known])
    return {
        "n": int(known.sum()),
        "same": float((prognosed[known] == found[known]).mean()),
        "table": {a: {b: int(cross.loc[a, b]) for b in cross.columns} for a in cross.index},
    }


def parameter_results() -> list[dict]:
    """Result over prognosis for the factors of the volume equation, discoveries only."""
    table = data.prospects()
    table = table[table["discovery"] == 1].copy()
    for stage in ("prog", "res"):
        table[f"hc_saturation_{stage}"] = 1 - table[f"water_saturation_{stage}"]
    rows = []
    for name, label in PARAMETERS.items():
        prognosis, result = table[f"{name}_prog"], table[f"{name}_res"]
        keep = (prognosis > 0) & (result > 0)
        ratio = (result[keep] / prognosis[keep]).to_numpy()
        low, high = stats.bootstrap(np.median, ratio)
        rows.append(
            {
                "parameter": label,
                "n": int(keep.sum()),
                "median": float(np.median(ratio)),
                "median_low": float(low),
                "median_high": float(high),
                "q10": float(np.quantile(ratio, 0.1)),
                "q90": float(np.quantile(ratio, 0.9)),
                "share_below": float(np.mean(ratio < 1)),
            }
        )
    return rows
