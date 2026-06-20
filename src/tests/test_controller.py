"""Unit tests for sequential PDF split controller."""

import runpy
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import fitz
from PIL import Image

from pdf_splitter.app.controller import SequentialPdfSplitController
from pdf_splitter.domain.models import (
    DocumentCompleteError,
    DocumentNotLoadedError,
    PageSelectionError,
    SplitSelectionError,
)
from pdf_splitter.infra.pdf_service import PdfDocumentInfo
from pdf_splitter.infra.pdf_service import PdfProcessingService


class FakePdfService:
    """Simple stub used to verify controller flow without real PDF I/O."""

    def __init__(self, total_pages: int, root_dir: Path) -> None:
        self._total_pages = total_pages
        self._root_dir = root_dir
        self.saved_ranges: list[tuple[int, int, int, Path]] = []
        self.saved_selected_pages: list[tuple[tuple[int, ...], Path]] = []

    def open_document(self, pdf_path: Path, output_dir: Path | None = None) -> PdfDocumentInfo:
        return PdfDocumentInfo(
            path=pdf_path,
            total_pages=self._total_pages,
            output_dir=output_dir or self._root_dir,
        )

    def render_thumbnail(
        self, pdf_path: Path, page_index: int, max_size: tuple[int, int]
    ) -> Image.Image:
        return Image.new("RGB", max_size, color=(255, 255, 255))

    def preview_output_path(self, pdf_path: Path, output_dir: Path, part_number: int) -> Path:
        return output_dir / f"{pdf_path.stem}_{part_number}장.pdf"

    def preview_selected_pages_output_path(self, pdf_path: Path, output_dir: Path) -> Path:
        return output_dir / f"{pdf_path.stem}_선택페이지.pdf"

    def save_segment(
        self,
        pdf_path: Path,
        start_page: int,
        end_page: int,
        output_dir: Path,
        part_number: int,
    ) -> Path:
        target = output_dir / f"{pdf_path.stem}_{part_number}장.pdf"
        self.saved_ranges.append((start_page, end_page, part_number, target))
        return target

    def save_selected_pages(
        self,
        pdf_path: Path,
        page_indexes: tuple[int, ...],
        output_dir: Path,
    ) -> Path:
        target = output_dir / f"{pdf_path.stem}_선택페이지.pdf"
        self.saved_selected_pages.append((page_indexes, target))
        return target


