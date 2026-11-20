"""Statistics for comparing forecasts with outcomes.

Plain functions on arrays, so that each can be tested on numbers worked out
by hand.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

Z90 = 1.6448536269514722  # two-sided 90 % interval of the normal distribution


def wilson(successes: float, n: float, z: float = Z90) -> tuple[float, float]:
    """Wilson score interval for a proportion (90 % by default)."""
    if n == 0:
        return (0.0, 1.0)
    p = successes / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (max(0.0, centre - half), min(1.0, centre + half))


def reliability(p: np.ndarray, outcome: np.ndarray, edges: np.ndarray) -> list[dict[str, float]]:
    """Forecast probability against observed frequency in bins of the probability.

    A bin holds its lower edge: 0.30 belongs to 0.3-0.4. The small shift keeps
    that true for edges that are not exact in floating point.
    """
    index = np.clip(np.digitize(p + 1e-9, edges[1:-1]), 0, len(edges) - 2)
    rows = []
    for b in range(len(edges) - 1):
        inside = index == b
        n = int(inside.sum())
        if n == 0:
            continue
        hits = float(outcome[inside].sum())
        low, high = wilson(hits, n)
        rows.append(
            {
                "from": float(edges[b]),
                "to": float(edges[b + 1]),
                "n": n,
                "forecast": float(p[inside].mean()),
                "observed": hits / n,
                "low": low,
                "high": high,
            }
        )
    return rows


def brier(p: np.ndarray, outcome: np.ndarray) -> float:
    return float(np.mean((p - outcome) ** 2))


def brier_decomposition(p: np.ndarray, outcome: np.ndarray, edges: np.ndarray) -> dict[str, float]:
    """Murphy's decomposition: Brier score = reliability - resolution + uncertainty.

    Exact when all forecasts in a bin are equal; with spread inside the bins
    the three terms add up to the score only approximately.
    """
    base = float(outcome.mean())
    n = len(p)
    rel = sum(r["n"] * (r["forecast"] - r["observed"]) ** 2 for r in reliability(p, outcome, edges))
    res = sum(r["n"] * (r["observed"] - base) ** 2 for r in reliability(p, outcome, edges))
    return {
        "brier": brier(p, outcome),
        "reliability": rel / n,
        "resolution": res / n,
        "uncertainty": base * (1 - base),
        "base_rate": base,
    }


def logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def expit(x: np.ndarray) -> np.ndarray:
    return 1 / (1 + np.exp(-x))


def fit_recalibration(p: np.ndarray, outcome: np.ndarray) -> tuple[float, float]:
    """Intercept and slope of logit(observed) = a + b * logit(forecast), by Newton's method.

    A slope below one means the forecasts are spread too widely (high ones too
    high, low ones too low); a perfectly calibrated forecast has a = 0, b = 1.
    """
    x = np.column_stack([np.ones_like(p), logit(p)])
    beta = np.zeros(2)
    for _ in range(50):
        mu = expit(x @ beta)
        gradient = x.T @ (outcome - mu)
        hessian = (x * (mu * (1 - mu))[:, None]).T @ x
        step = np.linalg.solve(hessian, gradient)
        beta = beta + step
        if np.abs(step).max() < 1e-10:
            break
    return float(beta[0]), float(beta[1])


def recalibrate(p: np.ndarray, a: float, b: float) -> np.ndarray:
    return expit(a + b * logit(p))


def folds(n: int, k: int, seed: int = 0) -> list[np.ndarray]:
    """Indices of ``k`` random test folds that together cover ``range(n)``."""
    order = np.random.default_rng(seed).permutation(n)
    return [np.sort(part) for part in np.array_split(order, k)]


def bootstrap(
    statistic: Callable[..., float | np.ndarray],
    *arrays: np.ndarray,
    n: int = 2000,
    seed: int = 0,
    level: float = 0.90,
) -> tuple[np.ndarray, np.ndarray]:
    """Percentile interval of a statistic under resampling of cases with replacement."""
    rng = np.random.default_rng(seed)
    size = len(arrays[0])
    draws = []
    for _ in range(n):
        pick = rng.integers(0, size, size)
        draws.append(statistic(*(a[pick] for a in arrays)))
    draws = np.asarray(draws, dtype=float)
    tail = (1 - level) / 2
    return np.nanquantile(draws, tail, axis=0), np.nanquantile(draws, 1 - tail, axis=0)


def ratio_summary(forecast: np.ndarray, outcome: np.ndarray) -> dict[str, float]:
    """Outcome relative to forecast for pairs where both are positive."""
    ratio = outcome / forecast
    return {
        "n": int(len(ratio)),
        "median": float(np.median(ratio)),
        "geometric_mean": float(np.exp(np.mean(np.log(ratio)))),
        "mean": float(np.mean(ratio)),
        "of_totals": float(outcome.sum() / forecast.sum()),
        "q10": float(np.quantile(ratio, 0.10)),
        "q25": float(np.quantile(ratio, 0.25)),
        "q75": float(np.quantile(ratio, 0.75)),
        "q90": float(np.quantile(ratio, 0.90)),
        "share_below_forecast": float(np.mean(ratio < 1)),
        "share_within_factor_2": float(np.mean((ratio >= 0.5) & (ratio <= 2))),
        "share_below_tenth": float(np.mean(ratio < 0.1)),
    }


def coverage(low: np.ndarray, high: np.ndarray, outcome: np.ndarray) -> dict[str, float]:
    """Shares of outcomes below, inside and above a stated low-high range."""
    below = float(np.mean(outcome < low))
    above = float(np.mean(outcome > high))
    return {"n": int(len(outcome)), "below": below, "inside": 1 - below - above, "above": above}


def percentile_of(value: float, sample: np.ndarray) -> float:
    """Share of the sample at or below ``value`` (mid-rank for ties)."""
    sample = np.asarray(sample, dtype=float)
    return float((np.sum(sample < value) + 0.5 * np.sum(sample == value)) / len(sample))


def weighted_quantile(values: np.ndarray, weights: np.ndarray, q: float) -> float:
    """Quantile of a weighted sample, interpolating between the weighted mid-points."""
    order = np.argsort(values)
    values, weights = np.asarray(values, float)[order], np.asarray(weights, float)[order]
    position = (np.cumsum(weights) - 0.5 * weights) / weights.sum()
    return float(np.interp(q, position, values))


def pinball(quantiles: dict[float, float], outcome: float) -> float:
    """Mean quantile (pinball) loss of a set of forecast quantiles; lower is better.

    With quantiles at 10, 50 and 90 % this approximates the continuous ranked
    probability score of the forecast distribution.
    """
    losses = [
        (q * (outcome - value) if outcome >= value else (1 - q) * (value - outcome))
        for q, value in quantiles.items()
    ]
    return float(np.mean(losses))
