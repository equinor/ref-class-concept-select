"""Figure cut-outs from born-digital PDF pages.

A figure is located from its caption: the graphics (images and vector
drawings) nearest to the caption are grouped, and the page is rendered
inside their bounding box.

    python -m dockit.figures cut <pdf> <figs-dir> [--word Figur]
"""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path

import pymupdf

from dockit.pdf import Block, Rect, overlap_fraction, page_blocks, render

RULE_THICKNESS = 2.5  # drawings thinner than this are table rules or underlines
MERGE_DISTANCE = 14.0  # graphics closer than this belong to one figure
LABEL_MARGIN = 12.0  # short text this close to the graphics is a label or legend
LABEL_LENGTH = 40  # longer text blocks near the graphics are body text, not labels


@dataclass(frozen=True)
class Figure:
    page: int
    number: str
    caption: str
    rect: Rect


def union(a: Rect, b: Rect) -> Rect:
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))


def near(a: Rect, b: Rect, distance: float) -> bool:
    return not (
        a[2] + distance < b[0]
        or b[2] + distance < a[0]
        or a[3] + distance < b[1]
        or b[3] + distance < a[1]
    )


def cluster(rects: list[Rect], distance: float = MERGE_DISTANCE) -> list[Rect]:
    """Merge rectangles that are within ``distance`` of each other."""
    groups = list(rects)
    merged = True
    while merged:
        merged = False
        result: list[Rect] = []
        for rect in groups:
            for index, other in enumerate(result):
                if near(rect, other, distance):
                    result[index] = union(rect, other)
                    merged = True
                    break
            else:
                result.append(rect)
        groups = result
    return groups


def graphics(page: pymupdf.Page) -> list[Rect]:
    """Bounding boxes of images and of drawings that are not thin rules."""
    rects = [tuple(info["bbox"]) for info in page.get_image_info()]
    for drawing in page.get_drawings():
        rect = tuple(drawing["rect"])
        if rect[2] - rect[0] > RULE_THICKNESS and rect[3] - rect[1] > RULE_THICKNESS:
            rects.append(rect)
    inside = tuple(page.rect)
    return [r for r in rects if r[0] >= inside[0] - 1 and r[2] <= inside[2] + 1]


def caption_numbers(text: str, word: str) -> list[str]:
    """Figure numbers in a caption block, e.g. ``["4.2"]``; empty if it is not a caption.

    Two figures side by side can share one caption line.
    """
    if not re.match(rf"\s*{word}\s*\d", text):
        return []
    return [f"{a}.{b}" for a, b in re.findall(rf"{word}\s*(\d+)\s*[.\-]\s*(\d+)", text)]


def horizontal_overlap(a: Rect, b: Rect) -> float:
    return max(0.0, min(a[2], b[2]) - max(a[0], b[0]))


def with_labels(box: Rect, blocks: list[Block], caption: Block) -> Rect:
    """Extend the graphics box by the text that belongs to the figure.

    That is text lying mostly inside the box, and short labels beside or below
    it. Text above the graphics is a heading or body text, and text at or below
    the caption never belongs to the figure.
    """
    result = box
    for block in blocks:
        if block is caption or block.rect[3] > caption.rect[1] + 2:
            continue
        inside = overlap_fraction(block.rect, box) >= 0.5
        short = len(block.text) <= LABEL_LENGTH and block.rect[1] >= box[1] - 2
        label = short and near(block.rect, box, LABEL_MARGIN)
        if inside or label:
            result = union(result, block.rect)
    return result


def locate(page: pymupdf.Page, word: str = "Figur") -> list[tuple[str, str, Rect]]:
    """Find (number, caption, bounding box) for every figure caption on the page.

    A caption with no graphics above or below it yields no figure.
    """
    blocks = page_blocks(page)
    groups = cluster(graphics(page))
    found = []
    for block in blocks:
        numbers = caption_numbers(block.text, word)
        candidates = [g for g in groups if horizontal_overlap(g, block.rect) > 0]
        if not numbers or not candidates:
            continue

        def gap(group: Rect, caption: Rect = block.rect) -> float:
            above = caption[1] - group[3]
            return above if above >= -6 else 1000 + abs(group[1] - caption[3])

        nearest = sorted(candidates, key=gap)[: len(numbers)]
        caption = " ".join(block.text.replace("**", "").split())
        for number, box in zip(numbers, sorted(nearest), strict=False):
            box = with_labels(box, blocks, block)
            if (box[1] + box[3]) / 2 < block.rect[1]:  # figure above its caption: stop there
                box = (box[0], box[1], box[2], min(box[3] + 4, block.rect[1] - 1))
            found.append((number, caption, box))
    return found


def cut(pdf: Path, target_dir: Path, *, word: str = "Figur", dpi: int = 150) -> list[Figure]:
    """Write one image per captioned figure and an index. Returns the figures found."""
    document = pymupdf.open(pdf)
    target_dir.mkdir(parents=True, exist_ok=True)
    figures = []
    for page_number, page in enumerate(document, start=1):
        for number, caption, box in locate(page, word):
            rect = tuple(pymupdf.Rect(box) + (-4, -3, 4, 0) & page.rect)
            name = f"{pdf.stem}_p{page_number:03d}_fig{number.replace('.', '-')}.png"
            render(page, target_dir / name, dpi=dpi, clip=rect)
            figures.append(Figure(page_number, number, caption, rect))
    with (target_dir / f"{pdf.stem}_figures.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("file", "page", "number", "caption_in_source", "x0", "y0", "x1", "y1"))
        for figure in figures:
            name = f"{pdf.stem}_p{figure.page:03d}_fig{figure.number.replace('.', '-')}.png"
            box = [round(v, 1) for v in figure.rect]
            writer.writerow((name, figure.page, figure.number, figure.caption, *box))
    return figures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("cut",))
    parser.add_argument("pdf", type=Path)
    parser.add_argument("target_dir", type=Path)
    parser.add_argument("--word", default="Figur", help="caption word, e.g. Figur or Figure")
    parser.add_argument("--dpi", type=int, default=150)
    args = parser.parse_args(argv)
    figures = cut(args.pdf, args.target_dir, word=args.word, dpi=args.dpi)
    print(f"{len(figures)} figures written to {args.target_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
