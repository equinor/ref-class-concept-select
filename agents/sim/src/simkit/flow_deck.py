"""Build the OPM Flow version of the Volve Eclipse deck.

The released deck does not run in OPM Flow. This module writes new versions of
the four files that have to change, beside the originals and with ``_FLOW`` in
the name. The originals are never modified.

    python -m simkit.flow_deck build

Every change is listed in ``DATA_EDITS``, ``RSVD_EDITS`` and ``SCHEDULE_EDITS``
below, with the reason. The grid file is the original with the corner-depth
shifts of the ADDZCORN keyword applied, taken from the geometry Eclipse wrote
to ``VOLVE_2016.GRID``.
"""

from __future__ import annotations

import argparse
import csv
import difflib
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from syskit import manifest
from syskit.paths import data_dir, repo_root, volve_data

DECK_DIR = "eclipse_model/sim_model_PPA-eclipse"
SUFFIX = "_FLOW"
ENCODING = "latin-1"  # the deck contains a few non-ASCII bytes; latin-1 round-trips them

DATA = "VOLVE_2016.DATA"
GRID = "GRID_postF1B_Nov2013_locupd_12112013.grdecl"
RSVD = "RSVD_input_new_combined_020610_perch_water_2914m.E100"
SCHEDULE = "SCH_010916_10DAYS.SCH"
ECLIPSE_GRID = "VOLVE_2016.GRID"
DIMS = (108, 100, 63)


def flow_name(name: str) -> str:
    """Name of the Flow version of a deck file: ``_FLOW`` before the extension."""
    stem, dot, extension = name.rpartition(".")
    return f"{stem}{SUFFIX}{dot}{extension}"


@dataclass(frozen=True)
class Edit:
    """One change to a text file, anchored to the original line numbers (1-based).

    The original lines ``first``..``last`` are kept as comments. ``replacement``
    lines, if any, are written in their place.
    """

    first: int
    last: int
    expect: str  # text the original lines must contain
    reason: str
    replacement: tuple[str, ...] = ()


DATA_EDITS = (
    Edit(
        99,
        99,
        "'THPRES' 'QUIESC'    'MOBILE'   /",
        "Flow does not implement the QUIESC and MOBILE equilibration options.",
        (" 'THPRES' /",),
    ),
    Edit(
        179,
        179,
        f"'{GRID}'",
        "Grid file with the ADDZCORN corner-depth shifts applied.",
        (f" '{flow_name(GRID)}' /",),
    ),
    Edit(
        480,
        481,
        "'FAULT_NW-15NOV13.GRDECL'",
        "Flow does not implement ADDZCORN; these shifts are in the _FLOW grid file.",
    ),
    Edit(486, 487, "'CONTACT_MAIN-NW-AP2014.GRDECL'", "ADDZCORN, as above."),
    Edit(492, 493, "'FAULT_MAIN-F14-AP2014.GRDECL'", "ADDZCORN, as above."),
    Edit(498, 499, "'FAULT_MAIN-F12-F14-AP2014.GRDECL'", "ADDZCORN, as above."),
    Edit(
        620,
        620,
        "329        2.0E-5    / #13",
        "13th ROCK record; TABDIMS declares 12. Eclipse ignored it as spurious data.",
    ),
    Edit(
        806,
        806,
        f"'{RSVD}'",
        "RSVD without the 13th table.",
        (f"   '{flow_name(RSVD)}' /",),
    ),
    Edit(
        941,
        942,
        "PRIORITY",
        "Flow does not implement PRIORITY. The deck has no prioritisation group control.",
    ),
    Edit(
        981,
        981,
        f"'{SCHEDULE}'",
        "Schedule without the records that have no keyword.",
        (f" '{flow_name(SCHEDULE)}' /",),
    ),
)
RSVD_EDITS = (
    Edit(
        236,
        256,
        "2950.0      128.8",
        "13th RSVD table; EQLDIMS declares 12. Eclipse ignored it as spurious data.",
    ),
)
SCHEDULE_EDITS = (
    Edit(
        4869,
        4873,
        "'P-F-14'      'OPEN'      'ORAT'    298.200",
        "Well records with no WCONHIST keyword. Eclipse ignored them as spurious data.",
    ),
)


def apply_edits(lines: list[str], edits: tuple[Edit, ...]) -> list[str]:
    """Return ``lines`` with ``edits`` applied. Lines keep their line endings."""
    result = list(lines)
    for edit in sorted(edits, key=lambda e: e.first, reverse=True):
        original = lines[edit.first - 1 : edit.last]
        if not original or edit.expect not in "".join(original):
            found = original[0].strip() if original else "<end of file>"
            raise ValueError(f"line {edit.first}: expected '{edit.expect}', found '{found}'")
        ending = "\r\n" if original[0].endswith("\r\n") else "\n"
        block = [f"-- FLOW: {edit.reason}{ending}"]
        block += [f"--FLOW {line}" for line in original]
        block += [f"{line}{ending}" for line in edit.replacement]
        result[edit.first - 1 : edit.last] = block
    return result


