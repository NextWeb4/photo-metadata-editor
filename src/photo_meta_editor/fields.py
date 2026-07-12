from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import re
from typing import Any, Mapping


@dataclass(frozen=True)
class FieldSpec:
    key: str
    label: str
    read_tags: tuple[str, ...]
    write_tags: tuple[str, ...] = ()
    multiline: bool = False
    help_text: str = ""
    readonly: bool = False


EDITABLE_FIELDS: tuple[FieldSpec, ...] = (
    FieldSpec(
        key="title",
        label="标题",
        read_tags=("XMP-dc:Title", "XMP:Title", "IPTC:ObjectName", "IFD0:XPTitle", "Keys:Title", "ItemList:Title"),
        write_tags=("XMP-dc:Title", "IPTC:ObjectName", "IFD0:XPTitle"),
    ),
    FieldSpec(
        key="file_name",
        label="文件名",
        read_tags=("System:FileName", "File:FileName", "SourceFile"),
        readonly=True,
    ),
    FieldSpec(
        key="description",
        label="描述",
        read_tags=(
            "XMP-dc:Description",
            "XMP:Description",
            "IFD0:ImageDescription",
            "EXIF:ImageDescription",
            "IPTC:Caption-Abstract",
            "IFD0:XPComment",
            "Keys:Description",
            "ItemList:Description",
        ),
        write_tags=("XMP-dc:Description", "IFD0:ImageDescription", "IPTC:Caption-Abstract", "IFD0:XPComment"),
        multiline=True,
    ),
    FieldSpec(
        key="keywords",
        label="关键词",
        read_tags=("XMP-dc:Subject", "XMP:Subject", "IPTC:Keywords", "IFD0:XPKeywords"),
        write_tags=("XMP-dc:Subject", "IPTC:Keywords", "IFD0:XPKeywords"),
        help_text="多个关键词用分号分隔",
    ),
    FieldSpec(
        key="creator",
        label="作者",
        read_tags=(
            "XMP-dc:Creator",
            "XMP:Creator",
            "IFD0:Artist",
            "EXIF:Artist",
            "IPTC:By-line",
            "IFD0:XPAuthor",
            "Keys:Author",
            "ItemList:Author",
        ),
        write_tags=("XMP-dc:Creator", "IFD0:Artist", "IPTC:By-line", "IFD0:XPAuthor"),
    ),
    FieldSpec(
        key="copyright",
        label="版权",
        read_tags=("XMP-dc:Rights", "XMP:Rights", "IFD0:Copyright", "EXIF:Copyright", "IPTC:CopyrightNotice"),
        write_tags=("XMP-dc:Rights", "IFD0:Copyright", "IPTC:CopyrightNotice"),
    ),
    FieldSpec(
        key="date_taken",
        label="拍摄时间",
        read_tags=(
            "ExifIFD:DateTimeOriginal",
            "EXIF:DateTimeOriginal",
            "XMP-exif:DateTimeOriginal",
            "XMP:DateTimeOriginal",
            "QuickTime:CreateDate",
            "QuickTime:CreationDate",
            "QuickTime:MediaCreateDate",
            "QuickTime:TrackCreateDate",
            "Track1:MediaCreateDate",
            "Track1:TrackCreateDate",
            "Keys:CreationDate",
            "ItemList:ContentCreateDate",
            "System:FileModifyDate",
            "File:FileModifyDate",
        ),
        write_tags=("ExifIFD:DateTimeOriginal", "XMP-exif:DateTimeOriginal"),
        help_text="格式：YYYY:MM:DD HH:MM:SS",
    ),
    FieldSpec(
        key="make",
        label="相机厂商",
        read_tags=("IFD0:Make", "EXIF:Make", "QuickTime:Make", "Keys:Make", "UserData:Make"),
        write_tags=("IFD0:Make",),
    ),
    FieldSpec(
        key="model",
        label="相机型号",
        read_tags=("IFD0:Model", "EXIF:Model", "QuickTime:Model", "Keys:Model", "UserData:Model"),
        write_tags=("IFD0:Model",),
    ),
    FieldSpec(
        key="software",
        label="软件",
        read_tags=(
            "IFD0:Software",
            "EXIF:Software",
            "XMP-xmp:CreatorTool",
            "XMP:CreatorTool",
            "QuickTime:Software",
            "Keys:Software",
            "UserData:SoftwareVersion",
        ),
        write_tags=("IFD0:Software", "XMP-xmp:CreatorTool"),
    ),
    FieldSpec(
        key="gps_latitude",
        label="GPS 纬度",
        read_tags=("GPS:GPSLatitude", "Composite:GPSLatitude"),
        help_text="十进制度数，南纬用负数",
    ),
    FieldSpec(
        key="gps_longitude",
        label="GPS 经度",
        read_tags=("GPS:GPSLongitude", "Composite:GPSLongitude"),
        help_text="十进制度数，西经用负数",
    ),
    FieldSpec(
        key="location_name",
        label="地点名称",
        read_tags=(
            "XMP-iptcCore:Location",
            "XMP:Location",
            "IPTC:Sub-location",
            "Keys:LocationName",
            "ItemList:LocationName",
        ),
        write_tags=("XMP-iptcCore:Location", "IPTC:Sub-location"),
    ),
    FieldSpec(
        key="file_type",
        label="文件格式",
        read_tags=("File:FileType", "File:FileTypeExtension", "QuickTime:MajorBrand"),
        readonly=True,
    ),
    FieldSpec(
        key="image_size",
        label="尺寸",
        read_tags=("Composite:ImageSize", "File:ImageSize"),
        readonly=True,
    ),
    FieldSpec(
        key="megapixels",
        label="像素",
        read_tags=("Composite:Megapixels",),
        readonly=True,
    ),
    FieldSpec(
        key="file_size",
        label="文件大小",
        read_tags=("File:FileSize", "System:FileSize"),
        readonly=True,
    ),
    FieldSpec(
        key="lens_model",
        label="镜头/相机",
        read_tags=("ExifIFD:LensModel", "EXIF:LensModel", "Composite:LensID", "QuickTime:LensModel", "Keys:LensModel"),
        readonly=True,
    ),
    FieldSpec(
        key="iso",
        label="ISO",
        read_tags=("ExifIFD:ISO", "EXIF:ISO", "Composite:ISO"),
        readonly=True,
    ),
    FieldSpec(
        key="focal_length",
        label="焦距",
        read_tags=("ExifIFD:FocalLength", "EXIF:FocalLength", "Composite:FocalLength"),
        readonly=True,
    ),
    FieldSpec(
        key="exposure_compensation",
        label="曝光补偿",
        read_tags=("ExifIFD:ExposureCompensation", "EXIF:ExposureCompensation"),
        readonly=True,
    ),
    FieldSpec(
        key="aperture",
        label="光圈",
        read_tags=("ExifIFD:FNumber", "EXIF:FNumber", "Composite:Aperture"),
        readonly=True,
    ),
    FieldSpec(
        key="exposure_time",
        label="快门速度",
        read_tags=("ExifIFD:ExposureTime", "EXIF:ExposureTime", "Composite:ShutterSpeed"),
        readonly=True,
    ),
)


