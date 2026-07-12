from __future__ import annotations

import os
from pathlib import Path
import stat


WINDOWS_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


def assert_resolved_under_root(path: Path, root: Path, action: str) -> None:
    resolved_path = path.resolve()
    resolved_root = root.resolve()
    if resolved_path != resolved_root and resolved_root not in resolved_path.parents:
        raise RuntimeError(f"Refusing to {action} path outside root: {resolved_path}")


def _entry_is_reparse_point(entry: os.DirEntry[str]) -> bool:
    if entry.is_symlink():
        return True
    try:
        attributes = getattr(entry.stat(follow_symlinks=False), "st_file_attributes", 0)
    except OSError as exc:
        raise RuntimeError(f"Unable to inspect path before recursive operation: {entry.path}") from exc
    return bool(attributes & WINDOWS_REPARSE_POINT)


def _path_is_reparse_point(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        attributes = getattr(path.stat(follow_symlinks=False), "st_file_attributes", 0)
    except OSError as exc:
        raise RuntimeError(f"Unable to inspect path before recursive operation: {path}") from exc
    return bool(attributes & WINDOWS_REPARSE_POINT)


def assert_no_reparse_points(root: Path) -> None:
    if not root.exists():
        return
    if _path_is_reparse_point(root):
        raise RuntimeError(f"Refusing recursive operation through reparse point: {root}")
    stack = [root]
    while stack:
        current = stack.pop()
        with os.scandir(current) as entries:
            for entry in entries:
                if _entry_is_reparse_point(entry):
                    raise RuntimeError(f"Refusing recursive operation through reparse point: {entry.path}")
                if entry.is_dir(follow_symlinks=False):
                    stack.append(Path(entry.path))
