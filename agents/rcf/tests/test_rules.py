import datetime as dt

import numpy as np
import pandas as pd

from rcfkit import data, fields, volve


def test_alternative_cases_add_up_to_the_chance_of_discovery():
    assert np.isclose(data.discovery_probability(np.array([0.18, 0.09])), 0.27)


def test_cases_with_the_same_probability_describe_one_chance():
    assert data.discovery_probability(np.array([0.28, 0.28])) == 0.28


def test_a_sum_above_one_falls_back_on_the_largest_case():
    assert data.discovery_probability(np.array([0.52, 0.45, 0.35])) == 0.52


def test_missing_probabilities_are_ignored():
    assert data.discovery_probability(np.array([np.nan, 0.38])) == 0.38
    assert np.isnan(data.discovery_probability(np.array([np.nan])))


def test_case_volumes_are_weighted_by_case_probability():
    volumes, weights = pd.Series([10.0, 40.0]), pd.Series([0.3, 0.1])

    assert np.isclose(data._weighted(volumes, weights), 17.5)
    assert data._weighted(volumes, pd.Series([np.nan, np.nan])) == 25.0
    assert data._weighted(pd.Series([np.nan, 40.0]), weights) == 40.0


def _profiles() -> pd.DataFrame:
    month = pd.Period
    return pd.DataFrame(
        {
            "field": ["A", "B", "C", "VOLVE"],
            "approval_month": [
                month("1995-01"),
                month("2001-06"),
                month("2006-01"),
                month("2005-04"),
            ],
            "start": [month("1997-01"), month("2003-07"), month("2008-01"), month("2008-02")],
            "oil_share": [0.9, 0.2, 0.8, 0.9],
            "fid_oe": [10.0, 100.0, 300.0, 13.0],
            **{years: [0.1 * years] * 4 for years in fields.HORIZONS},
        }
    )


def test_a_class_as_known_at_a_date_holds_only_what_had_happened_by_then():
    known = fields.select(_profiles(), known_by=pd.Period("2005-01"))

    assert list(known["field"]) == ["A", "B"]  # C and Volve were approved later
    a, b = known.iloc[0], known.iloc[1]
    assert a[8] == 0.8 and np.isnan(a[9])  # A completed its eighth year in December 2004
    assert b[1] == 0.1 and np.isnan(b[2])  # B had completed one year by then


def test_class_rules_combine():
    table = _profiles()

    assert list(fields.select(table, oil_only=True, exclude="VOLVE")["field"]) == ["A", "C"]
    assert list(fields.select(table, size_near=13.0)["field"]) == ["A", "VOLVE"]


def test_calendar_year_volumes_are_recounted_from_the_start_date():
    # 1.2 in the last 0.6 of the first year, then 2.0 a year: a rate of 2.0 a year throughout.
    start = dt.date(2007, 1, 1) + dt.timedelta(days=round(0.4 * 365.25))
    cumulative = volve.cumulative_since_start({2007: 1.2, 2008: 2.0, 2009: 2.0}, start)

    assert np.isclose(cumulative[1], 2.0, atol=0.01)
    assert np.isclose(cumulative[2], 4.0, atol=0.01)
    assert np.isclose(cumulative[3], 5.2)  # nothing after the last year given
    assert cumulative[9] == cumulative[3]
