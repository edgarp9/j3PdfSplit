"""Application metadata shared by UI and packaging-facing code."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version

APP_NAME = "j3PdfSplit"
AUTHOR_URL = "https://github.com/edgarp9"
PACKAGE_NAME = "pdf-sequential-splitter"
PROJECT_URL = "https://github.com/edgarp9/j3PdfSplit"
FALLBACK_VERSION = "0.1.0"


def app_version() -> str:
    """Return the installed package version, or the source-tree fallback."""
    try:
        return version(PACKAGE_NAME)
    except PackageNotFoundError:
        return FALLBACK_VERSION
