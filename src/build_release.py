from __future__ import annotations

import argparse
import importlib.util
import logging
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

APP_NAME = "j3PdfSplit"
CONTENTS_DIRECTORY_NAME = "lib"
MINIMUM_PYINSTALLER_MAJOR = 6
SUPPORTED_PLATFORMS = {
    "win": "windows",
    "linux": "linux",
}
SPEC_FILES_BY_PLATFORM = {
    "windows": "PdfSplitter.spec",
    "linux": "PdfSplitter.spec",
}
REQUIRED_LIB_PATHS: tuple[str, ...] = (
    "LICENSE",
    "THIRD_PARTY_NOTICES.txt",
    "about.txt",
    "licenses/tkdnd/license.terms",
)
REQUIRED_LIB_GLOBS: tuple[str, ...] = (
    "pillow-*.dist-info/licenses/LICENSE",
    "pymupdf-*.dist-info/COPYING",
    "pypdf-*.dist-info/licenses/LICENSE",
    "tkinterdnd2-*.dist-info/licenses/LICENSE",
    "licenses/python/LICENSE.txt",
    "licenses/tcl-tk/*/license.terms",
)
PYTHON_LICENSE_DEST = Path("licenses/python/LICENSE.txt")
TCL_TK_LICENSE_DEST_DIR = Path("licenses/tcl-tk")

LOGGER = logging.getLogger("build_release")


class BuildConfigurationError(RuntimeError):
    pass


def resolve_platform_name(platform: str | None = None) -> str:
    value = sys.platform if platform is None else platform
    for prefix, name in SUPPORTED_PLATFORMS.items():
        if value.startswith(prefix):
            return name
    raise BuildConfigurationError(
        "이 빌드 스크립트는 Windows와 Linux만 지원합니다. "
        f"현재 플랫폼: {value}"
    )


def ensure_pyinstaller_ready() -> str:
    if importlib.util.find_spec("PyInstaller") is None:
        raise BuildConfigurationError(
            "PyInstaller가 현재 Python 환경에 설치되어 있지 않습니다. "
            "예: python -m pip install pyinstaller"
        )

    import PyInstaller

    version = getattr(PyInstaller, "__version__", "")
    match = re.match(r"(\d+)", version.strip())
    if match is None or int(match.group(1)) < MINIMUM_PYINSTALLER_MAJOR:
        raise BuildConfigurationError(
            "dist/<platform>/<app>/lib/ 레이아웃을 위해 "
            f"PyInstaller {MINIMUM_PYINSTALLER_MAJOR}+ 가 필요합니다. "
            f"현재 버전: {version or 'unknown'}"
        )
    return version


def project_root() -> Path:
    return Path(__file__).resolve().parent


def spec_path(root: Path, platform_name: str) -> Path:
    spec_filename = SPEC_FILES_BY_PLATFORM[platform_name]
    path = root / spec_filename
    if not path.is_file():
        raise BuildConfigurationError(f"spec 파일을 찾을 수 없습니다: {path}")
    return path


def output_paths(root: Path, platform_name: str) -> tuple[Path, Path, Path]:
    bundle_dir = root / "dist" / platform_name / APP_NAME
    support_dir = bundle_dir / CONTENTS_DIRECTORY_NAME
    work_dir = root / "build" / platform_name
    return bundle_dir, support_dir, work_dir


def ensure_within_project(target: Path, root: Path) -> None:
    resolved_target = target.resolve()
    resolved_root = root.resolve()
    try:
        resolved_target.relative_to(resolved_root)
    except ValueError as exc:
        raise BuildConfigurationError(
            f"프로젝트 밖 경로는 정리하지 않습니다: {resolved_target}"
        ) from exc


def remove_tree(target: Path, root: Path) -> None:
    if not target.exists():
        return
    ensure_within_project(target, root)
    shutil.rmtree(target)


def _deduplicate_existing_files(paths: list[Path]) -> tuple[Path, ...]:
    seen: set[Path] = set()
    existing_paths: list[Path] = []
    for path in paths:
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if resolved in seen or not resolved.is_file():
            continue
        seen.add(resolved)
        existing_paths.append(resolved)
    return tuple(existing_paths)


def python_license_candidates() -> tuple[Path, ...]:
    roots = {
        Path(sys.base_prefix),
        Path(sys.base_exec_prefix),
        Path(sys.executable).resolve().parent,
    }
    candidates: list[Path] = []
    for root in roots:
        candidates.extend((root / "LICENSE.txt", root / "LICENSE"))

    if os.name != "nt":
        python_major_minor = f"python{sys.version_info.major}.{sys.version_info.minor}"
        candidates.extend(
            (
                Path("/usr/share/doc") / python_major_minor / "copyright",
                Path("/usr/share/doc") / f"python{sys.version_info.major}" / "copyright",
            )
        )
    return tuple(candidates)


