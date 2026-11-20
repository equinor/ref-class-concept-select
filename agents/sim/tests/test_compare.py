import numpy as np

from simkit import compare


def test_arrays_within_tolerance_count_as_equal():
    eclipse = np.array([100.0, 2000.0, 0.0, 5.0])
    flow = np.array([100.005, 2000.0, 0.0, 5.0])

    row = compare.compare_arrays("TRANZ", eclipse, flow, tolerance=1e-4)

    assert row["differing"] == 0
    assert row["max_abs_diff"] == np.float64(100.005) - 100.0


def test_differences_are_relative_to_the_larger_value_and_zero_pairs_are_equal():
    eclipse = np.array([200.0, 0.0, 0.0, 50.0])
    flow = np.array([2000.0, 0.0, 30.0, 50.0])

    row = compare.compare_arrays("TRANZ", eclipse, flow, tolerance=1e-4)

    assert row["differing"] == 2
    assert row["max_rel_diff"] == 1.0  # zero against non-zero
    assert row["sum_ratio"] == 2080.0 / 250.0


def test_arrays_over_different_cells_are_reported_without_statistics():
    row = compare.compare_arrays("DEPTH", np.zeros(4), np.zeros(3), tolerance=1e-4)

    assert (row["cells"], row["flow_cells"], row["differing"]) == (4, 3, "")


def test_vector_differences_are_scaled_by_the_eclipse_maximum():
    eclipse = np.array([0.0, 50.0, 100.0, 80.0])
    flow = np.array([0.0, 55.0, 90.0, 84.0])

    row = compare.vector_differences(eclipse, flow)

    assert (row["eclipse_last"], row["flow_last"]) == (80.0, 84.0)
    assert row["last_diff_pct"] == 5.0
    assert row["max_diff_pct_of_max"] == 10.0
    assert row["mean_diff_pct_of_max"] == 100 * (0 + 5 + 10 + 4) / 4 / 100.0


def test_vector_that_is_zero_throughout_has_no_percentages():
    row = compare.vector_differences(np.zeros(3), np.zeros(3))

    assert (row["last_diff_pct"], row["max_diff_pct_of_max"]) == ("", "")


def test_balance_error_is_zero_when_in_place_follows_injection_and_production():
    injected = np.array([0.0, 100.0, 250.0])
    produced = np.array([0.0, 30.0, 90.0])
    in_place = 1000.0 + injected - produced

    assert compare.balance_error(in_place, injected, produced).tolist() == [0.0, 0.0, 0.0]


def test_balance_error_reports_fluid_that_is_unaccounted_for():
    injected = np.array([0.0, 100.0, 250.0])
    produced = np.array([0.0, 30.0, 90.0])
    in_place = np.array([1000.0, 1065.0, 1140.0])  # 5, then 20, less than accounted for

    assert compare.balance_error(in_place, injected, produced).tolist() == [0.0, -5.0, -20.0]
