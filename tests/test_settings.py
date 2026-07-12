import json
from pathlib import Path
import tempfile
import unittest

from photo_meta_editor.settings import load_language, save_language


class SettingsTests(unittest.TestCase):
    def test_language_round_trip_uses_utf8_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "nested" / "settings.json"

            save_language("en", path)

            self.assertEqual(load_language(path), "en")
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"language": "en"})

    def test_invalid_or_missing_settings_fall_back_to_chinese(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "settings.json"
            self.assertEqual(load_language(path), "zh_CN")
            path.write_text('{"language": "invalid"}', encoding="utf-8")
            self.assertEqual(load_language(path), "zh_CN")
            path.write_text("not-json", encoding="utf-8")
            self.assertEqual(load_language(path), "zh_CN")


if __name__ == "__main__":
    unittest.main()
