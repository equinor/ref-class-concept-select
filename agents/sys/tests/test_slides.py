from syskit.slides import Deck
from syskit.svg import BLUE, Svg, tint


def test_tint_mixes_a_colour_into_white():
    assert tint("#000000", 0.0) == "#ffffff"
    assert tint("#000000", 1.0) == "#000000"
    assert tint("#1d4ed8", 0.5) == "#8ea6ec"


def test_a_drawing_escapes_text_and_defines_each_arrow_head_once():
    drawing = Svg(400, 200)
    drawing.box(10, 10, 200, 80, "Facts & <rules>", ["one per row"], color=BLUE)
    drawing.arrow(210, 50, 300, 50, color=BLUE)
    drawing.arrow(210, 90, 300, 90, color=BLUE)

    text = drawing.render()

    assert text.startswith('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200"')
    assert "Facts &amp; &lt;rules&gt;" in text
    assert text.count("<marker ") == 1
    assert text.count('marker-end="url(#arrow-1d4ed8)"') == 2


def test_a_deck_holds_its_slides_in_order_and_can_be_stepped_through(tmp_path):
    deck = Deck("Demo")
    deck.title_slide("Demo", "What it is", "2026")
    deck.figure_slide("A picture", "figs/a.svg", note="Seen from <above>")
    deck.pair_slide("Two", [("figs/b.svg", "<b>1</b> → 2"), ("figs/c.svg", "three")])

    page = deck.write(tmp_path / "deck" / "index.html").read_text()

    assert page.count('<section class="slide') == 3
    assert page.index("What it is") < page.index("A picture") < page.index("figs/b.svg")
    assert '<img src="figs/a.svg" alt="">' in page
    assert "Seen from &lt;above&gt;" in page
    assert "<b>1</b> → 2" in page  # captions of a pair are HTML
    assert "ArrowRight" in page and "location.hash" in page
