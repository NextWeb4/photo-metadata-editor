# AGENTS.md

## 1. 项目结构
- 当前项目根目录即本文件所在目录；文档和源码不得写入开发机绝对路径。
- `src/photo_meta_editor/` 是应用源码：`app.py` 负责 Tkinter 界面，`i18n.py` 负责中英文文案映射，`settings.py` 负责本地语言偏好，`exiftool.py` 负责 ExifTool 调用，`fields.py` 负责字段映射和校验，`presets.py` 负责相机/GPS预设，`ocr.py` 负责OCR引擎探测和时间解析。
- `vendor/exiftool/` 存放打包运行所需的 `exiftool.exe` 和 `exiftool_files/`。
- `scripts/build_exe.ps1` 是 Windows EXE 打包入口。
- `scripts/build_msi.ps1` 是 MSI 打包入口，`setup_msi.py` 是 cx_Freeze MSI 配置。
- `scripts/build_release.ps1` 是发布前总入口：编译、单元测试、EXE、MSI、可选受信证书签名、ZIP 和隐私扫描必须集中从这里跑。
- `scripts/generate_windows_version_info.py` 从 `metadata.py` 生成 PyInstaller 使用的 `scripts/windows_version_info.txt`。
- `scripts/collect_licenses.py` 生成分发包随附的 `licenses/` 目录，至少包含项目 `LICENSE`、`THIRD_PARTY.md`、ExifTool Windows 版说明、Strawberry Perl runtime 许可证包、PyInstaller COPYING、cx_Freeze 和 tkinterdnd2 许可证；PyInstaller 目录根部也必须保留一份可见 `licenses/`。
- `scripts/check_package_privacy.py` 扫描分发产物中的本机路径、临时附件名、桌面样例名和外部 ExifTool 样例路径。
- `scripts/prune_runtime_payload.py` 负责清理打包产物中非当前平台的 `tkinterdnd2\tkdnd` 文件和 Tk demos，避免 EXE/MSI 体积膨胀。
- `scripts/sign_artifacts.ps1` 只允许使用 `PHOTO_META_EDITOR_SIGNING_CERT_THUMBPRINT` 指定的受信代码签名证书；没有证书时产物必须保持未签名，不得创建自签名证书。
- `tests/` 存放标准库 `unittest` 测试。
- `docs/OPEN_SOURCE_AUDIT.md` 和 `docs/THIRD_PARTY.md` 记录方案审计与第三方组件。
- 当前仓库不提交 GitHub Actions 发布 workflow；本次发布使用 GitHub API 直接创建 Release。若后续恢复 `.github/workflows/release.yml`，推送凭据必须具备 `workflow` scope。
- `RELEASE_NOTES.md` 是 GitHub Release 的中英文说明；`release-assets/` 只保存待上传产物且不得提交。
- 外部 ExifTool 原始目录只作为本机开发来源，不得直接修改该目录内的样例图片。

## 2. 运行命令
- 源码运行：`$env:PYTHONPATH = "src"; python -m photo_meta_editor`
- 打包产物运行：`.\dist\PhotoMetaEditor\PhotoMetaEditor.exe`

## 3. 测试命令
- 单元测试：`$env:PYTHONPATH = "src"; python -m unittest discover -s tests`
- 修改字段映射、日期/GPS 校验、预设数据、OCR时间解析或 ExifTool 参数生成后必须运行单元测试。
- 修改 ExifTool 写入参数后必须至少保留一个真实 JPEG 写入回归测试，验证 UI 可接受的日期格式会被规范化并能被 ExifTool 读回；PNG 写入路径还必须覆盖标题与成对 GPS 坐标的真实读回，避免 JPEG 标签映射回归后误称支持常见无损图片。

