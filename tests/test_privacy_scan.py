import io
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from scripts.check_package_privacy import iter_files, relative_display_name, scan_file, scan_msi_payload, scan_pyinstaller_archive


class PrivacyScanTests(unittest.TestCase):
    def test_scan_file_detects_utf16_private_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "version.bin"
            path.write_bytes("C:\\Users\\Example\\PrivateWorkspace".encode("utf-16le"))

            findings = scan_file(path)

        self.assertEqual(findings, [(str(path), ["C:\\Users\\Example\\PrivateWorkspace"])])

    def test_scan_file_detects_private_marker_inside_zip_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive_path = Path(tmp) / "portable.zip"
            with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("app/config.txt", "source C:/Users/Example/PrivateWorkspace/codex-clipboard.png")

            findings = scan_file(archive_path)

        self.assertIn(
            (
                f"{archive_path}!app/config.txt",
                ["C:/Users/Example/PrivateWorkspace", "codex-clipboard"],
            ),
            findings,
        )

    def test_scan_file_detects_user_profile_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.txt"
            path.write_text("source C:/Users/Example/PrivateWorkspace/secret.png", encoding="utf-8")

            findings = scan_file(path)

        self.assertEqual(findings, [(str(path), ["C:/Users/Example/PrivateWorkspace"])])

    def test_scan_file_detects_dynamic_project_root_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "release-workspace" / "photo"
            project_root.mkdir(parents=True)
            resolved_project_root = project_root.resolve()
            path = Path(tmp) / "artifact.bin"
            path.write_text(f"source {resolved_project_root.as_posix()}/src/photo_meta_editor/app.py", encoding="utf-8")

            with (
                patch("scripts.check_package_privacy.ROOT", project_root),
                patch("scripts.check_package_privacy.STATIC_PRIVATE_MARKERS", ()),
                patch.dict("os.environ", {"USERPROFILE": "", "TEMP": "", "TMP": ""}),
            ):
                findings = scan_file(path)

        self.assertEqual(findings, [(str(path), [resolved_project_root.as_posix()])])

    def test_scan_file_detects_private_marker_case_insensitively(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.txt"
            path.write_text("source c:/users/example/privateworkspace/secret.png", encoding="utf-8")

            findings = scan_file(path)

        self.assertEqual(findings, [(str(path), ["C:/Users/Example/PrivateWorkspace"])])

    def test_scan_file_detects_private_marker_in_regular_file_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "codex-clipboard-example.txt"
            path.write_text("clean content", encoding="utf-8")

            findings = scan_file(path)

        self.assertEqual(findings, [(str(path), ["codex-clipboard"])])

    def test_relative_display_name_avoids_project_root_false_positive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "D_Codex_like_root"
            root.mkdir()
            clean_file = root / "clean-artifact.bin"
            clean_file.write_bytes(b"clean")
            files = iter_files([root])

            findings = [finding for file_path in files for finding in scan_file(file_path, relative_display_name(file_path, [root]))]

        self.assertEqual(findings, [])

    def test_scan_file_detects_private_marker_in_zip_entry_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive_path = Path(tmp) / "portable.zip"
            with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("PhotoMetaEditor/codex-clipboard-example.txt", "clean content")

            findings = scan_file(archive_path)

        self.assertIn(
            (
                f"{archive_path}!PhotoMetaEditor/codex-clipboard-example.txt",
                ["codex-clipboard"],
            ),
            findings,
        )

    def test_scan_file_rejects_excessively_nested_zip_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested.zip"
            payload = b"clean"
            for _ in range(4):
                buffer = io.BytesIO()
                with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                    archive.writestr("nested.zip", payload)
                payload = buffer.getvalue()
            path.write_bytes(payload)

            with self.assertRaisesRegex(RuntimeError, "nesting exceeds"):
                scan_file(path)

    def test_scan_file_deep_scans_msi_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "installer.msi"
            path.write_bytes(b"clean msi bytes")

            with patch(
                "scripts.check_package_privacy.scan_msi_payload",
                return_value=[(f"{path}!app/config.txt", ["C:\\Users\\Example\\PrivateWorkspace"])],
            ):
                findings = scan_file(path)

        self.assertIn((f"{path}!app/config.txt", ["C:\\Users\\Example\\PrivateWorkspace"]), findings)

    def test_scan_pyinstaller_archive_scans_decompressed_payload_and_pyz(self) -> None:
        class FakeCArchive:
            def __init__(self, _path: str) -> None:
                self.toc = {"assets/config.txt": (), "PYZ.pyz": ()}

            def extract(self, name: str) -> bytes:
                return b"source C:/Users/Example/PrivateWorkspace/project" if name == "assets/config.txt" else b"fake pyz"

        class FakePyzArchive:
            def __init__(self, _path: str) -> None:
                self.toc = {"photo_meta_editor.app": ()}

            def extract(self, name: str, raw: bool = False) -> bytes:
                self_name = name
                if not raw:
                    raise AssertionError("PYZ payload must be read as raw bytes")
                return f"source C:/Users/Example/PrivateWorkspace/{self_name}".encode("utf-8")

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "PhotoMetaEditor.exe"
            path.write_bytes(b"outer executable")

            with patch("scripts.check_package_privacy.CArchiveReader", FakeCArchive), patch(
                "scripts.check_package_privacy.ZlibArchiveReader", FakePyzArchive
            ):
                findings = scan_pyinstaller_archive(path)

        self.assertTrue(
            any(
                location == f"{path}!pyinstaller/assets/config.txt" and "C:/Users/Example/PrivateWorkspace" in matches
                for location, matches in findings
            )
        )
        self.assertIn(
            (f"{path}!pyinstaller/PYZ.pyz!photo_meta_editor.app", ["C:/Users/Example/PrivateWorkspace"]),
            findings,
        )

    def test_scan_file_deep_scans_pyinstaller_executable_inside_zip(self) -> None:
        class FakeCArchive:
            def __init__(self, _path: str) -> None:
                self.toc = {"assets/config.txt": ()}

            def extract(self, _name: str) -> bytes:
                return b"source C:/Users/Example/PrivateWorkspace/project"

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "portable.zip"
            with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("PhotoMetaEditor/PhotoMetaEditor.exe", b"frozen executable")

            with patch("scripts.check_package_privacy.CArchiveReader", FakeCArchive):
                findings = scan_file(path)

        self.assertTrue(
            any(
                location == f"{path}!PhotoMetaEditor/PhotoMetaEditor.exe!pyinstaller/assets/config.txt"
                and "C:/Users/Example/PrivateWorkspace" in matches
                for location, matches in findings
            )
        )

    def test_photo_meta_editor_exe_fails_closed_without_pyinstaller_reader(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "PhotoMetaEditor.exe"
            path.write_bytes(b"outer executable")

            with patch("scripts.check_package_privacy.CArchiveReader", None), patch(
                "scripts.check_package_privacy.ZlibArchiveReader", None
            ):
                with self.assertRaisesRegex(RuntimeError, "cannot deeply scan"):
                    scan_pyinstaller_archive(path, require_reader=True)

    def test_photo_meta_editor_exe_fails_closed_when_not_a_pyinstaller_archive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "PhotoMetaEditor.exe"
            path.write_bytes(b"not a PyInstaller archive")

            with self.assertRaisesRegex(RuntimeError, "Unable to inspect PyInstaller archive"):
                scan_pyinstaller_archive(path, require_reader=True)

    def test_non_pyinstaller_exe_with_same_name_uses_raw_scan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "PhotoMetaEditor.exe"
            path.write_bytes(b"clean cx_freeze executable")

            findings = scan_file(path)

        self.assertEqual(findings, [])

    def test_scan_msi_payload_uses_configured_staging_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload_root = root / "payload"
            payload_root.mkdir()
            (payload_root / "config.txt").write_text("source C:/Users/Example/PrivateWorkspace/project", encoding="utf-8")
            path = root / "installer.msi"
            path.write_bytes(b"clean msi bytes")

            with patch.dict("os.environ", {"PHOTO_META_EDITOR_MSI_PAYLOAD_ROOT": str(payload_root)}):
                findings = scan_msi_payload(path)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0][0], f"{path}!payload/config.txt")
        self.assertIn("C:/Users/Example/PrivateWorkspace", findings[0][1])


if __name__ == "__main__":
    unittest.main()
