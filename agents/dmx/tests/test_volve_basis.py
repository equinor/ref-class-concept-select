import numpy as np

from dmxkit import volve_basis as vb


def test_a_lognormal_through_two_percentiles_returns_them():
    d = vb.Lognormal(p90=3.4, p10=14.6)

    assert np.isclose(d.cdf(3.4), 0.10) and np.isclose(d.cdf(14.6), 0.90)
    assert np.isclose(d.median, np.sqrt(3.4 * 14.6))
    assert round(d.mean, 1) == 8.3  # the PDO's mean for the West


def test_lines_are_continued_with_the_end_slopes():
    xs, ys = (1.0, 2.0, 4.0), (10.0, 20.0, 30.0)

    assert vb.interpolate(1.5, xs, ys) == 15.0
    assert vb.interpolate(0.0, xs, ys) == 0.0  # slope 10 below the first point
    assert vb.interpolate(6.0, xs, ys) == 40.0  # slope 5 above the last


def test_the_relations_return_the_pdo_cases():
    p = vb.pdo()

    assert np.isclose(vb.reserves(p["closure"]["p90"]), p["reserves"]["p90"])
    assert np.isclose(vb.reserves(p["closure"]["p10"]), p["reserves"]["p10"])
    assert np.isclose(vb.value(p["reserves"]["mean"]), p["npv"]["expected_price"])
    assert np.isclose(vb.value(p["reserves"]["p90"]), p["npv"]["p90_profile"])
    assert p["two_wells"] == 70.0


def test_the_pdo_basis_reproduces_the_closure_of_table_3_4():
    stated = vb.bases()["PDO"]
    closure, published = vb.describe(stated["closure"]), vb.pdo()["closure"]

    for name in ("p90", "p50", "p10", "mean"):
        assert abs(closure[name] - published[name]) < 0.5, name


def test_calibration_changes_the_west_only_and_lowers_the_centre():
    both = vb.bases()

    assert np.array_equal(both["PDO"]["east"], both["Calibrated"]["east"])
    west = {name: vb.describe(basis["west"]) for name, basis in both.items()}
    assert west["Calibrated"]["p50"] < west["PDO"]["p50"]
    assert west["Calibrated"]["p90"] < west["PDO"]["p90"]


def test_the_base_model_treatment_keeps_the_shape_and_moves_the_mean():
    west = vb.calibrated_west(vb.BASE_MODEL)

    assert np.isclose(west.mean() / vb.draws()["west"].mean(), 4.6 / 8.3)


def test_west_decision_on_a_case_worked_by_hand():
    # East 20.9 in every draw; West 0 in half the draws and 5.8 in the other half.
    # Reserves follow the first PDO line: 9.0 at 20.9, 11.35 at 26.7.
    # Value follows 203 at 9.0 and 443 at 11.4, i.e. 100 per million Sm3: 203 and 438.
    basis = {"east": np.full(4, 20.9), "west": np.array([0.0, 0.0, 5.8, 5.8])}

    d = vb.west_decision(basis)

    assert np.isclose(d["commit"], (203 + 438) / 2)
    assert np.isclose(d["east_only"], 203 + 70)
    assert np.isclose(d["staged"], (273 + 438) / 2)  # skip the pair when the West is empty
    assert np.isclose(d["information"], 355.5 - 320.5)
    assert d["pair_does_not_pay"] == 0.5
    assert np.isclose(d["break_even_west"], 70 / (100 * 2.35 / 5.8))
