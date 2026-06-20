"""Scrollable thumbnail grid widgets."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable, Collection, Sequence
from tkinter import ttk

from pdf_splitter.domain.models import PageVisualState
from pdf_splitter.ui.localization import DEFAULT_LANGUAGE
from pdf_splitter.ui.localization import UiLanguage
from pdf_splitter.ui.localization import text
from pdf_splitter.ui.scaling import UiScale


class PageThumbnailCard(tk.Frame):
    """Single page thumbnail card with state-aware styling."""

    OUTER_PADDING_X = 8
    OUTER_PADDING_Y = 8
    FOOTER_HEIGHT = 56
    IMAGE_WRAP_PADDING = 20
    PAGE_LABEL_GAP_TOP = 8
    PAGE_LABEL_GAP_BOTTOM = 2
    BORDER_WIDTH = 1
    DEFAULT_HIGHLIGHT_THICKNESS = 2
    SELECTED_HIGHLIGHT_THICKNESS = 3
    SELECTED_BORDER = "#1971c2"

    _STATE_COLORS = {
        PageVisualState.COMPLETED: {
            "background": "#d8f3dc",
            "border": "#2d6a4f",
            "foreground": "#1b4332",
            "status_key": "thumbnail.completed",
        },
        PageVisualState.CURRENT: {
            "background": "#fff3bf",
            "border": "#f08c00",
            "foreground": "#7f5539",
            "status_key": "thumbnail.current",
        },
        PageVisualState.AVAILABLE: {
            "background": "#f1f3f5",
            "border": "#adb5bd",
            "foreground": "#343a40",
            "status_key": "thumbnail.available",
        },
    }

    def __init__(
        self,
        master: tk.Misc,
        page_index: int,
        on_select: Callable[[int], None],
        *,
        state: PageVisualState,
        thumbnail_size: tuple[int, int],
        ui_scale: UiScale | None = None,
        language: UiLanguage = DEFAULT_LANGUAGE,
    ) -> None:
        self._ui_scale = ui_scale or UiScale()
        self._language = language
        self._thumbnail_width, self._thumbnail_height = thumbnail_size
        self._outer_padding_x = self._ui_scale.scale(self.OUTER_PADDING_X, minimum=0)
        self._outer_padding_y = self._ui_scale.scale(self.OUTER_PADDING_Y, minimum=0)
        self._default_highlight_thickness = self._ui_scale.scale(
            self.DEFAULT_HIGHLIGHT_THICKNESS
        )
        self._selected_highlight_thickness = self._ui_scale.scale(
            self.SELECTED_HIGHLIGHT_THICKNESS
        )
        self._card_width, self._card_height = self.card_size_for_thumbnail(
            thumbnail_size,
            self._ui_scale,
        )
        super().__init__(
            master,
            bd=self._ui_scale.scale(self.BORDER_WIDTH),
            relief="solid",
            cursor="hand2",
            highlightthickness=self._default_highlight_thickness,
            padx=self._outer_padding_x,
            pady=self._outer_padding_y,
            width=self._card_width,
            height=self._card_height,
        )
        self.page_index = page_index
        self._on_select = on_select
        self._state = state
        self._selected = False
        self._photo_image: tk.PhotoImage | None = None
        self._message_key: str | None = "thumbnail.loading"
        self._message_values: dict[str, object] = {}
        self.grid_propagate(False)
        self.pack_propagate(False)

        self._image_frame = tk.Frame(
            self, width=self._thumbnail_width, height=self._thumbnail_height
        )
        self._image_frame.pack(fill="x", expand=False)
        self._image_frame.pack_propagate(False)

        self._image_label = tk.Label(
            self._image_frame,
            text=self._text("thumbnail.loading"),
            justify="center",
            anchor="center",
            wraplength=max(
                1,
                self._thumbnail_width - self._ui_scale.scale(self.IMAGE_WRAP_PADDING, minimum=0),
            ),
        )
        self._image_label.pack(fill="both", expand=True)

        self._page_label = tk.Label(
            self,
            text=self._text("thumbnail.page", page_index=page_index),
            font=self._ui_scale.font(10, "bold"),
        )
        self._page_label.pack(
            pady=self._ui_scale.padding(self.PAGE_LABEL_GAP_TOP, self.PAGE_LABEL_GAP_BOTTOM)
        )

        self._status_label = tk.Label(self, text="", font=self._ui_scale.font(9))
        self._status_label.pack()

        self._refresh_style()
        self._bind_click(self)
        self._bind_click(self._image_label)
        self._bind_click(self._page_label)
        self._bind_click(self._status_label)

    def apply_state(self, state: PageVisualState) -> None:
        """Refresh the visual style based on split progress."""
        self._state = state
        self._refresh_style()

    def set_selected(self, selected: bool) -> None:
        """Show whether the page is selected for export."""
        self._selected = selected
        self._refresh_style()

    def set_language(self, language: UiLanguage) -> None:
        """Refresh display text for a new UI language."""
        self._language = language
        self._page_label.configure(text=self._text("thumbnail.page", page_index=self.page_index))
        if self._photo_image is None and self._message_key is not None:
            self._image_label.configure(
                text=self._text(self._message_key, **self._message_values)
            )
        self._refresh_style()

    def _refresh_style(self) -> None:
        colors = self._STATE_COLORS[self._state]
        border_color = self.SELECTED_BORDER if self._selected else colors["border"]
        status_text = self._text(str(colors["status_key"]))
        if self._selected:
            status_text = f"{status_text} · {self._text('thumbnail.selected_suffix')}"
        self.configure(
            background=colors["background"],
            highlightbackground=border_color,
            highlightcolor=border_color,
            highlightthickness=(
                self._selected_highlight_thickness
                if self._selected
                else self._default_highlight_thickness
            ),
        )
        self._image_frame.configure(background=colors["background"])
        self._image_label.configure(
            background=colors["background"],
            foreground=colors["foreground"],
        )
        self._page_label.configure(
            background=colors["background"],
            foreground=colors["foreground"],
        )
        self._status_label.configure(
            background=colors["background"],
            foreground=border_color if self._selected else colors["foreground"],
            text=status_text,
        )

    def set_thumbnail(self, photo_image: tk.PhotoImage) -> None:
        """Display a rendered thumbnail on the card."""
        self._photo_image = photo_image
        self._message_key = None
        self._message_values = {}
        self._image_label.configure(image=photo_image, text="")

    def set_message(self, message: str) -> None:
        """Display a short message instead of an image."""
        self._photo_image = None
        self._message_key = None
        self._message_values = {}
        self._image_label.configure(image="", text=message)

    def set_message_key(self, message_key: str, **message_values: object) -> None:
        """Display a localized message instead of an image."""
        self._photo_image = None
        self._message_key = message_key
        self._message_values = message_values
        self._image_label.configure(
            image="",
            text=self._text(message_key, **message_values),
        )

    def _text(self, key: str, **values: object) -> str:
        return text(self._language, key, **values)

    def _bind_click(self, widget: tk.Widget) -> None:
        widget.bind("<Button-1>", self._handle_click)

    def _handle_click(self, _event: tk.Event[tk.Misc]) -> None:
        self._on_select(self.page_index)

    @classmethod
    def card_size_for_thumbnail(
        cls,
        thumbnail_size: tuple[int, int],
        ui_scale: UiScale,
    ) -> tuple[int, int]:
        """Return the pixel size of one card for a given thumbnail size."""
        outer_padding_x = ui_scale.scale(cls.OUTER_PADDING_X, minimum=0)
        outer_padding_y = ui_scale.scale(cls.OUTER_PADDING_Y, minimum=0)
        footer_height = ui_scale.scale(cls.FOOTER_HEIGHT, minimum=0)
        return (
            thumbnail_size[0] + (outer_padding_x * 2),
            thumbnail_size[1] + footer_height + (outer_padding_y * 2),
        )


class ScrollableThumbnailGrid(ttk.Frame):
    """Canvas-based scrollable thumbnail grid."""

    CARD_GAP_X = 18
    CARD_GAP_Y = 16
    CANVAS_PADDING = 8
    MOUSEWHEEL_SEQUENCES = ("<MouseWheel>", "<Button-4>", "<Button-5>")
    VISIBLE_PAGES_CALLBACK_INTERVAL_MS = 16

    def __init__(
        self,
        master: tk.Misc,
        thumbnail_size: tuple[int, int],
        *,
        ui_scale: UiScale | None = None,
        language: UiLanguage = DEFAULT_LANGUAGE,
    ) -> None:
        super().__init__(master)
        self._ui_scale = ui_scale or UiScale()
        self._language = language
        self._thumbnail_size = thumbnail_size
        self._card_width, self._card_height = PageThumbnailCard.card_size_for_thumbnail(
            thumbnail_size,
            self._ui_scale,
        )
        self._card_gap_x = self._ui_scale.scale(self.CARD_GAP_X, minimum=0)
        self._card_gap_y = self._ui_scale.scale(self.CARD_GAP_Y, minimum=0)
        self._canvas_padding = self._ui_scale.scale(self.CANVAS_PADDING, minimum=0)
        self._cards: list[PageThumbnailCard] = []
        self._card_windows: list[int] = []
        self._current_columns = 0
        self._visible_pages_callback: Callable[[list[int]], None] | None = None
        self._visible_pages_after_id: str | None = None
        self._last_visible_pages: tuple[int, ...] = ()
        self._canvas = tk.Canvas(self, background="#ffffff", highlightthickness=0)
        self._scrollbar = ttk.Scrollbar(self, orient="vertical", command=self._on_scrollbar)

        self._canvas.configure(yscrollcommand=self._on_canvas_scroll)
        self._canvas.pack(side="left", fill="both", expand=True)
        self._scrollbar.pack(side="right", fill="y")

        self._bind_mousewheel_tree(self._canvas)
        self._canvas.bind("<Configure>", self._on_canvas_configure)

    def set_thumbnail_size(self, thumbnail_size: tuple[int, int]) -> None:
        """Update the card size used for the next grid build."""
        self._thumbnail_size = thumbnail_size
        self._card_width, self._card_height = PageThumbnailCard.card_size_for_thumbnail(
            thumbnail_size,
            self._ui_scale,
        )
        self._current_columns = 0

    def set_language(self, language: UiLanguage) -> None:
        """Refresh existing cards and future card creation for a UI language."""
        self._language = language
        for card in self._cards:
            card.set_language(language)

    def set_ui_scale(self, ui_scale: UiScale, thumbnail_size: tuple[int, int]) -> None:
        """Update DPI-dependent grid metrics used by future layout passes."""
        self._ui_scale = ui_scale
        self._card_gap_x = self._ui_scale.scale(self.CARD_GAP_X, minimum=0)
        self._card_gap_y = self._ui_scale.scale(self.CARD_GAP_Y, minimum=0)
        self._canvas_padding = self._ui_scale.scale(self.CANVAS_PADDING, minimum=0)
        self.set_thumbnail_size(thumbnail_size)
        self._reflow(force=True)

    def set_visible_pages_callback(self, callback: Callable[[list[int]], None] | None) -> None:
        """Register a callback for viewport-driven thumbnail prioritization."""
        self._visible_pages_callback = callback
        self.notify_visible_pages_changed()

    def notify_visible_pages_changed(self) -> None:
        """Request one deferred visible-page callback."""
        self._schedule_visible_pages_callback()

    def visible_page_indexes(self, overscan_rows: int = 1) -> list[int]:
        """Return contiguous page indexes around the current viewport."""
        if not self._cards:
            return []

        columns = max(1, self._current_columns or 1)
        row_span = self._card_height + self._card_gap_y
        viewport_top = max(self._canvas.canvasy(0) - self._canvas_padding, 0)
        viewport_height = self._canvas.winfo_height() or self.winfo_height() or row_span
        viewport_bottom = max(
            self._canvas.canvasy(viewport_height) - self._canvas_padding,
            viewport_top,
        )
        start_row = max(0, int(viewport_top // row_span) - overscan_rows)
        end_row = max(0, int(viewport_bottom // row_span) + overscan_rows)
        start_index = start_row * columns
        end_index = min(len(self._cards), (end_row + 1) * columns)
        return list(range(start_index, end_index))

    def clear(self) -> None:
        """Remove all cards from the grid."""
        for card_window in self._card_windows:
            self._canvas.delete(card_window)
        self._card_windows.clear()
        for card in self._cards:
            card.destroy()
        self._cards.clear()
        self._current_columns = 0
        self._last_visible_pages = ()
        self._canvas.configure(scrollregion=(0, 0, 0, 0))
        self._canvas.yview_moveto(0)
        self.notify_visible_pages_changed()

    def build_cards(
        self,
        total_pages: int,
        on_select: Callable[[int], None],
        states: Sequence[PageVisualState],
    ) -> None:
        """Create placeholder cards for all pages."""
        self.clear()
        for page_index in range(total_pages):
            card = PageThumbnailCard(
                self._canvas,
                page_index=page_index,
                on_select=on_select,
                state=states[page_index],
                thumbnail_size=self._thumbnail_size,
                ui_scale=self._ui_scale,
                language=self._language,
            )
            self._bind_mousewheel_tree(card)
            self._cards.append(card)
            self._card_windows.append(
                self._canvas.create_window((0, 0), window=card, anchor="nw")
            )
        self._reflow(force=True)
        self.notify_visible_pages_changed()

    def update_states(self, states: Sequence[PageVisualState]) -> None:
        """Refresh card styles after a split completes."""
        for card, state in zip(self._cards, states, strict=False):
            card.apply_state(state)

    def update_selection(self, selected_pages: Collection[int]) -> None:
        """Refresh selection highlights for selected-pages export mode."""
        selected_page_set = set(selected_pages)
        for page_index, card in enumerate(self._cards):
            card.set_selected(page_index in selected_page_set)

    def set_thumbnail(self, page_index: int, photo_image: tk.PhotoImage) -> None:
        """Assign the rendered image to one page card."""
        self._cards[page_index].set_thumbnail(photo_image)

    def set_card_message(self, page_index: int, message: str) -> None:
        """Show a placeholder or error message for one card."""
        self._cards[page_index].set_message(message)

    def set_card_message_key(
        self,
        page_index: int,
        message_key: str,
        **message_values: object,
    ) -> None:
        """Show a localized placeholder or error message for one card."""
        self._cards[page_index].set_message_key(message_key, **message_values)

    def _on_canvas_configure(self, event: tk.Event[tk.Misc]) -> None:
        self._reflow(event.width)
        self._schedule_visible_pages_callback()

    def _reflow(self, available_width: int | None = None, *, force: bool = False) -> None:
        width = available_width or self._canvas.winfo_width() or self.winfo_width()
        padded_width = max(1, width - (self._canvas_padding * 2))
        columns = max(1, padded_width // (self._card_width + self._card_gap_x))
        if not force and columns == self._current_columns:
            return

        self._current_columns = columns
        row_span = self._card_height + self._card_gap_y
        column_span = self._card_width + self._card_gap_x
        for index, card_window in enumerate(self._card_windows):
            row = index // columns
            column = index % columns
            x_position = self._canvas_padding + (column * column_span)
            y_position = self._canvas_padding + (row * row_span)
            self._canvas.coords(card_window, x_position, y_position)

        total_rows = (len(self._cards) + columns - 1) // columns if self._cards else 0
        total_width = (
            (self._canvas_padding * 2)
            + (columns * self._card_width)
            + (max(0, columns - 1) * self._card_gap_x)
        )
        total_height = (
            (self._canvas_padding * 2)
            + (total_rows * self._card_height)
            + (max(0, total_rows - 1) * self._card_gap_y)
        )
        self._canvas.configure(
            scrollregion=(
                0,
                0,
                max(width, total_width),
                total_height,
            )
        )
        self._schedule_visible_pages_callback()

    def _bind_mousewheel_tree(self, widget: tk.Widget) -> None:
        self._bind_mousewheel_target(widget)
        for child in widget.winfo_children():
            self._bind_mousewheel_tree(child)

    def _bind_mousewheel_target(self, widget: tk.Widget) -> None:
        for sequence in self.MOUSEWHEEL_SEQUENCES:
            widget.bind(sequence, self._on_mousewheel, add="+")

    @staticmethod
    def _mousewheel_units(event: tk.Event[tk.Misc]) -> int:
        button_number = getattr(event, "num", None)
        if button_number == 4:
            return -1
        if button_number == 5:
            return 1

        delta = getattr(event, "delta", 0)
        if delta == 0:
            return 0
        steps = (abs(delta) // 120) or 1
        return -steps if delta > 0 else steps

    def _on_mousewheel(self, event: tk.Event[tk.Misc]) -> str | None:
        scroll_units = self._mousewheel_units(event)
        if scroll_units == 0:
            return None
        self._canvas.yview_scroll(scroll_units, "units")
        self._schedule_visible_pages_callback()
        return "break"

    def _on_scrollbar(self, *args: str) -> None:
        self._canvas.yview(*args)
        self._schedule_visible_pages_callback()

    def _on_canvas_scroll(self, first: str, last: str) -> None:
        self._scrollbar.set(first, last)
        self._schedule_visible_pages_callback()

    def _schedule_visible_pages_callback(self) -> None:
        if self._visible_pages_callback is None:
            return

        if self._visible_pages_after_id is not None:
            return
        self._visible_pages_after_id = self.after(
            self.VISIBLE_PAGES_CALLBACK_INTERVAL_MS,
            self._emit_visible_pages,
        )

    def _emit_visible_pages(self) -> None:
        self._visible_pages_after_id = None
        if self._visible_pages_callback is None:
            return
        visible_pages = tuple(self.visible_page_indexes())
        if visible_pages == self._last_visible_pages:
            return
        self._last_visible_pages = visible_pages
        self._visible_pages_callback(list(visible_pages))
