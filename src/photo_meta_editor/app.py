from __future__ import annotations

from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable, TypeVar
import webbrowser

from .exiftool import ExifToolClient, ExifToolError, original_backup_path
from .fields import EDITABLE_FIELDS, FieldSpec, extract_field_values, metadata_rows
from .i18n import LANGUAGE_BY_LABEL, LANGUAGE_LABELS, translate_text
from .metadata import APP_COPYRIGHT, APP_CREATOR, APP_DESCRIPTION, APP_EMAIL, APP_NAME, APP_VERSION, APP_WEBSITE
from .ocr import OcrDateResult, OcrError, available_ocr_engines, extract_datetime_from_image
from .presets import (
    camera_preset_names,
    find_camera_preset,
    find_location_preset,
    location_preset_names,
)
from .settings import load_language, save_language

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except Exception:  # noqa: BLE001 - drag/drop is optional when dependency is unavailable.
    DND_FILES = ""
    TkinterDnD = None


FILE_TYPES = (
    ("媒体文件", "*.jpg *.jpeg *.png *.tif *.tiff *.heic *.heif *.webp *.mov *.mp4"),
    ("图片文件", "*.jpg *.jpeg *.png *.tif *.tiff *.heic *.heif *.webp"),
    ("所有文件", "*.*"),
)

PALETTES = {
    "light": {
        "bg": "#f4f6f8",
        "panel": "#ffffff",
        "panel_alt": "#f8fafc",
        "fg": "#111827",
        "muted": "#64748b",
        "entry": "#ffffff",
        "readonly": "#f8fafc",
        "entry_fg": "#111827",
        "accent": "#2563eb",
        "accent_hover": "#1d4ed8",
        "drop": "#e8f0ff",
        "status": "#e5e7eb",
        "border": "#cbd5e1",
        "button": "#ffffff",
        "button_hover": "#eef2ff",
        "heading": "#f8fafc",
        "select_bg": "#2563eb",
        "select_fg": "#ffffff",
        "preset_entry": "#e9f8f3",
        "preset_border": "#0f766e",
    },
    "dark": {
        "bg": "#181a17",
        "panel": "#22241f",
        "panel_alt": "#2c2f29",
        "fg": "#f3f5ef",
        "muted": "#b3b8ac",
        "entry": "#191c18",
        "readonly": "#242721",
        "entry_fg": "#f3f5ef",
        "accent": "#24b68a",
        "accent_hover": "#4bca9f",
        "drop": "#1a2b24",
        "status": "#1d201c",
        "border": "#4a4e45",
        "button": "#30342e",
        "button_hover": "#3b4038",
        "heading": "#292d27",
        "select_bg": "#16795f",
        "select_fg": "#ffffff",
        "preset_entry": "#173d30",
        "preset_border": "#4bca9f",
    },
}

T = TypeVar("T")


class MetadataEditorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.drag_drop_enabled = bool(getattr(root, "_photo_meta_editor_dnd_enabled", False))
        self.root.title(APP_NAME)
        self.root.geometry("1280x820")
        self.root.minsize(980, 680)

        self.client = ExifToolClient()
        self.current_file: Path | None = None
        self.current_metadata: dict[str, object] = {}
        self.initial_values: dict[str, str] = {}
        self.is_busy = False
        self.is_closing = False
        self.active_task_id = 0
        self.current_task_kind: str | None = None
        self.ui_callback_queue: queue.Queue[Callable[[], None]] = queue.Queue()
        self.ui_callback_after_id: str | None = None
        self.entry_vars: dict[str, tk.StringVar] = {}
        self.editable_entry_widgets: dict[str, ttk.Entry] = {}
        self.text_widgets: dict[str, tk.Text] = {}
        self.preset_field_keys: set[str] = set()
        self._preset_write_keys: set[str] = set()
        self.editor_canvas: tk.Canvas | None = None
        self.editor_inner: ttk.Frame | None = None
        self.canvases: list[tk.Canvas] = []
        self.drop_widgets: list[tk.Widget] = []
        self.busy_sensitive_widgets: list[tk.Widget] = []
        self.busy_readonly_widgets: list[tk.Widget] = []
        self.option_widgets: list[tk.Widget] = []
        self.translatable_widget_texts: dict[tk.Widget, str] = {}

        self.language = load_language()
        self.language_var = tk.StringVar(value=LANGUAGE_LABELS[self.language])

        self.preserve_backup_var = tk.BooleanVar(value=True)
        self.sync_file_time_var = tk.BooleanVar(value=False)
        self.dark_mode_var = tk.BooleanVar(value=False)
        self.filter_var = tk.StringVar()
        self.path_var = tk.StringVar()
        self.camera_preset_var = tk.StringVar()
        self.location_preset_var = tk.StringVar()
        self.preset_summary_var = tk.StringVar()
        self.preset_summary_label: ttk.Label | None = None
        engines = ", ".join(available_ocr_engines()) or "未检测到本地OCR引擎"
        # ExifToolClient validates the bundled executable path without starting a
        # process.  Do not run `exiftool -ver` here: startup must not wait for an
        # external process before the Tk event loop can show the window.
        self.status_source_text = f"ExifTool 已就绪；OCR：{engines}"
        self.status_var = tk.StringVar(value=self.tr(self.status_source_text))

        self.style = ttk.Style()
        self._configure_style()
        self._build_ui()
        self._capture_translatable_widgets(self.root)
        self.apply_language(persist=False)
        self.update_editor_enabled_state()
        self._bind_preset_traces()
        self.apply_theme()
        self._bind_shortcuts()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self._schedule_ui_callback_drain()
        self.register_drag_drop()

    def _configure_style(self) -> None:
        if "clam" in self.style.theme_names() and self.style.theme_use() != "clam":
            self.style.theme_use("clam")

    def palette(self) -> dict[str, str]:
        return PALETTES["dark" if self.dark_mode_var.get() else "light"]

    def tr(self, text: str) -> str:
        return translate_text(text, self.language)

    def set_status(self, text: str) -> None:
        self.status_source_text = text
        self.status_var.set(self.tr(text))

    def _capture_translatable_widgets(self, parent: tk.Misc) -> None:
        for widget in parent.winfo_children():
            try:
                text = str(widget.cget("text"))
            except (tk.TclError, AttributeError):
                text = ""
            if text:
                self.translatable_widget_texts[widget] = text
            self._capture_translatable_widgets(widget)

    def on_language_selected(self, _event: tk.Event | None = None) -> None:
        selected = LANGUAGE_BY_LABEL.get(self.language_var.get())
        if selected and selected != self.language:
            self.language = selected
            self.apply_language(persist=True)

    def apply_language(self, persist: bool = True) -> None:
        self.language_var.set(LANGUAGE_LABELS[self.language])
        for widget, source_text in tuple(self.translatable_widget_texts.items()):
            try:
                if widget.winfo_exists():
                    widget.configure(text=self.tr(source_text))
            except tk.TclError:
                continue
        if hasattr(self, "metadata_tree"):
            self.metadata_tree.heading("tag", text=self.tr("标签"))
            self.metadata_tree.heading("value", text=self.tr("值"))
        self.status_var.set(self.tr(self.status_source_text))
        self.update_preset_summary()
        if persist:
            try:
                save_language(self.language)
            except OSError:
                pass

    def show_info(self, title: str, message: str) -> None:
        messagebox.showinfo(self.tr(title), self.tr(message), parent=self.root)

    def show_warning(self, title: str, message: str) -> None:
        messagebox.showwarning(self.tr(title), self.tr(message), parent=self.root)

    def ask_yes_no(self, title: str, message: str, **kwargs: object) -> bool:
        return bool(messagebox.askyesno(self.tr(title), self.tr(message), parent=self.root, **kwargs))

    def ask_yes_no_cancel(self, title: str, message: str, **kwargs: object) -> bool | None:
        return messagebox.askyesnocancel(self.tr(title), self.tr(message), parent=self.root, **kwargs)

    def apply_theme(self) -> None:
        palette = self.palette()
        self.root.tk_setPalette(
            background=palette["bg"],
            foreground=palette["fg"],
            activeBackground=palette["button_hover"],
            activeForeground=palette["fg"],
            highlightBackground=palette["border"],
            highlightColor=palette["accent"],
            selectBackground=palette["select_bg"],
            selectForeground=palette["select_fg"],
            insertBackground=palette["entry_fg"],
            troughColor=palette["panel"],
        )
        self.root.configure(bg=palette["bg"])
        self.root.option_add("*Background", palette["bg"])
        self.root.option_add("*Foreground", palette["fg"])
        self.root.option_add("*activeBackground", palette["button_hover"])
        self.root.option_add("*activeForeground", palette["fg"])
        self.root.option_add("*selectBackground", palette["select_bg"])
        self.root.option_add("*selectForeground", palette["select_fg"])
        self.root.option_add("*selectColor", palette["accent"])
        self.root.option_add("*highlightBackground", palette["border"])
        self.root.option_add("*highlightColor", palette["accent"])
        self.root.option_add("*Entry.Background", palette["entry"])
        self.root.option_add("*Entry.Foreground", palette["entry_fg"])
        self.root.option_add("*Entry.InsertBackground", palette["entry_fg"])
        self.root.option_add("*Text.Background", palette["entry"])
        self.root.option_add("*Text.Foreground", palette["entry_fg"])
        self.root.option_add("*Text.InsertBackground", palette["entry_fg"])
        self.root.option_add("*Listbox.Background", palette["entry"])
        self.root.option_add("*Listbox.Foreground", palette["entry_fg"])
        self.root.option_add("*Listbox.selectBackground", palette["select_bg"])
        self.root.option_add("*Listbox.selectForeground", palette["select_fg"])
        self.root.option_add("*TCombobox*Listbox*Background", palette["entry"])
        self.root.option_add("*TCombobox*Listbox*Foreground", palette["entry_fg"])
        self.root.option_add("*TCombobox*Listbox*selectBackground", palette["select_bg"])
        self.root.option_add("*TCombobox*Listbox*selectForeground", palette["select_fg"])
        self.root.option_add("*TCombobox*Listbox.background", palette["entry"])
        self.root.option_add("*TCombobox*Listbox.foreground", palette["entry_fg"])
        self.root.option_add("*TCombobox*Listbox.selectBackground", palette["select_bg"])
        self.root.option_add("*TCombobox*Listbox.selectForeground", palette["select_fg"])
        self.style.configure("TFrame", background=palette["bg"])
        self.style.configure("Surface.TFrame", background=palette["panel"], relief="solid", borderwidth=1, bordercolor=palette["border"])
        self.style.configure("PanelBody.TFrame", background=palette["panel"])
        self.style.configure("TPanedwindow", background=palette["bg"])
        self.style.configure("Sash", background=palette["border"])
        self.style.configure("Panel.TLabelframe", background=palette["panel"], padding=10, bordercolor=palette["border"], relief="solid")
        self.style.configure("Panel.TLabelframe.Label", font=("Microsoft YaHei UI", 10, "bold"), foreground=palette["fg"], background=palette["panel"])
        self.style.configure("Header.TLabel", font=("Microsoft YaHei UI", 11, "bold"), foreground=palette["fg"], background=palette["bg"])
        self.style.configure("Hint.TLabel", foreground=palette["muted"], background=palette["bg"])
        self.style.configure("Panel.TLabel", foreground=palette["fg"], background=palette["panel"])
        self.style.configure("PanelHint.TLabel", foreground=palette["muted"], background=palette["panel"])
        self.style.configure("Section.TLabel", foreground=palette["fg"], background=palette["panel"], font=("Microsoft YaHei UI", 10, "bold"))
        self.style.configure(
            "PresetSummary.TLabel",
            foreground=palette["preset_border"],
            background=palette["panel"],
            font=("Microsoft YaHei UI", 9),
            padding=(0, 0, 0, 6),
        )
        self.style.configure("FactLabel.TLabel", foreground=palette["muted"], background=palette["panel"], font=("Microsoft YaHei UI", 9))
        self.style.configure("Drop.TLabel", foreground=palette["fg"], background=palette["drop"], padding=(12, 12), relief="solid", bordercolor=palette["border"])
        self.style.configure("Status.TLabel", foreground=palette["fg"], background=palette["status"], padding=(10, 6))
        self.style.configure("TLabel", foreground=palette["fg"], background=palette["bg"])
        self.style.configure(
            "TCheckbutton",
            foreground=palette["fg"],
            background=palette["panel"],
            focuscolor=palette["accent"],
            indicatorcolor=palette["entry"],
            indicatorbackground=palette["entry"],
        )
        self.style.map("TCheckbutton", background=[("active", palette["panel"])], foreground=[("disabled", palette["muted"])])
        self.style.map(
            "TCheckbutton",
            indicatorcolor=[("selected", palette["accent"]), ("disabled", palette["panel_alt"]), ("!selected", palette["entry"])],
            indicatorbackground=[("selected", palette["accent"]), ("disabled", palette["panel_alt"]), ("!selected", palette["entry"])],
        )
        self.style.configure(
            "TButton",
            padding=(10, 6),
            foreground=palette["fg"],
            background=palette["button"],
            bordercolor=palette["border"],
            lightcolor=palette["button"],
            darkcolor=palette["button"],
            focuscolor=palette["accent"],
            relief="solid",
        )
        self.style.map(
            "TButton",
            background=[("pressed", palette["accent"]), ("active", palette["button_hover"])],
            foreground=[("disabled", palette["muted"]), ("pressed", palette["select_fg"])],
            bordercolor=[("focus", palette["accent"]), ("active", palette["accent"])],
        )
        self.style.configure(
            "Primary.TButton",
            padding=(12, 6),
            foreground=palette["select_fg"],
            background=palette["accent"],
            bordercolor=palette["accent"],
            lightcolor=palette["accent"],
            darkcolor=palette["accent"],
            focuscolor=palette["accent"],
            relief="solid",
        )
        self.style.map(
            "Primary.TButton",
            background=[("pressed", palette["accent_hover"]), ("active", palette["accent_hover"]), ("disabled", palette["button"])],
            foreground=[("disabled", palette["muted"])],
            bordercolor=[("disabled", palette["border"]), ("focus", palette["accent_hover"])],
        )
        self.style.configure(
            "TEntry",
            fieldbackground=palette["entry"],
            foreground=palette["entry_fg"],
            insertcolor=palette["entry_fg"],
            selectbackground=palette["select_bg"],
            selectforeground=palette["select_fg"],
            readonlybackground=palette["entry"],
            bordercolor=palette["border"],
            lightcolor=palette["entry"],
            darkcolor=palette["entry"],
            relief="solid",
            padding=(4, 3),
        )
        self.style.map(
            "TEntry",
            fieldbackground=[("readonly", palette["readonly"]), ("disabled", palette["panel"]), ("active", palette["entry"])],
            foreground=[("readonly", palette["entry_fg"]), ("disabled", palette["muted"])],
            bordercolor=[("focus", palette["accent"])],
        )
        self.style.configure(
            "Editable.TEntry",
            fieldbackground=palette["entry"],
            foreground=palette["entry_fg"],
            insertcolor=palette["entry_fg"],
            selectbackground=palette["select_bg"],
            selectforeground=palette["select_fg"],
            bordercolor=palette["border"],
            lightcolor=palette["entry"],
            darkcolor=palette["entry"],
            relief="solid",
            padding=(4, 3),
        )
        self.style.map(
            "Editable.TEntry",
            fieldbackground=[("disabled", palette["panel"]), ("active", palette["entry"])],
            foreground=[("disabled", palette["muted"])],
            bordercolor=[("focus", palette["accent"])],
        )
        self.style.configure(
            "Preset.TEntry",
            fieldbackground=palette["preset_entry"],
            foreground=palette["entry_fg"],
            insertcolor=palette["entry_fg"],
            selectbackground=palette["select_bg"],
            selectforeground=palette["select_fg"],
            bordercolor=palette["preset_border"],
            lightcolor=palette["preset_entry"],
            darkcolor=palette["preset_entry"],
            relief="solid",
            padding=(4, 3),
        )
        self.style.map(
            "Preset.TEntry",
            fieldbackground=[("disabled", palette["panel_alt"]), ("active", palette["preset_entry"])],
            foreground=[("disabled", palette["muted"])],
            bordercolor=[("focus", palette["accent_hover"])],
        )
        self.style.configure(
            "Fact.TEntry",
            fieldbackground=palette["readonly"],
            foreground=palette["entry_fg"],
            readonlybackground=palette["readonly"],
            bordercolor=palette["border"],
            lightcolor=palette["readonly"],
            darkcolor=palette["readonly"],
            relief="solid",
            padding=(4, 3),
        )
        self.style.map(
            "Fact.TEntry",
            fieldbackground=[("readonly", palette["readonly"]), ("disabled", palette["panel"])],
            foreground=[("readonly", palette["entry_fg"]), ("disabled", palette["muted"])],
        )
        self.style.configure(
            "TCombobox",
            fieldbackground=palette["entry"],
            foreground=palette["entry_fg"],
            background=palette["button"],
            arrowcolor=palette["fg"],
            selectbackground=palette["select_bg"],
            selectforeground=palette["select_fg"],
            bordercolor=palette["border"],
            lightcolor=palette["entry"],
            darkcolor=palette["entry"],
            relief="solid",
            padding=(4, 3),
        )
        self.style.map(
            "TCombobox",
            fieldbackground=[("readonly", palette["entry"]), ("disabled", palette["panel"]), ("active", palette["entry"])],
            background=[("readonly", palette["button"]), ("active", palette["button_hover"]), ("disabled", palette["panel"])],
            foreground=[("readonly", palette["entry_fg"]), ("disabled", palette["muted"])],
            selectbackground=[("readonly", palette["select_bg"])],
            selectforeground=[("readonly", palette["select_fg"])],
            arrowcolor=[("readonly", palette["fg"]), ("disabled", palette["muted"])],
            bordercolor=[("focus", palette["accent"])],
        )
        self.style.configure(
            "Treeview",
            background=palette["entry"],
            fieldbackground=palette["entry"],
            foreground=palette["entry_fg"],
            bordercolor=palette["border"],
            rowheight=24,
        )
        self.style.configure("Treeview.Heading", foreground=palette["fg"], background=palette["heading"], relief="flat")
        self.style.map("Treeview", background=[("selected", palette["select_bg"])], foreground=[("selected", palette["select_fg"])])
        self.style.map("Treeview.Heading", background=[("active", palette["button_hover"])], foreground=[("active", palette["fg"])])
        self.style.configure("TSeparator", background=palette["border"])
        self.style.configure(
            "TScrollbar",
            background=palette["button"],
            troughcolor=palette["panel"],
            bordercolor=palette["border"],
            arrowcolor=palette["fg"],
            relief="flat",
        )
        self.style.map(
            "TScrollbar",
            background=[("active", palette["button_hover"]), ("pressed", palette["accent"])],
            arrowcolor=[("disabled", palette["muted"]), ("active", palette["fg"])],
        )

        for canvas in self.canvases:
            canvas.configure(background=palette["panel"])
        for text in self.text_widgets.values():
            text.configure(
                background=palette["entry"],
                foreground=palette["entry_fg"],
                insertbackground=palette["entry_fg"],
                highlightbackground=palette["border"],
                highlightcolor=palette["accent"],
                selectbackground=palette["select_bg"],
                selectforeground=palette["select_fg"],
            )
        if hasattr(self, "metadata_tree"):
            self.metadata_tree.tag_configure("odd", background=palette["entry"], foreground=palette["entry_fg"])
            self.metadata_tree.tag_configure("even", background=palette["heading"], foreground=palette["entry_fg"])

    def _build_ui(self) -> None:
        root_frame = ttk.Frame(self.root, padding=12)
        root_frame.pack(fill=tk.BOTH, expand=True)

        self._build_toolbar(root_frame)
        self._build_drop_zone(root_frame)
        self._build_preset_bar(root_frame)

        paned = ttk.PanedWindow(root_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        editor_panel = ttk.LabelFrame(paned, text="可编辑信息 / 照片参数", style="Panel.TLabelframe")
        metadata_panel = ttk.LabelFrame(paned, text="全部元数据", style="Panel.TLabelframe")
        paned.add(editor_panel, weight=2)
        paned.add(metadata_panel, weight=3)

        self._build_editor(editor_panel)
        self._build_metadata_table(metadata_panel)

        status = ttk.Label(self.root, textvariable=self.status_var, anchor=tk.W, style="Status.TLabel")
        status.pack(side=tk.BOTTOM, fill=tk.X)

    def _build_toolbar(self, parent: ttk.Frame) -> None:
        toolbar = ttk.Frame(parent, style="Surface.TFrame", padding=(10, 8))
        toolbar.pack(fill=tk.X)
        ttk.Label(toolbar, text="文件", style="Panel.TLabel").grid(row=0, column=0, sticky=tk.W, padx=(0, 8))
        ttk.Entry(toolbar, textvariable=self.path_var, state="readonly").grid(row=0, column=1, sticky=tk.EW)
        self.choose_button = ttk.Button(toolbar, text="选择", command=self.choose_file)
        self.choose_button.grid(row=0, column=2, padx=(8, 0))
        self.reload_button = ttk.Button(toolbar, text="刷新", command=self.reload_file, state=tk.DISABLED)
        self.reload_button.grid(row=0, column=3, padx=(8, 0))
        self.save_button = ttk.Button(toolbar, text="保存修改", command=self.save_changes, state=tk.DISABLED, style="Primary.TButton")
        self.save_button.grid(row=0, column=4, padx=(8, 0))
        self.about_button = ttk.Button(toolbar, text="关于", command=self.show_about)
        self.about_button.grid(row=0, column=5, padx=(8, 0))
        self.dark_mode_check = ttk.Checkbutton(toolbar, text="暗色", variable=self.dark_mode_var, command=self.apply_theme)
        self.dark_mode_check.grid(row=1, column=4, sticky=tk.E, padx=(8, 0), pady=(8, 0))
        ttk.Label(toolbar, text="语言 / Language", style="Panel.TLabel").grid(row=1, column=5, sticky=tk.E, padx=(12, 6), pady=(8, 0))
        self.language_combo = ttk.Combobox(
            toolbar,
            textvariable=self.language_var,
            values=tuple(LANGUAGE_LABELS.values()),
            state="readonly",
            width=10,
        )
        self.language_combo.grid(row=1, column=6, sticky=tk.E, pady=(8, 0))
        self.language_combo.bind("<<ComboboxSelected>>", self.on_language_selected)
        toolbar.columnconfigure(1, weight=1)
        self.busy_sensitive_widgets.extend([self.choose_button, self.reload_button, self.save_button, self.about_button])
        self.busy_readonly_widgets.append(self.language_combo)

    def _bind_preset_traces(self) -> None:
        self.camera_preset_var.trace_add("write", lambda *_args: self.apply_camera_preset(show_message=False))
        self.location_preset_var.trace_add("write", lambda *_args: self.apply_location_preset(show_message=False))

    def _build_drop_zone(self, parent: ttk.Frame) -> None:
        text = "拖拽图片或视频文件到这里导入" if self.drag_drop_enabled else "拖拽组件不可用，请使用“选择”导入"
        self.drop_label = ttk.Label(parent, text=text, anchor=tk.CENTER, style="Drop.TLabel")
        self.drop_label.pack(fill=tk.X, pady=(10, 8))
        self.drop_widgets.append(self.drop_label)

    def _build_preset_bar(self, parent: ttk.Frame) -> None:
        preset_frame = ttk.Frame(parent, style="Surface.TFrame", padding=(10, 8))
        preset_frame.pack(fill=tk.X, pady=(8, 8))

        ttk.Label(preset_frame, text="相机预设", style="Panel.TLabel").grid(row=0, column=0, sticky=tk.W, padx=(0, 6))
        self.camera_combo = ttk.Combobox(
            preset_frame,
            textvariable=self.camera_preset_var,
            values=camera_preset_names(),
            state="readonly",
            width=28,
        )
        self.camera_combo.grid(row=0, column=1, sticky=tk.EW)
        self.camera_apply_button = ttk.Button(preset_frame, text="套用相机", command=self.apply_camera_preset)
        self.camera_apply_button.grid(row=0, column=2, sticky=tk.EW, padx=(6, 12))

        ttk.Label(preset_frame, text="地点预设", style="Panel.TLabel").grid(row=1, column=0, sticky=tk.W, padx=(0, 6), pady=(8, 0))
        self.location_combo = ttk.Combobox(
            preset_frame,
            textvariable=self.location_preset_var,
            values=location_preset_names(),
            state="readonly",
            width=24,
        )
        self.location_combo.grid(row=1, column=1, sticky=tk.EW, pady=(8, 0))
        self.location_apply_button = ttk.Button(preset_frame, text="套用GPS", command=self.apply_location_preset)
        self.location_apply_button.grid(row=1, column=2, sticky=tk.EW, padx=(6, 12), pady=(8, 0))

        self.ocr_button = ttk.Button(preset_frame, text="OCR识别时间", command=self.run_ocr_datetime)
        self.ocr_button.grid(row=0, column=3, sticky=tk.EW)

        self.preserve_backup_check = ttk.Checkbutton(preset_frame, text="保留 _original 备份", variable=self.preserve_backup_var)
        self.preserve_backup_check.grid(row=1, column=3, sticky=tk.W, pady=(8, 0))
        self.sync_file_time_check = ttk.Checkbutton(preset_frame, text="保存时同步文件创建/修改时间", variable=self.sync_file_time_var)
        self.sync_file_time_check.grid(
            row=2,
            column=1,
            columnspan=3,
            sticky=tk.W,
            pady=(8, 0),
        )
        self.restore_button = ttk.Button(
            preset_frame,
            text="恢复备份",
            command=self.restore_original_backup,
            state=tk.DISABLED,
        )
        self.restore_button.grid(row=2, column=0, sticky=tk.EW, pady=(8, 0), padx=(0, 6))
        preset_frame.columnconfigure(1, weight=1)
        preset_frame.columnconfigure(3, weight=0)
        self.option_widgets.extend([self.preserve_backup_check, self.sync_file_time_check])
        self.busy_sensitive_widgets.extend(
            [self.camera_apply_button, self.location_apply_button, self.ocr_button, self.restore_button, *self.option_widgets]
        )
        self.busy_readonly_widgets.extend([self.camera_combo, self.location_combo])

    def _build_editor(self, parent: ttk.Frame) -> None:
        # A selected preset is state the user must be able to see while the
        # editable form scrolls to the affected fields. Keep its value summary
        # outside the scroll area so it cannot disappear above the viewport.
        preset_summary_area = ttk.Frame(parent, style="PanelBody.TFrame")
        preset_summary_area.pack(fill=tk.X, pady=(0, 6))
        self.preset_summary_label = ttk.Label(
            preset_summary_area,
            textvariable=self.preset_summary_var,
            style="PresetSummary.TLabel",
            justify=tk.LEFT,
            wraplength=420,
        )
        self.preset_summary_label.pack(fill=tk.X, anchor=tk.W)
        self.preset_summary_label.pack_forget()

        editor_inner = self._build_scroll_area(parent)
        editable_fields = [field for field in EDITABLE_FIELDS if not field.readonly]
        readonly_fields = [field for field in EDITABLE_FIELDS if field.readonly]

        row = 0
        ttk.Label(editor_inner, text="可编辑信息", style="Section.TLabel").grid(
            row=row,
            column=0,
            columnspan=2,
            sticky=tk.W,
            pady=(2, 6),
        )
        row += 1
        for field in editable_fields:
            self._build_editable_field(editor_inner, row, field)
            row += 2

        ttk.Separator(editor_inner, orient=tk.HORIZONTAL).grid(
            row=row,
            column=0,
            columnspan=2,
            sticky=tk.EW,
            pady=(14, 8),
        )
        row += 1
        ttk.Label(editor_inner, text="照片参数（只读）", style="Section.TLabel").grid(
            row=row,
            column=0,
            columnspan=2,
            sticky=tk.W,
            pady=(0, 4),
        )
        row += 1
        facts_frame = ttk.Frame(editor_inner, style="PanelBody.TFrame")
        facts_frame.grid(row=row, column=0, columnspan=2, sticky=tk.EW)

        self._build_fact_fields(facts_frame, readonly_fields)
        editor_inner.columnconfigure(1, weight=1)

    def _build_scroll_area(self, parent: ttk.Frame) -> ttk.Frame:
        canvas = tk.Canvas(parent, highlightthickness=0, background=self.palette()["panel"])
        self.editor_canvas = canvas
        self.canvases.append(canvas)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        inner = ttk.Frame(canvas, style="PanelBody.TFrame")
        self.editor_inner = inner
        inner.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
        inner_window = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.bind("<Configure>", lambda event: self._resize_editor_canvas(canvas, inner_window, event.width))
        self._bind_mousewheel(canvas)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        return inner

    def _resize_editor_canvas(self, canvas: tk.Canvas, inner_window: int, width: int) -> None:
        canvas.itemconfigure(inner_window, width=width)
        if self.preset_summary_label is not None:
            self.preset_summary_label.configure(wraplength=max(width - 24, 200))

    def _build_editable_field(self, parent: ttk.Frame, grid_row: int, field: FieldSpec) -> None:
        ttk.Label(parent, text=field.label, style="Panel.TLabel").grid(row=grid_row, column=0, sticky=tk.NW, pady=(7, 2), padx=(0, 12))
        if field.multiline:
            text = tk.Text(parent, height=4, width=44, wrap=tk.WORD, undo=True, relief=tk.FLAT, borderwidth=0, highlightthickness=1)
            text.grid(row=grid_row, column=1, sticky=tk.EW, pady=(4, 2))
            self.text_widgets[field.key] = text
        else:
            var = tk.StringVar()
            var.trace_add("write", lambda *_args, key=field.key: self._clear_preset_marker_on_user_edit(key))
            entry = ttk.Entry(parent, textvariable=var, width=48, style="Editable.TEntry")
            entry.grid(row=grid_row, column=1, sticky=tk.EW, pady=(4, 2))
            self.entry_vars[field.key] = var
            self.editable_entry_widgets[field.key] = entry
        if field.help_text:
            ttk.Label(parent, text=field.help_text, style="PanelHint.TLabel").grid(row=grid_row + 1, column=1, sticky=tk.W, pady=(0, 4))

    def _build_fact_fields(self, parent: ttk.Frame, fields: list[FieldSpec]) -> None:
        row = 0
        col = 0
        for field in fields:
            is_wide = field.key in {"file_name", "lens_model"}
            if is_wide and col != 0:
                row += 2
                col = 0

            columnspan = 2 if is_wide else 1
            padx = (0, 12) if col == 0 else (12, 0)
            ttk.Label(parent, text=field.label, style="FactLabel.TLabel").grid(
                row=row,
                column=col,
                columnspan=columnspan,
                sticky=tk.W,
                padx=padx,
                pady=(8, 2),
            )
            var = tk.StringVar()
            entry = ttk.Entry(parent, textvariable=var, state="readonly", width=24, style="Fact.TEntry")
            entry.grid(
                row=row + 1,
                column=col,
                columnspan=columnspan,
                sticky=tk.EW,
                padx=padx,
                pady=(0, 6),
            )
            self.entry_vars[field.key] = var

            if is_wide:
                row += 2
                col = 0
            elif col == 0:
                col = 1
            else:
                row += 2
                col = 0

        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)

    def _build_metadata_table(self, parent: ttk.Frame) -> None:
        filter_bar = ttk.Frame(parent, style="PanelBody.TFrame")
        filter_bar.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(filter_bar, text="筛选", style="Panel.TLabel").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Entry(filter_bar, textvariable=self.filter_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.filter_var.trace_add("write", lambda *_: self.populate_metadata_table())

        table_frame = ttk.Frame(parent, style="PanelBody.TFrame")
        table_frame.pack(fill=tk.BOTH, expand=True)
        columns = ("tag", "value")
        self.metadata_tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        self.metadata_tree.heading("tag", text="标签")
        self.metadata_tree.heading("value", text="值")
        self.metadata_tree.column("tag", width=240, anchor=tk.W, stretch=False)
        self.metadata_tree.column("value", width=420, anchor=tk.W, stretch=True)
        y_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.metadata_tree.yview)
        x_scroll = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.metadata_tree.xview)
        self.metadata_tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        self.metadata_tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

    def register_drag_drop(self) -> None:
        if not self.drag_drop_enabled:
            return
        for widget in [self.root, *self.drop_widgets]:
            try:
                widget.drop_target_register(DND_FILES)
                widget.dnd_bind("<<Drop>>", self.handle_drop)
            except Exception:
                continue

    def _bind_shortcuts(self) -> None:
        self.root.bind("<Control-o>", lambda _event: self.choose_file() if not self.is_busy else None)
        self.root.bind("<Control-O>", lambda _event: self.choose_file() if not self.is_busy else None)
        self.root.bind("<F5>", lambda _event: self.reload_file() if self.current_file and not self.is_busy else None)
        self.root.bind("<Control-s>", lambda _event: self.save_changes() if self.current_file and not self.is_busy else None)
        self.root.bind("<Control-S>", lambda _event: self.save_changes() if self.current_file and not self.is_busy else None)

    def _bind_mousewheel(self, canvas: tk.Canvas) -> None:
        def on_mousewheel(event: tk.Event) -> None:
            delta = getattr(event, "delta", 0)
            if delta:
                canvas.yview_scroll(int(-1 * (delta / 120)), "units")

        canvas.bind("<Enter>", lambda _event: canvas.bind_all("<MouseWheel>", on_mousewheel))
        canvas.bind("<Leave>", lambda _event: canvas.unbind_all("<MouseWheel>"))

    def handle_drop(self, event: tk.Event) -> None:
        if self.is_busy or self.is_closing:
            return
        try:
            paths = self.root.tk.splitlist(getattr(event, "data", ""))
        except tk.TclError:
            self.set_status("拖拽数据无法解析，请使用“选择”导入。")
            return
        if not paths:
            return
        self.load_file(Path(paths[0]), unsaved_action="导入新文件")

    def choose_file(self) -> None:
        if self.is_busy or self.is_closing:
            return
        selected = filedialog.askopenfilename(
            title=self.tr("选择图片或媒体文件"),
            filetypes=tuple((self.tr(label), pattern) for label, pattern in FILE_TYPES),
        )
        if selected:
            self.load_file(Path(selected), unsaved_action="导入新文件")

    def reload_file(self) -> None:
        if self.current_file and not self.is_busy and not self.is_closing:
            self.load_file(self.current_file, unsaved_action="重新读取当前文件")

    def load_file(self, file_path: Path, unsaved_action: str = "导入新文件", confirm_unsaved: bool = True) -> None:
        if self.is_busy or self.is_closing:
            return
        if confirm_unsaved and not self.confirm_unsaved_changes(unsaved_action):
            return
        task_id = self.begin_task(f"正在读取：{file_path.name}", kind="read")

        def task() -> tuple[dict[str, object], dict[str, str]]:
            metadata = self.client.read_metadata(file_path)
            return metadata, extract_field_values(metadata)

        def done(result: tuple[dict[str, object], dict[str, str]]) -> None:
            if not self.is_current_task(task_id):
                return
            metadata, values = result
            self.current_file = file_path
            self.current_metadata = metadata
            self.initial_values = values
            self.path_var.set(str(file_path))
            self.set_editor_values(values)
            self.update_editor_enabled_state()
            applied_presets = self.apply_selected_presets(update_status=False, allow_while_busy=True)
            self.populate_metadata_table()
            self.sync_file_time_var.set(False)
            self.reload_button.configure(state=tk.NORMAL)
            self.save_button.configure(state=tk.NORMAL)
            self.update_restore_button()
            preset_text = f"，并套用{'、'.join(applied_presets)}预设" if applied_presets else ""
            self.set_busy(False, f"已预填 {sum(1 for value in values.values() if value)} 个字段{preset_text}，读取 {len(metadata)} 个元数据标签")

        self.run_background(task, done, task_id=task_id)

    def set_editor_values(self, values: dict[str, str]) -> None:
        self._clear_preset_markers()
        for key, var in self.entry_vars.items():
            var.set(values.get(key, ""))
        for key, text in self.text_widgets.items():
            self.replace_text_value(text, values.get(key, ""))
        self.update_preset_summary()

    def set_field_value(self, key: str, value: str, from_preset: bool = False) -> None:
        if key in self.entry_vars:
            if from_preset:
                self._preset_write_keys.add(key)
            try:
                self.entry_vars[key].set(value)
            finally:
                self._preset_write_keys.discard(key)
            if from_preset:
                self._mark_preset_fields(key)
        elif key in self.text_widgets:
            self.replace_text_value(self.text_widgets[key], value)

    def _mark_preset_fields(self, *keys: str) -> None:
        for key in keys:
            widget = self.editable_entry_widgets.get(key)
            if widget is None:
                continue
            self.preset_field_keys.add(key)
            widget.configure(style="Preset.TEntry")

    def _clear_preset_marker_on_user_edit(self, key: str) -> None:
        if key in self._preset_write_keys or key not in self.preset_field_keys:
            return
        self.preset_field_keys.remove(key)
        widget = self.editable_entry_widgets.get(key)
        if widget is not None:
            widget.configure(style="Editable.TEntry")
        if key in {"make", "model", "software"} and self.camera_preset_var.get():
            self._clear_preset_markers_for({"make", "model", "software"})
            self.camera_preset_var.set("")
            self.set_status("已取消相机预设，保留手动修改")
        elif key in {"gps_latitude", "gps_longitude", "location_name"} and self.location_preset_var.get():
            self._clear_preset_markers_for({"gps_latitude", "gps_longitude", "location_name"})
            self.location_preset_var.set("")
            self.set_status("已取消GPS预设，保留手动修改")
        self.update_preset_summary()

    def _clear_preset_markers_for(self, keys: set[str]) -> None:
        for preset_key in self.preset_field_keys.intersection(keys):
            widget = self.editable_entry_widgets.get(preset_key)
            if widget is not None:
                widget.configure(style="Editable.TEntry")
        self.preset_field_keys.difference_update(keys)

    def _clear_preset_markers(self) -> None:
        self._clear_preset_markers_for(set(self.preset_field_keys))

    def update_preset_summary(self) -> None:
        lines: list[str] = []
        camera_name = self.camera_preset_var.get()
        if find_camera_preset(camera_name):
            if self.language == "en":
                lines.append(
                    f"Camera preset: {camera_name}\n"
                    f"Make: {self.get_field_value('make') or 'Not set'}  "
                    f"Model: {self.get_field_value('model') or 'Not set'}  "
                    f"Software: {self.get_field_value('software') or 'Not set'}"
                )
            else:
                lines.append(
                    "相机预设："
                    f"{camera_name}\n"
                    f"厂商：{self.get_field_value('make') or '未设置'}  "
                    f"型号：{self.get_field_value('model') or '未设置'}  "
                    f"软件：{self.get_field_value('software') or '未设置'}"
                )

        location_name = self.location_preset_var.get()
        if find_location_preset(location_name):
            if self.language == "en":
                lines.append(
                    f"Location preset: {location_name}\n"
                    f"Latitude: {self.get_field_value('gps_latitude') or 'Not set'}  "
                    f"Longitude: {self.get_field_value('gps_longitude') or 'Not set'}  "
                    f"Location: {self.get_field_value('location_name') or 'Not set'}"
                )
            else:
                lines.append(
                    "地点预设："
                    f"{location_name}\n"
                    f"纬度：{self.get_field_value('gps_latitude') or '未设置'}  "
                    f"经度：{self.get_field_value('gps_longitude') or '未设置'}  "
                    f"地点：{self.get_field_value('location_name') or '未设置'}"
                )

        self.preset_summary_var.set("\n\n".join(lines))
        if self.preset_summary_label is None:
            return
        if lines:
            self.preset_summary_label.pack(fill=tk.X, anchor=tk.W)
        else:
            self.preset_summary_label.pack_forget()

    def reveal_editable_fields(self, *keys: str) -> None:
        if not self.editor_canvas or not self.editor_inner:
            return
        widgets = [self.editable_entry_widgets[key] for key in keys if key in self.editable_entry_widgets]
        if not widgets:
            return
        self.root.update_idletasks()
        content_height = max(self.editor_inner.winfo_height(), 1)
        visible_height = max(self.editor_canvas.winfo_height(), 1)
        scrollable_height = content_height - visible_height
        if scrollable_height <= 0:
            return
        target_y = max(min(widget.winfo_y() for widget in widgets) - 36, 0)
        self.editor_canvas.yview_moveto(min(target_y / content_height, 1.0))

    def replace_text_value(self, text: tk.Text, value: str) -> None:
        previous_state = str(text.cget("state"))
        if previous_state == tk.DISABLED:
            text.configure(state=tk.NORMAL)
        text.delete("1.0", tk.END)
        text.insert("1.0", value)
        if previous_state == tk.DISABLED:
            text.configure(state=tk.DISABLED)

    def get_field_value(self, key: str) -> str:
        if key in self.entry_vars:
            return self.entry_vars[key].get().strip()
        if key in self.text_widgets:
            return self.text_widgets[key].get("1.0", tk.END).strip()
        return ""

    def get_editor_values(self) -> dict[str, str]:
        values = {key: var.get().strip() for key, var in self.entry_vars.items()}
        for key, text in self.text_widgets.items():
            values[key] = text.get("1.0", tk.END).strip()
        return values

    def changed_values(self) -> dict[str, str]:
        current = self.get_editor_values()
        readonly_keys = {field.key for field in EDITABLE_FIELDS if field.readonly}
        changed = {key: value for key, value in current.items() if key not in readonly_keys and value != self.initial_values.get(key, "")}
        if "gps_latitude" in changed or "gps_longitude" in changed:
            changed["gps_latitude"] = current.get("gps_latitude", "")
            changed["gps_longitude"] = current.get("gps_longitude", "")
        return changed

    def has_unsaved_changes(self) -> bool:
        return bool(self.current_file and (self.changed_values() or self.sync_file_time_var.get()))

    def confirm_unsaved_changes(self, action: str) -> bool:
        if not self.has_unsaved_changes():
            return True
        response = self.ask_yes_no_cancel(
            "未保存修改",
            f"当前文件有未保存修改。\n\n选择“是”先保存，选择“否”放弃修改并{action}，选择“取消”继续编辑。",
            icon=messagebox.WARNING,
            default=messagebox.CANCEL,
        )
        if response is None:
            return False
        if response:
            self.save_changes()
            return False
        return True

    def apply_selected_presets(
        self,
        update_status: bool = True,
        allow_while_busy: bool = False,
        reveal: bool = False,
    ) -> list[str]:
        applied: list[str] = []
        if self.camera_preset_var.get() and self.apply_camera_preset(
            show_message=False,
            update_status=False,
            allow_while_busy=allow_while_busy,
            reveal=reveal,
        ):
            applied.append("相机")
        if self.location_preset_var.get() and self.apply_location_preset(
            show_message=False,
            update_status=False,
            allow_while_busy=allow_while_busy,
            reveal=reveal,
        ):
            applied.append("GPS")
        if applied and update_status:
            self.set_status(f"已套用{'、'.join(applied)}预设")
        return applied

    def apply_camera_preset(
        self,
        show_message: bool = True,
        update_status: bool = True,
        allow_while_busy: bool = False,
        reveal: bool = True,
    ) -> bool:
        if self.is_closing or (self.is_busy and not allow_while_busy):
            return False
        preset = find_camera_preset(self.camera_preset_var.get())
        if not preset:
            if show_message:
                self.show_info("未选择相机", "请先选择一个相机预设。")
            return False
        preset_keys = ("make", "model", "software")
        self.set_field_value("make", preset.make, from_preset=True)
        self.set_field_value("model", preset.model, from_preset=True)
        self.set_field_value("software", preset.software, from_preset=True)
        self.update_preset_summary()
        if reveal:
            self.reveal_editable_fields(*preset_keys)
        if update_status:
            self.set_status(f"已套用相机：{preset.name}")
        return True

    def apply_location_preset(
        self,
        show_message: bool = True,
        update_status: bool = True,
        allow_while_busy: bool = False,
        reveal: bool = True,
    ) -> bool:
        if self.is_closing or (self.is_busy and not allow_while_busy):
            return False
        preset = find_location_preset(self.location_preset_var.get())
        if not preset:
            if show_message:
                self.show_info("未选择地点", "请先选择一个地点预设。")
            return False
        preset_keys = ("gps_latitude", "gps_longitude", "location_name")
        self.set_field_value("gps_latitude", f"{preset.latitude:.8f}".rstrip("0").rstrip("."), from_preset=True)
        self.set_field_value("gps_longitude", f"{preset.longitude:.8f}".rstrip("0").rstrip("."), from_preset=True)
        self.set_field_value("location_name", preset.name, from_preset=True)
        self.update_preset_summary()
        if reveal:
            self.reveal_editable_fields(*preset_keys)
        if update_status:
            self.set_status(f"已套用GPS：{preset.name}")
        return True

    def run_ocr_datetime(self) -> None:
        if self.is_busy or self.is_closing:
            return
        if not self.current_file:
            self.show_info("未导入文件", "请先导入一张图片。")
            return

        file_path = self.current_file
        task_id = self.begin_task("正在OCR识别图片时间", kind="ocr")

        def task() -> OcrDateResult:
            return extract_datetime_from_image(file_path)

        def done(result: OcrDateResult) -> None:
            if not self.is_current_task(task_id):
                return
            self.set_field_value("date_taken", result.datetime_value)
            self.sync_file_time_var.set(True)
            self.set_busy(False, f"{result.engine} 识别到时间：{result.datetime_value}")
            self.show_info("OCR识别完成", f"{result.engine} 识别到时间：{result.datetime_value}")

        self.run_background(task, done, ocr_errors=True, task_id=task_id)

    def has_original_backup(self) -> bool:
        return bool(self.current_file and original_backup_path(self.current_file).is_file())

    def update_restore_button(self) -> None:
        self.restore_button.configure(state=tk.NORMAL if self.has_original_backup() and not self.is_busy else tk.DISABLED)

    def restore_original_backup(self) -> None:
        if self.is_busy or self.is_closing or not self.current_file:
            return
        file_path = self.current_file
        if not self.has_original_backup():
            self.show_info("没有备份", "当前文件没有可恢复的 _original 备份。")
            self.update_restore_button()
            return
        confirmed = self.ask_yes_no(
            "恢复原始备份",
            "将恢复 ExifTool 创建的 _original 备份。\n\n当前文件会先保存为 _before_restore 备份，然后被原始版本替换。",
            icon=messagebox.WARNING,
            default=messagebox.NO,
        )
        if not confirmed:
            return

        task_id = self.begin_task("正在恢复原始备份", kind="restore")

        def task() -> str:
            result = self.client.restore_original_backup(file_path)
            return f"已恢复原始备份；恢复前版本已保存为：{result.current_backup.name}"

        def done(message: str) -> None:
            if not self.is_current_task(task_id):
                return
            self.set_busy(False, message)
            self.show_info("恢复完成", message)
            self.load_file(file_path, confirm_unsaved=False)

        self.run_background(task, done, task_id=task_id)

    def save_changes(self) -> None:
        if self.is_busy or self.is_closing:
            return
        if not self.current_file:
            return

        changes = self.changed_values()
        sync_file_time = self.sync_file_time_var.get()
        file_time_value = self.get_field_value("date_taken")
        if sync_file_time and not file_time_value:
            self.show_error("同步文件时间需要先填写拍摄时间。", "缺少时间")
            return
        if not changes and not sync_file_time:
            self.show_info("没有变化", "当前没有需要保存的字段。")
            return

        task_id = self.begin_task("正在写入元数据", kind="write")
        preserve_backup = self.preserve_backup_var.get()
        file_path = self.current_file

        def task() -> str:
            result = self.client.write_metadata(
                file_path,
                changes,
                preserve_backup=preserve_backup,
                sync_file_time=sync_file_time,
                file_time_value=file_time_value,
            )
            return result.stdout or "元数据已写入。"

        def done(message: str) -> None:
            if not self.is_current_task(task_id):
                return
            self.set_busy(False, message)
            self.show_info("保存完成", message)
            self.load_file(file_path, confirm_unsaved=False)

        self.run_background(task, done, task_id=task_id)

    def populate_metadata_table(self) -> None:
        for item_id in self.metadata_tree.get_children():
            self.metadata_tree.delete(item_id)
        for index, (tag, value) in enumerate(metadata_rows(self.current_metadata, self.filter_var.get())):
            self.metadata_tree.insert("", tk.END, values=(tag, value), tags=("even" if index % 2 == 0 else "odd",))

    def show_about(self) -> None:
        if self.is_busy or self.is_closing:
            return
        about = tk.Toplevel(self.root)
        about.title(self.tr(f"关于 {APP_NAME}"))
        about.transient(self.root)
        about.resizable(False, False)
        about.configure(background=self.palette()["panel"])

        frame = ttk.Frame(about, style="PanelBody.TFrame", padding=18)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text=APP_NAME, style="Panel.TLabel", font=("Microsoft YaHei UI", 13, "bold")).grid(
            row=0,
            column=0,
            sticky=tk.W,
            pady=(0, 8),
        )
        for row, text in enumerate(
            (
                self.tr(f"版本：{APP_VERSION}"),
                self.tr(f"创作者：{APP_CREATOR}"),
                APP_DESCRIPTION,
                APP_COPYRIGHT,
            ),
            start=1,
        ):
            ttk.Label(frame, text=text, style="Panel.TLabel", wraplength=420).grid(row=row, column=0, sticky=tk.W, pady=2)

        self._build_about_link(frame, 5, self.tr(f"邮箱：{APP_EMAIL}"), f"mailto:{APP_EMAIL}")
        self._build_about_link(frame, 6, self.tr(f"网站：{APP_WEBSITE}"), APP_WEBSITE)
        ttk.Button(frame, text=self.tr("关闭"), command=about.destroy).grid(row=7, column=0, sticky=tk.E, pady=(14, 0))
        about.update_idletasks()
        x = self.root.winfo_rootx() + max((self.root.winfo_width() - about.winfo_width()) // 2, 0)
        y = self.root.winfo_rooty() + max((self.root.winfo_height() - about.winfo_height()) // 2, 0)
        about.geometry(f"+{x}+{y}")
        about.grab_set()

    def _build_about_link(self, parent: ttk.Frame, row: int, text: str, target: str) -> None:
        label = ttk.Label(parent, text=text, style="PanelHint.TLabel", cursor="hand2")
        label.grid(row=row, column=0, sticky=tk.W, pady=2)
        label.bind("<Button-1>", lambda _event: webbrowser.open(target))

    def set_busy(self, busy: bool, status: str) -> None:
        if self.is_closing:
            return
        self.is_busy = busy
        self.set_status(status)
        if busy:
            for widget in self.busy_sensitive_widgets:
                widget.configure(state=tk.DISABLED)
            for widget in self.busy_readonly_widgets:
                widget.configure(state=tk.DISABLED)
            for entry in self.editable_entry_widgets.values():
                entry.configure(state=tk.DISABLED)
            for text in self.text_widgets.values():
                text.configure(state=tk.DISABLED)
            return
        self.choose_button.configure(state=tk.NORMAL)
        self.camera_apply_button.configure(state=tk.NORMAL)
        self.location_apply_button.configure(state=tk.NORMAL)
        self.ocr_button.configure(state=tk.NORMAL)
        self.about_button.configure(state=tk.NORMAL)
        for widget in self.option_widgets:
            widget.configure(state=tk.NORMAL)
        for widget in self.busy_readonly_widgets:
            widget.configure(state="readonly")
        self.update_editor_enabled_state()
        if self.current_file:
            self.reload_button.configure(state=tk.NORMAL)
            self.save_button.configure(state=tk.NORMAL)
        else:
            self.reload_button.configure(state=tk.DISABLED)
            self.save_button.configure(state=tk.DISABLED)
        self.update_restore_button()
        self.current_task_kind = None

    def update_editor_enabled_state(self) -> None:
        enabled = bool(self.current_file) and not self.is_busy and not self.is_closing
        state = tk.NORMAL if enabled else tk.DISABLED
        for entry in self.editable_entry_widgets.values():
            entry.configure(state=state)
        for text in self.text_widgets.values():
            text.configure(state=state)

    def begin_task(self, status: str, kind: str = "generic") -> int:
        self.active_task_id += 1
        self.current_task_kind = kind
        self.set_busy(True, status)
        return self.active_task_id

    def is_current_task(self, task_id: int) -> bool:
        return not self.is_closing and task_id == self.active_task_id

    def call_on_ui_thread(self, callback: Callable[[], None]) -> None:
        if self.is_closing:
            return
        self.ui_callback_queue.put(callback)

    def _schedule_ui_callback_drain(self) -> None:
        if self.is_closing:
            return
        try:
            self.ui_callback_after_id = self.root.after(25, self._drain_ui_callbacks)
        except tk.TclError:
            self.is_closing = True

    def _drain_ui_callbacks(self) -> None:
        self.ui_callback_after_id = None
        if self.is_closing:
            return
        while True:
            try:
                callback = self.ui_callback_queue.get_nowait()
            except queue.Empty:
                break
            try:
                callback()
            except Exception as exc:  # noqa: BLE001 - keep a queued UI callback from stopping the event loop.
                self.show_error(f"界面更新失败：{exc}")
        self._schedule_ui_callback_drain()

    def run_background(
        self,
        task: Callable[[], T],
        done: Callable[[T], None],
        ocr_errors: bool = False,
        task_id: int | None = None,
    ) -> None:
        def deliver_error(message: str, title: str = "操作失败") -> None:
            if task_id is not None and not self.is_current_task(task_id):
                return
            self.show_error(message, title)

        def deliver_result(result: T) -> None:
            if task_id is not None and not self.is_current_task(task_id):
                return
            try:
                done(result)
            except Exception as exc:  # noqa: BLE001 - keep GUI callbacks from leaving the app busy.
                self.show_error(f"界面更新失败：{exc}")

        def worker() -> None:
            try:
                result = task()
            except OcrError as exc:
                message = str(exc)
                self.call_on_ui_thread(lambda: deliver_error(message, "OCR失败"))
            except ExifToolError as exc:
                message = str(exc)
                self.call_on_ui_thread(lambda: deliver_error(message))
            except Exception as exc:  # noqa: BLE001 - GUI boundary should display unexpected failures.
                message = f"发生未知错误：{exc}"
                if ocr_errors:
                    message = f"OCR失败：{exc}"
                self.call_on_ui_thread(lambda: deliver_error(message))
            except BaseException as exc:  # A worker-only SystemExit must not leave the GUI permanently busy.
                message = f"后台任务异常终止：{exc}"
                if ocr_errors:
                    message = f"OCR失败：{exc}"
                self.call_on_ui_thread(lambda: deliver_error(message))
            else:
                self.call_on_ui_thread(lambda: deliver_result(result))

        try:
            thread = threading.Thread(target=worker, daemon=True)
            thread.start()
        except Exception as exc:  # noqa: BLE001 - startup failure still needs a UI recovery path.
            deliver_error(f"无法启动后台任务：{exc}")

    def show_error(self, message: str, title: str = "操作失败") -> None:
        if self.is_closing:
            return
        self.set_busy(False, title)
        messagebox.showerror(self.tr(title), self.tr(message), parent=self.root)

    def close(self) -> None:
        if self.is_busy:
            labels = {
                "write": ("写入元数据", "writing metadata"),
                "read": ("读取元数据", "reading metadata"),
                "ocr": ("OCR识别", "running OCR"),
                "restore": ("恢复原始备份", "restoring the original backup"),
            }
            task_pair = labels.get(self.current_task_kind or "", ("处理文件", "processing a file"))
            task_label = task_pair[1] if self.language == "en" else task_pair[0]
            self.show_warning("正在处理", f"正在{task_label}，请等待完成后再关闭。")
            return
        if not self.confirm_unsaved_changes("关闭窗口"):
            return
        self.is_closing = True
        self.active_task_id += 1
        if self.ui_callback_after_id is not None:
            try:
                self.root.after_cancel(self.ui_callback_after_id)
            except tk.TclError:
                pass
            self.ui_callback_after_id = None
        try:
            self.root.update_idletasks()
            self.root.destroy()
        except tk.TclError:
            pass


def create_root() -> tk.Tk:
    if TkinterDnD:
        try:
            root = TkinterDnD.Tk()
        except tk.TclError:
            # tkinterdnd2 can import successfully while its bundled tkdnd runtime is
            # unavailable. Metadata editing must remain usable in that situation.
            root = tk.Tk()
            root._photo_meta_editor_dnd_enabled = False  # type: ignore[attr-defined]
            return root
        root._photo_meta_editor_dnd_enabled = True  # type: ignore[attr-defined]
        return root
    root = tk.Tk()
    root._photo_meta_editor_dnd_enabled = False  # type: ignore[attr-defined]
    return root


def main() -> None:
    root = create_root()
    try:
        MetadataEditorApp(root)
    except ExifToolError as exc:
        language = load_language()
        messagebox.showerror(translate_text("启动失败", language), translate_text(str(exc), language), parent=root)
        root.destroy()
        return
    root.mainloop()
