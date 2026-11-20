"""Facts read from the Discovery evaluation report (``disc1993``), and their registration.

    python -m dockit.disc_facts write      # rewrite data/facts/disc1993.csv

The report is a scan. Values were read from the page images; Table 10.1 was
checked digit by digit against the scan, the other tables were read once.
The report states percentiles as P(90), mean and P(10), with P(90) the low
value. Page numbers are PDF pages.
"""

from __future__ import annotations

import argparse
import csv

from syskit.facts import COLUMNS
from syskit.paths import data_dir

AS_OF = "1993-12"

# Tables 10.1 to 10.4: oil prospects. (P90, mean, P10) in place and recoverable,
# million Sm3 oil; discovery probability; PDF page; checked against the scan.
OIL_RESOURCES = {
    "theta_vest": ("Theta Vest", (7.22, 10.33, 12.83), (3.18, 4.55, 5.68), 1.00, 179, True),
    "theta_vest_west": (
        "Theta Vest, western segment", (4.17, 5.90, 7.50), (1.81, 2.60, 3.35), 1.00, 180, False,
    ),
    "theta_vest_east": (
        "Theta Vest, eastern segment", (3.62, 4.91, 6.15), (1.57, 2.17, 2.76), 0.90, 181, False,
    ),
    "theta_c": ("Theta C prospect", (8.28, 16.24, 25.86), (3.30, 6.51, 10.39), 0.12, 182, False),
}  # fmt: skip
# Table 10.1, page 179: associated gas for Theta Vest, billion Sm3.
THETA_VEST_GAS = {"in_place": (1.17, 1.65, 2.04), "recoverable": (0.50, 0.72, 0.90)}
# Table 10.1, page 179: input ranges for Theta Vest (minimum, most likely, maximum).
THETA_VEST_INPUTS = {
    "reservoir_thickness": ((18.00, 27.00, 36.00), "m"),
    "hydrocarbon_column": ((128.00, 191.00, 196.00), "m"),
    "net_gross_ratio": ((0.90, 0.92, 0.99), "fraction"),
    "porosity": ((0.19, 0.23, 0.26), "fraction"),
    "oil_saturation": ((0.80, 0.89, 0.95), "fraction"),
    "shrinkage_factor": ((0.64, 0.67, 0.69), "Sm3/m3"),
    "gas_oil_ratio": ((150.00, 158.00, 169.00), "Sm3/Sm3"),
    "oil_recovery_factor": ((0.35, 0.45, 0.50), "fraction"),
}
# Table 7.1, page 110, and Table 6.2, page 107: well 15/9-19 SR.
WELL = {
    "dst_max_oil_rate": (1358, "Sm3/d", "p110 table 7.1"),
    "dst_test_permeability": (914, "mD", "p110 table 7.1"),
    "dst_productivity_index": (144, "Sm3/d/bar", "p110 table 7.1"),
    "dst_reservoir_pressure": (327.7, "bar", "p110 table 7.1"),
    "dst_reservoir_temperature": (106.2, "degC", "p110 table 7.1"),
    "hugin_thickness": (18.059, "m TVT", "p107 table 6.2"),
    "hugin_porosity": (0.226, "fraction", "p107 table 6.2"),
    "hugin_water_saturation": (0.110, "fraction", "p107 table 6.2"),
    "hugin_net_gross": (0.924, "fraction", "p107 table 6.2"),
    "hugin_permeability": (2913.2, "mD", "p107 table 6.2"),
}


def rows() -> list[tuple]:
    out: list[tuple] = []

    def add(fid, quantity, value, unit, basis, subject, locator, confidence, note=""):
        out.append(
            (
                f"disc1993.{fid}",
                quantity,
                value,
                unit,
                basis,
                AS_OF,
                subject,
                "disc1993",
                locator,
                "vision",
                confidence,
                note,
            )
        )

    low = "P(90) is the low value"
    for key, (subject, in_place, recoverable, probability, page, checked) in OIL_RESOURCES.items():
        confidence = "high" if checked else "medium"
        note = low if checked else f"{low}; read once, not rechecked against the scan"
        locator = f"p{page} table 10.{page - 178}"
        for basis, value in zip(("P90", "mean", "P10"), in_place, strict=True):
            add(f"stooip.{key}.{basis.lower()}", "stooip", value, "MSm3", basis, subject, locator,
                confidence, note)  # fmt: skip
        for basis, value in zip(("P90", "mean", "P10"), recoverable, strict=True):
            add(f"recoverable_oil.{key}.{basis.lower()}", "recoverable_oil", value, "MSm3", basis,
                subject, locator, confidence, note)  # fmt: skip
        add(f"discovery_probability.{key}", "discovery_probability", probability, "fraction",
            "estimate", subject, locator, confidence)  # fmt: skip
    for name, values in THETA_VEST_GAS.items():
        for basis, value in zip(("P90", "mean", "P10"), values, strict=True):
            add(f"associated_gas_{name}.theta_vest.{basis.lower()}", f"associated_gas_{name}",
                value, "GSm3", basis, "Theta Vest", "p179 table 10.1", "high", low)  # fmt: skip
    for name, (values, unit) in THETA_VEST_INPUTS.items():
        for basis, value in zip(("minimum", "most likely", "maximum"), values, strict=True):
            add(f"input.{name}.{basis.replace(' ', '_')}", name, value, unit, basis, "Theta Vest",
                "p179 table 10.1", "high")  # fmt: skip
    for name, (value, unit, locator) in WELL.items():
        add(f"well.{name}", name, value, unit, "measured", "Well 15/9-19 SR", locator, "medium",
            "Read once, not rechecked against the scan")  # fmt: skip
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("write",))
    parser.parse_args(argv)
    target = data_dir() / "facts" / "disc1993.csv"
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(COLUMNS)
        writer.writerows(rows())
    print(f"{len(rows())} facts written to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
