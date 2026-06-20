"""Application bootstrap."""

from __future__ import annotations

import logging
import sys
import tkinter as tk
from pathlib import Path

if __package__ in {None, ""}:
    project_root = Path(__file__).resolve().parent.parent
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)

from pdf_splitter.app.controller import SequentialPdfSplitController
from pdf_splitter.infra.windows_dpi import configure_process_dpi_awareness
from pdf_splitter.infra.pdf_service import PdfProcessingService
from pdf_splitter.ui.main_window import APP_TITLE, PdfSplitApplication
from pdf_splitter.ui.scaling import DpiSyncController, UiScale
from pdf_splitter.ui.scaling import configure_default_tk_fonts, configure_tk_dpi

DEFAULT_WINDOW_SIZE = (750, 550)
MINIMUM_WINDOW_SIZE = (400, 300)
LOGGER = logging.getLogger(__name__)


def create_root() -> tk.Tk:
    """Create a Tk root, enabling OS file drag-and-drop when available."""
    try:
        from tkinterdnd2 import TkinterDnD
    except ImportError:
        LOGGER.info("tkinterdnd2 is not installed; file drag-and-drop is disabled.")
        return tk.Tk()

    try:
        return TkinterDnD.Tk()
    except tk.TclError as exc:
        LOGGER.warning("Could not initialize file drag-and-drop support: %s", exc)
        return tk.Tk()


def build_app() -> tuple[tk.Tk, PdfSplitApplication]:
    """Create the Tkinter root and wire dependencies."""
    configure_process_dpi_awareness()
    root = create_root()
    dpi_scale = configure_tk_dpi(root)
    font_family = configure_default_tk_fonts(root)
    ui_scale = UiScale(factor=dpi_scale.factor, font_family=font_family)
    root.title(APP_TITLE)
    root.geometry(ui_scale.geometry(*DEFAULT_WINDOW_SIZE))
    root.minsize(*ui_scale.size(*MINIMUM_WINDOW_SIZE))

    controller = SequentialPdfSplitController(PdfProcessingService())
    application = PdfSplitApplication(root, controller, ui_scale=ui_scale)
    application.pack(fill="both", expand=True)
    dpi_sync_controller = DpiSyncController(root, application.apply_ui_scale)
    application.set_dpi_sync_controller(dpi_sync_controller)
    dpi_sync_controller.bind()
    root.protocol("WM_DELETE_WINDOW", application.on_close)
    return root, application


def main() -> None:
    """Run the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    root, _application = build_app()
    root.mainloop()


if __name__ == "__main__":
    main()
