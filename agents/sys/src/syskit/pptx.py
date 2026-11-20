"""Read a PowerPoint file and lay its slides out as HTML, for ``syskit.slides``.

    slides = read(path)                       # one Slide per slide, in order
    html = slides[0].html(pictures)           # pictures: media name -> image address

Handles what presentations of results usually hold: titles and text boxes
(size, weight, colour, alignment, placeholder defaults from layout and
master), pictures, straight connectors with arrow heads, freeform shapes and
the right brace. Charts, tables, groups and animations are not read; an
element that is not understood is reported in ``Slide.skipped`` instead of
being dropped silently.

Lengths in the file are in EMU (914 400 per inch); the HTML is laid out on
the 1600 px wide stage of ``syskit.slides``.
"""

from __future__ import annotations

import colorsys
import html
import posixpath
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
REL = "{http://schemas.openxmlformats.org/package/2006/relationships}Relationship"
EMBED = "{" + NS["r"] + "}embed"
STAGE = 1600  # px
INSET = (91440, 45720)  # default text inset, horizontal and vertical
FALLBACK = "'Segoe UI', system-ui, -apple-system, Roboto, Helvetica, Arial, sans-serif"


@dataclass
class Slide:
    number: int
    parts: list[tuple] = field(default_factory=list)  # (kind, ...), in drawing order
    skipped: list[str] = field(default_factory=list)
    pictures: list[str] = field(default_factory=list)  # media names used, e.g. image3.png

    def html(self, pictures: dict[str, str]) -> str:
        """The slide's content as absolutely placed HTML; ``pictures`` maps media to addresses."""
        out = []
        for part in self.parts:
            if part[0] == "picture":
                _, box, media = part
                out.append(f'<img class="abs" src="{html.escape(pictures[media])}" alt="" '
                           f'style="{_place(box)}">')  # fmt: skip
            else:
                out.append(part[1])
        return "".join(out)


class Deck:
    """The parts of a presentation file that the slides refer to."""

    def __init__(self, path: Path) -> None:
        self.archive = zipfile.ZipFile(path)
        presentation = self._xml("ppt/presentation.xml")
        size = presentation.find("p:sldSz", NS)
        self.width, self.height = int(size.get("cx")), int(size.get("cy"))
        self.scale = STAGE / self.width
        rels = self._rels("ppt/presentation.xml")
        self.slide_paths = [
            rels[item.get("{" + NS["r"] + "}id")] for item in presentation.find("p:sldIdLst", NS)
        ]
        theme = self._xml(next(n for n in self.archive.namelist() if "theme/theme" in n))
        self.colors = {}
        for item in theme.find(".//a:clrScheme", NS):
            child = item[0]
            self.colors[item.tag.split("}")[1]] = child.get("lastClr") or child.get("val")
        self.colors |= {"tx1": self.colors["dk1"], "bg1": self.colors["lt1"],
                        "tx2": self.colors["dk2"], "bg2": self.colors["lt2"]}  # fmt: skip
        fonts = theme.find(".//a:fontScheme", NS)
        self.fonts = {
            "+mj-lt": fonts.find("a:majorFont/a:latin", NS).get("typeface"),
            "+mn-lt": fonts.find("a:minorFont/a:latin", NS).get("typeface"),
        }
        self.line_widths = [
            int(ln.get("w", 12700)) for ln in theme.findall(".//a:lnStyleLst/a:ln", NS)
        ]

    def _xml(self, name: str) -> ET.Element:
        return ET.fromstring(self.archive.read(name))

    def _rels(self, part: str) -> dict[str, str]:
        folder, name = posixpath.split(part)
        rels = f"{folder}/_rels/{name}.rels"
        if rels not in self.archive.namelist():
            return {}
        return {
            item.get("Id"): posixpath.normpath(posixpath.join(folder, item.get("Target")))
            for item in self._xml(rels).iter(REL)
        }

    # ------------------------------------------------------------------ colour and text style
    def color(self, node: ET.Element | None) -> str | None:
        """CSS colour of a fill or line element, or None if it has none."""
        if node is None:
            return None
        rgb = node.find("a:srgbClr", NS)
        scheme = node.find("a:schemeClr", NS)
        chosen = rgb if rgb is not None else scheme
        if chosen is None:
            return None
        value = chosen.get("val") if rgb is not None else self.colors.get(chosen.get("val"))
        if value is None:
            return None
        red, green, blue = (int(value[i : i + 2], 16) / 255 for i in (0, 2, 4))
        hue, light, saturation = colorsys.rgb_to_hls(red, green, blue)
        for change in chosen:
            amount = int(change.get("val", 100000)) / 100000
            kind = change.tag.split("}")[1]
            if kind == "lumMod":
                light *= amount
            elif kind == "lumOff":
                light += amount
            elif kind == "shade":
                light *= amount
            elif kind == "tint":
                light = light * amount + (1 - amount)
        red, green, blue = colorsys.hls_to_rgb(hue, min(max(light, 0), 1), saturation)
        return "#" + "".join(f"{round(c * 255):02x}" for c in (red, green, blue))

    def font(self, typeface: str | None, default: str) -> str:
        name = self.fonts.get(typeface or default, typeface or self.fonts[default])
        return f"'{name}', {FALLBACK}"

    # ------------------------------------------------------------------ placeholders
    def placeholders(self, slide_path: str) -> dict[str, dict]:
        """Position and text defaults of the placeholders, from master then layout."""
        layout = next(p for p in self._rels(slide_path).values() if "slideLayouts" in p)
        master = next(p for p in self._rels(layout).values() if "slideMasters" in p)
        master_xml = self._xml(master)
        styles = {
            "title": master_xml.find("p:txStyles/p:titleStyle/a:lvl1pPr", NS),
            "body": master_xml.find("p:txStyles/p:bodyStyle/a:lvl1pPr", NS),
        }
        found: dict[str, dict] = {}
        for source in (master_xml, self._xml(layout)):
            for shape in source.iter("{" + NS["p"] + "}sp"):
                ph = shape.find("p:nvSpPr/p:nvPr/p:ph", NS)
                if ph is None:
                    continue
                kind = ph.get("type", "body")
                key = (
                    "title"
                    if kind in ("title", "ctrTitle")
                    else "body"
                    if ph.get("idx") == "1"
                    else kind
                )
                entry = found.setdefault(key, {"size": None, "align": None, "anchor": None})
                box = _box(shape)
                if box:
                    entry["box"] = box
                body = shape.find("p:txBody/a:bodyPr", NS)
                if body is not None and body.get("anchor"):
                    entry["anchor"] = body.get("anchor")
                level = shape.find("p:txBody/a:lstStyle/a:lvl1pPr", NS)
                for style in (styles.get(key), level):
                    if style is None:
                        continue
                    entry["align"] = style.get("algn", entry["align"])
                    run = style.find("a:defRPr", NS)
                    if run is not None and run.get("sz"):
                        entry["size"] = int(run.get("sz"))
                    spacing = style.find("a:lnSpc/a:spcPct", NS)
                    if spacing is not None:
                        entry["spacing"] = int(spacing.get("val")) / 100000
        return found


