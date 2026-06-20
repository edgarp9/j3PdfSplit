"""PDF I/O implementation using PyMuPDF and pypdf."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from threading import Lock

import fitz
from PIL import Image
from pypdf import PdfReader, PdfWriter

from pdf_splitter.user_messages import UserMessageMixin


class PdfProcessingError(UserMessageMixin, RuntimeError):
    """Base class for PDF processing failures."""


class PdfOpenError(PdfProcessingError):
    """Raised when the source PDF cannot be opened."""


class PdfThumbnailError(PdfProcessingError):
    """Raised when a thumbnail cannot be rendered."""


class PdfSaveError(PdfProcessingError):
    """Raised when a split PDF cannot be written."""


@dataclass(frozen=True)
class PdfDocumentInfo:
    """Basic metadata required to start a split session."""

    path: Path
    total_pages: int
    output_dir: Path


class PdfProcessingService:
    """Perform PDF loading, thumbnail rendering, and segment saving."""

    def __init__(self) -> None:
        # PyMuPDF access is serialized because the library does not support multi-threaded use.
        self._fitz_lock = Lock()

    def open_document(self, pdf_path: Path, output_dir: Path | None = None) -> PdfDocumentInfo:
        """Read metadata from a PDF file and validate it."""
        source_path = Path(pdf_path).expanduser().resolve()
        if not source_path.exists() or not source_path.is_file():
            raise PdfOpenError(
                "선택한 PDF 파일을 찾을 수 없습니다.",
                message_code="error.pdf_not_found",
            )

        try:
            with self._fitz_lock:
                with fitz.open(str(source_path)) as document:
                    total_pages = document.page_count
        except Exception as exc:
            raise PdfOpenError(
                "PDF를 읽을 수 없습니다. 손상 여부를 확인해 주세요.",
                message_code="error.pdf_unreadable",
            ) from exc

        if total_pages <= 0:
            raise PdfOpenError(
                "페이지가 없는 PDF는 열 수 없습니다.",
                message_code="error.empty_pdf_open",
            )

        resolved_output_dir = (output_dir or source_path.parent).expanduser().resolve()
        resolved_output_dir.mkdir(parents=True, exist_ok=True)
        return PdfDocumentInfo(
            path=source_path,
            total_pages=total_pages,
            output_dir=resolved_output_dir,
        )

    def render_thumbnail(
        self,
        pdf_path: Path,
        page_index: int,
        max_size: tuple[int, int],
    ) -> Image.Image:
        """Render one PDF page to a resized PIL image."""
        try:
            with self._fitz_lock:
                with fitz.open(str(Path(pdf_path).expanduser().resolve())) as document:
                    page = document.load_page(page_index)
                    pixmap = page.get_pixmap(
                        matrix=fitz.Matrix(*self._fit_scale(page.rect, max_size)),
                        alpha=False,
                    )
                    image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
        except Exception as exc:
            raise PdfThumbnailError(
                f"{page_index}페이지 썸네일을 만들 수 없습니다.",
                message_code="error.thumbnail_failed",
                message_values={"page_index": page_index},
            ) from exc

        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        return image

    def _fit_scale(self, page_rect: fitz.Rect, max_size: tuple[int, int]) -> tuple[float, float]:
        """Return a scale that renders close to the requested thumbnail size."""
        max_width, max_height = max_size
        width_scale = max_width / max(page_rect.width, 1)
        height_scale = max_height / max(page_rect.height, 1)
        scale = max(min(width_scale, height_scale), 0.1)
        return scale, scale

    def save_segment(
        self,
        pdf_path: Path,
        start_page: int,
        end_page: int,
        output_dir: Path,
        part_number: int,
    ) -> Path:
        """Save an inclusive page range to a new PDF file."""
        output_path = self._build_output_path(pdf_path, output_dir, part_number)
        return self._write_pages(
            pdf_path=pdf_path,
            page_indexes=tuple(range(start_page, end_page + 1)),
            output_path=output_path,
            failure_message=(
                f"{start_page}~{end_page}페이지를 저장하지 못했습니다. "
                "파일 권한을 확인해 주세요."
            ),
            failure_message_code="error.save_segment_failed",
            failure_message_values={"start_page": start_page, "end_page": end_page},
        )

    def save_selected_pages(
        self,
        pdf_path: Path,
        page_indexes: Sequence[int],
        output_dir: Path,
    ) -> Path:
        """Save only the selected pages to a new PDF file."""
        output_path = self._build_selected_pages_output_path(pdf_path, output_dir)
        return self._write_pages(
            pdf_path=pdf_path,
            page_indexes=page_indexes,
            output_path=output_path,
            failure_message="선택한 페이지를 저장하지 못했습니다. 파일 권한을 확인해 주세요.",
            failure_message_code="error.save_selected_pages_failed",
        )

    def _write_pages(
        self,
        pdf_path: Path,
        page_indexes: Sequence[int],
        output_path: Path,
        failure_message: str,
        failure_message_code: str,
        failure_message_values: dict[str, object] | None = None,
    ) -> Path:
        """Write the requested pages to a new PDF file."""
        source_path = Path(pdf_path).expanduser().resolve()

        try:
            with source_path.open("rb") as input_stream, output_path.open("wb") as output_stream:
                reader = PdfReader(input_stream)
                writer = PdfWriter()
                for page_index in page_indexes:
                    writer.add_page(reader.pages[page_index])
                writer.write(output_stream)
        except Exception as exc:
            if output_path.exists():
                output_path.unlink(missing_ok=True)
            raise PdfSaveError(
                failure_message,
                message_code=failure_message_code,
                message_values=failure_message_values,
            ) from exc

        return output_path

    def preview_output_path(self, pdf_path: Path, output_dir: Path, part_number: int) -> Path:
        """Return the next available output path for a pending split."""
        return self._build_output_path(pdf_path, output_dir, part_number)

    def preview_selected_pages_output_path(self, pdf_path: Path, output_dir: Path) -> Path:
        """Return the next available output path for selected-pages export."""
        return self._build_selected_pages_output_path(pdf_path, output_dir)

    def _build_output_path(self, pdf_path: Path, output_dir: Path, part_number: int) -> Path:
        """Create a non-overwriting output path for one split segment."""
        base_name = f"{pdf_path.stem}_{part_number}장"
        return self._build_unique_output_path(output_dir, base_name)

    def _build_selected_pages_output_path(self, pdf_path: Path, output_dir: Path) -> Path:
        """Create a non-overwriting output path for selected-pages export."""
        return self._build_unique_output_path(output_dir, f"{pdf_path.stem}_선택페이지")

    def _build_unique_output_path(self, output_dir: Path, base_name: str) -> Path:
        """Create a non-overwriting path for one generated PDF."""
        candidate = output_dir / f"{base_name}.pdf"
        suffix = 1
        while candidate.exists():
            candidate = output_dir / f"{base_name}({suffix}).pdf"
            suffix += 1
        return candidate
