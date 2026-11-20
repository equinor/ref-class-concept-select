"""Assemble page files into one Markdown document, and check them first.

    python -m dockit.assemble <pages-dir> <target.md> --title "…" --source "…" [--text-dir DIR]

``pages-dir`` holds ``page_NNN.md`` files written under the page-conversion
rules. With ``--text-dir`` (the extracted text of a digitally created
document) the digits and the highlights of every page are compared with the
source text.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

PAGE_TYPES = ("text", "table", "figure", "mixed", "contents", "cover", "blank")
_IMAGE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
_COMMENT = re.compile(r"<!--.*?-->", re.S)
_BOLD = re.compile(r"\*\*(.+?)\*\*", re.S)


_GROUPING = re.compile(r"(?<=\d)[ .,\u00a0](?=\d{3}(?!\d))")


def digit_runs(text: str) -> Counter:
    """Every number in ``text`` as runs of digits, counted, whatever its separators.

    A separator followed by exactly three digits is dropped, so ``9.000``,
    ``9 000`` and ``9000`` are the same; ``19,9`` and ``19.9`` both give ``19``
    and ``9``. Decimal commas, decimal points and the way thousands are
    grouped therefore do not matter.
    """
    return Counter(re.findall(r"\d+", _GROUPING.sub("", text)))


def body(markdown: str) -> str:
    """The page content without comments and without image file names."""
    return _IMAGE.sub(lambda m: m.group(0).split("](")[0], _COMMENT.sub("", markdown))


def bold_length(markdown: str) -> int:
    return sum(len(span) for span in _BOLD.findall(markdown))


def check_page(number: int, markdown: str, target_dir: Path) -> list[str]:
    """Problems with the form of one page file."""
    problems = []
    lines = markdown.splitlines()
    if not lines or lines[0].strip() != f"<!-- page {number} -->":
        problems.append("first line is not the page marker")
    kind = re.fullmatch(r"<!-- type: (\w+) -->", lines[1].strip()) if len(lines) > 1 else None
    if not kind or kind.group(1) not in PAGE_TYPES:
        problems.append("second line is not a valid page type")
    for link in _IMAGE.findall(markdown):
        if not (target_dir / link).exists():
            problems.append(f"image not found: {link}")
    return problems


def check_against_text(markdown: str, text: str, ignore: Counter) -> list[str]:
    """Compare digits and highlights of a page with the text extracted from the source."""
    problems = []
    source, page = digit_runs(text) - ignore, digit_runs(body(markdown))
    missing = source - page
    if missing:
        listed = " ".join(sorted(missing.elements(), key=lambda run: (len(run), run)))
        problems.append(f"digits in the source but not in the page: {listed}")
    highlighted = bold_length(text)
    marked = bold_length(markdown)
    if bool(highlighted) != bool(marked):
        problems.append(f"highlighted characters in source {highlighted}, bold in page {marked}")
    elif highlighted and not 0.5 <= marked / highlighted <= 2.0:
        problems.append(f"bold length {marked} far from highlighted length {highlighted}")
    return problems


def page_type(markdown: str) -> str:
    match = re.search(r"<!-- type: (\w+) -->", markdown)
    return match.group(1) if match else ""


def assemble(pages: list[str], title: str, source: str, notes: list[str]) -> str:
    """Join the pages under a header. Page markers stay, so facts can cite pages."""
    header = [f"# {title}", "", f"Source: {source}", ""]
    header += [f"- {note}" for note in notes]
    return "\n".join(header) + "\n\n" + "\n\n".join(page.strip() for page in pages) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pages_dir", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--note", action="append", default=[], help="conversion note (repeatable)")
    parser.add_argument("--text-dir", type=Path, help="extracted text of a digital document")
    parser.add_argument("--ignore", default="", help="digit runs of running headers, e.g. '2005'")
    parser.add_argument("--pages", type=int, required=True, help="number of pages expected")
    args = parser.parse_args(argv)

    pages, failed = [], False
    for number in range(1, args.pages + 1):
        path = args.pages_dir / f"page_{number:03d}.md"
        if not path.exists():
            print(f"page {number}: missing", file=sys.stderr)
            failed = True
            continue
        markdown = path.read_text(encoding="utf-8")
        problems = check_page(number, markdown, args.target.parent)
        if args.text_dir:
            text = (args.text_dir / f"page_{number:03d}.txt").read_text(encoding="utf-8")
            ignore = Counter(args.ignore.split()) + Counter([str(number)])
            problems += check_against_text(markdown, text, ignore)
        for problem in problems:
            print(f"page {number}: {problem}", file=sys.stderr)
        failed = failed or any("missing" in p or "marker" in p or "image" in p for p in problems)
        pages.append(markdown)
    if failed:
        print("not assembled: fix the pages above", file=sys.stderr)
        return 1
    args.target.parent.mkdir(parents=True, exist_ok=True)
    args.target.write_text(assemble(pages, args.title, args.source, args.note), encoding="utf-8")
    kinds = Counter(page_type(page) for page in pages)
    print(f"{args.target}: {len(pages)} pages ({', '.join(f'{k} {v}' for k, v in kinds.items())})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
