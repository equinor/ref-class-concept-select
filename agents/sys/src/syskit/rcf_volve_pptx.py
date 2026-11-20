"""The web presentation ``rcf_volve_v2`` as a PowerPoint file.

    python -m syskit.rcf_volve_pptx build

writes ``agents/sys/out/rcf_volve_v2_extended.pptx``: the slides of
``rcf_volve_v2.pptx`` as they are, with the additions of the web version
(``syskit.rcf_volve_deck``). The agents diagram is placed on slide 4; three
slides follow at the end: the first use, the two plans, and what changes.
The diagrams are placed as pictures (rendered from the same drawings as the
web version); the last slide is a PowerPoint table and can be edited.

Rendering the drawings needs the cairo library on the system
(``libcairo2``), which CairoSVG uses.
"""

from __future__ import annotations

import argparse
import io
import zipfile
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR
from pptx.oxml.ns import qn
from pptx.util import Emu, Pt

from syskit import workflow_deck
from syskit.paths import repo_root
from syskit.rcf_volve_deck import SOURCE, WORKFLOW_SLIDE
from syskit.svg import Svg

OUT = "agents/sys/out/rcf_volve_v2_extended.pptx"
EMU_PER_PX = 7620  # the web stage is 1600 px wide, the slide 12 192 000 EMU
TITLE_BOX = (909675, 98437, 10515600, 662782)  # as on slides 5 to 7 of the source
PICTURE_AREA = (420000, 900000, 11352000, 5780000)
ORANGE = RGBColor(0xC2, 0x41, 0x0C)
MUTED = RGBColor(0x47, 0x55, 0x69)
LINE = "CBD5E1"
NO_STYLE = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"  # table style "No Style, No Grid"


def picture(drawing: Svg, width: int = 3200) -> io.BytesIO:
    """A drawing as a PNG, in the font of the web version so that the text fits its boxes."""
    import cairosvg

    return io.BytesIO(cairosvg.svg2png(bytestring=drawing.render().encode(), output_width=width))


def place(slide, image: io.BytesIO, drawing: Svg, area: tuple[int, int, int, int]) -> None:
    """Put a picture in an area of the slide, as large as fits, centred."""
    left, top, width, height = area
    scale = min(width / drawing.width, height / drawing.height)
    w, h = drawing.width * scale, drawing.height * scale
    slide.shapes.add_picture(
        image, Emu(int(left + (width - w) / 2)), Emu(int(top + (height - h) / 2)), Emu(int(w)),
        Emu(int(h)),
    )  # fmt: skip


def titled_slide(presentation, title: str):
    """A new slide at the end with a title set like the titles of slides 5 to 7."""
    layout = next(
        (item for item in presentation.slide_layouts if item.name == "Title Only"),
        presentation.slide_layouts[5],
    )
    slide = presentation.slides.add_slide(layout)
    shape = slide.shapes.title
    shape.left, shape.top, shape.width, shape.height = (Emu(v) for v in TITLE_BOX)
    frame = shape.text_frame
    frame.vertical_anchor = MSO_ANCHOR.BOTTOM
    frame.text = title
    run = frame.paragraphs[0].runs[0]
    run.font.size, run.font.name = Pt(40), "Arial"
    return slide


def _bottom_border(cell, width: int = 12700) -> None:
    properties = cell._tc.get_or_add_tcPr()
    line = properties.makeelement(qn("a:lnB"), {"w": str(width), "cap": "flat", "cmpd": "sng"})
    fill = line.makeelement(qn("a:solidFill"), {})
    fill.append(fill.makeelement(qn("a:srgbClr"), {"val": LINE}))
    line.append(fill)
    properties.append(line)


def changes_table(slide, rows: list[tuple[str, str, str]]) -> None:
    """The comparison of the two plans as a table that can be edited in PowerPoint."""
    widths = (2_900_000, 4_100_000, 4_350_000)
    frame = slide.shapes.add_table(
        len(rows) + 1, 3, Emu(420000), Emu(1_150_000), Emu(sum(widths)), Emu(700_000 * len(rows))
    )
    table = frame.table
    frame._element.graphic.graphicData.tbl.tblPr.find(qn("a:tableStyleId")).text = NO_STYLE
    for index, width in enumerate(widths):
        table.columns[index].width = Emu(width)
    for r, row in enumerate([("", "2005 plan", "Modified plan"), *rows]):
        for c, content in enumerate(row):
            cell = table.cell(r, c)
            cell.text = content
            cell.margin_top = cell.margin_bottom = Emu(90000)
            _bottom_border(cell)
            run = cell.text_frame.paragraphs[0].runs[0] if content else None
            if run is None:
                continue
            run.font.name, run.font.size = "Arial", Pt(17 if r == 0 else 20)
            run.font.bold = r > 0 and c == 0
            if r == 0:
                run.font.color.rgb = MUTED
            elif c == 2:
                run.font.color.rgb = ORANGE


def build(target: Path) -> Path:
    presentation = Presentation(str(repo_root() / SOURCE))
    numbers = workflow_deck.numbers()

    roles = workflow_deck.roles()
    place(
        presentation.slides[WORKFLOW_SLIDE - 1],
        picture(roles),
        roles,
        tuple(v * EMU_PER_PX for v in (70, 236, 1460, 640)),
    )
    for title, drawing in (
        ("First use", workflow_deck.use_case(numbers)),
        ("The 2005 plan and the modified plan", workflow_deck.concept_comparison(numbers)),
    ):
        place(titled_slide(presentation, title), picture(drawing), drawing, PICTURE_AREA)
    changes_table(titled_slide(presentation, "What changes"), workflow_deck.changes_rows(numbers))

    saved = io.BytesIO()
    presentation.save(saved)
    target.parent.mkdir(parents=True, exist_ok=True)
    _write_undated(saved, target)
    return target


def _write_undated(saved: io.BytesIO, target: Path) -> None:
    """Write the file with a fixed date on every part, so that a rebuild gives the same file."""
    with zipfile.ZipFile(saved) as source, zipfile.ZipFile(target, "w") as result:
        for item in source.infolist():
            entry = zipfile.ZipInfo(item.filename, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            result.writestr(entry, source.read(item))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("build",))
    parser.parse_args(argv)
    target = build(repo_root() / OUT)
    print(f"written: {target} ({target.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
