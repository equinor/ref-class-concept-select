import numpy as np
import pytest

from simkit import flow_deck
from simkit.flow_deck import Edit

DECK = [
    "RUNSPEC\n",
    "EQLOPTS\n",
    "'THPRES' 'QUIESC' /\n",
    "ROCK\n",
    " 329 2.0E-5 /\n",
    " 329 2.0E-5 / #13\n",
    "END\n",
]


def test_replaced_line_is_kept_as_a_comment_above_its_replacement():
    edit = Edit(3, 3, "'QUIESC'", "QUIESC is not implemented.", (" 'THPRES' /",))

    result = flow_deck.apply_edits(DECK, (edit,))

    assert result[2:5] == [
        "-- FLOW: QUIESC is not implemented.\n",
        "--FLOW 'THPRES' 'QUIESC' /\n",
        " 'THPRES' /\n",
    ]
    assert result[:2] == DECK[:2] and result[5:] == DECK[3:]


def test_edits_are_located_by_original_line_numbers_whatever_their_order():
    first = Edit(3, 3, "'QUIESC'", "one", (" 'THPRES' /",))
    second = Edit(6, 6, "#13", "two")

    result = flow_deck.apply_edits(DECK, (first, second))

    assert result == flow_deck.apply_edits(DECK, (second, first))
    assert result[-3:] == ["-- FLOW: two\n", "--FLOW  329 2.0E-5 / #13\n", "END\n"]


def test_range_of_lines_is_disabled_with_one_reason():
    result = flow_deck.apply_edits(DECK, (Edit(4, 6, "ROCK", "no rock"),))

    assert result[3:] == [
        "-- FLOW: no rock\n",
        "--FLOW ROCK\n",
        "--FLOW  329 2.0E-5 /\n",
        "--FLOW  329 2.0E-5 / #13\n",
        "END\n",
    ]


def test_edit_is_refused_when_the_original_is_not_what_was_expected():
    with pytest.raises(ValueError, match="line 3: expected 'MOBILE'"):
        flow_deck.apply_edits(DECK, (Edit(3, 3, "MOBILE", "x"),))
    with pytest.raises(ValueError, match="line 40"):
        flow_deck.apply_edits(DECK, (Edit(40, 40, "ROCK", "x"),))


def test_windows_line_endings_are_preserved():
    lines = ["DATES\r\n", " 'P-F-14' 'OPEN' /\r\n", "/\r\n"]

    result = flow_deck.apply_edits(lines, (Edit(2, 2, "P-F-14", "orphan record"),))

    assert result == [
        "DATES\r\n",
        "-- FLOW: orphan record\r\n",
        "--FLOW  'P-F-14' 'OPEN' /\r\n",
        "/\r\n",
    ]


def test_flow_name_puts_the_suffix_before_the_extension():
    assert flow_deck.flow_name("VOLVE_2016.DATA") == "VOLVE_2016_FLOW.DATA"
    assert flow_deck.flow_name("a.b.E100") == "a.b_FLOW.E100"


GRID = [
    "COORD\n",
    " 0 0 0 0 0 9 /\n",
    "\n",
    "ZCORN\n",
    "   2863.352    2857.268    2848.985 \n",
    "\n",
    "   2836.623    2830.100 \n",
    "  /\n",
    "ACTNUM\n",
    " 1 1 /\n",
]


def test_zcorn_is_read_across_blank_lines_up_to_the_slash():
    values, starts, first_line = flow_deck.read_zcorn(GRID)

    assert values.tolist() == [2863.352, 2857.268, 2848.985, 2836.623, 2830.1]
    assert (starts.tolist(), first_line) == ([0, 3, 3, 5], 4)


def test_shifted_values_keep_their_place_and_other_lines_are_untouched():
    result = flow_deck.shift_zcorn(GRID, {2: 10.0, 3: -20.0})

    assert result[4] == "   2863.352    2857.268    2858.985 \n"
    assert result[6] == "   2816.623    2830.100 \n"
    assert [n for n, (a, b) in enumerate(zip(GRID, result, strict=True)) if a != b] == [4, 6]


def test_shifts_are_whole_centimetres_and_single_precision_noise_is_ignored():
    original = np.array([2863.352, 2857.268, 2848.985, 2836.623])
    final = np.array([2863.3521, 2867.26795, 2848.985, 2816.6231])  # as read from float32

    shifts, irregular = flow_deck.corner_shifts(original, final)

    assert (shifts, irregular) == ({1: 10.0, 3: -20.0}, [])


def test_differences_that_are_not_clean_shifts_are_reported_not_applied():
    original = np.array([3131.608, 3131.608])
    final = np.array([12551.7341, 3131.608])

    shifts, irregular = flow_deck.corner_shifts(original, final)

    assert (shifts, irregular) == ({}, [0])


def test_zcorn_index_and_corner_of_are_inverse():
    for i, j, k, corner in [(0, 0, 0, 0), (57, 42, 0, 3), (107, 99, 62, 7), (64, 51, 30, 5)]:
        index = flow_deck.zcorn_index(i, j, k, corner)
        ci, cj, ck, label = flow_deck.corner_of(index)
        expected = (
            f"{'bottom' if corner & 4 else 'top'} "
            f"x{'+' if corner & 1 else '-'} y{'+' if corner & 2 else '-'}"
        )
        assert (ci, cj, ck, label) == (i + 1, j + 1, k + 1, expected)
    assert flow_deck.zcorn_index(107, 99, 62, 7) == 8 * 108 * 100 * 63 - 1
