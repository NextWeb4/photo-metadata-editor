# AGENTS.md

## 1. Project structure
- Application code lives in `src/photo_meta_editor/`: `app.py` is the Tkinter UI, `exiftool.py` owns ExifTool calls, `fields.py` owns mappings/validation, `metadata.py` owns application identity/version metadata, `ocr.py` owns local OCR detection, and `presets.py`, `i18n.py`, and `settings.py` own their named concerns.
- `vendor/exiftool/` is the bundled runtime. Treat it as third-party content.
- `scripts/` owns EXE/MSI/release packaging, signing, license collection, privacy scanning, runtime pruning, version resources, and path-safety checks. Tests live in `tests/`.

## 2. Run commands
- Install the project in a virtual environment with `.venv\Scripts\python -m pip install -e .`.
- From the repository root, run `$env:PYTHONPATH = "src"; .venv\Scripts\python -m photo_meta_editor`.
- `PHOTO_META_EDITOR_EXIFTOOL` may override ExifTool only in a source development environment; frozen builds must use the bundled executable.

## 3. Test commands
- Run the suite with `$env:PYTHONPATH = "src"; python -m unittest discover -s tests`.
- Add real-file write/read-back coverage when changing tags, date normalization, GPS pairs, QuickTime containers, backup restoration, or ExifTool arguments.

## 4. Build commands
- Build EXE with `powershell -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1`.
- Build MSI with `powershell -ExecutionPolicy Bypass -File .\scripts\build_msi.ps1`.
- Run the complete release pipeline with `powershell -ExecutionPolicy Bypass -File .\scripts\build_release.ps1`.
- Build scripts must retain license collection, privacy scans, path-safety checks, and runtime pruning.

## 5. Code style
- Keep the centered Shields language selector in all three root READMEs with the exact visible labels `English`, `简体中文`, and `日本語`, linked in that order to `README.md`, `README.zh-CN.md`, and `README.ja.md`; do not replace the SVG labels with browser-translatable text.
- Keep the three README versions aligned in section order, facts, commands, paths, links, images, numbers, and code fences; translate headings and prose naturally while preserving identifiers.
- Use typed Python and keep UI, parsing/validation, external-process execution, presets, OCR, and settings in their existing modules.
- User-visible text must remain centralized in `i18n.py`; update Chinese and English strings together.
- Application identity and version values come from `src/photo_meta_editor/metadata.py`, not duplicate literals.
- No lint/format command was found in the current repository; add one before claiming lint or formatter coverage.

## 6. Module boundaries
- UI callbacks may coordinate actions but must not build ExifTool command strings, parse metadata formats, or implement OCR backends.
- All metadata process calls pass structured arguments through `exiftool.py`; keep `-config ""` before `-@ -` and cover Unicode, whitespace, backslash, and multiline inputs.
- `fields.py` owns writable/read-only classification and normalization. Latitude and longitude are one paired invariant and must be written or cleared together.
- Packaging code stays outside runtime application modules.

## 7. Prohibited changes
- Do not overwrite an original media file without the documented backup/restore protections and explicit user action.
- Do not modify, delete, or reformat third-party files under `vendor/exiftool/` as part of application cleanup.
- Do not upload images/metadata, call cloud OCR, download models at runtime, or silently add telemetry.
- Do not package caches, fixtures containing personal media, absolute developer paths, secrets, `release-assets/`, or incomplete third-party notices.
- Do not create self-signed certificates and describe them as trusted signatures.

## 8. Completion criteria
- Run `$env:PYTHONPATH = "src"; python -m unittest discover -s tests` and report the actual result.
- Metadata writes validate the ExifTool summary and read important fields back; `0 image files updated` is an error.
- Restore changes preserve and verify `_before_restore`, detect concurrent file changes, and roll back after failed verification.
- Release changes build the affected artifact, pass privacy and license checks, and verify version/publisher metadata before optional signing.

## 9. Review criteria
- Verify the language selector renders through GitHub without browser-translatable text and all three README versions keep the same facts, commands, links, and images.
- Review original-file safety, backup atomicity, Unicode/space paths, argument construction, time/GPS normalization, and read-back verification first.
- Confirm long-running ExifTool/OCR work cannot block or update a destroyed Tk window and has a timeout/error path.
- Confirm optional OCR remains local and unavailable backends fail clearly without network fallback.
- For packaging changes, inspect recursive-delete/reparse-point protections and verify both artifact privacy and license completeness.

## 10. Common risks
- Write support varies by file format, permissions, and ExifTool tag table; a readable file is not necessarily writable.
- QuickTime GPS/date tags differ from common EXIF mappings and require container-specific tests.
- Frozen builds can omit ExifTool, Tk drag-and-drop files, licenses, or version resources.
- OCR availability depends on local Windows languages, Tesseract, or local model caches and must not be represented as universally available.
