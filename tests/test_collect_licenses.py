import unittest
from pathlib import Path

import scripts.collect_licenses as collect_licenses_module
from scripts.collect_licenses import collect_licenses


class CollectLicensesTests(unittest.TestCase):
    def test_collect_licenses_includes_third_party_notice(self) -> None:
        output_dir = collect_licenses()

        self.assertTrue((output_dir / "PROJECT-LICENSE.txt").is_file())
        self.assertTrue((output_dir / "THIRD_PARTY.md").is_file())
        self.assertTrue((output_dir / "ExifTool-Windows-LICENSE.txt").is_file())
        self.assertTrue((output_dir / "ExifTool-Windows-README.txt").is_file())
        self.assertTrue((output_dir / "Strawberry-Perl-Licenses.zip").is_file())
        self.assertTrue((output_dir / "PyInstaller-COPYING.txt").is_file())
        self.assertTrue((output_dir / "cx_Freeze-LICENSE.md").is_file())
        self.assertTrue((output_dir / "tkinterdnd2-LICENSE").is_file())

    def test_collect_licenses_rejects_reparse_points_before_recursive_delete(self) -> None:
        source = Path(collect_licenses_module.__file__).read_text(encoding="utf-8")

        check_index = source.index("assert_no_reparse_points(OUTPUT_DIR)")
        delete_index = source.index("shutil.rmtree(OUTPUT_DIR)")

        self.assertLess(check_index, delete_index)


if __name__ == "__main__":
    unittest.main()
