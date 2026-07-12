# 开源方案审计

## 当前项目事实

- 项目目标：做一个 Windows EXE，用于查看和修改图片/媒体文件元数据。
- 现有可复用组件：本机外部 ExifTool 13.50 目录，已复制运行所需文件到 `vendor/exiftool`。
- 当前技术栈：Python 3.12.7、Tkinter 标准库、tkinterdnd2、ExifTool CLI、PyInstaller 6.20.0、cx_Freeze 7.2.10。
- 离线边界：应用运行时不需要联网，也不上传图片或元数据。

## 候选方案对比

| 方案名称 | 来源 | 许可证 | 核心能力 | 优点 | 缺点 | 维护状态 | 与当前项目契合度 | 可能冲突点 | 是否采用 | 采用方式 |
|---|---|---|---|---|---|---|---|---|---|---|
| ExifTool | https://exiftool.org/ | GPL 或 Artistic License | 读写 EXIF/XMP/IPTC/QuickTime 等大量元数据 | 格式覆盖广、Windows 可直接运行、已有本地版本 | CLI 参数较多，需要封装安全调用 | 活跃，当前本机版本 13.50 | 很高 | 需随 EXE 打包 `exiftool_files` | 采用 | 作为唯一元数据读写引擎 |
| ExifToolGui | https://github.com/FrankBijnen/ExifToolGui | GPL-3.0 | Windows 图形化 ExifTool 前端 | 功能完整，可参考交互思路 | 直接复用会触发 GPL 派生风险，技术栈不适合本项目 | GitHub 项目可查 | 中 | 许可证与自定义轻量 EXE 目标冲突 | 不采用 | 只借鉴“GUI 调用 ExifTool”的设计方向，不复制代码 |
| pyexiftool | https://github.com/smarnach/pyexiftool | BSD 风格 | Python 封装 ExifTool 进程 | 可复用持久化 ExifTool 进程 | 当前需求只需要少量调用，引入后收益有限 | GitHub 项目可查 | 中 | 多一层依赖和调试面 | 不采用 | 直接用标准库 `subprocess.run` 列表化传参 |
| PySide6 / Qt | https://doc.qt.io/qtforpython-6/ | LGPL/GPL/Commercial | 桌面 GUI | UI 能力强 | 体积大、许可证义务更复杂、打包慢 | 活跃 | 低到中 | 与“轻量 EXE”目标冲突 | 不采用 | 使用 Tkinter 标准库 |
| PyInstaller | https://pyinstaller.org/ | GPLv2-or-later with exception | Python 应用打包为 Windows 可执行文件 | 本机已安装，适合快速生成 EXE | 产物可能被安全软件误报，需要冒烟测试 | 活跃，本机 6.20.0 | 高 | 需要显式加入 ExifTool 二进制和数据目录 | 采用 | 仅作为构建工具，不作为运行时依赖 |
| cx_Freeze bdist_msi | https://cx-freeze.readthedocs.io/ | PSF License | 从 Python 应用生成 Windows MSI | 可直接生成 MSI，无需本机 WiX/Inno/NSIS；支持作者、URL、快捷方式等元数据 | 生成的 MSI 视觉定制有限；仍需单独签名 | 活跃，本机 7.2.10 | 高 | 与 PyInstaller EXE 是两条构建链，必须分别做隐私扫描 | 采用 | 仅用于 MSI 安装包构建 |
| PowerShell Authenticode | Microsoft PowerShell | Windows 内置能力 | 使用明确提供的受信证书对 EXE/MSI 做 Authenticode 签名 | 无需额外 signtool；签名证书指纹和状态可验证 | 发布者必须自行持有可信代码签名证书 | Microsoft 维护 | 高 | 未配置证书时保持未签名，不能创建自签名证书冒充发布签名 | 条件采用 | 仅当环境变量提供证书指纹时签名并要求状态 `Valid` |
| WiX Toolset | https://wixtoolset.org/ | Microsoft Reciprocal License | 专业 MSI/MSIX 构建工具链 | 功能强、适合复杂安装器 | 本机未安装 .NET SDK/WiX；当前安装需求可用 cx_Freeze 满足 | 活跃 | 中 | 新增 .NET/WiX 工具链复杂度 | 不采用 | 后续需要复杂安装逻辑时再引入 |
| Inno Setup / NSIS | https://jrsoftware.org/isinfo.php / https://nsis.sourceforge.io/ | 自有许可 / zlib | Windows EXE 安装器 | 适合制作传统 setup.exe | 本机未安装；当前已有 PyInstaller EXE + MSI，继续引入收益不足 | 活跃 | 中 | 新增工具链和脚本维护成本 | 不采用 | 当前不生成传统 setup.exe 安装器 |
| tkinterdnd2 | https://github.com/Eliav2/tkinterdnd2 | MIT | Tkinter 文件拖拽 | 小依赖、适配当前 Tkinter 架构、PyInstaller 有 hook | 需要收集 tkdnd 数据文件 | 活跃，本机 0.4.4.1 | 高 | EXE 缺数据文件会导致拖拽不可用 | 采用 | 作为拖拽导入运行依赖 |
| Windows OCR / python-winsdk | https://github.com/pywinrt/python-winsdk | MIT | 调用 Windows.Media.Ocr | 可复用系统OCR，无需云服务 | 依赖系统OCR语言包，本机当前无可用语言 | 活跃，本机 winsdk 1.0.0b10 | 中 | 打包和系统语言包状态会影响可用性 | 条件采用 | 运行时探测，有语言包才启用 |
| Tesseract OCR | https://github.com/tesseract-ocr/tesseract | Apache-2.0 | 本地OCR识别 | 成熟离线OCR，不上传图片 | 本机当前未安装 `tesseract.exe`，不直接随包下载 | 活跃 | 中 | 需要用户或发行包提供二进制 | 条件采用 | 运行时探测本机 `tesseract.exe` |
| EasyOCR | https://github.com/JaidedAI/EasyOCR | Apache-2.0 | 深度学习OCR | 多语言能力强 | 依赖重，缺模型时会下载，不符合离线边界 | 活跃，本机已安装 | 低 | 隐式联网和打包体积冲突 | 不采用 | 不在应用中调用 |
| PaddleOCR | https://github.com/PaddlePaddle/PaddleOCR | Apache-2.0 | 深度学习OCR | 中文OCR能力强，本机已有缓存模型时识别效果好 | 依赖重，模型管理复杂，不适合默认随 EXE 打包 | 活跃，本机已安装 3.3.2 | 中 | 默认模型下载和打包体积与离线轻量目标冲突 | 条件采用 | 仅在已安装 `paddleocr` 且本地缓存模型存在时调用；不触发下载 |
| 本地相机/GPS预设 | Apple/Samsung/Canon/Fujifilm/Ricoh 官方产品名与常见城市坐标 | 事实数据/人工整理 | 常用设备和地点一键套用 | 离线、无隐式联网、可测试 | 不是完整全球数据库 | 自维护 | 高 | 需避免冒充权威全量数据库 | 采用 | `presets.py` 内置常用项 |
| Tkinter/ttk 内置主题与样式 | Python 官方文档 / TkDocs | Python Software Foundation License / TkDocs 文档许可 | 用 `ttk.Style`、`Frame`、`Separator`、`Treeview` 状态映射统一界面 | 标准库可用、无新增依赖、与当前 PyInstaller 打包兼容 | 视觉能力不如 Qt 或现代 Web UI，需要手工约束布局 | Python/Tk 官方维护 | 高 | 需要避免局部硬编码颜色导致暗色不一致 | 采用 | 继续使用内置 ttk 样式、统一面板和状态样式 |
| ttkbootstrap | PyPI / TkDocs 提及的第三方 Tkinter 主题方案 | MIT | 现成现代 Tkinter 主题和组件 | 暗色主题成熟，开发快 | 新增运行依赖和打包面；当前问题可用内置 ttk 解决 | 活跃 | 中 | 与“少依赖、轻量 EXE”目标存在轻度冲突 | 不采用 | 仅借鉴“统一主题令牌和组件状态”的设计思路 |

