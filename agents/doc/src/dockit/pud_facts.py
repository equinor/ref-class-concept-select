"""Facts read from the Volve PDO (``pud2005``), and the script that registers them.

    python -m dockit.pud_facts write      # rewrite data/facts/pud2005.csv

The values below are the single definition used by the fact register, the
analysis document and the comparison report. Page numbers are PDF pages.
All were read from the text layer of the born-digital PDF; percentiles follow
the document's convention, in which P90 is the low case.
"""

from __future__ import annotations

import argparse
import csv

from syskit.facts import COLUMNS
from syskit.paths import data_dir

AS_OF = "2005-02"
CASES = ("mean", "P90", "P50", "P10")

# Table 3.3, page 19: deterministic volumes, million Sm3 oil in place.
STOOIP_BASE = {
    "four_way_closure": ("Volve four-way closure", 24.5, "Volve 4-veis lukning"),
    "south": ("Volve South", 5.9, "Volve Sør"),
    "other_prospects": ("Other prospects", 0.4, "Øvrige prospekter"),
    "total": ("Volve and nearby prospects", 30.8, "Totalt"),
}
# Table 3.4, page 19: uncertainty study; base, mean, P90, P50, P10, standard deviation.
STOOIP_STUDY = {
    "east": ("Volve closure East", "Øst", (19.9, 19.2, 15.9, 19.1, 22.8, 2.6)),
    "west": ("Volve closure West", "Vest", (4.6, 8.3, 3.4, 7.5, 14.6, 4.3)),
    "closure": ("Volve closure", "Volve lukningen", (24.5, 27.5, 20.9, 26.7, 35.2, 5.5)),
    "prospects": ("Prospects", "Prospekter", (6.3, 13.8, 5.0, 9.9, 30.0, 11.6)),
    "risked_prospects": (
        "Risked prospects",
        "Riskede Prospekter",
        (3.9, 9.4, 0.2, 6.7, 24.3, 11.1),
    ),
    "total": ("Volve closure and prospects", "Totalt", (30.8, 41.3, 27.2, 36.4, 64.7, 15.8)),
    "total_risked": (
        "Volve closure and risked prospects",
        "Totalt risket volum",
        (28.4, 36.9, 23.0, 32.8, 58.2, 14.8),
    ),
}
# Table 3.5, page 19: possible oil-water contact (m) and probability (%).
CONTACTS = {3105: 24, 3120: 21, 3135: 28, 3170: 14, 3260: 7, 3330: 6}
# Table 4.5, page 25: reserves and oil in place, million Sm3.
RESERVES = {"mean": 11.40, "P90": 9.0, "P50": 11.35, "P10": 15.31}
STOOIP = {"mean": 27.50, "P90": 20.9, "P50": 26.70, "P10": 35.2}
# Table 4.5: oil production per year, million Sm3. 2007 is from March. Each case
# stops when the oil rate reaches the economic minimum of 2100 Sm3/d.
OIL_PER_YEAR = {
    "mean": {2007: 1.53, 2008: 3.10, 2009: 2.96, 2010: 2.14, 2011: 1.25, 2012: 0.40},
    "P90": {2007: 1.44, 2008: 3.10, 2009: 2.83, 2010: 1.49, 2011: 0.10},
    "P50": {2007: 1.53, 2008: 3.10, 2009: 2.96, 2010: 2.13, 2011: 1.22, 2012: 0.40},
    "P10": {
        2007: 1.54, 2008: 3.10, 2009: 3.15, 2010: 2.82, 2011: 1.82, 2012: 1.25, 2013: 0.88,
        2014: 0.75,
    },
}  # fmt: skip
# Table 4.6, page 26: expected sales products from the gas. 2007 is from 6 March.
GAS_PRODUCTS = {  # year: dry gas (million Sm3), NGL, condensate, ethane (tonnes)
    2007: (170, 25570, 10228, 1705),
    2008: (371, 55608, 22243, 3707),
    2009: (359, 53874, 21550, 3592),
    2010: (272, 40844, 16338, 2723),
    2011: (133, 19921, 7969, 1328),
    2012: (33, 5015, 2006, 334),
}
GAS_PRODUCTS_TOTAL = (1338, 200832, 80334, 13389)
# Tables 4.3 and 7.1, pages 23 and 35: design capacities.
CAPACITY = {
    "oil_capacity": (9000, "Sm3/d"),
    "liquid_capacity": (13000, "Sm3/d"),
    "gas_capacity": (1.5, "MSm3/d"),
    "water_injection_capacity": (16000, "Sm3/d"),
    "maximum_water_cut": (0.80, "fraction"),
}
# Table 12.1, page 48: investments, million NOK 2005.
INVESTMENTS_2005 = {
    "wells": 937,
    "mobilisation_of_platform": 291,
    "export_system_including_storage_vessel": 391,
    "project_management_including_reserve": 349,
    "total": 1968,
}
# Table 12.6, page 49: costs per year, million NOK nominal. 2012 covers five months.
COST_YEARS = (2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012)
COSTS_NOMINAL = {
    "wells": ((7, 67, 828, 189, None, None, None, None), 1091),
    "mobilisation_subsea_project_management": ((156, 720, None, None, None, None, None, None), 876),
    "unforeseen": ((None, 76, None, None, None, None, None, None), 76),
    "total_investments": ((163, 863, 828, 189, None, None, None, None), 2043),
    "lease_investment_element_and_tariff": ((None, None, 508, 734, 717, 513, 384, 142), 2998),
    "lease_operation_and_maintenance": ((None, None, 157, 250, 261, 268, 275, 116), 1327),
    "operator_operating_costs": ((5, 32, 170, 165, 167, 168, 173, 74), 954),
    "decommissioning": ((None, None, None, None, None, None, None, 61), 61),
    "plugging_of_wells": ((None, None, None, None, None, None, None, 110), 110),
    "total_operating_costs": ((5, 32, 835, 1149, 1145, 949, 832, 503), 5450),
    "total_costs": ((168, 895, 1663, 1338, 1145, 949, 832, 503), 7493),
}
# Table 12.7, page 50: economic assumptions.
ASSUMPTIONS = {
    "oil_price_brent_expected": (22, "USD/bbl", "p50 table 12.7"),
    "oil_price_brent_low": (15, "USD/bbl 2004", "p50 table 12.7"),
    "oil_price_brent_forward": (35, "USD/bbl nominal", "p50 table 12.7"),
    "price_penalty_volve_oil": (3.3, "USD/bbl 2004", "p50 table 12.7"),
    "oil_price_volve": (18.70, "USD/bbl", "p50 table 12.8"),
    "exchange_rate": (6.75, "NOK/USD", "p50 table 12.7"),
    "inflation": (2.5, "% per year", "p50 table 12.7"),
    "regularity": (94, "%", "p38 section 7.5"),
    "economic_production_period": (63, "months", "p50 section 12.2.1"),
    "minimum_economic_oil_rate": (2100, "Sm3/d", "p23 section 4.5.1"),
    "plateau_oil_rate": (9000, "Sm3/d", "p23 section 4.5.1"),
    "plateau_duration": (19, "months", "p23 section 4.5.1"),
    "expected_recovery_factor": (43, "%", "p26 section 4.8"),
    "rich_gas_cumulative": (1.5, "GSm3", "p24 section 4.5.3"),
    "break_even_price_brent": (17.50, "USD/bbl 2004", "p50 section 12.2.3"),
    "lease_period_committed": (3, "years", "p48 section 12.1.2"),
    "design_life": (10, "years", "p34 section 7.3.1"),
    "oil_producers_planned": (3, "wells", "p8 section 1.6"),
    "water_injectors_planned": (3, "wells", "p8 section 1.6"),
    "utsira_water_producers_planned": (2, "wells", "p8 section 1.6"),
    "well_slots": (13, "wells", "p8 section 1.7"),
}
# Tables 12.8 and 12.9, pages 50 and 51: net present value, million NOK 2005,
# before tax at 7 % and after tax at 8 %.
NPV = {
    "expected_price": (2534, 443),
    "forward_price": (5565, 1196),
    "low_price": (-211, -233),
    "p90_profile": (1520, 203),
    "p10_profile": (3677, 718),
    "investments_plus_300": (2247, 359),
    "investments_minus_300": (2822, 526),
    "two_extra_wells": (2295, 373),
}
IRR_AFTER_TAX = {"expected_price": 18.3, "forward_price": 38.7}
# Table 13.1, page 52: prospects; discovery probability, resources, risked resources.
PROSPECTS = {
    "volve_south": ("Volve Sør", 0.56, 5.9, 3.3),
    "theta_south": ("Theta Sør", 0.22, 27.5, 6.1),
    "western_prospects": ("Western prospects", 0.20, 30, 6),
}
TEXT = {
    "production_start_planned": ("March 2007", "p23 table 4.3", "Assumed production start"),
    "chosen_concept": (
        "Leased jack-up platform (Mærsk Inspirer) with process plant, wells drilled from the "
        "platform, rich gas exported to Sleipner A, oil exported by shuttle tanker via the "
        "leased storage vessel Navion Saga",
        "p8 section 1.7; p34 section 7.1",
        "",
    ),
    "drainage_strategy": (
        "Three producers high on the structure and three water injectors on the flanks; "
        "pressure kept above the bubble point by water injection; gas lift for start-up",
        "p22 section 4.4",
        "",
    ),
}


