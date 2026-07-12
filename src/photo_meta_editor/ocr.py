from __future__ import annotations

import asyncio
from collections.abc import Callable
import multiprocessing as mp
import queue
from dataclasses import dataclass
from datetime import datetime
import importlib.util
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from typing import TypeVar


class OcrError(RuntimeError):
    pass


@dataclass(frozen=True)
class OcrDateResult:
    engine: str
    text: str
    datetime_value: str


DATE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"(?P<year>20\d{2})[\-/年.](?P<month>\d{1,2})[\-/月.](?P<day>\d{1,2})"
        r"(?:[日\sT_]*(?P<hour>\d{1,2})[:：](?P<minute>\d{2})(?:[:：](?P<second>\d{2}))?)?"
    ),
    re.compile(
        r"(?P<month>\d{1,2})[\-/](?P<day>\d{1,2})[\-/](?P<year>20\d{2})"
        r"(?:[\sT_]*(?P<hour>\d{1,2})[:：](?P<minute>\d{2})(?:[:：](?P<second>\d{2}))?)?"
    ),
)
PADDLE_MODEL_ROOT = Path.home() / ".paddlex" / "official_models"
PADDLE_DET_MODEL = PADDLE_MODEL_ROOT / "PP-OCRv5_server_det"
PADDLE_REC_MODEL = PADDLE_MODEL_ROOT / "PP-OCRv5_server_rec"
OCR_PROCESS_TIMEOUT_SECONDS = 90
T = TypeVar("T")


def available_ocr_engines() -> list[str]:
    engines: list[str] = []
    if windows_ocr_available():
        engines.append("Windows OCR")
    if shutil.which("tesseract.exe") or shutil.which("tesseract"):
        engines.append("Tesseract")
    if paddle_ocr_available():
        engines.append("PaddleOCR(本地缓存)")
    return engines


def extract_datetime_from_image(file_path: Path) -> OcrDateResult:
    errors: list[str] = []
    if windows_ocr_available():
        try:
            text = run_with_timeout("Windows OCR", recognize_with_windows_ocr, file_path)
            datetime_value = parse_datetime_text(text)
            if datetime_value:
                return OcrDateResult("Windows OCR", text, datetime_value)
            errors.append("Windows OCR 未识别到可用时间。")
        except BaseException as exc:  # A provider can terminate its worker without preventing local fallback.
            errors.append(f"Windows OCR 失败：{exc}")

    tesseract = shutil.which("tesseract.exe") or shutil.which("tesseract")
    if tesseract:
        try:
            text = recognize_with_tesseract(file_path, tesseract)
            datetime_value = parse_datetime_text(text)
            if datetime_value:
                return OcrDateResult("Tesseract", text, datetime_value)
            errors.append("Tesseract 未识别到可用时间。")
        except BaseException as exc:  # A provider can terminate its worker without preventing local fallback.
            errors.append(f"Tesseract 失败：{exc}")

    if paddle_ocr_available():
        try:
            text = run_with_timeout("PaddleOCR", recognize_with_paddleocr, file_path)
            datetime_value = parse_datetime_text(text)
            if datetime_value:
                return OcrDateResult("PaddleOCR", text, datetime_value)
            errors.append("PaddleOCR 未识别到可用时间。")
        except BaseException as exc:  # A provider can terminate its worker without preventing local fallback.
            errors.append(f"PaddleOCR 失败：{exc}")

    if not errors:
        errors.append("当前没有可用 OCR 引擎。请安装 Windows OCR 语言包、Tesseract OCR，或提供本地 PaddleOCR 缓存模型。")
    raise OcrError("\n".join(errors))


def _run_backend_in_process(result_queue: mp.Queue, func: Callable[..., object], args: tuple[object, ...]) -> None:
    try:
        result_queue.put((True, func(*args)))
    except BaseException as exc:  # noqa: BLE001 - preserve backend-specific failure text for caller.
        result_queue.put((False, f"{type(exc).__name__}: {exc}"))


def run_with_timeout(label: str, func: Callable[..., T], *args: object) -> T:
    result_queue: mp.Queue = mp.Queue(maxsize=1)
    process = mp.Process(target=_run_backend_in_process, args=(result_queue, func, args), daemon=True)
    try:
        process.start()
        deadline = time.monotonic() + OCR_PROCESS_TIMEOUT_SECONDS
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                terminate_process(process)
                raise OcrError(f"{label} 执行超过 {OCR_PROCESS_TIMEOUT_SECONDS} 秒，已终止后端进程。")
            try:
                ok, result = result_queue.get(timeout=min(0.1, remaining))
            except queue.Empty:
                if not process.is_alive():
                    raise OcrError(f"{label} 执行失败，后端进程退出码 {process.exitcode}。")
                continue
            process.join(5)
            if process.is_alive():
                terminate_process(process)
                raise OcrError(f"{label} 执行失败，后端进程未正常退出。")
            if ok:
                return result  # type: ignore[return-value]
            raise OcrError(f"{label} 失败：{result}")
    except OSError as exc:
        raise OcrError(f"{label} 无法启动 OCR 后端进程：{exc}") from exc
    finally:
        result_queue.close()
        result_queue.join_thread()


