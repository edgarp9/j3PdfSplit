# PDF Split Domain Notes

## Terms

- Document: the source PDF opened by the user.
- Sequential split: saves non-overlapping page ranges in order from page `0`.
- Selected-pages export: exports the selected page indexes as one PDF without changing sequential split progress.
- UI language: the language used for labels, buttons, status text, dialogs, and thumbnail status text.
- File menu: the menu that exposes source PDF opening, output folder selection, and selected-pages export commands.
- File chooser: the native dialog used to select a source PDF or output folder.
- File drop: dropping a source PDF file from the OS file manager onto the app window.
- About: a modal window that shows app version information and the author GitHub link.

## Rules

1. Page indexes are zero-based in the document, code, and UI.
2. Sequential split starts at page `0` and advances to the page after the last saved range.
3. Selected-pages export preserves source document order.
4. Selected-pages export is the default UI mode.
5. The UI supports English and Korean, and the default UI language is English.
6. Changing the UI language from the menu updates existing UI text without changing split progress, selected pages, output paths, or saved file naming rules.
7. The About window displays the app version and opens `https://github.com/edgarp9` in the default browser when the link is clicked.
8. File chooser dialogs are owned by the main window so they stay active and in front while modal.
9. The File menu exposes the same Open PDF, output folder selection, and Export actions as the toolbar buttons.
10. Top action buttons are ordered Open PDF, output folder selection, then Export.
11. The main header does not show an app title label; the app name remains in the window title and About window.
12. The main view does not show page-state legend or mode guide labels above the thumbnails.
13. The top header separates primary actions from workflow/view settings: action buttons appear on the first row, and mode plus thumbnail-size controls appear on the second row.
14. The thumbnail-size control keeps the percentage value readable and visually separated from its spinner arrows and percent suffix.
15. Dropping a PDF file onto the app window opens it through the same workflow as the Open PDF action.
16. If a drop contains multiple files, the first file with a `.pdf` extension is opened.