## 采用结论

- 直接复用：ExifTool 的元数据读写能力、PyInstaller 的 Windows EXE 打包能力、cx_Freeze 的 MSI 构建能力、tkinterdnd2 的文件拖拽能力。
- 直接复用：Tkinter/ttk 内置 `Style`、`Combobox`、`Treeview` 和控件状态能力统一界面，不新增主题依赖。
- 条件复用：Windows OCR、Tesseract OCR 和 PaddleOCR 本地缓存后端，仅在本机可用时启用，不触发模型下载。
- 只借鉴设计：ExifToolGui 的“图形界面前端 + ExifTool 后端”思路。
- 不采用：PySide6/Qt、pyexiftool、ExifToolGui 源码、EasyOCR、PaddleOCR 的默认模型下载/随包内置大模型方案。
- 不采用：ttkbootstrap，因为当前界面协调性问题可通过内置 ttk 样式和布局分组解决，引入依赖的收益不足。
- 不采用：WiX/Inno/NSIS，因为当前机器缺少对应工具链，且当前需求可通过 PyInstaller EXE、cx_Freeze MSI 和 PowerShell 签名脚本覆盖。
- 保留现有代码：无历史代码需要保留。
- 替换自研逻辑：不自研 EXIF/XMP/IPTC 解析器，全部交给 ExifTool。

## 2026-07-10 补充审计

