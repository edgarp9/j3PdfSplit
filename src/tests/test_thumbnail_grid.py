"""Unit tests for thumbnail grid scrolling bindings."""

from __future__ import annotations

import tkinter as tk
import unittest
from types import SimpleNamespace

from pdf_splitter.domain.models import PageVisualState
from pdf_splitter.ui.localization import UiLanguage
from pdf_splitter.ui.thumbnail_grid import PageThumbnailCard
from pdf_splitter.ui.thumbnail_grid import ScrollableThumbnailGrid


def _walk_widgets(widget: tk.Widget):
    yield widget
    for child in widget.winfo_children():
        yield from _walk_widgets(child)


class ScrollableThumbnailGridTests(unittest.TestCase):
    """Verify wheel scrolling stays active over thumbnail cards."""

    def setUp(self) -> None:
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk unavailable: {exc}")
        self.addCleanup(self.root.destroy)
        self.root.withdraw()
        self.grid = ScrollableThumbnailGrid(self.root, thumbnail_size=(120, 160))
        self.grid.pack(fill="both", expand=True)
        self.root.update_idletasks()

    def test_build_cards_binds_mousewheel_to_card_descendants(self) -> None:
        self.grid.build_cards(1, lambda _page_index: None, [PageVisualState.AVAILABLE])

        card = self.grid._cards[0]
        for widget in _walk_widgets(card):
            self.assertTrue(
                widget.bind("<MouseWheel>"),
                f"MouseWheel binding missing for {widget}",
            )
        self.assertTrue(self.grid._canvas.bind("<MouseWheel>"))

    def test_mousewheel_units_support_windows_and_linux_events(self) -> None:
        self.assertEqual(-1, self.grid._mousewheel_units(SimpleNamespace(delta=120, num=0)))
        self.assertEqual(1, self.grid._mousewheel_units(SimpleNamespace(delta=-120, num=0)))
        self.assertEqual(-1, self.grid._mousewheel_units(SimpleNamespace(delta=0, num=4)))
        self.assertEqual(1, self.grid._mousewheel_units(SimpleNamespace(delta=0, num=5)))

    def test_update_selection_marks_selected_card(self) -> None:
        self.grid.build_cards(2, lambda _page_index: None, [PageVisualState.AVAILABLE] * 2)

        self.grid.update_selection({1})

        self.assertEqual("Unsplit · Selected", self.grid._cards[1]._status_label.cget("text"))
        self.assertEqual(
            PageThumbnailCard.SELECTED_BORDER,
            self.grid._cards[1].cget("highlightbackground"),
        )

    def test_set_language_refreshes_existing_cards(self) -> None:
        self.grid.build_cards(1, lambda _page_index: None, [PageVisualState.AVAILABLE])

        self.grid.update_selection({0})
        self.grid.set_language(UiLanguage.KOREAN)

        self.assertEqual("미분할 · 선택됨", self.grid._cards[0]._status_label.cget("text"))
        self.assertEqual("0페이지", self.grid._cards[0]._page_label.cget("text"))


if __name__ == "__main__":
    unittest.main()
