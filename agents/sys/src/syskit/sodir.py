"""Snapshots of the Sodir FactPages tables.

Analyses read a dated snapshot, never the live service.

    python -m syskit.sodir snapshot        # download today's snapshot to data/sodir/<YYYYMMDD>/
    python -m syskit.sodir facts           # write data/facts/sodir.csv from the latest snapshot
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import shutil
import sys
import urllib.request
from pathlib import Path

from syskit.facts import COLUMNS
from syskit.paths import data_dir

URL = (
    "https://factpages.sodir.no/public?/Factpages/external/tableview/{table}"
    "&rs:Command=Render&rc:Toolbar=false&rc:Parameters=f&IpAddress=not_used"
    "&CultureCode=en&rs:Format=CSV&Top100=false"
)
TABLES = (
    "field_production_yearly",
    "field_production_monthly",
    "field_investment_yearly",
    "field_reserves",
    "field_in_place_volumes",
    "field_description",
    "field_activity_status_hst",
    "field_licensee_hst",
    "wellbore_development_all",
)
FIELD = "VOLVE"
INDEX_FIELDS = ("table", "retrieved_utc", "bytes", "rows", "sha256", "url")

# Units as stated on the Sodir field page (checked 2026-11-19).
_PRODUCTION = {
    "prfPrdOilNetMillSm3": ("oil_production", "MSm3"),
    "prfPrdGasNetBillSm3": ("gas_production", "GSm3"),
    "prfPrdNGLNetMillSm3": ("ngl_production", "MSm3"),
    "prfPrdCondensateNetMillSm3": ("condensate_production", "MSm3"),
    "prfPrdOeNetMillSm3": ("oe_production", "MSm3oe"),
    "prfPrdProducedWaterInFieldMillSm3": ("water_production", "MSm3"),
}
_RESERVES = {
    "fldRecoverableOil": ("recoverable_oil", "MSm3"),
    "fldRecoverableGas": ("recoverable_gas", "GSm3"),
    "fldRecoverableNGL": ("recoverable_ngl", "Mt"),
    "fldRecoverableCondensate": ("recoverable_condensate", "MSm3"),
    "fldRecoverableOE": ("recoverable_oe", "MSm3oe"),
}
_IN_PLACE = {
    "fldInplaceOil": ("in_place_oil", "MSm3"),
    "fldInplaceAssLiquid": ("in_place_associated_liquid", "MSm3"),
    "fldInplaceAssGas": ("in_place_associated_gas", "GSm3"),
    "fldInplaceFreeGas": ("in_place_free_gas", "GSm3"),
}


def table_url(table: str) -> str:
    return URL.format(table=table)


def fetch(table: str, *, timeout: float = 180) -> bytes:
    """Download one table as CSV and check that it looks like a table."""
    request = urllib.request.Request(table_url(table), headers={"User-Agent": "syskit-sodir"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read()
    first_line = payload[:2000].decode("utf-8-sig", errors="replace").splitlines()[0:1]
    if not first_line or "," not in first_line[0] or "<" in first_line[0]:
        raise ValueError(f"{table}: response is not a CSV table")
    return payload


def snapshot(sodir_dir: Path, stamp: dt.datetime, *, force: bool = False) -> Path:
    """Download every table into ``<sodir_dir>/<YYYYMMDD>/`` with an index.

    The snapshot directory appears only when every table has been downloaded.
    """
    target = sodir_dir / stamp.strftime("%Y%m%d")
    if target.exists() and not force:
        raise FileExistsError(f"snapshot {target.name} already exists; use --force to replace it")
    staging = sodir_dir / f".{target.name}.partial"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    try:
        index = []
        for table in TABLES:
            payload = fetch(table)
            (staging / f"{table}.csv").write_bytes(payload)
            index.append(
                (
                    table,
                    stamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    len(payload),
                    sum(1 for line in payload.splitlines() if line.strip()) - 1,
                    hashlib.sha256(payload).hexdigest(),
                    table_url(table),
                )
            )
        with (staging / "index.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(INDEX_FIELDS)
            writer.writerows(index)
        shutil.rmtree(target, ignore_errors=True)
        staging.rename(target)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return target


def latest(sodir_dir: Path) -> Path:
    """Return the most recent snapshot directory."""
    snapshots = sorted(p for p in sodir_dir.iterdir() if p.is_dir() and p.name.isdigit())
    if not snapshots:
        raise FileNotFoundError(f"no Sodir snapshot in {sodir_dir}; run 'snapshot' first")
    return snapshots[-1]


def read_table(table: str, snapshot_dir: Path) -> list[dict[str, str]]:
    with (snapshot_dir / f"{table}.csv").open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _iso(date_ddmmyyyy: str) -> str:
    return dt.datetime.strptime(date_ddmmyyyy, "%d.%m.%Y").strftime("%Y-%m-%d")


def field_facts(field: str, snapshot_dir: Path) -> list[dict[str, str]]:
    """Return the facts Sodir holds for one field, in fact-register form."""
    name = field.upper()
    subject = name.title()
    where = f"snapshot {snapshot_dir.name}"
    facts: list[dict[str, str]] = []

    def add(fact_id, quantity, value, unit, basis, as_of, table, method="read", note=""):
        facts.append(
            dict(
                zip(
                    COLUMNS,
                    (
                        f"sodir.{fact_id}",
                        quantity,
                        value,
                        unit,
                        basis,
                        as_of,
                        subject,
                        "sodir",
                        f"{where} {table}",
                        method,
                        "high",
                        note,
                    ),
                    strict=True,
                )
            )
        )

    production = sorted(
        (
            r
            for r in read_table("field_production_yearly", snapshot_dir)
            if r["prfInformationCarrier"] == name
        ),
        key=lambda r: int(r["prfYear"]),
    )
    for row in production:
        for column, (quantity, unit) in _PRODUCTION.items():
            add(
                f"{quantity}.{row['prfYear']}",
                quantity,
                row[column],
                unit,
                "actual",
                row["prfYear"],
                "field_production_yearly",
            )
    if production:
        years = f"{production[0]['prfYear']}-{production[-1]['prfYear']}"
        total = sum(float(r["prfPrdOilNetMillSm3"]) for r in production)
        add(
            "oil_production.total",
            "oil_production_cumulative",
            f"{total:.3f}",
            "MSm3",
            "actual",
            production[-1]["prfYear"],
            "field_production_yearly",
            "computed",
            f"sum of yearly values {years}",
        )

    investments = sorted(
        (
            r
            for r in read_table("field_investment_yearly", snapshot_dir)
            if r["prfInformationCarrier"] == name
        ),
        key=lambda r: int(r["prfYear"]),
    )
    for row in investments:
        add(
            f"investment.{row['prfYear']}",
            "investment",
            row["prfInvestmentsMillNOK"],
            "MNOK nominal",
            "actual",
            row["prfYear"],
            "field_investment_yearly",
        )
    if investments:
        years = f"{investments[0]['prfYear']}-{investments[-1]['prfYear']}"
        total = sum(float(r["prfInvestmentsMillNOK"]) for r in investments)
        add(
            "investment.total",
            "investment_cumulative",
            f"{total:.0f}",
            "MNOK nominal",
            "actual",
            investments[-1]["prfYear"],
            "field_investment_yearly",
            "computed",
            f"sum of yearly values {years}",
        )

    reserves = sorted(
        (r for r in read_table("field_reserves", snapshot_dir) if r["fldName"] == name),
        key=lambda r: int(r["fldVersion"]),
    )
    for row in reserves:
        for column, (quantity, unit) in _RESERVES.items():
            add(
                f"{quantity}.{row['fldVersion']}",
                quantity,
                row[column],
                unit,
                "estimate",
                _iso(row["fldDateOffResEstDisplay"]),
                "field_reserves",
            )

    for row in read_table("field_in_place_volumes", snapshot_dir):
        if row["fldName"] == name:
            for column, (quantity, unit) in _IN_PLACE.items():
                add(
                    quantity,
                    quantity,
                    row[column],
                    unit,
                    "estimate",
                    _iso(row["fldDateOffResEstDisplay"]),
                    "field_in_place_volumes",
                )
    return facts


def write_facts(facts: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(facts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("snapshot", "facts"))
    parser.add_argument("--force", action="store_true", help="replace an existing snapshot")
    args = parser.parse_args(argv)
    sodir_dir = data_dir() / "sodir"

    if args.command == "snapshot":
        try:
            target = snapshot(sodir_dir, dt.datetime.now(dt.UTC), force=args.force)
        except (OSError, ValueError) as error:
            print(f"snapshot failed: {error}", file=sys.stderr)
            return 1
        size = sum(p.stat().st_size for p in target.glob("*.csv"))
        print(f"snapshot written: {target} ({len(TABLES)} tables, {size / 1e6:.1f} MB)")
        return 0

    source = latest(sodir_dir)
    facts = field_facts(FIELD, source)
    if not facts:
        print(f"no rows for field '{FIELD}' in snapshot {source.name}", file=sys.stderr)
        return 1
    write_facts(facts, data_dir() / "facts" / "sodir.csv")
    print(f"{len(facts)} facts for {FIELD} written from snapshot {source.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
