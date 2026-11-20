"""A report written once and rendered as Markdown and as a self-contained web page.

    report = Report("Title", "One-paragraph summary.")
    report.section("Findings")
    report.text("A paragraph with `code`, *emphasis* and [a link](https://example.org).")
    report.table(["Field", "Value"], [["Volve", "10.2"]])
    report.chart(chart, "What the chart shows and where the data comes from.")
    report.write_markdown(folder / "report.md")
    report.write_html(folder / "report" / "index.html")

Inline markup in text, table cells and captions is limited to backticks,
single asterisks and links. Numbers are formatted by the caller.
"""

from __future__ import annotations

import datetime as dt
import html
import os
import re
from pathlib import Path

from syskit.charts import Chart

CSS = """
:root { --ink:#0f172a; --muted:#475569; --line:#e2e8f0; --bg:#f8fafc; --card:#ffffff;
        --plan:#1d4ed8; --actual:#c2410c; }
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body { margin:0; font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
       color:var(--ink); background:var(--bg); line-height:1.55; }
header.top { background:#0f172a; color:#f8fafc; padding:44px 24px 36px; }
header.top .wrap, main, nav .wrap { max-width:1080px; margin:0 auto; }
header.top h1 { margin:0 0 8px; font-size:clamp(1.6rem, 3.2vw, 2.3rem); line-height:1.2; }
header.top p { margin:0; color:#cbd5e1; max-width:760px; }
header.top code { background:rgba(255,255,255,.14); color:inherit; }
nav { position:sticky; top:0; z-index:5; background:rgba(255,255,255,.94);
      border-bottom:1px solid var(--line); backdrop-filter: blur(6px); }
nav .wrap { display:flex; gap:18px; padding:10px 24px; overflow-x:auto; white-space:nowrap; }
nav a { color:var(--muted); text-decoration:none; font-size:.92rem; }
nav a:hover { color:var(--ink); }
main { padding:8px 24px 64px; }
section { padding-top:40px; }
h2 { font-size:1.45rem; margin:0 0 6px; }
h3 { font-size:1.08rem; margin:28px 0 6px; }
p.lead { color:var(--muted); margin:0 0 18px; max-width:780px; }
p, li { max-width:780px; }
.cards { display:grid; grid-template-columns:repeat(auto-fit, minmax(230px, 1fr)); gap:14px;
         margin:18px 0 8px; }
.card { background:var(--card); border:1px solid var(--line); border-radius:12px;
        padding:16px 18px; }
.card .label { color:var(--muted); font-size:.86rem; }
.card .pair { display:flex; align-items:baseline; gap:10px; margin:6px 0 2px; flex-wrap:wrap; }
.card .plan { color:var(--plan); font-size:1.05rem; }
.card .arrow { color:var(--muted); }
.card .actual { color:var(--actual); font-size:1.5rem; font-weight:650; }
.card .value { font-size:1.5rem; font-weight:650; margin:4px 0 2px; }
.card .note { color:var(--muted); font-size:.86rem; }
figure { background:var(--card); border:1px solid var(--line); border-radius:12px; margin:18px 0;
         padding:10px 12px 12px; }
figure img { max-width:100%; max-height:560px; width:auto; height:auto; display:block;
             margin:0 auto; }
figcaption { color:var(--muted); font-size:.9rem; padding:4px 8px 2px; max-width:none; }
.legend-key { display:flex; gap:18px; font-size:.9rem; color:var(--muted); margin:8px 0 0; }
.legend-key span::before { content:""; display:inline-block; width:12px; height:12px;
        border-radius:3px; margin-right:6px; vertical-align:-1px; }
.legend-key .p::before { background:var(--plan); }
.legend-key .a::before { background:var(--actual); }
.scroll { overflow-x:auto; background:var(--card); border:1px solid var(--line);
          border-radius:12px; margin:14px 0; }
table { border-collapse:collapse; width:100%; font-size:.93rem; font-variant-numeric:tabular-nums; }
th, td { padding:8px 12px; border-bottom:1px solid var(--line); vertical-align:top; }
th { background:#f1f5f9; font-weight:600; position:sticky; top:0; }
tbody tr:last-child td { border-bottom:0; }
.l { text-align:left; } .r { text-align:right; }
p.caption { color:var(--muted); font-size:.9rem; margin:14px 0 -6px; }
details { margin:8px 0 0; } summary { cursor:pointer; color:var(--muted); font-size:.92rem; }
.callout { border-left:4px solid var(--actual); background:#fff7ed; padding:12px 16px;
           border-radius:0 10px 10px 0; margin:16px 0; max-width:780px; }
footer { color:var(--muted); font-size:.88rem; border-top:1px solid var(--line); margin-top:48px;
         padding-top:18px; }
code { background:#e2e8f0; padding:1px 5px; border-radius:4px; font-size:.88em; }
@media print { nav { display:none; } header.top { background:#fff; color:#000; }
               header.top p { color:#333; } figure, .card, .scroll { break-inside:avoid; } }
"""


