"""Unit tests for thumbnail scale helpers in the main window."""

import tkinter as tk
import unittest
from pathlib import Path
from tkinter import ttk
from types import SimpleNamespace
from unittest.mock import patch

from pdf_splitter.app.controller import SequentialPdfSplitController
from pdf_splitter.app_info import APP_NAME, AUTHOR_URL, app_version
from pdf_splitter.infra.pdf_service import PdfProcessingService
from pdf_splitter.ui.main_window import APP_TITLE, PdfSplitApplication
from pdf_splitter.ui.localization import DEFAULT_LANGUAGE
from pdf_splitter.ui.localization import UiLanguage
from pdf_splitter.ui.scaling import UiScale


def _walk_widgets(widget: tk.Widget):
    yield widget
    for child in widget.winfo_children():
        yield from _walk_widgets(child)


class ThumbnailScaleHelperTests(unittest.TestCase):
    """Verify thumbnail scale parsing and size conversion rules."""

    def test_default_thumbnail_scale_percent_is_70(self) -> None:
        self.assertEqual(70, PdfSplitApplication.DEFAULT_THUMBNAIL_SCALE_PERCENT)

    def test_default_language_is_english(self) -> None:
        self.assertEqual(UiLanguage.ENGLISH, DEFAULT_LANGUAGE)

    def test_window_title_uses_project_name(self) -> None:
        self.assertEqual("j3PdfSplit", APP_TITLE)
        self.assertEqual(APP_NAME, APP_TITLE)

    def test_mode_values_are_stable_internal_keys(self) -> None:
        self.assertEqual("sequential_split", PdfSplitApplication.SEQUENTIAL_SPLIT_MODE)
        self.assertEqual(
            "selected_pages_export",
            PdfSplitApplication.SELECTED_PAGES_EXPORT_MODE,
        )

    def test_mode_labels_are_localized(self) -> None:
        self.assertEqual(
            "Sequential split",
            PdfSplitApplication._mode_label_for_language(
                UiLanguage.ENGLISH,
                PdfSplitApplication.SEQUENTIAL_SPLIT_MODE,
            ),
        )
        self.assertEqual(
            "순차 분할",
            PdfSplitApplication._mode_label_for_language(
                UiLanguage.KOREAN,
                PdfSplitApplication.SEQUENTIAL_SPLIT_MODE,
            ),
        )

    def test_parse_thumbnail_scale_accepts_percent_suffix(self) -> None:
        self.assertEqual(150, PdfSplitApplication._parse_thumbnail_scale_percent("150%"))

    def test_parse_thumbnail_scale_rejects_invalid_values(self) -> None:
        self.assertIsNone(PdfSplitApplication._parse_thumbnail_scale_percent("9"))
        self.assertIsNone(PdfSplitApplication._parse_thumbnail_scale_percent("201"))
        self.assertIsNone(PdfSplitApplication._parse_thumbnail_scale_percent("abc"))

    def test_thumbnail_size_for_scale_uses_base_size(self) -> None:
        self.assertEqual((30, 40), PdfSplitApplication._thumbnail_size_for_scale(10))
        self.assertEqual((600, 800), PdfSplitApplication._thumbnail_size_for_scale(200))

    def test_current_thumbnail_size_applies_ui_scale(self) -> None:
        application = PdfSplitApplication.__new__(PdfSplitApplication)
        application._thumbnail_scale_percent = 70
        application._ui_scale = UiScale(factor=1.5, font_family="Malgun Gothic")

        self.assertEqual((315, 420), application._current_thumbnail_size())

    def test_thumbnail_request_order_prioritizes_visible_pages(self) -> None:
        order = PdfSplitApplication._thumbnail_request_order(10, [4, 5, 6])

        self.assertEqual([4, 5, 6, 7, 3], order[:5])
        self.assertEqual(set(range(10)), set(order))

    def test_thumbnail_request_order_ignores_duplicates_and_out_of_range(self) -> None:
        order = PdfSplitApplication._thumbnail_request_order(6, [3, 3, -1, 9, 4])

        self.assertEqual([3, 4, 5, 2, 1, 0], order)

    def test_thumbnail_window_pages_defaults_to_first_chunk_without_visible_pages(self) -> None:
        pages = PdfSplitApplication._thumbnail_window_pages(
            500,
            [],
            viewport_multiplier=1,
            minimum_pages=18,
        )

        self.assertEqual(set(range(18)), pages)

    def test_thumbnail_window_pages_expands_around_visible_range(self) -> None:
        pages = PdfSplitApplication._thumbnail_window_pages(
            500,
            [200, 201, 202, 203],
            viewport_multiplier=1,
            minimum_pages=18,
        )

        self.assertEqual(set(range(191, 213)), pages)

    def test_thumbnail_window_pages_clamps_near_document_end(self) -> None:
        pages = PdfSplitApplication._thumbnail_window_pages(
            210,
            [205, 206, 207, 208, 209],
            viewport_multiplier=3,
            minimum_pages=72,
        )

        self.assertEqual(set(range(169, 210)), pages)

    def test_format_page_ranges_collapses_consecutive_pages(self) -> None:
        self.assertEqual("1~3, 5, 7~8", PdfSplitApplication._format_page_ranges({8, 1, 2, 3, 5, 7}))

    def test_format_page_ranges_returns_dash_for_empty_selection(self) -> None:
        self.assertEqual("-", PdfSplitApplication._format_page_ranges(set()))

    def test_first_pdf_path_uses_first_pdf_case_insensitively(self) -> None:
        self.assertEqual(
            Path("C:/tmp/source.PDF"),
            PdfSplitApplication._first_pdf_path(
                (
                    Path("C:/tmp/readme.txt"),
                    Path("C:/tmp/source.PDF"),
                    Path("C:/tmp/other.pdf"),
                )
            ),
        )

    def test_first_pdf_path_returns_none_without_pdf(self) -> None:
        self.assertIsNone(PdfSplitApplication._first_pdf_path((Path("C:/tmp/readme.txt"),)))


