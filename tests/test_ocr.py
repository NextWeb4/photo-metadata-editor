from pathlib import Path
import os
import subprocess
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from photo_meta_editor.ocr import (
    OcrError,
    extract_datetime_from_image,
    parse_datetime_text,
    recognize_with_paddleocr,
    recognize_with_tesseract,
    run_with_timeout,
)


def slow_backend_for_timeout() -> str:
    time.sleep(2)
    return "late"


def large_backend_output() -> str:
    return "2026-07-08 12:30\n" + ("x" * (2 * 1024 * 1024))


class OcrTests(unittest.TestCase):
    def test_parse_chinese_datetime_text(self) -> None:
        self.assertEqual(parse_datetime_text("拍摄于 2026年7月8日 12:30:05"), "2026:07:08 12:30:05")

    def test_parse_slash_datetime_without_seconds(self) -> None:
        self.assertEqual(parse_datetime_text("2026/07/08 12:30"), "2026:07:08 12:30:00")

    def test_parse_datetime_without_separator_before_time(self) -> None:
        self.assertEqual(parse_datetime_text("2026-07-0812:30:00"), "2026:07:08 12:30:00")

    def test_ignores_invalid_datetime(self) -> None:
        self.assertIsNone(parse_datetime_text("2026/99/08 12:30"))

    def test_skips_invalid_candidate_and_uses_later_valid_datetime(self) -> None:
        self.assertEqual(parse_datetime_text("bad 2026/99/08 ok 2026/07/08 12:30"), "2026:07:08 12:30:00")

    def test_ignores_impossible_calendar_day(self) -> None:
        self.assertIsNone(parse_datetime_text("2026-02-31 12:30:00"))

    def test_accepts_valid_leap_day(self) -> None:
        self.assertEqual(parse_datetime_text("2024-02-29 12:30:00"), "2024:02:29 12:30:00")

    def test_tesseract_timeout_is_reported_as_ocr_error(self) -> None:
        with patch("photo_meta_editor.ocr.subprocess.run", side_effect=subprocess.TimeoutExpired("tesseract", 90)):
            with self.assertRaisesRegex(OcrError, "超过 90 秒"):
                recognize_with_tesseract(Path("image.jpg"), "tesseract")

    def test_tesseract_failure_falls_back_to_paddleocr(self) -> None:
        def run_backend(_label: str, _func: object, _path: Path) -> str:
            return "2026-07-08 12:30"

        with (
            patch("photo_meta_editor.ocr.windows_ocr_available", return_value=False),
            patch("photo_meta_editor.ocr.shutil.which", return_value="tesseract"),
            patch("photo_meta_editor.ocr.recognize_with_tesseract", side_effect=OcrError("tesseract broken")),
            patch("photo_meta_editor.ocr.paddle_ocr_available", return_value=True),
            patch("photo_meta_editor.ocr.run_with_timeout", side_effect=run_backend),
        ):
            result = extract_datetime_from_image(Path("image.jpg"))

        self.assertEqual(result.engine, "PaddleOCR")
        self.assertEqual(result.datetime_value, "2026:07:08 12:30:00")

    def test_backend_system_exit_falls_back_to_the_next_local_engine(self) -> None:
        with (
            patch("photo_meta_editor.ocr.windows_ocr_available", return_value=True),
            patch("photo_meta_editor.ocr.run_with_timeout", side_effect=SystemExit("Windows OCR stopped")),
            patch("photo_meta_editor.ocr.shutil.which", return_value="tesseract"),
            patch("photo_meta_editor.ocr.recognize_with_tesseract", return_value="2026-07-08 12:30"),
            patch("photo_meta_editor.ocr.paddle_ocr_available", return_value=False),
        ):
            result = extract_datetime_from_image(Path("image.jpg"))

        self.assertEqual(result.engine, "Tesseract")
        self.assertEqual(result.datetime_value, "2026:07:08 12:30:00")

    def test_run_with_timeout_reports_backend_timeout(self) -> None:
        with patch("photo_meta_editor.ocr.OCR_PROCESS_TIMEOUT_SECONDS", 0.05):
            with self.assertRaisesRegex(OcrError, "PaddleOCR 执行超过"):
                run_with_timeout("PaddleOCR", slow_backend_for_timeout)

    def test_run_with_timeout_reads_large_backend_output_before_joining_process(self) -> None:
        with patch("photo_meta_editor.ocr.OCR_PROCESS_TIMEOUT_SECONDS", 10):
            text = run_with_timeout("PaddleOCR", large_backend_output)

        self.assertTrue(text.startswith("2026-07-08 12:30"))
        self.assertGreater(len(text), 2 * 1024 * 1024)

    def test_paddleocr_forces_local_model_source(self) -> None:
        class FakePaddleOCR:
            def __init__(self, **_kwargs: object) -> None:
                self.model_source = os.environ.get("PADDLE_PDX_MODEL_SOURCE")

            def predict(self, _path: str) -> list[dict[str, list[str]]]:
                return [{"rec_texts": [f"source={self.model_source}", "2026-07-08 12:30"]}]

        fake_module = SimpleNamespace(PaddleOCR=FakePaddleOCR)
        with (
            patch.dict(os.environ, {"PADDLE_PDX_MODEL_SOURCE": "ONLINE"}),
            patch("photo_meta_editor.ocr.paddle_ocr_available", return_value=True),
            patch("photo_meta_editor.ocr.importlib.import_module", return_value=fake_module),
        ):
            text = recognize_with_paddleocr(Path("image.jpg"))

        self.assertIn("source=LOCAL", text)


if __name__ == "__main__":
    unittest.main()
