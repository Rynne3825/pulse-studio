"""
THE PULSE EDITORIAL - THE CURATOR (CỘT PHẢI: BẢNG CHẤM ĐIỂM TIỀM NĂNG VIRAL & CHECKLIST TỐI ƯU)
Thay thế toàn bộ mô phỏng 24h cũ bằng Bộ Đo Lường Tiềm Năng Viral TikTok 0 - 100 Điểm:
- Thẻ điểm Hero: Điểm Viral tổng hợp và Xếp hạng Tier (S / A / B / C) với màu sắc nhận diện.
- 4 Thanh tiến trình tiêu chuẩn vàng: Hook 3s, Bám sát trend, Nhịp điệu thoại, CTA tương tác.
- Đo lường chi tiết: Số từ, thời lượng nói ước tính, từ khóa bắt trend.
- Checklist khuyến nghị tối ưu hóa nội dung (Actionable Feedback Checklist).
"""

import html
import streamlit as st
from typing import Dict, Any, Optional
from src.models.content_evaluator import evaluate_tiktok_script
from app.components.editorial_utils import render_clean_html


def render_editorial_curator(
    content: str,
    selected_article: Optional[Dict[str, Any]],
    topic_key: str,
    script_data: Optional[Dict[str, Any]] = None
) -> None:
    """
    Render cột The Curator bên phải: Bảng chấm điểm Viral và Checklist tối ưu hóa.
    """
    source_title = selected_article.get("title", "") if selected_article else ""
    source_summary = selected_article.get("summary", "") if selected_article else ""
    source_full = f"{source_title} {source_summary}".strip()

    # Chuẩn bị dữ liệu kịch bản để chấm điểm
    eval_script = dict(script_data or {})
    if content.strip():
        eval_script["full_script"] = content.strip()
        # Nếu chưa bóc tách từng phân cảnh, lấy câu đầu làm hook
        if not eval_script.get("hook"):
            sentences = re_split_sentences(content.strip())
            eval_script["hook"] = sentences[0] if sentences else content[:50]
            eval_script["body"] = " ".join(sentences[1:-1]) if len(sentences) > 2 else content
            eval_script["cta"] = sentences[-1] if len(sentences) > 1 else ""

    # Thực hiện chấm điểm bằng TikTokViralEvaluator
    report = evaluate_tiktok_script(eval_script, source_full)

    overall_score = report["overall_score"]
    grade = report["grade"]
    grade_title = report["grade_title"]
    grade_color = report["grade_color"]
    breakdown = report["breakdown"]
    metrics = report["metrics"]
    checklist = report["actionable_checklist"]

    # === PHẦN 1: THẺ ĐIỂM HERO VIRAL SCORECARD (0 - 100) ===
    with st.container(border=True):
        render_clean_html(
            f"""
            <div class="editorial-panel-title">Bảng Đo Lường Tiềm Năng Viral TikTok</div>
            <div class="editorial-panel-subtitle">Chấm điểm thuật toán phân phối nội dung video ngắn dựa trên 4 trụ cột</div>
            
            <div style="background: #FAFAFA; border: 2px solid {grade_color}; border-radius: 12px; padding: 1.5rem; margin-top: 0.75rem; text-align: center;">
                <div style="font-size: 0.85rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: #71717A;">
                    ĐIỂM SỐ TIỀM NĂNG VIRAL
                </div>
                <div style="font-family: 'Newsreader', Georgia, serif; font-size: 4rem; font-weight: 700; color: {grade_color}; line-height: 1; margin: 0.5rem 0;">
                    {int(overall_score)}<span style="font-size: 1.75rem; color: #A1A1AA;">/100</span>
                </div>
                <div style="display: inline-block; background: {grade_color}; color: #FFFFFF; font-weight: 700; font-size: 0.85rem; padding: 4px 16px; border-radius: 20px; text-transform: uppercase; letter-spacing: 0.05em;">
                    HẠNG {grade} · {grade_title}
                </div>
            </div>
            """
        )

    # === PHẦN 2: THANH TIẾN TRÌNH 4 TIÊU CHUẨN VÀNG ===
    with st.container(border=True):
        render_clean_html(
            """
            <div class="editorial-panel-title">Phân Tích 4 Tiêu Chuẩn Vàng Thuật Toán</div>
            <div class="editorial-panel-subtitle">Tỷ trọng các yếu tố quyết định khả năng giữ chân & đẩy xu hướng</div>
            """
        )

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**1. Sức mạnh Hook 3s (25%):** `{breakdown['hook_score']}/100`")
            st.progress(float(breakdown["hook_score"]) / 100.0)

            st.markdown(f"**3. Nhịp điệu thoại (20%):** `{breakdown['pacing_score']}/100`")
            st.progress(float(breakdown["pacing_score"]) / 100.0)

        with col2:
            st.markdown(f"**2. Bám sát tin tức gốc (35%):** `{breakdown['trend_similarity_score']}/100`")
            st.progress(float(breakdown["trend_similarity_score"]) / 100.0)

            st.markdown(f"**4. Kêu gọi CTA (20%):** `{breakdown['cta_score']}/100`")
            st.progress(float(breakdown["cta_score"]) / 100.0)

        # Thông số đo lường chi tiết
        word_count = metrics.get("word_count", 0)
        dur = metrics.get("estimated_duration_sec", 0.0)
        hook_kws = metrics.get("hook_keywords", [])
        cta_kws = metrics.get("cta_keywords", [])

        kw_badge_hook = ", ".join(hook_kws) if hook_kws else "Chưa có"
        kw_badge_cta = ", ".join(cta_kws) if cta_kws else "Chưa có"

        render_clean_html(
            f"""
            <div style="margin-top: 1rem; padding: 0.75rem; background: #F4F4F5; border-radius: 8px; font-size: 0.78rem; color: #3F3F46; display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem;">
                <div>📝 <strong>Số từ thoại:</strong> {word_count} từ</div>
                <div>⏱️ <strong>Thời lượng ước tính:</strong> ~{dur} giây</div>
                <div>⚡ <strong>Từ khóa Hook:</strong> {html.escape(kw_badge_hook)}</div>
                <div>💬 <strong>Từ khóa CTA:</strong> {html.escape(kw_badge_cta)}</div>
            </div>
            """
        )

    # === PHẦN 3: CHECKLIST KHUYẾN NGHỊ TỐI ƯU HÓA ===
    with st.container(border=True):
        render_clean_html(
            """
            <div class="editorial-panel-title">Checklist Khuyến Nghị Tối Ưu Hóa</div>
            <div class="editorial-panel-subtitle">Hướng dẫn hành động cụ thể để nâng hạng kịch bản lên Hạng S</div>
            """
        )

        for item in checklist:
            # Phân loại tích cực vs khuyến nghị cải thiện
            is_positive = any(term in item.lower() for term in ["hoàn hảo", "súc tích", "bám sát", "chứa từ khóa", "kêu gọi", "kích thích"])
            icon = "✅" if is_positive else "💡"
            text_color = "#15803D" if is_positive else "#B45309"
            bg_color = "#F0FDF4" if is_positive else "#FFFBEB"
            border_color = "#BBF7D0" if is_positive else "#FDE68A"

            render_clean_html(
                f"""
                <div style="padding: 0.5rem 0.75rem; margin-bottom: 0.4rem; background: {bg_color}; border: 1px solid {border_color}; border-radius: 6px; font-size: 0.8rem; color: {text_color}; line-height: 1.4;">
                    {icon} {html.escape(item)}
                </div>
                """
            )


def re_split_sentences(text: str) -> list[str]:
    """Tách câu đơn giản cho kịch bản tiếng Việt."""
    import re
    raw = [s.strip() for s in re.split(r"[.!?\n]+", text) if s.strip()]
    return raw
