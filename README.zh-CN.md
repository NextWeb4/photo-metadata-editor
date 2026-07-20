<p align="center">
  <a href="README.md"><img src="https://img.shields.io/badge/English-0969da?style=flat-square" alt="English"></a>
  <a href="README.zh-CN.md"><img src="https://img.shields.io/badge/%E7%AE%80%E4%BD%93%E4%B8%AD%E6%96%87-c8102e?style=flat-square" alt="简体中文"></a>
  <a href="README.ja.md"><img src="https://img.shields.io/badge/%E6%97%A5%E6%9C%AC%E8%AA%9E-8250df?style=flat-square" alt="日本語"></a>
</p>

# 照片元数据编辑器

一款由内置 ExifTool 驱动的 Windows 离线桌面工具，用于编辑 EXIF、XMP、IPTC 和 QuickTime 元数据。

[![最近提交](https://img.shields.io/github/last-commit/NextWeb4/photo-metadata-editor?style=flat-square)](https://github.com/NextWeb4/photo-metadata-editor/commits/main)
[![仓库大小](https://img.shields.io/github/repo-size/NextWeb4/photo-metadata-editor?style=flat-square)](https://github.com/NextWeb4/photo-metadata-editor)
[![GitHub Stars](https://img.shields.io/github/stars/NextWeb4/photo-metadata-editor?style=flat-square)](https://github.com/NextWeb4/photo-metadata-editor)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)
[![MIT 许可证](https://img.shields.io/github/license/NextWeb4/photo-metadata-editor?style=flat-square)](LICENSE)

## 功能

- 打开 JPG、PNG、TIFF、HEIC、HEIF、WEBP、MOV、MP4 等常见媒体格式。
- 编辑标题、描述、关键词、作者、版权、拍摄时间、相机、软件、GPS 和地点字段。
- 显示格式、尺寸、像素、镜头、ISO、焦距、光圈和快门等只读信息。
- 提供相机/GPS 预设、暗色主题、本地 OCR 日期识别和可选的文件时间同步。
- 切换中英文界面，并把语言偏好保存在 `%APPDATA%\PhotoMetadataEditor\settings.json`。
- 默认保留 ExifTool `_original` 备份；恢复前创建并校验 `_before_restore` 副本。
- 检查 ExifTool 写入摘要并回读关键字段，不会只根据退出码判断成功。
- 全程在本机处理文件，不上传图片或元数据，也不在运行时下载 OCR 模型。

## 环境要求与兼容性

- **操作系统：**内置 ExifTool runtime、支持拖放的桌面应用、打包脚本和 MSI 均面向 Windows。
- **Python：**`pyproject.toml` 要求 Python 3.11 或更高版本，并将 `tkinterdnd2` 声明为桌面依赖。
- **ExifTool：**源码和打包版本均依赖 `vendor/exiftool/` 中已提交的 Windows runtime；冻结构建不会改用 `PATH` 中的可执行文件。
- **可选 OCR：**可用性取决于本机 Windows OCR 语言、Tesseract 或本地安装的 PaddleOCR 资源。项目不提供云端回退，也不会在运行时下载模型。
- **媒体写入：**能够读取某种格式并不表示所有标签都可写；仍受容器支持、文件系统权限和 ExifTool 标签表限制。

## 安装发布包

从 [GitHub Releases](https://github.com/NextWeb4/photo-metadata-editor/releases) 下载：

- `PhotoMetadataEditor-0.1.2-win64.msi`：Windows 安装包。
- `PhotoMetaEditor-portable.zip`：便携包；完整解压后运行 `PhotoMetaEditor.exe`。
- `SHA256SUMS.txt`：发布文件校验值。

不要单独下载 `PhotoMetaEditor.exe`，它依赖便携包内相邻的 `_internal` 和 `exiftool` 内容。未配置受信任代码签名证书时，公开产物保持未签名状态，Windows 可能提示未知发布者。运行前请校验 SHA-256。

## 从源码运行

`pyproject.toml` 声明需要 Python 3.11 或更高版本。桌面运行依赖为 `tkinterdnd2`，所需 ExifTool Windows runtime 已放在 `vendor/exiftool/`。

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e .
$env:PYTHONPATH = "src"
.venv\Scripts\python -m photo_meta_editor
```

OCR 是可选功能。可用后端取决于源码环境中已安装的 Windows OCR、Tesseract 或 PaddleOCR 本地资源。应用不得下载模型或把图片发送到云端 OCR 服务。

## 使用编辑器

1. 选择文件，或把图片/视频拖入窗口。
2. 在左侧编辑支持的字段，在右侧查看或筛选原始元数据。
3. 按需套用相机/GPS 预设、使用本地 OCR 识别日期，或启用文件时间同步。
4. 点击“保存修改”；首次写入默认保留 `_original` 备份。
5. 需要回退时，在确认提示后使用“恢复备份”。

应用支持多种媒体容器，但实际写入能力仍取决于文件本身、文件权限和 ExifTool 支持情况。只有摘要检查和关键字段回读均通过时，才会报告写入成功。

## 写入与恢复安全

- 常规写入会保留 ExifTool 的 `_original` 备份，除非用户明确修改该行为。
- 恢复前会创建并校验 `_before_restore` 副本，检测并发文件变化，并在校验失败后回滚。
- GPS 纬度和经度是一个成对值；修改时必须同时写入或清除，不能留下只更新一半的地点信息。
- ExifTool 参数以结构化输入传递；Unicode 路径、空格、反斜杠和多行内容必须始终作为数据，而不能变成命令语法。
- 当 ExifTool 报告 `0 image files updated` 时，即使进程退出码为 0 也不能视为成功；应用还会检查摘要并回读关键字段。

## 项目结构

| 路径 | 职责 |
| --- | --- |
| `src/photo_meta_editor/app.py` | Tkinter 界面和应用协调 |
| `src/photo_meta_editor/exiftool.py` | 安全调用 ExifTool 并处理读写 |
| `src/photo_meta_editor/fields.py` | 字段/标签映射、规范化和校验 |
| `src/photo_meta_editor/metadata.py` | 应用身份与版本元数据 |
| `src/photo_meta_editor/ocr.py` | 本地 OCR 后端检测和日期解析 |
| `src/photo_meta_editor/presets.py` | 相机和 GPS 预设 |
| `src/photo_meta_editor/i18n.py` | 中英文 UI 文案 |
| `src/photo_meta_editor/settings.py` | 本地应用偏好 |
| `vendor/exiftool/` | 内置 ExifTool Windows runtime |
| `scripts/` | 打包、签名、许可证收集、隐私扫描和路径安全 |
| `tests/` | 基于标准库 `unittest` 的回归测试 |

## 测试

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests
```

## 构建

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_release.ps1
```

发布构建会执行编译检查、单元测试、EXE/MSI/ZIP 打包、第三方许可证完整性检查和隐私扫描。文档中确认的产物包括：

- `dist\PhotoMetaEditor\PhotoMetaEditor.exe`
- `dist\PhotoMetadataEditor-0.1.2-win64.msi`
- `dist\PhotoMetaEditor-portable.zip`

持有受信任证书的发布者可设置 `PHOTO_META_EDITOR_SIGNING_CERT_THUMBPRINT`。未设置时产物必须保持未签名；构建流程不会创建自签名证书来冒充可信签名。

## 隐私与分发

- 不得新增后台上传、遥测、云 OCR 或运行时模型下载。
- 冻结后的 EXE/MSI 必须使用包内 ExifTool，不能使用由 `PATH` 或 `PHOTO_META_EDITOR_EXIFTOOL` 替换的二进制。
- 分发包必须包含收集后的项目与第三方声明。
- 打包隐私扫描会检查本机路径和开发产物，但不能代替许可证完整性检查。

依赖详情见 [`docs/THIRD_PARTY.md`](docs/THIRD_PARTY.md) 和 [`docs/OPEN_SOURCE_AUDIT.md`](docs/OPEN_SOURCE_AUDIT.md)。

## 项目状态与限制

- 这是一个活跃的公开 Windows 应用，已记录 0.1.2 版本的 MSI 和 portable 发布产物。
- OCR 是可选的本地能力；后端不可用时会明确不可用，而不会静默切换到网络服务。
- 静态图片与 QuickTime 容器的读写覆盖并不完全一致，GPS 和日期标签尤其依赖具体格式。
- 未配置受信任证书时，公开产物保持未签名；SHA-256 只能校验内容完整性，不能证明发布者身份。
- 仓库包含第三方 ExifTool runtime；项目的 MIT 许可证不能替代其声明和其他打包组件的许可证。

## 参与贡献

请将 Tkinter 协调逻辑保留在 `app.py`，进程调用保留在 `exiftool.py`，字段规则保留在 `fields.py`，OCR 检测保留在 `ocr.py`，打包逻辑保留在 `scripts/`。修改标签、时间、GPS、QuickTime、备份或参数处理时，应补充真实文件回归测试并运行完整 `unittest`。打包改动必须保留路径安全、隐私、runtime 裁剪和许可证收集检查。项目当前没有 lint 或 format 命令。

## 作者

- [HaoXiang Huang](https://nextweb4.github.io/)
- [didadida1688@gmail.com](mailto:didadida1688@gmail.com)

## 许可证

项目源码采用 [MIT License](LICENSE)。内置组件（包括 ExifTool 及其 Windows runtime）保留各自许可证；重新分发时必须保留随附声明。
