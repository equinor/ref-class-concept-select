from xml.etree import ElementTree as ET

import pytest

from syskit import pptx, rcf_volve_deck
from syskit.paths import repo_root

SOURCE = repo_root() / rcf_volve_deck.SOURCE
pytestmark = pytest.mark.skipif(not SOURCE.exists(), reason="presentation not present")
A = "http://schemas.openxmlformats.org/drawingml/2006/main"


def test_every_slide_is_read_and_nothing_is_left_out():
    slides = pptx.read(SOURCE)

    assert [s.number for s in slides] == [1, 2, 3, 4, 5, 6, 7]
    assert [s.skipped for s in slides] == [[]] * 7
    assert [len(s.pictures) for s in slides] == [2, 0, 3, 0, 1, 1, 1]


def test_text_keeps_its_wording_colour_and_weight():
    slide = pptx.read(SOURCE)[1].html({})

    assert "Our understanding of in-place and recoverable volumes should improve over time" in slide
    assert 'font-weight:700;color:#c00000">But is this really the case?' in slide
    for label in ("Volumes", "Time/Information", "Pre-drill", "Post-drill", "Concept select"):
        assert f">{label}</span>" in slide


def test_a_title_that_the_file_shrinks_to_fit_is_marked_for_fitting():
    slides = pptx.read(SOURCE)

    assert 'class="abs tx fit"' in slides[2].html(
        {"image3.png": "", "image4.png": "", "image5.png": ""}
    )
    assert 'class="abs tx fit"' not in slides[0].html({"image1.jpeg": "", "image2.png": ""})


def test_theme_colours_are_lightened_as_the_file_says():
    deck = pptx.Deck(SOURCE)
    fill = ET.fromstring(
        f'<a:solidFill xmlns:a="{A}"><a:schemeClr val="accent4"><a:lumMod val="20000"/>'
        '<a:lumOff val="80000"/></a:schemeClr></a:solidFill>'
    )
    plain = ET.fromstring(f'<a:solidFill xmlns:a="{A}"><a:srgbClr val="C00000"/></a:solidFill>')

    assert deck.colors["accent4"] == "0F9ED5"
    assert deck.color(fill) == "#caeefb"  # the light blue band of slide 2
    assert deck.color(plain) == "#c00000"
    assert deck.color(None) is None


def test_arrows_point_the_way_they_do_in_the_file():
    shapes = [part[1] for part in pptx.read(SOURCE)[1].parts if part[0] == "shape"]

    time_axis, volume_axis = shapes[0], shapes[1]
    assert 'x1="342.8" y1="786.3" x2="1329.9" y2="786.3"' in time_axis  # left to right
    assert 'points="1329.9,786.3' in time_axis  # head at the right end
    assert 'y1="833.3"' in volume_axis and 'y2="369.5"' in volume_axis  # flipped: bottom to top


def test_pictures_are_matched_with_the_original_figure_files(tmp_path):
    addresses, rows = rcf_volve_deck.place_pictures(SOURCE, tmp_path, repo_root())
    origin = {row["in_presentation"]: row["original"] for row in rows}

    assert origin["image4.png"] == "agents/rcf/study/figures/calibration_plot.png"
    assert origin["image3.png"].endswith("inplace_result_vs_prognosis_loglog.png")
    assert origin["image8.png"] == "agents/rcf/out/figs/expert-study-review_slide6.png"
    assert origin["image1.jpeg"] == ""  # only in the presentation
    assert addresses["image4.png"] == "figs/calibration_plot.png"
    assert (tmp_path / "calibration_plot.png").read_bytes() == (
        repo_root() / origin["image4.png"]
    ).read_bytes()
