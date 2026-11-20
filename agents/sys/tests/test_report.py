from syskit.charts import Chart, Series
from syskit.report import Report, inline_html, number, percent, signed, slug


def _chart() -> Chart:
    return Chart(
        "demo",
        "Demo",
        "x",
        "y",
        [
            Series("band", [1, 2, 3], low=[0, 1, 2], high=[2, 3, 4], name="range"),
            Series("line", [1, 2, 3], [1, 2, 3], name="middle"),
            Series("errorbar", [1, 2, 3], [1, 2, 3], low=[0.5, 1.5, 2.5], high=[1.5, 2.5, 3.5]),
            Series("markers", [1, 2], [3, 1], labels=["a", "b"]),
        ],
    )


def test_numbers_are_formatted_for_reading():
    assert number(14399.7) == "14 400"
    assert signed(-0.4, 2) == "−0.40"
    assert percent(0.305) == "30 %" or percent(0.305) == "31 %"
    assert percent(0.281, 1) == "28.1 %"
    assert slug("What holds — and what not") == "what-holds-and-what-not"


def test_inline_markup_is_converted_and_other_text_escaped():
    text = inline_html("Use `a<b` in *this* [file](x/y.md), not 2 * 3 * 4 <i>")

    assert text == (
        'Use <code>a&lt;b</code> in <em>this</em> <a href="x/y.md">file</a>, '
        "not 2 * 3 * 4 &lt;i&gt;"
    )


def test_a_report_is_written_as_markdown_and_as_a_web_page(tmp_path):
    report = Report("Title", "Summary with `code`.", generator="make demo")
    report.section("First part", "First")
    report.text(
        "A   paragraph\n   over two lines. See [the data](data/x.csv) and [a site](https://e.org)."
    )
    report.bullets(["one", "two"], numbered=True)
    report.table(["Name", "Value"], [["a", 1.5], ["b|c", "2"]], caption="Numbers")
    report.chart(_chart(), "What it shows.")
    report.note("Mind this.")

    markdown = report.write_markdown(tmp_path / "demo.md").read_text()
    page = report.write_html(
        tmp_path / "demo" / "index.html", plotly="../lib/p.js", link_prefix="../"
    ).read_text()

    assert "## First part" in markdown
    assert "A paragraph over two lines. See [the data](data/x.csv)" in markdown
    # The page lies one folder down: its relative links are adjusted, others are not.
    assert '<a href="../data/x.csv">the data</a>' in page
    assert '<a href="https://e.org">a site</a>' in page
    assert "1. one\n2. two" in markdown
    assert "| a | 1.50 |" in markdown and "| b\\|c | 2 |" in markdown
    assert "![Demo](figs/demo_demo.png)" in markdown
    assert (tmp_path / "figs" / "demo_demo.png").stat().st_size > 5000
    assert "> Mind this." in markdown

    assert '<section id="first">' in page and '<a href="#first">First</a>' in page
    assert 'id="chart-demo"' in page
    assert '<script src="../lib/p.js"></script>' in page
    assert (tmp_path / "lib" / "p.js").exists()  # the chart library travels with the page
    assert '<td class="r">1.50</td>' in page