## 4. 构建命令
- EXE 构建：`powershell -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1`
- MSI 构建：`powershell -ExecutionPolicy Bypass -File .\scripts\build_msi.ps1`
- 完整发布构建：`powershell -ExecutionPolicy Bypass -File .\scripts\build_release.ps1`
- 构建产物目录：`dist\PhotoMetaEditor\`
- 构建脚本会排除 PaddleOCR/PyTorch/EasyOCR/winsdk 等重型或可选 OCR 依赖，避免 EXE/MSI 体积和启动复杂度失控。
- 构建后会运行 `scripts/prune_runtime_payload.py`；修改 PyInstaller 或 cx_Freeze 配置后必须确认只保留当前 Windows 平台所需的 `tkdnd` 目录。
- PyInstaller 构建前必须拒绝 `build/`、`dist/`、`build/pyinstaller-spec/` 及其 `PhotoMetaEditor/licenses` 子目录中的 Windows reparse point，并确认解析后的路径仍在项目根目录内；生成的 `.spec` 必须写入受保护的 `build/pyinstaller-spec/`，构建脚本不得通过目录联接删除或覆盖项目外文件。
- 对 `build/`、`dist/` 或其子目录执行递归删除/替换前，必须同时拒绝目标目录内部嵌套的 Windows reparse point；不能只检查顶层目录。
- Python 发布辅助脚本执行 `shutil.rmtree` 前必须调用 `scripts/path_safety.py` 的 reparse point 检查；脚本既要支持被测试导入，也要支持 `python scripts\*.py` 直接执行。
- PyInstaller 使用独立 `--specpath` 后，`--add-binary`、`--add-data`、`--paths`、版本文件和入口脚本必须传入项目根目录推导出的绝对路径；不得依赖 spec 目录改变前的相对路径解析。
- MSI 必须在 CostInitialize 前通过 Type 51 CustomAction 把安装会话的 `PersonalFolder` 设为 `[LocalAppDataFolder]`、把 `ROOTDRIVE` 设为 `[WindowsVolume]`；不得修改用户注册表。否则重定向到不可用盘的 Shell Folder 可能令真实安装在 `CostFinalize` 返回 1606/1603。
- cx_Freeze MSI 的非根 Directory identifier 必须由 `BuildMsiCommand` 生成为稳定的 `PME_DIR_*`；不得直接使用 ExifTool runtime 的 `Text`、`File` 等目录名作为 MSI 属性，否则可能与 Windows Installer 全局状态冲突并导致 CostFinalize 1606。

## 5. 代码风格
- 当前未发现 lint / format 命令。
- 新增代码时优先保持少依赖、清晰模块边界，不把 GUI、文件解析、ExifTool 调用混在同一个大文件中。
- Python 代码使用类型标注；业务逻辑优先放在可单测函数中。
- `tkinterdnd2` 是拖拽导入所需运行依赖；OCR依赖保持可选探测，不允许运行时自动下载模型，PaddleOCR 只能使用本地缓存模型。
- 默认分发包不内置 `winsdk`、PaddleOCR、EasyOCR、PyTorch；Windows OCR 只在源码环境安装了 `winsdk` 时可用。
- 应用元信息、作者、邮箱、网站必须统一来自 `src/photo_meta_editor/metadata.py`，不要在 UI、打包脚本和 MSI 配置中各自硬编码不同值。
- 不要手改 `scripts/windows_version_info.txt` 的作者、版本、邮箱或网站；应修改 `metadata.py` 后运行 `scripts/generate_windows_version_info.py` 或完整构建。
- 对外发布会改变已安装 MSI 行为、EXE 版本资源或分发内容时，必须先递增 `metadata.py` 的数字化 `APP_VERSION`，同步 `pyproject.toml`、README 产物名并通过 `tests/test_metadata.py`；cx_Freeze 的 ProductCode 每次生成，保持旧版本号会让安装升级语义不可靠。
- README 和中文文档必须保持 UTF-8 可读中文，不允许保存成 mojibake；修改 README 后必须运行 `python -m unittest discover -s tests -p test_metadata.py`。
- UI 新增或修改可见文案时必须同时补齐 `i18n.py` 的英文翻译；语言切换不得改变当前文件、编辑值、预设或忙碌状态。
- 语言偏好只能写入用户 AppData 的 `PhotoMetadataEditor/settings.json`，不得写入项目目录或发起联网请求。

## 6. 模块边界
- GUI 只负责用户交互、状态展示和调用服务层。
- 图片元数据读写必须通过 ExifTool 调用封装层完成。
- ExifTool 调用必须以命令行前缀 `-config "" -@ -` 禁用外部默认配置，并把其余参数以 UTF-8 C-string 输入流传递；中文路径、空格路径、反斜杠和多行元数据必须通过真实读写回归测试。
- 元数据字段读取、写入标签映射和校验必须放在 `fields.py`，不要散落到 GUI 事件里。
- iPhone“照片信息”卡片同类字段（文件名、格式、尺寸、像素、文件大小、镜头、ISO、焦距、曝光补偿、光圈、快门）必须在左侧信息区直接显示；不可写入的事实字段必须标记为只读，并在 `build_tag_assignments` 中跳过。
- UI 中可写字段和只读照片参数必须在左侧同一个信息面板内分区展示，不允许把照片参数藏在只有切换标签页才看到的位置，也不允许混成一条长表单导致用户误判哪些字段能保存。
- 相机型号和GPS预设只能放在 `presets.py`，不要在 GUI 回调中硬编码。
- OCR文本识别和时间解析只能放在 `ocr.py`，GUI 只调用服务函数。
- PaddleOCR 调用前必须强制 `PADDLE_PDX_MODEL_SOURCE=LOCAL` 并确认本地模型缓存存在；不得被外部环境变量改成联网模型源。
- 用户输入的拍摄时间可以接受 `YYYY:MM:DD`、`YYYY-MM-DD`、`YYYY/MM/DD`、`YYYY.MM.DD` 和中文年月日格式，但写入 ExifTool 前必须统一规范化为 `YYYY:MM:DD HH:MM:SS`。
- 编辑器可把文件名作为空标题的显示回填，但 ExifTool 写入后的读回校验必须比较原始存储字段；清空标题时不得把该显示回填误判成写入失败。
- 编辑器可根据镜头信息推断 iPhone 厂商和型号用于显示，但 ExifTool 写入后的读回校验必须跳过该推断；清空实际 `Make`/`Model` 时不得误报失败。
- GPS 读取必须正确处理十进制度数、DMS 度分秒格式、DM 度加小数分格式、半球方向和 ISO6709 组合坐标；不得用“取前两个数字”的方式解析带单位的组合坐标。
- GPS 纬度和经度是一个成对不变量：保存时必须同时修改并同时填写或同时清空；任何只传入或只清空一个坐标的写入请求必须在 `validate_changed_values` 拒绝，任一坐标变化时写入层必须拿到当前完整经纬度对。
- QuickTime 的 ISO 6709 坐标按 5 位小数写入；MOV/MP4/HEIC/HEIF 的 GPS 读回校验可仅接受该格式引起的半单位舍入误差，JPEG 等 EXIF 路径仍必须精确匹配。
- MOV/MP4/HEIC/HEIF 这类 QuickTime 容器必须使用目标文件感知的写入标签，常用字段要同步写入 `Keys:`/`ItemList:`/`QuickTime:` 等容器标签，不能只写 JPEG 常用的 EXIF/XMP/IFD0 标签；必须以 ExifTool 对应 tag table 验证每个组内标签真实可写，不能把 `LocationName` 或 `GPSCoordinates` 错写为 `ItemList:` 标签。
- QuickTime 日期标签清空后可能读回 `0000:00:00 00:00:00`；读取和写后验证必须将该容器哨兵值视为已清空，不能向界面显示或误报为保存失败。
- 打包配置必须独立于业务逻辑，避免在运行时代码中硬编码构建产物路径。
- 不允许在运行时代码中硬编码本机私有路径；开发期外部 ExifTool 覆盖必须使用 `PHOTO_META_EDITOR_EXIFTOOL` 环境变量。
- `PHOTO_META_EDITOR_EXIFTOOL` 与 PATH 回退只允许源码开发环境使用；冻结 EXE/MSI 必须只执行随包的 ExifTool，缺失时失败退出，不能继承环境变量替换签名分发的二进制。
- UI 预设下拉框选中后必须立即回填左侧可编辑字段，并以字段样式、滚动定位和“可编辑信息”顶部的实际值摘要直接呈现受影响的参数；不能只依赖“套用”按钮；用户手动覆盖预设字段时必须清空对应下拉选择、预设摘要和该预设组全部高亮，避免刷新重新覆盖手动值；相关回归测试必须覆盖 `<<ComboboxSelected>>` 事件、`StringVar` 变化、预设摘要和用户手动覆盖预设值后的样式复原。
- 已选择的相机/GPS预设不得在导入新文件后与左侧字段状态脱节；读取元数据回填后必须重新套用仍然显示为选中的预设，或清空预设显示。
- 相机预设切换时必须覆盖完整预设状态；预设字段为空时也要清空旧值，避免例如 Fujifilm 预设残留 iOS 软件字段。
- GUI 进入读取、写入、OCR 等忙碌状态时，主要操作按钮必须禁用，避免并发触发导致界面状态和后台任务错位。
- GUI 在没有导入当前文件时必须禁用可编辑字段；关闭、刷新、拖拽或选择新文件前必须对未保存修改提供保存、放弃、取消路径，不能静默覆盖或丢弃。
- GUI 忙碌状态必须同时禁用可编辑字段、Text 多行输入和保存选项；读取、写入或 OCR 期间不得关闭窗口，避免后台外部进程在界面销毁后不可见运行。
- GUI 后台线程完成后只能通过安全的 UI 线程调度回写；窗口关闭或旧任务完成时不得再更新控件、弹窗或覆盖当前文件状态。
- 后台线程不得直接调用 `root.after`、控件方法或消息框；必须写入线程安全队列，由创建 Tk 根窗口的线程定时清空队列后更新 UI。关闭窗口前必须取消该定时回调。
- ExifTool 和外部 OCR 后端必须设置超时并向 UI 返回可读错误，不能让任意文件或 OCR 卡死导致界面永久忙碌。
- Windows OCR 和 PaddleOCR 这类库内 OCR 后端必须在可终止的子进程中执行，超时后终止进程；父进程必须在等待子进程退出期间持续读取结果队列，避免大 OCR 文本填满管道导致 join 死锁；新增 multiprocessing 入口时必须保留 `freeze_support()` 以兼容冻结 EXE。
- 应用启动阶段不得同步执行外部 ExifTool/OCR 进程；路径可用性检查后必须立即建立 Tk 事件循环，耗时外部调用只能从用户操作触发的后台任务执行。
- OCR 单个本地后端失败时必须记录错误并继续尝试后续可用本地后端，不能因为 Tesseract 等某一个后端报错就阻断 PaddleOCR 等备用后端。
- GitHub Release 使用现有应用版本生成 tag（当前为 `v0.1.2`），不得另造与 `metadata.py` 不一致的版本；Release Notes 必须中英文双语。

## 7. 禁止事项
- 不允许覆盖用户原图；写入元数据时必须保留备份或使用明确的安全写入策略。
- “恢复备份”只能在用户明确确认后执行；必须先用排他创建把当前文件无覆盖地保存为唯一的 `_before_restore` 副本并校验摘要，替换前再次确认当前文件未被其他程序修改，再用 `_original` 的临时副本原子替换目标文件并校验内容；替换后的校验失败必须从 `_before_restore` 原子回滚，且不得覆盖该回滚副本。
- 不允许对外部 ExifTool 原始目录做清理、移动、删除或批量改名。
- 不允许新增会在后台上传图片或元数据的联网行为。
- 不允许OCR功能在用户不知情的情况下下载模型或调用云端服务。
- 不允许把 PaddleOCR 大模型默认打进 EXE；只有用户明确要求离线OCR一体包时才重新审计打包体积和许可证。
- 不允许为了修改少量元数据引入大型、不必要的框架。
- 不允许把 `build/`、`dist/`、`__pycache__/`、用户桌面样例、Codex 临时附件或外部样例路径打入分发产物。
- 不允许提交 `.env*`、密钥、token、credentials、`.learnings/`、`release-assets/`、IDE 配置或任何开发机绝对路径；提交前必须检查 `git status`、`git ls-files` 和隐私标记搜索结果。
- 不允许发布缺少 `licenses/THIRD_PARTY.md` 和关键第三方许可证说明的 EXE/MSI/ZIP。
- 许可证收集缺少 `THIRD_PARTY.md`、ExifTool Windows 许可证/说明、Strawberry Perl runtime 许可证包、PyInstaller COPYING、cx_Freeze 或 tkinterdnd2 许可证时必须失败，不允许静默发布许可证不完整的包。

## 8. 完成标准
- 应用能选择图片、读取常见 EXIF/XMP/IPTC 字段、修改字段并保存。
- 应用能拖拽导入文件，导入后预填已有标题、作者、时间、相机信息和GPS字段。
- 相机/GPS预设、暗色模式、OCR识别时间和保存时同步文件创建/修改时间可用。
- 中文/English 切换必须覆盖工具栏、字段标签、元数据表头、状态栏、对话框和 About 页面，并在重启后恢复选择。
- 暗色模式必须覆盖输入框、下拉框、按钮、表格、滚动条和状态栏，不能只改背景色。
- 暗色模式要同时覆盖左右面板内部背景、只读输入框、下拉列表弹层、复选框指示器和滚动条；可编辑输入框必须使用 `Editable.TEntry`，新增控件时必须接入现有 ttk 样式和 root option database。
- 顶部工具栏和预设栏必须在 980px 最小窗口宽度下不挤压、不截断；新增控制项优先使用网格分行布局。
- 修改前后能通过 ExifTool 验证关键字段变化。
- 保存完成不能只依赖 ExifTool 退出码；写入层必须检查 ExifTool 摘要里至少有文件被 updated/created/copied，`0 image files updated` 必须作为未写入错误返回给 UI。
- 勾选“同步文件创建/修改时间”时，写入层必须从读回元数据分别验证 `System:`/`File:` 的创建时间和修改时间；任一时间缺失或不匹配不得报告保存成功。
- `ExifToolClient.write_metadata(..., sync_file_time=True)` 必须要求有效的拍摄时间；可从显式 `file_time_value` 或本次 `date_taken` 变更取得，但两者皆空时必须拒绝，不能静默跳过文件时间同步。
- Windows EXE 打包命令可复现，产物位置明确。
- 发布前必须先运行单元测试和 `scripts/check_package_privacy.py`；隐私扫描失败时不得发布。
- 隐私扫描必须覆盖 UTF-8、UTF-16LE、UTF-16BE 字符串、大小写变体、普通文件名、ZIP 内部文件内容、ZIP 内部文件名、PyInstaller EXE 解压后的 CArchive/PYZ 载荷和 MSI 对应的 `build\cx_freeze\PhotoMetaEditor` staging payload；新增敏感标记时必须同步测试压缩包、压缩包条目名、PyInstaller 载荷、普通文件名和 Windows 资源常见编码。
- 隐私扫描必须动态纳入当前项目根目录的反斜杠和正斜杠形式，不能只依赖硬编码开发机路径。
- 发布脚本必须先在签名前运行隐私扫描，通过后才能签名和生成 portable ZIP；签名后还必须再扫描一次最终产物。
- 发布脚本签名前必须读取实际 EXE 版本资源，验证 `CompanyName`、`FileDescription`、`ProductName`、版本号、版权和 Comments 与 `metadata.py` 一致。
- 发布脚本签名前必须验证 PyInstaller dist 目录和 cx_Freeze MSI staging payload 中的 `licenses/` 关键文件齐全；隐私扫描不能替代许可证完整性验证。
- 生成 portable ZIP 后，发布脚本必须先验证 ZIP 非空、可读取，并包含 `PhotoMetaEditor.exe` 与根目录 `licenses/` 的关键许可证条目，再执行最终隐私扫描；隐私扫描通过不能替代分发包完整性验证。
- EXE 和 MSI 的作者/发布者元数据必须包含 `HaoXiang Huang`，联系信息必须包含 `didadida1688@gmail.com` 和 `https://nextweb4.github.io`。
- 发布脚本必须在签名前读取实际生成的 MSI Property/SummaryInformation，验证 `Manufacturer`、`ARPCONTACT`、`ARPURLINFOABOUT`、Summary author 和 Summary comments 与 `metadata.py` 一致；不能只检查 `setup_msi.py` 的配置文本。
- MSI 元数据验证使用 Windows Installer COM 后必须关闭 View 并释放 Summary/Database/Installer COM 引用，再进入可选签名或 ZIP 阶段；否则 MSI 文件锁会造成发布流程半完成。
- GitHub 发布前必须生成 `release-assets/SHA256SUMS.txt`，并在上传后通过 GitHub API/CLI核验 tag、Release URL 和资产列表；上传成功后删除本地 `release-assets/` 与构建缓存。

