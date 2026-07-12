from __future__ import annotations

import argparse
import io
import os
from pathlib import Path
import sys
import tempfile
import zipfile

try:
    from PyInstaller.archive.readers import ArchiveReadError, CArchiveReader, ZlibArchiveReader
except ImportError:  # PyInstaller is only required when release artifacts are scanned.
    ArchiveReadError = RuntimeError
    CArchiveReader = None  # type: ignore[assignment,misc]
    ZlibArchiveReader = None  # type: ignore[assignment,misc]


STATIC_PRIVATE_MARKERS = (
    "C:\\Users\\Example\\PrivateWorkspace",
    "C:/Users/Example/PrivateWorkspace",
    ".codex\\attachments",
    ".codex/attachments",
    "codex-clipboard",
)
MARKER_ENCODINGS = ("utf-8", "utf-16le", "utf-16be")
ROOT = Path(__file__).resolve().parents[1]
MAX_NESTED_ARCHIVE_DEPTH = 3
PYINSTALLER_CARCHIVE_COOKIE = b"MEI\x0c\x0b\x0a\x0b\x0e"


def private_markers() -> tuple[str, ...]:
    markers: list[str] = list(STATIC_PRIVATE_MARKERS)
    project_root = str(ROOT.resolve())
    markers.append(project_root)
    markers.append(project_root.replace("\\", "/"))
    for env_name in ("USERPROFILE", "TEMP", "TMP"):
        value = os.environ.get(env_name, "").strip()
        if not value:
            continue
        markers.append(value)
        markers.append(value.replace("\\", "/"))
    return tuple(dict.fromkeys(markers))


def iter_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(path)
        if path.is_file():
            files.append(path)
        else:
            files.extend(child for child in path.rglob("*") if child.is_file())
    return files


def marker_variants() -> tuple[tuple[str, bytes], ...]:
    variants: list[tuple[str, bytes]] = []
    seen: set[bytes] = set()
    for marker in private_markers():
        for encoding in MARKER_ENCODINGS:
            encoded = marker.encode(encoding)
            if encoded not in seen:
                seen.add(encoded)
                variants.append((marker, encoded))
    return tuple(variants)

def scan_bytes(data: bytes) -> list[str]:
    matches: list[str] = []
    seen: set[str] = set()
    decoded_text: dict[str, str] = {}
    for marker, encoded in marker_variants():
        if marker in seen:
            continue
        if encoded in data or marker_matches_case_insensitive(data, marker, decoded_text):
            matches.append(marker)
            seen.add(marker)
    return matches


def marker_matches_case_insensitive(data: bytes, marker: str, decoded_text: dict[str, str]) -> bool:
    marker_folded = marker.casefold()
    for encoding in MARKER_ENCODINGS:
        if encoding not in decoded_text:
            decoded_text[encoding] = data.decode(encoding, errors="ignore").casefold()
        if folded_marker_in_text(decoded_text[encoding], marker_folded):
            return True
    return False


def folded_marker_in_text(text: str, marker: str) -> bool:
    if not any(separator in marker for separator in ("\\", "/", ":")):
        return marker in text
    start = 0
    while True:
        index = text.find(marker, start)
        if index < 0:
            return False
        end = index + len(marker)
        if end >= len(text) or not text[end].isalnum():
            return True
        start = index + 1


def scan_file(path: Path, display_name: str | None = None) -> list[tuple[str, list[str]]]:
    findings: list[tuple[str, list[str]]] = []
    name_to_scan = display_name or path.name
    name_matches = scan_bytes(name_to_scan.encode("utf-8", errors="surrogateescape"))
    if name_matches:
        findings.append((str(path), name_matches))

    data = path.read_bytes()
    findings.extend(scan_embedded_bytes(str(path), data))

    if path.suffix.casefold() == ".msi":
        findings.extend(scan_msi_payload(path))

    return findings


def scan_embedded_bytes(location: str, data: bytes, depth: int = 0) -> list[tuple[str, list[str]]]:
    findings: list[tuple[str, list[str]]] = []
    matches = scan_bytes(data)
    if matches:
        findings.append((location, matches))

    if Path(location.rsplit("!", 1)[-1]).suffix.casefold() == ".exe":
        findings.extend(scan_pyinstaller_archive_bytes(location, data, require_reader=PYINSTALLER_CARCHIVE_COOKIE in data))

    archive_file = io.BytesIO(data)
    if not zipfile.is_zipfile(archive_file):
        return findings
    if depth >= MAX_NESTED_ARCHIVE_DEPTH:
        raise RuntimeError(f"Archive nesting exceeds {MAX_NESTED_ARCHIVE_DEPTH} levels: {location}")
    with zipfile.ZipFile(archive_file) as archive:
        for info in archive.infolist():
            entry_location = f"{location}!{info.filename}"
            name_matches = scan_bytes(info.filename.encode("utf-8", errors="surrogateescape"))
            if name_matches:
                findings.append((entry_location, name_matches))
            if info.is_dir():
                continue
            findings.extend(scan_embedded_bytes(entry_location, archive.read(info), depth + 1))
    return findings


