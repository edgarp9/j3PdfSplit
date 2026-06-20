"""Browser integration helpers."""

from __future__ import annotations

import webbrowser


def open_url(url: str) -> bool:
    """Open a URL in the user's default browser."""
    return webbrowser.open_new_tab(url)
