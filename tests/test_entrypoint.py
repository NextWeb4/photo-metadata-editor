from pathlib import Path
import runpy
import unittest


class EntrypointTests(unittest.TestCase):
    def test_main_file_imports_without_package_context(self) -> None:
        main_file = Path(__file__).resolve().parents[1] / "src" / "photo_meta_editor" / "__main__.py"

        namespace = runpy.run_path(str(main_file), run_name="photo_meta_editor_entrypoint_test")

        self.assertIn("main", namespace)

    def test_freeze_support_runs_before_gui_module_import_for_frozen_children(self) -> None:
        main_file = Path(__file__).resolve().parents[1] / "src" / "photo_meta_editor" / "__main__.py"
        source = main_file.read_text(encoding="utf-8")

        self.assertLess(source.index("multiprocessing.freeze_support()"), source.index("from .app import main"))


if __name__ == "__main__":
    unittest.main()
