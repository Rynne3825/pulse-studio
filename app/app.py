"""
THE PULSE EDITORIAL - MAIN ENTRY POINT
Kiến trúc Split-Screen Studio 2 Cột (The Atelier & The Curator)
Chuyên đề: Phân Tích Xu Hướng Mạng Xã Hội & Tối Ưu Bài Đăng Tích Hợp AI Tạo Sinh (TikTok Studio)
100% Python thuần, kiến trúc rõ ràng, sinh viên dễ dàng trình bày và bảo vệ trước hội đồng.
"""

import sys
from pathlib import Path
import streamlit as st

# Thiết lập đường dẫn thư mục gốc để nạp module src
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.components.editorial_styles import apply_editorial_styles
from app.components.editorial_masthead import render_editorial_masthead
from app.components.editorial_atelier import render_editorial_atelier
from app.components.editorial_curator import render_editorial_curator
from app.components.editorial_utils import render_clean_html


def main() -> None:
    # 1. Cấu hình cơ bản của trang Streamlit
    st.set_page_config(
        page_title="The Pulse Editorial — TikTok Trend & Content Optimization Studio",
        page_icon="🎬",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    # 2. Áp dụng hệ thống phong cách thẩm mỹ Editorial Minimalist
    apply_editorial_styles()

    # 3. Tiêu đề ấn phẩm báo chí (Masthead)
    render_editorial_masthead()

    # 4. Không gian làm việc Split-Screen 2 Cột (Tỷ lệ 50 : 50 cân đối)
    col_atelier, col_curator = st.columns([1, 1], gap="large")

    with col_atelier:
        # Cột Trái: Xưởng Sản Xuất (Atelier) - Cào xu hướng, AI biên kịch & Tạo video 9:16
        content, selected_article, topic_key, script_data = render_editorial_atelier()

    with col_curator:
        # Cột Phải: Ban Giám Tuyển (Curator) - Chấm điểm Viral 0-100 & Checklist tối ưu
        render_editorial_curator(content, selected_article, topic_key, script_data)

    # 5. Chân trang ghi nhận độ tin cậy mô hình (Editorial Colophon / Telemetry)
    render_clean_html(
        """
        <div style="border-top: 1px solid #EAE6DF; margin-top: 2.5rem; padding-top: 1rem; padding-bottom: 2rem; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem; font-size: 0.75rem; color: #71717A;">
            <div>
                © 2026 <strong>The Pulse Editorial</strong> · Hệ thống phân tích xu hướng mạng xã hội & tối ưu bài đăng tích hợp AI tạo sinh.
            </div>
            <div style="display: flex; gap: 1rem;">
                <span>AI Biên Kịch: <strong>Gemini 3.8 / Muse Chat</strong></span>
                <span>AI Video: <strong>Muse AI 9:16 & Safe Fallback</strong></span>
                <span>Thuật Toán: <strong>TF-IDF & Cosine NLP</strong></span>
                <span>Kiến Trúc: <strong>100% Python Thuần (0 n8n)</strong></span>
            </div>
        </div>
        """
    )


if __name__ == "__main__":
    main()
