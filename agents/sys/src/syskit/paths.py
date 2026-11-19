"""Locations used by every domain.

Raw data lives outside the repository. Its location is taken from the
``VOLVE_DATA`` environment variable and falls back to ``../volve_data``
relative to the repository root.
"""

from __future__ import annotations

import os
from pathlib import Path

_MARKER = "AGENTS.md"


def repo_root() -> Path:
    """Return the repository root (the directory holding ``AGENTS.md``)."""
    for start in (Path(__file__).resolve(), Path.cwd().resolve()):
        for candidate in (start, *start.parents):
            if (candidate / _MARKER).is_file() and (candidate / "pyproject.toml").is_file():
                return candidate
    raise RuntimeError(f"repository root not found: no directory with {_MARKER} above here")


def volve_data() -> Path:
    """Return the raw data directory. Raises if it does not exist."""
    configured = os.environ.get("VOLVE_DATA")
    path = Path(configured).expanduser() if configured else repo_root().parent / "volve_data"
    path = path.resolve()
    if not path.is_dir():
        origin = "VOLVE_DATA" if configured else "default ../volve_data"
        raise FileNotFoundError(f"raw data directory not found: {path} (from {origin})")
    return path


def data_dir() -> Path:
    """Return the versioned, shared data directory inside the repository."""
    return repo_root() / "data"
