import numpy as np

from rcfkit import stats


def test_wilson_interval_matches_a_worked_case():
    low, high = stats.wilson(5, 20, z=1.96)

    assert round(low, 3) == 0.112
    assert round(high, 3) == 0.469
    assert stats.wilson(0, 0) == (0.0, 1.0)


def test_a_probability_on_a_class_boundary_belongs_to_the_class_above():
    p = np.array([0.05, 0.1, 0.3, 0.3, 0.7, 1.0])
    y = np.array([0.0, 1.0, 0.0, 1.0, 1.0, 1.0])

    rows = stats.reliability(p, y, np.linspace(0, 1, 11))

    assert [(round(r["from"], 1), r["n"]) for r in rows] == [
        (0.0, 1),
        (0.1, 1),
        (0.3, 2),
        (0.7, 1),
        (0.9, 1),
    ]
    assert rows[2]["observed"] == 0.5


def test_brier_decomposition_adds_up_when_forecasts_within_a_class_are_equal():
    p = np.array([0.2] * 5 + [0.8] * 5)
    y = np.array([0, 0, 0, 1, 1, 1, 1, 1, 1, 0], dtype=float)

    d = stats.brier_decomposition(p, y, np.linspace(0, 1, 11))

    assert np.isclose(d["brier"], d["reliability"] - d["resolution"] + d["uncertainty"])
    assert np.isclose(d["reliability"], 0.02)  # half the cases miss by 0.2: 0.5 * 0.2**2
    assert np.isclose(d["resolution"], 0.04)  # observed 0.4 and 0.8 around a base rate of 0.6


def test_recalibration_recovers_a_known_distortion():
    rng = np.random.default_rng(1)
    truth = rng.uniform(0.05, 0.95, 20000)
    y = (rng.uniform(size=truth.size) < truth).astype(float)
    stated = stats.expit(2.0 * stats.logit(truth))  # twice as extreme as the truth

    a, b = stats.fit_recalibration(stated, y)

    assert abs(a) < 0.05
    assert abs(b - 0.5) < 0.03
    assert np.allclose(stats.recalibrate(stated, 0.0, 0.5), truth)


def test_folds_cover_every_case_once():
    parts = stats.folds(23, 5)

    assert sorted(np.concatenate(parts).tolist()) == list(range(23))
    assert {len(p) for p in parts} == {4, 5}


def test_ratio_summary():
    forecast = np.array([10.0, 10.0, 10.0, 10.0])
    outcome = np.array([1.0, 5.0, 10.0, 40.0])

    s = stats.ratio_summary(forecast, outcome)

    assert s["median"] == 0.75
    assert s["of_totals"] == 1.4
    assert np.isclose(s["geometric_mean"], (0.1 * 0.5 * 1 * 4) ** 0.25)
    assert s["share_below_forecast"] == 0.5
    assert s["share_within_factor_2"] == 0.5
    assert s["share_below_tenth"] == 0.0


def test_coverage_counts_outcomes_on_the_limits_as_inside():
    low, high = np.array([1.0, 1, 1, 1, 1]), np.array([2.0, 2, 2, 2, 2])

    c = stats.coverage(low, high, np.array([0.5, 1.0, 1.5, 2.0, 3.0]))

    assert (c["below"], c["above"]) == (0.2, 0.2)
    assert np.isclose(c["inside"], 0.6)


def test_percentile_of_uses_mid_rank_for_ties():
    sample = np.array([1.0, 2.0, 2.0, 3.0])

    assert stats.percentile_of(0.5, sample) == 0.0
    assert stats.percentile_of(2.0, sample) == 0.5
    assert stats.percentile_of(9.0, sample) == 1.0


def test_pinball_penalises_a_miss_above_the_high_value_more_than_one_inside():
    forecast = {0.1: 8.0, 0.5: 10.0, 0.9: 12.0}

    assert np.isclose(stats.pinball(forecast, 10.0), (0.1 * 2 + 0 + 0.1 * 2) / 3)
    assert np.isclose(stats.pinball(forecast, 20.0), (0.1 * 12 + 0.5 * 10 + 0.9 * 8) / 3)
    assert stats.pinball(forecast, 20.0) > stats.pinball(forecast, 11.0)


def test_bootstrap_interval_brackets_the_mean_of_a_known_sample():
    values = np.arange(100.0)

    low, high = stats.bootstrap(np.mean, values, n=500)

    assert low < 49.5 < high
    assert high - low < 12
