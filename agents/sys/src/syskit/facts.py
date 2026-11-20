"""Validation of the fact register.

Facts are stored one per row in ``data/facts/<source-id>.csv``. The sources
are listed in ``data/sources.csv``.

    python -m syskit.facts validate
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

from syskit.paths import data_dir

COLUMNS = (
    "fact_id",
    "quantity",
    "value",
    "unit",
    "basis",
    "as_of",
    "subject",
    "source",
    "locator",
    "method",
    "confidence",
    "note",
)
REQUIRED = COLUMNS[:-1]
METHODS = frozenset({"read", "vision", "digitised", "computed", "translated"})
CONFIDENCE = frozenset({"high", "medium", "low"})
TEXT_UNIT = "text"

_AS_OF = re.compile(r"\d{4}(-\d{2}(-\d{2})?)?")
_FACT_ID = re.compile(r"[a-z0-9_]+(\.[a-z0-9_-]+)+")


def read(source: str, facts_dir: Path | None = None) -> dict[str, float | str]:
    """Values of one source's facts by fact id; numbers as floats, text as written."""
    path = (facts_dir or data_dir() / "facts") / f"{source}.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {
        row["fact_id"]: row["value"] if row["unit"] == TEXT_UNIT else float(row["value"])
        for row in rows
    }


def load_sources(sources_file: Path) -> set[str]:
    with sources_file.open(newline="", encoding="utf-8") as handle:
        return {row["id"] for row in csv.DictReader(handle)}


def _is_number(text: str) -> bool:
    try:
        float(text)
    except ValueError:
        return False
    return True


def check_row(row: dict[str, str], *, file_source: str, sources: set[str]) -> list[str]:
    """Return the problems found in one row."""
    problems = [f"'{name}' is empty" for name in REQUIRED if not (row.get(name) or "").strip()]
    if problems:
        return problems

    if row["source"] not in sources:
        problems.append(f"unknown source '{row['source']}'; add it to sources.csv first")
    if row["source"] != file_source:
        problems.append(f"source '{row['source']}' does not belong in {file_source}.csv")
    if not _FACT_ID.fullmatch(row["fact_id"]) or not row["fact_id"].startswith(f"{file_source}."):
        problems.append(f"fact_id '{row['fact_id']}' must look like '{file_source}.<name>'")
    if row["method"] not in METHODS:
        problems.append(f"method '{row['method']}' is not one of {sorted(METHODS)}")
    if row["confidence"] not in CONFIDENCE:
        problems.append(f"confidence '{row['confidence']}' is not one of {sorted(CONFIDENCE)}")
    if not _AS_OF.fullmatch(row["as_of"]):
        problems.append(f"as_of '{row['as_of']}' is not YYYY, YYYY-MM or YYYY-MM-DD")
    if row["unit"] != TEXT_UNIT and not _is_number(row["value"]):
        problems.append(f"value '{row['value']}' is not a number (use unit 'text' for text)")
    return problems


def validate_file(path: Path, sources: set[str], seen_ids: dict[str, str]) -> list[str]:
    """Return the problems found in one fact file, as ``file:line: message``."""
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != COLUMNS:
            return [f"{path.name}:1: header must be exactly {','.join(COLUMNS)}"]
        problems = []
        for row in reader:
            where = f"{path.name}:{reader.line_num}"
            problems += [
                f"{where}: {p}" for p in check_row(row, file_source=path.stem, sources=sources)
            ]
            fact_id = row.get("fact_id") or ""
            if fact_id in seen_ids:
                problems.append(f"{where}: fact_id '{fact_id}' already used at {seen_ids[fact_id]}")
            elif fact_id:
                seen_ids[fact_id] = where
        return problems


def validate_register(facts_dir: Path, sources_file: Path) -> tuple[int, list[str]]:
    """Validate every fact file. Returns (number of facts, problems)."""
    sources = load_sources(sources_file)
    seen_ids: dict[str, str] = {}
    problems: list[str] = []
    for path in sorted(facts_dir.glob("*.csv")):
        problems += validate_file(path, sources, seen_ids)
    return len(seen_ids), problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("validate",))
    parser.parse_args(argv)

    count, problems = validate_register(data_dir() / "facts", data_dir() / "sources.csv")
    if problems:
        print(f"fact register has {len(problems)} problem(s):", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1
    print(f"fact register is valid: {count} facts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
