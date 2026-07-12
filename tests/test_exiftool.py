import base64
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from photo_meta_editor.exiftool import (
    ExifToolClient,
    ExifToolError,
    build_argfile_input,
    build_write_args,
    ensure_no_write_warnings,
    ensure_write_updated_file,
    expected_readback_values,
    file_digest,
    find_exiftool,
    has_write_assignments,
    readback_value_matches,
    original_backup_path,
    verify_synced_file_times,
)
from photo_meta_editor.fields import extract_field_values


TINY_JPEG_BASE64 = (
    "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////"
    "2wBDAf//////////////////////////////////////////////////////////////////////////////////////wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQ"
    "AAAAAAAAAAAAAAAAAAAAX/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIQAxAAAAH/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oACAEBAAEFAqf/"
    "xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oACAEDAQE/ASP/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oACAECAQE/ASP/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/"
    "9oACAEBAAY/An//xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oACAEBAAE/IV//2gAMAwEAAgADAAAAEP/EABQRAQAAAAAAAAAAAAAAAAAAABD/2gAIAQ"
    "MBAT8QH//EABQRAQAAAAAAAAAAAAAAAAAAABD/2gAIAQIBAT8QH//EABQQAQAAAAAAAAAAAAAAAAAAABD/2gAIAQEAAT8QH//Z"
)
TINY_PNG_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="


