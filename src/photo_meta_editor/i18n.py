from __future__ import annotations

import re


DEFAULT_LANGUAGE = "zh_CN"
SUPPORTED_LANGUAGES = ("zh_CN", "en")
LANGUAGE_LABELS = {"zh_CN": "中文", "en": "English"}
LANGUAGE_BY_LABEL = {label: language for language, label in LANGUAGE_LABELS.items()}


ENGLISH_TEXT = {
    "可编辑信息 / 照片参数": "Editable metadata / Photo details",
    "全部元数据": "All metadata",
    "文件": "File",
    "选择": "Open",
    "刷新": "Reload",
    "保存修改": "Save changes",
    "关于": "About",
    "暗色": "Dark",
    "拖拽图片或视频文件到这里导入": "Drop an image or video file here",
    "拖拽组件不可用，请使用“选择”导入": "Drag and drop is unavailable; use Open instead",
    "相机预设": "Camera preset",
    "套用相机": "Apply camera",
    "地点预设": "Location preset",
    "套用GPS": "Apply GPS",
    "OCR识别时间": "Read time with OCR",
    "保留 _original 备份": "Keep _original backup",
    "保存时同步文件创建/修改时间": "Sync file created/modified time when saving",
    "恢复备份": "Restore backup",
    "可编辑信息": "Editable metadata",
    "照片参数（只读）": "Photo details (read-only)",
    "筛选": "Filter",
    "标签": "Tag",
    "值": "Value",
    "标题": "Title",
    "文件名": "File name",
    "描述": "Description",
    "关键词": "Keywords",
    "多个关键词用分号分隔": "Separate multiple keywords with semicolons",
    "作者": "Creator",
    "版权": "Copyright",
    "拍摄时间": "Date taken",
    "格式：YYYY:MM:DD HH:MM:SS": "Format: YYYY:MM:DD HH:MM:SS",
    "相机厂商": "Camera make",
    "相机型号": "Camera model",
    "软件": "Software",
    "GPS 纬度": "GPS latitude",
    "十进制度数，南纬用负数": "Decimal degrees; use a negative value for south",
    "GPS 经度": "GPS longitude",
    "十进制度数，西经用负数": "Decimal degrees; use a negative value for west",
    "地点名称": "Location name",
    "文件格式": "File format",
    "尺寸": "Dimensions",
    "像素": "Megapixels",
    "文件大小": "File size",
    "镜头/相机": "Lens / Camera",
    "焦距": "Focal length",
    "曝光补偿": "Exposure compensation",
    "光圈": "Aperture",
    "快门速度": "Shutter speed",
    "未检测到本地OCR引擎": "No local OCR engine detected",
    "拖拽数据无法解析，请使用“选择”导入。": "The dropped data could not be parsed. Use Open instead.",
    "选择图片或媒体文件": "Select an image or media file",
    "媒体文件": "Media files",
    "图片文件": "Image files",
    "所有文件": "All files",
    "导入新文件": "open another file",
    "重新读取当前文件": "reload the current file",
    "关闭窗口": "close the window",
    "已取消相机预设，保留手动修改": "Camera preset cleared; manual changes kept",
    "已取消GPS预设，保留手动修改": "GPS preset cleared; manual changes kept",
    "未保存修改": "Unsaved changes",
    "未选择相机": "No camera preset selected",
    "请先选择一个相机预设。": "Select a camera preset first.",
    "未选择地点": "No location preset selected",
    "请先选择一个地点预设。": "Select a location preset first.",
    "未导入文件": "No file loaded",
    "请先导入一张图片。": "Load an image first.",
    "OCR识别完成": "OCR completed",
    "没有备份": "No backup",
    "当前文件没有可恢复的 _original 备份。": "The current file has no restorable _original backup.",
    "恢复原始备份": "Restore original backup",
    "将恢复 ExifTool 创建的 _original 备份。\n\n当前文件会先保存为 _before_restore 备份，然后被原始版本替换。": (
        "The _original backup created by ExifTool will be restored.\n\n"
        "The current file will first be saved as a unique _before_restore backup, then replaced by the original version."
    ),
    "恢复完成": "Restore completed",
    "缺少时间": "Missing date",
    "同步文件时间需要先填写拍摄时间。": "Enter a date taken before synchronizing file times.",
    "没有变化": "No changes",
    "当前没有需要保存的字段。": "There are no changes to save.",
    "保存完成": "Save completed",
    "关闭": "Close",
    "正在写入元数据": "Writing metadata",
    "正在恢复原始备份": "Restoring original backup",
    "正在OCR识别图片时间": "Reading image time with OCR",
    "元数据已写入。": "Metadata was written.",
    "操作失败": "Operation failed",
    "OCR失败": "OCR failed",
    "正在处理": "Operation in progress",
    "处理文件": "processing a file",
    "写入元数据": "writing metadata",
    "读取元数据": "reading metadata",
    "OCR识别": "running OCR",
    "启动失败": "Startup failed",
    "测试清理": "Test cleanup",
    "就绪": "Ready",
}


