from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CameraPreset:
    name: str
    make: str
    model: str
    software: str = ""


@dataclass(frozen=True)
class LocationPreset:
    name: str
    latitude: float
    longitude: float


CAMERA_PRESETS: tuple[CameraPreset, ...] = (
    CameraPreset("Apple iPhone 11", "Apple", "iPhone 11", "iOS"),
    CameraPreset("Apple iPhone 11 Pro", "Apple", "iPhone 11 Pro", "iOS"),
    CameraPreset("Apple iPhone 11 Pro Max", "Apple", "iPhone 11 Pro Max", "iOS"),
    CameraPreset("Apple iPhone 12", "Apple", "iPhone 12", "iOS"),
    CameraPreset("Apple iPhone 12 Pro", "Apple", "iPhone 12 Pro", "iOS"),
    CameraPreset("Apple iPhone 12 Pro Max", "Apple", "iPhone 12 Pro Max", "iOS"),
    CameraPreset("Apple iPhone 13", "Apple", "iPhone 13", "iOS"),
    CameraPreset("Apple iPhone 13 Pro", "Apple", "iPhone 13 Pro", "iOS"),
    CameraPreset("Apple iPhone 13 Pro Max", "Apple", "iPhone 13 Pro Max", "iOS"),
    CameraPreset("Apple iPhone 14", "Apple", "iPhone 14", "iOS"),
    CameraPreset("Apple iPhone 14 Pro", "Apple", "iPhone 14 Pro", "iOS"),
    CameraPreset("Apple iPhone 14 Pro Max", "Apple", "iPhone 14 Pro Max", "iOS"),
    CameraPreset("Apple iPhone 15", "Apple", "iPhone 15", "iOS"),
    CameraPreset("Apple iPhone 15 Pro", "Apple", "iPhone 15 Pro", "iOS"),
    CameraPreset("Apple iPhone 15 Pro Max", "Apple", "iPhone 15 Pro Max", "iOS"),
    CameraPreset("Apple iPhone 16", "Apple", "iPhone 16", "iOS"),
    CameraPreset("Apple iPhone 16 Pro", "Apple", "iPhone 16 Pro", "iOS"),
    CameraPreset("Apple iPhone 16 Pro Max", "Apple", "iPhone 16 Pro Max", "iOS"),
    CameraPreset("Apple iPhone 17", "Apple", "iPhone 17", "iOS"),
    CameraPreset("Apple iPhone 17 Pro", "Apple", "iPhone 17 Pro", "iOS"),
    CameraPreset("Apple iPhone 17 Pro Max", "Apple", "iPhone 17 Pro Max", "iOS"),
    CameraPreset("Samsung Galaxy S21 Ultra", "samsung", "SM-G998B", "Android"),
    CameraPreset("Samsung Galaxy S22 Ultra", "samsung", "SM-S908B", "Android"),
    CameraPreset("Samsung Galaxy S23 Ultra", "samsung", "SM-S918B", "Android"),
    CameraPreset("Samsung Galaxy S24 Ultra", "samsung", "SM-S928B", "Android"),
    CameraPreset("Samsung Galaxy S25 Ultra", "samsung", "SM-S938B", "Android"),
    CameraPreset("Samsung Galaxy Z Fold6", "samsung", "SM-F956B", "Android"),
    CameraPreset("Canon EOS R5", "Canon", "Canon EOS R5", "Digital Photo Professional"),
    CameraPreset("Canon EOS R6 Mark II", "Canon", "Canon EOS R6 Mark II", "Digital Photo Professional"),
    CameraPreset("Canon EOS R7", "Canon", "Canon EOS R7", "Digital Photo Professional"),
    CameraPreset("Canon EOS R8", "Canon", "Canon EOS R8", "Digital Photo Professional"),
    CameraPreset("Canon EOS R10", "Canon", "Canon EOS R10", "Digital Photo Professional"),
    CameraPreset("Canon EOS 5D Mark IV", "Canon", "Canon EOS 5D Mark IV", "Digital Photo Professional"),
    CameraPreset("Ricoh GR III", "RICOH IMAGING COMPANY, LTD.", "RICOH GR III", ""),
    CameraPreset("Ricoh GR IIIx", "RICOH IMAGING COMPANY, LTD.", "RICOH GR IIIx", ""),
    CameraPreset("Fujifilm X100V", "FUJIFILM", "X100V", ""),
    CameraPreset("Fujifilm X100VI", "FUJIFILM", "X100VI", ""),
    CameraPreset("Fujifilm X-T5", "FUJIFILM", "X-T5", ""),
    CameraPreset("Fujifilm X-H2", "FUJIFILM", "X-H2", ""),
    CameraPreset("Fujifilm GFX100 II", "FUJIFILM", "GFX100 II", ""),
)


LOCATION_PRESETS: tuple[LocationPreset, ...] = (
    LocationPreset("北京 天安门", 39.908722, 116.397499),
    LocationPreset("上海 外滩", 31.240000, 121.490000),
    LocationPreset("深圳 市民中心", 22.543096, 114.057865),
    LocationPreset("广州 珠江新城", 23.120049, 113.323568),
    LocationPreset("杭州 西湖", 30.259244, 120.130260),
    LocationPreset("成都 天府广场", 30.657000, 104.066000),
    LocationPreset("重庆 解放碑", 29.563760, 106.581210),
    LocationPreset("武汉 江汉路", 30.584355, 114.298572),
    LocationPreset("西安 钟楼", 34.261004, 108.942336),
    LocationPreset("南京 新街口", 32.042420, 118.784800),
    LocationPreset("香港 中环", 22.281900, 114.158900),
    LocationPreset("台北 101", 25.033964, 121.564468),
    LocationPreset("东京 Shinjuku", 35.689487, 139.691706),
    LocationPreset("首尔 Gangnam", 37.497942, 127.027621),
    LocationPreset("新加坡 Marina Bay", 1.283400, 103.860700),
    LocationPreset("伦敦 Westminster", 51.500729, -0.124625),
    LocationPreset("巴黎 Eiffel Tower", 48.858370, 2.294481),
    LocationPreset("纽约 Times Square", 40.758896, -73.985130),
    LocationPreset("洛杉矶 Hollywood", 34.101600, -118.326900),
    LocationPreset("旧金山 Golden Gate", 37.819929, -122.478255),
    LocationPreset("悉尼 Opera House", -33.856784, 151.215297),
)


def camera_preset_names() -> list[str]:
    return [preset.name for preset in CAMERA_PRESETS]


def location_preset_names() -> list[str]:
    return [preset.name for preset in LOCATION_PRESETS]


def find_camera_preset(name: str) -> CameraPreset | None:
    return next((preset for preset in CAMERA_PRESETS if preset.name == name), None)


def find_location_preset(name: str) -> LocationPreset | None:
    return next((preset for preset in LOCATION_PRESETS if preset.name == name), None)

