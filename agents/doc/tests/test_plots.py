import numpy as np

from dockit.plots import Axis, cluster_1d, despike, longest_run, plot_area, trace, yearly_mean


def test_axis_maps_positions_to_values_and_back():
    axis = Axis(161.0, 0.0, 9.0, 9000.0)  # pixel rows run downwards

    assert axis.value(85.0) == 4500.0
    assert axis.position(9000.0) == 9.0
    assert axis.value(axis.position(1234.5)) == 1234.5


def test_longest_run_bridges_short_gaps_only():
    flags = np.array([0, 1, 1, 0, 1, 1, 1, 0, 0, 0, 1, 1], dtype=bool)

    assert longest_run(flags) == (4, 6)
    assert longest_run(flags, bridge=1) == (1, 6)
    assert longest_run(flags, bridge=3) == (1, 11)


def test_plot_area_is_found_through_gridlines():
    image = np.full((60, 80, 3), 255)
    image[10:50, 20:70] = 192  # grey plot area
    image[20, 20:70] = 0  # gridlines
    image[30, 20:70] = 0

    def grey(a):
        return a[:, :, 0] == 192

    assert plot_area(image, grey) == (20, 10, 69, 49)


def test_trace_gives_the_middle_row_of_the_curve_in_each_column():
    mask = np.zeros((20, 10), dtype=bool)
    mask[5, 2] = True
    mask[6:9, 3] = True  # steep part: three pixels in one column
    mask[10, 4] = True
    mask[2, 9] = True  # outside the plot area

    columns, rows = trace(mask, (2, 0, 6, 19))

    assert columns.tolist() == [2, 3, 4]
    assert rows.tolist() == [5, 7, 10]


def test_despike_removes_a_stray_pixel_but_keeps_a_step():
    curve = np.array([10.0, 10, 10, 30, 10, 10, 10, 10, 50, 50, 50, 50])

    assert despike(curve).tolist() == [10] * 8 + [50] * 4


def test_cluster_1d_splits_at_gaps():
    groups = cluster_1d(np.array([5.0, 1.0, 1.5, 9.0, 5.2]), gap=2.0)

    assert [g.tolist() for g in groups] == [[1.0, 1.5], [5.0, 5.2], [9.0]]


def test_yearly_mean_uses_only_the_years_the_series_covers():
    years = np.array([2007.5, 2007.9, 2008.2, 2008.6])
    values = np.array([100.0, 300.0, 400.0, 600.0])

    assert yearly_mean(years, values, 2006, 2009) == {2007: 200.0, 2008: 500.0}
