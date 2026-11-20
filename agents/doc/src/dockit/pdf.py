"""Deterministic extraction from PDF pages: text in reading order, highlights, renders.

This is the layer the language work builds on. It never interprets content;
it reports what is on the page and where.

    python -m dockit.pdf prepare <pdf> <work-dir> [--dpi 150]

writes ``text/page_NNN.txt`` (text in reading order, highlighted words wrapped
in ``**``) and ``png/page_NNN.png`` (page image) for every page.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import pymupdf

Rect = tuple[float, float, float, float]


@dataclass(frozen=True)
class Word:
    rect: Rect
    text: str
    block: int
    line: int
    highlighted: bool = False


@dataclass(frozen=True)
class Block:
    rect: Rect
    text: str


def overlap_fraction(inner: Rect, outer: Rect) -> float:
    """Fraction of ``inner``'s area that lies inside ``outer``."""
    width = min(inner[2], outer[2]) - max(inner[0], outer[0])
    height = min(inner[3], outer[3]) - max(inner[1], outer[1])
    area = (inner[2] - inner[0]) * (inner[3] - inner[1])
    if width <= 0 or height <= 0 or area <= 0:
        return 0.0
    return width * height / area


def highlight_rects(page: pymupdf.Page) -> list[Rect]:
    """Rectangles covered by highlight annotations, one per highlighted line segment."""
    rects: list[Rect] = []
    for annotation in page.annots() or []:
        if annotation.type[1] != "Highlight":
            continue
        points = annotation.vertices or []
        for start in range(0, len(points) - 3, 4):
            quad = points[start : start + 4]
            xs, ys = [p[0] for p in quad], [p[1] for p in quad]
            rects.append((min(xs), min(ys), max(xs), max(ys)))
    return rects


def page_words(page: pymupdf.Page, *, threshold: float = 0.5) -> list[Word]:
    """Words on the page, flagged when at least ``threshold`` of the word is highlighted."""
    marks = highlight_rects(page)
    words = []
    for x0, y0, x1, y1, text, block, line, _ in page.get_text("words"):
        rect = (x0, y0, x1, y1)
        lit = any(overlap_fraction(rect, mark) >= threshold for mark in marks)
        words.append(Word(rect, text, block, line, lit))
    return words


def mark_runs(words: list[Word]) -> str:
    """Join words into text, wrapping each run of highlighted words in ``**``."""
    pieces: list[str] = []
    inside = False
    for word in words:
        if word.highlighted and not inside:
            pieces.append("**" + word.text)
        elif not word.highlighted and inside:
            pieces[-1] += "**"
            pieces.append(word.text)
        else:
            pieces.append(word.text)
        inside = word.highlighted
    if inside:
        pieces[-1] += "**"
    return " ".join(pieces)


def page_blocks(page: pymupdf.Page) -> list[Block]:
    """Text blocks of the page; lines are kept, highlighted words are marked."""
    grouped: dict[int, dict[int, list[Word]]] = {}
    for word in page_words(page):
        grouped.setdefault(word.block, {}).setdefault(word.line, []).append(word)
    blocks = []
    for lines in grouped.values():
        words = [w for line in lines.values() for w in line]
        rect = (
            min(w.rect[0] for w in words),
            min(w.rect[1] for w in words),
            max(w.rect[2] for w in words),
            max(w.rect[3] for w in words),
        )
        text = "\n".join(mark_runs(line) for line in lines.values())
        blocks.append(Block(rect, text))
    return blocks


def reading_order(blocks: list[Block], page_width: float, *, gutter: float = 12.0) -> list[Block]:
    """Order blocks for a page that mixes full-width and two-column parts.

    A block that crosses the middle of the page is full width. Full-width blocks
    split the page into bands; within a band the left column is read before the
    right one.
    """
    middle = page_width / 2

    def full_width(block: Block) -> bool:
        return block.rect[0] < middle - gutter and block.rect[2] > middle + gutter

    ordered: list[Block] = []
    band: list[Block] = []

    def flush() -> None:
        left = sorted((b for b in band if b.rect[0] < middle), key=lambda b: (b.rect[1], b.rect[0]))
        right = sorted(
            (b for b in band if b.rect[0] >= middle), key=lambda b: (b.rect[1], b.rect[0])
        )
        ordered.extend(left + right)
        band.clear()

    for block in sorted(blocks, key=lambda b: (b.rect[1], b.rect[0])):
        if full_width(block):
            flush()
            ordered.append(block)
        else:
            band.append(block)
    flush()
    return ordered


def page_text(page: pymupdf.Page) -> str:
    """Text of the page in reading order, blocks separated by blank lines."""
    blocks = reading_order(page_blocks(page), page.rect.width)
    return "\n\n".join(block.text for block in blocks) + "\n"


def render(page: pymupdf.Page, target: Path, *, dpi: int = 150, clip: Rect | None = None) -> None:
    """Write the page, or the part of it inside ``clip``, as an image."""
    target.parent.mkdir(parents=True, exist_ok=True)
    pixmap = page.get_pixmap(dpi=dpi, clip=pymupdf.Rect(clip) if clip else None, annots=False)
    if target.suffix.lower() in (".jpg", ".jpeg"):
        pixmap.save(target, jpg_quality=70)
    else:
        pixmap.save(target)


def prepare(pdf: Path, work_dir: Path, *, dpi: int = 150, image_format: str = "png") -> int:
    """Write the text and the image of every page. Returns the number of pages."""
    document = pymupdf.open(pdf)
    (work_dir / "text").mkdir(parents=True, exist_ok=True)
    for number, page in enumerate(document, start=1):
        (work_dir / "text" / f"page_{number:03d}.txt").write_text(page_text(page), encoding="utf-8")
        render(page, work_dir / image_format / f"page_{number:03d}.{image_format}", dpi=dpi)
    return len(document)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("prepare",))
    parser.add_argument("pdf", type=Path)
    parser.add_argument("work_dir", type=Path)
    parser.add_argument("--dpi", type=int, default=150)
    parser.add_argument("--format", choices=("png", "jpg"), default="png")
    args = parser.parse_args(argv)
    pages = prepare(args.pdf, args.work_dir, dpi=args.dpi, image_format=args.format)
    print(f"{pages} pages written to {args.work_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