class ExifToolTests(unittest.TestCase):
    def test_find_exiftool_prefers_frozen_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp)
            exiftool = bundle / "exiftool" / "exiftool.exe"
            exiftool.parent.mkdir()
            exiftool.write_text("", encoding="utf-8")

            with patch.object(sys, "frozen", True, create=True), patch.object(sys, "_MEIPASS", str(bundle), create=True):
                self.assertEqual(find_exiftool(), exiftool)

    def test_frozen_application_ignores_environment_exiftool_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "bundle"
            bundled_exiftool = bundle / "exiftool" / "exiftool.exe"
            bundled_exiftool.parent.mkdir(parents=True)
            bundled_exiftool.write_text("", encoding="utf-8")
            override_exiftool = Path(tmp) / "override.exe"
            override_exiftool.write_text("", encoding="utf-8")

            with patch.object(sys, "frozen", True, create=True), patch.object(sys, "_MEIPASS", str(bundle), create=True), patch.dict(
                "os.environ", {"PHOTO_META_EDITOR_EXIFTOOL": str(override_exiftool)}
            ):
                self.assertEqual(find_exiftool(), bundled_exiftool)

    def test_find_exiftool_can_use_explicit_env_override_without_private_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_exiftool = Path(tmp) / "custom-exiftool.exe"
            fake_exiftool.write_text("", encoding="utf-8")

            with patch.dict("os.environ", {"PHOTO_META_EDITOR_EXIFTOOL": str(fake_exiftool)}):
                self.assertEqual(find_exiftool(), fake_exiftool)

    def test_argfile_input_preserves_literal_backslashes_and_multiline_values(self) -> None:
        payload = build_argfile_input([r"-XMP-dc:Description=Path\name", "-XMP-dc:Title=first\nsecond"])

        self.assertEqual(
            payload.decode("utf-8"),
            "#[CSTR]-XMP-dc:Description=Path\\\\name\n#[CSTR]-XMP-dc:Title=first\\nsecond\n",
        )

    def test_exiftool_run_disables_external_default_config_before_argfile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_exiftool = Path(tmp) / "exiftool.exe"
            fake_exiftool.write_text("", encoding="utf-8")
            client = ExifToolClient(executable=fake_exiftool)
            completed = subprocess.CompletedProcess(args=[], returncode=0, stdout=b"13.50\n", stderr=b"")

            with patch("photo_meta_editor.exiftool.subprocess.run", return_value=completed) as run:
                client.version()

        command = run.call_args.args[0]
        self.assertEqual(command[:5], [str(fake_exiftool), "-config", "", "-@", "-"])

    def test_read_metadata_rejects_missing_file_before_running_exiftool(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_exiftool = Path(tmp) / "exiftool.exe"
            fake_exiftool.write_text("", encoding="utf-8")
            client = ExifToolClient(executable=fake_exiftool)

            with self.assertRaisesRegex(ExifToolError, "文件不存在"):
                client.read_metadata(Path(tmp) / "missing.jpg")

    def test_exiftool_constructor_rejects_directory_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ExifToolError, "不是文件"):
                ExifToolClient(executable=Path(tmp))

    def test_build_write_args_can_sync_file_time_without_metadata_changes(self) -> None:
        args = build_write_args({}, sync_file_time=True, file_time_value="2026-07-08 12:30:00")

        self.assertIn("-FileModifyDate=2026:07:08 12:30:00", args)
        self.assertIn("-FileCreateDate=2026:07:08 12:30:00", args)
        self.assertTrue(has_write_assignments({}, sync_file_time=True, file_time_value="2026-07-08 12:30:00"))

    def test_build_write_args_adds_quicktime_tags_for_supported_media(self) -> None:
        args = build_write_args(
            {"date_taken": "2026-07-08 12:30", "title": "Video"},
            target_path="clip.mp4",
        )

        self.assertIn("-QuickTime:CreateDate=2026:07:08 12:30:00", args)
        self.assertIn("-Keys:CreationDate=2026:07:08 12:30:00", args)
        self.assertNotIn("-QuickTime:ModifyDate=2026:07:08 12:30:00", args)
        self.assertNotIn("-QuickTime:TrackModifyDate=2026:07:08 12:30:00", args)
        self.assertIn("-Keys:Title=Video", args)
        self.assertTrue(has_write_assignments({"date_taken": "2026-07-08 12:30"}, target_path="clip.mp4"))

    def test_write_summary_requires_updated_file(self) -> None:
        with self.assertRaisesRegex(ExifToolError, "没有写入任何文件"):
            ensure_write_updated_file("    0 image files updated\n    1 image files unchanged\n")

    def test_write_summary_accepts_updated_file(self) -> None:
        ensure_write_updated_file("    1 image files updated\n")

    def test_write_summary_rejects_unknown_output(self) -> None:
        with self.assertRaisesRegex(ExifToolError, "无法确认"):
            ensure_write_updated_file("Done.\n")

    def test_write_warning_is_user_visible_failure(self) -> None:
        with self.assertRaisesRegex(ExifToolError, "返回警告"):
            ensure_no_write_warnings("Warning: Tag is not writable\n")

    def test_expected_readback_values_are_normalized(self) -> None:
        expected = expected_readback_values({"date_taken": "2026.7.8 12:30", "gps_latitude": "39.90000000"})

        self.assertEqual(expected["date_taken"], "2026:07:08 12:30:00")
        self.assertEqual(expected["gps_latitude"], "39.9")

    def test_expected_readback_values_include_cleared_fields(self) -> None:
        expected = expected_readback_values({"title": "", "gps_latitude": "", "gps_longitude": ""})

        self.assertEqual(expected["title"], "")
        self.assertEqual(expected["gps_latitude"], "")
        self.assertEqual(expected["gps_longitude"], "")

    def test_expected_readback_values_skip_readonly_fields(self) -> None:
        expected = expected_readback_values({"file_name": "IMG_0001.JPG", "iso": "125"})

        self.assertEqual(expected, {})

    def test_quicktime_gps_readback_accepts_iso6709_rounding_only(self) -> None:
        self.assertTrue(readback_value_matches("gps_latitude", "39.908722", "39.90872", "clip.mov"))
        self.assertTrue(readback_value_matches("gps_longitude", "116.397499", "116.3975", "clip.heic"))
        self.assertFalse(readback_value_matches("gps_latitude", "39.908722", "39.90871", "clip.mov"))
        self.assertFalse(readback_value_matches("gps_latitude", "39.908722", "39.90872", "photo.jpg"))

    def test_write_metadata_rejects_exiftool_unchanged_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_exiftool = Path(tmp) / "exiftool.exe"
            fake_exiftool.write_text("", encoding="utf-8")
            image_path = Path(tmp) / "tiny.jpg"
            image_path.write_bytes(base64.b64decode(TINY_JPEG_BASE64))
            client = ExifToolClient(executable=fake_exiftool)

            with patch.object(client, "_run", return_value=("    0 image files updated\n    1 image files unchanged\n", "")):
                with self.assertRaisesRegex(ExifToolError, "没有写入任何文件"):
                    client.write_metadata(image_path, {"title": "new"}, preserve_backup=False)

    def test_write_metadata_rejects_failed_readback_verification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_exiftool = Path(tmp) / "exiftool.exe"
            fake_exiftool.write_text("", encoding="utf-8")
            image_path = Path(tmp) / "tiny.jpg"
            image_path.write_bytes(base64.b64decode(TINY_JPEG_BASE64))
            client = ExifToolClient(executable=fake_exiftool)

            with patch.object(client, "_run", side_effect=[("    1 image files updated\n", ""), ('[{"XMP-dc:Title":"old"}]', "")]):
                with self.assertRaisesRegex(ExifToolError, "读回校验失败"):
                    client.write_metadata(image_path, {"title": "new"}, preserve_backup=False)

    def test_file_time_sync_requires_both_system_times_to_read_back(self) -> None:
        verify_synced_file_times(
            {
                "System:FileModifyDate": "2026:07:08 12:30:00+08:00",
                "System:FileCreateDate": "2026:07:08 12:30:00+08:00",
            },
            "2026:07:08 12:30:00",
        )

        with self.assertRaisesRegex(ExifToolError, "文件创建时间"):
            verify_synced_file_times(
                {
                    "System:FileModifyDate": "2026:07:08 12:30:00+08:00",
                    "System:FileCreateDate": "2026:07:08 12:30:01+08:00",
                },
                "2026:07:08 12:30:00",
            )

    def test_write_metadata_verifies_file_time_only_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_exiftool = Path(tmp) / "exiftool.exe"
            fake_exiftool.write_text("", encoding="utf-8")
            image_path = Path(tmp) / "tiny.jpg"
            image_path.write_bytes(base64.b64decode(TINY_JPEG_BASE64))
            client = ExifToolClient(executable=fake_exiftool)

            with patch.object(
                client,
                "_run",
                side_effect=[
                    ("    1 image files updated\n", ""),
                    (
                        '[{"System:FileModifyDate":"2026:07:08 12:30:00+08:00",'
                        '"System:FileCreateDate":"2026:07:08 12:30:00+08:00"}]',
                        "",
                    ),
                ],
            ):
                client.write_metadata(
                    image_path,
                    {},
                    preserve_backup=False,
                    sync_file_time=True,
                    file_time_value="2026-07-08 12:30",
                )

    def test_file_time_sync_rejects_an_empty_effective_capture_time(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "tiny.jpg"
            image_path.write_bytes(base64.b64decode(TINY_JPEG_BASE64))
            client = ExifToolClient()

            with self.assertRaisesRegex(ExifToolError, "同步文件时间需要先填写拍摄时间"):
                client.write_metadata(
                    image_path,
                    {"title": "updated"},
                    preserve_backup=False,
                    sync_file_time=True,
                )

    def test_file_time_sync_uses_the_changed_capture_time_when_no_override_is_given(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "tiny.jpg"
            image_path.write_bytes(base64.b64decode(TINY_JPEG_BASE64))
            client = ExifToolClient()

            client.write_metadata(
                image_path,
                {"date_taken": "2026-07-08 12:30"},
                preserve_backup=False,
                sync_file_time=True,
            )
            metadata = client.read_metadata(image_path)

        self.assertEqual(metadata["ExifIFD:DateTimeOriginal"], "2026:07:08 12:30:00")
        self.assertEqual(metadata["System:FileModifyDate"], "2026:07:08 12:30:00+08:00")
        self.assertEqual(metadata["System:FileCreateDate"], "2026:07:08 12:30:00+08:00")

    def test_exiftool_timeout_is_reported_as_user_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_exiftool = Path(tmp) / "exiftool.exe"
            fake_exiftool.write_text("", encoding="utf-8")
            client = ExifToolClient(executable=fake_exiftool)

            with patch("photo_meta_editor.exiftool.subprocess.run", side_effect=subprocess.TimeoutExpired("exiftool", 120)):
                with self.assertRaisesRegex(ExifToolError, "超过 120 秒"):
                    client.version()

    def test_exiftool_start_failure_is_reported_as_user_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_exiftool = Path(tmp) / "exiftool.exe"
            fake_exiftool.write_text("", encoding="utf-8")
            client = ExifToolClient(executable=fake_exiftool)

            with patch("photo_meta_editor.exiftool.subprocess.run", side_effect=OSError("not executable")):
                with self.assertRaisesRegex(ExifToolError, "无法启动 ExifTool"):
                    client.version()

    def test_default_backup_preserves_the_original_across_consecutive_saves(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "tiny.jpg"
            original_bytes = base64.b64decode(TINY_JPEG_BASE64)
            image_path.write_bytes(original_bytes)
            client = ExifToolClient()

            client.write_metadata(image_path, {"title": "first"})
            backup_path = image_path.with_name(f"{image_path.name}_original")
            self.assertTrue(backup_path.is_file())
            self.assertEqual(backup_path.read_bytes(), original_bytes)

            client.write_metadata(image_path, {"title": "second"})
            self.assertEqual(backup_path.read_bytes(), original_bytes)
            self.assertEqual(client.read_metadata(image_path)["XMP-dc:Title"], "second")

    def test_restore_original_backup_preserves_current_file_as_a_reversible_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "tiny.jpg"
            original_bytes = base64.b64decode(TINY_JPEG_BASE64)
            edited_bytes = b"edited current bytes"
            image_path.write_bytes(edited_bytes)
            original_backup = original_backup_path(image_path)
            original_backup.write_bytes(original_bytes)
            client = ExifToolClient()

            result = client.restore_original_backup(image_path)

            self.assertEqual(image_path.read_bytes(), original_bytes)
            self.assertEqual(original_backup.read_bytes(), original_bytes)
            self.assertEqual(result.current_backup.read_bytes(), edited_bytes)
            self.assertEqual(result.current_backup.name, "tiny.jpg_before_restore")

    def test_restore_original_backup_never_overwrites_a_racing_backup_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "tiny.jpg"
            image_path.write_bytes(b"edited")
            original_backup = original_backup_path(image_path)
            original_backup.write_bytes(b"original")
            protected_backup = image_path.with_name(f"{image_path.name}_before_restore")
            protected_backup.write_bytes(b"another restore")
            client = ExifToolClient()

            with patch("photo_meta_editor.exiftool.next_restore_backup_path", return_value=protected_backup):
                with self.assertRaisesRegex(ExifToolError, "恢复原始备份失败"):
                    client.restore_original_backup(image_path)

            self.assertEqual(image_path.read_bytes(), b"edited")
            self.assertEqual(protected_backup.read_bytes(), b"another restore")

    def test_restore_verification_failure_rolls_back_the_current_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "tiny.jpg"
            edited_bytes = b"edited"
            original_bytes = b"original"
            image_path.write_bytes(edited_bytes)
            original_backup = original_backup_path(image_path)
            original_backup.write_bytes(original_bytes)
            client = ExifToolClient()
            real_file_digest = file_digest
            failed_post_replace_check = False

            def fail_first_restored_target_check(path: Path) -> bytes:
                nonlocal failed_post_replace_check
                if path == image_path and path.read_bytes() == original_bytes and not failed_post_replace_check:
                    failed_post_replace_check = True
                    return b"invalid digest"
                return real_file_digest(path)

            with patch("photo_meta_editor.exiftool.file_digest", side_effect=fail_first_restored_target_check):
                with self.assertRaisesRegex(ExifToolError, "恢复后文件校验失败"):
                    client.restore_original_backup(image_path)

            self.assertTrue(failed_post_replace_check)
            self.assertEqual(image_path.read_bytes(), edited_bytes)
            self.assertEqual(image_path.with_name(f"{image_path.name}_before_restore").read_bytes(), edited_bytes)

    def test_restore_stops_if_the_current_file_changes_before_replace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "tiny.jpg"
            edited_bytes = b"edited"
            external_bytes = b"external update"
            image_path.write_bytes(edited_bytes)
            original_backup = original_backup_path(image_path)
            original_backup.write_bytes(b"original")
            client = ExifToolClient()
            real_copy2 = shutil.copy2

            def copy_and_simulate_external_update(source: Path, destination: Path) -> str:
                result = real_copy2(source, destination)
                if source == original_backup:
                    image_path.write_bytes(external_bytes)
                return str(result)

            with patch("photo_meta_editor.exiftool.shutil.copy2", side_effect=copy_and_simulate_external_update):
                with self.assertRaisesRegex(ExifToolError, "当前文件已被其他程序修改"):
                    client.restore_original_backup(image_path)

            self.assertEqual(image_path.read_bytes(), external_bytes)
            self.assertEqual(image_path.with_name(f"{image_path.name}_before_restore").read_bytes(), edited_bytes)

    def test_clears_title_without_confusing_the_file_name_ui_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "tiny.jpg"
            image_path.write_bytes(base64.b64decode(TINY_JPEG_BASE64))
            client = ExifToolClient()

            client.write_metadata(image_path, {"title": "Before"}, preserve_backup=False)
            client.write_metadata(image_path, {"title": ""}, preserve_backup=False)

            self.assertNotIn("XMP-dc:Title", client.read_metadata(image_path))

    def test_clears_camera_without_confusing_lens_inference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "tiny.jpg"
            image_path.write_bytes(base64.b64decode(TINY_JPEG_BASE64))
            client = ExifToolClient()
            client._run(
                [
                    "-EXIF:LensMake=Apple iphone 17Pro",
                    "-overwrite_original",
                    "--",
                    str(image_path),
                ]
            )
            client.write_metadata(
                image_path,
                {"make": "Apple", "model": "iPhone 17 Pro"},
                preserve_backup=False,
            )
            client.write_metadata(image_path, {"make": "", "model": ""}, preserve_backup=False)

            metadata = client.read_metadata(image_path)
            self.assertNotIn("IFD0:Make", metadata)
            self.assertNotIn("IFD0:Model", metadata)

    def test_clears_date_without_confusing_file_time_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "tiny.jpg"
            image_path.write_bytes(base64.b64decode(TINY_JPEG_BASE64))
            client = ExifToolClient()

            client.write_metadata(image_path, {"date_taken": "2026:07:08 12:30:00"}, preserve_backup=False)
            client.write_metadata(image_path, {"date_taken": ""}, preserve_backup=False)

            self.assertNotIn("ExifIFD:DateTimeOriginal", client.read_metadata(image_path))

    def test_writes_normalized_common_date_to_jpeg(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "tiny.jpg"
            image_path.write_bytes(base64.b64decode(TINY_JPEG_BASE64))
            client = ExifToolClient()

            client.write_metadata(image_path, {"date_taken": "2026.7.8 12:30"}, preserve_backup=False)
            metadata = client.read_metadata(image_path)

        self.assertEqual(metadata["ExifIFD:DateTimeOriginal"], "2026:07:08 12:30:00")

    def test_writes_title_and_gps_to_png(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "tiny.png"
            image_path.write_bytes(base64.b64decode(TINY_PNG_BASE64))
            client = ExifToolClient()

            client.write_metadata(
                image_path,
                {
                    "title": "PNG metadata",
                    "gps_latitude": "39.908722",
                    "gps_longitude": "116.397499",
                },
                preserve_backup=False,
            )
            metadata = client.read_metadata(image_path)
            values = extract_field_values(metadata, use_file_name_as_title=False)

        self.assertEqual(metadata["XMP-dc:Title"], "PNG metadata")
        self.assertEqual(values["gps_latitude"], "39.908722")
        self.assertEqual(values["gps_longitude"], "116.397499")

    def test_reads_and_writes_chinese_path_and_multiline_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "照片 空格" / "测试 图片.jpg"
            image_path.parent.mkdir()
            image_path.write_bytes(base64.b64decode(TINY_JPEG_BASE64))
            client = ExifToolClient()

            client.write_metadata(image_path, {"title": "中文 标题\n第二行"}, preserve_backup=False)
            values = extract_field_values(client.read_metadata(image_path), use_file_name_as_title=False)

        self.assertEqual(values["title"], "中文 标题\n第二行")

    def test_syncs_both_file_times_to_jpeg(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "tiny.jpg"
            image_path.write_bytes(base64.b64decode(TINY_JPEG_BASE64))
            client = ExifToolClient()

            client.write_metadata(
                image_path,
                {},
                preserve_backup=False,
                sync_file_time=True,
                file_time_value="2026-07-08 12:30",
            )
            metadata = client.read_metadata(image_path)

        self.assertEqual(metadata["System:FileModifyDate"], "2026:07:08 12:30:00+08:00")
        self.assertEqual(metadata["System:FileCreateDate"], "2026:07:08 12:30:00+08:00")


if __name__ == "__main__":
    unittest.main()