| 方案名称 | 来源 | 许可证 | 核心能力 | 优点 | 缺点 | 维护状态 | 与当前项目的契合度 | 可能冲突点 | 是否采用 | 采用方式 |
|---|---|---|---|---|---|---|---|---|---|---|
| 升级 ExifTool 到 13.59 | https://exiftool.org/ | GPL 或 Artistic License | 最新 ExifTool 元数据读写能力 | 官方仍活跃，最新版支持面更广 | 当前项目已随本机 13.50 打包且没有复现 13.50 阻塞缺陷；替换二进制需重新校验分发和签名 | 活跃，官网显示 13.59 | 中 | 新二进制来源、校验和和回归范围扩大 | 暂不采用 | 继续使用已验证的本机 13.50；后续发现格式兼容问题再单独升级 |
| Python `zipfile` + 多编码字节扫描 | Python 标准库 | PSF License | 扫描普通文件名、ZIP 内部文件、ZIP 条目名和 UTF-16 Windows 资源字符串 | 无新增依赖，覆盖便携包条目名、便携包内容、普通文件名和 Windows 资源常见编码 | 不负责 MSI CAB 解包；MSI 由原始字节扫描加 cx_Freeze staging payload 扫描覆盖 | Python 标准库维护 | 高 | 无运行时联网或许可证冲突 | 采用 | 增强 `scripts/check_package_privacy.py`，并添加 ZIP 内容/条目名/普通文件名/UTF-16 回归测试 |
| PyInstaller CArchive/PYZ 读取器 | PyInstaller `archive.readers` | GPL-2.0-or-later with Bootloader exception（项目现有构建依赖） | 解压并扫描 EXE 中被压缩的 Python 代码和数据 | 补足原始字节扫描无法读取压缩载荷的盲点；不新增依赖或联网行为 | 使用构建工具的归档格式实现，PyInstaller 缺失时无法完成应用 EXE 深度扫描 | 随 PyInstaller 维护 | 高 | 仅能用于发布构建环境；检测到 CArchive cookie 后，读取器缺失或归档无法解析必须失败关闭，避免与同名 cx_Freeze EXE 冲突 | 采用 | 只在发布隐私扫描中调用现有 PyInstaller 读取器，扫描 CArchive 条目、嵌套 ZIP 和 PYZ 原始字节码 |
| cx_Freeze MSI staging payload 扫描 | cx_Freeze 构建目录 + Python 标准库 | PSF License | 扫描 MSI 对应的 `build\cx_freeze\PhotoMetaEditor` 安装载荷来源 | 不新增依赖，不调用可能卡住的 `msiexec /a`，能覆盖将被写入 MSI 的应用 payload | 依赖发布流程保留本次 MSI 对应的 staging 目录；不能替代对 MSI 文件本身的原始字节扫描 | Python/cx_Freeze 维护 | 高 | 发布脚本必须先构建 MSI，再扫描同一次构建生成的 staging payload；不得扫描陈旧 payload | 采用 | `.msi` 先扫描原始字节，再扫描 `PHOTO_META_EDITOR_MSI_PAYLOAD_ROOT` 或默认 `build\cx_freeze\PhotoMetaEditor` |
| 继续使用 ttk.Style 自定义主题 | Python 官方 `tkinter.ttk` 文档 | PSF License | 统一 Entry/Combobox/Button/Treeview/Scrollbar 状态样式 | 无新增依赖，符合现有 Tkinter 架构 | 视觉能力仍受 Tk 原生控件限制 | Python/Tk 官方维护 | 高 | 需要在新增控件时同步样式映射 | 采用 | 改进暗色调色板、只读输入框样式、option database 和 ttk 状态映射 |
| Tkinter/ttk 单面板分区布局 | Python 官方 `tkinter.ttk` 文档 | PSF License | 用 Frame/Separator/Combobox 事件把可编辑字段和只读照片参数放在同一左侧信息面板 | 标准库可实现，用户选择文件后能直接看到照片参数；`<<ComboboxSelected>>` 可覆盖预设选择回填 | 没有第三方主题库的现成视觉组件，需要维护样式令牌 | Python/Tk 官方维护 | 高 | 不得再次把照片参数藏到单独标签页 | 采用 | 删除左侧 Notebook，改为“可编辑信息”和“照片参数（只读）”同面板分区 |
| Tkinter `StringVar.trace_add` + root option database | Python 官方 `tkinter`/`ttk` 文档 | PSF License | 让相机/GPS预设变量变化时立即同步左侧字段，并用 `tk_setPalette`/option database 覆盖原生控件暗色 | 无新增依赖，能修复“顶部已选择但左侧无体现”和原生控件白底问题 | 仍受 Windows Tk 控件绘制限制，部分复选框指示器表现依赖主题引擎 | Python/Tk 官方维护 | 高 | 需要避免读取文件回填后覆盖已选预设状态 | 采用 | 预设变量加 trace，导入回填后重新套用仍选中的预设；暗色模式同步 Tk palette、下拉弹层和 ttk 状态映射 |
| Tkinter 主线程回调队列 | Python 官方 Tkinter threading model + Python `queue` 标准库 | PSF License | 将后台读取/写入/OCR结果排队，由 Tk 主线程消费 | 消除后台线程直接调用 Tk API 在事件循环未就绪或关闭时造成的崩溃和永久忙碌状态；无新增依赖 | 结果回显最多延迟一个轮询周期 | Python/Tk 官方维护 | 高 | 必须取消关闭前未执行的定时回调，不能让已销毁解释器继续调度 | 采用 | `app.py` 用 `queue.Queue` 接收后台结果，根窗口每 25ms 在主线程清空队列；关闭时取消定时任务 |
| Tkinter 未保存修改守卫 | Tkinter messagebox + 现有状态模型 | PSF License | 在关闭、刷新、拖拽或选择新文件前保护当前文件未保存编辑 | 无新增依赖；符合桌面编辑器基本预期，避免静默丢失标题、时间、GPS 等修改 | “先保存再切换”会先留在当前文件等待写入完成，需要用户再次执行切换 | Python/Tk 官方维护 | 高 | 不得在忙碌状态弹出二次保存流程；未导入文件时可编辑区应禁用 | 采用 | `app.py` 增加 dirty guard、空文件编辑禁用和后台线程启动失败恢复测试 |
| ttkbootstrap 1.20.4 复核 | PyPI | MIT AND (Apache-2.0 OR BSD-2-Clause) | 现成现代 Tkinter 主题 | 2026-06-25 有最新发布，暗色主题能力成熟 | 新增运行依赖和打包面；当前暗色问题可通过内置 ttk.Style 修复 | 活跃，PyPI 显示 1.20.4 为最新版本 | 中 | 与轻量 EXE、少依赖和既有 ttk 样式体系存在轻度冲突 | 不采用 | 只借鉴主题令牌和控件状态统一的思路 |
| OCR 后端失败继续降级 | Python 标准库异常处理 + 现有 OCR 后端 | PSF License / 现有后端许可证 | 某个本地 OCR 后端失败后继续尝试下一个可用后端 | 无新增依赖，避免 Tesseract 单点失败阻断 PaddleOCR 本地缓存后端 | 错误信息需要合并展示，避免用户误判 | Python 标准库维护 | 高 | 不能吞掉所有后端失败信息 | 采用 | Tesseract 异常加入错误列表后继续执行 PaddleOCR 探测 |
| OCR 后端超时和 PaddleOCR 本地源锁定 | Python 标准库 `multiprocessing` + PaddleOCR 环境变量 | PSF License / Apache-2.0 | 限制 Windows OCR/PaddleOCR 等本地库后端执行时间，并强制 PaddleOCR 使用本地模型源 | 无新增依赖；超时后可终止 OCR 子进程，避免后台线程继续占用文件、CPU/GPU 或模型资源 | 多进程在冻结 EXE 中需要 `multiprocessing.freeze_support()`；只适合顶层可序列化 OCR 函数 | Python 标准库维护 | 高 | 不得把超时包装改成联网重试；构建入口必须保留 freeze_support；父进程等待子进程期间必须持续读取结果队列，避免大文本填满管道造成 join 死锁 | 采用 | `run_with_timeout` 用子进程包装本地后端，超时 terminate/kill，并在循环中先读取结果再 join；`PADDLE_PDX_MODEL_SOURCE` 每次调用强制设为 `LOCAL` |
| GPS DMS/ISO6709 解析 | Python 标准库正则 | PSF License | 解析 ExifTool 可能返回的 DMS 分秒、半球方向和 ISO6709 组合坐标 | 无新增依赖，避免南纬/西经或分秒坐标被错误写入 UI | 坐标文本格式非常多，仍需围绕真实样本补充用例 | Python 标准库维护 | 高 | 不得用宽松“取前两个数字”覆盖 DMS 语义 | 采用 | 在 `fields.py` 增加专门 GPS parser 并补单测 |
| ExifTool QuickTime 容器写入标签 | ExifTool 官方 QuickTime TagNames | GPL 或 Artistic License 文档对应组件 | 为 MOV/MP4/HEIC/HEIF 补写 `QuickTime:`、`Keys:`、`ItemList:`、`UserData:` 标签 | 复用 ExifTool 官方标签体系，修复视频/HEIC 只写 JPEG 风格 EXIF/XMP 后字段不生效的问题 | 不同播放器读取的 QuickTime 标签集合不完全一致，需要写入多个常用组 | ExifTool 官方维护 | 高 | 不能对所有 JPEG 无条件写 QuickTime 标签；GPS 组合坐标必须有完整经纬度 | 采用 | `build_tag_assignments` 接收目标路径，QuickTime 容器追加容器标签，GPS 写 ISO 6709 组合坐标 |
| 发布包许可证收集 | Python 标准库 `importlib.metadata`/`shutil` | PSF License | 将 `THIRD_PARTY.md`、ExifTool Windows 版说明、Strawberry Perl runtime 许可证包和 tkinterdnd2 许可证放入分发包 `licenses/` | 无新增依赖，便携 ZIP、EXE 目录和 MSI 构建根目录都有可见许可证说明 | 依赖本机已安装包 metadata 中存在 license 文件，以及随包 ExifTool 目录保留 `Licenses_Strawberry_Perl.zip` | Python 标准库维护 | 高 | 不得硬编码开发机 site-packages 路径；PyInstaller `_internal` 内部数据不能替代用户可见根目录许可证 | 采用 | `scripts/collect_licenses.py` 在构建前生成 `build/licenses`，PyInstaller 构建后复制到 `dist/PhotoMetaEditor/licenses` |
| Python `pathlib`/`shutil` 产物裁剪 | Python 标准库 | PSF License | 删除打包产物中非当前平台 tkdnd 文件和 Tk demos | 无新增依赖，降低 EXE/MSI 体积和误打包面 | 必须严格限制删除范围在构建产物根目录内 | Python 标准库维护 | 高 | 删除范围写错会破坏构建产物 | 采用 | `scripts/prune_runtime_payload.py` 在 PyInstaller/cx_Freeze 构建后执行，并带路径边界测试 |
| Python `subprocess.run(timeout=...)` | Python 标准库 | PSF License | 限制 ExifTool/Tesseract 外部进程等待时间 | 无新增依赖，避免异常文件或 OCR 进程导致 GUI 永久忙碌 | 只能停止等待，不能修复外部工具本身的问题 | Python 标准库维护 | 高 | 超时时间过短会影响超大文件 | 采用 | ExifTool 120 秒、Tesseract 90 秒，并添加超时错误测试 |
| ExifTool 写入摘要校验 | ExifTool CLI 标准输出 | GPL 或 Artistic License 对应工具输出 | 区分“进程成功退出”和“实际有文件写入” | 避免 `0 image files updated / 1 unchanged` 被 UI 误报为保存成功 | 依赖 ExifTool 英文摘要格式；若未来本地化输出需同步调整正则 | ExifTool 官方维护 | 高 | 不应把无写入当作成功，也不能阻断正常 `updated/created/copied` 摘要 | 采用 | `ensure_write_updated_file` 检查摘要，未写入时抛出可读错误 |

