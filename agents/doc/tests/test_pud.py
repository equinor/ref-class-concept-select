import datetime as dt

import numpy as np

from dockit import pud_data, pud_facts, pud_report


def test_decimal_year_and_months_between():
    assert pud_data.decimal_year(dt.date(2008, 1, 1)) == 2008.0
    assert pud_data.decimal_year(dt.date(2008, 7, 2)) == 2008.5  # leap year: day 183 of 366
    assert round(pud_data.months_between(dt.date(2007, 3, 6), dt.date(2008, 3, 6)), 1) == 12.0


def test_plan_volume_integrates_the_rate_from_planned_first_oil():
    years = np.array([2007.0, 2012.0])
    rate = np.array([1000.0, 1000.0])  # Sm3 per day, constant

    volume = pud_data.plan_volume(years, rate, 12)

    assert round(volume, 4) == round(1000 * 365.25 / 1e6, 4)


def test_integrate_year_counts_only_the_part_of_the_year_with_data():
    years = np.array([2007.5, 2009.0])
    rate = np.array([200.0, 200.0])

    assert round(pud_report.integrate_year(years, rate, 2007) / 365.25, 0) == 100  # half a year
    assert round(pud_report.integrate_year(years, rate, 2008) / 365.25, 0) == 200
    assert pud_report.integrate_year(years, rate, 2010) == 0.0


def test_cumulative_follows_the_years_in_order():
    assert pud_report.cumulative({2009: 2.0, 2007: 1.0, 2008: 3.0}) == {
        2007: 1.0,
        2008: 4.0,
        2009: 6.0,
    }


def test_numbers_use_a_space_for_thousands_and_a_true_minus_sign():
    assert pud_report.number(4689) == "4 689"
    assert pud_report.signed(-10.8, 1) == "−10.8"
    assert pud_report.signed(44) == "+44"


def test_text_columns_are_left_aligned_and_numbers_right_aligned():
    html = pud_report.table(["Kind", "Planned", "Wellbores"], [["Oil", "3", "F-12"]], left=(0, 2))

    assert '<td class="l">Oil</td><td class="r">3</td><td class="l">F-12</td>' in html


def test_plan_tables_are_internally_consistent():
    """The PDO's own totals are reproduced by the values registered from it.

    Table 4.5 is the exception: its yearly values are rounded and sum to
    0.01 to 0.04 less than the totals it states.
    """
    for case, per_year in pud_facts.OIL_PER_YEAR.items():
        assert abs(sum(per_year.values()) - pud_facts.RESERVES[case]) <= 0.045, case
    parts = [v for k, v in pud_facts.INVESTMENTS_2005.items() if k != "total"]
    assert sum(parts) == pud_facts.INVESTMENTS_2005["total"]
    for name, (per_year, total) in pud_facts.COSTS_NOMINAL.items():
        assert sum(v for v in per_year if v) == total, name
    assert sum(pud_facts.CONTACTS.values()) == 100