def scan_pyinstaller_archive(path: Path, require_reader: bool | None = None) -> list[tuple[str, list[str]]]:
    if require_reader is None:
        require_reader = PYINSTALLER_CARCHIVE_COOKIE in path.read_bytes()
    return _scan_pyinstaller_archive(path, str(path), require_reader)


def scan_pyinstaller_archive_bytes(
    location: str,
    data: bytes,
    require_reader: bool = False,
) -> list[tuple[str, list[str]]]:
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as temporary_file:
            temporary_file.write(data)
            temporary_path = Path(temporary_file.name)
        return _scan_pyinstaller_archive(
            temporary_path,
            location,
            require_reader,
        )
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _scan_pyinstaller_archive(path: Path, location_prefix: str, require_reader: bool) -> list[tuple[str, list[str]]]:
    if CArchiveReader is None or ZlibArchiveReader is None:
        if require_reader:
            raise RuntimeError("PyInstaller archive reader is unavailable; cannot deeply scan PhotoMetaEditor.exe.")
        return []

    try:
        archive = CArchiveReader(str(path))
    except ArchiveReadError as exc:
        if not require_reader and "COOKIE magic" in str(exc):
            return []
        raise RuntimeError(f"Unable to inspect PyInstaller archive: {path}") from exc

    findings: list[tuple[str, list[str]]] = []
    for name in sorted(archive.toc):
        location = f"{location_prefix}!pyinstaller/{name}"
        name_matches = scan_bytes(name.encode("utf-8", errors="surrogateescape"))
        if name_matches:
            findings.append((location, name_matches))
        data = archive.extract(name)
        findings.extend(scan_embedded_bytes(location, data))
        if name.casefold().endswith(".pyz"):
            findings.extend(scan_pyinstaller_pyz(location, data))
    return findings


def scan_pyinstaller_pyz(location: str, data: bytes) -> list[tuple[str, list[str]]]:
    if ZlibArchiveReader is None:
        raise RuntimeError("PyInstaller PYZ reader is unavailable.")
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pyz", delete=False) as temporary_file:
            temporary_file.write(data)
            temporary_path = Path(temporary_file.name)
        archive = ZlibArchiveReader(str(temporary_path))
        findings: list[tuple[str, list[str]]] = []
        for name in sorted(archive.toc):
            entry_location = f"{location}!{name}"
            name_matches = scan_bytes(name.encode("utf-8", errors="surrogateescape"))
            if name_matches:
                findings.append((entry_location, name_matches))
            entry_data = archive.extract(name, raw=True)
            if entry_data is not None:
                findings.extend(scan_embedded_bytes(entry_location, entry_data))
        return findings
    except ArchiveReadError as exc:
        raise RuntimeError(f"Unable to inspect PyInstaller PYZ payload: {location}") from exc
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def scan_msi_payload(path: Path) -> list[tuple[str, list[str]]]:
    payload_root = msi_payload_root()
    if payload_root is None:
        raise RuntimeError(f"MSI payload root is unavailable for deep privacy scan: {path}")
    findings: list[tuple[str, list[str]]] = []
    for file_path in iter_files([payload_root]):
        display_name = relative_display_name(file_path, [payload_root])
        for _location, matches in scan_file(file_path, display_name):
            findings.append((f"{path}!payload/{display_name}", matches))
    return findings


def msi_payload_root() -> Path | None:
    env_value = os.environ.get("PHOTO_META_EDITOR_MSI_PAYLOAD_ROOT", "").strip()
    candidates = [Path(env_value)] if env_value else []
    candidates.append(ROOT / "build" / "cx_freeze" / "PhotoMetaEditor")
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None


def relative_display_name(file_path: Path, roots: list[Path]) -> str:
    resolved_file = file_path.resolve()
    for root in roots:
        resolved_root = root.resolve()
        if resolved_root.is_file() and resolved_file == resolved_root:
            return resolved_file.name
        if resolved_root.is_dir():
            try:
                return str(resolved_file.relative_to(resolved_root))
            except ValueError:
                continue
    return resolved_file.name


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan distributable artifacts for local private paths and sample names.")
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    files = iter_files(args.paths)
    findings: list[tuple[str, list[str]]] = []
    for file_path in files:
        findings.extend(scan_file(file_path, relative_display_name(file_path, args.paths)))

    if findings:
        print("Privacy scan failed. Found local/private markers:", file=sys.stderr)
        for location, matches in findings:
            rendered = ", ".join(matches)
            print(f"- {location}: {rendered}", file=sys.stderr)
        return 1

    print(f"Privacy scan passed for {len(files)} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