## 冲突检查

- 技术栈：Python + Tkinter + ExifTool 兼容当前 Windows 环境。
- 目录结构：`vendor/exiftool` 独立放置第三方二进制，不与业务代码混放。
- 运行方式：源码运行和 PyInstaller onedir 运行均能定位 ExifTool。
- 构建方式：PyInstaller 显式打包 `exiftool.exe` 和 `exiftool_files`。
- 安装包方式：cx_Freeze MSI 显式打包 `exiftool.exe` 和 `exiftool_files`，作者信息来自 `photo_meta_editor.metadata`。
- 隐私边界：分发包构建后必须运行 `scripts/check_package_privacy.py`，拦截本机路径、Codex 临时附件名、用户桌面样例图片名和外部样例目录路径；PyInstaller EXE 必须解压其 CArchive/PYZ 后再扫描，不能只扫描压缩后的 EXE 原始字节。
- 隐私边界补充：敏感标记必须动态纳入当前项目根目录的反斜杠和正斜杠形式，避免迁移到其他工作区或 CI 路径后漏扫项目绝对路径。
- 签名边界：`scripts/sign_artifacts.ps1` 只接受显式提供的受信代码签名证书指纹；没有证书时发布产物保持未签名，不创建或伪造自签名证书。
- 发布顺序：`scripts/build_release.ps1` 在签名前先扫描 EXE/MSI/staging，扫描通过后只签名本次构建生成的 EXE 和唯一 MSI，生成 portable ZIP 后再扫描最终产物。
- 便携包完整性：portable ZIP 生成后先以 .NET `ZipFile` 验证文件非空、归档可读，并检查 EXE 与三份关键许可证条目；仅扫描 ZIP 原始字节无法证明压缩命令确实生成了完整可分发包。
- 安装包元数据完整性：发布流程通过 Windows Installer COM 读取实际 MSI 的 Property/SummaryInformation，并与 `metadata.py` 的创作者、邮箱、网站逐项比对；这避免 cx_Freeze 或 MSI 写入规则变化后只在源码配置中“看似正确”。
- MSI 验证与签名的资源边界：Windows Installer COM 打开的 View/Database 会锁定 MSI；元数据断言后必须关闭 View 并 `FinalReleaseComObject` 释放 Summary、Database、Installer，再调用签名脚本，避免生成“EXE 已签、MSI 未签”的不完整发布。
- 运行时 ExifTool 信任边界：源码开发可用 `PHOTO_META_EDITOR_EXIFTOOL`/PATH 覆盖本机工具；冻结产物只接受随包 ExifTool，避免继承环境变量后执行未经发布包审计和签名流程覆盖的外部二进制。
- ExifTool Unicode 参数边界：Windows ExifTool 启动器会按活动代码页解释直接命令行参数，`-charset filename=utf8` 本身不足以修复 Python 传入的中文路径。参数统一改经 ExifTool 官方 `-@ -` UTF-8 argfile 输入并使用 `#[CSTR]` 转义，保证中文、空格、反斜杠和换行文本可读写。
- 原始备份恢复：复用 ExifTool 默认 `_original` 备份作为恢复来源，使用 Python 标准库 `shutil`、`tempfile`、`os.replace` 和 SHA-256 校验实现显式、可逆的本地回滚；不新增依赖或联网行为。
- MSI 升级边界：cx_Freeze 会为每次构建生成 ProductCode，并依据 ProductVersion/Upgrade 表决定删除旧安装；功能或发布行为变化后必须提升数字版本。本次从 `0.1.0` 升至 `0.1.1`，使已安装 `0.1.0` 能通过固定 UpgradeCode 走标准更新路径。
- 构建方式补充：PyInstaller 使用 `tkinterdnd2` 官方 hook 收集当前平台 tkdnd 文件，构建后再统一裁剪非当前平台目录；cx_Freeze MSI 通过自定义 `build_exe` 命令在生成 MSI 前裁剪同类文件；同时显式排除 PaddleOCR/PyTorch/EasyOCR/winsdk 等重型或可选OCR依赖，避免默认 EXE/MSI 过大。
- 构建路径补充：PyInstaller 在写入或替换 `build/`、`dist/`、`build/pyinstaller-spec/` 前必须拒绝 Windows directory junction、symbolic link 等 reparse point，并验证解析路径仍在项目根目录内；`.spec` 也必须输出到受保护的 build 子目录，避免构建清理或生成文件沿联接影响项目外文件。
- 构建路径冲突修复：设置独立 `--specpath` 后，PyInstaller 会以 spec 目录解释部分相对数据路径，导致 ExifTool 载荷找不到；因此所有数据载荷、模块搜索路径、版本文件和入口脚本统一从项目根目录计算绝对路径，避免安全隔离与构建输入解析互相冲突。
- UI 状态补充：预设下拉框的显示值和左侧可编辑字段必须保持一致，读取新文件造成字段回填时不能留下“顶部有选择、左侧无参数”的错位状态。
- GUI 线程补充：Python 官方文档说明跨线程 Tk 调用依赖事件循环；后台线程只允许投递到 `queue.Queue`，由 Tk 创建线程调度回写，窗口销毁前取消轮询回调。
- 媒体容器补充：`MOV/MP4/HEIC/HEIF` 的写入路径必须根据目标扩展名追加 QuickTime 容器标签；GPS 写入必须保持经纬度成对，否则停止保存并提示用户。
- 写入结果补充：ExifTool 返回码为 0 只能证明命令执行完成，不能证明元数据已落盘；发布前回归测试必须覆盖 `0 image files updated` 不被误报为成功。
- 隐私扫描补充：Windows 路径大小写不敏感，敏感标记扫描必须覆盖大小写变体；MSI 必须扫描对应 cx_Freeze staging payload，不能只扫描安装包原始字节。
- 许可证补充：关键第三方许可证缺失必须中断构建，不能静默跳过后继续发布。
- 签名补充：未提供受信代码签名证书时必须跳过签名；`UnknownError` 或自签名状态不得当作可信签名成功。
- 联网行为：运行时无新增联网行为；OCR 不会自动下载模型，PaddleOCR 只使用本地缓存目录。
- 许可证：ExifTool 和 PyInstaller 都需要在分发时保留许可证说明；未复制 GPL GUI 源码。
- 许可证补充：tkinterdnd2 为 MIT；Tesseract、EasyOCR、PaddleOCR 为 Apache-2.0；winsdk 为 MIT。
- 许可证分发补充：许可证收集改为从安装包 metadata 定位 PyInstaller COPYING、cx_Freeze LICENSE 和 tkinterdnd2 LICENSE；分发目录和 portable ZIP 都必须包含完整文本，不能只保留 `THIRD_PARTY.md` 摘要。

