"""Plot data of the Volve PDO (``Volve_PUD_cmt.pdf``): production forecasts and cash flow.

    python -m dockit.pud_plots extract

writes one CSV per figure beside its cut-out in ``data/volve/reports/figs/``
and the workbook ``data/volve/reports/md/Volve_PUD_cmt.xlsx``, and prints the
checks against Table 4.5 of the document.

Figures 4.2, 4.3 and 4.4 are small pictures embedded in the PDF; their curves
are traced by colour. Figure 4.5 is drawn with vector shapes; its points are
read from the shapes. Figure 12.1 prints its values as labels.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
import pymupdf
from openpyxl import Workbook
from openpyxl.styles import Font

from dockit.plots import Axis, cluster_1d, despike, plot_area, trace, yearly_mean
from syskit.paths import data_dir, volve_data

PDF = "reports/Volve_PUD_cmt.pdf"
STEM = "Volve_PUD_cmt"
YEARS = (2007, 2017)
DAYS_PER_YEAR = 365.25

# Table 4.5, page 25: oil production per year in million Sm3 (read from the text layer).
# The table stops each case when the oil rate falls below 2100 Sm3/d.
TABLE_4_5 = {
    "mean": {2007: 1.53, 2008: 3.10, 2009: 2.96, 2010: 2.14, 2011: 1.25, 2012: 0.40},
    "p90": {2007: 1.44, 2008: 3.10, 2009: 2.83, 2010: 1.49, 2011: 0.10},
    "p50": {2007: 1.53, 2008: 3.10, 2009: 2.96, 2010: 2.13, 2011: 1.22, 2012: 0.40},
    "p10": {
        2007: 1.54, 2008: 3.10, 2009: 3.15, 2010: 2.82, 2011: 1.82, 2012: 1.25, 2013: 0.88,
        2014: 0.75,
    },
}  # fmt: skip
TABLE_4_5_TOTAL = {"mean": 11.40, "p90": 9.00, "p50": 11.35, "p10": 15.31}

# Figure 12.1, page 51: labels printed on the bars, million NOK nominal, before tax.
# The 2008 label is blurred and reads 2295 or 2296.
CASH_FLOW = {
    2005: -163, 2006: -800, 2007: -1398, 2008: 2295, 2009: 2356, 2010: 1218, 2011: 399,
    2012: -107.8,
}  # fmt: skip


def is_background(image: np.ndarray) -> np.ndarray:
    r, g, b = image[:, :, 0], image[:, :, 1], image[:, :, 2]
    return (np.abs(r - g) < 14) & (np.abs(g - b) < 14) & (r > 165) & (r < 215)


def is_magenta(image: np.ndarray) -> np.ndarray:
    r, g, b = image[:, :, 0], image[:, :, 1], image[:, :, 2]
    return (r > 150) & (b > 150) & (r - g > 70)


def is_navy(image: np.ndarray) -> np.ndarray:
    r, g, b = image[:, :, 0], image[:, :, 1], image[:, :, 2]
    return (b - np.maximum(r, g) > 28) & (r < 110)


def is_gridline(image: np.ndarray) -> np.ndarray:
    """Neutral pixels clearly darker than the plot background."""
    return (image.max(axis=2) - image.min(axis=2) < 25) & (image.max(axis=2) < 150)


def embedded_image(document: pymupdf.Document, page: int, box: tuple) -> np.ndarray:
    """The picture embedded on ``page`` whose bounding box is ``box`` (points), as RGB."""
    for info in document[page - 1].get_image_info(xrefs=True):
        if all(abs(a - b) <= 1.5 for a, b in zip(info["bbox"], box, strict=True)):
            pixmap = pymupdf.Pixmap(document, info["xref"])
            if pixmap.colorspace.n != 3 or pixmap.alpha:
                pixmap = pymupdf.Pixmap(pymupdf.csRGB, pixmap)
            shape = (pixmap.height, pixmap.width, 3)
            return np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(shape).astype(int)
    raise ValueError(f"no embedded picture at {box} on page {page}")


def gridline_axis(image: np.ndarray, area: tuple, minimum: float, step: float) -> Axis:
    """Value axis of a chart from its horizontal gridlines.

    The gridlines are the rows that are dark grey across the plot area; the
    lowest line of the plot area is ``minimum`` and consecutive gridlines are
    ``step`` apart. A straight line is fitted through all gridlines found.
    """
    left, top, right, bottom = area
    dark = is_gridline(image)[:, left : right + 1].mean(axis=1)
    rows = [row for row in range(top + 2, bottom - 1) if dark[row] > 0.45]
    lines = [float(np.mean(group)) for group in cluster_1d(np.array(rows, dtype=float), 2.5)]
    spacing = min(b - a for a, b in zip(lines, lines[1:], strict=False))
    ticks = [round((bottom - line) / spacing) for line in lines]
    slope, intercept = np.polyfit(lines, [minimum + tick * step for tick in ticks], 1)
    return Axis(0.0, intercept, 1.0, intercept + slope)


def raster_chart(image: np.ndarray, series: dict, minimum: float, step: float) -> dict:
    """Trace the series of a chart with a year axis from 2007 to 2017.

    ``series`` maps a name to (colour test, factor); the factor converts the
    left axis to the axis the series is plotted on.
    """
    area = plot_area(image, is_background, bridge=8)
    time = Axis(area[0], YEARS[0], area[2], YEARS[1])
    value = gridline_axis(image, area, minimum, step)
    result = {}
    for name, (test, factor) in series.items():
        columns, rows = trace(test(image), area)
        result[name] = (time.value(columns), value.value(despike(rows)) * factor)
    return result


def figure_4_5(document: pymupdf.Document) -> dict[str, dict[int, float]]:
    """Annual oil production (million Sm3) and cumulative, per case, from the vector shapes."""
    left, right, top, bottom = 112.6, 362.7, 175.0, 367.3  # plot frame on page 25, points
    centres = left + (np.arange(11) + 0.5) * (right - left) / 11
    rate, cumulative = Axis(bottom, 0.0, top, 3.5), Axis(bottom, 0.0, top, 18.0)
    points: dict[tuple, list] = {}
    for drawing in document[24].get_drawings():
        if drawing["type"] != "f":
            continue
        colour = tuple(round(c, 2) for c in drawing["fill"])
        for item in drawing["items"]:
            for part in item[1:]:
                if isinstance(part, pymupdf.Point):
                    points.setdefault(colour, []).append((part.x, part.y))

    def clusters(colour: tuple, index: int) -> list[float]:
        array = np.array(points[colour])
        inside = (array[:, 1] > top - 2) & (array[:, 1] < bottom + 2)
        ys = array[inside & (np.abs(array[:, 0] - centres[index]) < 2.0), 1]
        return [float(group.mean()) for group in cluster_1d(ys, 8.0)] if ys.size else []

    def single(colour: tuple, axis: Axis) -> dict[int, float]:
        found = {YEARS[0] + i: clusters(colour, i) for i in range(11)}
        return {year: float(axis.value(np.mean(ys))) for year, ys in found.items() if ys}

    def shared(colour: tuple) -> tuple[dict[int, float], dict[int, float]]:
        """Rate and cumulative drawn in one colour: the cumulative never decreases."""
        rates, totals, previous = {}, {}, -1.0
        for index in range(11):
            ys = clusters(colour, index)
            values = sorted(float(cumulative.value(y)) for y in ys)
            total = next(v for v in values if v >= previous - 0.05)
            rest = [y for y in ys if abs(float(cumulative.value(y)) - total) > 1e-9]
            totals[YEARS[0] + index] = previous = total
            if rest:
                rates[YEARS[0] + index] = float(rate.value(max(rest)))
        return rates, totals

    mean_rate, mean_total = shared((1.0, 0.25, 1.0))
    p10_rate, p10_total = shared((1.0, 0.99, 0.0))
    return {
        "p90": single((0.02, 0.09, 0.58), rate),
        "mean": mean_rate,
        "p50": single((0.0, 0.99, 1.0), rate),
        "p10": p10_rate,
        "p90 cumulative": single((0.58, 0.13, 0.57), cumulative),
        "mean cumulative": mean_total,
        "p50 cumulative": single((0.06, 0.18, 1.0), cumulative),
        "p10 cumulative": p10_total,
    }


def extract() -> dict:
    """Read all plot data of the document."""
    document = pymupdf.open(volve_data() / PDF)
    fig42 = raster_chart(
        embedded_image(document, 23, (70.9, 417.2, 422.4, 640.9)),
        {
            "oil rate (Sm3/d)": (is_magenta, 1.0),
            "cumulative oil (million Sm3)": (is_navy, 16 / 9000),
        },
        0.0,
        1000.0,
    )
    fig43 = raster_chart(
        embedded_image(document, 24, (70.2, 85.2, 430.9, 318.0)),
        {
            "produced water rate (Sm3/d)": (is_navy, 1.0),
            "water injection rate (Sm3/d)": (is_magenta, 1.0),
        },
        0.0,
        2000.0,
    )
    fig44 = raster_chart(
        embedded_image(document, 24, (70.9, 446.3, 431.3, 681.0)),
        {"gas rate (million Sm3/d)": (is_navy, 1.0)},
        0.0,
        0.2,
    )
    return {"4.2": fig42, "4.3": fig43, "4.4": fig44, "4.5": figure_4_5(document)}


def yearly(series: tuple[np.ndarray, np.ndarray]) -> dict[int, float]:
    return yearly_mean(series[0], series[1], YEARS[0], YEARS[1] - 1)


def checks(data: dict) -> list[tuple[str, float, float]]:
    """Digitised values against values the document states, as (what, digitised, stated).

    The last year Table 4.5 gives for a case is cut short by the economic
    limit, so it is not compared.
    """
    rows = []
    oil = data["4.2"]["oil rate (Sm3/d)"]
    stated = TABLE_4_5["mean"]
    for year, rate in yearly(oil).items():
        if year >= 2008 and year + 1 in stated:
            volume = rate * DAYS_PER_YEAR / 1e6
            rows.append((f"Fig 4.2 oil volume {year} vs Table 4.5 mean", volume, stated[year]))
    plateau = float(np.percentile(oil[1], 97))
    rows.append(("Fig 4.2 plateau vs 9000 Sm3/d at 94 % regularity", plateau, 9000 * 0.94))
    for case in ("mean", "p90", "p50", "p10"):
        for year, value in TABLE_4_5[case].items():
            if year + 1 in TABLE_4_5[case] and year in data["4.5"][case]:
                rows.append((f"Fig 4.5 {case} {year} vs Table 4.5", data["4.5"][case][year], value))
    return rows


def write_csv(path: Path, header: tuple, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def tables(data: dict) -> dict[str, tuple[tuple, list]]:
    """Every sheet of the workbook as (header, rows)."""
    sheets: dict[str, tuple[tuple, list]] = {}
    for number, name in (("4.2", "fig4-2"), ("4.3", "fig4-3"), ("4.4", "fig4-4")):
        series = data[number]
        for label, (years, values) in series.items():
            short = label.split(" (")[0]
            rows = [
                (round(float(y), 3), round(float(v), 4)) for y, v in zip(years, values, strict=True)
            ]
            sheets[f"{name} {short}"[:31]] = (("year", label), rows)
        means = {label: yearly(s) for label, s in series.items()}
        span = sorted({year for m in means.values() for year in m})
        rows = [
            (year, *(round(m[year], 4) if year in m else "" for m in means.values()))
            for year in span
        ]
        sheets[f"{name} yearly mean"] = (("year", *means), rows)
    cases = ("p90", "mean", "p50", "p10")
    header = (
        "year",
        *(f"{c} (million Sm3 per year)" for c in cases),
        *(f"{c} cumulative (million Sm3)" for c in cases),
        *(f"Table 4.5 {c} (million Sm3)" for c in cases),
    )
    rows = []
    for year in range(YEARS[0], YEARS[1] + 1):
        digitised = [round(data["4.5"][c].get(year, np.nan), 3) for c in cases]
        totals = [round(data["4.5"][f"{c} cumulative"].get(year, np.nan), 2) for c in cases]
        stated = [TABLE_4_5[c].get(year, "") for c in cases]
        rows.append((year, *("" if np.isnan(v) else v for v in (*digitised, *totals)), *stated))
    sheets["fig4-5"] = (header, rows)
    running, rows = 0.0, []
    for year, value in CASH_FLOW.items():
        running += value
        rows.append((year, value, round(running, 1)))
    sheets["fig12-1"] = (("year", "cash flow before tax (million NOK nominal)", "cumulative"), rows)
    return sheets


TRACED = "digitised: curve traced by colour in the embedded picture"
INDEX = (
    ("sheet", "figure", "page", "content", "method", "resolution and checks"),
    (
        "fig4-2 …",
        "Figure 4.2",
        23,
        "Oil rate and cumulative oil production, 2007–2017",
        f"{TRACED} (352 x 224 pixels)",
        "about 0.04 year and 60 Sm3/d per pixel; yearly volumes checked against Table 4.5",
    ),
    (
        "fig4-3 …",
        "Figure 4.3",
        24,
        "Produced water rate and water injection rate, 2007–2017",
        f"{TRACED} (361 x 233 pixels)",
        "about 0.035 year and 105 Sm3/d per pixel; no table to check against",
    ),
    (
        "fig4-4 …",
        "Figure 4.4",
        24,
        "Gas production rate, 2007–2017",
        f"{TRACED} (361 x 235 pixels)",
        "about 0.035 year and 0.008 million Sm3/d per pixel; no table to check against",
    ),
    (
        "fig4-5",
        "Figure 4.5",
        25,
        "Oil production per year and cumulative for the p90, mean, p50 and p10 cases",
        "digitised: positions of the vector shapes at each year",
        "about 0.02 million Sm3 per year and 0.15 million Sm3 cumulative; checked against "
        "Table 4.5, which stops each case at the economic cut-off",
    ),
    (
        "fig12-1",
        "Figure 12.1",
        51,
        "Cash flow before tax per year, 2005–2012",
        "read: labels printed on the bars; cumulative computed",
        "the 2008 label is blurred: 2295 or 2296",
    ),
    (
        "",
        "Figure 3-7",
        20,
        "Contribution of each factor to the uncertainty (bar chart)",
        "not extracted",
        "not a production profile",
    ),
)


def write_outputs(data: dict) -> None:
    sheets = tables(data)
    figs = data_dir() / "volve" / "reports" / "figs"
    pages = {"fig4-2": 23, "fig4-3": 24, "fig4-4": 24, "fig4-5": 25, "fig12-1": 51}
    for name, (header, rows) in sheets.items():
        figure = name.split(" ")[0]
        suffix = name[len(figure) :].strip().replace(" ", "-")
        target = figs / f"{STEM}_p{pages[figure]:03d}_{figure}{'_' + suffix if suffix else ''}.csv"
        write_csv(target, header, rows)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "index"
    for row in INDEX:
        sheet.append(row)
    for name, (header, rows) in sheets.items():
        sheet = workbook.create_sheet(name)
        sheet.append(header)
        for row in rows:
            sheet.append(row)
    for sheet in workbook:
        for cell in sheet[1]:
            cell.font = Font(bold=True)
    workbook.save(data_dir() / "volve" / "reports" / "md" / f"{STEM}.xlsx")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("extract",))
    parser.parse_args(argv)
    data = extract()
    write_outputs(data)
    print(f"{'check':58s} {'digitised':>10s} {'stated':>8s} {'diff %':>7s}")
    for what, digitised, stated in checks(data):
        print(f"{what:58s} {digitised:10.3f} {stated:8.2f} {100 * (digitised / stated - 1):7.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