def number(value: float, digits: int = 0) -> str:
    """A number with a space as thousands separator."""
    return f"{value:,.{digits}f}".replace(",", " ")


def signed(value: float, digits: int = 0) -> str:
    return f"{value:+,.{digits}f}".replace(",", " ").replace("-", "−")


def percent(value: float, digits: int = 0) -> str:
    return f"{100 * value:.{digits}f} %"


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def inline_html(text: str) -> str:
    """Backticks, single asterisks and links to HTML; everything else escaped."""
    result = html.escape(text, quote=False)
    result = re.sub(r"`([^`]+)`", r"<code>\1</code>", result)
    result = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', result)
    # Emphasis hugs its text: "2 * 3 * 4" is arithmetic, not markup.
    return re.sub(r"(?<![\w*])\*(?=\S)([^*\n]+?)(?<=\S)\*(?![\w*])", r"<em>\1</em>", result)


def html_table(headers: list[str], rows: list[list], *, left: tuple[int, ...] = (0,)) -> str:
    """An HTML table; the columns listed in ``left`` hold text and are left-aligned."""

    def cell(value, tag: str, index: int) -> str:
        side = "l" if index in left else "r"
        text = inline_html(value) if isinstance(value, str) else number(value, 2)
        return f'<{tag} class="{side}">{text}</{tag}>'

    head = "".join(cell(h, "th", i) for i, h in enumerate(headers))
    body = "".join(
        "<tr>" + "".join(cell(v, "td", i) for i, v in enumerate(row)) + "</tr>" for row in rows
    )
    return (
        f'<div class="scroll"><table><thead><tr>{head}</tr></thead>'
        f"<tbody>{body}</tbody></table></div>"
    )