## 2026-07-11 GitHub / Google 复核

| 方案名称 | 来源 | 许可证 | 核心能力 | 优点 | 缺点 | 维护状态 | 与当前项目的契合度 | 可能冲突点 | 是否采用 | 采用方式 |
|---|---|---|---|---|---|---|---|---|---|---|
| LeoSetter | https://github.com/AHJ32/LeoSetter | 仓库未声明 LICENSE | 基于 ExifTool 的批量元数据编辑和模板 | 可参考批量处理、模板等后续交互方向 | 当前项目为单文件安全编辑；仓库热度和维护历史有限，且没有可确认的许可证 | GitHub 可访问，但仓库较新 | 低 | 无许可证不能复用代码；引入模板会扩大当前单文件工作流和测试面 | 不采用 | 不复制代码、不引入依赖；仅记录其批量模板功能作为未来独立需求的参考 |

- GitHub：通过公开仓库信息复核了 LeoSetter；由于没有可确认的许可证，不能把它的实现集成到本项目。
- Google：搜索入口返回浏览器验证/脚本页面，未获得可审计且可复用的结果，因此不以其内容作为选型依据。
- 本次没有新增第三方依赖、没有改变离线边界，也没有替换现有的 ExifTool 调用层。

## 2026-07-11 深入复核

