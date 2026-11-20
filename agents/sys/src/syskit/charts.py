"""Charts described once and drawn twice: interactive for web pages, PNG for Markdown.

A chart is a list of series over shared axes. ``Chart.plotly()`` gives the
interactive figure and ``Chart.png()`` writes the same chart as an image, so a
report's Markdown and web versions cannot drift apart.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

BLUE, ORANGE, GREEN, GREY, INK = "#1d4ed8", "#c2410c", "#15803d", "#64748b", "#0f172a"
FONT = "system-ui, -apple-system, Segoe UI, Roboto, sans-serif"


@dataclass
class Series:
    """One series. ``kind`` is line, markers, band, bar or errorbar.

    ``band`` fills between ``low`` and ``high``; ``errorbar`` draws markers at
    ``y`` with whiskers from ``low`` to ``high``. ``labels`` are shown on hover
    in the interactive chart.
    """

    kind: str
    x: Sequence
    y: Sequence = ()
    name: str = ""
    color: str = BLUE
    low: Sequence = ()
    high: Sequence = ()
    dash: bool = False
    width: float = 2.0
    size: float = 7.0
    opacity: float = 1.0
    labels: Sequence[str] = ()
    connect: bool = False  # errorbar: join the markers with a line


@dataclass
class Chart:
    name: str
    title: str
    x_title: str
    y_title: str
    series: list[Series] = field(default_factory=list)
    log_x: bool = False
    log_y: bool = False
    x_range: tuple[float, float] | None = None
    y_range: tuple[float, float] | None = None
    height: int = 460

    def plotly(self):
        import math

        import plotly.graph_objects as go

        figure = go.Figure()
        for s in self.series:
            x, y = list(s.x), list(s.y)
            line = {"color": s.color, "width": s.width, "dash": "dash" if s.dash else "solid"}
            hover = {"text": list(s.labels), "hoverinfo": "text+x+y"} if s.labels else {}
            if s.kind == "line":
                figure.add_scatter(x=x, y=y, mode="lines", name=s.name, line=line, **hover)
            elif s.kind == "markers":
                marker = {"color": s.color, "size": s.size, "opacity": s.opacity}
                figure.add_scatter(x=x, y=y, mode="markers", name=s.name, marker=marker, **hover)
            elif s.kind == "band":
                rgb = tuple(int(s.color[i : i + 2], 16) for i in (1, 3, 5))
                fill = f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, {0.16 * s.opacity})"
                edge = {"width": 0, "color": s.color}
                figure.add_scatter(
                    x=x, y=list(s.high), mode="lines", line=edge, showlegend=False, hoverinfo="skip"
                )
                figure.add_scatter(
                    x=x, y=list(s.low), mode="lines", line=edge, fill="tonexty", fillcolor=fill,
                    name=s.name, hoverinfo="skip",
                )  # fmt: skip
            elif s.kind == "bar":
                figure.add_bar(x=x, y=y, name=s.name, marker={"color": s.color})
            elif s.kind == "errorbar":
                error = {
                    "type": "data",
                    "symmetric": False,
                    "array": [h - v for h, v in zip(s.high, y, strict=True)],
                    "arrayminus": [v - lo for lo, v in zip(s.low, y, strict=True)],
                    "color": s.color,
                    "thickness": 1.4,
                }
                figure.add_scatter(
                    x=x, y=y, mode="lines+markers" if s.connect else "markers", name=s.name,
                    marker={"color": s.color, "size": s.size}, line=line, error_y=error, **hover,
                )  # fmt: skip
            else:
                raise ValueError(f"unknown series kind: {s.kind}")

        def axis(title: str, log: bool, limits: tuple[float, float] | None) -> dict:
            result: dict = {"title": title, "type": "log" if log else "linear"}
            if limits:
                result["range"] = [math.log10(v) for v in limits] if log else list(limits)
            return result

        figure.update_layout(
            title={"text": self.title, "font": {"size": 16}, "x": 0, "xanchor": "left"},
            template="plotly_white",
            font={"family": FONT, "size": 13},
            margin={"l": 64, "r": 24, "t": 48, "b": 110},
            height=self.height,
            legend={"orientation": "h", "y": -0.18, "yanchor": "top", "x": 0, "xanchor": "left"},
            xaxis=axis(self.x_title, self.log_x, self.x_range),
            yaxis=axis(self.y_title, self.log_y, self.y_range),
            barmode="group",
            bargap=0.25,
        )
        return figure

    def html(self) -> str:
        config = {"displaylogo": False, "responsive": True, "modeBarButtonsToRemove": ["lasso2d"]}
        # The prefix keeps chart ids apart from the ids of page sections.
        return self.plotly().to_html(
            full_html=False, include_plotlyjs=False, div_id=f"chart-{self.name}", config=config
        )

    def png(self, path: Path, dpi: int = 130) -> None:
        self._draw(path, dpi=dpi)

    def svg(self, path: Path, scale: float = 1.0, size: tuple[float, float] = (8.4, 4.8)) -> None:
        """The chart as a vector image; ``scale`` enlarges the lettering, e.g. for slides."""
        self._draw(path, scale=scale, size=size)

    def _draw(
        self,
        path: Path,
        dpi: int = 130,
        scale: float = 1.0,
        size: tuple[float, float] = (8.4, 4.8),
    ) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        # A fixed salt keeps the identifiers in vector output the same from run to run.
        with plt.rc_context({"font.size": 10 * scale, "svg.hashsalt": "syskit"}):
            self._plot(plt, path, dpi, scale, size)

    def _plot(self, plt, path: Path, dpi: int, scale: float, size: tuple[float, float]) -> None:
        figure, axes = plt.subplots(figsize=size)
        bars = [s for s in self.series if s.kind == "bar"]
        # Bars sit at whole-number positions; other series on a bar chart follow them.
        place = {value: index for index, value in enumerate(bars[0].x)} if bars else {}
        for s in self.series:
            style = {"color": s.color, "label": s.name or None}
            if s.kind == "line":
                x = [place.get(v, v) for v in s.x]
                axes.plot(
                    x, s.y, linewidth=s.width * scale, linestyle="--" if s.dash else "-", **style
                )
            elif s.kind == "markers":
                axes.scatter(
                    s.x, s.y, s=s.size**2 * 0.6 * scale, alpha=s.opacity, linewidths=0, **style
                )
            elif s.kind == "band":
                axes.fill_between(s.x, s.low, s.high, alpha=0.16 * s.opacity, linewidth=0, **style)
            elif s.kind == "bar":
                width = 0.8 / len(bars)
                offset = (bars.index(s) - (len(bars) - 1) / 2) * width
                positions = [i + offset for i in range(len(s.x))]
                axes.bar(positions, s.y, width=width, **style)
                axes.set_xticks(range(len(s.x)), [str(v) for v in s.x])
            elif s.kind == "errorbar":
                errors = [
                    [v - lo for lo, v in zip(s.low, s.y, strict=True)],
                    [h - v for h, v in zip(s.high, s.y, strict=True)],
                ]
                axes.errorbar(
                    s.x,
                    s.y,
                    yerr=errors,
                    fmt="o-" if s.connect else "o",
                    markersize=s.size * 0.7 * scale,
                    capsize=3 * scale,
                    linewidth=s.width * scale if s.connect else 0,
                    elinewidth=1.2 * scale,
                    **style,
                )
        labels = [str(v) for s in self.series for v in s.x if isinstance(v, str)]
        if sum(len(v) for v in set(labels)) > 70:
            axes.tick_params(axis="x", labelrotation=20)
            for label in axes.get_xticklabels():
                label.set_horizontalalignment("right")
        if self.log_x:
            axes.set_xscale("log")
        if self.log_y:
            axes.set_yscale("log")
        if self.x_range:
            axes.set_xlim(*self.x_range)
        if self.y_range:
            axes.set_ylim(*self.y_range)
        axes.set_title(self.title, loc="left", fontsize=12 * scale)
        axes.set_xlabel(self.x_title)
        axes.set_ylabel(self.y_title)
        axes.grid(True, color="#e2e8f0", linewidth=0.8)
        axes.set_axisbelow(True)
        for side in ("top", "right"):
            axes.spines[side].set_visible(False)
        if any(s.name for s in self.series):
            axes.legend(frameon=False, fontsize=9 * scale, loc="best")
        figure.tight_layout()
        path.parent.mkdir(parents=True, exist_ok=True)
        vector = Path(path).suffix == ".svg"
        figure.savefig(path, dpi=dpi, metadata={"Date": None} if vector else None)
        plt.close(figure)
