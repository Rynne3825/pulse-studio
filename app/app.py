"""
THE PULSE STUDIO - MAIN ENTRY POINT
Kiến trúc Swiss Bento Light Studio (KPI Ribbon + 3 Tabs chuyên biệt)
Chuyên đề: Phân Tích Xu Hướng Mạng Xã Hội & Tối Ưu Bài Đăng Tích Hợp AI Tạo Sinh
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)

import streamlit as st

sys.path.insert(0, str(PROJECT_ROOT))

from app.components.styles import apply_studio_styles
from app.components.header import render_studio_header, render_kpi_ribbon
from app.components.editor import (
    init_studio_state,
    get_current_trend_context,
    render_trend_radar_tab,
    render_post_editor_panel,
)
from app.components.curator import (
    render_curator_panel,
    render_experiment_lab_tab,
    load_experiment_history,
)
from app.components.utils import resolve_active_evaluation, render_clean_html


def main() -> None:
    st.set_page_config(
        page_title="The Pulse Studio — Phân Tích Xu Hướng & Tối Ưu Hóa Bài Đăng AI",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    apply_studio_styles()
    init_studio_state()

    topic_key, articles, trend_data, selected_article = get_current_trend_context()
    current_draft = str(st.session_state.get("editorial_editor_textarea", ""))
    has_draft = bool(current_draft.strip())
    has_refined = bool(st.session_state.get("v2_eval"))

    render_studio_header(has_draft=has_draft, has_refined=has_refined)

    active_eval, delta_score = resolve_active_evaluation(current_draft, selected_article)
    keywords = trend_data.get("keywords", []) if isinstance(trend_data, dict) else []
    top_keyword = ""
    top_keyword_heat = 0.0
    if keywords:
        first_kw = keywords[0]
        if isinstance(first_kw, (tuple, list)) and len(first_kw) >= 2:
            top_keyword = str(first_kw[0])
            top_keyword_heat = float(first_kw[1])
        elif isinstance(first_kw, dict):
            top_keyword = str(first_kw.get("keyword", ""))
            top_keyword_heat = float(first_kw.get("score", first_kw.get("heat", first_kw.get("weight", 0.0))))

    active_score = float(active_eval.get("overall_score", 0.0)) if has_draft else 0.0
    active_grade = str(active_eval.get("grade", "—")) if has_draft else "—"
    if "experiment_history" not in st.session_state:
        st.session_state.experiment_history = load_experiment_history()
    history = st.session_state.experiment_history

    render_kpi_ribbon(
        articles_count=len(articles),
        top_keyword=top_keyword,
        top_keyword_heat=top_keyword_heat,
        active_score=active_score,
        active_grade=active_grade,
        delta_score=delta_score,
        history=history,
    )

    tab_radar, tab_studio, tab_lab = st.tabs(
        [
            "📡 Radar Xu Hướng & Nguồn Tin",
            "⚡ Xưởng Biên Tập & Tối Ưu Hóa",
            "🧪 Thực Nghiệm & Báo Cáo Khóa Luận",
        ]
    )

    with tab_radar:
        selected_from_tab = render_trend_radar_tab(topic_key, articles, trend_data)
        if selected_from_tab is not None:
            selected_article = selected_from_tab

    with tab_studio:
        col_editor, col_curator = st.columns([1, 1], gap="large")
        with col_editor:
            content, post_data = render_post_editor_panel(selected_article)
        with col_curator:
            render_curator_panel(content, selected_article, topic_key, post_data)

    with tab_lab:
        render_experiment_lab_tab()

    render_clean_html(
        """
        <div style="border-top: 1px solid #E2E8F0; margin-top: 2.5rem; padding: 1rem 0 2rem 0; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.75rem; font-size: 0.75rem; color: #64748B;">
            <div>
                © 2026 <strong style="color: #0F172A;">The Pulse Studio</strong> · Hệ Thống Phân Tích Xu Hướng & Tối Ưu Bài Đăng AI.
            </div>
            <div style="display: flex; gap: 1.25rem; flex-wrap: wrap;">
                <span>AI Biên Tập: <strong style="color: #4F46E5;">Gemini 3.8 Flash</strong></span>
                <span>Nền Tảng: <strong style="color: #0F172A;">Facebook & Threads / X</strong></span>
                <span>Thuật Toán: <strong style="color: #0F172A;">TF-IDF N-grams & Cosine NLP</strong></span>
                <span>Kiến Trúc: <strong style="color: #0F172A;">100% Python Thuần</strong></span>
            </div>
        </div>
        """
    )


if __name__ == "__main__":
    main()
