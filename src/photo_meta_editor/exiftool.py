from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Mapping

from .fields import (
    FIELD_BY_KEY,
    QUICKTIME_GPS_DECIMALS,
    build_tag_assignments,
    extract_field_values,
    format_gps_number,
    is_quicktime_target,
    normalize_metadata_datetime,
    normalize_changed_values,
    validate_changed_values,
)


class ExifToolError(RuntimeError):
    pass


EXIFTOOL_TIMEOUT_SECONDS = 120
EXIFTOOL_UPDATED_RE = re.compile(r"(?P<count>\d+)\s+image files?\s+(?:updated|created|copied)", re.IGNORECASE)
EXIFTOOL_UNCHANGED_RE = re.compile(r"(?P<count>\d+)\s+image files?\s+unchanged", re.IGNORECASE)


@dataclass(frozen=True)
class WriteResult:
    stdout: str
    stderr: str
    backup_preserved: bool


@dataclass(frozen=True)
class RestoreResult:
    original_backup: Path
    current_backup: Path


def build_argfile_input(args: list[str]) -> bytes:
    """Encode ExifTool arguments as UTF-8 C-string lines for ``-@ -``."""
    lines = []
    for argument in args:
        escaped = argument.replace("\\", "\\\\").replace("\r", "\\r").replace("\n", "\\n")
        lines.append(f"#[CSTR]{escaped}\n")
    return "".join(lines).encode("utf-8")


def decode_exiftool_output(output: bytes | str | None) -> str:
    if isinstance(output, bytes):
        return output.decode("utf-8", errors="replace")
    return output or ""


def original_backup_path(file_path: Path) -> Path:
    return file_path.with_name(f"{file_path.name}_original")


def next_restore_backup_path(file_path: Path) -> Path:
    candidate = file_path.with_name(f"{file_path.name}_before_restore")
    sequence = 1
    while candidate.exists():
        candidate = file_path.with_name(f"{file_path.name}_before_restore.{sequence}")
        sequence += 1
    return candidate


def file_digest(file_path: Path) -> bytes:
    digest = hashlib.sha256()
    with file_path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.digest()


def copy_file_exclusive(source: Path, destination: Path) -> None:
    """Copy *source* without ever replacing an existing destination."""
    destination_created = False
    try:
        with source.open("rb") as source_file, destination.open("xb") as destination_file:
            destination_created = True
            shutil.copyfileobj(source_file, destination_file, length=1024 * 1024)
        shutil.copystat(source, destination)
    except BaseException:
        if destination_created:
            destination.unlink(missing_ok=True)
        raise


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def bundled_base() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return project_root()


def find_exiftool() -> Path:
    if getattr(sys, "frozen", False):
        # A packaged application must execute the reviewed ExifTool payload that
        # was shipped and signed with it. Development-only environment/PATH
        # overrides would otherwise let an inherited process environment replace
        # this binary at runtime.
        candidates: list[Path] = [
            bundled_base() / "exiftool" / "exiftool.exe",
            Path(sys.executable).resolve().parent / "exiftool" / "exiftool.exe",
        ]
    else:
        candidates = [
            bundled_base() / "vendor" / "exiftool" / "exiftool.exe",
            project_root() / "vendor" / "exiftool" / "exiftool.exe",
        ]
        env_exiftool = os.environ.get("PHOTO_META_EDITOR_EXIFTOOL")
        if env_exiftool:
            candidates.insert(0, Path(env_exiftool))

        path_value = shutil.which("exiftool.exe") or shutil.which("exiftool")
        if path_value:
            candidates.append(Path(path_value))

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    raise ExifToolError("未找到 exiftool.exe。请确认 vendor\\exiftool\\exiftool.exe 存在，或把 exiftool.exe 加入 PATH。")


