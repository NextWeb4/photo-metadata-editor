<p align="center">
  <a href="README.md"><img src="https://img.shields.io/badge/English-0969da?style=flat-square" alt="English"></a>
  <a href="README.zh-CN.md"><img src="https://img.shields.io/badge/%E7%AE%80%E4%BD%93%E4%B8%AD%E6%96%87-c8102e?style=flat-square" alt="简体中文"></a>
  <a href="README.ja.md"><img src="https://img.shields.io/badge/%E6%97%A5%E6%9C%AC%E8%AA%9E-8250df?style=flat-square" alt="日本語"></a>
</p>

# Photo Metadata Editor

An offline Windows desktop editor for EXIF, XMP, IPTC, and QuickTime metadata, powered by a bundled ExifTool runtime.

[![Last commit](https://img.shields.io/github/last-commit/NextWeb4/photo-metadata-editor?style=flat-square)](https://github.com/NextWeb4/photo-metadata-editor/commits/main)
[![Repository size](https://img.shields.io/github/repo-size/NextWeb4/photo-metadata-editor?style=flat-square)](https://github.com/NextWeb4/photo-metadata-editor)
[![GitHub stars](https://img.shields.io/github/stars/NextWeb4/photo-metadata-editor?style=flat-square)](https://github.com/NextWeb4/photo-metadata-editor)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)
[![MIT License](https://img.shields.io/github/license/NextWeb4/photo-metadata-editor?style=flat-square)](LICENSE)

## Features

- Opens common media formats including JPG, PNG, TIFF, HEIC, HEIF, WEBP, MOV, and MP4.
- Edits titles, descriptions, keywords, creators, copyright, capture time, camera, software, GPS, and location fields.
- Shows read-only facts such as format, dimensions, megapixels, lens, ISO, focal length, aperture, and shutter speed.
- Provides camera and GPS presets, a dark theme, local OCR date detection, and optional file-time synchronization.
- Switches between Chinese and English and stores the preference in `%APPDATA%\PhotoMetadataEditor\settings.json`.
- Keeps ExifTool `_original` backups by default and creates a checked `_before_restore` copy before restoration.
- Verifies ExifTool's write summary and reads important fields back instead of treating a zero exit code as proof of success.
- Processes files locally; it does not upload photos or metadata and does not download OCR models at runtime.

## Requirements and Compatibility

- **Operating system:** the bundled ExifTool runtime, drag-and-drop desktop application, packaging scripts, and MSI target Windows.
- **Python:** `pyproject.toml` requires Python 3.11 or newer and declares `tkinterdnd2` as the desktop dependency.
- **ExifTool:** source and packaged runs depend on the checked-in Windows runtime under `vendor/exiftool/`; frozen builds do not substitute an executable from `PATH`.
- **Optional OCR:** availability depends on local Windows OCR languages, Tesseract, or locally installed PaddleOCR resources. The project provides no cloud fallback and performs no runtime model download.
- **Media writes:** a format being readable does not guarantee that every tag is writable. Container support, filesystem permissions, and ExifTool's tag tables still apply.

## Install a Release

Download the release artifacts from [GitHub Releases](https://github.com/NextWeb4/photo-metadata-editor/releases):

- `PhotoMetadataEditor-0.1.2-win64.msi`: Windows installer.
- `PhotoMetaEditor-portable.zip`: portable distribution; extract every file and run `PhotoMetaEditor.exe`.
- `SHA256SUMS.txt`: checksums for release files.

Do not download `PhotoMetaEditor.exe` by itself: it requires the adjacent `_internal` and `exiftool` payload from the portable ZIP. Public artifacts are unsigned when no trusted code-signing certificate is configured, so Windows may show an unknown-publisher warning. Verify the SHA-256 checksum before running a downloaded package.

## Run From Source

Python 3.11 or newer is declared in `pyproject.toml`. The desktop dependency is `tkinterdnd2`; the required ExifTool Windows runtime is checked into `vendor/exiftool/`.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e .
$env:PYTHONPATH = "src"
.venv\Scripts\python -m photo_meta_editor
```

OCR support is optional. Available local backends depend on the source environment and installed Windows OCR/Tesseract/PaddleOCR resources. The application must not fetch models or send images to a cloud OCR service.

## Use the Editor

1. Select a file or drag an image/video into the window.
2. Edit supported fields on the left and inspect or filter raw metadata on the right.
3. Optionally apply a camera/GPS preset, detect a date with a local OCR backend, or enable file-time synchronization.
4. Choose **Save changes**. The first write keeps an `_original` backup by default.
5. Use **Restore backup** only after reviewing the confirmation prompt.

The application supports many media containers, but actual write support also depends on the file, its permissions, and ExifTool's capabilities. A successful write is reported only after summary and read-back checks pass.

## Write and Restore Safety

- Normal writes keep ExifTool's `_original` backup unless the user explicitly changes that behavior.
- Restoration first creates and verifies a `_before_restore` copy, detects concurrent file changes, and rolls back after failed verification.
- GPS latitude and longitude form one value pair; changes must write or clear both together rather than leave a half-updated location.
- ExifTool arguments are passed as structured input. Unicode paths, whitespace, backslashes, and multiline values must remain data rather than command syntax.
- A zero process exit code is insufficient when ExifTool reports `0 image files updated`; the application verifies the summary and reads important fields back.

## Project Structure

| Path | Responsibility |
| --- | --- |
| `src/photo_meta_editor/app.py` | Tkinter interface and application coordination |
| `src/photo_meta_editor/exiftool.py` | Safe ExifTool process invocation and read/write handling |
| `src/photo_meta_editor/fields.py` | Field/tag mapping, normalization, and validation |
| `src/photo_meta_editor/metadata.py` | Application identity and version metadata |
| `src/photo_meta_editor/ocr.py` | Local OCR backend detection and date parsing |
| `src/photo_meta_editor/presets.py` | Camera and GPS presets |
| `src/photo_meta_editor/i18n.py` | Chinese and English UI strings |
| `src/photo_meta_editor/settings.py` | Local application preferences |
| `vendor/exiftool/` | Bundled ExifTool Windows runtime |
| `scripts/` | Packaging, signing, license collection, privacy checks, and path safety |
| `tests/` | Standard-library `unittest` regression suite |

## Test

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests
```

## Build

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_release.ps1
```

The release build performs compilation checks, unit tests, EXE/MSI/ZIP packaging, third-party license validation, and privacy scans. Its documented outputs are:

- `dist\PhotoMetaEditor\PhotoMetaEditor.exe`
- `dist\PhotoMetadataEditor-0.1.2-win64.msi`
- `dist\PhotoMetaEditor-portable.zip`

A publisher with a trusted certificate may set `PHOTO_META_EDITOR_SIGNING_CERT_THUMBPRINT`. When it is unset, artifacts must remain unsigned; the build does not create a self-signed certificate to imitate trusted signing.

## Privacy and Distribution

- Do not add background uploads, telemetry, cloud OCR, or runtime model downloads.
- Frozen EXE/MSI builds must use the bundled ExifTool rather than a user-controlled binary from `PATH` or `PHOTO_META_EDITOR_EXIFTOOL`.
- Distribution packages must include the collected project and third-party notices.
- Packaging privacy checks cover local paths and development artifacts; a privacy scan does not replace license-completeness checks.

See [`docs/THIRD_PARTY.md`](docs/THIRD_PARTY.md) and [`docs/OPEN_SOURCE_AUDIT.md`](docs/OPEN_SOURCE_AUDIT.md) for the repository's detailed dependency record.

## Project Status and Limitations

- This is an active, public Windows application with documented version 0.1.2 MSI and portable release artifacts.
- OCR is optional and local; an unavailable backend fails as unavailable rather than silently switching to a network service.
- Read and write coverage varies across still-image and QuickTime containers, especially for GPS and date tags.
- Published artifacts remain unsigned when no trusted certificate is configured. SHA-256 checks verify content integrity but not publisher identity.
- The repository includes a third-party ExifTool runtime. Project MIT licensing does not replace its notices or the licenses of packaged components.

## Contributing

Keep Tkinter coordination in `app.py`, process invocation in `exiftool.py`, field rules in `fields.py`, OCR detection in `ocr.py`, and packaging logic under `scripts/`. Add real-file regression coverage for tag, time, GPS, QuickTime, backup, or argument changes; then run the complete `unittest` suite. Packaging work must retain path-safety, privacy, runtime-pruning, and license-collection checks. No lint or formatter command is currently declared.

## Author

- [HaoXiang Huang](https://nextweb4.github.io/)
- [didadida1688@gmail.com](mailto:didadida1688@gmail.com)

## License

The project source is released under the [MIT License](LICENSE). Bundled components, including ExifTool and its Windows runtime, retain their own licenses; preserve all accompanying notices when redistributing the application.
