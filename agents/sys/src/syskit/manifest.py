"""Checksummed inventory of the raw data.

The manifest lets each machine confirm it holds exactly the same raw files.

    python -m syskit.manifest create    # write data/manifest.csv from the raw data
    python -m syskit.manifest verify    # compare the raw data against the manifest
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path

from syskit.paths import data_dir, volve_data

FIELDS = ("path", "size", "sha256")


@dataclass(frozen=True)
class Entry:
    path: str
    size: int
    sha256: str


@dataclass
class Diff:
    missing: list[str]
    changed: list[str]
    extra: list[str]

    @property
    def clean(self) -> bool:
        return not (self.missing or self.changed or self.extra)


def file_sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def scan(root: Path, *, hashes: bool = True) -> list[Entry]:
    """List every file under ``root``, sorted by path."""
    files = sorted(p for p in root.rglob("*") if p.is_file())
    return [
        Entry(p.relative_to(root).as_posix(), p.stat().st_size, file_sha256(p) if hashes else "")
        for p in files
    ]


def write(entries: list[Entry], manifest: Path) -> None:
    manifest.parent.mkdir(parents=True, exist_ok=True)
    with manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(FIELDS)
        writer.writerows((e.path, e.size, e.sha256) for e in entries)


def read(manifest: Path) -> list[Entry]:
    with manifest.open(newline="", encoding="utf-8") as handle:
        return [Entry(r["path"], int(r["size"]), r["sha256"]) for r in csv.DictReader(handle)]


def compare(recorded: list[Entry], root: Path, *, hashes: bool = True) -> Diff:
    """Compare the files under ``root`` with the recorded entries.

    Sizes are always compared. Hashes are computed only for files whose size
    matches, and only when ``hashes`` is true.
    """
    expected = {e.path: e for e in recorded}
    present = {e.path: e for e in scan(root, hashes=False)}
    diff = Diff(
        missing=sorted(expected.keys() - present.keys()),
        changed=[],
        extra=sorted(present.keys() - expected.keys()),
    )
    for path in sorted(expected.keys() & present.keys()):
        same = expected[path].size == present[path].size
        if same and hashes:
            same = expected[path].sha256 == file_sha256(root / path)
        if not same:
            diff.changed.append(path)
    return diff


def _report(diff: Diff, file=sys.stdout) -> None:
    groups = (("missing", diff.missing), ("changed", diff.changed), ("extra", diff.extra))
    for label, paths in groups:
        for path in paths:
            print(f"  {label:8s} {path}", file=file)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("create", "verify"))
    parser.add_argument("--quick", action="store_true", help="verify sizes only, skip hashing")
    args = parser.parse_args(argv)

    root = volve_data()
    manifest = data_dir() / "manifest.csv"

    if args.command == "create":
        entries = scan(root)
        if manifest.exists():
            previous = {e.path: e for e in read(manifest)}
            current = {e.path: e for e in entries}
            _report(
                Diff(
                    missing=sorted(previous.keys() - current.keys()),
                    changed=sorted(
                        p for p in previous.keys() & current.keys() if previous[p] != current[p]
                    ),
                    extra=sorted(current.keys() - previous.keys()),
                )
            )
        write(entries, manifest)
        total = sum(e.size for e in entries)
        print(f"manifest written: {len(entries)} files, {total / 1e9:.2f} GB, from {root}")
        return 0

    if not manifest.exists():
        print(f"no manifest at {manifest}; run 'create' first", file=sys.stderr)
        return 1
    recorded = read(manifest)
    diff = compare(recorded, root, hashes=not args.quick)
    if diff.clean:
        mode = "sizes" if args.quick else "sizes and hashes"
        print(f"raw data matches the manifest: {len(recorded)} files ({mode}), {root}")
        return 0
    print(f"raw data differs from the manifest ({root}):", file=sys.stderr)
    _report(diff, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
