from dockit.figures import caption_numbers, cluster, with_labels
from dockit.pdf import Block


def test_caption_numbers_accepts_dot_and_hyphen():
    assert caption_numbers("Figur 4.2 - Volve oljerate", "Figur") == ["4.2"]
    assert caption_numbers("Figur 3-7 - Ulike faktorers bidrag", "Figur") == ["3.7"]


def test_one_caption_line_can_name_two_figures():
    text = "Figur 6.2 - Vanninjeksjonsbrønn       Figur 6.3 - Utsira vannproduksjonsbrønn"

    assert caption_numbers(text, "Figur") == ["6.2", "6.3"]


def test_a_reference_to_a_figure_inside_a_sentence_is_not_a_caption():
    assert caption_numbers("Oljerate er vist i Figur 4.2.", "Figur") == []
    assert caption_numbers("Tabell 4.5 - Resultat", "Figur") == []


def test_nearby_rectangles_merge_and_distant_ones_stay_apart():
    parts = [(0, 0, 10, 10), (12, 0, 30, 10), (28, 8, 40, 30), (200, 200, 220, 220)]

    assert sorted(cluster(parts, distance=5)) == [(0, 0, 40, 30), (200, 200, 220, 220)]


def test_labels_join_the_figure_but_headings_body_text_and_captions_do_not():
    box = (100, 100, 300, 250)
    caption = Block((100, 262, 300, 272), "Figur 4.2 - Volve oljerate")
    axis_label = Block((84, 150, 96, 200), "Sm3/d")
    inside = Block((120, 110, 280, 122), "Produksjons start 06.03.2007")
    heading = Block((100, 80, 300, 96), "7.4.2 Produksjonsplattformen")
    paragraph = Block((100, 252, 300, 260), "x" * 120)
    below = Block((100, 280, 300, 290), "år")

    result = with_labels(box, [caption, axis_label, inside, heading, paragraph, below], caption)

    assert result == (84, 100, 300, 250)


def test_journal_captions_end_the_number_with_a_full_stop():
    assert caption_numbers("Fig. 9. 90% confidence interval", "Fig.", "journal") == ["9"]
    assert caption_numbers("Fig. A.16. Example of forecasts", "Fig.", "journal") == ["A.16"]
    assert caption_numbers("Fig. 8 shows an example operator forecast", "Fig.", "journal") == []
    assert caption_numbers("end of body text\nFig. 1. General problem", "Fig.", "journal") == ["1"]
