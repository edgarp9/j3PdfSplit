"""Pure domain models for PDF splitting workflows."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from pdf_splitter.user_messages import UserMessageMixin


class DocumentNotLoadedError(UserMessageMixin, RuntimeError):
    """Raised when an action requires a loaded PDF session."""


class DocumentCompleteError(UserMessageMixin, RuntimeError):
    """Raised when the document has already been fully split."""


class SplitSelectionError(UserMessageMixin, ValueError):
    """Raised when the selected page cannot be used for the next split."""


class PageSelectionError(UserMessageMixin, ValueError):
    """Raised when selected pages cannot be exported."""


class PageVisualState(StrEnum):
    """Visual state of a page thumbnail."""

    COMPLETED = "completed"
    CURRENT = "current"
    AVAILABLE = "available"


@dataclass(frozen=True)
class SplitPlan:
    """Planned inclusive page range for one saved segment."""

    part_number: int
    start_page: int
    end_page: int


@dataclass(frozen=True)
class SessionSnapshot:
    """Immutable UI-friendly snapshot of the split session."""

    source_path: Path | None
    output_dir: Path | None
    total_pages: int
    next_start_page: int
    next_part_number: int

    @property
    def completed_until(self) -> int:
        """Return the last fully saved page index, or -1 if none."""
        return self.next_start_page - 1

    @property
    def is_complete(self) -> bool:
        """Return whether the full document has been split."""
        return self.total_pages > 0 and self.next_start_page >= self.total_pages


class SequentialSplitSession:
    """Track sequential page ranges for one PDF document."""

    def __init__(self) -> None:
        self._source_path: Path | None = None
        self._output_dir: Path | None = None
        self._total_pages = 0
        self._next_start_page = 0
        self._next_part_number = 1

    def load(self, source_path: Path, total_pages: int, output_dir: Path) -> None:
        """Start a new split session for a loaded PDF."""
        if total_pages <= 0:
            raise ValueError("페이지가 없는 PDF는 분할할 수 없습니다.")

        self._source_path = source_path.resolve()
        self._output_dir = output_dir.resolve()
        self._total_pages = total_pages
        self._next_start_page = 0
        self._next_part_number = 1

    def set_output_dir(self, output_dir: Path) -> None:
        """Change the target output directory for future saves."""
        if self._source_path is None:
            raise DocumentNotLoadedError(
                "먼저 PDF를 열어 주세요.",
                message_code="error.document_not_loaded",
            )

        self._output_dir = output_dir.resolve()

    def snapshot(self) -> SessionSnapshot:
        """Return a copy of the current session state."""
        return SessionSnapshot(
            source_path=self._source_path,
            output_dir=self._output_dir,
            total_pages=self._total_pages,
            next_start_page=self._next_start_page,
            next_part_number=self._next_part_number,
        )

    def build_plan(self, selected_page: int) -> SplitPlan:
        """Create a split plan from the current pointer to the selected page."""
        if self._source_path is None:
            raise DocumentNotLoadedError(
                "먼저 PDF를 열어 주세요.",
                message_code="error.document_not_loaded",
            )

        if self._next_start_page >= self._total_pages:
            raise DocumentCompleteError(
                "마지막 페이지까지 모두 분할했습니다.",
                message_code="error.document_complete",
            )

        if selected_page < 0 or selected_page >= self._total_pages:
            raise SplitSelectionError(
                f"선택 가능한 페이지는 0부터 {self._total_pages - 1}까지입니다.",
                message_code="error.invalid_selection_range",
                message_values={"last_page": self._total_pages - 1},
            )

        if selected_page < self._next_start_page:
            raise SplitSelectionError(
                f"이미 {self._next_start_page - 1}페이지까지 저장했습니다. "
                f"{self._next_start_page}페이지 이상을 선택해 주세요.",
                message_code="error.already_saved_until",
                message_values={
                    "completed_page": self._next_start_page - 1,
                    "next_start_page": self._next_start_page,
                },
            )

        return SplitPlan(
            part_number=self._next_part_number,
            start_page=self._next_start_page,
            end_page=selected_page,
        )

    def mark_saved(self, plan: SplitPlan) -> None:
        """Advance the split pointer after a segment has been saved."""
        expected = self.build_plan(plan.end_page)
        if expected != plan:
            raise SplitSelectionError(
                "현재 저장 계획과 일치하지 않는 분할 결과입니다.",
                message_code="error.split_plan_mismatch",
            )

        self._next_start_page = plan.end_page + 1
        self._next_part_number += 1

    def page_state(self, page_index: int) -> PageVisualState:
        """Return the visual state for one page."""
        if page_index < 0 or page_index >= self._total_pages:
            raise IndexError("유효하지 않은 페이지 인덱스입니다.")

        if page_index < self._next_start_page:
            return PageVisualState.COMPLETED

        if page_index == self._next_start_page and self._next_start_page < self._total_pages:
            return PageVisualState.CURRENT

        return PageVisualState.AVAILABLE
