"""
THE PULSE EDITORIAL - THE ATELIER (CỘT TRÁI: PRODUCTION STUDIO & XU HƯỚNG TIKTOK)
- Cảm hứng thời gian thực: RSS Tin nóng GenK / Kenh14 + Trích xuất Top Từ khóa Xu hướng (TF-IDF) & Sentiment.
- Trợ lý AI Biên kịch Dual-Engine: Chọn giữa Gemini 3.8 Flash và Muse AI Chat.
- Sinh kịch bản phân cảnh Review / Bóc Mẽ 4 phần chuẩn TikTok.
- Tích hợp Tạo sinh Video TikTok 9:16 qua Muse AI REST API & Safe Fallback Engine.
- Trình phát video dọc TikTok 9:16 trực tiếp kèm nút tải file MP4.
"""

import html
import streamlit as st
from typing import Dict, Any, Tuple, Optional
from pathlib import Path

from src.scraper.rss_scraper import fetch_trending_news
from src.preprocessing.trend_extractor import extract_trending_topics
from src.ai.generator import generate_tiktok_script
from src.video.muse_integration import generate_tiktok_video
from app.components.editorial_utils import is_safe_url, render_clean_html


def render_editorial_atelier() -> Tuple[str, Optional[Dict[str, Any]], str, Dict[str, Any]]:
    """
    Render giao diện Xưởng Sản Xuất (Atelier) bên trái.
    Trả về: (content, selected_article_dict, topic_key, script_data)
    """
    # 1. Khởi tạo trạng thái phiên làm việc (Session State)
    if "editorial_topic" not in st.session_state:
        st.session_state.editorial_topic = "CongNghe"
    if "editorial_editor_textarea" not in st.session_state:
        st.session_state.editorial_editor_textarea = ""
    if "cached_articles" not in st.session_state:
        st.session_state.cached_articles = {}
    if "current_script_data" not in st.session_state:
        st.session_state.current_script_data = {}
    if "generated_video_result" not in st.session_state:
        st.session_state.generated_video_result = None

    # === PHẦN 1: NGUỒN CẢM HỨNG BÁO CHÍ & XU HƯỚNG (TREND RADAR) ===
    with st.container(border=True):
        render_clean_html(
            """
            <div class="editorial-panel-title">1. Radar Xu Hướng Thời Gian Thực (Trend Radar)</div>
            <div class="editorial-panel-subtitle">Dữ liệu dòng chảy báo chí trực tiếp từ các tòa soạn hàng đầu</div>
            """
        )

        selected_topic = st.segmented_control(
            "Chuyên mục báo chí:",
            options=["CongNghe", "GiaiTri"],
            format_func=lambda x: "Công nghệ & Số hóa (GenK)" if x == "CongNghe" else "Giải trí & Showbiz (Kenh14)",
            label_visibility="collapsed",
            key="editorial_topic"
        )
        topic_key = selected_topic or st.session_state.editorial_topic

        # Tải tin tức RSS
        if topic_key not in st.session_state.cached_articles or not st.session_state.cached_articles[topic_key]:
            with st.spinner("Đang cập nhật dòng tin tức thời gian thực..."):
                try:
                    fetched = fetch_trending_news(topic_key, limit=8)
                    st.session_state.cached_articles[topic_key] = fetched
                except Exception:
                    st.session_state.cached_articles[topic_key] = []

        articles = st.session_state.cached_articles.get(topic_key, [])
        selected_article = None

        if articles:
            # Trích xuất Top từ khóa xu hướng bằng TF-IDF N-grams
            trend_data = extract_trending_topics(articles, top_n=6)
            keywords = trend_data.get("keywords", [])
            sentiment = trend_data.get("sentiment", {})
            tone = trend_data.get("overall_tone", "Sôi động")

            # Hiển thị Badges từ khóa xu hướng
            badges_html = " ".join([
                f"""<span style="background: #FEF3C7; color: #92400E; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; margin-right: 4px; display: inline-block;">#{kw[0]} ({kw[1]}%)</span>"""
                for kw in keywords[:5]
            ])
            render_clean_html(
                f"""
                <div style="margin-bottom: 0.75rem; padding: 0.5rem 0.75rem; background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 6px;">
                    <div style="font-size: 0.7rem; font-weight: 700; text-transform: uppercase; color: #B45309; margin-bottom: 0.25rem;">
                        🔥 TOP TỪ KHÓA NÓNG: {badges_html}
                    </div>
                    <div style="font-size: 0.72rem; color: #78350F;">
                        Sắc thái cộng đồng: <strong>{tone}</strong> (Tích cực: {sentiment.get('positive', 60)}% · Trung tính: {sentiment.get('neutral', 30)}% · Tiêu cực: {sentiment.get('negative', 10)}%)
                    </div>
                </div>
                """
            )

            article_titles = [f"{i+1}. {a.get('title', 'Bản tin')}" for i, a in enumerate(articles)]
            chosen_title_idx = st.selectbox(
                "Chọn bài báo làm nguồn cảm hứng:",
                options=range(len(article_titles)),
                format_func=lambda i: article_titles[i],
                key=f"article_select_{topic_key}"
            )
            selected_article = articles[chosen_title_idx]

            # Trích dẫn bài báo nguồn và ảnh thumbnail thực tế
            summary_text = selected_article.get("summary", "").strip()
            article_url = selected_article.get("link") or selected_article.get("url") or "#"
            safe_url = html.escape(article_url, quote=True) if is_safe_url(article_url) else "#"
            safe_summary = html.escape(summary_text)
            safe_source = html.escape(str(selected_article.get("source", "Báo")))

            render_clean_html(
                f"""
                <div class="editorial-quote">
                    <div>"{safe_summary}"</div>
                    <div style="margin-top: 0.35rem; font-size: 0.75rem; font-style: normal;">
                        <a href="{safe_url}" target="_blank" rel="noopener noreferrer" style="color: #C2410C; text-decoration: none; font-weight: 500;">
                            Xem nguồn bài viết trên {safe_source} ↗
                        </a>
                    </div>
                </div>
                """
            )
        else:
            st.info("Hiện không có bài báo mới trong danh mục này.")

    # === PHẦN 2: BÀN SOẠN THẢO KỊCH BẢN DUAL-ENGINE AI ===
    with st.container(border=True):
        render_clean_html(
            """
            <div class="editorial-panel-title">2. Xưởng Biên Kịch TikTok (AI Script Atelier)</div>
            <div class="editorial-panel-subtitle">Sáng tạo kịch bản Review / Bóc Mẽ 4 phân cảnh chuẩn TikTok</div>
            """
        )

        col_engine, col_btn = st.columns([6, 6])
        with col_engine:
            if "ai_script_engine" not in st.session_state:
                st.session_state.ai_script_engine = "gemini"

            script_engine = st.radio(
                "Chọn AI Soạn Kịch Bản:",
                options=["gemini", "muse"],
                format_func=lambda x: "✨ Gemini 3.8 Flash (Tốc độ cao)" if x == "gemini" else "🎬 Muse AI Chat (Meta Muse)",
                horizontal=True,
                key="ai_script_engine"
            )

        with col_btn:
            st.write("")  # Cân chỉnh lề dọc
            generate_clicked = st.button("✨ Soạn Kịch Bản Review/Bóc Mẽ", key="btn_script_action", use_container_width=True)

        # Xử lý sinh kịch bản bằng AI
        if generate_clicked:
            if not selected_article:
                st.warning("Vui lòng chọn một bài báo nguồn trước khi tạo kịch bản!")
            else:
                engine_name = "Gemini 3.8 Flash" if script_engine == "gemini" else "Muse AI Chat"
                with st.spinner(f"Đang gọi {engine_name} sáng tác kịch bản Review / Bóc Mẽ 4 phân cảnh..."):
                    try:
                        title = selected_article.get("title", "")
                        summary = selected_article.get("summary", "")
                        script_res = generate_tiktok_script(title=title, summary=summary, engine=script_engine)

                        # Lưu trữ vào session state
                        st.session_state.current_script_data = script_res
                        st.session_state["editorial_editor_textarea"] = script_res.get("full_script", "")
                        st.toast(f"Đã soạn xong kịch bản cùng {engine_name}!", icon="✍️")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi khi gọi {engine_name}: {e}")

        # Trình soạn thảo văn bản kịch bản
        content = st.text_area(
            "Nội dung kịch bản thoại TikTok (Toàn văn):",
            height=200,
            placeholder="Kịch bản 4 phân cảnh sẽ xuất hiện tại đây sau khi bạn bấm 'Soạn Kịch Bản Review/Bóc Mẽ'...",
            key="editorial_editor_textarea"
        )

        # Cập nhật script data khi người dùng sửa tay
        current_script = st.session_state.current_script_data
        if content and (not current_script or current_script.get("full_script") != content):
            current_script["full_script"] = content

        # Hiển thị Visual Prompt sinh riêng cho Muse AI trong expander
        muse_prompt = current_script.get("muse_visual_prompt", "")
        if muse_prompt:
            with st.expander("🎨 Xem Visual Prompt tiếng Anh tối ưu riêng cho Muse AI (9:16)", expanded=False):
                st.code(muse_prompt, language="text")

    # === PHẦN 3: TẠO SINH VIDEO TIKTOK 9:16 (MUSE AI VIDEO STUDIO) ===
    with st.container(border=True):
        render_clean_html(
            """
            <div class="editorial-panel-title">3. Xưởng Tạo Sinh Video TikTok 9:16 (Muse AI Studio)</div>
            <div class="editorial-panel-subtitle">Tạo video dọc TikTok chân thực với ảnh nhân vật thật & phụ đề động</div>
            """
        )

        col_v_btn, col_v_mode = st.columns([7, 5])
        with col_v_btn:
            render_video_clicked = st.button("🎬 Tạo Video TikTok (Muse AI)", key="btn_render_video", use_container_width=True)
        with col_v_mode:
            v_mode = st.selectbox(
                "Chế độ tạo video:",
                options=["auto", "fallback", "muse_api"],
                format_func=lambda x: "Tự động thích ứng (Khuyên dùng)" if x == "auto" else ("Safe Fallback (Ngoại tuyến/Demo)" if x == "fallback" else "Muse AI API Thật"),
                key="video_render_mode_select"
            )

        if render_video_clicked:
            if not content.strip():
                st.warning("Vui lòng soạn thảo kịch bản trước khi tạo video!")
            else:
                ref_img_url = None
                if selected_article:
                    ref_img_url = selected_article.get("thumbnail") or selected_article.get("thumbnail_url")

                with st.spinner("Đang tạo sinh video TikTok dọc 9:16 (kết hợp chuyển động, âm thanh và phụ đề)..."):
                    try:
                        v_res = generate_tiktok_video(
                            visual_prompt=muse_prompt or content[:150],
                            reference_image_url=ref_img_url,
                            script_data=current_script or {"hook": content[:40], "body": content, "cta": "Xem thêm!"},
                            mode=v_mode,
                            duration=5
                        )
                        st.session_state.generated_video_result = v_res
                        st.toast("Đã xuất bản video TikTok 9:16 thành công!", icon="🎬")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi tạo video: {e}")

        # Hiển thị trình phát video dọc nếu đã có video
        video_result = st.session_state.generated_video_result
        if video_result and video_result.get("status") == "success":
            v_path = video_result.get("video_path", "")
            if v_path and Path(v_path).exists():
                render_clean_html(
                    f"""
                    <div style="margin-top: 0.5rem; margin-bottom: 0.5rem; font-size: 0.8rem; color: #16A34A; font-weight: 600;">
                        ✓ {video_result.get('message', 'Video đã tạo thành công')} ({video_result.get('mode', 'auto')})
                    </div>
                    """
                )
                col_player, col_dl = st.columns([8, 4])
                with col_player:
                    st.video(v_path)
                with col_dl:
                    with open(v_path, "rb") as vf:
                        st.download_button(
                            label="📥 Tải Video MP4",
                            data=vf,
                            file_name=Path(v_path).name,
                            mime="video/mp4",
                            use_container_width=True
                        )

    return content, selected_article, topic_key, current_script