| 方案名称 | 来源 | 许可证 | 核心能力 | 优点 | 缺点 | 维护状态 | 与当前项目的契合度 | 可能冲突点 | 是否采用 | 采用方式 |
|---|---|---|---|---|---|---|---|---|---|---|
| ExifTool QuickTime tag table 复核 | 随包 ExifTool 13.50 `QuickTime.pm` 与 https://exiftool.org/config.html | GPL 或 Artistic License | 验证 `Keys:LocationName`、`Keys/UserData:GPSCoordinates` 和时间标签的真实可写组 | 直接以当前随包版本的 tag table 校验，避免按网络示例猜测组名 | 不改变 ExifTool 二进制本身；不同播放器仍可能偏好不同组 | ExifTool 官方维护 | 高 | 不能将 `LocationName`/GPS 错写到 ItemList | 采用 | 仅作为现有写入映射的校验依据；真实临时 MP4 已验证写入和清空 |
| 批量编辑/模板工作流 | GitHub 搜索：ExifTool metadata editor；公开查询出现 HTTP 429，前次已审计 LeoSetter | 不确定或项目各异 | 批量套用元数据模板 | 可减少重复操作 | 当前需求是单文件安全编辑；会引入多文件事务、冲突处理、备份策略和更多测试面 | 信息不足 | 低 | 扩大原图保护和失败回滚范围 | 不采用 | 保持单文件工作流，后续如单独提出批量需求再设计事务模型 |

- 本轮网络搜索通过 Brave 公开索引完成；GitHub 查询遇到限流，因此没有以未验证仓库内容引入依赖或复制代码。
- 本轮没有新增运行时或构建时依赖，没有联网行为变化，没有新增许可证风险。

## 2026-07-11 GitHub 再复核

| 方案名称 | 来源 | 许可证 | 核心能力 | 优点 | 缺点 | 维护状态 | 与当前项目的契合度 | 可能冲突点 | 是否采用 | 采用方式 |
|---|---|---|---|---|---|---|---|---|---|---|
| ExifToolGUI | https://github.com/FrankBijnen/ExifToolGui | GPL-3.0 | 功能完整的 ExifTool GUI | 活跃、约 955 stars，可继续参考字段组织与交互边界 | GPL-3.0 不适合复制到当前轻量分发项目；技术栈不同 | GitHub API 显示 2026-07-11 有更新 | 中 | 复制代码会引入 GPL 派生许可义务 | 不采用 | 只保留“GUI 前端调用 ExifTool”的既有设计参考，不复制代码或依赖 |
| LeoSetter | https://github.com/AHJ32/LeoSetter | 未声明许可证 | 批量应用、模板和基础 EXIF/XMP 编辑 | 可作为未来批量/模板工作流的需求参考 | 无可确认许可证；当前单文件安全写入没有事务/回滚模型 | GitHub API 显示 2026-03-03 更新，约 5 stars | 低 | 直接复用无许可证，批量功能也会扩大备份、冲突和回滚边界 | 不采用 | 不复制、不引入；后续单独提出批量需求时再设计事务模型 |
| EditorialOS/photo-editor | https://github.com/EditorialOS/photo-editor | Apache-2.0 | 通过 ExifTool 写入可追溯的 XMP/IPTC 后期处理流程 | 许可证兼容，可借鉴“权利/拍摄上下文”字段建模方向 | 新项目、GitHub API 为 0 stars；面向编辑生产线，不匹配本地单文件编辑器 | GitHub API 显示 2026-07-06 更新 | 低 | 引入生产工作流会破坏当前轻量、离线、单文件边界 | 不采用 | 不复制、不引入依赖；只记录权利元数据可作为未来独立需求 |

- 本次使用 GitHub 公开 API 复核许可证、活跃度和维护信号；本机未安装 GitHub CLI，因此未依赖认证态或用户账号信息。
- 复核结果没有满足“成熟、许可证明确、能以最小集成解决当前问题”的新方案；当前继续复用 ExifTool 和 Tkinter 标准库。
- 未新增依赖、没有联网行为变化、没有新增许可证风险。运行时应用仍不会发起网络请求。

## 2026-07-11 发布脚本 reparse point 补充

