"""Compare an OPM Flow run of the Volve deck with the shipped Eclipse results.

    python -m simkit.compare init <flow-output-dir>       # grid and static properties
    python -m simkit.compare summary <flow-output-dir>    # field and well vectors over time
    python -m simkit.compare balance <flow-output-dir>    # material balance of each run

Each command prints a table and writes it as CSV into the Flow output directory.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

from syskit.paths import volve_data

DECK_DIR = "eclipse_model/sim_model_PPA-eclipse"
ECLIPSE_CASE = "VOLVE_2016"
FLOW_CASE = "VOLVE_2016_FLOW"

INIT_ARRAYS = (
    "PORV", "DEPTH", "DX", "DY", "DZ", "TOPS", "PORO", "NTG", "PERMX", "PERMY", "PERMZ",
    "TRANX", "TRANY", "TRANZ", "MULTX", "MULTY", "MULTZ", "PVTNUM", "SATNUM", "EQLNUM", "FIPNUM",
)  # fmt: skip
# Cumulative and state vectors only: rates change in steps at times the two
# simulators do not share, so interpolated rate differences are mostly artefacts.
FIELD_VECTORS = ("FOPT", "FWPT", "FGPT", "FWIT", "FPR", "FOIP", "FWIP", "FGIP")
WELL_VECTORS = ("WOPT", "WWPT", "WGPT", "WWIT")


def compare_arrays(name: str, eclipse: np.ndarray, flow: np.ndarray, tolerance: float) -> dict:
    """Describe how two arrays over the same cells differ.

    ``tolerance`` is relative to the larger magnitude of the pair; cells where
    both values are zero count as equal.
    """
    row = {"array": name, "cells": eclipse.size, "flow_cells": flow.size}
    if eclipse.size != flow.size:
        return row | {"differing": "", "max_abs_diff": "", "max_rel_diff": "", "sum_ratio": ""}
    difference = np.abs(flow - eclipse)
    scale = np.maximum(np.abs(eclipse), np.abs(flow))
    relative = np.divide(difference, scale, out=np.zeros_like(difference), where=scale > 0)
    total = float(eclipse.sum())
    return row | {
        "differing": int((relative > tolerance).sum()),
        "max_abs_diff": float(difference.max()),
        "max_rel_diff": float(relative.max()),
        "sum_ratio": float(flow.sum()) / total if total else "",
    }


def _init_array(init, name: str, active: np.ndarray) -> np.ndarray | None:
    if name not in init:
        return None
    values = np.asarray(init[name][0].numpy_view(), dtype=np.float64)
    return values[active] if values.size == active.size else values


def compare_init(eclipse_init: Path, flow_init: Path, tolerance: float = 1e-4) -> list[dict]:
    from resdata.resfile import ResdataFile

    eclipse, flow = ResdataFile(str(eclipse_init)), ResdataFile(str(flow_init))
    active_e = np.asarray(eclipse["PORV"][0].numpy_view()) > 0
    active_f = np.asarray(flow["PORV"][0].numpy_view()) > 0
    rows = [
        {
            "array": "active cells",
            "cells": int(active_e.sum()),
            "flow_cells": int(active_f.sum()),
            "differing": int((active_e != active_f).sum()),
        }
    ]
    for name in INIT_ARRAYS:
        a, b = _init_array(eclipse, name, active_e), _init_array(flow, name, active_f)
        if a is None or b is None:
            rows.append(
                {
                    "array": name,
                    "cells": "absent" if a is None else a.size,
                    "flow_cells": "absent" if b is None else b.size,
                }
            )
            continue
        rows.append(compare_arrays(name, a, b, tolerance))
    return rows


def compare_summary(eclipse_case: Path, flow_case: Path) -> list[dict]:
    """Compare vectors over the period both runs cover, at Eclipse's report times.

    Flow values are interpolated linearly in time onto Eclipse's times.
    """
    from resdata.summary import Summary

    eclipse, flow = Summary(str(eclipse_case)), Summary(str(flow_case))
    days_e, days_f = np.asarray(eclipse.days), np.asarray(flow.days)
    common = (days_e >= days_f[0]) & (days_e <= days_f[-1])
    keys = [k for k in FIELD_VECTORS if k in eclipse]
    for well in eclipse.wells():
        keys += [f"{v}:{well}" for v in WELL_VECTORS if f"{v}:{well}" in eclipse]
    rows = []
    for key in keys:
        if key not in flow:
            rows.append({"vector": key, "unit": eclipse.unit(key), "flow_last": "absent"})
            continue
        a = np.asarray(eclipse.numpy_vector(key), dtype=float)[common]
        b = np.interp(days_e[common], days_f, np.asarray(flow.numpy_vector(key), dtype=float))
        rows.append({"vector": key, "unit": eclipse.unit(key)} | vector_differences(a, b))
    rows.insert(
        0,
        {
            "vector": "days compared",
            "eclipse_last": float(days_e[common][-1]),
            "flow_last": float(days_f[-1]),
        },
    )
    return rows


def vector_differences(eclipse: np.ndarray, flow: np.ndarray) -> dict:
    """First and last values, and the differences over time relative to Eclipse's maximum."""
    scale = float(np.abs(eclipse).max())
    difference = np.abs(flow - eclipse)
    return {
        "eclipse_first": float(eclipse[0]),
        "flow_first": float(flow[0]),
        "eclipse_last": float(eclipse[-1]),
        "flow_last": float(flow[-1]),
        "last_diff_pct": 100 * (flow[-1] - eclipse[-1]) / eclipse[-1] if eclipse[-1] else "",
        "mean_diff_pct_of_max": 100 * float(difference.mean()) / scale if scale else "",
        "max_diff_pct_of_max": 100 * float(difference.max()) / scale if scale else "",
    }


