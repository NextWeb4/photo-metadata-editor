from __future__ import annotations

import hashlib
import importlib
import os
import sys
from pathlib import Path

from cx_Freeze import Executable, setup
from cx_Freeze.command.build_exe import build_exe as cx_build_exe
from cx_Freeze.command.bdist_msi import bdist_msi as cx_bdist_msi


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from photo_meta_editor.metadata import (  # noqa: E402
    APP_COPYRIGHT,
    APP_CREATOR,
    APP_DESCRIPTION,
    APP_EMAIL,
    APP_NAME,
    APP_VERSION,
    APP_WEBSITE,
)
from scripts.collect_licenses import collect_licenses  # noqa: E402
from scripts.prune_runtime_payload import prune_runtime_payload  # noqa: E402


class BuildExeCommand(cx_build_exe):
    def run(self) -> None:
        super().run()
        prune_runtime_payload(Path(self.build_exe))


class BuildMsiCommand(cx_bdist_msi):
    """Build MSI directory identifiers in an application-owned namespace."""

    def add_files(self) -> None:
        # cx_Freeze normally derives MSI Directory identifiers directly from
        # folder names. ExifTool's Perl runtime contains folders such as
        # ``Text``; that identifier collides with Windows Installer UI state and
        # can be overwritten with an action timestamp before CostFinalize.
        # Stable prefixed identifiers keep filesystem names out of MSI's global
        # property namespace while preserving the installed directory names.
        msi_module = importlib.import_module("cx_Freeze.command.bdist_msi")
        database = self.db
        cab = msi_module.CAB("distfiles")
        feature = msi_module.Feature(
            database,
            "default",
            "Default Feature",
            "Everything",
            1,
            directory="TARGETDIR",
        )
        feature.set_current()
        root_dir = os.path.abspath(self.bdist_dir)
        root = msi_module.Directory(database, cab, None, root_dir, "TARGETDIR", "SourceDir")
        database.Commit()
        todo = [root]
        while todo:
            directory = todo.pop()
            for file_name in os.listdir(directory.absolute):
                absolute = os.path.join(directory.absolute, file_name)
                relative = os.path.relpath(absolute, self.bdist_dir)
                separate_component = self.separate_components.get(relative)
                if separate_component is not None:
                    restore_component = directory.component
                    directory.start_component(
                        component=separate_component,
                        flags=0,
                        feature=feature,
                        keyfile=file_name,
                    )
                    directory.add_file(file_name)
                    directory.component = restore_component
                elif os.path.isdir(absolute):
                    short_name = directory.make_short(file_name)
                    digest = hashlib.sha256(relative.casefold().encode("utf-8")).hexdigest()[:24]
                    logical_name = f"PME_DIR_{digest}"
                    child = msi_module.Directory(
                        database,
                        cab,
                        directory,
                        file_name,
                        logical_name,
                        f"{short_name}|{file_name}",
                    )
                    todo.append(child)
                else:
                    directory.add_file(file_name)
        cab.commit(database)


base = "Win32GUI" if sys.platform == "win32" else None
LICENSE_DIR = collect_licenses()

build_exe_options = {
    "build_exe": str(ROOT / "build" / "cx_freeze" / "PhotoMetaEditor"),
    "packages": ["photo_meta_editor", "tkinterdnd2"],
    "include_files": [
        (str(ROOT / "vendor" / "exiftool" / "exiftool.exe"), "exiftool/exiftool.exe"),
        (str(ROOT / "vendor" / "exiftool" / "exiftool_files"), "exiftool/exiftool_files"),
        (str(LICENSE_DIR), "licenses"),
    ],
    "excludes": [
        "cv2",
        "easyocr",
        "matplotlib",
        "paddle",
        "paddleocr",
        "pandas",
        "scipy",
        "torch",
        "torchvision",
        "winsdk",
    ],
    "include_msvcr": True,
    "replace_paths": [("*", ".")],
}

bdist_msi_options = {
    "add_to_path": False,
    "all_users": False,
    "data": {
        # Windows Installer may derive ROOTDRIVE from a redirected Documents
        # folder. If that folder points to an unavailable network/removable
        # drive, CostFinalize fails with Error 1606 even though TARGETDIR is on
        # the local system drive. Resolve it from WindowsVolume before costing.
        "CustomAction": [
            ("A_SET_PERSONAL_FOLDER", 256 + 51, "PersonalFolder", "[LocalAppDataFolder]"),
            ("A_SET_ROOT_DRIVE", 256 + 51, "ROOTDRIVE", "[WindowsVolume]"),
        ],
        "InstallExecuteSequence": [
            ("A_SET_PERSONAL_FOLDER", "1", 399),
            ("A_SET_ROOT_DRIVE", "1", 400),
        ],
        "InstallUISequence": [
            ("A_SET_PERSONAL_FOLDER", "1", 399),
            ("A_SET_ROOT_DRIVE", "1", 400),
        ],
    },
    "initial_target_dir": r"[ProgramFilesFolder]\HaoXiang Huang\Photo Metadata Editor",
    "summary_data": {
        "author": APP_CREATOR,
        "comments": f"Email: {APP_EMAIL}; Website: {APP_WEBSITE}",
        "keywords": "Photo Metadata Editor; ExifTool; EXIF; XMP; IPTC",
    },
    "target_name": "PhotoMetadataEditor",
    "target_version": APP_VERSION,
    "upgrade_code": "{7A3C1D3C-6BAF-49C1-8F05-B2F8F780E8A1}",
}

setup(
    name="PhotoMetadataEditor",
    version=APP_VERSION,
    description=APP_DESCRIPTION,
    long_description=APP_DESCRIPTION,
    author=APP_CREATOR,
    author_email=APP_EMAIL,
    url=APP_WEBSITE,
    options={
        "build_exe": build_exe_options,
        "bdist_msi": bdist_msi_options,
    },
    cmdclass={"build_exe": BuildExeCommand, "bdist_msi": BuildMsiCommand},
    executables=[
        Executable(
            str(ROOT / "src" / "photo_meta_editor" / "__main__.py"),
            base=base,
            target_name="PhotoMetaEditor.exe",
            shortcut_name=APP_NAME,
            shortcut_dir="ProgramMenuFolder",
            copyright=APP_COPYRIGHT,
        )
    ],
)
