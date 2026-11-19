import pytest

from syskit import paths


def test_volve_data_follows_the_environment_variable(tmp_path, monkeypatch):
    monkeypatch.setenv("VOLVE_DATA", str(tmp_path))

    assert paths.volve_data() == tmp_path.resolve()


def test_missing_data_directory_is_an_error_naming_its_origin(tmp_path, monkeypatch):
    monkeypatch.setenv("VOLVE_DATA", str(tmp_path / "absent"))

    with pytest.raises(FileNotFoundError, match="from VOLVE_DATA"):
        paths.volve_data()


def test_repo_root_holds_the_agent_rules():
    assert (paths.repo_root() / "AGENTS.md").is_file()