def read_zcorn(lines: list[str]) -> tuple[np.ndarray, np.ndarray, int]:
    """Return the ZCORN values, the index of the first value on each line, and the first line.

    ``starts[n]`` is the position in the value array of the first value on line
    ``first_line + n`` (0-based line index into ``lines``).
    """
    keyword = next(i for i, line in enumerate(lines) if line.split()[:1] == ["ZCORN"])
    values: list[str] = []
    starts = []
    for line in lines[keyword + 1 :]:
        starts.append(len(values))
        tokens = line.split()
        if "/" in tokens:
            values += tokens[: tokens.index("/")]
            break
        values += tokens
    return np.array(values, dtype=np.float64), np.array(starts), keyword + 1


def corner_shifts(
    original: np.ndarray, final: np.ndarray, *, noise: float = 0.002
) -> tuple[dict[int, float], list[int]]:
    """Compare input corner depths with those Eclipse wrote out.

    Returns the shifts (value index -> shift, rounded to the centimetre) and the
    indices that differ without being a clean shift. ``final`` is single
    precision, so differences below ``noise`` are rounding.
    """
    delta = final - original
    changed = np.flatnonzero(np.abs(delta) > noise)
    rounded = np.round(delta[changed], 2)
    clean = np.abs(delta[changed] - rounded) < noise
    shifts = {int(i): float(s) for i, s in zip(changed[clean], rounded[clean], strict=True)}
    return shifts, [int(i) for i in changed[~clean]]


def shift_zcorn(lines: list[str], shifts: dict[int, float]) -> list[str]:
    """Return ``lines`` with the ZCORN values at the given indices shifted.

    Only the lines that hold a shifted value are rewritten; each new value takes
    the place and width of the old one.
    """
    values, starts, first_line = read_zcorn(lines)
    result = list(lines)
    by_line: dict[int, list[int]] = {}
    for index in shifts:
        by_line.setdefault(int(np.searchsorted(starts, index, side="right")) - 1, []).append(index)
    for offset, indices in by_line.items():
        line = lines[first_line + offset]
        spans = _token_spans(line)
        pieces, cursor = [], 0
        for index in sorted(indices):
            begin, end = spans[index - int(starts[offset])]
            new = f"{values[index] + shifts[index]:.3f}".rjust(end - begin)
            pieces += [line[cursor:begin], new]
            cursor = end
        result[first_line + offset] = "".join(pieces) + line[cursor:]
    return result


def _token_spans(line: str) -> list[tuple[int, int]]:
    spans, begin = [], None
    for position, char in enumerate(line):
        if char.isspace():
            if begin is not None:
                spans.append((begin, position))
                begin = None
        elif begin is None:
            begin = position
    if begin is not None:
        spans.append((begin, len(line)))
    return spans


def corner_of(index: int, dims: tuple[int, int, int] = DIMS) -> tuple[int, int, int, str]:
    """Translate a ZCORN value index into cell (i, j, k), 1-based, and the corner."""
    nx, ny, _ = dims
    layer, rest = divmod(index, 4 * nx * ny)
    k, bottom = divmod(layer, 2)
    row, column = divmod(rest, 2 * nx)
    j, y_side = divmod(row, 2)
    i, x_side = divmod(column, 2)
    corner = f"{'bottom' if bottom else 'top'} x{'+' if x_side else '-'} y{'+' if y_side else '-'}"
    return i + 1, j + 1, k + 1, corner


def zcorn_index(i, j, k, corner, dims: tuple[int, int, int] = DIMS):
    """Position in the ZCORN array of a cell corner. ``i``, ``j``, ``k`` are 0-based.

    ``corner`` counts 0-7 in Eclipse order: x-side, then y-side, then top/bottom.
    """
    nx, ny, _ = dims
    x_side, y_side, bottom = corner & 1, (corner >> 1) & 1, (corner >> 2) & 1
    return (2 * i + x_side) + 2 * nx * (2 * j + y_side) + 4 * nx * ny * (2 * k + bottom)