def _box(shape: ET.Element) -> tuple[int, int, int, int] | None:
    frame = shape.find(".//a:xfrm", NS)
    if frame is None or frame.find("a:off", NS) is None:
        return None
    off, ext = frame.find("a:off", NS), frame.find("a:ext", NS)
    return int(off.get("x")), int(off.get("y")), int(ext.get("cx")), int(ext.get("cy"))


def _place(box: tuple[float, float, float, float]) -> str:
    left, top, width, height = box
    return f"left:{left:.1f}px;top:{top:.1f}px;width:{width:.1f}px;height:{height:.1f}px"


def read(path: Path) -> list[Slide]:
    """The slides of a presentation, converted."""
    deck = Deck(path)
    k = deck.scale
    point = STAGE / (deck.width / 12700)  # px per point on the stage
    slides = []
    for number, slide_path in enumerate(deck.slide_paths, start=1):
        slide = Slide(number)
        rels = deck._rels(slide_path)
        defaults = deck.placeholders(slide_path)
        tree = deck._xml(slide_path).find("p:cSld/p:spTree", NS)
        for element in tree:
            tag = element.tag.split("}")[1]
            if tag in ("nvGrpSpPr", "grpSpPr"):
                continue
            name = element.find(".//p:cNvPr", NS).get("name")
            if tag == "pic":
                media = posixpath.basename(rels[element.find(".//a:blip", NS).get(EMBED)])
                box = tuple(v * k for v in _box(element))
                slide.parts.append(("picture", box, media))
                slide.pictures.append(media)
            elif tag == "cxnSp":
                slide.parts.append(("shape", _connector(deck, element, k)))
            elif tag == "sp":
                ph = element.find("p:nvSpPr/p:nvPr/p:ph", NS)
                default = {}
                if ph is not None:
                    kind = ph.get("type", "body")
                    default = defaults.get("title" if kind in ("title", "ctrTitle") else "body", {})
                box = _box(element) or default.get("box")
                if box is None:
                    slide.skipped.append(f"{name}: no position")
                    continue
                geometry = _geometry(deck, element, box, k)
                if geometry:
                    slide.parts.append(("shape", geometry))
                text = _text(deck, element, box, k, point, default, title=ph is not None
                             and ph.get("type") in ("title", "ctrTitle"))  # fmt: skip
                if text:
                    slide.parts.append(("text", text))
                if not geometry and not text and element.find("a:custGeom", NS) is None:
                    preset = element.find("p:spPr/a:prstGeom", NS)
                    if preset is not None and preset.get("prst") not in ("rect",):
                        slide.skipped.append(f"{name}: shape {preset.get('prst')}")
            else:
                slide.skipped.append(f"{name}: {tag}")
        slides.append(slide)
    return slides


