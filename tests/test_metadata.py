import unittest
import tomllib
from pathlib import Path

from photo_meta_editor.metadata import APP_CREATOR, APP_EMAIL, APP_NAME, APP_VERSION, APP_WEBSITE
from scripts.generate_windows_version_info import render_version_info, version_tuple


class MetadataTests(unittest.TestCase):
    def test_creator_contact_metadata_is_available_for_about_and_packaging(self) -> None:
        self.assertEqual(APP_CREATOR, "HaoXiang Huang")
        self.assertEqual(APP_EMAIL, "didadida1688@gmail.com")
        self.assertEqual(APP_WEBSITE, "https://nextweb4.github.io")

    def test_pyproject_version_matches_application_metadata(self) -> None:
        pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
        pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))

        self.assertEqual(pyproject["project"]["version"], APP_VERSION)

    def test_generated_windows_version_info_uses_application_metadata(self) -> None:
        rendered = render_version_info()

        self.assertIn(f"StringStruct('CompanyName', {APP_CREATOR!r})", rendered)
        self.assertIn(f"StringStruct('FileDescription', {APP_NAME!r})", rendered)
        self.assertIn(f"Email: {APP_EMAIL}; Website: {APP_WEBSITE}", rendered)
        self.assertEqual(version_tuple(APP_VERSION), (0, 1, 2, 0))

    def test_readme_remains_utf8_chinese_without_mojibake(self) -> None:
        readme_path = Path(__file__).resolve().parents[1] / "README.md"
        text = readme_path.read_text(encoding="utf-8")

        self.assertIn("Photo Metadata Editor 是一个离线 Windows 桌面工具", text)
        self.assertIn("作者：[HaoXiang Huang]", text)
        self.assertIn("Photo Metadata Editor is an offline Windows desktop application", text)
        for marker in ("锛", "绛", "涓", "濯", "骞", "閿", "鈥"):
            self.assertNotIn(marker, text)


if __name__ == "__main__":
    unittest.main()
