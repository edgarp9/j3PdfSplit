"""Main Tkinter window for PDF splitting workflows."""

from __future__ import annotations

import gc
import logging
import queue
import tkinter as tk
from collections.abc import Callable, Iterator
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from PIL import ImageTk

from pdf_splitter.app_info import APP_NAME, AUTHOR_URL, app_version
from pdf_splitter.app.controller import (
    ExportedPages,
    SavedSegment,
    SelectedPagesPreview,
    SequentialPdfSplitController,
    SplitPreview,
)
from pdf_splitter.domain.models import DocumentCompleteError
from pdf_splitter.domain.models import DocumentNotLoadedError
from pdf_splitter.domain.models import PageSelectionError
from pdf_splitter.domain.models import SessionSnapshot
from pdf_splitter.domain.models import SplitSelectionError
from pdf_splitter.infra.pdf_service import (
    PdfOpenError,
    PdfProcessingError,
    PdfSaveError,
    PdfThumbnailError,
)
from pdf_splitter.infra.browser import open_url
from pdf_splitter.ui.localization import DEFAULT_LANGUAGE
from pdf_splitter.ui.localization import UiLanguage
from pdf_splitter.ui.localization import language_from_label
from pdf_splitter.ui.localization import language_label
from pdf_splitter.ui.localization import page_count_text
from pdf_splitter.ui.localization import supported_languages
from pdf_splitter.ui.localization import text
from pdf_splitter.ui.scaling import DpiSyncController, UiScale
from pdf_splitter.ui.thumbnail_grid import ScrollableThumbnailGrid

APP_TITLE = APP_NAME
LOGGER = logging.getLogger(__name__)


