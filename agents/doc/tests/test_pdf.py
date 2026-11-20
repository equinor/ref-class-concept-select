from dockit.pdf import Block, Word, mark_runs, overlap_fraction, reading_order


def _word(text: str, highlighted: bool = False) -> Word:
    return Word((0, 0, 1, 1), text, 0, 0, highlighted)


def test_overlap_is_the_share_of_the_inner_rectangle_inside_the_outer():
    assert overlap_fraction((0, 0, 10, 10), (5, 0, 20, 10)) == 0.5
    assert overlap_fraction((0, 0, 10, 10), (0, 0, 10, 10)) == 1.0
    assert overlap_fraction((0, 0, 10, 10), (10, 0, 20, 10)) == 0.0


def test_each_run_of_highlighted_words_is_wrapped_once():
    words = [_word("tre"), _word("produsenter", True), _word("høyt", True), _word("på"),
             _word("flankene.", True)]  # fmt: skip

    assert mark_runs(words) == "tre **produsenter høyt** på **flankene.**"


def test_text_without_highlights_is_left_alone():
    assert mark_runs([_word("Volve"), _word("feltet")]) == "Volve feltet"


def test_left_column_is_read_before_right_within_bands_split_by_full_width_blocks():
    width = 600
    blocks = [
        Block((320, 100, 560, 200), "right 1"),
        Block((70, 100, 290, 300), "left 1"),
        Block((70, 320, 560, 340), "full-width caption"),
        Block((320, 360, 560, 400), "right 2"),
        Block((70, 380, 290, 420), "left 2"),
        Block((70, 40, 560, 60), "title"),
    ]

    order = [block.text for block in reading_order(blocks, width)]

    assert order == ["title", "left 1", "right 1", "full-width caption", "left 2", "right 2"]