def eclipse_zcorn(grid_file: Path, dims: tuple[int, int, int] = DIMS) -> np.ndarray:
    """Return the corner depths Eclipse wrote to its GRID file, in ZCORN order.

    The file holds one CORNERS record (eight x, y, z triplets) per cell, in
    natural cell order. The records are read directly; the grid export of
    resdata returns undefined values for the first entries of such a file.
    """
    from resdata.resfile import ResdataFile  # imported here so text edits work without it

    nx, ny, nz = dims
    depths = np.empty((nx * ny * nz, 8))
    count = 0
    for keyword in ResdataFile(str(grid_file)):
        if keyword.get_name() == "CORNERS":
            depths[count] = keyword.numpy_view()[2::3]
            count += 1
    if count != nx * ny * nz:
        raise ValueError(f"{grid_file.name}: {count} cells, expected {nx * ny * nz}")
    cell = np.arange(count)
    i, j, k = cell % nx, (cell // nx) % ny, cell // (nx * ny)
    zcorn = np.empty(8 * count)
    for corner in range(8):
        zcorn[zcorn_index(i, j, k, corner, dims)] = depths[:, corner]
    return zcorn


def _read(path: Path) -> list[str]:
    return path.read_bytes().decode(ENCODING).splitlines(keepends=True)


def _write(path: Path, lines: list[str]) -> None:
    if SUFFIX not in path.name:
        raise ValueError(f"refusing to write {path.name}: not a {SUFFIX} file")
    path.write_bytes("".join(lines).encode(ENCODING))


def _check_originals(deck: Path, names: tuple[str, ...]) -> None:
    """Stop unless the files to be edited are the ones recorded in the manifest."""
    recorded = {e.path: e for e in manifest.read(data_dir() / "manifest.csv")}
    for name in names:
        entry = recorded[f"{DECK_DIR}/{name}"]
        path = deck / name
        if path.stat().st_size != entry.size or manifest.file_sha256(path) != entry.sha256:
            raise ValueError(f"{name} differs from the manifest; edits are tied to that version")


def _header(ending: str) -> list[str]:
    text = [
        "OPM Flow version of VOLVE_2016.DATA.",
        "Generated by simkit.flow_deck from the released deck; do not edit by hand.",
        "Every change is marked '-- FLOW:' with its reason; replaced or disabled",
        "original lines are kept as '--FLOW' comments. Nothing else differs.",
        "See agents/sim/out/volve_2016_flow/README.md in the repository.",
    ]
    return [f"-- FLOW: {line}{ending}" for line in text] + [f"--{ending}"]


def build(deck: Path, record_dir: Path) -> dict[str, int]:
    """Write the four ``_FLOW`` files into ``deck`` and the change record into ``record_dir``."""
    _check_originals(deck, (DATA, GRID, RSVD, SCHEDULE, ECLIPSE_GRID))
    record_dir.mkdir(parents=True, exist_ok=True)
    diff: list[str] = []
    summary = {}

    for name, edits in ((DATA, DATA_EDITS), (RSVD, RSVD_EDITS), (SCHEDULE, SCHEDULE_EDITS)):
        original = _read(deck / name)
        changed = apply_edits(original, edits)
        if name == DATA:
            changed = _header("\n") + changed
        _write(deck / flow_name(name), changed)
        diff += difflib.unified_diff(original, changed, name, flow_name(name), n=1)
        summary[flow_name(name)] = len(edits)

    grid_lines = _read(deck / GRID)
    original_zcorn, _, _ = read_zcorn(grid_lines)
    shifts, irregular = corner_shifts(original_zcorn, eclipse_zcorn(deck / ECLIPSE_GRID))
    if irregular:
        where = corner_of(irregular[0])
        raise ValueError(f"{len(irregular)} corner depths differ irregularly, first at {where}")

    shifted = shift_zcorn(grid_lines, shifts)
    new_zcorn, _, _ = read_zcorn(shifted)
    expected = original_zcorn.copy()
    expected[list(shifts)] += list(shifts.values())
    if not np.allclose(new_zcorn, expected, rtol=0, atol=1e-9):
        raise AssertionError("rewritten ZCORN does not equal the original plus the shifts")
    _write(deck / flow_name(GRID), shifted)
    summary[flow_name(GRID)] = len(shifts)

    with (record_dir / "zcorn_shifts.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("zcorn_index", "i", "j", "k", "corner", "shift_m"))
        writer.writerows((index, *corner_of(index), shifts[index]) for index in sorted(shifts))
    (record_dir / "changes.diff").write_bytes("".join(diff).encode(ENCODING))
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("build",))
    parser.parse_args(argv)

    deck = volve_data() / DECK_DIR
    record_dir = repo_root() / "agents" / "sim" / "out" / "volve_2016_flow"
    try:
        summary = build(deck, record_dir)
    except (ValueError, KeyError, OSError) as error:
        print(f"build failed: {error}", file=sys.stderr)
        return 1
    print(f"written to {deck}:")
    for name, count in summary.items():
        print(f"  {count:6d}  {name}")
    print(f"change record: {record_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
