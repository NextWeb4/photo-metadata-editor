import unittest

from photo_meta_editor.presets import find_camera_preset, find_location_preset


class PresetTests(unittest.TestCase):
    def test_finds_iphone_17_camera_preset(self) -> None:
        preset = find_camera_preset("Apple iPhone 17 Pro")

        self.assertIsNotNone(preset)
        self.assertEqual(preset.make, "Apple")
        self.assertEqual(preset.model, "iPhone 17 Pro")

    def test_finds_location_preset_with_negative_longitude(self) -> None:
        preset = find_location_preset("纽约 Times Square")

        self.assertIsNotNone(preset)
        self.assertLess(preset.longitude, 0)


if __name__ == "__main__":
    unittest.main()

