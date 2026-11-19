import csv

import pytest

from syskit import facts

SOURCES = {"pud2005", "sodir"}
GOOD = {
    "fact_id": "pud2005.reserves.mean",
    "quantity": "recoverable_oil",
    "value": "11.40",
    "unit": "MSm3",
    "basis": "mean",
    "as_of": "2005-02",
    "subject": "Volve",
    "source": "pud2005",
    "locator": "p25 table 4.5",
    "method": "read",
    "confidence": "high",
    "note": "",
}


def _problems(**changes):
    return facts.check_row(GOOD | changes, file_source="pud2005", sources=SOURCES)


def test_complete_row_is_accepted():
    assert _problems() == []


@pytest.mark.parametrize("column", ["source", "unit", "locator", "as_of", "method"])
def test_row_without_a_required_field_is_rejected(column):
    assert _problems(**{column: " "}) == [f"'{column}' is empty"]


def test_note_is_optional():
    assert _problems(note="") == []


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({"source": "unknown"}, "unknown source"),
        ({"source": "sodir"}, "does not belong in pud2005.csv"),
        ({"fact_id": "sodir.reserves.mean"}, "must look like 'pud2005.<name>'"),
        ({"fact_id": "pud2005"}, "must look like 'pud2005.<name>'"),
        ({"method": "guessed"}, "method 'guessed'"),
        ({"confidence": "certain"}, "confidence 'certain'"),
        ({"as_of": "Feb 2005"}, "as_of 'Feb 2005'"),
        ({"as_of": "2005-2"}, "as_of '2005-2'"),
        ({"value": "11,40"}, "is not a number"),
    ],
)
def test_invalid_values_are_rejected(changes, expected):
    assert any(expected in problem for problem in _problems(**changes))


def test_text_facts_are_allowed_with_the_text_unit():
    assert _problems(value="Leased jack-up with storage vessel", unit="text") == []


def _write(path, rows, header=facts.COLUMNS):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows([row[name] for name in facts.COLUMNS] for row in rows)


def _register(tmp_path, files):
    (tmp_path / "sources.csv").write_text("id,description\npud2005,x\nsodir,y\n")
    directory = tmp_path / "facts"
    directory.mkdir()
    for name, rows in files.items():
        _write(directory / name, rows)
    return facts.validate_register(directory, tmp_path / "sources.csv")


def test_register_counts_facts_across_files(tmp_path):
    sodir_row = GOOD | {"fact_id": "sodir.oil.2008", "source": "sodir"}

    count, problems = _register(tmp_path, {"pud2005.csv": [GOOD], "sodir.csv": [sodir_row]})

    assert (count, problems) == (2, [])


def test_duplicate_fact_id_is_reported_with_both_locations(tmp_path):
    _, problems = _register(tmp_path, {"pud2005.csv": [GOOD, GOOD]})

    assert problems == [
        "pud2005.csv:3: fact_id 'pud2005.reserves.mean' already used at pud2005.csv:2"
    ]


def test_wrong_header_is_reported(tmp_path):
    (tmp_path / "sources.csv").write_text("id\npud2005\n")
    directory = tmp_path / "facts"
    directory.mkdir()
    _write(directory / "pud2005.csv", [], header=facts.COLUMNS[:-1])

    _, problems = facts.validate_register(directory, tmp_path / "sources.csv")

    assert len(problems) == 1 and "header must be exactly" in problems[0]
