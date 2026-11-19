import datetime as dt

import pytest

from syskit import facts, sodir
from syskit.paths import data_dir

STAMP = dt.datetime(2026, 11, 19, 12, 0, tzinfo=dt.UTC)


def _fake_fetch(table):
    return f"\ufeffname,value\r\n{table},1\r\n".encode()


def test_snapshot_writes_every_table_and_an_index(tmp_path, monkeypatch):
    monkeypatch.setattr(sodir, "fetch", _fake_fetch)

    target = sodir.snapshot(tmp_path, STAMP)

    assert target.name == "20261119"
    assert sorted(p.stem for p in target.glob("*.csv")) == sorted([*sodir.TABLES, "index"])
    index = sodir.read_table("index", target)
    assert [row["table"] for row in index] == list(sodir.TABLES)
    assert {row["rows"] for row in index} == {"1"}
    assert sodir.read_table("field_reserves", target) == [{"name": "field_reserves", "value": "1"}]


def test_failed_download_leaves_no_snapshot_behind(tmp_path, monkeypatch):
    def fetch(table):
        if table == sodir.TABLES[3]:
            raise ValueError("not a CSV table")
        return _fake_fetch(table)

    monkeypatch.setattr(sodir, "fetch", fetch)

    with pytest.raises(ValueError):
        sodir.snapshot(tmp_path, STAMP)

    assert list(tmp_path.iterdir()) == []


def test_existing_snapshot_is_kept_unless_forced(tmp_path, monkeypatch):
    monkeypatch.setattr(sodir, "fetch", _fake_fetch)
    target = sodir.snapshot(tmp_path, STAMP)
    (target / "marker").write_text("original")

    with pytest.raises(FileExistsError):
        sodir.snapshot(tmp_path, STAMP)
    assert (target / "marker").exists()

    sodir.snapshot(tmp_path, STAMP, force=True)
    assert not (target / "marker").exists()


def test_latest_picks_the_newest_snapshot(tmp_path):
    for name in ("20261119", "20270105", ".20270301.partial", "notes"):
        (tmp_path / name).mkdir()

    assert sodir.latest(tmp_path).name == "20270105"


def test_volve_facts_from_the_committed_snapshot():
    """The values quoted in docs/data-sources.md come out of the 2026-11-19 snapshot."""
    rows = sodir.field_facts("VOLVE", data_dir() / "sodir" / "20261119")
    by_id = {row["fact_id"]: row for row in rows}

    def fact(name):
        row = by_id[f"sodir.{name}"]
        return float(row["value"]), row["unit"], row["as_of"]

    assert fact("oil_production.total") == (10.172, "MSm3", "2016")
    assert fact("investment.total") == (4689.0, "MNOK nominal", "2021")
    assert fact("in_place_oil") == (18.70, "MSm3", "2025-12-31")
    assert fact("recoverable_oil.2005") == (11.90, "MSm3", "2005-12-31")
    assert fact("recoverable_oil.2010") == (8.15, "MSm3", "2010-12-31")
    assert fact("recoverable_ngl.2025") == (0.16, "Mt", "2025-12-31")
    assert len(by_id) == len(rows)
    for row in rows:
        assert facts.check_row(row, file_source="sodir", sources={"sodir"}) == []
