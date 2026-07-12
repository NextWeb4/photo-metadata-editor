from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from photo_meta_editor.metadata import (  # noqa: E402
    APP_COPYRIGHT,
    APP_CREATOR,
    APP_DESCRIPTION,
    APP_EMAIL,
    APP_NAME,
    APP_VERSION,
    APP_WEBSITE,
)


def version_tuple(version: str) -> tuple[int, int, int, int]:
    parts = [int(part) for part in version.split(".")]
    return tuple((parts + [0, 0, 0, 0])[:4])  # type: ignore[return-value]


def render_version_info() -> str:
    version = version_tuple(APP_VERSION)
    version_text = ".".join(str(part) for part in version)
    comments = f"Creator: {APP_CREATOR}; Email: {APP_EMAIL}; Website: {APP_WEBSITE}"
    return f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={version},
    prodvers={version},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', {APP_CREATOR!r}),
          StringStruct('FileDescription', {APP_NAME!r}),
          StringStruct('FileVersion', {version_text!r}),
          StringStruct('InternalName', 'PhotoMetaEditor'),
          StringStruct('LegalCopyright', {APP_COPYRIGHT!r}),
          StringStruct('OriginalFilename', 'PhotoMetaEditor.exe'),
          StringStruct('ProductName', {APP_NAME!r}),
          StringStruct('ProductVersion', {version_text!r}),
          StringStruct('Comments', {comments!r})
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""


def main() -> int:
    output_path = ROOT / "scripts" / "windows_version_info.txt"
    output_path.write_text(render_version_info(), encoding="utf-8", newline="\n")
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
