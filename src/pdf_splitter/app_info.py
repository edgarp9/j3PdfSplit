"""Application metadata shared by UI and packaging-facing code."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version

APP_NAME = "j3PdfSplit"
AUTHOR_URL = "https://github.com/edgarp9"
PACKAGE_NAME = "pdf-sequential-splitter"
PROJECT_URL = "https://github.com/edgarp9/j3PdfSplit"
PROJECT_COPYRIGHT = "Copyright (C) 2026 j3PdfSplit contributors"
PROJECT_LICENSE_NAME = "GPL-3.0-or-later"
PROJECT_LICENSE_URL = f"{PROJECT_URL}/blob/main/LICENSE"
PROJECT_LICENSE_FILE = "LICENSE"
THIRD_PARTY_NOTICES_FILE = "THIRD_PARTY_NOTICES.txt"
ABOUT_FILE = "about.txt"
FALLBACK_VERSION = "0.2.0"


@dataclass(frozen=True, slots=True)
class LicenseNotice:
    """A third-party license entry that should be visible from About."""

    component: str
    version: str
    license_name: str
    copyright_notice: str
    source_url: str
    license_file: str
    distributed: str
    compliance_note: str


NOTICE_REQUIRED_LICENSES: tuple[LicenseNotice, ...] = (
    LicenseNotice(
        component="Pillow",
        version="12.2.0 audited; project requires >=12.2.0",
        license_name="MIT-CMU",
        copyright_notice=(
            "Copyright (C) 1997-2011 Secret Labs AB; "
            "Copyright (C) 1995-2011 Fredrik Lundh and contributors; "
            "Copyright (C) 2010 Jeffrey 'Alex' Clark and contributors"
        ),
        source_url="https://github.com/python-pillow/Pillow",
        license_file="pillow-12.2.0.dist-info/licenses/LICENSE",
        distributed="Yes, runtime dependency; metadata copied into PyInstaller bundles",
        compliance_note="Keep copyright and MIT-CMU license notices with distributions.",
    ),
    LicenseNotice(
        component="PyMuPDF / MuPDF",
        version="PyMuPDF 1.27.2.3 / MuPDF 1.27.2 audited; project requires >=1.27.2.3",
        license_name="GNU AGPL 3.0 or Artifex commercial license; this project uses AGPL",
        copyright_notice="Copyright (C) 2015-2026 Artifex",
        source_url="https://github.com/pymupdf/PyMuPDF",
        license_file=(
            "pymupdf-1.27.2.3.dist-info/COPYING; AGPL text in "
            "THIRD_PARTY_NOTICES.txt"
        ),
        distributed="Yes, runtime dependency; metadata copied into PyInstaller bundles",
        compliance_note=(
            "Provide corresponding source for each binary release and preserve AGPL notices."
        ),
    ),
    LicenseNotice(
        component="pypdf",
        version="6.13.3 audited; project requires >=6.13.3",
        license_name="BSD-3-Clause",
        copyright_notice="Copyright (c) 2006-2008, Mathieu Fenniak and contributors",
        source_url="https://github.com/py-pdf/pypdf",
        license_file="pypdf-6.13.3.dist-info/licenses/LICENSE",
        distributed="Yes, runtime dependency; metadata copied into PyInstaller bundles",
        compliance_note=(
            "Keep copyright, license conditions, disclaimer, and non-endorsement notice."
        ),
    ),
    LicenseNotice(
        component="tkinterdnd2",
        version="0.5.0 audited; project requires >=0.5.0",
        license_name="MIT",
        copyright_notice="Copyright (c) 2020 Philippe Gagne",
        source_url="https://github.com/Eliav2/tkinterdnd2",
        license_file="tkinterdnd2-0.5.0.dist-info/licenses/LICENSE",
        distributed="Yes, runtime dependency; package data copied into PyInstaller bundles",
        compliance_note=(
            "Keep copyright and MIT license notices. Bundled tkDND files have separate terms."
        ),
    ),
    LicenseNotice(
        component="tkDND native extension bundled by tkinterdnd2",
        version="2.9.3, 2.9.4, and 2.9.5 files observed in tkinterdnd2 0.5.0",
        license_name="TCL/TK-style permissive terms",
        copyright_notice=(
            "Copyright Georgios Petasis; Mac portions (c) 2009-2014 "
            "Kevin Walzer/WordTech Communications LLC"
        ),
        source_url="https://github.com/petasis/tkdnd",
        license_file="licenses/tkdnd/license.terms",
        distributed="Yes, as tkinterdnd2 native package data in PyInstaller bundles",
        compliance_note=(
            "Keep licenses/tkdnd/license.terms with source and binary distributions."
        ),
    ),
    LicenseNotice(
        component="Python runtime",
        version="3.14.4 observed in the audit environment",
        license_name="PSF License Version 2 plus incorporated-software notices",
        copyright_notice="Python Software Foundation and other contributors; see runtime license",
        source_url="https://docs.python.org/3/license.html",
        license_file="lib/licenses/python/LICENSE.txt in release bundles",
        distributed="Yes, in PyInstaller binary bundles; not vendored in the source tree",
        compliance_note="Keep the Python runtime license file with binary bundles.",
    ),
    LicenseNotice(
        component="Tcl/Tk runtime",
        version="8.6.x release-time runtime; Tcl 8.6.15 observed",
        license_name="Tcl/Tk license terms",
        copyright_notice=(
            "Copyright Regents of the University of California, Sun Microsystems, Inc., "
            "Scriptics Corporation, and other parties"
        ),
        source_url="https://www.tcl-lang.org/software/tcltk/license.html",
        license_file="lib/licenses/tcl-tk/*/license.terms in release bundles",
        distributed="Yes, in PyInstaller binary bundles when bundled by the interpreter",
        compliance_note="Keep discovered Tcl/Tk license.terms files with binary bundles.",
    ),
    LicenseNotice(
        component="PyInstaller bootloader",
        version="6.21.0 observed",
        license_name="GPL-2.0-or-later with bootloader exception; selected files Apache-2.0",
        copyright_notice=(
            "Copyright (c) 2010-2023 PyInstaller Development Team; "
            "Copyright (c) 2005-2009 Giovanni Bajo; "
            "based on work Copyright (c) 2002 McMillan Enterprises, Inc."
        ),
        source_url="https://github.com/pyinstaller/pyinstaller",
        license_file="pyinstaller-6.21.0.dist-info/licenses/COPYING.txt",
        distributed="Yes, as bootloader in PyInstaller binary bundles",
        compliance_note=(
            "Bootloader exception allows the bundle license, subject to dependency licenses."
        ),
    ),
    LicenseNotice(
        component="setuptools",
        version="82.0.1 observed",
        license_name="MIT",
        copyright_notice="Python Packaging Authority and contributors; see license file",
        source_url="https://github.com/pypa/setuptools",
        license_file="setuptools-82.0.1.dist-info/licenses/LICENSE",
        distributed="No, build-system dependency unless the build environment is redistributed",
        compliance_note="Include notices only if redistributing setuptools or a build image.",
    ),
    LicenseNotice(
        component="PyInstaller build tool",
        version="6.21.0 observed",
        license_name="GPL-2.0-or-later with bootloader exception; selected files Apache-2.0",
        copyright_notice=(
            "Copyright (c) 2010-2023 PyInstaller Development Team; "
            "Copyright (c) 2005-2009 Giovanni Bajo"
        ),
        source_url="https://github.com/pyinstaller/pyinstaller",
        license_file="pyinstaller-6.21.0.dist-info/licenses/COPYING.txt",
        distributed="No, build tool; generated bootloader is distributed in binary bundles",
        compliance_note="Modified PyInstaller code has separate GPL obligations.",
    ),
    LicenseNotice(
        component="altgraph",
        version="0.17.5 observed",
        license_name="MIT",
        copyright_notice=(
            "Copyright (c) 2004 Istvan Albert; Copyright (c) 2006-2010 Bob Ippolito; "
            "Copyright (c) 2010-2020 Ronald Oussoren et al."
        ),
        source_url="https://github.com/ronaldoussoren/altgraph",
        license_file="altgraph-0.17.5.dist-info/LICENSE",
        distributed="No, PyInstaller build dependency unless the build environment is redistributed",
        compliance_note="Include notices only if redistributed.",
    ),
    LicenseNotice(
        component="packaging",
        version="26.2 observed",
        license_name="Apache-2.0 OR BSD-2-Clause",
        copyright_notice="Copyright (c) Donald Stufft and individual contributors",
        source_url="https://github.com/pypa/packaging",
        license_file="packaging-26.2.dist-info/licenses/LICENSE",
        distributed="No, PyInstaller build dependency unless the build environment is redistributed",
        compliance_note="Include Apache/BSD license files only if redistributed.",
    ),
    LicenseNotice(
        component="pefile",
        version="2024.8.26 observed",
        license_name="MIT",
        copyright_notice="Copyright (c) 2004-2024 Ero Carrera",
        source_url="https://github.com/erocarrera/pefile",
        license_file="pefile-2024.8.26.dist-info/LICENSE",
        distributed="No, Windows PyInstaller build dependency unless redistributed",
        compliance_note="Include notices only if redistributed.",
    ),
    LicenseNotice(
        component="pyinstaller-hooks-contrib",
        version="2026.6 observed",
        license_name="GPL-2.0-or-later for standard hooks; Apache-2.0 for runtime hooks",
        copyright_notice="PyInstaller Community Hooks contributors; see license file",
        source_url="https://github.com/pyinstaller/pyinstaller-hooks-contrib",
        license_file="pyinstaller_hooks_contrib-2026.6.dist-info/licenses/LICENSE",
        distributed="Usually no; runtime hooks may be bundled depending on final PyInstaller output",
        compliance_note="Confirm final dist output before release if runtime hooks are present.",
    ),
    LicenseNotice(
        component="pywin32-ctypes",
        version="0.2.3 observed",
        license_name="BSD-3-Clause",
        copyright_notice="Copyright (c) 2014, Enthought, Inc.",
        source_url="https://github.com/enthought/pywin32-ctypes",
        license_file="pywin32_ctypes-0.2.3.dist-info/LICENSE.txt",
        distributed="No, Windows PyInstaller build dependency unless redistributed",
        compliance_note="Include BSD-3-Clause notice only if redistributed.",
    ),
)


def app_version() -> str:
    """Return the installed package version, or the source-tree fallback."""
    try:
        return version(PACKAGE_NAME)
    except PackageNotFoundError:
        return FALLBACK_VERSION


def corresponding_source_url() -> str:
    """Return the public source repository URL for source-code access."""
    return PROJECT_URL


def default_about_text() -> str:
    """Return built-in About text used when about.txt cannot be read."""
    return (
        f"{APP_NAME}\n\n"
        f"Version: {app_version()}\n"
        f"Copyright: {PROJECT_COPYRIGHT}\n"
        "License: GNU General Public License v3.0 or later (GPL-3.0-or-later)\n\n"
        "License\n"
        "-------\n\n"
        "This program is free software: you can redistribute it and/or modify it under\n"
        "the terms of the GNU General Public License as published by the Free Software\n"
        "Foundation, either version 3 of the License, or (at your option) any later\n"
        "version.\n\n"
        "This program is distributed in the hope that it will be useful, but WITHOUT ANY\n"
        "WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A\n"
        "PARTICULAR PURPOSE. See the GNU General Public License for more details.\n\n"
        f"Full license text:\n{PROJECT_LICENSE_FILE}\n\n"
        "Source Code\n"
        "-----------\n\n"
        f"Source code for this release:\n{corresponding_source_url()}\n\n"
        "Third-Party Notices\n"
        "-------------------\n\n"
        "This program uses third-party open source components. Their licenses,\n"
        "copyright notices, source URLs, and required notices are listed in:\n\n"
        f"{THIRD_PARTY_NOTICES_FILE}\n\n"
        "Release Files\n"
        "-------------\n\n"
        "The source and binary distributions for this release should include:\n\n"
        f"- {PROJECT_LICENSE_FILE}\n"
        f"- {THIRD_PARTY_NOTICES_FILE}\n"
        f"- {ABOUT_FILE}\n"
    )
