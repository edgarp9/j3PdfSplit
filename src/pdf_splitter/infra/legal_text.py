"""Helpers for loading bundled legal text resources."""

from __future__ import annotations

import logging
import sys
from collections.abc import Iterator
from pathlib import Path

LOGGER = logging.getLogger(__name__)


def _resource_roots() -> Iterator[Path]:
    pyinstaller_root = getattr(sys, "_MEIPASS", None)
    if pyinstaller_root:
        yield Path(pyinstaller_root)

    if getattr(sys, "frozen", False):
        executable_dir = Path(sys.executable).resolve().parent
        yield executable_dir
        yield executable_dir / "lib"

    yield Path(__file__).resolve().parents[2]


def read_legal_text(filename: str, *, fallback: str) -> str:
    """Read a legal text file from source or PyInstaller resource locations."""
    for root in _resource_roots():
        path = root / filename
        if not path.is_file():
            continue
        try:
            return path.read_text(encoding="utf-8")
        except OSError as exc:
            LOGGER.warning("Could not read legal text resource %s: %s", path, exc)

    LOGGER.warning("Legal text resource not found: %s", filename)
    return fallback
