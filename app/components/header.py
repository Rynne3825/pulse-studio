"""
THE PULSE STUDIO - MASTHEAD HEADER, STEPPER & 4 KPI BENTO CARDS
- Đèn tín hiệu LIVE nhấp nháy & Thanh tiến trình 3 bước động
- Popover công thức toán học (TF-IDF, Cosine Similarity, Weighted Score)
- Hàng 4 KPI Bento Cards đồng bộ trạng thái thời gian thực
"""

import html
from datetime import datetime
from typing import Dict, Any, List, Optional
import streamlit as st

from app.components.utils import render_clean_html


def render_studio_header(has_draft: bool = False, has_refined: bool = False) -> None:
    """Render phần đầu trang gồm trạng thái LIVE, tên đồ án, stepper và Popover công thức."""
    now = datetime.now()
    days_vi = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
    formatted_date = f"{days_vi[now.weekday()]}, {now.day}/{now.month}/{now.year}"

    step1_cls = "step-pill done" if has_draft else "step-pill active"
    step2_cls = "step-pill done" if has_refined else ("step-pill active" if has_draft else "step-pill")
    step3_cls = "step-pill done" if has_refined else "step-pill"

    col_title, col_action = st.columns([9.2, 2.8], gap="small")
    with col_title:
        render_clean_html(
            f"""
            <div style="display:flex;flex-direction:column;gap:0.45rem;margin-bottom:0.55rem;">
                <div style="display:flex;align-items:center;gap:0.65rem;flex-wrap:wrap;">
                    <span class="live-badge"><span class="live-dot"></span> LIVE · 4 TÒA SOẠN</span>
                    <span style="font-size:0.78rem;font-weight:600;letter-spacing:0.05em;color:#64748B;text-transform:uppercase;">
                        ĐỒ ÁN TỐT NGHIỆP · {formatted_date}
                    </span>
                </div>
                <div style="display:flex;align-items:baseline;justify-content:space-between;flex-wrap:wrap;gap:0.75rem;">
                    <div>
                        <h1 style="font-family:'Space Grotesk',sans-serif;font-size:2rem;font-weight:700;letter-spacing:-0.03em;color:#0F172A;margin:0;line-height:1.12;">
                            The Pulse Studio
                        </h1>
                        <div style="font-size:0.86rem;color:#475569;margin-top:0.2rem;">
                            Phân tích xu hướng mạng xã hội &amp; tối ưu hóa bài đăng AI tạo sinh (Gemini 3.8 Flash)
                        </div>
                    </div>
                    <div class="stepper-bar">
                        <span class="{step1_cls}">① Quét Xu Hướng</span>
                        <span class="step-arrow">→</span>
                        <span class="{step2_cls}">② AI Soạn Bài</span>
                        <span class="step-arrow">→</span>
                        <span class="{step3_cls}">③ Tối Ưu Hạng S</span>
                    </div>
                </div>
            </div>
            """
        )

    with col_action:
        st.write("")
        with st.popover("📐 Công thức Toán & Cơ sở KH", width="stretch"):
            st.markdown("### Cơ Sở Thuật Toán & Mô Hình")
            st.markdown("**1. Khai phá xu hướng (`TF-IDF N-grams 1–3 từ`):**")
            st.latex(r"\text{TF-IDF}(t, d, D) = \text{TF}(t, d) \times \log\left(\frac{|D|}{1 + df(t)}\right)")
            st.markdown("**2. Độ bám sát tin tức gốc (`Cosine Similarity`):**")
            st.latex(r"\text{Similarity}(\vec{A}, \vec{B}) = \frac{\vec{A} \cdot \vec{B}}{\|\vec{A}\| \, \|\vec{B}\|}")
            st.markdown("**3. Điểm tiềm năng Viral đa tiêu chí (0 – 100):**")
            st.latex(r"\text{Score} = 0.25 \cdot \text{Hook} + 0.35 \cdot \text{Trend} + 0.20 \cdot \text{Pacing} + 0.20 \cdot \text{CTA}")
            st.markdown(
                "**4. Tối ưu khép kín (Closed-Loop Refinement):** Bóc tách lỗi từ 4 trụ cột trên, "
                "đưa phản hồi ngược lại cho Gemini 3.8 Flash tái biên tập phiên bản v2 nhằm tối đa hóa $\\Delta\\text{Score}$."
            )


def render_kpi_ribbon(
    articles_count: int,
    top_keyword: str,
    top_keyword_heat: float,
    active_score: float,
    active_grade: str,
    delta_score: Optional[float],
    history: List[Dict[str, Any]],
) -> None:
    """Render 4 thẻ KPI tổng quan theo phong cách Swiss Bento."""
    kw_display = f"#{top_keyword}" if top_keyword else "Chưa quét"
    kw_sub = f"Độ nóng TF-IDF: {top_keyword_heat:.1f}%" if top_keyword else "Chọn chuyên mục ở Tab 1"

    score_display = f"{active_score:.1f}/100" if active_score > 0 else "—"
    if delta_score is not None:
        score_sub = f"Hạng {active_grade} · Tối ưu {delta_score:+.1f} điểm"
    elif active_score > 0:
        score_sub = f"Xếp hạng {active_grade}"
    else:
        score_sub = "Chưa có bài viết nháp"

    if history:
        avg_delta = round(sum(float(h.get("delta", 0.0)) for h in history) / len(history), 1)
        exp_display = f"{avg_delta:+.1f} đ"
        exp_sub = f"Trung bình trên {len(history)} mẫu thử"
    else:
        exp_display = "0 mẫu"
        exp_sub = "Chạy tối ưu v1 → v2 để lưu"

    render_clean_html(
        f"""
        <div class="kpi-grid">
            <div class="kpi-card" style="--kpi-accent:#4F46E5;">
                <div class="kpi-label"><span>📰 Tin tức thời gian thực</span><span class="kpi-tag" style="color:#4F46E5;background:#EEF2FF;">RSS</span></div>
                <div class="kpi-value">{articles_count} bài</div>
                <div class="kpi-sub">Cập nhật trực tiếp từ tòa soạn</div>
            </div>
            <div class="kpi-card" style="--kpi-accent:#F59E0B;">
                <div class="kpi-label"><span>🔥 Từ khóa nóng Top #1</span><span class="kpi-tag" style="color:#D97706;background:#FEF3C7;">NLP</span></div>
                <div class="kpi-value" title="{html.escape(kw_display)}">{html.escape(kw_display)}</div>
                <div class="kpi-sub">{html.escape(kw_sub)}</div>
            </div>
            <div class="kpi-card" style="--kpi-accent:#10B981;">
                <div class="kpi-label"><span>🎯 Điểm Viral hiện tại</span><span class="kpi-tag" style="color:#059669;background:#DCFCE7;">Score</span></div>
                <div class="kpi-value">{html.escape(score_display)}</div>
                <div class="kpi-sub">{html.escape(score_sub)}</div>
            </div>
            <div class="kpi-card" style="--kpi-accent:#6366F1;">
                <div class="kpi-label"><span>📈 Hiệu suất tối ưu TB</span><span class="kpi-tag" style="color:#4338CA;background:#E0E7FF;">Δ Lab</span></div>
                <div class="kpi-value">{html.escape(exp_display)}</div>
                <div class="kpi-sub">{html.escape(exp_sub)}</div>
            </div>
        </div>
        """
    )
