"""Checks against the data of the expert study, which is part of the repository."""

import numpy as np

from rcfkit import data, expert, exploration, fields, volve


def test_resource_account_agrees_with_sodir_after_the_year_labels_are_put_right():
    merged = data.resource_account().merge(data.sodir_reserves(), on=["field_id", "year"])
    agrees = (merged["oil_reserves"] - merged["oil"]).abs() < 0.06

    by_year = agrees.groupby(merged["year"]).mean()

    assert by_year.loc[2020] > 0.97 and by_year.loc[2021] > 0.97
    assert by_year.min() > 0.97


def test_the_expert_studys_reference_class_is_reproduced():
    fractions = expert.reference_class()

    assert len(fractions) == 102
    low, median, high = np.quantile(fractions[5], [0.1, 0.5, 0.9])
    # Values in the study's workbook, row for the fifth year.
    assert np.allclose([low, median, high], [0.153947, 0.515163, 0.918415], atol=1e-6)


def test_the_expert_studys_volume_totals_are_reproduced():
    in_place = expert.volumes()["in_place"]

    assert round(in_place["prognosis"], 1) == 11342.0
    assert round(in_place["result"], 1) == 1754.7
    assert round(in_place["correlation"], 3) == 0.062


def test_volve_discovery_well_in_the_prognosis_data():
    prospects = volve.prospect().set_index("prospect")

    assert list(prospects["discovery"]) == [0.0, 1.0]
    assert list(prospects["p"]) == [0.72, 0.324]
    assert np.isclose(prospects.loc["LOKE-WEST-139", "ip_oe_res"], 2.93)


def test_every_prospect_in_the_probability_sample_is_counted_once():
    sample = exploration.probability_sample()

    assert not sample.duplicated(["well", "prospect"]).any()
    assert sample["p"].between(0, 1).all()
    assert set(sample["discovery"]) == {0.0, 1.0}


def test_volve_is_in_the_field_table_and_never_in_its_own_class():
    row = fields.candidates().set_index("field").loc[volve.FIELD]

    assert row["excluded"] == ""
    assert (row["fid_oil"], row["fid_gas"]) == (11.876, 1.303)
    assert str(row["start"]) == "2008-02"
    for name in volve.CLASSES:
        assert volve.FIELD not in set(volve.members(name)["field"])