FIELD_BY_KEY = {field.key: field for field in EDITABLE_FIELDS}
DATE_RE = re.compile(r"^\d{4}:\d{2}:\d{2} \d{2}:\d{2}:\d{2}$")
USER_DATE_RE = re.compile(
    r"^\s*(?P<year>\d{4})\s*[:/\-.年]\s*(?P<month>\d{1,2})\s*[:/\-.月]\s*(?P<day>\d{1,2})"
    r"(?:\s*日)?(?:[\sT_]+(?P<hour>\d{1,2})[:：](?P<minute>\d{2})(?:[:：](?P<second>\d{2}))?)?\s*$"
)
METADATA_DATE_RE = re.compile(r"(\d{4})[:\-/\.](\d{1,2})[:\-/\.](\d{1,2})[ T](\d{1,2}):(\d{2}):(\d{2})")
IPHONE_MODEL_RE = re.compile(r"iphone\s*(?P<number>1[1-9])\s*(?P<tier>pro\s*max|pro|max|plus|mini)?", re.IGNORECASE)
GPS_NUMBER_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")
ISO6709_RE = re.compile(r"(?P<lat>[+-]\d{1,2}(?:\.\d+)?)(?P<lon>[+-]\d{1,3}(?:\.\d+)?)")
GPS_DIRECTION_RE = re.compile(r"(?<![A-Za-z])(north|south|east|west|[NSEW])(?![A-Za-z])", re.IGNORECASE)
GPS_DMS_RE = re.compile(
    r"(?P<deg>[-+]?\d+(?:\.\d+)?)\D+"
    r"(?P<minute>\d+(?:\.\d+)?)\D+"
    r"(?P<second>\d+(?:\.\d+)?)"
    r"(?:\s*(?P<direction>north|south|east|west|[NSEW]))?",
    re.IGNORECASE,
)
GPS_DM_RE = re.compile(
    r"(?P<deg>[-+]?\d+(?:\.\d+)?)\D+"
    r"(?P<minute>\d+(?:\.\d+)?)\s*(?:['′]|min(?:ute)?s?)\s*"
    r"(?P<direction>north|south|east|west|[NSEW])",
    re.IGNORECASE,
)
DECIMAL_GPS_PAIR_RE = re.compile(
    r"^\s*"
    r"(?P<latitude>[-+]?\d+(?:\.\d+)?)\s*"
    r"(?P<latitude_direction>north|south|[NS])?\s*"
    r"(?:,|;|\s+)\s*"
    r"(?P<longitude>[-+]?\d+(?:\.\d+)?)\s*"
    r"(?P<longitude_direction>east|west|[EW])?\s*/?\s*$",
    re.IGNORECASE,
)
COMBINED_GPS_TAGS = (
    "Composite:GPSPosition",
    "Composite:GPSCoordinates",
    "QuickTime:GPSCoordinates",
    "Keys:GPSCoordinates",
    "UserData:GPSCoordinates",
    "ItemList:GPSCoordinates",
)
QUICKTIME_EXTENSIONS = {".mov", ".mp4", ".m4v", ".heic", ".heif"}
QUICKTIME_GPS_DECIMALS = 5
QUICKTIME_WRITE_TAGS: dict[str, tuple[str, ...]] = {
    "title": ("ItemList:Title", "Keys:Title"),
    "description": ("ItemList:Description", "Keys:Description"),
    "keywords": ("Keys:Keywords",),
    "creator": ("ItemList:Author", "Keys:Author"),
    "copyright": ("ItemList:Copyright", "Keys:Copyright"),
    "date_taken": (
        "QuickTime:CreateDate",
        "QuickTime:TrackCreateDate",
        "QuickTime:MediaCreateDate",
        "Keys:CreationDate",
        "ItemList:ContentCreateDate",
    ),
    "make": ("Keys:Make", "UserData:Make"),
    "model": ("Keys:Model", "UserData:Model"),
    "software": ("Keys:Software", "UserData:SoftwareVersion"),
    # LocationName and GPSCoordinates are not ItemList tags.  Writing them there
    # makes ExifTool update the media but return a warning, which previously made
    # the UI report a failed save after a partial write.
    "location_name": ("Keys:LocationName",),
}
QUICKTIME_GPS_TAGS = ("Keys:GPSCoordinates", "UserData:GPSCoordinates")
FILE_TIME_DATE_TAGS = ("System:FileModifyDate", "File:FileModifyDate")