def terminate_process(process: mp.Process) -> None:
    if not process.is_alive():
        return
    process.terminate()
    process.join(5)
    if process.is_alive():
        process.kill()
        process.join(5)


def parse_datetime_text(text: str) -> str | None:
    normalized = text.replace("：", ":")
    for pattern in DATE_PATTERNS:
        for match in pattern.finditer(normalized):
            year = int(match.group("year"))
            month = int(match.group("month"))
            day = int(match.group("day"))
            hour = int(match.group("hour") or 0)
            minute = int(match.group("minute") or 0)
            second = int(match.group("second") or 0)
            if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
                continue
            try:
                parsed = datetime(year, month, day, hour, minute, second)
            except ValueError:
                continue
            return parsed.strftime("%Y:%m:%d %H:%M:%S")
    return None


def recognize_with_tesseract(file_path: Path, executable: str) -> str:
    try:
        completed = subprocess.run(
            [executable, str(file_path), "stdout", "--psm", "6"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            timeout=OCR_PROCESS_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise OcrError(f"Tesseract OCR 执行超过 {OCR_PROCESS_TIMEOUT_SECONDS} 秒，已停止等待。") from exc
    if completed.returncode != 0:
        raise OcrError(completed.stderr.strip() or "Tesseract OCR 执行失败。")
    return completed.stdout


def paddle_ocr_available() -> bool:
    if importlib.util.find_spec("paddleocr") is None:
        return False
    return (PADDLE_DET_MODEL / "inference.pdiparams").exists() and (PADDLE_REC_MODEL / "inference.pdiparams").exists()


def recognize_with_paddleocr(file_path: Path) -> str:
    if not paddle_ocr_available():
        raise OcrError("PaddleOCR 本地缓存模型不完整。")
    os.environ["PADDLE_PDX_MODEL_SOURCE"] = "LOCAL"
    paddleocr_module = importlib.import_module("paddleocr")
    paddleocr_class = getattr(paddleocr_module, "PaddleOCR")

    ocr = paddleocr_class(
        text_detection_model_dir=str(PADDLE_DET_MODEL),
        text_recognition_model_dir=str(PADDLE_REC_MODEL),
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )
    result = ocr.predict(str(file_path))
    texts: list[str] = []
    for page in result:
        if isinstance(page, dict):
            texts.extend(str(text) for text in page.get("rec_texts", []))
        elif hasattr(page, "get"):
            texts.extend(str(text) for text in page.get("rec_texts", []))
    return "\n".join(texts)


def windows_ocr_available() -> bool:
    try:
        from winsdk.windows.media.ocr import OcrEngine
    except Exception:
        return False
    try:
        return OcrEngine.available_recognizer_languages.size > 0
    except Exception:
        return False


def recognize_with_windows_ocr(file_path: Path) -> str:
    return asyncio.run(_recognize_with_windows_ocr(file_path))


async def _recognize_with_windows_ocr(file_path: Path) -> str:
    from winsdk.windows.graphics.imaging import BitmapAlphaMode, BitmapDecoder, BitmapPixelFormat, SoftwareBitmap
    from winsdk.windows.media.ocr import OcrEngine
    from winsdk.windows.storage import FileAccessMode, StorageFile

    engine = OcrEngine.try_create_from_user_profile_languages()
    if engine is None:
        raise OcrError("Windows OCR 没有可用语言。")

    storage_file = await StorageFile.get_file_from_path_async(str(file_path.resolve()))
    stream = await storage_file.open_async(FileAccessMode.READ)
    decoder = await BitmapDecoder.create_async(stream)
    bitmap = await decoder.get_software_bitmap_async()
    if bitmap.bitmap_pixel_format != BitmapPixelFormat.BGRA8 or bitmap.bitmap_alpha_mode != BitmapAlphaMode.PREMULTIPLIED:
        bitmap = SoftwareBitmap.convert(bitmap, BitmapPixelFormat.BGRA8, BitmapAlphaMode.PREMULTIPLIED)
    result = await engine.recognize_async(bitmap)
    return result.text
