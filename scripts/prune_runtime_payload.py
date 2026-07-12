from __future__ import annotations

import argparse
import os
from pathlib import Path
import platform
import shutil

try:
    from scripts.path_safety import assert_no_reparse_points, assert_resolved_under_root
except ModuleNotFoundError:  # Running as python scripts/prune_runtime_payload.py
    from path_safety import assert_no_reparse_points, assert_resolved_under_root


TKDND_PLATFORM_DIRS = {
    "Darwin": {"arm64": "osx-arm64", "x86_64": "osx-x64"},
    "Linux": {"aarch64": "linux-arm64", "x86_64": "linux-x64"},
    "Windows": {"ARM64": "win-arm64", "AMD64": "win-x64", "x86": "win-x86"},
}


def current_tkdnd_platform_dir() -> str:
    system = platform.system()
    machine = os.environ.get("PROCESSOR_ARCHITECTURE", platform.machine()) if system == "Windows" else platform.machine()
    platform_dir = TKDND_PLATFORM_DIRS.get(system, {}).get(machine)
    if not platform_dir:
        raise RuntimeError(f"Unsupported tkdnd platform: {system} {machine}")
    return platform_dir


def assert_under_root(path: Path, root: Path) -> None:
    assert_resolved_under_root(path, root, "prune")


def remove_tree(path: Path, root: Path) -> None:
    assert_under_root(path, root)
    assert_no_reparse_points(path)
    shutil.rmtree(path)


def prune_tkdnd_platforms(root: Path, keep_platform: str | None = None) -> int:
    keep = keep_platform or current_tkdnd_platform_dir()
    removed = 0
    for tkdnd_dir in root.rglob("tkdnd"):
        if not tkdnd_dir.is_dir() or tkdnd_dir.parent.name != "tkinterdnd2":
            continue
        for child in tkdnd_dir.iterdir():
            if child.is_dir() and child.name != keep:
                remove_tree(child, root)
                removed += 1
    return removed


def prune_tk_demos(root: Path) -> int:
    removed = 0
    for demos_dir in root.rglob("demos"):
        if demos_dir.is_dir() and demos_dir.parent.name == "tk8.6":
            remove_tree(demos_dir, root)
            removed += 1
    return removed


def prune_runtime_payload(root: Path) -> dict[str, int]:
    if not root.exists():
        raise FileNotFoundError(root)
    if not root.is_dir():
        raise NotADirectoryError(root)
    assert_no_reparse_points(root)
    return {
        "tkdnd_platform_dirs": prune_tkdnd_platforms(root),
        "tk_demo_dirs": prune_tk_demos(root),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prune unused platform/demo files from packaged runtime payloads.")
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    for root in args.paths:
        stats = prune_runtime_payload(root)
        print(f"Pruned {root}: {stats}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
