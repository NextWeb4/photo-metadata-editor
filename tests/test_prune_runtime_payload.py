import tempfile
import unittest
from pathlib import Path

import scripts.prune_runtime_payload as prune_runtime_payload_module
from scripts.path_safety import assert_no_reparse_points
from scripts.prune_runtime_payload import prune_runtime_payload, prune_tkdnd_platforms


class PruneRuntimePayloadTests(unittest.TestCase):
    def test_prunes_unused_tkdnd_platforms(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tkdnd = root / "lib" / "tkinterdnd2" / "tkdnd"
            (tkdnd / "win-x64").mkdir(parents=True)
            (tkdnd / "linux-x64").mkdir()
            (tkdnd / "osx-x64").mkdir()

            removed = prune_tkdnd_platforms(root, keep_platform="win-x64")

            self.assertEqual(removed, 2)
            self.assertTrue((tkdnd / "win-x64").exists())
            self.assertFalse((tkdnd / "linux-x64").exists())
            self.assertFalse((tkdnd / "osx-x64").exists())

    def test_prunes_tk_demo_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            demos = root / "share" / "tk8.6" / "demos"
            demos.mkdir(parents=True)
            (demos / "demo.tcl").write_text("demo", encoding="utf-8")

            stats = prune_runtime_payload(root)

            self.assertEqual(stats["tk_demo_dirs"], 1)
            self.assertFalse(demos.exists())

    def test_prune_checks_for_reparse_points_before_recursive_delete(self) -> None:
        source = Path(prune_runtime_payload_module.__file__).read_text(encoding="utf-8")

        check_index = source.index("assert_no_reparse_points(path)")
        delete_index = source.index("shutil.rmtree(path)")

        self.assertLess(check_index, delete_index)

    def test_rejects_symlink_before_recursive_operation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "target"
            target.mkdir()
            link = root / "link"
            try:
                link.symlink_to(target, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")

            with self.assertRaises(RuntimeError):
                assert_no_reparse_points(root)


if __name__ == "__main__":
    unittest.main()
