"""UI localization helpers."""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class UiLanguage(StrEnum):
    """Supported UI languages."""

    ENGLISH = "en"
    KOREAN = "ko"


DEFAULT_LANGUAGE = UiLanguage.ENGLISH
LANGUAGE_LABELS: dict[UiLanguage, str] = {
    UiLanguage.ENGLISH: "English",
    UiLanguage.KOREAN: "한국어",
}

_TRANSLATIONS: dict[UiLanguage, dict[str, str]] = {
    UiLanguage.ENGLISH: {
        "app.title": "PDF Splitter",
        "app.window_title": "j3PdfSplit",
        "about.close": "Close",
        "about.copyright": "{copyright_notice}",
        "about.gpl_distribution": (
            "This program is distributed under the GPL-3.0-or-later license."
        ),
        "about.license_path": "Full license text: {license_file}",
        "about.licenses": "Licenses",
        "about.project_license": "Project license: {license_name}",
        "about.source_code": "Source code: {source_url}",
        "about.title": "About j3PdfSplit",
        "about.version": "Version {version}",
        "button.export": "Export",
        "button.open_pdf": "Open PDF",
        "button.select_output_dir": "Choose output folder",
        "dialog.all_filetype": "All files",
        "dialog.output_folder_title": "Choose output folder",
        "dialog.pdf_filetype": "PDF files",
        "dialog.select_pdf_title": "Select PDF",
        "dialog.selected_pages_preview": (
            "Export the selected pages?\n\n"
            "Selected pages: {page_ranges}\n"
            "Page count: {page_count}\n"
            "Expected filename: {filename}\n"
            "Output folder: {folder}"
        ),
        "dialog.split_preview": (
            "Save this range?\n\n"
            "File number: {part_number}\n"
            "Page range: {start_page}~{end_page}\n"
            "Page count: {page_count}\n"
            "Expected filename: {filename}\n"
            "Output folder: {folder}"
        ),
        "error.already_saved_until": (
            "Pages through {completed_page} have already been saved. "
            "Select page {next_start_page} or later."
        ),
        "error.document_complete": "All pages have been split.",
        "error.document_not_loaded": "Open a PDF first.",
        "error.drop_pdf_required": "Drop a PDF file.",
        "error.empty_pdf_open": "PDFs without pages cannot be opened.",
        "error.empty_pdf_split": "PDFs without pages cannot be split.",
        "error.invalid_page_index": "Invalid page index.",
        "error.invalid_selection_range": "Selectable pages are 0 through {last_page}.",
        "error.no_pages_selected": "Select at least one page to export.",
        "error.open_pdf_failed": "Could not open the PDF.",
        "error.pdf_not_found": "The selected PDF file was not found.",
        "error.pdf_unreadable": "The PDF could not be read. Check whether it is damaged.",
        "error.preview_failed": "Preview failed",
        "error.save_pdf_failed": "Could not save the PDF.",
        "error.save_selected_pages_failed": (
            "Could not save the selected pages. Check file permissions."
        ),
        "error.save_segment_failed": (
            "Could not save pages {start_page}~{end_page}. Check file permissions."
        ),
        "error.selected_pages_export_failed": "Could not export selected pages.",
        "error.selected_pages_preview_failed": (
            "Could not prepare selected-pages export details."
        ),
        "error.split_plan_mismatch": "The saved result does not match the current split plan.",
        "error.split_preview_failed": "Could not prepare split details.",
        "error.thumbnail_failed": "Could not create a thumbnail for page {page_index}.",
        "label.language": "Language",
        "label.mode": "Mode",
        "label.thumbnail_size": "Thumbnail size",
        "licenses.no_warranty": "This program is distributed without warranty.",
        "licenses.notice_item": (
            "{component}\n"
            "Version: {version}\n"
            "License: {license_name}\n"
            "Copyright: {copyright_notice}\n"
            "Source: {source_url}\n"
            "License text or notice file: {license_file}\n"
            "Included in distribution: {distributed}\n"
            "Compliance note: {compliance_note}"
        ),
        "licenses.notice_required": "Notice-required licenses:",
        "licenses.project": "{app_name} is licensed under {license_name}.",
        "licenses.project_file": "Project license file: {license_file}",
        "licenses.source": "Corresponding source code for this binary release:",
        "licenses.third_party": "Third-party notices are included in {notice_file}.",
        "licenses.title": "Licenses",
        "menu.about": "About",
        "menu.file": "File",
        "menu.help": "Help",
        "menu.language": "Language",
        "mode.selected_pages_export": "Selected pages export",
        "mode.sequential_split": "Sequential split",
        "status.export_canceled": "Selected-pages export canceled.",
        "status.exporting_selected": "Exporting selected pages: {page_count}.",
        "status.open_pdf_prompt": "Open a PDF to begin.",
        "status.opening_pdf": "Opening PDF: {filename}",
        "status.output_dir_changed": "Output folder changed.",
        "status.page_selected": "Page {page_index} selected.",
        "status.page_unselected": "Page {page_index} unselected.",
        "status.pdf_file": "Opened PDF: {filename}",
        "status.pdf_file_none": "None",
        "status.progress": "Progress: {progress}",
        "status.save_folder": "Output folder: {folder}",
        "status.save_folder_none": "-",
        "status.saving_split": "Saving pages {start_page}~{end_page}.",
        "status.select_pages_export_prompt": "Select pages, then click Export.",
        "status.selected_pages_exported": (
            "Saved selected pages ({page_ranges}) to {filename}."
        ),
        "status.selected_pages_none": "Selected pages: None",
        "status.selected_pages_summary": "Selected pages: {page_ranges} ({page_count})",
        "status.sequential_prompt": "Click a thumbnail to start sequential splitting.",
        "status.split_canceled": "Split canceled.",
        "status.split_saved": "Saved pages {start_page}~{end_page} to {filename}.",
        "status.thumbnail_scale_changing": (
            "Changing thumbnail size to {scale_percent}%."
        ),
        "status.thumbnail_scale_invalid": (
            "Enter an integer thumbnail size from {min_percent}% to {max_percent}%."
        ),
        "status.thumbnail_scale_set": "Thumbnail size set to {scale_percent}%.",
        "status.next_start": "Next start page: {page}",
        "status.next_start_complete": "Next start page: Complete",
        "status.next_start_none": "Next start page: -",
        "thumbnail.available": "Unsplit",
        "thumbnail.completed": "Saved",
        "thumbnail.current": "Next start",
        "thumbnail.loading": "Loading...",
        "thumbnail.page": "Page {page_index}",
        "thumbnail.preview_failed": "Preview failed",
        "thumbnail.selected_suffix": "Selected",
    },
    UiLanguage.KOREAN: {
        "app.title": "PDF 분할기",
        "app.window_title": "j3PdfSplit",
        "about.close": "닫기",
        "about.copyright": "{copyright_notice}",
        "about.gpl_distribution": (
            "이 프로그램은 GPL-3.0-or-later 라이선스에 따라 배포됩니다."
        ),
        "about.license_path": "라이선스 전문 확인 경로: {license_file}",
        "about.licenses": "라이선스",
        "about.project_license": "프로젝트 라이선스: {license_name}",
        "about.source_code": "소스코드 제공 위치: {source_url}",
        "about.title": "j3PdfSplit 정보",
        "about.version": "버전 {version}",
        "button.export": "내보내기",
        "button.open_pdf": "PDF 열기",
        "button.select_output_dir": "저장 폴더 선택",
        "dialog.all_filetype": "모든 파일",
        "dialog.output_folder_title": "저장 폴더 선택",
        "dialog.pdf_filetype": "PDF 파일",
        "dialog.select_pdf_title": "PDF 선택",
        "dialog.selected_pages_preview": (
            "선택한 페이지만 내보낼까요?\n\n"
            "선택 페이지: {page_ranges}\n"
            "페이지 수: {page_count}\n"
            "예상 파일명: {filename}\n"
            "저장 폴더: {folder}"
        ),
        "dialog.split_preview": (
            "다음 구간을 저장할까요?\n\n"
            "저장 순서: {part_number}번째 파일\n"
            "저장 범위: {start_page}~{end_page}페이지\n"
            "페이지 수: {page_count}\n"
            "예상 파일명: {filename}\n"
            "저장 폴더: {folder}"
        ),
        "error.already_saved_until": (
            "이미 {completed_page}페이지까지 저장했습니다. "
            "{next_start_page}페이지 이상을 선택해 주세요."
        ),
        "error.document_complete": "마지막 페이지까지 모두 분할했습니다.",
        "error.document_not_loaded": "먼저 PDF를 열어 주세요.",
        "error.drop_pdf_required": "PDF 파일을 드롭해 주세요.",
        "error.empty_pdf_open": "페이지가 없는 PDF는 열 수 없습니다.",
        "error.empty_pdf_split": "페이지가 없는 PDF는 분할할 수 없습니다.",
        "error.invalid_page_index": "유효하지 않은 페이지 인덱스입니다.",
        "error.invalid_selection_range": "선택 가능한 페이지는 0부터 {last_page}까지입니다.",
        "error.no_pages_selected": "내보낼 페이지를 하나 이상 선택해 주세요.",
        "error.open_pdf_failed": "PDF를 열지 못했습니다.",
        "error.pdf_not_found": "선택한 PDF 파일을 찾을 수 없습니다.",
        "error.pdf_unreadable": "PDF를 읽을 수 없습니다. 손상 여부를 확인해 주세요.",
        "error.preview_failed": "미리보기 실패",
        "error.save_pdf_failed": "PDF 저장에 실패했습니다.",
        "error.save_selected_pages_failed": (
            "선택한 페이지를 저장하지 못했습니다. 파일 권한을 확인해 주세요."
        ),
        "error.save_segment_failed": (
            "{start_page}~{end_page}페이지를 저장하지 못했습니다. "
            "파일 권한을 확인해 주세요."
        ),
        "error.selected_pages_export_failed": "선택 페이지 내보내기에 실패했습니다.",
        "error.selected_pages_preview_failed": (
            "선택 페이지 내보내기 정보를 준비하지 못했습니다."
        ),
        "error.split_plan_mismatch": "현재 저장 계획과 일치하지 않는 분할 결과입니다.",
        "error.split_preview_failed": "분할 정보를 준비하지 못했습니다.",
        "error.thumbnail_failed": "{page_index}페이지 썸네일을 만들 수 없습니다.",
        "label.language": "언어",
        "label.mode": "모드",
        "label.thumbnail_size": "썸네일 크기",
        "licenses.no_warranty": "이 프로그램은 어떠한 보증 없이 배포됩니다.",
        "licenses.notice_item": (
            "{component}\n"
            "버전: {version}\n"
            "라이선스: {license_name}\n"
            "저작권: {copyright_notice}\n"
            "원본 URL: {source_url}\n"
            "라이선스 전문 또는 고지 파일: {license_file}\n"
            "배포물 포함 여부: {distributed}\n"
            "준수 메모: {compliance_note}"
        ),
        "licenses.notice_required": "고지가 필요한 라이선스:",
        "licenses.project": "{app_name}은 {license_name} 라이선스로 배포됩니다.",
        "licenses.project_file": "프로젝트 라이선스 파일: {license_file}",
        "licenses.source": "이 바이너리 릴리스의 대응 소스 코드:",
        "licenses.third_party": "외부 라이브러리 고지는 {notice_file}에 포함되어 있습니다.",
        "licenses.title": "라이선스",
        "menu.about": "정보",
        "menu.file": "파일",
        "menu.help": "도움말",
        "menu.language": "언어",
        "mode.selected_pages_export": "선택 페이지 내보내기",
        "mode.sequential_split": "순차 분할",
        "status.export_canceled": "선택 페이지 내보내기를 취소했습니다.",
        "status.exporting_selected": "선택한 {page_count}을 내보내는 중입니다.",
        "status.open_pdf_prompt": "PDF를 열어 주세요.",
        "status.opening_pdf": "PDF를 여는 중: {filename}",
        "status.output_dir_changed": "저장 폴더를 변경했습니다.",
        "status.page_selected": "{page_index}페이지를 선택했습니다.",
        "status.page_unselected": "{page_index}페이지 선택을 해제했습니다.",
        "status.pdf_file": "열린 PDF: {filename}",
        "status.pdf_file_none": "없음",
        "status.progress": "진행률: {progress}",
        "status.save_folder": "저장 폴더: {folder}",
        "status.save_folder_none": "-",
        "status.saving_split": "{start_page}~{end_page}페이지 PDF를 저장하는 중입니다.",
        "status.select_pages_export_prompt": "페이지를 선택한 뒤 내보내기를 누르세요.",
        "status.selected_pages_exported": (
            "선택한 페이지({page_ranges})를 {filename}로 저장했습니다."
        ),
        "status.selected_pages_none": "선택 페이지: 없음",
        "status.selected_pages_summary": "선택 페이지: {page_ranges} ({page_count})",
        "status.sequential_prompt": "썸네일을 클릭해 순차 분할을 시작하세요.",
        "status.split_canceled": "분할 저장을 취소했습니다.",
        "status.split_saved": "{start_page}~{end_page}페이지를 {filename}로 저장했습니다.",
        "status.thumbnail_scale_changing": (
            "썸네일 크기를 {scale_percent}%로 변경하는 중입니다."
        ),
        "status.thumbnail_scale_invalid": (
            "썸네일 크기는 {min_percent}%~{max_percent}% 사이 정수로 입력해 주세요."
        ),
        "status.thumbnail_scale_set": "썸네일 크기를 {scale_percent}%로 설정했습니다.",
        "status.next_start": "다음 시작 페이지: {page}",
        "status.next_start_complete": "다음 시작 페이지: 완료",
        "status.next_start_none": "다음 시작 페이지: -",
        "thumbnail.available": "미분할",
        "thumbnail.completed": "저장 완료",
        "thumbnail.current": "다음 시작",
        "thumbnail.loading": "로딩 중...",
        "thumbnail.page": "{page_index}페이지",
        "thumbnail.preview_failed": "미리보기 실패",
        "thumbnail.selected_suffix": "선택됨",
    },
}


def supported_languages() -> tuple[UiLanguage, ...]:
    """Return languages in the order used by language selectors."""
    return (UiLanguage.ENGLISH, UiLanguage.KOREAN)


def language_label(language: UiLanguage) -> str:
    """Return the display label for a language."""
    return LANGUAGE_LABELS[language]


def language_from_label(label: str) -> UiLanguage:
    """Return the language represented by a display label."""
    for language, language_label_text in LANGUAGE_LABELS.items():
        if label == language_label_text:
            return language
    return DEFAULT_LANGUAGE


def page_count_text(language: UiLanguage, page_count: int) -> str:
    """Return a localized page-count phrase."""
    if language == UiLanguage.ENGLISH:
        suffix = "page" if page_count == 1 else "pages"
        return f"{page_count} {suffix}"
    return f"{page_count}장"


def text(language: UiLanguage, key: str, **values: Any) -> str:
    """Return localized text for a key."""
    language_translations = _TRANSLATIONS.get(language, _TRANSLATIONS[DEFAULT_LANGUAGE])
    template = language_translations.get(key)
    if template is None:
        template = _TRANSLATIONS[DEFAULT_LANGUAGE][key]
    return template.format(**values)