## 9. Review 标准
- 优先检查是否会覆盖原图、是否正确处理路径空格和中文路径。
- 检查 ExifTool 调用参数是否经过列表化传参，避免字符串拼接导致命令注入或转义错误。
- 检查 ExifTool 启动参数是否包含命令行级 `-config ""`，且位于 `-@ -` 前，避免加载用户目录或程序目录 `.ExifTool_config`。
- 检查用户常见日期输入格式是否会被规范化后再校验和写入，避免 UI 显示可编辑但保存失败。
- 检查 GUI 线程是否会被长时间 ExifTool 操作阻塞。
- 检查后台读取、写入、OCR 任务在窗口关闭、重复导入、任务失败和 UI 回调异常时是否能安全退出并恢复状态。
- 检查关闭、刷新、拖拽和选择新文件是否会保护未保存修改；后台线程启动失败是否会恢复忙碌状态。
- 检查拖拽导入在 EXE 中是否包含 `tkinterdnd2` 的 tkdnd 数据文件。
- 检查OCR不可用时是否给出明确错误，而不是静默失败或联网下载。
- 检查打包产物是否包含本机绝对路径、样例图片名、临时附件名和 Codex 工作目录。
- 检查 EXE/MSI 构建脚本在递归清理或覆盖构建目录前是否拒绝目录联接、符号链接和项目外解析路径。
- 检查 Python 发布辅助脚本在 `shutil.rmtree` 前是否拒绝 nested reparse point，且直接脚本入口不会因导入路径失败。
- 检查签名状态时，只有 Authenticode `Valid` 且证书指纹与显式配置一致才可声明签名成功；未配置证书时必须明确报告未签名。
- `scripts/sign_artifacts.ps1` 不得创建 `New-SelfSignedCertificate`，也不得把 `UnknownError` 或 `UntrustedRoot` 当作可信签名成功。

## 10. 常见风险
- HEIC/MOV 等格式写入能力取决于 ExifTool 支持和文件权限。
- Windows Defender 可能拦截 PyInstaller 产物，需要构建后做本机冒烟测试。
- 图片元数据字段名跨格式不完全一致，界面字段需要映射到 ExifTool 标签。
- Windows OCR 依赖系统已安装的OCR语言包；Tesseract OCR 依赖本机存在 `tesseract.exe`；PaddleOCR 依赖本机 Python 环境和 `.paddlex\official_models` 缓存模型。
