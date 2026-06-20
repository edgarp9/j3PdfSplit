"""Windows DPI-awareness helpers for Tkinter startup."""

from __future__ import annotations

import ctypes
import logging
import sys
from ctypes import wintypes

LOGGER = logging.getLogger(__name__)

_PROCESS_PER_MONITOR_DPI_AWARE = 2
_PROCESS_SYSTEM_DPI_AWARE = 1
_DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE = ctypes.c_void_p(-3)
_DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = ctypes.c_void_p(-4)
_DPI_AWARENESS_CONTEXT_SYSTEM_AWARE = ctypes.c_void_p(-2)
_ERROR_ACCESS_DENIED = 5
_S_OK = 0
_E_ACCESSDENIED = ctypes.c_long(0x80070005).value


def configure_process_dpi_awareness() -> str:
    """Configure the current process for crisp DPI-aware Tk rendering."""
    if sys.platform != "win32":
        return "unsupported-platform"

    for configure in (
        _set_system_awareness,
        _set_per_monitor_awareness,
        _set_per_monitor_awareness_v2,
        _set_shcore_system_awareness,
        _set_shcore_per_monitor_awareness,
        _set_legacy_system_dpi_awareness,
    ):
        strategy = configure()
        if strategy is not None:
            return strategy

    return "unavailable"


def _set_per_monitor_awareness() -> str | None:
    return _set_awareness_context(
        _DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE,
        "per-monitor-v1",
    )


def _set_per_monitor_awareness_v2() -> str | None:
    return _set_awareness_context(
        _DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2,
        "per-monitor-v2",
    )


def _set_system_awareness() -> str | None:
    return _set_awareness_context(
        _DPI_AWARENESS_CONTEXT_SYSTEM_AWARE,
        "system-aware",
    )


def _set_awareness_context(context: wintypes.HANDLE, strategy: str) -> str | None:
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        set_process_dpi_awareness_context = user32.SetProcessDpiAwarenessContext
    except (AttributeError, OSError):
        return None

    set_process_dpi_awareness_context.argtypes = [wintypes.HANDLE]
    set_process_dpi_awareness_context.restype = wintypes.BOOL
    if set_process_dpi_awareness_context(context):
        return strategy

    last_error = ctypes.get_last_error()
    if last_error == _ERROR_ACCESS_DENIED:
        LOGGER.debug("DPI awareness context was already configured before Tk startup.")
        return "already-configured"
    return None


def _set_shcore_per_monitor_awareness() -> str | None:
    return _set_shcore_awareness(_PROCESS_PER_MONITOR_DPI_AWARE, "per-monitor-v1")


def _set_shcore_system_awareness() -> str | None:
    return _set_shcore_awareness(_PROCESS_SYSTEM_DPI_AWARE, "system-aware")


def _set_shcore_awareness(awareness: int, strategy: str) -> str | None:
    try:
        shcore = ctypes.WinDLL("shcore", use_last_error=True)
        set_process_dpi_awareness = shcore.SetProcessDpiAwareness
    except (AttributeError, OSError):
        return None

    set_process_dpi_awareness.argtypes = [ctypes.c_int]
    set_process_dpi_awareness.restype = ctypes.c_long
    result = set_process_dpi_awareness(awareness)
    if result == _S_OK:
        return strategy
    if result == _E_ACCESSDENIED:
        LOGGER.debug("SHCore DPI awareness was already configured before Tk startup.")
        return "already-configured"
    return None


def _set_legacy_system_dpi_awareness() -> str | None:
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        set_process_dpi_aware = user32.SetProcessDPIAware
    except (AttributeError, OSError):
        return None

    set_process_dpi_aware.argtypes = []
    set_process_dpi_aware.restype = wintypes.BOOL
    if set_process_dpi_aware():
        return "system-dpi-aware"

    last_error = ctypes.get_last_error()
    if last_error == _ERROR_ACCESS_DENIED:
        LOGGER.debug("Legacy DPI awareness was already configured before Tk startup.")
        return "already-configured"
    return None