class ExifToolClient:
    def __init__(self, executable: Path | None = None) -> None:
        self.executable = executable or find_exiftool()
        if not self.executable.exists():
            raise ExifToolError(f"未找到 exiftool.exe：{self.executable}")
        if not self.executable.is_file():
            raise ExifToolError(f"ExifTool 路径不是文件：{self.executable}")

    def version(self) -> str:
        stdout, _ = self._run(["-ver"])
        return stdout.strip()

    def read_metadata(self, file_path: Path) -> dict[str, object]:
        self._ensure_file(file_path)
        stdout, _ = self._run(
            [
                "-json",
                "-G1",
                "-s",
                "-a",
                "-charset",
                "filename=utf8",
                "-charset",
                "exif=utf8",
                "-sep",
                "; ",
                "-c",
                "%.8f",
                "--",
                str(file_path),
            ]
        )
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise ExifToolError(f"ExifTool 返回的 JSON 无法解析：{exc}") from exc
        if not payload:
            return {}
        if not isinstance(payload[0], dict):
            raise ExifToolError("ExifTool 返回了意外的数据结构。")
        return payload[0]

    def write_metadata(
        self,
        file_path: Path,
        changed_values: Mapping[str, str],
        preserve_backup: bool = True,
        sync_file_time: bool = False,
        file_time_value: str = "",
    ) -> WriteResult:
        self._ensure_file(file_path)
        errors = validate_changed_values(changed_values)
        effective_file_time = file_time_value or changed_values.get("date_taken", "")
        if sync_file_time:
            normalized_file_time = normalize_changed_values({"date_taken": effective_file_time}).get("date_taken", "")
            if not normalized_file_time:
                errors.append("同步文件时间需要先填写拍摄时间。")
            else:
                errors.extend(validate_changed_values({"date_taken": effective_file_time}))
        if errors:
            raise ExifToolError("\n".join(errors))

        target_path = str(file_path)
        if not has_write_assignments(changed_values, sync_file_time=sync_file_time, file_time_value=file_time_value, target_path=target_path):
            return WriteResult(stdout="没有需要写入的字段。", stderr="", backup_preserved=preserve_backup)

        args = build_write_args(
            changed_values,
            preserve_backup=preserve_backup,
            sync_file_time=sync_file_time,
            file_time_value=effective_file_time,
            target_path=target_path,
        )
        args.extend(["--", str(file_path)])

        stdout, stderr = self._run(args)
        ensure_write_updated_file(stdout)
        ensure_no_write_warnings(stderr)
        self.verify_written_values(
            file_path,
            changed_values,
            sync_file_time=sync_file_time,
            file_time_value=effective_file_time,
        )
        return WriteResult(stdout=stdout.strip(), stderr=stderr.strip(), backup_preserved=preserve_backup)

    def restore_original_backup(self, file_path: Path) -> RestoreResult:
        self._ensure_file(file_path)
        original_backup = original_backup_path(file_path)
        if not original_backup.is_file():
            raise ExifToolError(f"未找到原始备份：{original_backup.name}")

        current_backup = next_restore_backup_path(file_path)
        temporary_restore: Path | None = None
        restore_replaced_target = False
        current_digest: bytes | None = None
        try:
            # Preserve the current edited state before atomically restoring the
            # ExifTool original. This makes an explicit rollback reversible.
            current_digest = file_digest(file_path)
            copy_file_exclusive(file_path, current_backup)
            if file_digest(current_backup) != current_digest or file_digest(file_path) != current_digest:
                raise ExifToolError("恢复前的当前文件备份校验失败；原文件未被替换。")

            original_digest = file_digest(original_backup)
            descriptor, temporary_name = tempfile.mkstemp(prefix=f"{file_path.name}.restore-", suffix=".tmp", dir=file_path.parent)
            os.close(descriptor)
            temporary_restore = Path(temporary_name)
            shutil.copy2(original_backup, temporary_restore)
            if file_digest(temporary_restore) != original_digest or file_digest(original_backup) != original_digest:
                raise ExifToolError("原始备份临时副本校验失败。")
            if file_digest(file_path) != current_digest:
                raise ExifToolError("恢复期间当前文件已被其他程序修改；已停止恢复，未替换当前文件。")
            os.replace(temporary_restore, file_path)
            temporary_restore = None
            restore_replaced_target = True
            if file_digest(file_path) != original_digest:
                raise ExifToolError("恢复后文件校验失败。")
        except (OSError, ExifToolError) as exc:
            if restore_replaced_target and current_digest is not None:
                try:
                    self._rollback_failed_restore(file_path, current_backup, current_digest)
                except (OSError, ExifToolError) as rollback_exc:
                    raise ExifToolError(f"恢复原始备份失败，且无法回滚当前文件：{rollback_exc}") from rollback_exc
            if isinstance(exc, ExifToolError):
                raise
            raise ExifToolError(f"恢复原始备份失败：{exc}") from exc
        finally:
            if temporary_restore is not None:
                temporary_restore.unlink(missing_ok=True)

        return RestoreResult(original_backup=original_backup, current_backup=current_backup)

    @staticmethod
    def _rollback_failed_restore(file_path: Path, current_backup: Path, expected_digest: bytes) -> None:
        descriptor, temporary_name = tempfile.mkstemp(prefix=f"{file_path.name}.rollback-", suffix=".tmp", dir=file_path.parent)
        os.close(descriptor)
        temporary_rollback = Path(temporary_name)
        try:
            shutil.copy2(current_backup, temporary_rollback)
            if file_digest(temporary_rollback) != expected_digest:
                raise ExifToolError("恢复前版本的回滚副本校验失败。")
            os.replace(temporary_rollback, file_path)
            temporary_rollback = None
            if file_digest(file_path) != expected_digest:
                raise ExifToolError("恢复失败后的当前文件回滚校验失败。")
        finally:
            if temporary_rollback is not None:
                temporary_rollback.unlink(missing_ok=True)

    def verify_written_values(
        self,
        file_path: Path,
        changed_values: Mapping[str, str],
        sync_file_time: bool = False,
        file_time_value: str = "",
    ) -> None:
        expected = expected_readback_values(changed_values)
        normalized_file_time = normalize_changed_values({"date_taken": file_time_value}).get("date_taken", "")
        if not expected and not (sync_file_time and normalized_file_time):
            return
        # The editor adds display-only fallbacks for missing fields. Verification
        # must compare stored tag values so a successful clear is not reported as
        # a failed write because of a filename, lens, or file-time fallback.
        metadata = self.read_metadata(file_path)
        actual = extract_field_values(
            metadata,
            use_file_name_as_title=False,
            infer_camera_from_lens=False,
            use_file_time_as_date=False,
        )
        target_path = str(file_path)
        mismatches = [
            f"{key}: 期望 {value!r}，读回 {actual.get(key, '')!r}"
            for key, value in expected.items()
            if not readback_value_matches(key, value, actual.get(key, ""), target_path)
        ]
        if mismatches:
            raise ExifToolError("ExifTool 写入后读回校验失败：\n" + "\n".join(mismatches))
        if sync_file_time and normalized_file_time:
            verify_synced_file_times(metadata, normalized_file_time)

    def _ensure_file(self, file_path: Path) -> None:
        if not file_path.exists():
            raise ExifToolError(f"文件不存在：{file_path}")
        if not file_path.is_file():
            raise ExifToolError(f"不是可处理的文件：{file_path}")

    def _run(self, args: list[str]) -> tuple[str, str]:
        env = os.environ.copy()
        for key in ("LC_ALL", "LC_CTYPE", "LANG"):
            if env.get(key) == "C.UTF-8":
                env.pop(key, None)

        creationflags = 0
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        try:
            completed = subprocess.run(
                # ExifTool's Windows launcher receives command-line text using
                # the active code page. Feed all arguments through its UTF-8
                # ``-@ -`` input instead so Chinese paths and multiline values
                # preserve their bytes before ExifTool converts file names to
                # Windows UTF-16 APIs.
                [str(self.executable), "-config", "", "-@", "-"],
                input=build_argfile_input(args),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                creationflags=creationflags,
                timeout=EXIFTOOL_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ExifToolError(f"ExifTool 执行超过 {EXIFTOOL_TIMEOUT_SECONDS} 秒，已停止等待。") from exc
        except OSError as exc:
            raise ExifToolError(f"无法启动 ExifTool：{exc}") from exc
        stdout = decode_exiftool_output(completed.stdout)
        stderr = decode_exiftool_output(completed.stderr)
        if completed.returncode != 0:
            message = stderr.strip() or stdout.strip() or f"ExifTool 退出码：{completed.returncode}"
            raise ExifToolError(message)
        return stdout, stderr


def build_write_args(
    changed_values: Mapping[str, str],
    preserve_backup: bool = True,
    sync_file_time: bool = False,
    file_time_value: str = "",
    target_path: str | None = None,
) -> list[str]:
    assignments = build_tag_assignments(changed_values, target_path=target_path)
    if sync_file_time:
        normalized = normalize_changed_values({"date_taken": file_time_value or changed_values.get("date_taken", "")})
        date_value = normalized.get("date_taken", "")
        if date_value:
            assignments.extend(
                [
                    ("FileModifyDate", date_value),
                    ("FileCreateDate", date_value),
                ]
            )

    args = [
        "-m",
        "-P",
        "-charset",
        "filename=utf8",
        "-charset",
        "exif=utf8",
        "-codedcharacterset=utf8",
        "-sep",
        "; ",
    ]
    if not preserve_backup:
        args.append("-overwrite_original")
    for tag, value in assignments:
        args.append(f"-{tag}={value}")
    return args


def has_write_assignments(
    changed_values: Mapping[str, str],
    sync_file_time: bool = False,
    file_time_value: str = "",
    target_path: str | None = None,
) -> bool:
    if build_tag_assignments(changed_values, target_path=target_path):
        return True
    if not sync_file_time:
        return False
    normalized = normalize_changed_values({"date_taken": file_time_value or changed_values.get("date_taken", "")})
    return bool(normalized.get("date_taken"))


def ensure_write_updated_file(stdout: str) -> None:
    updated = sum(int(match.group("count")) for match in EXIFTOOL_UPDATED_RE.finditer(stdout))
    if updated > 0:
        return
    unchanged = sum(int(match.group("count")) for match in EXIFTOOL_UNCHANGED_RE.finditer(stdout))
    if unchanged > 0:
        raise ExifToolError("ExifTool 没有写入任何文件；请确认目标格式支持这些字段，或字段值是否已经相同。")
    if stdout.strip():
        raise ExifToolError("ExifTool 写入结果无法确认：\n" + stdout.strip())
    raise ExifToolError("ExifTool 没有返回可确认的写入结果。")


def ensure_no_write_warnings(stderr: str) -> None:
    warning_lines = [line.strip() for line in stderr.splitlines() if line.strip().casefold().startswith("warning:")]
    if warning_lines:
        raise ExifToolError("ExifTool 写入时返回警告：\n" + "\n".join(warning_lines))


def expected_readback_values(changed_values: Mapping[str, str]) -> dict[str, str]:
    normalized = normalize_changed_values(changed_values)
    expected: dict[str, str] = {}
    for key, value in normalized.items():
        if key == "gps_latitude" or key == "gps_longitude":
            expected[key] = format_gps_number(float(value)) if value else ""
            continue
        field = FIELD_BY_KEY.get(key)
        if not field or field.readonly or not field.write_tags:
            continue
        expected[key] = value
    return expected


def readback_value_matches(key: str, expected: str, actual: str, target_path: str | None = None) -> bool:
    if expected == actual:
        return True
    if key not in {"gps_latitude", "gps_longitude"} or not expected or not actual or not is_quicktime_target(target_path):
        return False
    try:
        # ISO 6709 values are intentionally written with five decimal places for
        # QuickTime compatibility, so a value may be rounded when read back.
        return abs(float(expected) - float(actual)) <= 0.5 * 10 ** (-QUICKTIME_GPS_DECIMALS) + 1e-12
    except ValueError:
        return False


def verify_synced_file_times(metadata: Mapping[str, object], expected: str) -> None:
    mismatches: list[str] = []
    for label, tags in (
        ("文件修改时间", ("System:FileModifyDate", "File:FileModifyDate")),
        ("文件创建时间", ("System:FileCreateDate", "File:FileCreateDate")),
    ):
        actual = next((str(metadata[tag]) for tag in tags if metadata.get(tag) not in (None, "")), "")
        if normalize_metadata_datetime(actual) != expected:
            mismatches.append(f"{label}: 期望 {expected!r}，读回 {actual!r}")
    if mismatches:
        raise ExifToolError("文件时间同步读回校验失败：\n" + "\n".join(mismatches))
