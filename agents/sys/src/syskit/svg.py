"""Diagrams as SVG, written from code.

    drawing = Svg(1600, 760)
    drawing.box(40, 60, 300, 110, "Fact register", ["one number per row"], color=BLUE)
    drawing.arrow(340, 115, 440, 115)
    drawing.write(folder / "diagram.svg")

Coordinates are in the drawing's own units; the file scales to any size.
"""

from __future__ import annotations

import html
from pathlib import Path

INK, MUTED, LINE, PAPER = "#0f172a", "#475569", "#cbd5e1", "#ffffff"
BLUE, GREEN, ORANGE, PURPLE, SLATE = "#1d4ed8", "#15803d", "#c2410c", "#7c3aed", "#334155"
FONT = "system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"


def tint(color: str, share: float = 0.12) -> str:
    """The colour mixed into white; ``share`` is how much of the colour remains."""
    parts = [int(color[i : i + 2], 16) for i in (1, 3, 5)]
    mixed = [round(255 - share * (255 - c)) for c in parts]
    return "#" + "".join(f"{c:02x}" for c in mixed)


class Svg:
    def __init__(self, width: int = 1600, height: int = 900, background: str | None = None):
        self.width, self.height = width, height
        self.parts: list[str] = []
        self.markers: dict[str, str] = {}
        if background:
            self.rect(0, 0, width, height, fill=background, stroke="none", radius=0)

    # ------------------------------------------------------------------ primitives
    def rect(
        self, x, y, w, h, *, fill=PAPER, stroke=LINE, radius=14, width=2, dash=False, opacity=1.0
    ) -> None:
        dashes = ' stroke-dasharray="12 9"' if dash else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{width}" opacity="{opacity}"{dashes}/>'
        )

    def text(
        self, x, y, content, *, size=26, weight=400, fill=INK, anchor="start", italic=False
    ) -> None:
        style = ' font-style="italic"' if italic else ""
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
            f'text-anchor="{anchor}"{style}>{html.escape(str(content))}</text>'
        )

    def lines(self, x, y, rows: list[str], *, size=24, gap=1.32, **style) -> None:
        """Several lines of text; ``y`` is the baseline of the first."""
        for index, row in enumerate(rows):
            self.text(x, y + index * size * gap, row, size=size, **style)

    def line(self, x1, y1, x2, y2, *, color=LINE, width=2, dash=False) -> None:
        dashes = ' stroke-dasharray="10 8"' if dash else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{width}" stroke-linecap="round"{dashes}/>'
        )

    def path(self, d: str, *, color=INK, width=3, fill="none", dash=False, arrow=False) -> None:
        dashes = ' stroke-dasharray="10 8"' if dash else ""
        end = f' marker-end="url(#{self._marker(color)})"' if arrow else ""
        self.parts.append(
            f'<path d="{d}" stroke="{color}" stroke-width="{width}" fill="{fill}" '
            f'stroke-linecap="round" stroke-linejoin="round"{dashes}{end}/>'
        )

    def polygon(self, points: list[tuple[float, float]], *, fill=PAPER, stroke=LINE, width=2,
                dash=False, opacity=1.0) -> None:  # fmt: skip
        dashes = ' stroke-dasharray="10 8"' if dash else ""
        coordinates = " ".join(f"{x},{y}" for x, y in points)
        self.parts.append(
            f'<polygon points="{coordinates}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{width}" stroke-linejoin="round" opacity="{opacity}"{dashes}/>'
        )

    def circle(self, x, y, r, *, fill=PAPER, stroke=INK, width=2) -> None:
        self.parts.append(
            f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{width}"/>'
        )

    def _marker(self, color: str) -> str:
        name = "arrow-" + color.lstrip("#")
        self.markers[name] = (
            f'<marker id="{name}" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" '
            f'markerHeight="7" orient="auto-start-reverse">'
            f'<path d="M0 0 L10 5 L0 10 z" fill="{color}"/></marker>'
        )
        return name

    def arrow(self, x1, y1, x2, y2, *, color=MUTED, width=4, dash=False) -> None:
        self.path(f"M{x1} {y1} L{x2} {y2}", color=color, width=width, dash=dash, arrow=True)

    # ------------------------------------------------------------------ composites
    def box(
        self, x, y, w, h, title: str, rows: list[str] | None = None, *, color=SLATE,
        dash=False, title_size=28, size=22, fill: str | None = None,
    ) -> None:  # fmt: skip
        """A card: tinted, with a coloured edge on the left, a title and a few short lines."""
        self.rect(x, y, w, h, fill=fill or tint(color), stroke=color, dash=dash)
        self.rect(x, y, 10, h, fill=color, stroke="none", radius=5)
        self.text(x + 28, y + title_size + 14, title, size=title_size, weight=650)
        if rows:
            first = y + title_size + 14 + size * 1.5
            self.lines(x + 28, first, rows, size=size, fill=MUTED)

    def note(self, x, y, content: str, *, color=ORANGE, size=20, anchor="start") -> None:
        """A short remark in the margin, in italics."""
        self.text(x, y, content, size=size, fill=color, anchor=anchor, italic=True)

    def pill(self, x, y, content: str, *, color=SLATE, size=20, dash=False) -> float:
        """A small rounded label; returns its width."""
        width = 26 + 0.56 * size * len(content)
        self.rect(x, y, width, size * 1.7, fill=PAPER if dash else color, stroke=color,
                  radius=size * 0.85, dash=dash)  # fmt: skip
        self.text(x + width / 2, y + size * 1.18, content, size=size, weight=600,
                  fill=color if dash else PAPER, anchor="middle")  # fmt: skip
        return width

    # ------------------------------------------------------------------ output
    def render(self) -> str:
        defs = f"<defs>{''.join(self.markers.values())}</defs>" if self.markers else ""
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.width} {self.height}" '
            f'font-family="{FONT}">{defs}{"".join(self.parts)}</svg>'
        )

    def write(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.render(), encoding="utf-8")
        return path
