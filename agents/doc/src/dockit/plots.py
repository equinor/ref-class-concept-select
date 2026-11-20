"""Reading data off plots: raster charts by colour, vector charts by their shapes.

Values obtained here are digitised, not read: they carry the resolution of the
picture and must be labelled as such and checked against any table of the
same data.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Axis:
    """Linear map from a position (pixel or point) to a value."""

    position_0: float
    value_0: float
    position_1: float
    value_1: float

    def value(self, position):
        scale = (self.value_1 - self.value_0) / (self.position_1 - self.position_0)
        return self.value_0 + (np.asarray(position, dtype=float) - self.position_0) * scale

    def position(self, value):
        scale = (self.position_1 - self.position_0) / (self.value_1 - self.value_0)
        return self.position_0 + (np.asarray(value, dtype=float) - self.value_0) * scale


def longest_run(flags: np.ndarray, *, bridge: int = 0) -> tuple[int, int]:
    """First and last index of the longest run of true values.

    Runs separated by at most ``bridge`` false values count as one run.
    """
    best, start, last_true = (0, -1), None, None
    for index, flag in enumerate(flags):
        if flag:
            if start is None or index - last_true - 1 > bridge:
                start = index
            last_true = index
            if last_true - start > best[1] - best[0]:
                best = (start, last_true)
    return best


def plot_area(
    image: np.ndarray, background: Callable[[np.ndarray], np.ndarray], *, bridge: int = 4
) -> tuple[int, int, int, int]:
    """Bounds (left, top, right, bottom) of the plot area, found from its background colour.

    ``background`` maps the RGB image to a boolean mask of background pixels.
    Rows and columns count as inside when at least a third of them is
    background; gridlines and steep curves interrupt the background for a few
    pixels, which ``bridge`` allows for.
    """
    mask = background(image)
    top, bottom = longest_run(mask.sum(axis=1) > image.shape[1] / 3, bridge=bridge)
    left, right = longest_run(mask.sum(axis=0) > image.shape[0] / 3, bridge=bridge)
    return left, top, right, bottom


def trace(mask: np.ndarray, area: tuple[int, int, int, int]) -> tuple[np.ndarray, np.ndarray]:
    """Follow a curve through a colour mask: for each column, the mean row of its pixels.

    Returns (columns, rows) for the columns inside ``area`` that contain the
    curve. Where a curve is steep a column holds a vertical stretch of it and
    the mean row is its middle.
    """
    left, top, right, bottom = area
    columns, rows = [], []
    for column in range(left, right + 1):
        hits = np.flatnonzero(mask[top : bottom + 1, column])
        if hits.size:
            columns.append(column)
            rows.append(top + hits.mean())
    return np.array(columns, dtype=float), np.array(rows)


def despike(values: np.ndarray, *, window: int = 5, threshold: float = 3.0) -> np.ndarray:
    """Replace isolated outliers by the median of their neighbourhood.

    A value further than ``threshold`` from the median of the ``window`` values
    around it is a stray pixel, not part of the curve. Steps and slopes are
    kept, because there the median moves with the curve.
    """
    half = window // 2
    padded = np.pad(values, half, mode="edge")
    medians = np.array([np.median(padded[i : i + window]) for i in range(values.size)])
    return np.where(np.abs(values - medians) > threshold, medians, values)


def yearly_mean(years: np.ndarray, values: np.ndarray, first: int, last: int) -> dict[int, float]:
    """Mean of a digitised series within each calendar year that it covers."""
    result = {}
    for year in range(first, last + 1):
        inside = (years >= year) & (years < year + 1)
        if inside.any():
            result[year] = float(values[inside].mean())
    return result


def cluster_1d(values: np.ndarray, gap: float) -> list[np.ndarray]:
    """Split sorted values into groups separated by more than ``gap``."""
    ordered = np.sort(values)
    breaks = np.flatnonzero(np.diff(ordered) > gap) + 1
    return np.split(ordered, breaks)
