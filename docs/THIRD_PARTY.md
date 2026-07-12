# Third-Party Components

## ExifTool

- Website: https://exiftool.org/
- Local source used for this project: an external local ExifTool 13.50 directory.
- Bundled location: `vendor\exiftool`
- Version checked locally: `13.50`
- License: GPL or Artistic License, as published by ExifTool.
- Usage: runtime metadata reader/writer invoked as a subprocess.
- Distribution notice: the generated EXE/MSI payloads and portable ZIP include ExifTool's own license plus `licenses\Strawberry-Perl-Licenses.zip` for the bundled Strawberry Perl runtime components shipped inside `exiftool_files`.
- Rollback: remove `vendor\exiftool`, then configure the app to use an `exiftool.exe` available on `PATH`.

## PyInstaller

- Website: https://pyinstaller.org/
- Local version checked: `6.20.0`
- License: GPLv2-or-later with a special exception allowing distribution of bundled applications.
- Usage: build-time packaging only.
- Distribution notice: the generated EXE and portable ZIP include `licenses\PyInstaller-COPYING.txt`.
- Rollback: run the app from source with `python -m photo_meta_editor`.

## cx_Freeze

- Website: https://cx-freeze.readthedocs.io/
- Local version checked: `7.2.10`
- License: Python Software Foundation License.
- Usage: build-time MSI packaging via `setup_msi.py bdist_msi`.
- Distribution notice: generated EXE/MSI payloads and portable ZIP include `licenses\cx_Freeze-LICENSE.md`.
- Rollback: keep the PyInstaller portable EXE build and skip MSI generation.

## PowerShell Authenticode Signing

- Website: https://learn.microsoft.com/powershell/module/microsoft.powershell.security/set-authenticodesignature
- Provider: Microsoft PowerShell / Windows certificate store.
- Usage: optional EXE/MSI signing only when an explicit trusted code-signing certificate thumbprint is supplied; unsigned builds remain unsigned.
- Limitation: no signing certificate is bundled; builds remain unsigned unless the publisher explicitly provides a trusted certificate thumbprint.

## tkinterdnd2

- Website: https://github.com/Eliav2/tkinterdnd2
- Local version checked: `0.4.4.1`
- License: MIT.
- Usage: runtime drag-and-drop file import for the Tkinter UI.
- Distribution notice: the generated EXE, MSI payload and portable ZIP include `licenses\tkinterdnd2-LICENSE`.
- Key packaging note: PyInstaller uses the installed tkinterdnd2 hook, then `scripts\prune_runtime_payload.py` keeps only the current Windows tkdnd platform directory.
- Rollback: remove drag-and-drop registration and use the file picker only.

## OCR Backends

- Windows OCR via `winsdk`
  - Website: https://github.com/pywinrt/python-winsdk
  - Local version checked: `1.0.0b10`
  - License: MIT.
  - Usage: optional runtime OCR in source mode if Windows has installed OCR recognizer languages.
  - Packaging note: excluded from the default EXE/MSI to keep distribution size and optional API surface controlled.
- Tesseract OCR
  - Website: https://github.com/tesseract-ocr/tesseract
  - License: Apache-2.0.
  - Usage: optional runtime OCR if `tesseract.exe` is found on `PATH`.
- PaddleOCR
  - Website: https://github.com/PaddlePaddle/PaddleOCR
  - Local version checked: `3.3.2`
  - License: Apache-2.0.
  - Usage: optional runtime OCR only when `paddleocr` is installed and local cached models exist under `.paddlex\official_models`.
  - Packaging note: excluded from the default PyInstaller EXE to keep the app lightweight; source-mode backend only unless a separate OCR bundle is explicitly designed.

OCR is local-only. The app must not download OCR models or call cloud OCR services at runtime.
