from syskit import manifest


def _tree(root):
    (root / "reports").mkdir()
    (root / "reports" / "a.pdf").write_bytes(b"alpha")
    (root / "b.txt").write_bytes(b"beta")


def test_unchanged_tree_matches_its_manifest(tmp_path):
    _tree(tmp_path)
    recorded = manifest.scan(tmp_path)

    assert [e.path for e in recorded] == ["b.txt", "reports/a.pdf"]
    assert manifest.compare(recorded, tmp_path).clean


def test_manifest_survives_a_round_trip_through_the_file(tmp_path):
    _tree(tmp_path)
    recorded = manifest.scan(tmp_path)
    target = tmp_path.parent / "manifest.csv"

    manifest.write(recorded, target)

    assert manifest.read(target) == recorded


def test_missing_changed_and_extra_files_are_reported(tmp_path):
    _tree(tmp_path)
    recorded = manifest.scan(tmp_path)

    (tmp_path / "b.txt").unlink()
    (tmp_path / "reports" / "a.pdf").write_bytes(b"ALPHA")  # same size, different content
    (tmp_path / "new.xlsx").write_bytes(b"new")
    diff = manifest.compare(recorded, tmp_path)

    assert diff.missing == ["b.txt"]
    assert diff.changed == ["reports/a.pdf"]
    assert diff.extra == ["new.xlsx"]


def test_quick_comparison_misses_same_size_changes_but_catches_size_changes(tmp_path):
    _tree(tmp_path)
    recorded = manifest.scan(tmp_path)

    (tmp_path / "reports" / "a.pdf").write_bytes(b"ALPHA")
    assert manifest.compare(recorded, tmp_path, hashes=False).clean

    (tmp_path / "reports" / "a.pdf").write_bytes(b"longer content")
    assert manifest.compare(recorded, tmp_path, hashes=False).changed == ["reports/a.pdf"]
