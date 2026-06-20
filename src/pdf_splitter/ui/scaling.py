"""Shared UI scaling helpers for DPI-aware Tk layouts."""

from __future__ import annotations

import tkinter as tk
import ctypes
import os
from dataclasses import dataclass
from tkinter import font as tkfont
from typing import Callable

BASELINE_DPI = 96.0
PREFERRED_WINDOWS_FONT_FAMILY = "Malgun Gothic"
NAMED_FONT_NAMES = (
    "TkDefaultFont",
    "TkTextFont",
    "TkFixedFont",
    "TkMenuFont",
    "TkHeadingFont",
    "TkCaptionFont",
    "TkSmallCaptionFont",
    "TkIconFont",
    "TkTooltipFont",
)


@dataclass(frozen=True, slots=True)
class UiScale:
    """Convert baseline pixel constants to the active Tk DPI scale."""

    factor: float = 1.0
    font_family: str = PREFERRED_WINDOWS_FONT_FAMILY

    @classmethod
    def from_root(
        cls,
        root: tk.Misc,
        *,
        font_family: str = PREFERRED_WINDOWS_FONT_FAMILY,
    ) -> UiScale:
        """Create a scale helper using the current Tk root DPI."""
        pixels_per_inch = get_current_dpi(root)
        factor = pixels_per_inch / BASELINE_DPI if pixels_per_inch > 0 else 1.0
        return cls(factor=factor, font_family=font_family)

    def scale(self, value: int | float, *, minimum: int | None = 1) -> int:
        """Scale one baseline pixel value and round it to an integer."""
        if value == 0:
            return 0

        scaled_value = round(value * self.factor)
        if minimum is None:
            return scaled_value
        return max(minimum, scaled_value)

    def padding(self, *values: int) -> tuple[int, ...]:
        """Scale Tk padding tuples while keeping zero values untouched."""
        return tuple(self.scale(value, minimum=0) for value in values)

    def size(self, width: int, height: int) -> tuple[int, int]:
        """Scale a width/height pair."""
        return (
            self.scale(width),
            self.scale(height),
        )

    def geometry(self, width: int, height: int) -> str:
        """Return a Tk geometry string using scaled pixels."""
        scaled_width, scaled_height = self.size(width, height)
        return f"{scaled_width}x{scaled_height}"

    def font(self, point_size: int, *options: str) -> tuple[object, ...]:
        """Return a Tk font tuple with the configured family."""
        return (self.font_family, point_size, *options)


def configure_default_tk_fonts(
    root: tk.Misc,
    *,
    preferred_family: str = PREFERRED_WINDOWS_FONT_FAMILY,
) -> str:
    """Apply one family to Tk's named fonts and return the family in use."""
    font_family = _resolve_font_family(root, preferred_family)
    for font_name in NAMED_FONT_NAMES:
        try:
            named_font = tkfont.nametofont(font_name, root=root)
        except tk.TclError:
            continue
        named_font.configure(family=font_family)
    return font_family


def _resolve_font_family(root: tk.Misc, preferred_family: str) -> str:
    default_family = str(tkfont.nametofont("TkDefaultFont", root=root).cget("family"))
    try:
        available_families = set(tkfont.families(root))
    except tk.TclError:
        return preferred_family
    return preferred_family if preferred_family in available_families else default_family


def _get_toplevel_frame_hwnd(root: tk.Misc) -> int:
    for method_name in ("frame", "wm_frame"):
        frame_method = getattr(root, method_name, None)
        if not callable(frame_method):
            continue
        try:
            hwnd = int(str(frame_method()), 0)
        except (tk.TclError, TypeError, ValueError):
            hwnd = 0
        if hwnd > 0:
            return hwnd

    try:
        hwnd = int(root.winfo_id())
    except (tk.TclError, TypeError, ValueError):
        return 0
    return max(hwnd, 0)


def get_current_dpi(root: tk.Misc) -> float:
    if os.name == "nt":
        windll = getattr(ctypes, "windll", None)
        user32 = getattr(windll, "user32", None) if windll is not None else None
        if user32 is not None:
            get_dpi_for_window = getattr(user32, "GetDpiForWindow", None)
            if callable(get_dpi_for_window):
                try:
                    hwnd = _get_toplevel_frame_hwnd(root)
                    if hwnd > 0:
                        dpi = float(get_dpi_for_window(hwnd))
                        if dpi > 0:
                            return dpi
                except (OSError, tk.TclError, TypeError, ValueError):
                    pass

            get_dpi_for_system = getattr(user32, "GetDpiForSystem", None)
            if callable(get_dpi_for_system):
                try:
                    dpi = float(get_dpi_for_system())
                    if dpi > 0:
                        return dpi
                except (OSError, TypeError, ValueError):
                    pass

    try:
        dpi = float(root.winfo_fpixels("1i"))
        if dpi > 0:
            return dpi
    except (tk.TclError, TypeError, ValueError):
        return BASELINE_DPI
    return BASELINE_DPI


def configure_tk_dpi(root: tk.Misc) -> UiScale:
    ui_scale = UiScale.from_root(root)
    _apply_tk_scaling(root, ui_scale)
    return ui_scale


def sync_tk_dpi(root: tk.Misc) -> UiScale | None:
    ui_scale = UiScale.from_root(root)
    previous = getattr(root, "_pdfsplit_ui_scale", None)
    if isinstance(previous, UiScale) and abs(previous.factor - ui_scale.factor) < 0.005:
        return None
    _apply_tk_scaling(root, ui_scale)
    return ui_scale


def _apply_tk_scaling(root: tk.Misc, ui_scale: UiScale) -> None:
    try:
        root.tk.call("tk", "scaling", (BASELINE_DPI * ui_scale.factor) / 72.0)
    except tk.TclError:
        pass
    setattr(root, "_pdfsplit_ui_scale", ui_scale)


class DpiSyncController:
    def __init__(
        self,
        root: tk.Misc,
        on_scale_changed: Callable[[UiScale], None],
        *,
        debounce_ms: int = 150,
    ) -> None:
        self._root = root
        self._on_scale_changed = on_scale_changed
        self._debounce_ms = debounce_ms
        self._after_id: str | None = None

    def bind(self) -> None:
        try:
            self._root.bind("<Configure>", self._on_root_configure, add="+")
        except tk.TclError:
            pass

    def close(self) -> None:
        if self._after_id is None:
            return
        after_id = self._after_id
        self._after_id = None
        try:
            self._root.after_cancel(after_id)
        except tk.TclError:
            pass

    def _on_root_configure(self, event: tk.Event) -> None:
        if getattr(event, "widget", None) is not self._root:
            return
        self.close()
        try:
            self._after_id = self._root.after(
                self._debounce_ms,
                self._run_deferred_sync,
            )
        except tk.TclError:
            self._after_id = None

    def _run_deferred_sync(self) -> None:
        self._after_id = None
        try:
            if not self._root.winfo_exists():
                return
        except tk.TclError:
            return
        ui_scale = sync_tk_dpi(self._root)
        if ui_scale is not None:
            self._on_scale_changed(ui_scale)
