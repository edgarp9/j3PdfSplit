# j3PdfSplit

j3PdfSplit is a small desktop utility for splitting PDF files from a thumbnail-based Tkinter interface.

It is designed for quick internal document handling: open a PDF, inspect its pages as thumbnails, then either split the document sequentially or export selected pages into a new PDF.

<img width="523" height="568" alt="j3PdfSplit" src="https://github.com/user-attachments/assets/aef1e8ea-ffb0-4941-bfd8-b529f86ee27f" />


## Features

- Open a PDF from the file picker or by drag and drop.
- Preview pages as scrollable thumbnails.
- Adjust thumbnail size from the UI.
- Split a PDF sequentially by choosing the end page for each part.
- Export manually selected pages into a separate PDF.
- Choose the output folder before saving.
- Avoid overwriting existing files by generating unique output names.
- Switch the UI language between English and Korean.

## Project Status

This project was created as an in-house tool with assistance from AI.

Test coverage is still limited. Please review the output files carefully before using them for important work, and treat this repository as a practical utility rather than a fully hardened PDF workflow product.

## Requirements

- Python 3.14.3
- Pillow
- PyMuPDF
- pypdf
- tkinterdnd2

The Python dependencies are listed in [src/requirements.txt](src/requirements.txt).

## Installation

From the `src` directory:

```powershell
python -m pip install -e .
```

Or install the runtime dependencies directly:

```powershell
python -m pip install Pillow PyMuPDF pypdf tkinterdnd2
```

## Usage

From the `src` directory:

```powershell
python -m pdf_splitter
```

After editable installation, you can also run:

```powershell
pdf-splitter
```

Basic workflow:

1. Open a PDF file.
2. Choose an output folder if the default folder is not desired.
3. Select either sequential split mode or selected-page export mode.
4. Click thumbnails to define split ranges or select pages.
5. Confirm the save operation when prompted.

## Development Checks

From the `src` directory:

```powershell
python -m compileall .
python -m unittest
ruff check .
```

These checks are useful during development, but they do not replace manual verification of generated PDF files.

## License

This project is distributed under the GNU General Public License v3.0. See [LICENSE](LICENSE).

## Icon Notice

This project uses icons from [Google Fonts Icons](https://fonts.google.com/icons), including Material Symbols. Material Symbols are available under the [Apache License Version 2.0](https://www.apache.org/licenses/LICENSE-2.0).

Thank you to Google Fonts and the Material Symbols team for providing these icons.