class MainWindowMenuTests(unittest.TestCase):
    """Verify menu and About dialog behavior."""

    def setUp(self) -> None:
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk unavailable: {exc}")
        self.root.withdraw()
        self.application = PdfSplitApplication(
            self.root,
            SequentialPdfSplitController(PdfProcessingService()),
        )
        self.application.pack(fill="both", expand=True)
        self.addCleanup(self.application.on_close)

    def test_menu_contains_language_and_about_items(self) -> None:
        self.assertEqual("File", self.application._menu_bar.entrycget(0, "label"))
        self.assertEqual("Open PDF", self.application._file_menu.entrycget(0, "label"))
        self.assertEqual("Choose output folder", self.application._file_menu.entrycget(1, "label"))
        self.assertEqual("Export", self.application._file_menu.entrycget(2, "label"))
        self.assertEqual("Language", self.application._menu_bar.entrycget(1, "label"))
        self.assertEqual("English", self.application._language_menu.entrycget(0, "label"))
        self.assertEqual("한국어", self.application._language_menu.entrycget(1, "label"))
        self.assertEqual("Help", self.application._menu_bar.entrycget(2, "label"))
        self.assertEqual("About", self.application._help_menu.entrycget(0, "label"))

        self.application._language_var.set("한국어")
        self.application._on_language_changed()

        self.assertEqual("파일", self.application._menu_bar.entrycget(0, "label"))
        self.assertEqual("PDF 열기", self.application._file_menu.entrycget(0, "label"))
        self.assertEqual("저장 폴더 선택", self.application._file_menu.entrycget(1, "label"))
        self.assertEqual("내보내기", self.application._file_menu.entrycget(2, "label"))
        self.assertEqual("언어", self.application._menu_bar.entrycget(1, "label"))
        self.assertEqual("도움말", self.application._menu_bar.entrycget(2, "label"))
        self.assertEqual("정보", self.application._help_menu.entrycget(0, "label"))

    def test_language_selector_is_not_in_header(self) -> None:
        comboboxes = [
            widget for widget in _walk_widgets(self.application) if isinstance(widget, ttk.Combobox)
        ]

        self.assertEqual([self.application._mode_combobox], comboboxes)

    def test_app_title_label_is_not_shown_in_header(self) -> None:
        header = self.application.winfo_children()[0]
        labels = [
            widget
            for widget in _walk_widgets(header)
            if isinstance(widget, ttk.Label)
        ]

        self.assertNotIn("PDF Splitter", {label.cget("text") for label in labels})

    def test_guide_labels_are_not_shown_above_thumbnails(self) -> None:
        label_texts = {
            widget.cget("text")
            for widget in _walk_widgets(self.application)
            if isinstance(widget, ttk.Label)
        }

        self.assertNotIn("Green: saved / Yellow: next start / Gray: remaining pages", label_texts)
        self.assertNotIn(
            "In selected-pages export mode, click thumbnails to select or clear pages, "
            "then click Export.",
            label_texts,
        )

        self.application._language_var.set("한국어")
        self.application._on_language_changed()
        label_texts = {
            widget.cget("text")
            for widget in _walk_widgets(self.application)
            if isinstance(widget, ttk.Label)
        }

        self.assertNotIn("녹색: 저장 완료 / 노랑: 다음 시작 / 회색: 아직 남은 페이지", label_texts)
        self.assertNotIn(
            "선택 페이지 내보내기 모드에서는 썸네일 클릭으로 선택/해제한 뒤 "
            "`내보내기`를 눌러 저장합니다.",
            label_texts,
        )

    def test_selected_pages_export_is_default_mode(self) -> None:
        self.assertEqual(
            PdfSplitApplication.SELECTED_PAGES_EXPORT_MODE,
            self.application._mode,
        )
        self.assertEqual("Selected pages export", self.application._mode_var.get())

    def test_top_action_buttons_are_ordered_before_mode_controls(self) -> None:
        header_actions = self.application._open_button.nametowidget(
            self.application._open_button.winfo_parent()
        )

        self.assertEqual(
            [
                self.application._open_button,
                self.application._output_button,
                self.application._export_button,
            ],
            header_actions.winfo_children()[:3],
        )

    def test_top_header_groups_actions_above_workflow_and_view_controls(self) -> None:
        action_row = self.application._open_button.nametowidget(
            self.application._open_button.winfo_parent()
        )
        mode_frame = self.application._mode_combobox.nametowidget(
            self.application._mode_combobox.winfo_parent()
        )
        scale_frame = self.application._thumbnail_size_label.nametowidget(
            self.application._thumbnail_size_label.winfo_parent()
        )

        self.assertEqual(0, int(action_row.grid_info()["row"]))
        self.assertEqual(0, int(action_row.grid_info()["column"]))
        self.assertEqual(2, int(action_row.grid_info()["columnspan"]))
        self.assertEqual(1, int(mode_frame.grid_info()["row"]))
        self.assertEqual(0, int(mode_frame.grid_info()["column"]))
        self.assertEqual(1, int(scale_frame.grid_info()["row"]))
        self.assertEqual(1, int(scale_frame.grid_info()["column"]))

    def test_thumbnail_scale_spinbox_keeps_value_clear_of_spinner_arrows(self) -> None:
        spinbox_width = int(self.application._thumbnail_scale_spinbox.cget("width"))
        max_scale_text_length = len(str(PdfSplitApplication.MAX_THUMBNAIL_SCALE_PERCENT))

        self.assertEqual(PdfSplitApplication.THUMBNAIL_SCALE_SPINBOX_WIDTH, spinbox_width)
        self.assertGreaterEqual(spinbox_width, max_scale_text_length + 4)
        self.assertEqual("center", self.application._thumbnail_scale_spinbox.cget("justify"))

    def test_open_pdf_button_is_enabled_initially(self) -> None:
        self.assertEqual("normal", str(self.application._open_button.cget("state")))

    def test_file_menu_open_is_enabled_and_other_actions_are_disabled_initially(self) -> None:
        self.assertEqual("normal", self.application._file_menu.entrycget(0, "state"))
        self.assertEqual("disabled", self.application._file_menu.entrycget(1, "state"))
        self.assertEqual("disabled", self.application._file_menu.entrycget(2, "state"))

    def test_open_pdf_dialog_uses_main_window_parent(self) -> None:
        with patch(
            "pdf_splitter.ui.main_window.filedialog.askopenfilename",
            return_value="",
        ) as askopenfilename_mock:
            self.application._on_open_pdf()

        askopenfilename_mock.assert_called_once()
        self.assertIs(self.root, askopenfilename_mock.call_args.kwargs["parent"])

    def test_file_menu_output_dir_uses_output_dir_action(self) -> None:
        self.application._controller = SimpleNamespace(
            snapshot=lambda: SimpleNamespace(
                source_path=Path("C:/tmp/source.pdf"),
                output_dir=Path("C:/tmp"),
            )
        )
        self.application._set_buttons_state(True)

        with patch(
            "pdf_splitter.ui.main_window.filedialog.askdirectory",
            return_value="",
        ) as askdirectory_mock:
            self.application._file_menu.invoke(1)

        askdirectory_mock.assert_called_once()
        self.assertIs(self.root, askdirectory_mock.call_args.kwargs["parent"])

    def test_file_menu_open_uses_open_pdf_action(self) -> None:
        with patch(
            "pdf_splitter.ui.main_window.filedialog.askopenfilename",
            return_value="",
        ) as askopenfilename_mock:
            self.application._file_menu.invoke(0)

        askopenfilename_mock.assert_called_once()
        self.assertIs(self.root, askopenfilename_mock.call_args.kwargs["parent"])

    def test_pdf_file_drop_uses_open_pdf_path(self) -> None:
        event = SimpleNamespace(data="{C:/tmp/source file.pdf}")

        with patch.object(self.application, "_open_pdf_path") as open_pdf_path_mock:
            result = self.application._on_file_dropped(event)

        self.assertEqual(PdfSplitApplication.DROP_ACTION_COPY, result)
        open_pdf_path_mock.assert_called_once_with(Path("C:/tmp/source file.pdf"))

    def test_non_pdf_file_drop_shows_warning(self) -> None:
        event = SimpleNamespace(data="{C:/tmp/readme.txt}")

        with (
            patch.object(self.application, "_open_pdf_path") as open_pdf_path_mock,
            patch("pdf_splitter.ui.main_window.messagebox.showwarning") as showwarning_mock,
        ):
            result = self.application._on_file_dropped(event)

        self.assertEqual(PdfSplitApplication.DROP_ACTION_COPY, result)
        open_pdf_path_mock.assert_not_called()
        showwarning_mock.assert_called_once_with("PDF Splitter", "Drop a PDF file.")
        self.assertEqual("Drop a PDF file.", self.application._status_var.get())

    def test_about_dialog_shows_version_and_author_link(self) -> None:
        dialog = self.application._create_about_dialog()
        self.addCleanup(dialog.destroy)

        label_texts = {
            widget.cget("text")
            for widget in _walk_widgets(dialog)
            if isinstance(widget, ttk.Label)
        }

        self.assertEqual("About j3PdfSplit", dialog.title())
        self.assertIn(APP_NAME, label_texts)
        self.assertIn(f"Version {app_version()}", label_texts)
        self.assertIn(AUTHOR_URL, label_texts)

    def test_about_link_opens_author_url(self) -> None:
        with patch("pdf_splitter.ui.main_window.open_url", return_value=True) as open_url_mock:
            self.application._on_about_link_clicked(None)

        open_url_mock.assert_called_once_with(AUTHOR_URL)


if __name__ == "__main__":
    unittest.main()
