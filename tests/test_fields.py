import unittest

from photo_meta_editor.fields import (
    build_tag_assignments,
    extract_field_values,
    metadata_rows,
    normalize_changed_values,
    validate_changed_values,
)


class FieldTests(unittest.TestCase):
    def test_extracts_first_available_tag(self) -> None:
        metadata = {
            "XMP:Title": "XMP title",
            "IFD0:ImageDescription": "Camera description",
            "IPTC:Keywords": ["alpha", "beta"],
            "ExifIFD:DateTimeOriginal": "2026:07:08 12:30:00",
        }

        values = extract_field_values(metadata)

        self.assertEqual(values["title"], "XMP title")
        self.assertEqual(values["description"], "Camera description")
        self.assertEqual(values["keywords"], "alpha; beta")
        self.assertEqual(values["date_taken"], "2026:07:08 12:30:00")

    def test_extracts_requested_editable_fields_for_prefill(self) -> None:
        values = extract_field_values(
            {
                "IFD0:XPTitle": "夏日照片",
                "IFD0:XPAuthor": "Alice",
                "QuickTime:CreationDate": "2026:07:08 12:30:00+08:00",
                "IFD0:Make": "Canon",
                "IFD0:Model": "Canon EOS R5",
                "Keys:Software": "Digital Photo Professional",
                "Composite:GPSPosition": "39.908722 116.397499",
            }
        )

        self.assertEqual(values["title"], "夏日照片")
        self.assertEqual(values["creator"], "Alice")
        self.assertEqual(values["date_taken"], "2026:07:08 12:30:00")
        self.assertEqual(values["make"], "Canon")
        self.assertEqual(values["model"], "Canon EOS R5")
        self.assertEqual(values["software"], "Digital Photo Professional")
        self.assertEqual(values["gps_latitude"], "39.908722")
        self.assertEqual(values["gps_longitude"], "116.397499")

    def test_extracts_apple_photos_info_card_fields(self) -> None:
        values = extract_field_values(
            {
                "System:FileName": "IMG_6846.HEIC",
                "File:FileType": "HEIF",
                "File:FileSize": "1.8 MB",
                "Composite:ImageSize": "3024x4032",
                "Composite:Megapixels": "12",
                "ExifIFD:LensModel": "Wide Camera",
                "ExifIFD:ISO": "125",
                "ExifIFD:FocalLength": "25",
                "ExifIFD:ExposureCompensation": "0",
                "ExifIFD:FNumber": "1.8",
                "ExifIFD:ExposureTime": "1/94",
                "IPTC:Sub-location": "温泉",
            }
        )

        self.assertEqual(values["file_name"], "IMG_6846.HEIC")
        self.assertEqual(values["file_type"], "HEIF")
        self.assertEqual(values["file_size"], "1.8 MB")
        self.assertEqual(values["image_size"], "3024x4032")
        self.assertEqual(values["megapixels"], "12 MP")
        self.assertEqual(values["lens_model"], "Wide Camera")
        self.assertEqual(values["iso"], "125")
        self.assertEqual(values["focal_length"], "25 mm")
        self.assertEqual(values["exposure_compensation"], "0 ev")
        self.assertEqual(values["aperture"], "f/1.8")
        self.assertEqual(values["exposure_time"], "1/94 s")
        self.assertEqual(values["location_name"], "温泉")

    def test_prefills_title_date_and_camera_from_fallback_tags(self) -> None:
        values = extract_field_values(
            {
                "System:FileName": "IMG_0001.HEIC",
                "System:FileModifyDate": "2026:07:08 12:30:00+08:00",
                "ExifIFD:LensMake": "Apple iphone 17Pro",
                "ExifIFD:LensModel": "30mm f1.90 1/129 ISO 32",
            }
        )

        self.assertEqual(values["title"], "IMG_0001")
        self.assertEqual(values["date_taken"], "2026:07:08 12:30:00")
        self.assertEqual(values["make"], "Apple")
        self.assertEqual(values["model"], "iPhone 17 Pro")

    def test_can_disable_file_name_title_fallback_for_write_verification(self) -> None:
        values = extract_field_values(
            {"System:FileName": "IMG_0001.HEIC"},
            use_file_name_as_title=False,
        )

        self.assertEqual(values["title"], "")

    def test_can_disable_lens_camera_inference_for_write_verification(self) -> None:
        values = extract_field_values(
            {"ExifIFD:LensMake": "Apple iphone 17Pro"},
            infer_camera_from_lens=False,
        )

        self.assertEqual(values["make"], "")
        self.assertEqual(values["model"], "")

    def test_can_disable_file_time_date_fallback_for_write_verification(self) -> None:
        values = extract_field_values(
            {"System:FileModifyDate": "2026:07:08 12:30:00+08:00"},
            use_file_time_as_date=False,
        )

        self.assertEqual(values["date_taken"], "")

    def test_normalizes_dash_date(self) -> None:
        values = normalize_changed_values({"date_taken": "2026-07-08 12:30:00"})

        self.assertEqual(values["date_taken"], "2026:07:08 12:30:00")

    def test_normalizes_common_user_date_separators(self) -> None:
        for raw_value in (
            "2026-07-08",
            "2026/7/8",
            "2026年7月8日",
            "2026/07/08 12:30",
            "2026.7.8 12:30:00",
            "2026年7月8日 12：30：00",
        ):
            with self.subTest(raw_value=raw_value):
                values = normalize_changed_values({"date_taken": raw_value})

                expected = "2026:07:08 00:00:00" if raw_value in {"2026-07-08", "2026/7/8", "2026年7月8日"} else "2026:07:08 12:30:00"
                self.assertEqual(values["date_taken"], expected)

    def test_normalizes_metadata_date_with_dots(self) -> None:
        values = extract_field_values({"ExifIFD:DateTimeOriginal": "2026.7.8 12:30:00"})

        self.assertEqual(values["date_taken"], "2026:07:08 12:30:00")

    def test_treats_quicktime_zero_date_as_a_cleared_value(self) -> None:
        values = extract_field_values({"QuickTime:CreateDate": "0000:00:00 00:00:00"})

        self.assertEqual(values["date_taken"], "")

    def test_extracts_quicktime_track_dates_from_numbered_groups(self) -> None:
        values = extract_field_values({"Track1:TrackCreateDate": "2026:07:08 12:30:00+08:00"})

        self.assertEqual(values["date_taken"], "2026:07:08 12:30:00")

    def test_extracts_quicktime_userdata_fields_written_by_editor(self) -> None:
        values = extract_field_values(
            {
                "UserData:Make": "Apple",
                "UserData:Model": "iPhone 17 Pro",
                "UserData:SoftwareVersion": "iOS 26",
                "UserData:GPSCoordinates": "+39.908722+116.397499/",
            }
        )

        self.assertEqual(values["make"], "Apple")
        self.assertEqual(values["model"], "iPhone 17 Pro")
        self.assertEqual(values["software"], "iOS 26")
        self.assertEqual(values["gps_latitude"], "39.908722")
        self.assertEqual(values["gps_longitude"], "116.397499")

    def test_validates_date_and_gps(self) -> None:
        errors = validate_changed_values({"date_taken": "bad", "gps_latitude": "91"})

        self.assertEqual(len(errors), 3)

    def test_requires_gps_coordinates_as_a_pair(self) -> None:
        errors = validate_changed_values({"gps_latitude": "39.908722"})

        self.assertEqual(errors, ["GPS 纬度和经度必须同时修改，或同时清空。"])

    def test_rejects_clearing_only_one_gps_coordinate(self) -> None:
        errors = validate_changed_values({"gps_latitude": ""})

        self.assertEqual(errors, ["GPS 纬度和经度必须同时修改，或同时清空。"])

    def test_validates_real_calendar_date(self) -> None:
        errors = validate_changed_values({"date_taken": "2026:02:31 12:30:00"})

        self.assertEqual(errors, ["拍摄时间不是有效日期，例如不能填写 2026:02:31 12:30:00。"])

    def test_builds_gps_assignments_with_refs(self) -> None:
        assignments = dict(build_tag_assignments({"gps_latitude": "-31.5", "gps_longitude": "121.25"}))

        self.assertEqual(assignments["GPS:GPSLatitude"], "31.50000000")
        self.assertEqual(assignments["GPS:GPSLatitudeRef"], "S")
        self.assertEqual(assignments["GPS:GPSLongitude"], "121.25000000")
        self.assertEqual(assignments["GPS:GPSLongitudeRef"], "E")

    def test_builds_quicktime_assignments_for_media_targets(self) -> None:
        assignments = dict(
            build_tag_assignments(
                {
                    "title": "City clip",
                    "date_taken": "2026-07-08 12:30",
                    "make": "Apple",
                    "model": "iPhone 17 Pro",
                    "gps_latitude": "39.908722",
                    "gps_longitude": "116.397499",
                },
                target_path="clip.mov",
            )
        )

        self.assertEqual(assignments["Keys:Title"], "City clip")
        self.assertEqual(assignments["QuickTime:CreateDate"], "2026:07:08 12:30:00")
        self.assertEqual(assignments["Keys:CreationDate"], "2026:07:08 12:30:00")
        self.assertEqual(assignments["Keys:Make"], "Apple")
        self.assertEqual(assignments["Keys:Model"], "iPhone 17 Pro")
        self.assertEqual(assignments["Keys:GPSCoordinates"], "+39.90872+116.39750/")
        self.assertNotIn("ItemList:GPSCoordinates", assignments)

    def test_uses_only_supported_quicktime_location_tags(self) -> None:
        assignments = dict(
            build_tag_assignments(
                {
                    "location_name": "审计地点",
                    "gps_latitude": "39.908722",
                    "gps_longitude": "116.397499",
                },
                target_path="clip.mov",
            )
        )

        self.assertEqual(assignments["Keys:LocationName"], "审计地点")
        self.assertNotIn("ItemList:LocationName", assignments)
        self.assertIn("UserData:GPSCoordinates", assignments)

    def test_does_not_add_quicktime_assignments_for_jpeg_targets(self) -> None:
        assignments = dict(build_tag_assignments({"title": "Still"}, target_path="photo.jpg"))

        self.assertIn("XMP-dc:Title", assignments)
        self.assertNotIn("Keys:Title", assignments)

    def test_does_not_write_readonly_photo_fact_fields(self) -> None:
        assignments = build_tag_assignments({"file_name": "IMG_6846.HEIC", "file_type": "HEIF", "iso": "125", "image_size": "3024x4032"})

        self.assertEqual(assignments, [])

    def test_extracts_signed_gps_values(self) -> None:
        values = extract_field_values(
            {
                "GPS:GPSLatitude": 31.2304,
                "GPS:GPSLatitudeRef": "South",
                "GPS:GPSLongitude": "121.47370000",
                "GPS:GPSLongitudeRef": "East",
            }
        )

        self.assertEqual(values["gps_latitude"], "-31.2304")
        self.assertEqual(values["gps_longitude"], "121.4737")

    def test_extracts_west_gps_with_single_letter_ref(self) -> None:
        values = extract_field_values(
            {
                "GPS:GPSLongitude": 121.4737,
                "GPS:GPSLongitudeRef": "W",
            }
        )

        self.assertEqual(values["gps_longitude"], "-121.4737")

    def test_preserves_signed_composite_gps_without_ref(self) -> None:
        values = extract_field_values(
            {
                "Composite:GPSLatitude": "-33.856784",
                "Composite:GPSLongitude": "151.215297",
            }
        )

        self.assertEqual(values["gps_latitude"], "-33.856784")
        self.assertEqual(values["gps_longitude"], "151.215297")

    def test_extracts_combined_gps_coordinates(self) -> None:
        values = extract_field_values({"QuickTime:GPSCoordinates": "33.856784 S 151.215297 E"})

        self.assertEqual(values["gps_latitude"], "-33.856784")
        self.assertEqual(values["gps_longitude"], "151.215297")

    def test_rejects_malformed_combined_gps_instead_of_taking_first_two_numbers(self) -> None:
        values = extract_field_values({"QuickTime:GPSCoordinates": "31 degrees 99 minutes 20 seconds, 121 degrees 28 minutes 25 seconds"})

        self.assertEqual(values["gps_latitude"], "")
        self.assertEqual(values["gps_longitude"], "")

    def test_extracts_dms_gps_coordinates_with_direction(self) -> None:
        values = extract_field_values(
            {
                "Composite:GPSLatitude": "31 13 49.44 S",
                "Composite:GPSLongitude": "121 28 25.32 W",
            }
        )

        self.assertEqual(values["gps_latitude"], "-31.2304")
        self.assertEqual(values["gps_longitude"], "-121.4737")

    def test_extracts_combined_dms_gps_coordinates(self) -> None:
        values = extract_field_values({"QuickTime:GPSCoordinates": "31 13 49.44 S 121 28 25.32 W"})

        self.assertEqual(values["gps_latitude"], "-31.2304")
        self.assertEqual(values["gps_longitude"], "-121.4737")

    def test_extracts_combined_degrees_minutes_gps_coordinates(self) -> None:
        values = extract_field_values(
            {"QuickTime:GPSCoordinates": "31 deg 13.824' S, 121 deg 28.422' W"}
        )

        self.assertEqual(values["gps_latitude"], "-31.2304")
        self.assertEqual(values["gps_longitude"], "-121.4737")

    def test_extracts_iso6709_gps_coordinates(self) -> None:
        values = extract_field_values({"Keys:GPSCoordinates": "+39.908722+116.397499/"})

        self.assertEqual(values["gps_latitude"], "39.908722")
        self.assertEqual(values["gps_longitude"], "116.397499")

    def test_filters_metadata_rows(self) -> None:
        rows = metadata_rows({"IFD0:Make": "Apple", "File:FileSize": "1 MB"}, "make")

        self.assertEqual(rows, [("IFD0:Make", "Apple")])


if __name__ == "__main__":
    unittest.main()
