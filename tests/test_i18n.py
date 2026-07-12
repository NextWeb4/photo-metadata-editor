import unittest

from photo_meta_editor.i18n import translate_text


class I18nTests(unittest.TestCase):
    def test_translates_static_and_dynamic_ui_text(self) -> None:
        self.assertEqual(translate_text("保存修改", "en"), "Save changes")
        self.assertEqual(translate_text("正在读取：照片.jpg", "en"), "Reading: 照片.jpg")
        self.assertEqual(translate_text("保存修改", "zh_CN"), "保存修改")

    def test_translates_unsaved_changes_prompt_with_action(self) -> None:
        translated = translate_text(
            "当前文件有未保存修改。\n\n选择“是”先保存，选择“否”放弃修改并关闭窗口，选择“取消”继续编辑。",
            "en",
        )

        self.assertIn("unsaved changes", translated)
        self.assertIn("close the window", translated)


if __name__ == "__main__":
    unittest.main()