def _line(deck: Deck, element: ET.Element) -> tuple[str | None, float]:
    """Colour and width (EMU) of a shape's outline, from the shape or its style."""
    line = element.find("p:spPr/a:ln", NS)
    reference = element.find("p:style/a:lnRef", NS)
    color, width = None, 12700.0
    if reference is not None and int(reference.get("idx", 0)) > 0:
        color = deck.color(reference)
        index = int(reference.get("idx")) - 1
        if index < len(deck.line_widths):
            width = deck.line_widths[index]
    if line is not None:
        if line.find("a:noFill", NS) is not None:
            return None, 0.0
        color = deck.color(line.find("a:solidFill", NS)) or color
        width = float(line.get("w", width))
    return color, width


def _svg(box: tuple[int, int, int, int], k: float, body: str, view: str) -> str:
    place = _place(tuple(v * k for v in box))
    return (f'<svg class="abs" style="{place};overflow:visible" viewBox="{view}" '
            f'preserveAspectRatio="none">{body}</svg>')  # fmt: skip


def _connector(deck: Deck, element: ET.Element, k: float) -> str:
    x, y, w, h = _box(element)
    frame = element.find(".//a:xfrm", NS)
    x1, x2 = (x + w, x) if frame.get("flipH") == "1" else (x, x + w)
    y1, y2 = (y + h, y) if frame.get("flipV") == "1" else (y, y + h)
    color, width = _line(deck, element)
    color = color or "#000000"
    line = element.find("p:spPr/a:ln", NS)
    stroke = max(width * k, 1.5)
    px = [v * k for v in (x1, y1, x2, y2)]
    body = (f'<line x1="{px[0]:.1f}" y1="{px[1]:.1f}" x2="{px[2]:.1f}" y2="{px[3]:.1f}" '
            f'stroke="{color}" stroke-width="{stroke:.1f}"/>')  # fmt: skip
    for end, (ax, ay, bx, by) in (("tailEnd", px), ("headEnd", (px[2], px[3], px[0], px[1]))):
        if line is not None and line.find(f"a:{end}", NS) is not None:
            if line.find(f"a:{end}", NS).get("type", "none") == "none":
                continue
            length = (((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5) or 1.0
            ux, uy = (bx - ax) / length, (by - ay) / length
            size = 5 * stroke
            base = (bx - ux * size, by - uy * size)
            left = (base[0] - uy * size * 0.45, base[1] + ux * size * 0.45)
            right = (base[0] + uy * size * 0.45, base[1] - ux * size * 0.45)
            body += (f'<polygon points="{bx:.1f},{by:.1f} {left[0]:.1f},{left[1]:.1f} '
                     f'{right[0]:.1f},{right[1]:.1f}" fill="{color}"/>')  # fmt: skip
    return (f'<svg class="abs" style="left:0;top:0;width:{STAGE}px;height:900px;overflow:visible">'
            f"{body}</svg>")  # fmt: skip


def _geometry(deck: Deck, element: ET.Element, box, k: float) -> str:
    """A freeform or a right brace as SVG; empty for plain rectangles without fill or line."""
    properties = element.find("p:spPr", NS)
    custom = properties.find("a:custGeom", NS)
    preset = properties.find("a:prstGeom", NS)
    fill = (
        None
        if properties.find("a:noFill", NS) is not None
        else deck.color(properties.find("a:solidFill", NS))
    )
    color, width = _line(deck, element)
    stroke = (
        f'stroke="{color}" stroke-width="{max(width * k, 1.2):.1f}" '
        'vector-effect="non-scaling-stroke"'
    )
    if custom is not None:
        path = custom.find("a:pathLst/a:path", NS)
        commands = []
        for step in path:
            points = " ".join(f"{pt.get('x')} {pt.get('y')}" for pt in step.findall("a:pt", NS))
            letter = {"moveTo": "M", "lnTo": "L", "cubicBezTo": "C", "close": "Z"}.get(
                step.tag.split("}")[1]
            )
            if letter:
                commands.append(f"{letter}{points}")
        body = (f'<path d="{" ".join(commands)}" fill="{fill or "none"}" '
                f"{stroke if color else 'stroke=\"none\"'}/>")  # fmt: skip
        return _svg(box, k, body, f"0 0 {path.get('w')} {path.get('h')}")
    if preset is not None and preset.get("prst") == "rightBrace":
        w, h = box[2], box[3]
        r = min(w, h) * 0.08333
        m, c = w / 2, h / 2
        d = (
            f"M0 0 Q{m} 0 {m} {r} L{m} {c - r} Q{m} {c} {w} {c} "
            f"Q{m} {c} {m} {c + r} L{m} {h - r} Q{m} {h} 0 {h}"
        )
        return _svg(box, k, f'<path d="{d}" fill="none" {stroke}/>', f"0 0 {w} {h}")
    return ""


def _text(deck: Deck, element: ET.Element, box, k: float, point: float, default: dict,
          title: bool) -> str:  # fmt: skip
    body = element.find("p:txBody", NS)
    if body is None:
        return ""
    properties = body.find("a:bodyPr", NS)
    fit = properties.find("a:normAutofit", NS)
    shrink = int(fit.get("fontScale", 100000)) / 100000 if fit is not None else 1.0
    anchor = properties.get("anchor") or default.get("anchor") or "t"
    spacing = default.get("spacing", 1.0) * 1.2
    paragraphs = []
    for paragraph in body.findall("a:p", NS):
        runs = []
        for run in paragraph.findall("a:r", NS):
            content = run.find("a:t", NS).text or ""
            style = run.find("a:rPr", NS)
            size = (
                int(style.get("sz"))
                if style is not None and style.get("sz")
                else (default.get("size") or 1800)
            )
            css = [f"font-size:{size / 100 * shrink:.2f}em"]
            face = (
                style.find("a:latin", NS).get("typeface")
                if (style is not None and style.find("a:latin", NS) is not None)
                else None
            )
            css.append(f"font-family:{deck.font(face, '+mj-lt' if title else '+mn-lt')}")
            if style is not None and style.get("b") == "1":
                css.append("font-weight:700")
            if style is not None and style.get("i") == "1":
                css.append("font-style:italic")
            color = deck.color(style.find("a:solidFill", NS)) if style is not None else None
            if color:
                css.append(f"color:{color}")
            runs.append(f'<span style="{";".join(css)}">{html.escape(content)}</span>')
        if not runs:
            continue
        level = paragraph.find("a:pPr", NS)
        align = (level.get("algn") if level is not None else None) or default.get("align") or "l"
        side = {"l": "left", "ctr": "center", "r": "right", "just": "justify"}[align]
        paragraphs.append(f'<p style="text-align:{side}">{"".join(runs)}</p>')
    if not paragraphs:
        return ""
    sides = (("lIns", INSET[0]), ("tIns", INSET[1]), ("rIns", INSET[0]), ("bIns", INSET[1]))
    inset = [int(properties.get(side, standard)) * k for side, standard in sides]
    vertical = {"t": "flex-start", "ctr": "center", "b": "flex-end"}[anchor]
    grows = properties.find("a:spAutoFit", NS) is not None
    left, top, width, height = (v * k for v in box)
    size_css = f"left:{left:.1f}px;top:{top:.1f}px;width:{width:.1f}px;" + (
        f"min-height:{height:.1f}px" if grows else f"height:{height:.1f}px"
    )
    # Sizes inside are in em of one point, so that a box marked as shrink-to-fit can be
    # scaled as a whole when the reader's fonts are wider than the author's.
    fit_class = " fit" if fit is not None else ""
    return (
        f'<div class="abs tx{fit_class}" data-size="{point:.3f}" '
        f'style="{size_css};font-size:{point:.3f}px;justify-content:{vertical};'
        f"padding:{inset[1]:.1f}px {inset[2]:.1f}px {inset[3]:.1f}px {inset[0]:.1f}px;"
        f'line-height:{spacing:.2f}">{"".join(paragraphs)}</div>'
    )


def media(path: Path) -> dict[str, bytes]:
    """The pictures stored in the presentation, by file name."""
    with zipfile.ZipFile(path) as archive:
        return {
            posixpath.basename(name): archive.read(name)
            for name in archive.namelist()
            if re.match(r"ppt/media/[^/]+$", name)
        }
