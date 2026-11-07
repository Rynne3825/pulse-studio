"""
THE PULSE EDITORIAL - MASTHEAD HEADER
Tiêu đề chuẩn tòa soạn báo in danh tiếng:
- Đề tài: Phân tích xu hướng mạng xã hội & Tối ưu bài đăng tích hợp AI tạo sinh
- Trợ lý AI Kịch bản: Dual-Engine (Gemini 3.8 Flash & Muse AI Chat)
- Trợ lý AI Video: Muse AI (Image-to-Video 9:16 & Safe Fallback Engine)
- Đo lường: Viral Content Evaluator (0 - 100 Điểm)
"""

from datetime import datetime
from app.components.editorial_utils import render_clean_html


def render_editorial_masthead() -> None:
    now = datetime.now()
    days_vi = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
    day_name = days_vi[now.weekday()]
    formatted_date = f"{day_name}, {now.day} tháng {now.month}, {now.year}"

    render_clean_html(
        f"""
        <div style="padding-bottom: 0.5rem; margin-bottom: 1.5rem; border-bottom: 2px solid #18181B;">
            <div style="display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 0.5rem; padding-bottom: 0.25rem;">
                <div style="font-size: 0.8125rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.12em; color: #71717A;">
                    ĐỒ ÁN TỐT NGHIỆP: PHÂN TÍCH XU HƯỚNG MẠNG XÃ HỘI & TỐI ƯU BÀI ĐĂNG TÍCH HỢP AI TẠO SINH
                </div>
                <div style="font-size: 0.8125rem; color: #71717A; font-family: 'Newsreader', serif; font-style: italic;">
                    {formatted_date} · TikTok Studio v5.0
                </div>
            </div>
            
            <div style="display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; margin-top: 0.25rem;">
                <h1 style="font-family: 'Newsreader', Georgia, serif; font-size: 2.25rem; font-weight: 500; letter-spacing: -0.02em; color: #18181B; margin: 0; line-height: 1.1;">
                    The Pulse Editorial
                </h1>
                
                <div style="display: flex; gap: 1.25rem; font-size: 0.78rem; color: #52525B; padding-bottom: 0.25rem;">
                    <span><strong style="color: #18181B;">AI Kịch Bản:</strong> Dual-Engine (Gemini / Muse)</span>
                    <span><strong style="color: #18181B;">AI Video:</strong> Muse AI 9:16 (Image-to-Video)</span>
                    <span><strong style="color: #18181B;">Đo Lường:</strong> Viral Scorecard (0 - 100)</span>
                </div>
            </div>
        </div>
        """
    )
