from __future__ import annotations

import importlib.metadata
from pathlib import Path
import shutil

try:
    from scripts.path_safety import assert_no_reparse_points, assert_resolved_under_root
except ModuleNotFoundError:  # Running as python scripts/collect_licenses.py
    from path_safety import assert_no_reparse_points, assert_resolved_under_root


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "build" / "licenses"


def assert_under_root(path: Path) -> None:
    assert_resolved_under_root(path, ROOT, "modify")


def copy_if_exists(source: Path, target_name: str) -> bool:
    if source.is_file():
        shutil.copy2(source, OUTPUT_DIR / target_name)
        return True
    return False


def copy_required(source: Path, target_name: str) -> None:
    if not copy_if_exists(source, target_name):
        raise FileNotFoundError(f"Required license file is missing: {source}")


def copy_distribution_license(distribution_name: str, target_name: str) -> None:
    try:
        distribution = importlib.metadata.distribution(distribution_name)
    except importlib.metadata.PackageNotFoundError:
        raise FileNotFoundError(f"Required {distribution_name} package metadata is missing; cannot collect its license.") from None

    candidates = [
        file
        for file in distribution.files or ()
        if "license" in file.name.casefold() or "copying" in file.name.casefold()
    ]
    candidates.sort(key=lambda file: (".dist-info/" not in str(file).replace("\\", "/").casefold(), str(file).casefold()))
    for file in candidates:
        if copy_if_exists(Path(distribution.locate_file(file)), target_name):
            return
    raise FileNotFoundError(f"Required {distribution_name} license file was not found in package metadata.")


def collect_licenses() -> Path:
    assert_under_root(OUTPUT_DIR)
    if OUTPUT_DIR.exists():
        assert_no_reparse_points(OUTPUT_DIR)
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    copy_required(ROOT / "LICENSE", "PROJECT-LICENSE.txt")
    copy_required(ROOT / "docs" / "THIRD_PARTY.md", "THIRD_PARTY.md")
    copy_required(ROOT / "vendor" / "exiftool" / "exiftool_files" / "LICENSE", "ExifTool-Windows-LICENSE.txt")
    copy_required(ROOT / "vendor" / "exiftool" / "exiftool_files" / "readme_windows.txt", "ExifTool-Windows-README.txt")
    copy_required(
        ROOT / "vendor" / "exiftool" / "exiftool_files" / "Licenses_Strawberry_Perl.zip",
        "Strawberry-Perl-Licenses.zip",
    )

    copy_distribution_license("PyInstaller", "PyInstaller-COPYING.txt")
    copy_distribution_license("cx_Freeze", "cx_Freeze-LICENSE.md")
    copy_distribution_license("tkinterdnd2", "tkinterdnd2-LICENSE")

    return OUTPUT_DIR


def main() -> int:
    output_dir = collect_licenses()
    print(f"Collected licenses in {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