def balance_error(in_place: np.ndarray, injected: np.ndarray, produced: np.ndarray) -> np.ndarray:
    """Fluid in place minus what the initial volume, injection and production account for."""
    return in_place - (in_place[0] + injected - produced)


def compare_balance(cases: dict[str, Path]) -> list[dict]:
    """Water and oil balance error of each run, in surface volumes."""
    from resdata.summary import Summary

    rows = []
    for name, case in cases.items():
        summary = Summary(str(case))

        def vector(key, summary=summary):
            return np.asarray(summary.numpy_vector(key), dtype=float)

        water = balance_error(vector("FWIP"), vector("FWIT"), vector("FWPT"))
        oil = balance_error(vector("FOIP"), np.zeros(len(summary.days)), vector("FOPT"))
        rows.append(
            {
                "run": name,
                "water_error_end_sm3": float(water[-1]),
                "water_error_max_sm3": float(np.abs(water).max()),
                "oil_error_end_sm3": float(oil[-1]),
                "oil_error_max_sm3": float(np.abs(oil).max()),
                "water_error_end_pct_of_injected": 100
                * float(water[-1])
                / float(vector("FWIT")[-1]),
                "oil_error_end_pct_of_produced": 100 * float(oil[-1]) / float(vector("FOPT")[-1]),
            }
        )
    return rows


def _format(value) -> str:
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def report(rows: list[dict], target: Path) -> None:
    columns = list(dict.fromkeys(key for row in rows for key in row))
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    table = [columns] + [[_format(row.get(c, "")) for c in columns] for row in rows]
    widths = [max(len(line[n]) for line in table) for n in range(len(columns))]
    for line in table:
        print("  ".join(cell.rjust(width) for cell, width in zip(line, widths, strict=True)))
    print(f"written: {target}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("init", "summary", "balance"))
    parser.add_argument("flow_dir", type=Path, help="directory holding the Flow output")
    args = parser.parse_args(argv)

    eclipse = volve_data() / DECK_DIR / ECLIPSE_CASE
    flow = args.flow_dir / FLOW_CASE
    try:
        if args.command == "init":
            rows = compare_init(eclipse.with_suffix(".INIT"), flow.with_suffix(".INIT"))
            report(rows, args.flow_dir / "compare_init.csv")
        elif args.command == "summary":
            report(compare_summary(eclipse, flow), args.flow_dir / "compare_summary.csv")
        else:
            rows = compare_balance({"eclipse": eclipse, "flow": flow})
            report(rows, args.flow_dir / "compare_balance.csv")
    except OSError as error:
        print(f"comparison failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
