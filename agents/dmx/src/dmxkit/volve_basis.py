"""Volve, concept selection 2005: the volume basis, as stated and as calibrated.

The PDO's estimate of oil in place is rebuilt from its published percentiles,
then recalibrated with the reference class of undrilled prognoses
(``rcfkit.inplace``) for the part of it that no well had tested. Both bases
are carried through the PDO's own relations between oil in place, reserves
and value, so that the only thing that differs is the volume basis.

Percentiles follow the PDO: P90 is the low case, P10 the high case.
Volumes in million Sm3; values in million NOK of 2005, after tax at 8 %.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache

import numpy as np
from scipy import stats as scipy_stats

from rcfkit import inplace
from syskit import facts

DECISION_YEAR = 2005
DRAWS = 400_000
SEED = 2005
Z90 = scipy_stats.norm.ppf(0.9)
QUANTILES = {"p90": 0.10, "p50": 0.50, "p10": 0.90}  # PDO name -> share of outcomes below


@dataclass(frozen=True)
class Lognormal:
    """A lognormal distribution fixed by its P90 (low) and P10 (high)."""

    p90: float
    p10: float

    @property
    def median(self) -> float:
        return float(np.sqrt(self.p90 * self.p10))

    @property
    def sigma(self) -> float:
        return float(np.log(self.p10 / self.p90) / (2 * Z90))

    @property
    def mean(self) -> float:
        return float(self.median * np.exp(self.sigma**2 / 2))

    def from_normal(self, z: np.ndarray) -> np.ndarray:
        return self.median * np.exp(self.sigma * z)

    def cdf(self, x: float) -> float:
        return float(scipy_stats.norm.cdf(np.log(x / self.median) / self.sigma))


def interpolate(x: np.ndarray | float, xs: tuple[float, ...], ys: tuple[float, ...]) -> np.ndarray:
    """Straight lines through the points, continued with the end slopes outside them."""
    x = np.asarray(x, dtype=float)
    result = np.interp(x, xs, ys)
    low = (ys[1] - ys[0]) / (xs[1] - xs[0])
    high = (ys[-1] - ys[-2]) / (xs[-1] - xs[-2])
    result = np.where(x < xs[0], ys[0] + low * (x - xs[0]), result)
    return np.where(x > xs[-1], ys[-1] + high * (x - xs[-1]), result)


@cache
def pdo() -> dict:
    """What the PDO states: volumes by area, reserves, value, and the cost of two wells."""
    f = facts.read("pud2005")

    def area(name: str) -> dict[str, float]:
        keys = ("base", "mean", "p90", "p50", "p10", "sd")
        return {k: float(f[f"pud2005.stooip.t34.{name}.{k}"]) for k in keys}

    value = {k: float(f[f"pud2005.npv.after_tax_8.{k}"]) for k in ("p90_profile", "expected_price")}
    value |= {
        k: float(f[f"pud2005.npv.after_tax_8.{k}"]) for k in ("p10_profile", "two_extra_wells")
    }
    value |= {k: float(f[f"pud2005.npv.after_tax_8.{k}"]) for k in ("low_price", "forward_price")}
    before = {
        k: float(f[f"pud2005.npv.before_tax_7.{k}"])
        for k in ("p90_profile", "expected_price", "p10_profile", "two_extra_wells")
    }
    prospects = {
        name: {k: float(f[f"pud2005.prospect.{name}.{k}"]) for k in ("probability", "resources")}
        for name in ("volve_south", "theta_south", "western_prospects")
    }
    return {
        "east": area("east"),
        "west": area("west"),
        "closure": area("closure"),
        "reserves": {
            k: float(f[f"pud2005.recoverable_oil.t45.{k}"]) for k in ("p90", "p50", "mean", "p10")
        },
        "npv": value,
        "npv_before_tax": before,
        "two_wells": value["expected_price"] - value["two_extra_wells"],
        "two_wells_before_tax": before["expected_price"] - before["two_extra_wells"],
        "prospects": prospects,
        "capacity_oil": float(f["pud2005.capacity.oil_capacity"]),
        "producers": int(f["pud2005.assumption.oil_producers_planned"]),
        "injectors": int(f["pud2005.assumption.water_injectors_planned"]),
        "well_slots": int(f["pud2005.assumption.well_slots"]),
        "life_months": float(f["pud2005.assumption.economic_production_period"]),
        "lease_years": float(f["pud2005.assumption.lease_period_committed"]),
    }


def reserves(in_place: np.ndarray | float) -> np.ndarray:
    """Recoverable oil for a volume in place, by the PDO's own three pairs of percentiles."""
    p = pdo()
    xs = tuple(p["closure"][k] for k in ("p90", "p50", "p10"))
    ys = tuple(p["reserves"][k] for k in ("p90", "p50", "p10"))
    return interpolate(in_place, xs, ys)


def value(recoverable: np.ndarray | float) -> np.ndarray:
    """Net present value after tax for a recoverable volume, by the PDO's three profile cases."""
    p = pdo()
    xs = (p["reserves"]["p90"], p["reserves"]["mean"], p["reserves"]["p10"])
    ys = (p["npv"]["p90_profile"], p["npv"]["expected_price"], p["npv"]["p10_profile"])
    return interpolate(recoverable, xs, ys)


def correlation() -> float:
    """Correlation of East and West that reproduces the PDO's P90 and P10 for the closure."""
    return 0.2


