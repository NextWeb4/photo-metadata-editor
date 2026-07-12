from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

from .i18n import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES


def settings_path() -> Path:
    app_data = os.environ.get("APPDATA")
    base = Path(app_data) if app_data else Path.home() / ".config"
    return base / "PhotoMetadataEditor" / "settings.json"


def load_language(path: Path | None = None) -> str:
    target = path or settings_path()
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return DEFAULT_LANGUAGE
    language = payload.get("language") if isinstance(payload, dict) else None
    return language if language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def save_language(language: str, path: Path | None = None) -> None:
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported language: {language}")
    target = path or settings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix="settings-", suffix=".tmp", dir=target.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as file:
            json.dump({"language": language}, file, ensure_ascii=False, indent=2)
            file.write("\n")
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