def rows() -> list[tuple]:
    """Every fact as a row of the register."""
    out: list[tuple] = []

    def add(fid, quantity, value, unit, basis, subject, locator, note="", confidence="high"):
        out.append(
            (
                f"pud2005.{fid}",
                quantity,
                value,
                unit,
                basis,
                AS_OF,
                subject,
                "pud2005",
                locator,
                "read",
                confidence,
                note,
            )
        )

    low = "P90 is the low case"
    for key, (subject, value, label) in STOOIP_BASE.items():
        add(
            f"stooip.t33.{key}",
            "stooip",
            value,
            "MSm3",
            "base",
            subject,
            "p19 table 3.3",
            f"Norwegian label: {label}",
        )
    for key, (subject, label, values) in STOOIP_STUDY.items():
        for basis, value in zip(("base", "mean", "P90", "P50", "P10", "sd"), values, strict=True):
            quantity = "stooip_sd" if basis == "sd" else "stooip"
            add(
                f"stooip.t34.{key}.{basis.lower()}",
                quantity,
                value,
                "MSm3",
                basis,
                subject,
                "p19 table 3.4",
                f"Norwegian label: {label}. Uncertainty study; {low}",
            )
    for depth, probability in CONTACTS.items():
        add(
            f"owc_probability.{depth}",
            "owc_probability",
            probability,
            "%",
            "estimate",
            f"Oil-water contact at {depth} m",
            "p19 table 3.5",
        )
    for case in CASES:
        add(
            f"stooip.t45.{case.lower()}",
            "stooip",
            STOOIP[case],
            "MSm3",
            case,
            "Volve closure",
            "p25 table 4.5",
            f"Uncertainty study; {low}",
        )
        add(
            f"recoverable_oil.t45.{case.lower()}",
            "recoverable_oil",
            RESERVES[case],
            "MSm3",
            case,
            "Volve",
            "p25 table 4.5",
            f"Reserves at a minimum oil rate of 2100 Sm3/d; {low}",
        )
        for year, value in OIL_PER_YEAR[case].items():
            note = "From March" if year == 2007 else ""
            add(
                f"oil_production.{case.lower()}.{year}",
                "oil_production_forecast",
                value,
                "MSm3",
                case,
                f"Volve, {year}",
                "p25 table 4.5",
                note,
            )
    add(
        "stooip.summary",
        "stooip",
        27.5,
        "MSm3",
        "mean",
        "Volve",
        "p7 section 1.3",
        "Summary text: 27,5 millioner Sm3 tilstedeværende olje",
    )
    names = ("dry_gas", "ngl", "condensate", "ethane")
    units = ("million Sm3", "tonnes", "tonnes", "tonnes")
    for year, values in {**GAS_PRODUCTS, "total": GAS_PRODUCTS_TOTAL}.items():
        for name, unit, value in zip(names, units, values, strict=True):
            add(
                f"gas_products.{name}.{year}",
                f"{name}_sales_forecast",
                value,
                unit,
                "mean",
                f"Volve, {year}",
                "p26 table 4.6",
            )
    for key, (value, unit) in CAPACITY.items():
        add(
            f"capacity.{key}",
            key,
            value,
            unit,
            "design",
            "Production platform",
            "p23 table 4.3; p35 table 7.1",
        )
    for key, value in INVESTMENTS_2005.items():
        add(
            f"investments_2005.{key}",
            "investment",
            value,
            "MNOK-2005",
            "estimate",
            key.replace("_", " "),
            "p48 table 12.1",
        )
    for key, (per_year, total) in COSTS_NOMINAL.items():
        for year, value in zip(COST_YEARS, per_year, strict=True):
            if value is not None:
                note = "Five months of operation" if year == 2012 else ""
                add(
                    f"costs_nominal.{key}.{year}",
                    "cost",
                    value,
                    "MNOK nominal",
                    "estimate",
                    f"{key.replace('_', ' ')}, {year}",
                    "p49 table 12.6",
                    note,
                )
        add(
            f"costs_nominal.{key}.total",
            "cost",
            total,
            "MNOK nominal",
            "estimate",
            f"{key.replace('_', ' ')}, 2005-2012",
            "p49 table 12.6",
        )
    for key, (value, unit, locator) in ASSUMPTIONS.items():
        add(f"assumption.{key}", key, value, unit, "assumption", "Volve", locator)
    for key, (before, after) in NPV.items():
        subject = key.replace("_", " ")
        add(
            f"npv.before_tax_7.{key}",
            "npv_before_tax_7pct",
            before,
            "MNOK-2005",
            "estimate",
            subject,
            "p50 table 12.8; p51 table 12.9",
        )
        add(
            f"npv.after_tax_8.{key}",
            "npv_after_tax_8pct",
            after,
            "MNOK-2005",
            "estimate",
            subject,
            "p50 table 12.8; p51 table 12.9",
        )
    for key, value in IRR_AFTER_TAX.items():
        add(
            f"irr.after_tax.{key}",
            "irr_after_tax",
            value,
            "%",
            "estimate",
            key.replace("_", " "),
            "p50 table 12.8",
        )
    for key, (subject, probability, resources, risked) in PROSPECTS.items():
        note = "The table prints no unit; million Sm3 by comparison with table 3.3"
        add(
            f"prospect.{key}.probability",
            "discovery_probability",
            probability,
            "fraction",
            "estimate",
            subject,
            "p52 table 13.1",
        )
        add(
            f"prospect.{key}.resources",
            "resources",
            resources,
            "MSm3",
            "estimate",
            subject,
            "p52 table 13.1",
            note,
            "medium",
        )
        add(
            f"prospect.{key}.risked",
            "risked_resources",
            risked,
            "MSm3",
            "estimate",
            subject,
            "p52 table 13.1",
            note,
            "medium",
        )
    for key, (value, locator, note) in TEXT.items():
        out.append(
            (
                f"pud2005.text.{key}",
                key,
                value,
                "text",
                "plan",
                AS_OF,
                "Volve",
                "pud2005",
                locator,
                "translated",
                "high",
                note,
            )
        )
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("write",))
    parser.parse_args(argv)
    target = data_dir() / "facts" / "pud2005.csv"
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(COLUMNS)
        writer.writerows(rows())
    print(f"{len(rows())} facts written to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
