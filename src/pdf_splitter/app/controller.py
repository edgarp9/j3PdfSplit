"""Application controller coordinating PDF workflows and services."""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass
from pathlib import Path
from threading import Lock

from PIL import Image

from pdf_splitter.domain.models import DocumentNotLoadedError
from pdf_splitter.domain.models import PageSelectionError
from pdf_splitter.domain.models import PageVisualState
from pdf_splitter.domain.models import SequentialSplitSession
from pdf_splitter.domain.models import SessionSnapshot
from pdf_splitter.domain.models import SplitPlan
from pdf_splitter.infra.pdf_service import PdfProcessingService


@dataclass(frozen=True)
class SavedSegment:
    """Represents one successfully saved output PDF."""

    plan: SplitPlan
    file_path: Path
    snapshot: SessionSnapshot


@dataclass(frozen=True)
class SplitPreview:
    """Represents a pending sequential split before saving."""

    plan: SplitPlan
    output_path: Path
    snapshot: SessionSnapshot

    @property
    def page_count(self) -> int:
        """Return the number of pages included in the planned segment."""
        return self.plan.end_page - self.plan.start_page + 1


@dataclass(frozen=True)
class SelectedPagesPreview:
    """Represents a pending selected-pages export before saving."""

    page_indexes: tuple[int, ...]
    output_path: Path
    snapshot: SessionSnapshot

    @property
    def page_count(self) -> int:
        """Return the number of selected pages to export."""
        return len(self.page_indexes)


@dataclass(frozen=True)
class ExportedPages:
    """Represents one successfully exported selected-pages PDF."""

    page_indexes: tuple[int, ...]
    file_path: Path
    snapshot: SessionSnapshot

    @property
    def page_count(self) -> int:
        """Return the number of exported pages."""
        return len(self.page_indexes)


class SequentialPdfSplitController:
    """Expose thread-safe use cases for the Tkinter UI."""

    def __init__(self, pdf_service: PdfProcessingService) -> None:
        self._pdf_service = pdf_service
        self._session = SequentialSplitSession()
        self._lock = Lock()

    def open_document(self, pdf_path: Path, output_dir: Path | None = None) -> SessionSnapshot:
        """Load a PDF and reset the sequential split session."""
        info = self._pdf_service.open_document(pdf_path, output_dir)
        with self._lock:
            self._session.load(info.path, info.total_pages, info.output_dir)
            return self._session.snapshot()

    def set_output_dir(self, output_dir: Path) -> SessionSnapshot:
        """Change the save destination for subsequent splits."""
        resolved_dir = output_dir.resolve()
        resolved_dir.mkdir(parents=True, exist_ok=True)
        with self._lock:
            self._session.set_output_dir(resolved_dir)
            return self._session.snapshot()

    def snapshot(self) -> SessionSnapshot:
        """Return the latest session snapshot."""
        with self._lock:
            return self._session.snapshot()

    def page_states(self) -> list[PageVisualState]:
        """Return visual states for all pages in the active document."""
        snapshot = self.snapshot()
        return [self.page_state(page_index) for page_index in range(snapshot.total_pages)]

    def page_state(self, page_index: int) -> PageVisualState:
        """Return the visual state for a single page."""
        with self._lock:
            return self._session.page_state(page_index)

    def render_thumbnail(self, page_index: int, max_size: tuple[int, int]) -> Image.Image:
        """Render one page into a PIL image thumbnail."""
        snapshot = self.snapshot()
        if snapshot.source_path is None:
            raise DocumentNotLoadedError(
                "먼저 PDF를 열어 주세요.",
                message_code="error.document_not_loaded",
            )

        return self._pdf_service.render_thumbnail(snapshot.source_path, page_index, max_size)

    def preview_split_to_page(self, selected_page: int) -> SplitPreview:
        """Build a preview for the next sequential split without saving it."""
        with self._lock:
            plan = self._session.build_plan(selected_page)
            snapshot = self._session.snapshot()

        if snapshot.source_path is None or snapshot.output_dir is None:
            raise DocumentNotLoadedError(
                "먼저 PDF를 열어 주세요.",
                message_code="error.document_not_loaded",
            )

        output_path = self._pdf_service.preview_output_path(
            pdf_path=snapshot.source_path,
            output_dir=snapshot.output_dir,
            part_number=plan.part_number,
        )
        return SplitPreview(plan=plan, output_path=output_path, snapshot=snapshot)

    def split_to_page(self, selected_page: int) -> SavedSegment:
        """Save the next sequential PDF segment ending at the selected page."""
        with self._lock:
            plan = self._session.build_plan(selected_page)
            snapshot = self._session.snapshot()

        if snapshot.source_path is None or snapshot.output_dir is None:
            raise DocumentNotLoadedError(
                "먼저 PDF를 열어 주세요.",
                message_code="error.document_not_loaded",
            )

        saved_path = self._pdf_service.save_segment(
            pdf_path=snapshot.source_path,
            start_page=plan.start_page,
            end_page=plan.end_page,
            output_dir=snapshot.output_dir,
            part_number=plan.part_number,
        )

        with self._lock:
            self._session.mark_saved(plan)
            return SavedSegment(plan=plan, file_path=saved_path, snapshot=self._session.snapshot())

    def preview_selected_pages(self, selected_pages: Collection[int]) -> SelectedPagesPreview:
        """Build a preview for exporting only the selected pages."""
        snapshot = self.snapshot()
        if snapshot.source_path is None or snapshot.output_dir is None:
            raise DocumentNotLoadedError(
                "먼저 PDF를 열어 주세요.",
                message_code="error.document_not_loaded",
            )

        page_indexes = self._normalize_selected_pages(selected_pages, snapshot.total_pages)
        output_path = self._pdf_service.preview_selected_pages_output_path(
            pdf_path=snapshot.source_path,
            output_dir=snapshot.output_dir,
        )
        return SelectedPagesPreview(
            page_indexes=page_indexes,
            output_path=output_path,
            snapshot=snapshot,
        )

    def export_selected_pages(self, selected_pages: Collection[int]) -> ExportedPages:
        """Export only the selected pages without mutating split progress."""
        snapshot = self.snapshot()
        if snapshot.source_path is None or snapshot.output_dir is None:
            raise DocumentNotLoadedError(
                "먼저 PDF를 열어 주세요.",
                message_code="error.document_not_loaded",
            )

        page_indexes = self._normalize_selected_pages(selected_pages, snapshot.total_pages)
        saved_path = self._pdf_service.save_selected_pages(
            pdf_path=snapshot.source_path,
            page_indexes=page_indexes,
            output_dir=snapshot.output_dir,
        )
        return ExportedPages(
            page_indexes=page_indexes,
            file_path=saved_path,
            snapshot=self.snapshot(),
        )

    @staticmethod
    def _normalize_selected_pages(
        selected_pages: Collection[int],
        total_pages: int,
    ) -> tuple[int, ...]:
        """Return sorted unique page indexes for selected-pages export."""
        if not selected_pages:
            raise PageSelectionError(
                "내보낼 페이지를 하나 이상 선택해 주세요.",
                message_code="error.no_pages_selected",
            )

        page_indexes = tuple(sorted(set(selected_pages)))
        if any(page_index < 0 or page_index >= total_pages for page_index in page_indexes):
            raise PageSelectionError(
                f"선택 가능한 페이지는 0부터 {total_pages - 1}까지입니다.",
                message_code="error.invalid_selection_range",
                message_values={"last_page": total_pages - 1},
            )
        return page_indexes