class Report:
    def __init__(self, title: str, summary: str, generator: str = "") -> None:
        self.title, self.summary, self.generator = title, summary, generator
        self.blocks: list[tuple] = []

    def section(self, title: str, short: str | None = None) -> None:
        """Start a section; ``short`` is its label in the page's navigation bar."""
        self.blocks.append(("section", title, short or title))

    def heading(self, title: str) -> None:
        self.blocks.append(("heading", title))

    def text(self, *paragraphs: str) -> None:
        self.blocks.extend(("text", " ".join(p.split())) for p in paragraphs)

    def bullets(self, items: list[str], numbered: bool = False) -> None:
        self.blocks.append(("bullets", [" ".join(i.split()) for i in items], numbered))

    def note(self, text: str) -> None:
        self.blocks.append(("note", " ".join(text.split())))

    def table(
        self,
        headers: list[str],
        rows: list[list],
        *,
        left: tuple[int, ...] = (0,),
        caption: str = "",
    ) -> None:
        self.blocks.append(("table", headers, rows, left, " ".join(caption.split())))

    def chart(self, chart: Chart, caption: str) -> None:
        self.blocks.append(("chart", chart, " ".join(caption.split())))

    def image(self, path: Path, caption: str) -> None:
        """An existing picture, e.g. a figure from a source that is being reviewed."""
        self.blocks.append(("image", Path(path), " ".join(caption.split())))

    def cards(self, items: list[tuple[str, str, str]]) -> None:
        """Key figures as (label, value, note): cards on the web page, a table in Markdown."""
        self.blocks.append(("cards", items))

    def _footer(self) -> str:
        made = f" by `{self.generator}`" if self.generator else ""
        return f"Generated {dt.date.today().isoformat()}{made}."

    def write_markdown(self, target: Path, figures: str = "figs") -> Path:
        """Write the Markdown version; charts are drawn into ``figures`` beside it."""
        lines = [f"# {self.title}", "", self.summary, ""]
        for block in self.blocks:
            kind = block[0]
            if kind == "section":
                lines += [f"## {block[1]}", ""]
            elif kind == "heading":
                lines += [f"### {block[1]}", ""]
            elif kind == "text":
                lines += [block[1], ""]
            elif kind == "bullets":
                marks = [f"{i}." if block[2] else "-" for i in range(1, len(block[1]) + 1)]
                lines += [f"{mark} {item}" for mark, item in zip(marks, block[1], strict=True)]
                lines.append("")
            elif kind == "note":
                lines += [f"> {block[1]}", ""]
            elif kind == "cards":
                lines += ["| | | |", "|---|---|---|"]
                lines += [f"| {label} | {value} | {note} |" for label, value, note in block[1]]
                lines.append("")
            elif kind == "table":
                _, headers, rows, left, caption = block
                if caption:
                    lines += [f"*{caption}*", ""]
                align = ["---" if i in left else "---:" for i in range(len(headers))]
                lines.append("| " + " | ".join(headers) + " |")
                lines.append("|" + "|".join(align) + "|")
                for row in rows:
                    cells = [v if isinstance(v, str) else number(v, 2) for v in row]
                    lines.append("| " + " | ".join(c.replace("|", "\\|") for c in cells) + " |")
                lines.append("")
            elif kind == "chart":
                _, chart, caption = block
                name = f"{target.stem}_{chart.name}.png"
                chart.png(target.parent / figures / name)
                lines += [f"![{chart.title}]({figures}/{name})", "", f"*{caption}*", ""]
            elif kind == "image":
                _, path, caption = block
                relative = Path(os.path.relpath(path, target.parent)).as_posix()
                lines += [f"![Figure]({relative.replace(' ', '%20')})", "", f"*{caption}*", ""]
        lines += ["---", "", self._footer(), ""]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n".join(lines), encoding="utf-8")
        return target

    def write_html(
        self, target: Path, plotly: str = "assets/plotly.min.js", link_prefix: str = ""
    ) -> Path:
        """Write the web page.

        ``plotly`` is the path of the chart library relative to the page; the
        file is created there if it does not exist, so the page works without
        a network. ``link_prefix`` is put before relative links in the text,
        which are written as seen from the Markdown version (``"../"`` when
        the page lies one folder below it).
        """
        from plotly.offline import get_plotlyjs

        parts, nav, open_section = [], [], False
        for block in self.blocks:
            kind = block[0]
            if kind == "section":
                anchor = slug(block[2])
                nav.append(f'<a href="#{anchor}">{html.escape(block[2])}</a>')
                parts.append(("</section>" if open_section else "") + f'<section id="{anchor}">')
                parts.append(f"<h2>{inline_html(block[1])}</h2>")
                open_section = True
            elif kind == "heading":
                parts.append(f"<h3>{inline_html(block[1])}</h3>")
            elif kind == "text":
                parts.append(f"<p>{inline_html(block[1])}</p>")
            elif kind == "bullets":
                tag = "ol" if block[2] else "ul"
                items = "".join(f"<li>{inline_html(i)}</li>" for i in block[1])
                parts.append(f"<{tag}>{items}</{tag}>")
            elif kind == "note":
                parts.append(f'<div class="callout">{inline_html(block[1])}</div>')
            elif kind == "cards":
                cards = "".join(
                    f'<div class="card"><div class="label">{inline_html(label)}</div>'
                    f'<div class="value">{inline_html(value)}</div>'
                    f'<div class="note">{inline_html(note)}</div></div>'
                    for label, value, note in block[1]
                )
                parts.append(f'<div class="cards">{cards}</div>')
            elif kind == "table":
                _, headers, rows, left, caption = block
                if caption:
                    parts.append(f'<p class="caption">{inline_html(caption)}</p>')
                parts.append(html_table(headers, rows, left=left))
            elif kind == "chart":
                _, chart, caption = block
                parts.append(
                    f"<figure>{chart.html()}<figcaption>{inline_html(caption)}</figcaption></figure>"
                )
            elif kind == "image":
                _, path, caption = block
                relative = Path(os.path.relpath(path, target.parent)).as_posix()
                parts.append(
                    f'<figure><img src="{html.escape(relative.replace(" ", "%20"))}" alt="Figure">'
                    f"<figcaption>{inline_html(caption)}</figcaption></figure>"
                )
        if open_section:
            parts.append("</section>")
        body = (
            f'<header class="top"><div class="wrap"><h1>{html.escape(self.title)}</h1>'
            f"<p>{inline_html(self.summary)}</p></div></header>"
            f'<nav><div class="wrap">{"".join(nav)}</div></nav>'
            f"<main>{''.join(parts)}<footer>{inline_html(self._footer())}</footer></main>"
        )
        page = (
            '<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f"<title>{html.escape(self.title)}</title>"
            f'<style>{CSS}</style><script src="{plotly}"></script></head>'
            f"<body>{body}</body></html>"
        )
        if link_prefix:
            page = re.sub(r'<a href="(?!https?:|mailto:|#|/)', f'<a href="{link_prefix}', page)
        target.parent.mkdir(parents=True, exist_ok=True)
        library = target.parent / plotly
        if not library.exists():
            library.parent.mkdir(parents=True, exist_ok=True)
            library.write_text(get_plotlyjs(), encoding="utf-8")
        target.write_text(page, encoding="utf-8")
        return target