def translate_text(text: str, language: str) -> str:
    if language != "en" or not text:
        return text
    exact = ENGLISH_TEXT.get(text)
    if exact is not None:
        return exact

    patterns: tuple[tuple[str, object], ...] = (
        (r"^ExifTool 已就绪；OCR：(.*)$", lambda m: f"ExifTool ready; OCR: {translate_text(m.group(1), language)}"),
        (r"^正在读取：(.*)$", lambda m: f"Reading: {m.group(1)}"),
        (r"^已套用相机：(.*)$", lambda m: f"Camera preset applied: {m.group(1)}"),
        (r"^已套用GPS：(.*)$", lambda m: f"GPS preset applied: {m.group(1)}"),
        (r"^已套用(.*)预设$", lambda m: f"Applied {m.group(1).replace('、', ' and ')} preset(s)"),
        (r"^(.*) 识别到时间：(.*)$", lambda m: f"{m.group(1)} detected time: {m.group(2)}"),
        (r"^已恢复原始备份；恢复前版本已保存为：(.*)$", lambda m: f"Original restored; previous version saved as: {m.group(1)}"),
        (r"^界面更新失败：(.*)$", lambda m: f"UI update failed: {m.group(1)}"),
        (r"^发生未知错误：(.*)$", lambda m: f"Unexpected error: {m.group(1)}"),
        (r"^OCR失败：(.*)$", lambda m: f"OCR failed: {m.group(1)}"),
        (r"^后台任务异常终止：(.*)$", lambda m: f"Background task terminated unexpectedly: {m.group(1)}"),
        (r"^无法启动后台任务：(.*)$", lambda m: f"Unable to start background task: {m.group(1)}"),
        (r"^关于 (.*)$", lambda m: f"About {m.group(1)}"),
        (r"^版本：(.*)$", lambda m: f"Version: {m.group(1)}"),
        (r"^创作者：(.*)$", lambda m: f"Creator: {m.group(1)}"),
        (r"^邮箱：(.*)$", lambda m: f"Email: {m.group(1)}"),
        (r"^网站：(.*)$", lambda m: f"Website: {m.group(1)}"),
    )
    for pattern, formatter in patterns:
        match = re.match(pattern, text, flags=re.DOTALL)
        if match:
            return formatter(match)  # type: ignore[operator]

    prefill = re.match(r"^已预填 (\d+) 个字段(.*?)，读取 (\d+) 个元数据标签$", text)
    if prefill:
        suffix = prefill.group(2)
        if suffix.startswith("，并套用") and suffix.endswith("预设"):
            names = suffix[len("，并套用") : -len("预设")].replace("、", " and ")
            suffix = f" and applied {names} preset(s)"
        return f"Prefilled {prefill.group(1)} fields{suffix}; read {prefill.group(3)} metadata tags"

    unsaved = re.match(
        r"^当前文件有未保存修改。\n\n选择“是”先保存，选择“否”放弃修改并(.*)，选择“取消”继续编辑。$",
        text,
        flags=re.DOTALL,
    )
    if unsaved:
        action = translate_text(unsaved.group(1), language)
        return (
            "The current file has unsaved changes.\n\n"
            f"Choose Yes to save first, No to discard changes and {action}, or Cancel to continue editing."
        )

    busy = re.match(r"^正在(.*)，请等待完成后再关闭。$", text, flags=re.DOTALL)
    if busy:
        task = translate_text(busy.group(1), language)
        return f"The application is {task}. Wait for it to finish before closing."
    return text
