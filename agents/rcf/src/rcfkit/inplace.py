"""Reference class for a volume in place that rests on a prognosis, not on a well.

The class is the record of exploration prospects that turned out to be
discoveries: the volume in place recorded after drilling over the volume
prognosed before it (``rcfkit.exploration``). It applies to any part of an
in-place estimate that no well has tested — an undrilled prospect, or an
undrilled segment or flank of a discovered field.
"""

from __future__ import annotations

import numpy as np

from rcfkit import exploration


def prognosis_ratios(
    *, spudded_before: int | None = None, phase_as_prognosed: bool = False
) -> np.ndarray:
    """Volume in place found over volume prognosed, one value per discovery.

    ``spudded_before`` keeps only wells spudded before that year, i.e. the
    record as it stood then. ``phase_as_prognosed`` keeps the discoveries with
    a single prognosis and the main phase found as prognosed, and compares the
    main-phase volumes; the default compares oil equivalents of all phases and
    includes discoveries that came in with another phase.
    """
    if phase_as_prognosed:
        sample = exploration.range_sample()
        ratio = sample["outcome"] / sample["central"]
    else:
        sample = exploration.volume_sample("ip")
        ratio = sample["ratio"]
    if spudded_before is not None:
        ratio = ratio[sample["spud_year"] < spudded_before]
    return ratio.to_numpy()
