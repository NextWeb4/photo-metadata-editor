import unittest
from unittest.mock import Mock, patch
import tkinter as tk
import time
import tempfile
from pathlib import Path

from photo_meta_editor.app import MetadataEditorApp, create_root


class AppTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = create_root()
        self.root.withdraw()
        self.app = MetadataEditorApp(self.root)

    def tearDown(self) -> None:
        try:
            if self.root.winfo_exists():
                self.root.update()
            if self.root.winfo_exists() and not self.app.is_closing:
                self.app.set_busy(False, "测试清理")
                self.app.close()
        except Exception:
            pass

    def test_camera_preset_clears_stale_software_value(self) -> None:
        self.app.set_field_value("software", "iOS")
        self.app.camera_preset_var.set("Fujifilm X-T5")

        self.app.apply_camera_preset(show_message=False)

        self.assertEqual(self.app.get_field_value("make"), "FUJIFILM")
        self.assertEqual(self.app.get_field_value("model"), "X-T5")
        self.assertEqual(self.app.get_field_value("software"), "")

    def test_startup_does_not_run_exiftool_process_for_version_display(self) -> None:
        self.app.close()
        root = create_root()
        root.withdraw()
        app: MetadataEditorApp | None = None
        try:
            with patch("photo_meta_editor.app.ExifToolClient.version", side_effect=AssertionError("must not run at startup")):
                app = MetadataEditorApp(root)

            self.assertIn("ExifTool 已就绪", app.status_var.get())
        finally:
            if app is not None:
                app.close()
            elif root.winfo_exists():
                root.destroy()

    def test_language_selector_updates_visible_ui_and_persists_selection(self) -> None:
        with patch("photo_meta_editor.app.save_language") as save:
            self.app.language_var.set("English")
            self.app.language_combo.event_generate("<<ComboboxSelected>>")
            self.root.update()

        self.assertEqual(self.app.language, "en")
        self.assertEqual(str(self.app.choose_button.cget("text")), "Open")
        self.assertEqual(str(self.app.save_button.cget("text")), "Save changes")
        self.assertEqual(self.app.metadata_tree.heading("tag", "text"), "Tag")
        self.assertIn("ExifTool ready", self.app.status_var.get())
        save.assert_called_once_with("en")

        with patch("photo_meta_editor.app.save_language"):
            self.app.language_var.set("中文")
            self.app.language_combo.event_generate("<<ComboboxSelected>>")
            self.root.update()
        self.assertEqual(str(self.app.choose_button.cget("text")), "选择")

    def test_camera_combo_selection_prefills_editable_fields(self) -> None:
        self.app.camera_preset_var.set("Ricoh GR IIIx")

        self.app.camera_combo.event_generate("<<ComboboxSelected>>")
        self.root.update()

        self.assertEqual(self.app.get_field_value("make"), "RICOH IMAGING COMPANY, LTD.")
        self.assertEqual(self.app.get_field_value("model"), "RICOH GR IIIx")
        self.assertIn("make", self.app.preset_field_keys)
        self.assertEqual(str(self.app.editable_entry_widgets["make"].cget("style")), "Preset.TEntry")
        self.assertIn("相机预设：Ricoh GR IIIx", self.app.preset_summary_var.get())
        self.assertIn("厂商：RICOH IMAGING COMPANY, LTD.", self.app.preset_summary_var.get())
        self.assertIn("型号：RICOH GR IIIx", self.app.preset_summary_var.get())
        self.assertEqual(str(self.app.preset_summary_label.winfo_manager()), "pack")

    def test_location_combo_selection_prefills_editable_fields(self) -> None:
        self.app.location_preset_var.set("北京 天安门")

        self.app.location_combo.event_generate("<<ComboboxSelected>>")
        self.root.update()

        self.assertEqual(self.app.get_field_value("gps_latitude"), "39.908722")
        self.assertEqual(self.app.get_field_value("gps_longitude"), "116.397499")
        self.assertEqual(self.app.get_field_value("location_name"), "北京 天安门")
        self.assertIn("gps_latitude", self.app.preset_field_keys)
        self.assertEqual(str(self.app.editable_entry_widgets["gps_latitude"].cget("style")), "Preset.TEntry")
        self.assertIn("地点预设：北京 天安门", self.app.preset_summary_var.get())
        self.assertIn("纬度：39.908722", self.app.preset_summary_var.get())
        self.assertIn("经度：116.397499", self.app.preset_summary_var.get())

    def test_preset_stringvars_apply_without_waiting_for_button(self) -> None:
        self.app.camera_preset_var.set("Fujifilm X-T5")
        self.app.location_preset_var.set("纽约 Times Square")

        self.assertEqual(self.app.get_field_value("make"), "FUJIFILM")
        self.assertEqual(self.app.get_field_value("model"), "X-T5")
        self.assertEqual(self.app.get_field_value("software"), "")
        self.assertEqual(self.app.get_field_value("gps_latitude"), "40.758896")
        self.assertEqual(self.app.get_field_value("gps_longitude"), "-73.98513")
        self.assertEqual(self.app.get_field_value("location_name"), "纽约 Times Square")

    def test_selected_presets_are_reapplied_after_metadata_prefill(self) -> None:
        self.app.camera_preset_var.set("Ricoh GR IIIx")
        self.app.location_preset_var.set("北京 天安门")

        self.app.set_editor_values(
            {
                "make": "",
                "model": "",
                "software": "",
                "gps_latitude": "",
                "gps_longitude": "",
                "location_name": "",
            }
        )
        applied = self.app.apply_selected_presets(update_status=False)

        self.assertEqual(applied, ["相机", "GPS"])
        self.assertEqual(self.app.get_field_value("make"), "RICOH IMAGING COMPANY, LTD.")
        self.assertEqual(self.app.get_field_value("model"), "RICOH GR IIIx")
        self.assertEqual(self.app.get_field_value("gps_latitude"), "39.908722")
        self.assertEqual(self.app.get_field_value("gps_longitude"), "116.397499")
        self.assertEqual(
            self.app.preset_field_keys,
            {"make", "model", "software", "gps_latitude", "gps_longitude", "location_name"},
        )

    def test_manually_editing_a_preset_field_removes_its_preset_marker(self) -> None:
        self.app.camera_preset_var.set("Ricoh GR IIIx")

        self.app.set_field_value("model", "手动相机型号")

        self.assertNotIn("model", self.app.preset_field_keys)
        self.assertEqual(str(self.app.editable_entry_widgets["model"].cget("style")), "Editable.TEntry")
        self.assertNotIn("make", self.app.preset_field_keys)
        self.assertEqual(str(self.app.editable_entry_widgets["make"].cget("style")), "Editable.TEntry")
        self.assertEqual(self.app.camera_preset_var.get(), "")
        self.assertNotIn("相机预设：", self.app.preset_summary_var.get())
        self.assertEqual(str(self.app.preset_summary_label.winfo_manager()), "")

    def test_manually_editing_a_location_preset_field_clears_its_selection(self) -> None:
        self.app.location_preset_var.set("北京 天安门")

        self.app.set_field_value("gps_latitude", "40.0")

        self.assertNotIn("gps_latitude", self.app.preset_field_keys)
        self.assertNotIn("gps_longitude", self.app.preset_field_keys)
        self.assertEqual(self.app.location_preset_var.get(), "")
        self.assertEqual(self.app.get_field_value("gps_longitude"), "116.397499")
        self.assertNotIn("地点预设：", self.app.preset_summary_var.get())

    def test_reveal_editable_fields_uses_content_height_for_scroll_fraction(self) -> None:
        canvas = Mock()
        inner = Mock()
        entry = Mock()
        canvas.winfo_height.return_value = 400
        inner.winfo_height.return_value = 1000
        entry.winfo_y.return_value = 700
        self.app.editor_canvas = canvas
        self.app.editor_inner = inner
        self.app.editable_entry_widgets["gps_latitude"] = entry

        self.app.reveal_editable_fields("gps_latitude")

        canvas.yview_moveto.assert_called_once_with(0.664)

    def test_preset_summary_wraps_inside_the_editor_width(self) -> None:
        canvas = Mock()
        self.app._resize_editor_canvas(canvas, 7, 320)

        canvas.itemconfigure.assert_called_once_with(7, width=320)
        self.assertEqual(str(self.app.preset_summary_label.cget("wraplength")), "296")

    def test_selected_presets_can_reapply_during_readback_completion(self) -> None:
        self.app.camera_preset_var.set("Ricoh GR IIIx")
        self.app.location_preset_var.set("北京 天安门")
        self.app.set_busy(True, "正在读取")
        self.app.set_editor_values({"make": "", "model": "", "gps_latitude": "", "gps_longitude": ""})

        applied = self.app.apply_selected_presets(update_status=False, allow_while_busy=True)

        self.assertEqual(applied, ["相机", "GPS"])
        self.assertEqual(self.app.get_field_value("make"), "RICOH IMAGING COMPANY, LTD.")
        self.assertEqual(self.app.get_field_value("gps_longitude"), "116.397499")
        self.app.set_busy(False, "就绪")

    def test_changed_values_keeps_gps_pair_when_one_coordinate_changes(self) -> None:
        self.app.initial_values = {"gps_latitude": "39.908722", "gps_longitude": "116.397499"}
        self.app.set_field_value("gps_latitude", "40.0")
        self.app.set_field_value("gps_longitude", "116.397499")

        changes = self.app.changed_values()

        self.assertEqual(changes["gps_latitude"], "40.0")
        self.assertEqual(changes["gps_longitude"], "116.397499")

    def test_photo_parameters_are_visible_in_editor_panel(self) -> None:
        self.assertFalse(hasattr(self.app, "editor_notebook"))

        self.app.set_editor_values({"file_type": "JPEG", "image_size": "1086x1448", "iso": "125"})

        self.assertEqual(self.app.get_field_value("file_type"), "JPEG")
        self.assertEqual(self.app.get_field_value("image_size"), "1086x1448")
        self.assertEqual(self.app.get_field_value("iso"), "125")

    def test_dark_theme_styles_inputs_without_white_fields(self) -> None:
        self.app.dark_mode_var.set(True)
        self.app.apply_theme()
        palette = self.app.palette()

        self.assertEqual(self.app.style.lookup("TEntry", "fieldbackground"), palette["entry"])
        self.assertEqual(self.app.style.lookup("Editable.TEntry", "fieldbackground"), palette["entry"])
        self.assertEqual(self.app.style.lookup("TEntry", "fieldbackground", ("readonly",)), palette["readonly"])
        self.assertEqual(self.app.style.lookup("Preset.TEntry", "fieldbackground"), palette["preset_entry"])
        self.assertEqual(self.app.style.lookup("Preset.TEntry", "bordercolor"), palette["preset_border"])
        self.assertEqual(self.app.style.lookup("Fact.TEntry", "fieldbackground", ("readonly",)), palette["readonly"])
        self.assertEqual(self.app.style.lookup("TCombobox", "fieldbackground", ("readonly",)), palette["entry"])
        self.assertEqual(self.app.style.lookup("Treeview", "background"), palette["entry"])
        self.assertEqual(str(self.root.cget("background")), palette["bg"])
        self.assertEqual(self.app.style.lookup("TCheckbutton", "background"), palette["panel"])
        self.assertEqual(str(self.app.text_widgets["description"].cget("background")), palette["entry"])
        self.assertEqual(str(self.app.editable_entry_widgets["title"].cget("style")), "Editable.TEntry")

    def test_busy_state_disables_and_restores_preset_combos(self) -> None:
        self.app.set_busy(True, "忙碌中")

        self.assertEqual(str(self.app.camera_combo.cget("state")), "disabled")
        self.assertEqual(str(self.app.location_combo.cget("state")), "disabled")

        self.app.set_busy(False, "就绪")

        self.assertEqual(str(self.app.camera_combo.cget("state")), "readonly")
        self.assertEqual(str(self.app.location_combo.cget("state")), "readonly")

    def test_busy_state_disables_editable_fields_and_save_options(self) -> None:
        self.app.current_file = Path("photo.jpg")
        self.app.set_busy(True, "忙碌中")

        self.assertEqual(str(self.app.editable_entry_widgets["title"].cget("state")), "disabled")
        self.assertEqual(str(self.app.text_widgets["description"].cget("state")), "disabled")
        self.assertEqual(str(self.app.preserve_backup_check.cget("state")), "disabled")
        self.assertEqual(str(self.app.sync_file_time_check.cget("state")), "disabled")

        self.app.set_busy(False, "就绪")

        self.assertEqual(str(self.app.editable_entry_widgets["title"].cget("state")), "normal")
        self.assertEqual(str(self.app.text_widgets["description"].cget("state")), "normal")
        self.assertEqual(str(self.app.preserve_backup_check.cget("state")), "normal")
        self.assertEqual(str(self.app.sync_file_time_check.cget("state")), "normal")

    def test_editor_fields_are_disabled_until_a_file_is_loaded(self) -> None:
        self.assertEqual(str(self.app.editable_entry_widgets["title"].cget("state")), "disabled")
        self.assertEqual(str(self.app.text_widgets["description"].cget("state")), "disabled")

        self.app.current_file = Path("photo.jpg")
        self.app.set_busy(False, "ready")

        self.assertEqual(str(self.app.editable_entry_widgets["title"].cget("state")), "normal")
        self.assertEqual(str(self.app.text_widgets["description"].cget("state")), "normal")

    def test_restore_button_reflects_original_backup_for_the_current_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            file_path = Path(tmp) / "photo.jpg"
            file_path.write_bytes(b"current")
            self.app.current_file = file_path
            self.app.update_restore_button()
            self.assertEqual(str(self.app.restore_button.cget("state")), "disabled")

            Path(f"{file_path}_original").write_bytes(b"original")
            self.app.update_restore_button()

        self.assertEqual(str(self.app.restore_button.cget("state")), "normal")

    def test_programmatic_text_updates_work_while_busy(self) -> None:
        self.app.set_busy(True, "忙碌中")

        self.app.set_field_value("description", "后台结果")

        self.assertEqual(self.app.get_field_value("description"), "后台结果")
        self.assertEqual(str(self.app.text_widgets["description"].cget("state")), "disabled")

    def test_about_window_is_ignored_while_busy(self) -> None:
        self.app.set_busy(True, "忙碌中")

        self.app.show_about()
        self.root.update()

        windows = [widget for widget in self.root.winfo_children() if widget.winfo_toplevel() is widget]
        about_windows = [window for window in windows if str(window.wm_title()).startswith("关于")]
        self.assertEqual(about_windows, [])

    def test_about_window_renders_creator_contact(self) -> None:
        self.app.show_about()
        self.root.update()

        windows = [widget for widget in self.root.winfo_children() if widget.winfo_toplevel() is widget]
        about_windows = [window for window in windows if str(window.wm_title()).startswith("关于")]

        self.assertEqual(len(about_windows), 1)
        self.assertIn("Photo Metadata Editor", about_windows[0].wm_title())
        about_windows[0].destroy()

    def test_drop_is_ignored_while_busy(self) -> None:
        self.app.set_busy(True, "忙碌中")
        self.app.load_file = Mock()  # type: ignore[method-assign]
        event = type("DropEvent", (), {"data": "C:/tmp/photo.jpg"})()

        self.app.handle_drop(event)

        self.app.load_file.assert_not_called()

    def test_malformed_drop_payload_is_ignored(self) -> None:
        self.app.load_file = Mock()  # type: ignore[method-assign]
        event = type("DropEvent", (), {"data": "{"})()

        self.app.handle_drop(event)

        self.app.load_file.assert_not_called()
        self.assertIn("拖拽数据无法解析", self.app.status_var.get())

    def test_app_starts_without_drag_drop_when_tkdnd_runtime_fails(self) -> None:
        self.app.close()

        with patch("photo_meta_editor.app.TkinterDnD") as tkinter_dnd:
            tkinter_dnd.Tk.side_effect = tk.TclError("can't find package tkdnd")
            root = create_root()
        fallback_app: MetadataEditorApp | None = None
        try:
            root.withdraw()
            fallback_app = MetadataEditorApp(root)

            self.assertFalse(fallback_app.drag_drop_enabled)
            self.assertIn("拖拽组件不可用", fallback_app.drop_label.cget("text"))
        finally:
            if fallback_app is not None:
                fallback_app.close()
            elif root.winfo_exists():
                root.destroy()

    def test_closing_window_makes_pending_task_stale(self) -> None:
        task_id = self.app.active_task_id

        self.app.close()

        self.assertTrue(self.app.is_closing)
        self.assertFalse(self.app.is_current_task(task_id))

    def test_close_is_blocked_while_writing_metadata(self) -> None:
        self.app.begin_task("写入中", kind="write")

        with patch("photo_meta_editor.app.messagebox.showwarning") as showwarning:
            self.app.close()

        showwarning.assert_called_once()
        self.assertFalse(self.app.is_closing)
        self.assertTrue(self.root.winfo_exists())
        self.app.set_busy(False, "就绪")

    def test_close_is_blocked_while_reading_metadata(self) -> None:
        self.app.begin_task("读取中", kind="read")

        with patch("photo_meta_editor.app.messagebox.showwarning") as showwarning:
            self.app.close()

        showwarning.assert_called_once()
        self.assertFalse(self.app.is_closing)
        self.assertTrue(self.root.winfo_exists())
        self.app.set_busy(False, "就绪")

    def test_close_is_blocked_while_running_ocr(self) -> None:
        self.app.begin_task("OCR中", kind="ocr")

        with patch("photo_meta_editor.app.messagebox.showwarning") as showwarning:
            self.app.close()

        showwarning.assert_called_once()
        self.assertFalse(self.app.is_closing)
        self.assertTrue(self.root.winfo_exists())
        self.app.set_busy(False, "就绪")

    def test_close_cancel_keeps_unsaved_edits(self) -> None:
        self.app.current_file = Path("photo.jpg")
        self.app.initial_values = {"title": ""}
        self.app.set_busy(False, "ready")
        self.app.set_field_value("title", "draft")

        with patch("photo_meta_editor.app.messagebox.askyesnocancel", return_value=None) as askyesnocancel:
            self.app.close()

        askyesnocancel.assert_called_once()
        self.assertFalse(self.app.is_closing)
        self.assertTrue(self.root.winfo_exists())
        self.assertEqual(self.app.get_field_value("title"), "draft")
        self.app.current_file = None

    def test_reload_cancel_keeps_unsaved_edits_without_starting_read(self) -> None:
        self.app.current_file = Path("photo.jpg")
        self.app.initial_values = {"title": ""}
        self.app.set_busy(False, "ready")
        self.app.set_field_value("title", "draft")
        self.app.begin_task = Mock(wraps=self.app.begin_task)  # type: ignore[method-assign]

        with patch("photo_meta_editor.app.messagebox.askyesnocancel", return_value=None):
            self.app.reload_file()

        self.app.begin_task.assert_not_called()
        self.assertEqual(self.app.get_field_value("title"), "draft")
        self.app.current_file = None

    def test_unsaved_prompt_save_starts_save_without_reloading(self) -> None:
        self.app.current_file = Path("photo.jpg")
        self.app.initial_values = {"title": ""}
        self.app.set_busy(False, "ready")
        self.app.set_field_value("title", "draft")
        self.app.save_changes = Mock()  # type: ignore[method-assign]
        self.app.begin_task = Mock(wraps=self.app.begin_task)  # type: ignore[method-assign]

        with patch("photo_meta_editor.app.messagebox.askyesnocancel", return_value=True):
            self.app.reload_file()

        self.app.save_changes.assert_called_once()
        self.app.begin_task.assert_not_called()
        self.app.current_file = None

    def test_background_base_exception_restores_busy_state(self) -> None:
        task_id = self.app.begin_task("读取中")

        def fail() -> None:
            raise SystemExit("backend exited")

        with patch("photo_meta_editor.app.messagebox.showerror") as showerror:
            self.app.run_background(fail, lambda _result: None, task_id=task_id)
            for _ in range(50):
                self.root.update()
                if not self.app.is_busy:
                    break
                time.sleep(0.01)

        self.assertFalse(self.app.is_busy)
        showerror.assert_called_once()

    def test_background_thread_start_failure_restores_busy_state(self) -> None:
        task_id = self.app.begin_task("reading")

        with patch("photo_meta_editor.app.threading.Thread.start", side_effect=RuntimeError("can't start new thread")):
            with patch("photo_meta_editor.app.messagebox.showerror") as showerror:
                self.app.run_background(lambda: None, lambda _result: None, task_id=task_id)

        self.assertFalse(self.app.is_busy)
        showerror.assert_called_once()


if __name__ == "__main__":
    unittest.main()
