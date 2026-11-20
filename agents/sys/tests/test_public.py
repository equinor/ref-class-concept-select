from syskit import public


def test_series_with_years_down_the_first_column():
    rows = [["observation_date", "DCOILBRENTEU"], ["2005-01-01", "54.90"], ["2006-01-01", "65.25"]]

    assert public.parse_series(rows) == {2005: 54.90, 2006: 65.25}


def test_series_with_years_across_the_header():
    rows = [
        ["consumption group", "Consumer Price Index (2015=100) 2005", "Consumer Price Index 2006"],
        ["TOTAL All-item index", "82.3", "84.2"],
    ]

    assert public.parse_series(rows) == {2005: 82.3, 2006: 84.2}