def tcl_tk_license_sources() -> tuple[Path, ...]:
    candidates: list[Path] = []
    try:
        import tkinter

        interpreter = tkinter.Tcl()
        tcl_library = Path(interpreter.eval("info library")).resolve()
        candidates.append(tcl_library / "license.terms")
        candidates.extend(tcl_library.parent.glob("tcl*/license.terms"))
        candidates.extend(tcl_library.parent.glob("tk*/license.terms"))
    except Exception as exc:  # noqa: BLE001
        LOGGER.debug("Tcl/Tk license discovery via tkinter failed: %s", exc)

    bundled_tcl_root = Path(sys.base_prefix) / "tcl"
    if bundled_tcl_root.is_dir():
        candidates.extend(bundled_tcl_root.glob("*/license.terms"))

    return _deduplicate_existing_files(candidates)


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def copy_runtime_license_files(support_dir: Path) -> None:
    python_license_sources = _deduplicate_existing_files(list(python_license_candidates()))
    if not python_license_sources:
        raise BuildConfigurationError(
            "Python 런타임 라이선스 파일을 찾을 수 없습니다. "
            "릴리스 번들에 PSF 라이선스 고지를 포함해야 합니다."
        )
    copy_file(python_license_sources[0], support_dir / PYTHON_LICENSE_DEST)

    tcl_tk_sources = tcl_tk_license_sources()
    if not tcl_tk_sources:
        raise BuildConfigurationError(
            "Tcl/Tk license.terms 파일을 찾을 수 없습니다. "
            "Tkinter 릴리스 번들에 Tcl/Tk 라이선스 고지를 포함해야 합니다."
        )

    for source in tcl_tk_sources:
        destination = support_dir / TCL_TK_LICENSE_DEST_DIR / source.parent.name / source.name
        copy_file(source, destination)


def build_command(
    root: Path,
    platform_name: str,
    spec_file: Path,
    *,
    clean: bool,
    extra_args: list[str],
) -> list[str]:
    _bundle_dir, _support_dir, work_dir = output_paths(root, platform_name)
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--distpath",
        str(root / "dist" / platform_name),
        "--workpath",
        str(work_dir),
    ]
    if clean:
        command.append("--clean")
    command.extend(extra_args)
    command.append(str(spec_file))
    return command


def build_environment() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("TCL_LIBRARY", None)
    env.pop("TK_LIBRARY", None)
    return env


def format_command(command: list[str]) -> str:
    if os.name == "nt":
        return subprocess.list2cmdline(command)
    return shlex.join(command)


def verify_output(root: Path, platform_name: str) -> None:
    bundle_dir, support_dir, _work_dir = output_paths(root, platform_name)
    executable = bundle_dir / (f"{APP_NAME}.exe" if platform_name == "windows" else APP_NAME)
    if not executable.is_file():
        raise BuildConfigurationError(f"실행 파일이 생성되지 않았습니다: {executable}")
    if not support_dir.is_dir():
        raise BuildConfigurationError(f"lib 디렉터리가 생성되지 않았습니다: {support_dir}")
    for relative_path in REQUIRED_LIB_PATHS:
        expected = support_dir / relative_path
        if not expected.exists():
            raise BuildConfigurationError(f"번들 리소스가 누락되었습니다: {expected}")
    for path_pattern in REQUIRED_LIB_GLOBS:
        if not any(support_dir.glob(path_pattern)):
            raise BuildConfigurationError(f"번들 라이선스 파일이 누락되었습니다: {path_pattern}")


def run_release_build(*, clean: bool, dry_run: bool, extra_args: list[str]) -> int:
    root = project_root()
    platform_name = resolve_platform_name()
    version = ensure_pyinstaller_ready()
    spec_file = spec_path(root, platform_name)
    bundle_dir, support_dir, work_dir = output_paths(root, platform_name)
    command = build_command(
        root,
        platform_name,
        spec_file,
        clean=clean,
        extra_args=extra_args,
    )

    LOGGER.info("Platform: %s", platform_name)
    LOGGER.info("PyInstaller: %s", version)
    LOGGER.info("Bundle output: %s", bundle_dir)
    LOGGER.info("Support files: %s", support_dir)
    LOGGER.info("Command: %s", format_command(command))

    if dry_run:
        LOGGER.info("Dry run enabled. Build command was not executed.")
        return 0

    remove_tree(bundle_dir, root)
    remove_tree(work_dir, root)
    subprocess.run(command, check=True, cwd=root, env=build_environment())
    copy_runtime_license_files(support_dir)
    verify_output(root, platform_name)
    LOGGER.info("Build completed: %s", bundle_dir)
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a PyInstaller onedir release bundle with support files in "
            "dist/<platform>/<app>/lib/."
        )
    )
    parser.add_argument("--dry-run", action="store_true", help="빌드 명령만 출력합니다.")
    parser.add_argument(
        "--no-clean",
        dest="clean",
        action="store_false",
        help="PyInstaller clean 옵션을 사용하지 않습니다.",
    )
    parser.add_argument(
        "pyinstaller_args",
        nargs=argparse.REMAINDER,
        help="추가 PyInstaller 인자. 필요하면 '-- <args>' 형태로 전달합니다.",
    )
    parser.set_defaults(clean=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args(argv)
    extra_args = list(args.pyinstaller_args)
    if extra_args[:1] == ["--"]:
        extra_args = extra_args[1:]
    try:
        return run_release_build(
            clean=args.clean,
            dry_run=args.dry_run,
            extra_args=extra_args,
        )
    except BuildConfigurationError as exc:
        LOGGER.error("%s", exc)
        return 2
    except subprocess.CalledProcessError as exc:
        LOGGER.error("PyInstaller 빌드가 실패했습니다. 종료 코드: %s", exc.returncode)
        return exc.returncode or 1
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("예상하지 못한 빌드 오류가 발생했습니다: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