| 方案名称 | 来源 | 许可证 | 核心能力 | 优点 | 缺点 | 维护状态 | 与当前项目的契合度 | 可能冲突点 | 是否采用 | 采用方式 |
|---|---|---|---|---|---|---|---|---|---|---|
| PowerShell 手动目录栈遍历 | Windows PowerShell / .NET `System.IO.DirectoryInfo` | Windows / .NET 平台能力 | 在递归删除或替换构建目录前检查目标树内部是否含 reparse point | 无新增依赖；不跟随目录联接继续递归；能在 `Remove-Item -Recurse` 前阻断越界风险 | 只负责构建脚本清理前检查，不能替代操作系统权限隔离 | Microsoft 维护 | 高 | 扫描大目录会增加少量构建前耗时 | 采用 | `build_exe.ps1` 和 `build_msi.ps1` 增加 `Assert-NoNestedReparsePoint`，在递归清理/替换前执行 |
| Python `os.scandir` / `stat` reparse point 检查 | Python 标准库 | PSF License | 在许可证收集、运行时 payload 裁剪等 Python 辅助脚本执行 `shutil.rmtree` 前拒绝符号链接、目录联接和其他 reparse point | 无新增依赖；同一检查可复用于多个脚本；能同时支持测试导入与 `python scripts\*.py` 入口 | 只负责发布脚本自身递归删除边界，不能替代系统权限控制 | Python 标准库维护 | 高 | 全量扫描 payload 会增加少量发布耗时 | 采用 | 新增 `scripts/path_safety.py`，`collect_licenses.py` 和 `prune_runtime_payload.py` 在递归删除前调用，并增加回归测试 |
| ExifTool `-config ""` 禁用默认配置 | ExifTool 官方 CLI 能力 | GPL 或 Artistic License | 阻止 ExifTool 自动加载用户目录或程序目录 `.ExifTool_config` | 不新增依赖；保持读写行为只由随包 ExifTool 与显式参数决定 | 禁用用户自定义 tag 扩展，符合本应用确定性写入边界 | ExifTool 官方维护 | 高 | `-config ""` 必须在命令行级参数中位于 `-@ -` 之前，不能放进 argfile | 采用 | `ExifToolClient._run()` 使用 `exiftool -config "" -@ -`，其余参数仍走 UTF-8 C-string argfile |
| 发布元数据与许可证 payload 断言 | PowerShell / .NET / Python 标准库 | Windows / PSF 平台能力 | 发布签名前校验实际 EXE 版本资源、MSI 属性和 dist/MSI staging 许可证文件 | 不新增依赖；能发现构建工具忽略版本文件、许可证 include 失效或 staging 缺文件 | 依赖 Windows FileVersionInfo 和 MSI COM，可运行于当前 Windows 发布环境 | 高 | 必须在签名前运行，避免半完成发布 | 采用 | `build_release.ps1` 增加 `Assert-ExeMetadata` 和 `Assert-LicensePayload`，并保留 MSI COM 元数据校验 |
| Authenticode 受信证书显式签名 | PowerShell `Set-AuthenticodeSignature` | Windows 平台能力 | 使用用户显式提供的代码签名证书指纹签署 EXE/MSI | 不创建虚假自签名证书；签名来源和信任状态可验证 | 需要用户自行持有并安装可信代码签名证书 | Microsoft 维护 | 高 | 未提供证书时必须保持未签名；`UnknownError` 不能视为成功 | 采用 | `PHOTO_META_EDITOR_SIGNING_CERT_THUMBPRINT` 存在时签名并要求状态 `Valid`，否则明确跳过 |

- 本次没有引入 GitHub/npm/PyPI 等新依赖。
- 直接复用 PowerShell/.NET 平台能力，符合当前 Windows 打包脚本技术栈。
- 修复范围限定在发布脚本安全边界，不改变运行时应用、网络行为或许可证义务。

## 2026-07-12 原始备份恢复事务复核

| 方案名称 | 来源 | 许可证 | 核心能力 | 优点 | 缺点 | 维护状态 | 与当前项目的契合度 | 可能冲突点 | 是否采用 | 采用方式 |
|---|---|---|---|---|---|---|---|---|---|---|
| Python `open("xb")` + `tempfile` + `os.replace` + SHA-256 | Python 标准库 | PSF License | 排他创建恢复前副本、同目录原子替换、写后校验和失败回滚 | 无新增依赖；能精确维持“不覆盖回滚副本、失败不改变当前文件”的不变量 | 只保证进程运行期间的事务式回滚，不宣称断电后的持久化事务 | Python 官方维护 | 高 | 必须区分替换前失败与替换后校验失败，后者需要从已校验副本回滚 | 采用 | `_before_restore` 使用 `xb` 排他创建并校验；替换后校验失败时复制该副本并再次 `os.replace` 回滚 |
| `atomicwrites` | PyPI / GitHub | MIT | 封装临时文件和原子替换 | API 简洁 | 项目已能用标准库完成；新增依赖和许可证分发工作超过收益，且不能替代业务层摘要校验和回滚副本语义 | 项目维护活跃度有限 | 低 | 会增加构建、许可证与离线分发范围，仍需自研恢复事务状态 | 不采用 | 不引入；仅使用标准库最小修复 |

- 第一性原理不变量：用户当前文件必须先有一个不覆盖既有文件、内容已校验的恢复前副本；一旦 `_original` 替换后的校验失败，函数返回错误前必须把当前文件回滚到调用前字节。
- 根因：旧实现用 `shutil.copy2` 写 `_before_restore`，存在检查后到复制时的竞态覆盖；`os.replace` 完成后的校验失败也只报错，没有回滚已改变的目标文件。
- 最小修复：新增排他复制函数、替换前并发修改复核和替换后回滚路径；不改变成功恢复接口、不引入新依赖、不增加联网行为。
- 发布版本从 `0.1.1` 提升到 `0.1.2`，用于区分恢复安全语义变化并保持 MSI 升级路径可靠。