class PdfSplitApplication(ttk.Frame):
    """Tkinter application frame."""

    SEQUENTIAL_SPLIT_MODE = "sequential_split"
    SELECTED_PAGES_EXPORT_MODE = "selected_pages_export"
    POLL_INTERVAL_MS = 16
    MAX_QUEUE_EVENTS_PER_POLL = 12
    BASE_THUMBNAIL_SIZE = (300, 400)
    MIN_THUMBNAIL_SCALE_PERCENT = 10
    MAX_THUMBNAIL_SCALE_PERCENT = 200
    DEFAULT_THUMBNAIL_SCALE_PERCENT = 70
    THUMBNAIL_SCALE_SPINBOX_WIDTH = 7
    THUMBNAIL_PARALLELISM = 1
    THUMBNAIL_REQUEST_VIEWPORT_MULTIPLIER = 1
    THUMBNAIL_CACHE_VIEWPORT_MULTIPLIER = 3
    MIN_REQUEST_PAGES = 18
    MIN_CACHE_PAGES = 72
    THUMBNAIL_LOADING_MESSAGE_KEY = "thumbnail.loading"
    THUMBNAIL_RENDER_INTERVAL_MS = 1
    ROOT_PADDING = 12
    SECTION_GAP = 12
    INLINE_GAP = 6
    BUTTON_GAP = 8
    INFO_FRAME_PADDING_Y = 10
    INFO_COLUMN_GAP = 12
    INFO_ROW_GAP = 6
    STATUS_BAR_GAP = 10
    ABOUT_DIALOG_PADDING = 18
    ABOUT_CONTENT_GAP = 12
    ABOUT_FOOTER_GAP = 16
    FILE_MENU_INDEX = 0
    LANGUAGE_MENU_INDEX = 1
    HELP_MENU_INDEX = 2
    FILE_MENU_OPEN_INDEX = 0
    FILE_MENU_OUTPUT_DIR_INDEX = 1
    FILE_MENU_EXPORT_INDEX = 2
    FILE_DROP_TYPE = "DND_Files"
    DROP_ACTION_COPY = "copy"

    def __init__(
        self,
        master: tk.Misc,
        controller: SequentialPdfSplitController,
        *,
        ui_scale: UiScale | None = None,
    ) -> None:
        self._ui_scale = ui_scale or UiScale()
        self._dpi_sync_controller: DpiSyncController | None = None
        super().__init__(master, padding=self._ui_scale.scale(self.ROOT_PADDING, minimum=0))
        self._controller = controller
        self._executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="pdf-split")
        self._worker_queue: queue.Queue[tuple[str, int, dict[str, Any], Future[Any]]] = (
            queue.Queue()
        )
        self._document_token = 0
        self._total_thumbnail_pages = 0
        self._pending_thumbnail_pages: set[int] = set()
        self._inflight_thumbnail_pages: set[int] = set()
        self._visible_thumbnail_pages: tuple[int, ...] = ()
        self._failed_thumbnail_pages: set[int] = set()
        self._photo_images: dict[int, ImageTk.PhotoImage] = {}
        self._thumbnail_render_after_id: str | None = None
        self._busy = False
        self._save_in_progress = False
        self._selected_pages: set[int] = set()
        self._language = DEFAULT_LANGUAGE
        self._mode = self.SELECTED_PAGES_EXPORT_MODE

        self._file_var = tk.StringVar(
            value=self._text(
                "status.pdf_file",
                filename=self._text("status.pdf_file_none"),
            )
        )
        self._output_dir_var = tk.StringVar(
            value=self._text(
                "status.save_folder",
                folder=self._text("status.save_folder_none"),
            )
        )
        self._next_start_var = tk.StringVar(value=self._text("status.next_start_none"))
        self._progress_var = tk.StringVar(value=self._text("status.progress", progress="0/0"))
        self._selected_pages_var = tk.StringVar(value=self._text("status.selected_pages_none"))
        self._status_var = tk.StringVar(value=self._text("status.open_pdf_prompt"))
        self._mode_var = tk.StringVar(value=self._mode_label(self._mode))
        self._language_var = tk.StringVar(value=language_label(self._language))
        self._thumbnail_scale_percent = self.DEFAULT_THUMBNAIL_SCALE_PERCENT
        self._thumbnail_scale_var = tk.StringVar(value=str(self._thumbnail_scale_percent))
        self._file_drop_enabled = False
        self._file_drop_unavailable_logged = False

        self._configure_styles()
        self._build_menu()
        self._build_layout()
        self._enable_file_drop()
        self._apply_language_text(reset_status=False)
        self._refresh_mode_ui()
        self._set_buttons_state(False)
        self.after(self.POLL_INTERVAL_MS, self._poll_worker_queue)

    def on_close(self) -> None:
        """Shut down worker threads and close the window."""
        if self._dpi_sync_controller is not None:
            self._dpi_sync_controller.close()
            self._dpi_sync_controller = None
        if self._thumbnail_render_after_id is not None:
            self.after_cancel(self._thumbnail_render_after_id)
            self._thumbnail_render_after_id = None
        self._executor.shutdown(wait=False, cancel_futures=True)
        self.winfo_toplevel().destroy()

    def _configure_styles(self) -> None:
        style = ttk.Style()
        style.configure("Title.TLabel", font=self._ui_scale.font(16, "bold"))
        style.configure("Info.TLabel", font=self._ui_scale.font(10))
        style.configure(
            "Link.TLabel",
            font=self._ui_scale.font(10, "underline"),
            foreground="#0b66c3",
        )

    def set_dpi_sync_controller(self, controller: DpiSyncController) -> None:
        self._dpi_sync_controller = controller

    def apply_ui_scale(self, ui_scale: UiScale) -> None:
        self._ui_scale = UiScale(
            factor=ui_scale.factor,
            font_family=self._ui_scale.font_family,
        )
        self.configure(padding=self._ui_scale.scale(self.ROOT_PADDING, minimum=0))
        self._configure_styles()
        root = self.winfo_toplevel()
        root.minsize(*self._ui_scale.size(400, 300))
        self._thumbnail_grid.set_ui_scale(
            self._ui_scale,
            self._current_thumbnail_size(),
        )

    def _text(self, key: str, **values: object) -> str:
        return text(self._language, key, **values)

    @staticmethod
    def _language_labels() -> tuple[str, ...]:
        return tuple(language_label(language) for language in supported_languages())

    @classmethod
    def _mode_label_for_language(cls, language: UiLanguage, mode: str) -> str:
        mode_keys = {
            cls.SEQUENTIAL_SPLIT_MODE: "mode.sequential_split",
            cls.SELECTED_PAGES_EXPORT_MODE: "mode.selected_pages_export",
        }
        return text(language, mode_keys[mode])

    @classmethod
    def _mode_from_label(cls, language: UiLanguage, label: str) -> str:
        for mode in (cls.SEQUENTIAL_SPLIT_MODE, cls.SELECTED_PAGES_EXPORT_MODE):
            if label == cls._mode_label_for_language(language, mode):
                return mode
        return cls.SEQUENTIAL_SPLIT_MODE

    def _mode_label(self, mode: str) -> str:
        return self._mode_label_for_language(self._language, mode)

    def _mode_labels(self) -> tuple[str, ...]:
        return (
            self._mode_label(self.SEQUENTIAL_SPLIT_MODE),
            self._mode_label(self.SELECTED_PAGES_EXPORT_MODE),
        )

    def _apply_language_text(self, *, reset_status: bool) -> None:
        """Refresh visible UI text for the current language."""
        self.winfo_toplevel().title(self._text("app.window_title"))
        self._menu_bar.entryconfigure(self.FILE_MENU_INDEX, label=self._text("menu.file"))
        self._menu_bar.entryconfigure(self.LANGUAGE_MENU_INDEX, label=self._text("menu.language"))
        self._menu_bar.entryconfigure(self.HELP_MENU_INDEX, label=self._text("menu.help"))
        self._file_menu.entryconfigure(
            self.FILE_MENU_OPEN_INDEX,
            label=self._text("button.open_pdf"),
        )
        self._file_menu.entryconfigure(
            self.FILE_MENU_OUTPUT_DIR_INDEX,
            label=self._text("button.select_output_dir"),
        )
        self._file_menu.entryconfigure(
            self.FILE_MENU_EXPORT_INDEX,
            label=self._text("button.export"),
        )
        self._help_menu.entryconfigure(0, label=self._text("menu.about"))
        self._language_var.set(language_label(self._language))
        self._mode_text_label.configure(text=self._text("label.mode"))
        self._mode_combobox.configure(values=self._mode_labels())
        self._mode_var.set(self._mode_label(self._mode))
        self._thumbnail_size_label.configure(text=self._text("label.thumbnail_size"))
        self._output_button.configure(text=self._text("button.select_output_dir"))
        self._export_button.configure(text=self._text("button.export"))
        self._open_button.configure(text=self._text("button.open_pdf"))
        self._thumbnail_grid.set_language(self._language)
        snapshot = self._controller.snapshot()
        self._refresh_session(snapshot)
        self._refresh_mode_ui()
        if reset_status:
            self._status_var.set(self._default_status_message(snapshot))

    def _build_menu(self) -> None:
        root = self.winfo_toplevel()
        self._menu_bar = tk.Menu(root, tearoff=False)
        self._file_menu = tk.Menu(self._menu_bar, tearoff=False)
        self._file_menu.add_command(
            label=self._text("button.open_pdf"),
            command=self._on_open_pdf,
        )
        self._file_menu.add_command(
            label=self._text("button.select_output_dir"),
            command=self._on_select_output_dir,
        )
        self._file_menu.add_command(
            label=self._text("button.export"),
            command=self._on_export_selected_pages,
        )
        self._language_menu = tk.Menu(self._menu_bar, tearoff=False)
        for language_name in self._language_labels():
            self._language_menu.add_radiobutton(
                label=language_name,
                value=language_name,
                variable=self._language_var,
                command=self._on_language_changed,
            )
        self._help_menu = tk.Menu(self._menu_bar, tearoff=False)
        self._help_menu.add_command(
            label=self._text("menu.about"),
            command=self._show_about_dialog,
        )
        self._menu_bar.add_cascade(label=self._text("menu.file"), menu=self._file_menu)
        self._menu_bar.add_cascade(
            label=self._text("menu.language"),
            menu=self._language_menu,
        )
        self._menu_bar.add_cascade(label=self._text("menu.help"), menu=self._help_menu)
        root.configure(menu=self._menu_bar)

    def _build_layout(self) -> None:
        header = ttk.Frame(self)
        header.pack(fill="x")
        header.columnconfigure(0, weight=1)
        header.columnconfigure(1, weight=0)

        action_row = ttk.Frame(header)
        action_row.grid(row=0, column=0, columnspan=2, sticky="w")

        self._open_button = ttk.Button(
            action_row,
            text=self._text("button.open_pdf"),
            command=self._on_open_pdf,
        )
        self._open_button.pack(side="left")
        self._output_button = ttk.Button(
            action_row,
            text=self._text("button.select_output_dir"),
            command=self._on_select_output_dir,
        )
        self._output_button.pack(side="left", padx=self._ui_scale.padding(self.BUTTON_GAP, 0))
        self._export_button = ttk.Button(
            action_row,
            text=self._text("button.export"),
            command=self._on_export_selected_pages,
        )
        self._export_button.pack(side="left", padx=self._ui_scale.padding(self.BUTTON_GAP, 0))

        mode_frame = ttk.Frame(header)
        mode_frame.grid(
            row=1,
            column=0,
            sticky="w",
            pady=self._ui_scale.padding(self.SECTION_GAP, 0),
        )
        self._mode_text_label = ttk.Label(
            mode_frame,
            text=self._text("label.mode"),
            style="Info.TLabel",
        )
        self._mode_text_label.pack(side="left")
        self._mode_combobox = ttk.Combobox(
            mode_frame,
            state="readonly",
            width=20,
            textvariable=self._mode_var,
            values=self._mode_labels(),
        )
        self._mode_combobox.pack(side="left", padx=self._ui_scale.padding(self.INLINE_GAP, 0))
        self._mode_combobox.bind("<<ComboboxSelected>>", self._on_mode_changed)

        scale_frame = ttk.Frame(header)
        scale_frame.grid(
            row=1,
            column=1,
            sticky="e",
            padx=self._ui_scale.padding(self.SECTION_GAP, 0),
            pady=self._ui_scale.padding(self.SECTION_GAP, 0),
        )
        self._thumbnail_size_label = ttk.Label(
            scale_frame,
            text=self._text("label.thumbnail_size"),
            style="Info.TLabel",
        )
        self._thumbnail_size_label.pack(side="left")
        self._thumbnail_scale_spinbox = ttk.Spinbox(
            scale_frame,
            from_=self.MIN_THUMBNAIL_SCALE_PERCENT,
            to=self.MAX_THUMBNAIL_SCALE_PERCENT,
            increment=10,
            width=self.THUMBNAIL_SCALE_SPINBOX_WIDTH,
            textvariable=self._thumbnail_scale_var,
            command=self._on_thumbnail_scale_changed,
            justify="center",
        )
        self._thumbnail_scale_spinbox.pack(
            side="left",
            padx=self._ui_scale.padding(self.INLINE_GAP, 0),
        )
        ttk.Label(scale_frame, text="%", style="Info.TLabel").pack(
            side="left",
            padx=self._ui_scale.padding(4, 0),
        )
        self._thumbnail_scale_spinbox.bind("<Return>", self._on_thumbnail_scale_change_event)
        self._thumbnail_scale_spinbox.bind("<FocusOut>", self._on_thumbnail_scale_change_event)

        info_frame = ttk.Frame(
            self,
            padding=self._ui_scale.padding(
                0,
                self.INFO_FRAME_PADDING_Y,
                0,
                self.INFO_FRAME_PADDING_Y,
            ),
        )
        info_frame.pack(fill="x")
        info_frame.columnconfigure(0, weight=1)
        info_frame.columnconfigure(1, weight=1)

        ttk.Label(info_frame, textvariable=self._file_var, style="Info.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(info_frame, textvariable=self._output_dir_var, style="Info.TLabel").grid(
            row=0,
            column=1,
            sticky="w",
            padx=self._ui_scale.padding(self.INFO_COLUMN_GAP, 0),
        )
        ttk.Label(info_frame, textvariable=self._next_start_var, style="Info.TLabel").grid(
            row=1,
            column=0,
            sticky="w",
            pady=self._ui_scale.padding(self.INFO_ROW_GAP, 0),
        )
        ttk.Label(info_frame, textvariable=self._progress_var, style="Info.TLabel").grid(
            row=1,
            column=1,
            sticky="w",
            padx=self._ui_scale.padding(self.INFO_COLUMN_GAP, 0),
            pady=self._ui_scale.padding(self.INFO_ROW_GAP, 0),
        )
        ttk.Label(info_frame, textvariable=self._selected_pages_var, style="Info.TLabel").grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="w",
            pady=self._ui_scale.padding(self.INFO_ROW_GAP, 0),
        )

        self._thumbnail_grid = ScrollableThumbnailGrid(
            self,
            thumbnail_size=self._current_thumbnail_size(),
            ui_scale=self._ui_scale,
            language=self._language,
        )
        self._thumbnail_grid.set_visible_pages_callback(self._on_visible_pages_changed)
        self._thumbnail_grid.pack(fill="both", expand=True)

        status_bar = ttk.Label(self, textvariable=self._status_var, relief="sunken", anchor="w")
        status_bar.pack(fill="x", pady=self._ui_scale.padding(self.STATUS_BAR_GAP, 0))

    def _enable_file_drop(self) -> None:
        """Register current window widgets as external PDF file drop targets."""
        registered = False
        for widget in self._file_drop_widgets():
            registered = self._register_file_drop_target(widget) or registered

        if registered:
            self._file_drop_enabled = True
            return

        if not self._file_drop_unavailable_logged:
            LOGGER.info("File drag-and-drop support is unavailable.")
            self._file_drop_unavailable_logged = True

    def _file_drop_widgets(self) -> Iterator[tk.Misc]:
        yield self.winfo_toplevel()
        yield from self._walk_widget_tree(self)

    @classmethod
    def _walk_widget_tree(cls, widget: tk.Misc) -> Iterator[tk.Misc]:
        yield widget
        for child in widget.winfo_children():
            yield from cls._walk_widget_tree(child)

    def _register_file_drop_target(self, widget: tk.Misc) -> bool:
        drop_target_register = getattr(widget, "drop_target_register", None)
        dnd_bind = getattr(widget, "dnd_bind", None)
        if not callable(drop_target_register) or not callable(dnd_bind):
            return False

        try:
            drop_target_register(self.FILE_DROP_TYPE)
            dnd_bind("<<Drop>>", self._on_file_dropped)
        except tk.TclError as exc:
            LOGGER.warning("Could not register file drop target: %s", exc)
            return False
        return True

    def _show_about_dialog(self) -> None:
        dialog = self._create_about_dialog()
        self._center_on_root(dialog)
        dialog.grab_set()
        dialog.focus_set()
        dialog.wait_window()

    def _create_about_dialog(self) -> tk.Toplevel:
        root = self.winfo_toplevel()
        dialog = tk.Toplevel(root)
        dialog.title(self._text("about.title"))
        dialog.transient(root)
        dialog.resizable(False, False)
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)

        content = ttk.Frame(
            dialog,
            padding=self._ui_scale.padding(
                self.ABOUT_DIALOG_PADDING,
                self.ABOUT_DIALOG_PADDING,
                self.ABOUT_DIALOG_PADDING,
                self.ABOUT_DIALOG_PADDING,
            ),
        )
        content.pack(fill="both", expand=True)

        ttk.Label(content, text=APP_NAME, style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            content,
            text=self._text("about.version", version=app_version()),
            style="Info.TLabel",
        ).pack(anchor="w", pady=self._ui_scale.padding(self.ABOUT_CONTENT_GAP, 0))

        footer = ttk.Frame(content)
        footer.pack(fill="x", pady=self._ui_scale.padding(self.ABOUT_FOOTER_GAP, 0))
        link_label = ttk.Label(
            footer,
            text=AUTHOR_URL,
            style="Link.TLabel",
            cursor="hand2",
        )
        link_label.pack(side="left")
        link_label.bind("<Button-1>", self._on_about_link_clicked)
        ttk.Button(
            footer,
            text=self._text("about.close"),
            command=dialog.destroy,
        ).pack(side="right")

        return dialog

    def _on_about_link_clicked(self, _event: tk.Event[tk.Misc]) -> None:
        if not open_url(AUTHOR_URL):
            LOGGER.warning("Could not open URL in browser: %s", AUTHOR_URL)

    def _center_on_root(self, child: tk.Toplevel) -> None:
        root = self.winfo_toplevel()
        root.update_idletasks()
        child.update_idletasks()

        root_width = root.winfo_width() or root.winfo_reqwidth()
        root_height = root.winfo_height() or root.winfo_reqheight()
        root_x = root.winfo_rootx()
        root_y = root.winfo_rooty()
        child_width = child.winfo_reqwidth()
        child_height = child.winfo_reqheight()
        child_x = root_x + max((root_width - child_width) // 2, 0)
        child_y = root_y + max((root_height - child_height) // 2, 0)
        child.geometry(f"+{child_x}+{child_y}")

    def _on_open_pdf(self) -> None:
        if self._busy:
            return

        file_path = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            title=self._text("dialog.select_pdf_title"),
            filetypes=[
                (self._text("dialog.pdf_filetype"), "*.pdf"),
                (self._text("dialog.all_filetype"), "*.*"),
            ],
        )
        if not file_path:
            return

        self._open_pdf_path(Path(file_path))

    def _on_file_dropped(self, event: tk.Event[tk.Misc]) -> str:
        if self._busy:
            return self.DROP_ACTION_COPY

        pdf_path = self._first_pdf_path(self._dropped_paths(event))
        if pdf_path is None:
            message = self._text("error.drop_pdf_required")
            messagebox.showwarning(self._text("app.title"), message)
            self._status_var.set(message)
            return self.DROP_ACTION_COPY

        self._open_pdf_path(pdf_path)
        return self.DROP_ACTION_COPY

    def _dropped_paths(self, event: tk.Event[tk.Misc]) -> tuple[Path, ...]:
        raw_data = str(getattr(event, "data", ""))
        if not raw_data:
            return ()

        try:
            raw_paths = self.tk.splitlist(raw_data)
        except tk.TclError as exc:
            LOGGER.warning("Could not parse dropped file data: %s", exc)
            return ()
        return tuple(Path(str(raw_path)) for raw_path in raw_paths if str(raw_path))

    @staticmethod
    def _first_pdf_path(paths: tuple[Path, ...]) -> Path | None:
        for path in paths:
            if path.suffix.lower() == ".pdf":
                return path
        return None

    def _open_pdf_path(self, file_path: Path) -> None:
        if self._busy:
            return

        self._busy = True
        self._set_buttons_state(False)
        self._document_token += 1
        token = self._document_token
        self._status_var.set(self._text("status.opening_pdf", filename=Path(file_path).name))
        self._submit_job(
            "open_document",
            lambda path=Path(file_path): self._controller.open_document(path),
            token=token,
        )

    def _on_select_output_dir(self) -> None:
        if self._busy:
            return

        snapshot = self._controller.snapshot()
        if snapshot.source_path is None:
            messagebox.showinfo(
                self._text("app.title"),
                self._text("error.document_not_loaded"),
            )
            return

        selected_dir = filedialog.askdirectory(
            parent=self.winfo_toplevel(),
            title=self._text("dialog.output_folder_title"),
            initialdir=str(snapshot.output_dir or snapshot.source_path.parent),
        )
        if not selected_dir:
            return

        updated_snapshot = self._controller.set_output_dir(Path(selected_dir))
        self._refresh_session(updated_snapshot)
        self._status_var.set(self._text("status.output_dir_changed"))

    def _on_mode_changed(self, _event: tk.Event[tk.Misc]) -> None:
        self._mode = self._mode_from_label(self._language, self._mode_var.get())
        self._refresh_mode_ui()
        snapshot = self._controller.snapshot()
        self._status_var.set(self._default_status_message(snapshot))
        self._set_buttons_state(not self._busy)

    def _on_language_changed(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        if self._busy:
            self._language_var.set(language_label(self._language))
            return

        selected_language = language_from_label(self._language_var.get())
        if selected_language == self._language:
            return

        self._language = selected_language
        self._apply_language_text(reset_status=True)
        self._set_buttons_state(not self._busy)

    def _on_page_selected(self, page_index: int) -> None:
        if self._busy:
            return

        if self._is_selected_pages_export_mode():
            self._toggle_selected_page(page_index)
            return

        try:
            preview = self._controller.preview_split_to_page(page_index)
        except Exception as exc:
            self._show_worker_error("error.split_preview_failed", exc)
            return

        if not self._confirm_split(preview):
            self._status_var.set(self._text("status.split_canceled"))
            return

        self._busy = True
        self._save_in_progress = True
        self._set_buttons_state(False)
        self._status_var.set(
            self._text(
                "status.saving_split",
                start_page=preview.plan.start_page,
                end_page=preview.plan.end_page,
            )
        )
        self._submit_job(
            "split_document",
            lambda: self._controller.split_to_page(page_index),
            token=self._document_token,
        )

    def _toggle_selected_page(self, page_index: int) -> None:
        """Toggle one page in selected-pages export mode."""
        if page_index in self._selected_pages:
            self._selected_pages.remove(page_index)
            self._status_var.set(self._text("status.page_unselected", page_index=page_index))
        else:
            self._selected_pages.add(page_index)
            self._status_var.set(self._text("status.page_selected", page_index=page_index))
        self._refresh_thumbnail_states()
        self._refresh_selected_pages_summary()
        self._set_buttons_state(not self._busy)

    def _on_export_selected_pages(self) -> None:
        if self._busy:
            return

        try:
            preview = self._controller.preview_selected_pages(self._selected_pages)
        except Exception as exc:
            self._show_worker_error("error.selected_pages_preview_failed", exc)
            return

        if not self._confirm_selected_pages_export(preview):
            self._status_var.set(self._text("status.export_canceled"))
            return

        selected_pages = tuple(preview.page_indexes)
        self._busy = True
        self._save_in_progress = True
        self._set_buttons_state(False)
        self._status_var.set(
            self._text(
                "status.exporting_selected",
                page_count=page_count_text(self._language, preview.page_count),
            )
        )
        self._submit_job(
            "export_selected_pages",
            lambda: self._controller.export_selected_pages(selected_pages),
            token=self._document_token,
        )

    def _confirm_split(self, preview: SplitPreview) -> bool:
        """Ask the user to confirm the pending split."""
        return messagebox.askyesno(
            self._text("app.title"),
            self._build_split_preview_message(preview),
            icon="question",
        )

    def _confirm_selected_pages_export(self, preview: SelectedPagesPreview) -> bool:
        """Ask the user to confirm the pending selected-pages export."""
        return messagebox.askyesno(
            self._text("app.title"),
            self._build_selected_pages_preview_message(preview),
            icon="question",
        )

    def _build_split_preview_message(self, preview: SplitPreview) -> str:
        """Build a user-facing description of the pending split."""
        return self._text(
            "dialog.split_preview",
            part_number=preview.plan.part_number,
            start_page=preview.plan.start_page,
            end_page=preview.plan.end_page,
            page_count=page_count_text(self._language, preview.page_count),
            filename=preview.output_path.name,
            folder=preview.output_path.parent,
        )

    def _build_selected_pages_preview_message(self, preview: SelectedPagesPreview) -> str:
        """Build a user-facing description of the pending selected-pages export."""
        return self._text(
            "dialog.selected_pages_preview",
            page_ranges=self._format_page_ranges(preview.page_indexes),
            page_count=page_count_text(self._language, preview.page_count),
            filename=preview.output_path.name,
            folder=preview.output_path.parent,
        )

    def _submit_job(self, job_name: str, task: Callable[[], Any], *, token: int) -> None:
        future = self._executor.submit(task)
        future.add_done_callback(
            lambda completed_future, name=job_name, current_token=token: self._worker_queue.put(
                (name, current_token, {}, completed_future)
            )
        )

    def _poll_worker_queue(self) -> None:
        try:
            processed = 0
            while processed < self.MAX_QUEUE_EVENTS_PER_POLL:
                job_name, token, _meta, future = self._worker_queue.get_nowait()
                if token != self._document_token and job_name != "thumbnail":
                    continue
                self._process_job_result(job_name, token, future)
                processed += 1
        except queue.Empty:
            pass
        finally:
            self._ensure_visible_thumbnail_progress()
            self.after(self.POLL_INTERVAL_MS, self._poll_worker_queue)

    def _process_job_result(self, job_name: str, token: int, future: Future[Any]) -> None:
        try:
            result = future.result()
        except Exception as exc:
            self._handle_job_error(job_name, token, exc)
            return

        if token != self._document_token and job_name.startswith("thumbnail:"):
            return

        if job_name == "open_document":
            self._busy = False
            self._set_buttons_state(True)
            self._replace_document(result)
            return

        if job_name == "split_document":
            self._busy = False
            self._save_in_progress = False
            self._set_buttons_state(True)
            self._handle_split_success(result)
            self._schedule_thumbnail_jobs()
            return

        if job_name == "export_selected_pages":
            self._busy = False
            self._save_in_progress = False
            self._set_buttons_state(True)
            self._handle_selected_pages_export_success(result)
            self._schedule_thumbnail_jobs()
            return

        if job_name.startswith("thumbnail:"):
            page_index = int(job_name.split(":", maxsplit=1)[1])
            self._inflight_thumbnail_pages.discard(page_index)
            self._pending_thumbnail_pages.discard(page_index)
            self._failed_thumbnail_pages.discard(page_index)
            photo_image = ImageTk.PhotoImage(result)
            self._photo_images[page_index] = photo_image
            self._thumbnail_grid.set_thumbnail(page_index, photo_image)
            self._trim_thumbnail_cache()
            self._schedule_thumbnail_jobs()

    def _handle_job_error(self, job_name: str, token: int, exc: Exception) -> None:
        if job_name == "open_document":
            self._busy = False
            self._set_buttons_state(True)
            self._show_worker_error("error.open_pdf_failed", exc)
            return

        if job_name == "split_document":
            self._busy = False
            self._save_in_progress = False
            self._set_buttons_state(True)
            self._show_worker_error("error.save_pdf_failed", exc)
            self._schedule_thumbnail_jobs()
            return

        if job_name == "export_selected_pages":
            self._busy = False
            self._save_in_progress = False
            self._set_buttons_state(True)
            self._show_worker_error("error.selected_pages_export_failed", exc)
            self._schedule_thumbnail_jobs()
            return

        if job_name.startswith("thumbnail:"):
            if token != self._document_token:
                return
            page_index = int(job_name.split(":", maxsplit=1)[1])
            self._inflight_thumbnail_pages.discard(page_index)
            self._pending_thumbnail_pages.discard(page_index)
            self._failed_thumbnail_pages.add(page_index)
            self._thumbnail_grid.set_card_message_key(page_index, "thumbnail.preview_failed")
            self._schedule_thumbnail_jobs()

    def _show_worker_error(self, fallback_key: str, exc: Exception) -> None:
        fallback_title = self._text(fallback_key)
        user_message = self._localized_exception_message(exc)
        if isinstance(exc, (DocumentNotLoadedError, SplitSelectionError, PageSelectionError)):
            messagebox.showwarning(self._text("app.title"), user_message)
            self._status_var.set(user_message)
            return

        if isinstance(exc, DocumentCompleteError):
            messagebox.showinfo(self._text("app.title"), user_message)
            self._status_var.set(user_message)
            return

        if isinstance(exc, (PdfOpenError, PdfSaveError, PdfThumbnailError, PdfProcessingError)):
            LOGGER.exception(fallback_title, exc_info=exc)
            messagebox.showerror(self._text("app.title"), user_message)
            self._status_var.set(user_message)
            return

        LOGGER.exception(fallback_title, exc_info=exc)
        messagebox.showerror(self._text("app.title"), fallback_title)
        self._status_var.set(fallback_title)

    def _localized_exception_message(self, exc: Exception) -> str:
        message_code = getattr(exc, "message_code", None)
        if message_code is None:
            message_code = getattr(exc, "message_key", None)
        message_values = getattr(exc, "message_values", {})
        if isinstance(message_code, str):
            try:
                return self._text(message_code, **message_values)
            except KeyError:
                LOGGER.warning("Unknown localization message code: %s", message_code)
        return str(exc)

    def _replace_document(self, snapshot: SessionSnapshot) -> None:
        self._selected_pages.clear()
        self._reset_thumbnail_state()
        self._thumbnail_grid.set_thumbnail_size(self._current_thumbnail_size())
        self._thumbnail_grid.build_cards(
            snapshot.total_pages,
            self._on_page_selected,
            self._controller.page_states(),
        )
        self._enable_file_drop()
        self._refresh_session(snapshot)
        self._status_var.set(self._default_status_message(snapshot))
        self._start_thumbnail_loading(snapshot.total_pages)

    def _refresh_session(self, snapshot: SessionSnapshot) -> None:
        file_name = (
            snapshot.source_path.name
            if snapshot.source_path
            else self._text("status.pdf_file_none")
        )
        output_dir = (
            str(snapshot.output_dir)
            if snapshot.output_dir
            else self._text("status.save_folder_none")
        )
        progress = f"{min(snapshot.next_start_page, snapshot.total_pages)}/{snapshot.total_pages}"

        self._file_var.set(self._text("status.pdf_file", filename=file_name))
        self._output_dir_var.set(self._text("status.save_folder", folder=output_dir))
        if snapshot.source_path is None:
            self._next_start_var.set(self._text("status.next_start_none"))
        elif snapshot.is_complete:
            self._next_start_var.set(self._text("status.next_start_complete"))
        else:
            self._next_start_var.set(
                self._text("status.next_start", page=snapshot.next_start_page)
            )
        self._progress_var.set(self._text("status.progress", progress=progress))
        self._refresh_selected_pages_summary()
        self._refresh_thumbnail_states()

    def _handle_split_success(self, saved_segment: SavedSegment) -> None:
        self._refresh_session(saved_segment.snapshot)
        self._status_var.set(
            self._text(
                "status.split_saved",
                start_page=saved_segment.plan.start_page,
                end_page=saved_segment.plan.end_page,
                filename=saved_segment.file_path.name,
            )
        )
        if saved_segment.snapshot.is_complete:
            messagebox.showinfo(
                self._text("app.title"),
                self._text("error.document_complete"),
            )

    def _handle_selected_pages_export_success(self, exported_pages: ExportedPages) -> None:
        self._selected_pages.clear()
        self._refresh_session(exported_pages.snapshot)
        self._status_var.set(
            self._text(
                "status.selected_pages_exported",
                page_count=page_count_text(self._language, exported_pages.page_count),
                page_ranges=self._format_page_ranges(exported_pages.page_indexes),
                filename=exported_pages.file_path.name,
            )
        )

    def _set_buttons_state(self, enabled: bool) -> None:
        has_document = self._controller.snapshot().source_path is not None
        open_state = "normal" if not self._busy else "disabled"
        output_state = "normal" if enabled and not self._busy and has_document else "disabled"
        export_state = (
            "normal"
            if (
                enabled
                and not self._busy
                and has_document
                and self._is_selected_pages_export_mode()
                and bool(self._selected_pages)
            )
            else "disabled"
        )

        self._open_button.configure(state=open_state)
        self._file_menu.entryconfigure(self.FILE_MENU_OPEN_INDEX, state=open_state)
        self._set_language_menu_state(not self._busy)
        self._mode_combobox.configure(state="readonly" if not self._busy else "disabled")
        self._output_button.configure(state=output_state)
        self._file_menu.entryconfigure(self.FILE_MENU_OUTPUT_DIR_INDEX, state=output_state)
        self._export_button.configure(state=export_state)
        self._file_menu.entryconfigure(self.FILE_MENU_EXPORT_INDEX, state=export_state)
        self._thumbnail_scale_spinbox.configure(state="normal" if not self._busy else "disabled")

    def _set_language_menu_state(self, enabled: bool) -> None:
        """Enable or disable all language choices in the menu."""
        last_index = self._language_menu.index("end")
        if last_index is None:
            return

        state = "normal" if enabled else "disabled"
        for index in range(last_index + 1):
            self._language_menu.entryconfigure(index, state=state)

    def _refresh_mode_ui(self) -> None:
        """Refresh mode-specific selection highlights."""
        self._refresh_thumbnail_states()
        self._refresh_selected_pages_summary()

    def _refresh_thumbnail_states(self) -> None:
        """Refresh split-state and selection-state visuals together."""
        self._thumbnail_grid.update_states(self._controller.page_states())
        self._thumbnail_grid.update_selection(
            self._selected_pages if self._is_selected_pages_export_mode() else set()
        )

    def _refresh_selected_pages_summary(self) -> None:
        """Update the info label that shows selected pages for export."""
        if not self._selected_pages:
            self._selected_pages_var.set(self._text("status.selected_pages_none"))
            return
        self._selected_pages_var.set(
            self._text(
                "status.selected_pages_summary",
                page_ranges=self._format_page_ranges(self._selected_pages),
                page_count=page_count_text(self._language, len(self._selected_pages)),
            )
        )

    def _default_status_message(self, snapshot: SessionSnapshot) -> str:
        """Return the default status message for the current mode."""
        if snapshot.source_path is None:
            return self._text("status.open_pdf_prompt")
        if self._is_selected_pages_export_mode():
            return self._text("status.select_pages_export_prompt")
        return self._text("status.sequential_prompt")

    def _is_selected_pages_export_mode(self) -> bool:
        """Return whether the UI is currently in selected-pages export mode."""
        return self._mode == self.SELECTED_PAGES_EXPORT_MODE

    def _on_thumbnail_scale_changed(self) -> None:
        self._apply_thumbnail_scale()

    def _on_thumbnail_scale_change_event(self, _event: tk.Event[tk.Misc]) -> None:
        self._apply_thumbnail_scale()

    @staticmethod
    def _format_page_ranges(page_indexes: set[int] | tuple[int, ...]) -> str:
        """Collapse sorted page indexes into compact display ranges."""
        normalized_pages = sorted(set(page_indexes))
        if not normalized_pages:
            return "-"

        ranges: list[str] = []
        start_page = normalized_pages[0]
        end_page = normalized_pages[0]
        for page_index in normalized_pages[1:]:
            if page_index == end_page + 1:
                end_page = page_index
                continue
            ranges.append(
                f"{start_page}" if start_page == end_page else f"{start_page}~{end_page}"
            )
            start_page = page_index
            end_page = page_index

        ranges.append(f"{start_page}" if start_page == end_page else f"{start_page}~{end_page}")
        return ", ".join(ranges)

    @classmethod
    def _thumbnail_size_for_scale(cls, scale_percent: int) -> tuple[int, int]:
        return tuple(
            max(1, round(base_size * scale_percent / 100)) for base_size in cls.BASE_THUMBNAIL_SIZE
        )

    @classmethod
    def _thumbnail_request_order(cls, total_pages: int, visible_pages: list[int]) -> list[int]:
        """Return page indexes ordered around the current viewport."""
        if total_pages <= 0:
            return []

        order: list[int] = []
        seen: set[int] = set()
        for page_index in visible_pages:
            if 0 <= page_index < total_pages and page_index not in seen:
                order.append(page_index)
                seen.add(page_index)

        if not order:
            order.append(0)
            seen.add(0)

        left = order[0] - 1
        right = order[-1] + 1
        while len(order) < total_pages:
            appended = False
            if right < total_pages and right not in seen:
                order.append(right)
                seen.add(right)
                appended = True
            if left >= 0 and left not in seen:
                order.append(left)
                seen.add(left)
                appended = True
            if not appended:
                for page_index in range(total_pages):
                    if page_index in seen:
                        continue
                    order.append(page_index)
                    seen.add(page_index)
                break
            right += 1
            left -= 1
        return order

    @classmethod
    def _thumbnail_window_pages(
        cls,
        total_pages: int,
        visible_pages: list[int],
        *,
        viewport_multiplier: int,
        minimum_pages: int,
    ) -> set[int]:
        """Return a contiguous workset around the viewport for loading or caching."""
        if total_pages <= 0:
            return set()

        normalized_visible_pages = sorted(
            {page_index for page_index in visible_pages if 0 <= page_index < total_pages}
        )
        if not normalized_visible_pages:
            return set(range(min(total_pages, minimum_pages)))

        visible_start = normalized_visible_pages[0]
        visible_end = normalized_visible_pages[-1]
        visible_span = max(1, visible_end - visible_start + 1)
        margin = max(visible_span * viewport_multiplier, minimum_pages // 2)
        start_page = max(0, visible_start - margin)
        end_page = min(total_pages, visible_end + margin + 1)
        return set(range(start_page, end_page))

    @classmethod
    def _parse_thumbnail_scale_percent(cls, raw_value: str) -> int | None:
        normalized_value = raw_value.strip().removesuffix("%").strip()
        if not normalized_value:
            return None

        try:
            scale_percent = int(normalized_value)
        except ValueError:
            return None

        if cls.MIN_THUMBNAIL_SCALE_PERCENT <= scale_percent <= cls.MAX_THUMBNAIL_SCALE_PERCENT:
            return scale_percent
        return None

    def _current_thumbnail_size(self) -> tuple[int, int]:
        base_width, base_height = self._thumbnail_size_for_scale(self._thumbnail_scale_percent)
        return self._ui_scale.size(base_width, base_height)

    def _on_visible_pages_changed(self, visible_pages: list[int]) -> None:
        self._visible_thumbnail_pages = tuple(visible_pages)
        self._schedule_thumbnail_jobs()

    def _ensure_visible_thumbnail_progress(self) -> None:
        """Recover thumbnail scheduling if a scroll callback was missed."""
        if self._total_thumbnail_pages <= 0:
            return

        visible_pages = tuple(self._thumbnail_grid.visible_page_indexes())
        if visible_pages and visible_pages != self._visible_thumbnail_pages:
            self._visible_thumbnail_pages = visible_pages

        if not self._visible_thumbnail_pages:
            return

        if any(
            page_index not in self._photo_images
            and page_index not in self._inflight_thumbnail_pages
            and page_index not in self._failed_thumbnail_pages
            for page_index in self._visible_thumbnail_pages
        ):
            self._schedule_thumbnail_jobs()

    def _next_thumbnail_page(self) -> int | None:
        for page_index in self._thumbnail_request_order(
            self._total_thumbnail_pages,
            list(self._visible_thumbnail_pages),
        ):
            if (
                page_index in self._pending_thumbnail_pages
                and page_index not in self._inflight_thumbnail_pages
            ):
                return page_index
        return None

    def _reset_thumbnail_state(self) -> None:
        self._total_thumbnail_pages = 0
        self._pending_thumbnail_pages.clear()
        self._inflight_thumbnail_pages.clear()
        self._visible_thumbnail_pages = ()
        self._failed_thumbnail_pages.clear()
        self._photo_images.clear()
        if self._thumbnail_render_after_id is not None:
            self.after_cancel(self._thumbnail_render_after_id)
            self._thumbnail_render_after_id = None

    def _apply_thumbnail_scale(self) -> None:
        if self._busy:
            self._thumbnail_scale_var.set(str(self._thumbnail_scale_percent))
            return

        selected_scale = self._parse_thumbnail_scale_percent(self._thumbnail_scale_var.get())
        if selected_scale is None:
            self._thumbnail_scale_var.set(str(self._thumbnail_scale_percent))
            self._status_var.set(
                self._text(
                    "status.thumbnail_scale_invalid",
                    min_percent=self.MIN_THUMBNAIL_SCALE_PERCENT,
                    max_percent=self.MAX_THUMBNAIL_SCALE_PERCENT,
                )
            )
            return

        self._thumbnail_scale_var.set(str(selected_scale))
        if selected_scale == self._thumbnail_scale_percent:
            return

        self._thumbnail_scale_percent = selected_scale
        snapshot = self._controller.snapshot()
        if snapshot.source_path is None:
            self._status_var.set(
                self._text("status.thumbnail_scale_set", scale_percent=selected_scale)
            )
            return

        self._rerender_thumbnails(snapshot)
        self._status_var.set(
            self._text("status.thumbnail_scale_changing", scale_percent=selected_scale)
        )

    def _rerender_thumbnails(self, snapshot: SessionSnapshot) -> None:
        # Invalidate in-flight thumbnail jobs so previous-scale results are ignored.
        self._document_token += 1
        self._reset_thumbnail_state()
        self._thumbnail_grid.set_thumbnail_size(self._current_thumbnail_size())
        self._thumbnail_grid.build_cards(
            snapshot.total_pages,
            self._on_page_selected,
            self._controller.page_states(),
        )
        self._enable_file_drop()
        self._refresh_session(snapshot)
        self._start_thumbnail_loading(snapshot.total_pages)

    def _start_thumbnail_loading(self, total_pages: int) -> None:
        self._total_thumbnail_pages = total_pages
        self._pending_thumbnail_pages.clear()
        self._inflight_thumbnail_pages.clear()
        self._visible_thumbnail_pages = ()
        self._failed_thumbnail_pages.clear()
        self.after_idle(self._thumbnail_grid.notify_visible_pages_changed)

    def _schedule_thumbnail_jobs(self) -> None:
        if self._save_in_progress or self._total_thumbnail_pages <= 0:
            return

        self._refresh_thumbnail_workset()
        if not self._pending_thumbnail_pages:
            return

        if self._thumbnail_render_after_id is not None or self._inflight_thumbnail_pages:
            return

        self._thumbnail_render_after_id = self.after(
            self.THUMBNAIL_RENDER_INTERVAL_MS,
            self._render_next_thumbnail,
        )

    def _render_next_thumbnail(self) -> None:
        self._thumbnail_render_after_id = None
        if self._save_in_progress or self._total_thumbnail_pages <= 0:
            return

        self._refresh_thumbnail_workset()
        page_index = self._next_thumbnail_page()
        if page_index is None:
            return

        self._inflight_thumbnail_pages.add(page_index)
        try:
            result = self._controller.render_thumbnail(
                page_index,
                self._current_thumbnail_size(),
            )
        except Exception as exc:
            LOGGER.exception("썸네일 렌더링에 실패했습니다.", exc_info=exc)
            self._inflight_thumbnail_pages.discard(page_index)
            self._pending_thumbnail_pages.discard(page_index)
            self._failed_thumbnail_pages.add(page_index)
            self._thumbnail_grid.set_card_message_key(page_index, "thumbnail.preview_failed")
            self._schedule_thumbnail_jobs()
            return

        self._inflight_thumbnail_pages.discard(page_index)
        self._pending_thumbnail_pages.discard(page_index)
        self._failed_thumbnail_pages.discard(page_index)
        try:
            photo_image = self._create_thumbnail_photo_image(page_index, result)
        except tk.TclError as exc:
            LOGGER.exception("썸네일 이미지를 Tk에 적용하지 못했습니다.", exc_info=exc)
            self._failed_thumbnail_pages.add(page_index)
            self._thumbnail_grid.set_card_message_key(page_index, "thumbnail.preview_failed")
            self._schedule_thumbnail_jobs()
            return
        self._photo_images[page_index] = photo_image
        self._thumbnail_grid.set_thumbnail(page_index, photo_image)
        self._trim_thumbnail_cache()
        self._schedule_thumbnail_jobs()

    def _refresh_thumbnail_workset(self) -> None:
        request_pages = self._thumbnail_window_pages(
            self._total_thumbnail_pages,
            list(self._visible_thumbnail_pages),
            viewport_multiplier=self.THUMBNAIL_REQUEST_VIEWPORT_MULTIPLIER,
            minimum_pages=self.MIN_REQUEST_PAGES,
        )
        self._pending_thumbnail_pages.intersection_update(request_pages)
        for page_index in request_pages:
            if (
                page_index in self._failed_thumbnail_pages
                or page_index in self._photo_images
                or page_index in self._inflight_thumbnail_pages
            ):
                continue
            self._pending_thumbnail_pages.add(page_index)
            self._thumbnail_grid.set_card_message_key(
                page_index,
                self.THUMBNAIL_LOADING_MESSAGE_KEY,
            )
        self._trim_thumbnail_cache()

    def _create_thumbnail_photo_image(
        self,
        page_index: int,
        image: Any,
    ) -> ImageTk.PhotoImage:
        """Create a Tk image after freeing off-screen thumbnails if needed."""
        self._trim_thumbnail_cache(protected_pages={page_index})
        gc.collect()
        try:
            return ImageTk.PhotoImage(image)
        except tk.TclError:
            self._trim_thumbnail_cache(
                protected_pages=set(self._visible_thumbnail_pages) | {page_index}
            )
            gc.collect()
            return ImageTk.PhotoImage(image)

    def _trim_thumbnail_cache(self, protected_pages: set[int] | None = None) -> None:
        retained_pages = self._thumbnail_window_pages(
            self._total_thumbnail_pages,
            list(self._visible_thumbnail_pages),
            viewport_multiplier=self.THUMBNAIL_CACHE_VIEWPORT_MULTIPLIER,
            minimum_pages=self.MIN_CACHE_PAGES,
        )
        if protected_pages is not None:
            retained_pages.update(protected_pages)
        for page_index in tuple(self._photo_images):
            if page_index in retained_pages:
                continue
            self._photo_images.pop(page_index, None)
            self._thumbnail_grid.set_card_message_key(
                page_index,
                self.THUMBNAIL_LOADING_MESSAGE_KEY,
            )