@cache
def draws() -> dict[str, np.ndarray]:
    """Monte Carlo draws of oil in place by area under the PDO basis.

    East and West are lognormal through their P90 and P10; their correlation
    is set so that the sum reproduces the PDO's closure percentiles.
    """
    p = pdo()
    rng = np.random.default_rng(SEED)
    rho = correlation()
    z = rng.multivariate_normal([0, 0], [[1, rho], [rho, 1]], DRAWS)
    east = Lognormal(p["east"]["p90"], p["east"]["p10"]).from_normal(z[:, 0])
    west = Lognormal(p["west"]["p90"], p["west"]["p10"]).from_normal(z[:, 1])
    return {"east": east, "west": west}


CLASSES = {
    "Discoveries on record at the end of 2004": {"spudded_before": DECISION_YEAR},
    "All discoveries to 2024": {},
    "All discoveries to 2024, phase as prognosed": {"phase_as_prognosed": True},
}
PRIMARY = "Discoveries on record at the end of 2004"
BASE_MODEL = "PDO range around the base model"  # the mildest recalibration; no class involved


def calibrated_west(name: str = PRIMARY, seed: int = SEED + 1) -> np.ndarray:
    """Oil in place in the West under the outside view.

    The West's stated uncertainty is that of a prognosis, so it is treated as
    one: the PDO's mean for it times the ratio of result to prognosis drawn
    from the reference class. ``BASE_MODEL`` instead keeps the PDO's
    distribution for the West and scales it so that its mean is the base
    model's volume, i.e. it only takes back what the uncertainty study added.
    """
    west = pdo()["west"]
    if name == BASE_MODEL:
        return draws()["west"] * west["base"] / west["mean"]
    ratios = inplace.prognosis_ratios(**CLASSES[name])
    rng = np.random.default_rng(seed)
    return west["mean"] * rng.choice(ratios, DRAWS)


def bases(name: str = PRIMARY) -> dict[str, dict[str, np.ndarray]]:
    """Draws of East, West and their sum under the PDO basis and the calibrated basis."""
    stated = draws()
    west = calibrated_west(name)
    return {
        "PDO": {**stated, "closure": stated["east"] + stated["west"]},
        "Calibrated": {"east": stated["east"], "west": west, "closure": stated["east"] + west},
    }


def describe(values: np.ndarray) -> dict[str, float]:
    result = {name: float(np.quantile(values, q)) for name, q in QUANTILES.items()}
    result["mean"] = float(values.mean())
    return result


def class_interval(name: str = PRIMARY, repeats: int = 300) -> dict[str, tuple[float, float]]:
    """90 % interval of the calibrated closure percentiles from resampling the class."""
    ratios = inplace.prognosis_ratios(**CLASSES[name])
    east = draws()["east"][:50_000]
    rng = np.random.default_rng(SEED + 2)
    rows = []
    for _ in range(repeats):
        resampled = rng.choice(ratios, len(ratios))
        west = pdo()["west"]["mean"] * rng.choice(resampled, len(east))
        rows.append(list(describe(east + west).values()))
    low, high = np.quantile(np.array(rows), [0.05, 0.95], axis=0)
    return {
        k: (float(a), float(b))
        for k, a, b in zip(("p90", "p50", "p10", "mean"), low, high, strict=True)
    }


def metrics(basis: dict[str, np.ndarray]) -> dict[str, float]:
    """What a volume basis implies for reserves and value, with all planned wells drilled."""
    p = pdo()
    closure = basis["closure"]
    recoverable = reserves(closure)
    npv = value(recoverable)
    zero = float(interpolate(0.0, tuple(value(np.array([5.0, 9.0]))), (5.0, 9.0)))
    return {
        **{f"in_place_{k}": v for k, v in describe(closure).items()},
        **{f"reserves_{k}": v for k, v in describe(recoverable).items()},
        **{f"npv_{k}": v for k, v in describe(npv).items()},
        "below_pdo_low_in_place": float(np.mean(closure < p["closure"]["p90"])),
        "below_pdo_low_reserves": float(np.mean(recoverable < p["reserves"]["p90"])),
        "loss": float(np.mean(npv < 0)),
        "break_even_reserves": zero,
        "west_share_of_mean": float(basis["west"].mean() / closure.mean()),
    }


def west_decision(basis: dict[str, np.ndarray]) -> dict[str, float]:
    """The well pair in the West: commit with the rest, or decide after appraising the West.

    The gain from the pair is the value of the reserves the West adds, less
    what the PDO gives as the effect of two wells on value. It is assumed that
    the West is drained only by its own pair, and that an appraisal tells the
    West's volume exactly; the cost of the appraisal is not known and is left
    out, so ``information`` is the most it could be worth.
    """
    wells = pdo()["two_wells"]
    east, west = basis["east"], basis["west"]
    with_pair = value(reserves(east + west))
    east_only = value(reserves(east)) + wells
    gain = with_pair - east_only
    commit, skip = float(with_pair.mean()), float(east_only.mean())
    staged = float(np.maximum(with_pair, east_only).mean())
    slope = float((value(reserves(21.0)) - value(reserves(20.0))).item())
    return {
        "commit": commit,
        "east_only": skip,
        "staged": staged,
        "information": staged - max(commit, skip),
        "pair_does_not_pay": float(np.mean(gain < 0)),
        "mean_gain": float(gain.mean()),
        "median_gain": float(np.median(gain)),
        "break_even_west": wells / slope,
        "value_per_volume": slope,
    }


def prospects(ratios: np.ndarray) -> dict[str, float]:
    """Risked volume in place of the prospects around Volve, as stated and after the class."""
    listed = pdo()["prospects"]
    risked = sum(v["probability"] * v["resources"] for v in listed.values())
    return {
        "stated": risked,
        "with_mean_ratio": risked * float(ratios.mean()),
        "with_median_ratio": risked * float(np.median(ratios)),
    }