class SequentialPdfSplitControllerTests(unittest.TestCase):
    """Verify sequential range planning and validation rules."""

    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self._root_dir = Path(self._temp_dir.name)
        self._service = FakePdfService(total_pages=9, root_dir=self._root_dir)
        self._controller = SequentialPdfSplitController(self._service)
        self._pdf_path = self._root_dir / "sample.pdf"

    def test_first_split_starts_from_zero(self) -> None:
        self._controller.open_document(self._pdf_path)

        result = self._controller.split_to_page(3)

        self.assertEqual(
            (0, 3, 1), (result.plan.start_page, result.plan.end_page, result.plan.part_number)
        )
        self.assertEqual(self._root_dir / "sample_1장.pdf", result.file_path)
        self.assertEqual(4, result.snapshot.next_start_page)

    def test_following_split_uses_next_page(self) -> None:
        self._controller.open_document(self._pdf_path)
        self._controller.split_to_page(3)

        result = self._controller.split_to_page(5)

        self.assertEqual(
            (4, 5, 2), (result.plan.start_page, result.plan.end_page, result.plan.part_number)
        )
        self.assertEqual(6, result.snapshot.next_start_page)

    def test_selecting_previous_page_is_rejected(self) -> None:
        self._controller.open_document(self._pdf_path)
        self._controller.split_to_page(3)

        with self.assertRaises(SplitSelectionError):
            self._controller.split_to_page(2)

    def test_selection_error_keeps_user_message_code_and_values(self) -> None:
        self._controller.open_document(self._pdf_path)
        self._controller.split_to_page(3)

        with self.assertRaises(SplitSelectionError) as context:
            self._controller.split_to_page(2)

        self.assertEqual("error.already_saved_until", context.exception.message_code)
        self.assertEqual(
            {"completed_page": 3, "next_start_page": 4},
            context.exception.message_values,
        )

    def test_completion_blocks_more_saves(self) -> None:
        service = FakePdfService(total_pages=3, root_dir=self._root_dir)
        controller = SequentialPdfSplitController(service)
        controller.open_document(self._pdf_path)
        result = controller.split_to_page(2)

        self.assertTrue(result.snapshot.is_complete)
        with self.assertRaises(DocumentCompleteError):
            controller.split_to_page(2)

    def test_output_dir_requires_open_document(self) -> None:
        with self.assertRaises(DocumentNotLoadedError) as context:
            self._controller.set_output_dir(self._root_dir / "out")

        self.assertEqual("error.document_not_loaded", context.exception.message_code)

    def test_preview_does_not_advance_state(self) -> None:
        self._controller.open_document(self._pdf_path)

        preview = self._controller.preview_split_to_page(3)

        self.assertEqual(
            (0, 3, 1), (preview.plan.start_page, preview.plan.end_page, preview.plan.part_number)
        )
        self.assertEqual(self._root_dir / "sample_1장.pdf", preview.output_path)
        self.assertEqual(4, preview.page_count)
        self.assertEqual(0, self._controller.snapshot().next_start_page)

    def test_preview_selected_pages_sorts_and_deduplicates_indexes(self) -> None:
        self._controller.open_document(self._pdf_path)

        preview = self._controller.preview_selected_pages({5, 1, 5, 3})

        self.assertEqual((1, 3, 5), preview.page_indexes)
        self.assertEqual(3, preview.page_count)
        self.assertEqual(self._root_dir / "sample_선택페이지.pdf", preview.output_path)
        self.assertEqual(0, self._controller.snapshot().next_start_page)

    def test_export_selected_pages_does_not_advance_split_progress(self) -> None:
        self._controller.open_document(self._pdf_path)

        exported = self._controller.export_selected_pages({4, 2, 4})

        self.assertEqual((2, 4), exported.page_indexes)
        self.assertEqual(self._root_dir / "sample_선택페이지.pdf", exported.file_path)
        self.assertEqual(
            [((2, 4), self._root_dir / "sample_선택페이지.pdf")],
            self._service.saved_selected_pages,
        )
        self.assertEqual(0, exported.snapshot.next_start_page)

    def test_export_selected_pages_requires_non_empty_selection(self) -> None:
        self._controller.open_document(self._pdf_path)

        with self.assertRaises(PageSelectionError) as context:
            self._controller.export_selected_pages(set())

        self.assertEqual("error.no_pages_selected", context.exception.message_code)


class ScriptBootstrapTests(unittest.TestCase):
    """Verify direct script execution can resolve package imports."""

    def test_main_py_supports_direct_script_bootstrap(self) -> None:
        namespace = runpy.run_path(
            str(Path(__file__).resolve().parent.parent / "pdf_splitter" / "main.py"),
            run_name="script_bootstrap_test",
        )

        self.assertIn("build_app", namespace)
        self.assertTrue(callable(namespace["build_app"]))


class PdfProcessingServiceTests(unittest.TestCase):
    """Verify thumbnail rendering helpers stay within requested bounds."""

    def test_fit_scale_uses_requested_thumbnail_bounds(self) -> None:
        service = PdfProcessingService()

        scale_x, scale_y = service._fit_scale(fitz.Rect(0, 0, 600, 800), (300, 400))

        self.assertEqual((0.5, 0.5), (scale_x, scale_y))

    def test_render_thumbnail_opens_document_for_each_call(self) -> None:
        service = PdfProcessingService()
        fake_page = Mock()
        fake_page.rect = fitz.Rect(0, 0, 100, 100)
        fake_page.get_pixmap.return_value = SimpleNamespace(
            width=1,
            height=1,
            samples=b"\x00\x00\x00",
        )
        fake_document = Mock()
        fake_document.load_page.return_value = fake_page

        open_context = Mock()
        open_context.__enter__ = Mock(return_value=fake_document)
        open_context.__exit__ = Mock(return_value=False)

        with patch(
            "pdf_splitter.infra.pdf_service.fitz.open",
            return_value=open_context,
        ) as open_mock:
            service.render_thumbnail(Path("sample.pdf"), 0, (50, 50))
            service.render_thumbnail(Path("sample.pdf"), 1, (50, 50))

        self.assertEqual(2, open_mock.call_count)
        self.assertEqual(2, fake_document.load_page.call_count)


if __name__ == "__main__":
    unittest.main()
