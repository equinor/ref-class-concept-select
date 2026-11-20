"""Redraw the forecast charts of the Volve PDO from the extracted data.

    python -m dockit.pud_redraw draw

writes PNG files to ``agents/doc/out/figs/`` for use in the analysis document.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from dockit import pud_data, pud_facts  # noqa: E402
from dockit.pud_plots import CASH_FLOW  # noqa: E402
from syskit.paths import repo_root  # noqa: E402

COLOURS = {"P90": "#1e3a8a", "mean": "#c026d3", "P50": "#0891b2", "P10": "#ca8a04"}
OUT = "agents/doc/out/figs"


def _axes(title: str, y_label: str, x_label: str = "") -> tuple:
    figure, axes = plt.subplots(figsize=(8.2, 4.4), dpi=130)
    axes.set_title(title, loc="left", fontsize=12, fontweight="bold")
    axes.set_ylabel(y_label)
    axes.set_xlabel(x_label)
    axes.grid(axis="y", color="#e2e8f0", linewidth=0.8)
    axes.spines[["top", "right"]].set_visible(False)
    return figure, axes


def _save(figure, target_dir: Path, name: str) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / name
    figure.tight_layout()
    figure.savefig(path)
    plt.close(figure)
    return path


def draw(target_dir: Path) -> list[Path]:
    written = []
    profiles = pud_data.plan_profiles()

    figure, axes = _axes(
        "Oil production per year for the four cases (PDO Figure 4.5 and Table 4.5)",
        "million Sm3 per year",
    )
    for case, colour in COLOURS.items():
        years = sorted(profiles[case])
        axes.plot(
            years,
            [profiles[case][y] for y in years],
            color=colour,
            linewidth=1.6,
            linestyle="--",
            label=f"{case}, before cut-off (Figure 4.5, digitised)",
        )
        stated = pud_facts.OIL_PER_YEAR[case]
        axes.plot(
            list(stated),
            list(stated.values()),
            color=colour,
            marker="o",
            linewidth=0,
            markersize=6,
            label=f"{case}, Table 4.5",
        )
    axes.set_xticks(range(2007, 2018))
    axes.set_ylim(0, 3.6)
    axes.legend(fontsize=7.5, ncol=2, frameon=False)
    written.append(_save(figure, target_dir, "Volve_PUD_cmt_fig4-5_redrawn.png"))

    years, rate = pud_data.plan_series("Volve_PUD_cmt_p023_fig4-2_oil-rate.csv")
    cum_years, total = pud_data.plan_series("Volve_PUD_cmt_p023_fig4-2_cumulative-oil.csv")
    figure, axes = _axes("Oil rate and cumulative oil, mean case (PDO Figure 4.2)", "Sm3 per day")
    axes.plot(years, rate, color="#c026d3", linewidth=1.8, label="Oil rate (left axis)")
    twin = axes.twinx()
    twin.plot(cum_years, total, color="#1e3a8a", linewidth=1.8, label="Cumulative oil (right axis)")
    twin.set_ylabel("million Sm3")
    twin.set_ylim(0, 16)
    twin.spines[["top"]].set_visible(False)
    axes.set_ylim(0, 9000)
    axes.set_xlim(2007, 2017)
    lines = axes.get_lines() + twin.get_lines()
    axes.legend(
        lines, [line.get_label() for line in lines], fontsize=8, frameon=False, loc="center right"
    )
    written.append(_save(figure, target_dir, "Volve_PUD_cmt_fig4-2_redrawn.png"))

    figure, axes = _axes("Water produced and water injected (PDO Figure 4.3)", "Sm3 per day")
    for name, label, colour in (
        ("Volve_PUD_cmt_p024_fig4-3_water-injection-rate.csv", "Water injection rate", "#c026d3"),
        ("Volve_PUD_cmt_p024_fig4-3_produced-water-rate.csv", "Produced water rate", "#1e3a8a"),
    ):
        years, values = pud_data.plan_series(name)
        axes.plot(years, values, color=colour, linewidth=1.8, label=label)
    axes.set_ylim(0, 16000)
    axes.set_xlim(2007, 2017)
    axes.legend(fontsize=8, frameon=False)
    written.append(_save(figure, target_dir, "Volve_PUD_cmt_fig4-3_redrawn.png"))

    years, values = pud_data.plan_series("Volve_PUD_cmt_p024_fig4-4_gas-rate.csv")
    figure, axes = _axes("Gas production rate (PDO Figure 4.4)", "million Sm3 per day")
    axes.plot(years, values, color="#1e3a8a", linewidth=1.8)
    axes.set_ylim(0, 1.4)
    axes.set_xlim(2007, 2017)
    written.append(_save(figure, target_dir, "Volve_PUD_cmt_fig4-4_redrawn.png"))

    figure, axes = _axes("Cash flow before tax (PDO Figure 12.1)", "million NOK, nominal")
    years = list(CASH_FLOW)
    axes.bar(years, list(CASH_FLOW.values()), color="#15803d", label="Per year")
    running, totals = 0.0, []
    for value in CASH_FLOW.values():
        running += value
        totals.append(running)
    axes.plot(years, totals, color="#dc2626", linewidth=1.8, label="Cumulative")
    axes.axhline(0, color="#475569", linewidth=0.8)
    axes.legend(fontsize=8, frameon=False)
    written.append(_save(figure, target_dir, "Volve_PUD_cmt_fig12-1_redrawn.png"))
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("draw",))
    parser.parse_args(argv)
    for path in draw(repo_root() / OUT):
        print(f"written: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
