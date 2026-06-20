"""Domain layer for PDF splitting workflows."""

from pdf_splitter.domain.models import (
    DocumentCompleteError,
    DocumentNotLoadedError,
    PageSelectionError,
    PageVisualState,
    SequentialSplitSession,
    SessionSnapshot,
    SplitPlan,
    SplitSelectionError,
)

__all__ = [
    "DocumentCompleteError",
    "DocumentNotLoadedError",
    "PageSelectionError",
    "PageVisualState",
    "SequentialSplitSession",
    "SessionSnapshot",
    "SplitPlan",
    "SplitSelectionError",
]
