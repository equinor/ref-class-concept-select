from collections import Counter

from dockit import assemble


def test_number_formatting_does_not_change_the_digits_compared():
    norwegian = "9.000 Sm3/d, 19,9 mill. Sm3, 92 500 USD, 200832 tonn"
    english = "9 000 Sm3/d, 19.9 million Sm3, 92 500 USD, 200 832 tonnes"

    assert assemble.digit_runs(norwegian) == assemble.digit_runs(english)
    assert assemble.digit_runs("19,9") == Counter(["19", "9"])


def test_a_changed_digit_is_noticed():
    assert assemble.digit_runs("11,40") != assemble.digit_runs("11.46")


def test_page_form_is_checked(tmp_path):
    good = "<!-- page 3 -->\n<!-- type: text -->\n\nText."

    assert assemble.check_page(3, good, tmp_path) == []
    assert assemble.check_page(4, good, tmp_path) == ["first line is not the page marker"]
    wrong_type = good.replace("text -->", "prose -->")
    assert assemble.check_page(3, wrong_type, tmp_path) == ["second line is not a valid page type"]


def test_missing_figure_file_is_reported(tmp_path):
    (tmp_path / "figs").mkdir()
    (tmp_path / "md").mkdir()
    (tmp_path / "figs" / "a.png").write_bytes(b"x")
    page = (
        "<!-- page 1 -->\n<!-- type: mixed -->\n![Figure 1](../figs/a.png)\n![F 2](../figs/b.png)"
    )

    assert assemble.check_page(1, page, tmp_path / "md") == ["image not found: ../figs/b.png"]


def test_digits_missing_from_a_page_are_listed():
    source = "Reserver 11,40 mill Sm3 i 2012"
    page = "<!-- page 9 -->\nReserves 11.4 million Sm3 in 2012"

    problems = assemble.check_against_text(page, source, Counter())

    assert problems == ["digits in the source but not in the page: 40"]


def test_page_number_and_image_names_do_not_count_as_content():
    source = "Side 25\nFigur 4.5 - Profiler"
    page = "<!-- page 25 -->\n![Figure 4.5 – Profiles](../figs/doc_p025_fig4-5.png)"

    assert assemble.check_against_text(page, source, Counter(["25"])) == []


def test_highlight_without_bold_and_bold_without_highlight_are_both_reported():
    assert assemble.check_against_text("plain", "**uthevet tekst**", Counter()) == [
        "highlighted characters in source 13, bold in page 0"
    ]
    assert assemble.check_against_text("**bold text**", "vanlig", Counter()) == [
        "highlighted characters in source 0, bold in page 9"
    ]
    assert assemble.check_against_text("**highlighted text**", "**uthevet tekst**", Counter()) == []
