"""The presentation ``rcf_volve_v2.pptx`` as a web page, with slides of the workflow deck.

    python -m syskit.rcf_volve_deck build

writes ``agents/sys/out/rcf_volve_v2/index.html``. The slides of the
PowerPoint file are laid out as in the file, with its pictures taken from
the original figure files where the repository holds them. Four slides of
the workflow deck (``syskit.workflow_deck``) are added: its slide 3 fills
the PowerPoint's slide 4, which has a title only; its slides 6, 12 and 13
follow at the end. ``figures.csv`` lists where each picture comes from.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path

from syskit import pptx, workflow_deck
from syskit.paths import repo_root
from syskit.slides import Deck

SOURCE = "agents/sys/out/rcf_volve_v2.pptx"
OUT = "agents/sys/out/rcf_volve_v2"
ORIGINALS = ("agents/rcf/study/figures", "agents/rcf/study", "agents/rcf/out/figs")
WORKFLOW_SLIDE = 4  # the PowerPoint slide that has only a title


def originals(root: Path) -> dict[str, Path]:
    """Figure files of the reports and of the expert study, by checksum."""
    found: dict[str, Path] = {}
    for folder in ORIGINALS:
        for path in sorted((root / folder).glob("*.png")):
            found.setdefault(hashlib.sha256(path.read_bytes()).hexdigest(), path)
    return found


def place_pictures(source: Path, target: Path, root: Path) -> tuple[dict[str, str], list[dict]]:
    """Write the presentation's pictures to ``target``; return their addresses and origins.

    A picture that is byte for byte a figure file of the repository is written
    under that file's name and recorded with its path.
    """
    known = originals(root)
    target.mkdir(parents=True, exist_ok=True)
    addresses, rows = {}, []
    for name, content in sorted(pptx.media(source).items()):
        original = known.get(hashlib.sha256(content).hexdigest())
        file_name = original.name.replace(" ", "_") if original else f"pptx_{name}"
        (target / file_name).write_bytes(content)
        addresses[name] = f"figs/{file_name}"
        rows.append(
            {
                "file": file_name,
                "in_presentation": name,
                "original": original.relative_to(root).as_posix() if original else "",
            }
        )
    return addresses, rows


def build(target_dir: Path) -> Path:
    root = repo_root()
    source = root / SOURCE
    figures = target_dir / "figs"
    addresses, rows = place_pictures(source, figures, root)
    slides = pptx.read(source)

    numbers = workflow_deck.numbers()
    diagrams = {
        "roles": workflow_deck.roles(),
        "use-case": workflow_deck.use_case(numbers),
        "concept-comparison": workflow_deck.concept_comparison(numbers),
    }
    for name, drawing in diagrams.items():
        drawing.write(figures / f"{name}.svg")
        rows.append({"file": f"{name}.svg", "in_presentation": "",
                     "original": f"agents/sys/out/workflow-deck/figs/{name}.svg"})  # fmt: skip

    deck = Deck("Bias Busting Decision Analysis")
    for slide in slides:
        content = slide.html(addresses)
        if slide.number == WORKFLOW_SLIDE:
            content += (
                '<img class="abs" src="figs/roles.svg" alt="" '
                'style="left:70px;top:236px;width:1460px;height:640px;object-fit:contain">'
            )
        deck.raw_slide(content)
    deck.figure_slide("First use", "figs/use-case.svg")
    deck.figure_slide("The 2005 plan and the modified plan", "figs/concept-comparison.svg")
    workflow_deck.changes_slide(deck, numbers)

    with (target_dir / "figures.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, ("file", "in_presentation", "original"), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    skipped = [f"slide {s.number}: {item}" for s in slides for item in s.skipped]
    if skipped:
        raise SystemExit("not converted: " + "; ".join(skipped))
    return deck.write(target_dir / "index.html")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("build",))
    parser.parse_args(argv)
    target = build(repo_root() / OUT)
    print(f"written: {target} ({target.stat().st_size / 1e3:.0f} kB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
