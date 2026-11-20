"""Dated snapshots of small public data series used for context.

    python -m syskit.public snapshot

writes each series to ``data/public/<name>_<YYYYMMDD>.csv`` and records it in
``data/public/index.csv``. Analyses read the snapshot, never the live service.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

from syskit.paths import data_dir

YEARS = [str(year) for year in range(2004, 2017)]
SERIES = {
    # Statistics Norway, table 03014: consumer price index, all items, annual, 2015 = 100.
    "ssb_cpi": {
        "url": "https://data.ssb.no/api/v0/en/table/03014",
        "query": {
            "query": [
                {"code": "Konsumgrp", "selection": {"filter": "item", "values": ["TOTAL"]}},
                {"code": "ContentsCode", "selection": {"filter": "item", "values": ["KpiAar"]}},
                {"code": "Tid", "selection": {"filter": "item", "values": YEARS}},
            ],
            "response": {"format": "csv"},
        },
    },
    # FRED series DCOILBRENTEU: Brent crude, Europe, USD per barrel, annual average.
    "fred_brent": {
        "url": (
            "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DCOILBRENTEU"
            "&cosd=2004-01-01&coed=2016-12-31&fq=Annual&fam=avg"
        ),
        "query": None,
    },
}
INDEX_FIELDS = ("file", "series", "retrieved_utc", "bytes", "sha256", "url")


def fetch(url: str, query: dict | None, *, timeout: float = 60, attempts: int = 3) -> bytes:
    data = json.dumps(query).encode() if query else None
    headers = {"User-Agent": "curl/8.5.0", "Accept": "*/*"}
    request = urllib.request.Request(url, data=data, headers=headers)
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = response.read()
            break
        except OSError:
            if attempt == attempts:
                raise
    if b"," not in payload[:400] or payload.lstrip()[:1] == b"<":
        raise ValueError(f"{url}: response is not CSV")
    return payload


def snapshot(target_dir: Path, stamp: dt.datetime) -> list[Path]:
    """Download every series. Nothing is written unless all downloads succeed."""
    payloads = {name: fetch(spec["url"], spec["query"]) for name, spec in SERIES.items()}
    target_dir.mkdir(parents=True, exist_ok=True)
    index = target_dir / "index.csv"
    new_index = not index.exists()
    written = []
    with index.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        if new_index:
            writer.writerow(INDEX_FIELDS)
        for name, payload in payloads.items():
            path = target_dir / f"{name}_{stamp:%Y%m%d}.csv"
            path.write_bytes(payload)
            digest = hashlib.sha256(payload).hexdigest()
            row = (path.name, name, f"{stamp:%Y-%m-%dT%H:%M:%SZ}", len(payload), digest)
            writer.writerow((*row, SERIES[name]["url"]))
            written.append(path)
    return written


def latest(name: str, target_dir: Path | None = None) -> Path:
    """The most recent snapshot of a series."""
    files = sorted((target_dir or data_dir() / "public").glob(f"{name}_*.csv"))
    if not files:
        raise FileNotFoundError(f"no snapshot of {name}; run 'python -m syskit.public snapshot'")
    return files[-1]


def parse_series(rows: list[list[str]]) -> dict[int, float]:
    """Year -> value from a table that has the years down a column or across the header."""
    header, body = rows[0], rows[1:]
    across = [cell[-4:] for cell in header[1:]]
    if across and all(year.isdigit() for year in across):
        return {int(year): float(value) for year, value in zip(across, body[0][1:], strict=True)}
    return {int(row[0][:4]): float(row[-1]) for row in body if row and row[0][:4].isdigit()}


def read_series(name: str, target_dir: Path | None = None) -> dict[int, float]:
    """The most recent snapshot of a series as year -> value."""
    with latest(name, target_dir).open(newline="", encoding="utf-8-sig") as handle:
        return parse_series(list(csv.reader(handle)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("snapshot",))
    parser.parse_args(argv)
    try:
        written = snapshot(data_dir() / "public", dt.datetime.now(dt.UTC))
    except (OSError, ValueError) as error:
        print(f"snapshot failed: {error}", file=sys.stderr)
        return 1
    for path in written:
        print(f"written: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
