# Photo Metadata Editor

[English](#english) | [中文](#中文)

## 中文

### 项目简介

Photo Metadata Editor 是一个离线 Windows 桌面工具，使用 Tkinter 提供图形界面，并通过内置的 ExifTool 读取和修改 EXIF、XMP、IPTC 与 QuickTime 元数据。项目不会上传图片或元数据，也不会在运行时自动下载 OCR 模型。

### 功能特点

- 支持 JPG、PNG、TIFF、HEIC、HEIF、WEBP、MOV、MP4 等常见媒体文件。
- 编辑标题、描述、关键词、作者、版权、拍摄时间、相机、软件、GPS 与地点字段。
- 显示文件格式、尺寸、像素、镜头、ISO、焦距、光圈、快门等只读照片参数。
- 支持相机和 GPS 预设、暗色模式、本地 OCR 时间识别与文件时间同步。
- 中文/English 界面切换；桌面版将语言选择保存在 `%APPDATA%\PhotoMetadataEditor\settings.json`。
- 默认保留 ExifTool `_original` 备份；恢复前另存 `_before_restore`，并提供校验与失败回滚。
- 写入后检查 ExifTool 摘要和关键字段读回结果，避免把未写入误报为成功。

### 安装方法

从 [GitHub Releases](https://github.com/NextWeb4/photo-metadata-editor/releases) 下载：

- `PhotoMetadataEditor-0.1.2-win64.msi`：Windows 安装包。
- `PhotoMetaEditor-portable.zip`：免安装便携版，解压后运行其中的 `PhotoMetaEditor.exe`。
- `SHA256SUMS.txt`：下载文件校验值。

当前公开构建未配置商业代码签名证书，因此保持未签名；Windows 可能显示未知发布者。项目不会创建自签名证书冒充可信签名。

### 使用方法

1. 打开软件并点击“选择”，或把图片/视频拖入窗口。
2. 修改左侧可编辑字段；右侧可筛选查看全部原始元数据。
3. 根据需要选择相机/GPS 预设、OCR 时间或同步文件时间。
4. 点击“保存修改”。首次写入默认生成 `_original` 备份。
5. 需要回退时点击“恢复备份”并确认。

源码运行：

```powershell
$env:PYTHONPATH = "src"
python -m photo_meta_editor
```

### 测试与打包

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests
powershell -ExecutionPolicy Bypass -File .\scripts\build_release.ps1
```

完整发布构建会执行编译检查、单元测试、EXE/MSI/ZIP 构建、许可证完整性检查和隐私扫描。如果发布者持有受信代码签名证书，可设置 `PHOTO_META_EDITOR_SIGNING_CERT_THUMBPRINT`；未设置时产物保持未签名。

主要产物：

- `dist\PhotoMetaEditor\PhotoMetaEditor.exe`
- `dist\PhotoMetadataEditor-0.1.2-win64.msi`
- `dist\PhotoMetaEditor-portable.zip`

### 作者信息

- 作者：[HaoXiang Huang](https://nextweb4.github.io/)
- 邮箱：[didadida1688@gmail.com](mailto:didadida1688@gmail.com)
- 主页：[https://nextweb4.github.io/](https://nextweb4.github.io/)
- GitHub：[https://github.com/NextWeb4](https://github.com/NextWeb4)

### License

项目源码使用 [MIT License](LICENSE)。分发包内置的 ExifTool、tkinterdnd2、PyInstaller、cx_Freeze 等第三方组件继续遵循各自许可证；详见 [第三方说明](docs/THIRD_PARTY.md)。

## English

### Overview

Photo Metadata Editor is an offline Windows desktop application built with Tkinter and the bundled ExifTool. It reads and edits EXIF, XMP, IPTC, and QuickTime metadata without uploading images or metadata and without downloading OCR models at runtime.

### Features

- Supports common media formats including JPG, PNG, TIFF, HEIC, HEIF, WEBP, MOV, and MP4.
- Edits title, description, keywords, creator, copyright, capture time, camera, software, GPS, and location fields.
- Shows read-only photo facts such as dimensions, megapixels, lens, ISO, focal length, aperture, and shutter speed.
- Includes camera/GPS presets, dark mode, local OCR date detection, and file-time synchronization.
- Switches between Chinese and English; the desktop language preference is stored in `%APPDATA%\PhotoMetadataEditor\settings.json`.
- Preserves ExifTool `_original` backups and creates a verified `_before_restore` copy before a restore.
- Verifies ExifTool summaries and reads important values back after writing.

### Installation

Download from [GitHub Releases](https://github.com/NextWeb4/photo-metadata-editor/releases):

- `PhotoMetadataEditor-0.1.2-win64.msi`: Windows installer.
- `PhotoMetaEditor-portable.zip`: portable package; extract it and run `PhotoMetaEditor.exe`.
- `SHA256SUMS.txt`: SHA-256 checksums for the release files.

Public builds remain unsigned when no trusted commercial code-signing certificate is configured. Windows may therefore show an unknown-publisher warning. The project does not create a self-signed certificate to imitate trusted signing.

### Usage

1. Open the application and select a file, or drop an image/video into the window.
2. Edit fields on the left and inspect/filter all raw metadata on the right.
3. Optionally apply camera/GPS presets, detect a time with local OCR, or synchronize file times.
4. Select **Save changes**. The first write keeps an `_original` backup by default.
5. Use **Restore backup** and confirm when a rollback is needed.

Run from source:

```powershell
$env:PYTHONPATH = "src"
python -m photo_meta_editor
```

### Testing and packaging

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests
powershell -ExecutionPolicy Bypass -File .\scripts\build_release.ps1
```

The release build performs compilation checks, unit tests, EXE/MSI/ZIP packaging, license validation, and privacy scans. A publisher with a trusted code-signing certificate may set `PHOTO_META_EDITOR_SIGNING_CERT_THUMBPRINT`; otherwise artifacts remain unsigned.

### Author

- Author: [HaoXiang Huang](https://nextweb4.github.io/)
- Email: [didadida1688@gmail.com](mailto:didadida1688@gmail.com)
- Website: [https://nextweb4.github.io/](https://nextweb4.github.io/)
- GitHub: [https://github.com/NextWeb4](https://github.com/NextWeb4)

### License

The project source is released under the [MIT License](LICENSE). Bundled third-party components retain their own licenses; see [Third-party notices](docs/THIRD_PARTY.md).