def stringify_metadata_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "; ".join(stringify_metadata_value(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def first_present(metadata: Mapping[str, Any], tags: tuple[str, ...]) -> str:
    for tag in tags:
        if tag in metadata and metadata[tag] not in (None, ""):
            return stringify_metadata_value(metadata[tag])
    return ""


def extract_field_values(
    metadata: Mapping[str, Any],
    use_file_name_as_title: bool = True,
    infer_camera_from_lens: bool = True,
    use_file_time_as_date: bool = True,
) -> dict[str, str]:
    values: dict[str, str] = {}
    for field in EDITABLE_FIELDS:
        read_tags = field.read_tags
        if field.key == "date_taken" and not use_file_time_as_date:
            read_tags = tuple(tag for tag in read_tags if tag not in FILE_TIME_DATE_TAGS)
        values[field.key] = first_present(metadata, read_tags)
    if use_file_name_as_title and not values.get("title"):
        values["title"] = file_stem_from_metadata(metadata)
    fill_derived_photo_info(values, metadata)
    if values.get("date_taken"):
        values["date_taken"] = normalize_metadata_datetime(values["date_taken"])
    if infer_camera_from_lens:
        inferred_make, inferred_model = infer_camera_from_metadata(metadata)
        if inferred_make and not values.get("make"):
            values["make"] = inferred_make
        if inferred_model and not values.get("model"):
            values["model"] = inferred_model
    latitude = signed_gps_value(metadata, "GPS:GPSLatitude", "GPS:GPSLatitudeRef", "Composite:GPSLatitude")
    longitude = signed_gps_value(metadata, "GPS:GPSLongitude", "GPS:GPSLongitudeRef", "Composite:GPSLongitude")
    combined_latitude, combined_longitude = combined_gps_values(metadata)
    if not latitude and combined_latitude:
        latitude = combined_latitude
    if not longitude and combined_longitude:
        longitude = combined_longitude
    if latitude:
        values["gps_latitude"] = latitude
    if longitude:
        values["gps_longitude"] = longitude
    return values


def fill_derived_photo_info(values: dict[str, str], metadata: Mapping[str, Any]) -> None:
    if values.get("file_name"):
        values["file_name"] = values["file_name"].replace("\\", "/").rsplit("/", 1)[-1]
    if not values.get("file_type"):
        file_type = first_present(metadata, ("File:FileTypeExtension", "File:FileType", "System:FileExtension"))
        values["file_type"] = file_type.upper() if file_type else ""
    if not values.get("image_size"):
        width = first_present(metadata, ("File:ImageWidth", "EXIF:ExifImageWidth", "Composite:ImageWidth"))
        height = first_present(metadata, ("File:ImageHeight", "EXIF:ExifImageHeight", "Composite:ImageHeight"))
        if width and height:
            values["image_size"] = f"{width}x{height}"
    if values.get("megapixels") and "mp" not in values["megapixels"].casefold():
        values["megapixels"] = f"{values['megapixels']} MP"
    if values.get("aperture") and not values["aperture"].casefold().startswith("f/"):
        values["aperture"] = f"f/{values['aperture']}"
    if values.get("focal_length") and "mm" not in values["focal_length"].casefold():
        values["focal_length"] = f"{values['focal_length']} mm"
    if values.get("exposure_compensation") and "ev" not in values["exposure_compensation"].casefold():
        values["exposure_compensation"] = f"{values['exposure_compensation']} ev"
    if values.get("exposure_time"):
        folded = values["exposure_time"].casefold()
        if "s" not in folded and "sec" not in folded:
            values["exposure_time"] = f"{values['exposure_time']} s"


def file_stem_from_metadata(metadata: Mapping[str, Any]) -> str:
    file_name = first_present(metadata, ("System:FileName", "File:FileName", "SourceFile"))
    if not file_name:
        return ""
    normalized = file_name.replace("\\", "/").rsplit("/", 1)[-1]
    if "." in normalized:
        return normalized.rsplit(".", 1)[0]
    return normalized


def normalize_metadata_datetime(value: str) -> str:
    match = METADATA_DATE_RE.search(value.strip())
    if not match:
        return value.strip()
    normalized = normalize_datetime_parts(match.group(1), match.group(2), match.group(3), match.group(4), match.group(5), match.group(6))
    # QuickTime uses an all-zero timestamp after clearing some creation-date
    # atoms. It is a container sentinel, not a valid editable capture time.
    if normalized == "0000:00:00 00:00:00":
        return ""
    return normalized


def normalize_datetime_parts(
    year: str,
    month: str,
    day: str,
    hour: str | None = None,
    minute: str | None = None,
    second: str | None = None,
) -> str:
    return f"{int(year):04d}:{int(month):02d}:{int(day):02d} {int(hour or 0):02d}:{int(minute or 0):02d}:{int(second or 0):02d}"


def normalize_user_datetime(value: str) -> str:
    match = USER_DATE_RE.match(value)
    if not match:
        return value.strip()
    return normalize_datetime_parts(
        match.group("year"),
        match.group("month"),
        match.group("day"),
        match.group("hour"),
        match.group("minute"),
        match.group("second"),
    )


def infer_camera_from_metadata(metadata: Mapping[str, Any]) -> tuple[str, str]:
    lens_make = first_present(metadata, ("ExifIFD:LensMake", "EXIF:LensMake"))
    iphone_model = normalize_iphone_model(lens_make)
    if iphone_model:
        return "Apple", iphone_model
    return "", ""


def normalize_iphone_model(value: str) -> str:
    match = IPHONE_MODEL_RE.search(value)
    if not match:
        return ""
    tier = (match.group("tier") or "").lower().replace(" ", "")
    tier_label = {
        "pro": " Pro",
        "promax": " Pro Max",
        "max": " Max",
        "plus": " Plus",
        "mini": " mini",
    }.get(tier, "")
    return f"iPhone {match.group('number')}{tier_label}"


def signed_gps_value(metadata: Mapping[str, Any], value_tag: str, ref_tag: str, composite_tag: str) -> str:
    raw_value = first_present(metadata, (value_tag, composite_tag))
    if not raw_value:
        return ""
    axis = "lat" if "Latitude" in value_tag else "lon"
    parsed = parse_gps_coordinate(raw_value, axis=axis, ref_value=first_present(metadata, (ref_tag,)))
    if parsed:
        return parsed
    return raw_value

def parse_gps_coordinate(raw_value: str, axis: str, ref_value: str = "") -> str:
    limit = 90.0 if axis == "lat" else 180.0
    dms_value = parse_dms_coordinate(raw_value, axis=axis, ref_value=ref_value)
    if dms_value is not None and -limit <= dms_value <= limit:
        return format_gps_number(dms_value)

    dm_value = parse_dm_coordinate(raw_value, axis=axis, ref_value=ref_value)
    if dm_value is not None and -limit <= dm_value <= limit:
        return format_gps_number(dm_value)

    match = GPS_NUMBER_RE.search(raw_value)
    if not match:
        return ""

    number = float(match.group(0))
    direction = gps_direction(raw_value, axis=axis, ref_value=ref_value)
    if direction in {"S", "W"}:
        number = -abs(number)
    elif direction in {"N", "E"}:
        number = abs(number)
    if not -limit <= number <= limit:
        return ""
    return format_gps_number(number)


def parse_dms_coordinate(raw_value: str, axis: str, ref_value: str = "") -> float | None:
    match = GPS_DMS_RE.search(raw_value)
    if not match:
        return None
    degrees = float(match.group("deg"))
    minutes = float(match.group("minute"))
    seconds = float(match.group("second"))
    if not (0 <= minutes < 60 and 0 <= seconds < 60):
        return None
    number = abs(degrees) + minutes / 60 + seconds / 3600
    direction = gps_direction(match.group("direction") or raw_value, axis=axis, ref_value=ref_value)
    if degrees < 0 or direction in {"S", "W"}:
        number = -number
    return number


def parse_dm_coordinate(raw_value: str, axis: str, ref_value: str = "") -> float | None:
    match = GPS_DM_RE.search(raw_value)
    if not match:
        return None
    degrees = float(match.group("deg"))
    minutes = float(match.group("minute"))
    if not 0 <= minutes < 60:
        return None
    number = abs(degrees) + minutes / 60
    direction = gps_direction(match.group("direction"), axis=axis, ref_value=ref_value)
    if degrees < 0 or direction in {"S", "W"}:
        number = -number
    return number


def gps_direction(raw_value: str, axis: str, ref_value: str = "") -> str:
    candidates = [ref_value, raw_value]
    allowed = {"N", "S"} if axis == "lat" else {"E", "W"}
    for text in candidates:
        for match in GPS_DIRECTION_RE.finditer(text):
            token = match.group(1).casefold()
            direction = {
                "north": "N",
                "n": "N",
                "south": "S",
                "s": "S",
                "east": "E",
                "e": "E",
                "west": "W",
                "w": "W",
            }.get(token, "")
            if direction in allowed:
                return direction
    return ""


def format_gps_number(number: float) -> str:
    return f"{number:.8f}".rstrip("0").rstrip(".")


def format_iso6709(latitude: float, longitude: float) -> str:
    return f"{latitude:+.{QUICKTIME_GPS_DECIMALS}f}{longitude:+.{QUICKTIME_GPS_DECIMALS}f}/"


def is_quicktime_target(target_path: str | None = None) -> bool:
    if not target_path or "." not in target_path:
        return False
    return f".{target_path.rsplit('.', 1)[-1].casefold()}" in QUICKTIME_EXTENSIONS


def combined_gps_values(metadata: Mapping[str, Any]) -> tuple[str, str]:
    raw_value = first_present(metadata, COMBINED_GPS_TAGS)
    if not raw_value:
        return "", ""

    iso_match = ISO6709_RE.search(raw_value.strip())
    if iso_match:
        latitude = float(iso_match.group("lat"))
        longitude = float(iso_match.group("lon"))
        if -90 <= latitude <= 90 and -180 <= longitude <= 180:
            return format_gps_number(latitude), format_gps_number(longitude)

    dms_matches = list(GPS_DMS_RE.finditer(raw_value))
    if len(dms_matches) >= 2:
        latitude_text = dms_matches[0].group(0)
        longitude_text = dms_matches[1].group(0)
        latitude = parse_dms_coordinate(latitude_text, axis="lat")
        longitude = parse_dms_coordinate(longitude_text, axis="lon")
        if latitude is not None and longitude is not None and -90 <= latitude <= 90 and -180 <= longitude <= 180:
            return format_gps_number(latitude), format_gps_number(longitude)

    dm_matches = list(GPS_DM_RE.finditer(raw_value))
    if len(dm_matches) >= 2:
        latitude = parse_dm_coordinate(dm_matches[0].group(0), axis="lat")
        longitude = parse_dm_coordinate(dm_matches[1].group(0), axis="lon")
        if latitude is not None and longitude is not None and -90 <= latitude <= 90 and -180 <= longitude <= 180:
            return format_gps_number(latitude), format_gps_number(longitude)

    decimal_pair = DECIMAL_GPS_PAIR_RE.fullmatch(raw_value)
    if not decimal_pair:
        return "", ""

    latitude = float(decimal_pair.group("latitude"))
    longitude = float(decimal_pair.group("longitude"))
    latitude_direction = gps_direction(decimal_pair.group("latitude_direction") or "", axis="lat")
    longitude_direction = gps_direction(decimal_pair.group("longitude_direction") or "", axis="lon")
    if latitude_direction == "S":
        latitude = -abs(latitude)
    elif latitude_direction == "N":
        latitude = abs(latitude)
    if longitude_direction == "W":
        longitude = -abs(longitude)
    elif longitude_direction == "E":
        longitude = abs(longitude)
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return "", ""
    return format_gps_number(latitude), format_gps_number(longitude)


def normalize_changed_values(values: Mapping[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in values.items():
        cleaned = value.strip()
        if key == "date_taken":
            cleaned = normalize_user_datetime(cleaned)
        normalized[key] = cleaned
    return normalized


def validate_changed_values(values: Mapping[str, str]) -> list[str]:
    errors: list[str] = []
    normalized = normalize_changed_values(values)

    date_value = normalized.get("date_taken")
    if date_value:
        if not DATE_RE.match(date_value):
            errors.append("拍摄时间必须是 YYYY:MM:DD HH:MM:SS，例如 2026:07:08 12:30:00。")
        else:
            try:
                datetime.strptime(date_value, "%Y:%m:%d %H:%M:%S")
            except ValueError:
                errors.append("拍摄时间不是有效日期，例如不能填写 2026:02:31 12:30:00。")

    for key, label, minimum, maximum in (
        ("gps_latitude", "GPS 纬度", -90.0, 90.0),
        ("gps_longitude", "GPS 经度", -180.0, 180.0),
    ):
        raw_value = normalized.get(key)
        if not raw_value:
            continue
        try:
            value = float(raw_value)
        except ValueError:
            errors.append(f"{label}必须是数字。")
            continue
        if not minimum <= value <= maximum:
            errors.append(f"{label}必须在 {minimum:g} 到 {maximum:g} 之间。")

    latitude_changed = "gps_latitude" in normalized
    longitude_changed = "gps_longitude" in normalized
    if latitude_changed != longitude_changed:
        errors.append("GPS 纬度和经度必须同时修改，或同时清空。")
    elif latitude_changed and bool(normalized.get("gps_latitude")) != bool(normalized.get("gps_longitude")):
        errors.append("GPS 纬度和经度必须同时填写，或同时清空。")

    return errors


def build_tag_assignments(values: Mapping[str, str], target_path: str | None = None) -> list[tuple[str, str]]:
    normalized = normalize_changed_values(values)
    assignments: list[tuple[str, str]] = []
    quicktime_target = is_quicktime_target(target_path)

    for key, value in normalized.items():
        if key in {"gps_latitude", "gps_longitude"}:
            continue
        field = FIELD_BY_KEY.get(key)
        if not field or field.readonly:
            continue
        for tag in field.write_tags:
            assignments.append((tag, value))
        if quicktime_target:
            for tag in QUICKTIME_WRITE_TAGS.get(key, ()):
                assignments.append((tag, value))

    if "gps_latitude" in normalized:
        latitude = normalized["gps_latitude"]
        if latitude:
            number = float(latitude)
            assignments.append(("GPS:GPSLatitude", f"{abs(number):.8f}"))
            assignments.append(("GPS:GPSLatitudeRef", "N" if number >= 0 else "S"))
        else:
            assignments.append(("GPS:GPSLatitude", ""))
            assignments.append(("GPS:GPSLatitudeRef", ""))

    if "gps_longitude" in normalized:
        longitude = normalized["gps_longitude"]
        if longitude:
            number = float(longitude)
            assignments.append(("GPS:GPSLongitude", f"{abs(number):.8f}"))
            assignments.append(("GPS:GPSLongitudeRef", "E" if number >= 0 else "W"))
        else:
            assignments.append(("GPS:GPSLongitude", ""))
            assignments.append(("GPS:GPSLongitudeRef", ""))

    if quicktime_target and ("gps_latitude" in normalized or "gps_longitude" in normalized):
        latitude = normalized.get("gps_latitude", "")
        longitude = normalized.get("gps_longitude", "")
        quicktime_gps = format_iso6709(float(latitude), float(longitude)) if latitude and longitude else ""
        for tag in QUICKTIME_GPS_TAGS:
            assignments.append((tag, quicktime_gps))

    return assignments


def metadata_rows(metadata: Mapping[str, Any], filter_text: str = "") -> list[tuple[str, str]]:
    needle = filter_text.casefold().strip()
    rows = [(key, stringify_metadata_value(value)) for key, value in metadata.items()]
    if needle:
        rows = [(key, value) for key, value in rows if needle in key.casefold() or needle in value.casefold()]
    return sorted(rows, key=lambda row: row[0].casefold())
