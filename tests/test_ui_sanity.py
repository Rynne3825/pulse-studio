"""
Kiểm thử tự động giao diện Streamlit (UI Sanity & Regression Test Suite).
Sử dụng streamlit.testing.v1.AppTest để giả lập tương tác người dùng:
1. Render ban đầu không văng lỗi TypeError/KeyError khi chưa có dữ liệu kịch bản.
2. Luồng soạn kịch bản AI (btn_script_action) cập nhật The Curator không lỗi.
3. Luồng dựng video TikTok (btn_render_video) xuất bản MP4 thành công.
"""

import sys
import unittest
from pathlib import Path

# Đảm bảo project root nằm trong sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from streamlit.testing.v1 import AppTest


class TestStreamlitUISanity(unittest.TestCase):
    """Bộ test hồi quy tự động giao diện Streamlit."""

    def test_01_initial_render_no_exception(self):
        """Kiểm tra trang chủ khởi động mượt mà, không gặp TypeError (str + list)."""
        at = AppTest.from_file(str(PROJECT_ROOT / "app" / "app.py"), default_timeout=30)
        at.run()
        self.assertEqual(len(at.exception), 0, f"Trang chủ lỗi khi tải lần đầu: {[e.message for e in at.exception]}")

    def test_02_script_generation_flow(self):
        """Kiểm tra bấm nút soạn kịch bản không phát sinh ngoại lệ giao diện."""
        at = AppTest.from_file(str(PROJECT_ROOT / "app" / "app.py"), default_timeout=45)
        at.run()
        self.assertEqual(len(at.exception), 0)

        # Bấm nút soạn kịch bản
        btn_script = at.button(key="btn_script_action")
        self.assertIsNotNone(btn_script)
        btn_script.click()
        at.run()

        self.assertEqual(len(at.exception), 0, f"Lỗi khi bấm soạn kịch bản: {[e.message for e in at.exception]}")
        content = at.text_area(key="editorial_editor_textarea").value
        self.assertTrue(len(content.strip()) > 0, "Kịch bản soạn xong không được rỗng")

    def test_03_video_render_flow(self):
        """Kiểm tra bấm nút dựng video tạo ra video thành công trong giao diện."""
        at = AppTest.from_file(str(PROJECT_ROOT / "app" / "app.py"), default_timeout=60)
        at.run()

        # Điền kịch bản thử nghiệm
        editor = at.text_area(key="editorial_editor_textarea")
        editor.input("Cảnh báo xu hướng mới! Sự thật cần làm rõ ngay. Bạn nghĩ sao? Hãy bình luận nhé!")
        at.run()

        # Chọn duration 15s cho nhanh
        dur_select = at.selectbox(key="video_duration_select")
        dur_select.select(15)
        at.run()

        # Bấm nút dựng video
        btn_video = at.button(key="btn_render_video")
        btn_video.click()
        at.run()

        self.assertEqual(len(at.exception), 0, f"Lỗi khi bấm dựng video: {[e.message for e in at.exception]}")
        res = at.session_state.get("generated_video_result")
        self.assertIsNotNone(res)
        self.assertEqual(res.get("status"), "success")
        v_path = Path(res.get("video_path", ""))
        self.assertTrue(v_path.exists(), f"File video không tồn tại: {v_path}")
        self.assertGreater(v_path.stat().st_size, 100000, "Dung lượng video phải > 100KB")


if __name__ == "__main__":
    unittest.main()