## 2026-07-12 双语界面与 GitHub 发布方案

| 方案名称 | 来源 | 许可证 | 核心能力 | 优点 | 缺点 | 维护状态 | 与当前项目的契合度 | 可能冲突点 | 是否采用 | 采用方式 |
|---|---|---|---|---|---|---|---|---|---|---|
| Python 标准库字典 + JSON 设置 | Python 标准库 | PSF License | 中英文界面映射及语言偏好持久化 | 无新增依赖；适合当前两种语言和 Tkinter 小型 UI；离线可用 | 新增第三种语言时需要扩展映射 | Python 官方维护 | 高 | 必须覆盖动态状态、对话框、字段标签与窗口控件，不能只翻译按钮 | 采用 | 新增 `i18n.py`、`settings.py`，界面切换后更新控件并保存到用户 AppData |
| `gettext` | Python 标准库 | PSF License | 标准 PO/MO 国际化流程 | 适合多语言和翻译团队 | 当前只有中英文，需额外维护消息提取、PO/MO 编译与打包流程 | Python 官方维护 | 中 | 会扩大构建与发布验证范围 | 不采用 | 保留为未来语言数量明显增加时的迁移方向 |
| Babel | PyPI | BSD-3-Clause | 消息提取、区域格式化与翻译目录 | 生态成熟 | 当前不需要复杂日期、数字本地化；新增依赖、许可证和打包体积超过收益 | 活跃维护 | 低 | 与项目少依赖、离线轻量边界不匹配 | 不采用 | 不引入 |
| GitHub REST API + Git Credential Manager | GitHub 官方 API / 本机 Git 凭据 | GitHub 平台能力 | 创建公开仓库、推送源码、创建 Release 并上传资产 | 无新增项目依赖；不需要提交 workflow；适合当前已有 Git 凭据但缺少 `workflow` scope 的环境 | 依赖本机已有 GitHub 凭据；无法作为 CI 自动发布方案 | GitHub 官方维护 | 高 | token 必须有仓库创建、推送和 Release 上传权限；若提交 workflow 还需额外 `workflow` scope | 采用 | 使用 GitHub API 创建 Release 并上传 `release-assets/` |
| `softprops/action-gh-release` | GitHub Marketplace | MIT | 封装 Release 创建和资产上传 | 使用简洁、社区成熟 | 额外第三方 Action 供应链与版本审计不如 runner 内置 `gh` 简单 | 活跃维护 | 中 | 增加第三方 CI 依赖 | 不采用 | 使用 GitHub 官方 runner 内置 CLI 替代 |

- 技术栈冲突：无；i18n 保持在 GUI/设置模块内，ExifTool 字段映射和写入层不变。
- 离线边界：语言切换只读写本地 AppData JSON，不发起网络请求。
- 许可证：项目源码采用 MIT；第三方组件继续随分发包附带各自许可证。
- GitHub 发布：仓库名采用 `photo-metadata-editor`，与项目功能和 PyPI 包名一致；版本沿用现有 `0.1.2`，Release tag 为 `v0.1.2`。

## 2026-07-12 MSI 安装失败修复

- 期望不变量：MSI 的安装目标已经位于本机系统盘时，用户 Documents 等 Shell Folder 被重定向到不可用网络盘或移动盘，不应导致 `CostFinalize` 失败。
- 最小复现：真实静默安装返回 `1603`；详细 MSI 日志显示 `PersonalFolder` 被重定向到不可用路径，`CostFinalize` 报 `Error 1606`。即使把 `ROOTDRIVE` 修正到系统盘，失效的 `PersonalFolder` 仍会让成本计算失败。
- 根因层级：Windows Installer 环境/目录成本计算边界；不是应用文件、权限或 cx_Freeze payload 数据损坏。
- 采用方案：复用 MSI Type 51 CustomAction，在成本计算前把安装会话的 `PersonalFolder` 设为已由 Windows Installer 解析的本地 `[LocalAppDataFolder]`，并把 `ROOTDRIVE` 设为 `[WindowsVolume]`。这些值只存在于本次 MSI 会话，不修改用户注册表或系统 Shell Folder 设置；无新增依赖或许可证。
- 不采用：硬编码 `C:\`，因为 Windows 可能安装在其他系统盘；也不接受只用行政解包代替真实安装测试。
- 验证方式：重新构建 MSI 后执行真实静默安装、启动已安装 EXE、再按 ProductCode 静默卸载。

### ExifTool runtime 目录标识冲突补充

- 最小隔离：移除 ExifTool runtime 后，同一 cx_Freeze MSI 在相同环境真实安装成功；恢复 runtime 后在 `CostFinalize` 失败。
- 根因：cx_Freeze 默认把文件夹名直接用作 MSI Directory identifier。ExifTool Perl runtime 含 `lib/Text` 等通用名称，而 MSI Directory identifier 同时处于 Windows Installer 全局属性命名空间；`Text` 可被安装界面/动作状态覆盖为时间文本，导致目录成本计算把时间当路径并报 1606。
- 修复：保留 cx_Freeze 的 CAB、Feature、Component 与文件添加逻辑，只在自定义 `BuildMsiCommand.add_files()` 中把非根目录标识改为基于相对路径 SHA-256 的稳定 `PME_DIR_*` 名称；实际安装目录名完全不变。
- 方案取舍：不删除 ExifTool runtime、不修改第三方目录名、不换用 WiX/Inno Setup；最小适配 cx_Freeze 扩展点，并通过真实安装/卸载验证。
