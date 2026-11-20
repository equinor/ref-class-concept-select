import hashlib

import pytest
from pptx import Presentation

from syskit import rcf_volve_deck, rcf_volve_pptx, workflow_deck
from syskit.paths import repo_root

SOURCE = repo_root() / rcf_volve_deck.SOURCE
pytestmark = pytest.mark.skipif(not SOURCE.exists(), reason="presentation not present")


def texts(slide) -> list[str]:
    return [shape.text_frame.text for shape in slide.shapes if shape.has_text_frame]


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    try:
        import cairosvg  # noqa: F401
    except OSError:
        pytest.skip("the cairo library is not installed")
    before = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    target = rcf_volve_pptx.build(tmp_path_factory.mktemp("deck") / "deck.pptx")
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == before
    return target


def test_the_slides_of_the_source_are_kept_and_three_follow(built):
    source, result = Presentation(str(SOURCE)).slides, Presentation(str(built)).slides

    assert len(result) == len(source) + 3
    for number, (old, new) in enumerate(zip(source, result, strict=False), start=1):
        assert texts(new) == texts(old)
        added = 1 if number == rcf_volve_deck.WORKFLOW_SLIDE else 0
        assert len(new.shapes) == len(old.shapes) + added
    assert [s.shapes.title.text for s in list(result)[-3:]] == [
        "First use",
        "The 2005 plan and the modified plan",
        "What changes",
    ]


def test_the_last_slide_is_a_table_with_the_rows_of_the_web_version(built):
    slide = list(Presentation(str(built)).slides)[-1]
    table = next(shape for shape in slide.shapes if shape.has_table).table

    rows = [tuple(cell.text for cell in row.cells) for row in table.rows]
    assert rows[0] == ("", "2005 plan", "Modified plan")
    assert rows[1:] == workflow_deck.changes_rows(workflow_deck.numbers())


def test_a_rebuild_gives_the_same_file(built, tmp_path):
    again = rcf_volve_pptx.build(tmp_path / "again.pptx")

    assert again.read_bytes() == built.read_bytes()
