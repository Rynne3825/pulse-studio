"""
THE PULSE STUDIO - TAB 1 (RADAR XU HƯỚNG) & CỘT TRÁI TAB 2 (XƯỞNG BIÊN TẬP BÀI ĐĂNG)
- Tab 1: Radar RSS 4 chuyên mục báo chí, biểu đồ Top từ khóa TF-IDF, Donut sắc thái & thẻ tin gốc
- Cột trái Tab 2: Cấu hình nền tảng Facebook/Threads, AI biên tập Gemini 3.8 Flash & Live Social Preview Card
"""

import html
import json
import logging
import re
from typing import Dict, Tuple, Optional, Any, List
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

logger = logging.getLogger(__name__)

from src.rss.scraper import fetch_trending_news, RSS_CONFIG
from src.nlp.trends import extract_trending_topics
from src.ai.generator import generate_social_post
from src.eval.scorer import evaluate_post
from app.components.utils import is_safe_url, render_clean_html
from app.components.charts import (
    build_keywords_bar_chart,
    build_sentiment_donut_chart,
)

TOPIC_DISPLAY_NAMES = {
    "CongNghe": "💻 Công nghệ (GenK)",
    "GiaiTri": "🎬 Giải trí (Kenh14)",
    "KinhDoanh": "💼 Kinh doanh (VnExpress)",
    "DoiSong": "🌏 Đời sống (Tuổi Trẻ)",
}


def init_studio_state() -> None:
    """Khởi tạo toàn bộ biến trạng thái phiên làm việc."""
    if "editorial_topic" not in st.session_state:
        st.session_state.editorial_topic = "CongNghe"
    if "_pending_editor_text" in st.session_state:
        st.session_state.editorial_editor_textarea = st.session_state.pop("_pending_editor_text")
    if "editorial_editor_textarea" not in st.session_state:
        st.session_state.editorial_editor_textarea = ""
    if "cached_articles" not in st.session_state:
        st.session_state.cached_articles = {}
    if "current_post_data" not in st.session_state:
        st.session_state.current_post_data = {}
    if "v1_post" not in st.session_state:
        st.session_state.v1_post = None
    if "v1_eval" not in st.session_state:
        st.session_state.v1_eval = None
    if "v2_post" not in st.session_state:
        st.session_state.v2_post = None
    if "v2_eval" not in st.session_state:
        st.session_state.v2_eval = None
    if "social_platform" not in st.session_state:
        st.session_state.social_platform = "facebook"
    if "social_style" not in st.session_state:
        st.session_state.social_style = "trend"
    if "experiment_history" not in st.session_state:
        st.session_state.experiment_history = []


def get_current_trend_context() -> Tuple[str, List[Dict[str, Any]], Dict[str, Any], Optional[Dict[str, Any]]]:
    """Lấy chuyên mục hiện tại, danh sách bài báo và phân tích xu hướng NLP."""
    init_studio_state()
    topic_key = st.session_state.get("editorial_topic") or "CongNghe"
    if topic_key not in RSS_CONFIG:
        topic_key = "CongNghe"

    if topic_key not in st.session_state.cached_articles or not st.session_state.cached_articles[topic_key]:
        try:
            fetched = fetch_trending_news(topic_key, limit=10)
            st.session_state.cached_articles[topic_key] = fetched
        except Exception as exc:
            logger.warning("Không thể tải tin RSS chuyên mục %s: %s", topic_key, exc)
            st.session_state.cached_articles[topic_key] = []

    articles = st.session_state.cached_articles.get(topic_key, [])
    trend_data = extract_trending_topics(articles, top_n=8) if articles else {
        "keywords": [],
        "sentiment": {"positive": 50.0, "neutral": 50.0, "negative": 0.0},
        "overall_tone": "Chưa có dữ liệu",
    }

    sel_idx = st.session_state.get(f"article_select_{topic_key}", 0)
    if not isinstance(sel_idx, int) or sel_idx < 0 or sel_idx >= len(articles):
        sel_idx = 0
    selected_article = articles[sel_idx] if articles else None
    return topic_key, articles, trend_data, selected_article


def render_trend_radar_tab(
    topic_key: str,
    articles: List[Dict[str, Any]],
    trend_data: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Render Tab 1: Radar Tin Tức Xu Hướng & Phân Tích NLP."""
    with st.container(border=True):
        col_head, col_ref = st.columns([9.5, 2.5], gap="small")
        with col_head:
            render_clean_html(
                """
                <div class="panel-title">📡 Radar Xu Hướng Báo Chí &amp; Mạng Xã Hội</div>
                <div class="panel-subtitle">Theo dõi dòng tin tức thời gian thực và khai phá cụm chủ đề nóng bằng TF-IDF N-grams</div>
                """
            )
        with col_ref:
            if st.button("🔄 Làm Mới Tin RSS", type="secondary", key="btn_refresh_rss", width="stretch"):
                st.session_state.cached_articles[topic_key] = []
                st.toast("Đang tải lại dữ liệu mới nhất từ tòa soạn...", icon="🔄")
                st.rerun()

        topic_options = list(RSS_CONFIG.keys())
        st.segmented_control(
            "Chuyên mục báo chí:",
            options=topic_options,
            format_func=lambda x: TOPIC_DISPLAY_NAMES.get(x, x),
            label_visibility="collapsed",
            key="editorial_topic",
        )

    if not articles:
        st.warning("Hiện chưa tải được bài viết trực tiếp từ máy chủ RSS tòa soạn. Vui lòng bấm '🔄 Làm Mới Tin RSS' để thử lại.")
        return None

    keywords = trend_data.get("keywords", [])
    sentiment = trend_data.get("sentiment", {})
    overall_tone = trend_data.get("overall_tone", "Sôi động")

    col_kw, col_senti = st.columns([7, 5], gap="large")
    with col_kw:
        with st.container(border=True):
            render_clean_html(
                """
                <div class="panel-title">🔥 Top Từ Khóa Xu Hướng (TF-IDF N-grams)</div>
                <div class="panel-subtitle">Xếp hạng cụm từ ghép tiếng Việt có tần suất xuất hiện và độ bám tin vượt trội</div>
                """
            )
            if keywords:
                st.altair_chart(build_keywords_bar_chart(keywords), width="stretch")
            else:
                st.info("Chưa trích xuất được từ khóa nổi bật từ danh sách bài hiện tại.")

    with col_senti:
        with st.container(border=True):
            render_clean_html(
                f"""
                <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:0.5rem;flex-wrap:wrap;">
                    <div>
                        <div class="panel-title">🎭 Phân Bố Sắc Thái Dư Luận</div>
                        <div class="panel-subtitle">Định lượng tỷ lệ cảm xúc qua từ điển chuyên dụng</div>
                    </div>
                    <span style="background:#EEF2FF;color:#4338CA;font-size:0.72rem;font-weight:700;padding:4px 10px;border-radius:999px;border:1px solid #C7D2FE;">
                        {html.escape(str(overall_tone))}
                    </span>
                </div>
                """
            )
            st.altair_chart(build_sentiment_donut_chart(sentiment), width="stretch")

            pos_pct = round(float(sentiment.get("positive", 50.0)), 1)
            neu_pct = round(float(sentiment.get("neutral", 40.0)), 1)
            neg_pct = round(float(sentiment.get("negative", 10.0)), 1)
            render_clean_html(
                f"""
                <div class="sentiment-pills-row">
                    <div class="sentiment-pill" style="border-color:#A7F3D0;">
                        <div class="sentiment-pill-val" style="color:#059669;">{pos_pct}%</div>
                        <div class="sentiment-pill-lbl">Tích cực</div>
                    </div>
                    <div class="sentiment-pill" style="border-color:#FDE68A;">
                        <div class="sentiment-pill-val" style="color:#D97706;">{neu_pct}%</div>
                        <div class="sentiment-pill-lbl">Trung tính</div>
                    </div>
                    <div class="sentiment-pill" style="border-color:#FECDD3;">
                        <div class="sentiment-pill-val" style="color:#E11D48;">{neg_pct}%</div>
                        <div class="sentiment-pill-lbl">Tiêu cực</div>
                    </div>
                </div>
                """
            )

    with st.container(border=True):
        render_clean_html(
            """
            <div class="panel-title">🗞️ Kho Bài Báo Xu Hướng Đang Theo Dõi</div>
            <div class="panel-subtitle">Xem nhanh danh sách tin nóng vừa quét từ RSS và chọn một bài báo làm dữ liệu gốc cho Tab 2</div>
            """
        )
        feed_rows = [
            {
                "STT": i + 1,
                "Nguồn": str(a.get("source", "")),
                "Tiêu đề tin tức": str(a.get("title", "")),
                "Ảnh": "✅ Có ảnh" if is_safe_url(str(a.get("thumbnail_url", ""))) else "—",
                "Thời gian": str(a.get("published_at", ""))[:22],
            }
            for i, a in enumerate(articles)
        ]
        st.dataframe(
            pd.DataFrame(feed_rows),
            hide_index=True,
            width="stretch",
            height=min(235, 42 + len(feed_rows) * 35),
            column_config={
                "STT": st.column_config.NumberColumn(width="small"),
                "Nguồn": st.column_config.TextColumn(width="small"),
                "Ảnh": st.column_config.TextColumn(width="small"),
            },
        )
        article_titles = [f"{i + 1}. {a.get('title', 'Bản tin')}" for i, a in enumerate(articles)]
        chosen_idx = st.selectbox(
            "Chọn bài báo nguồn:",
            options=range(len(article_titles)),
            format_func=lambda i: article_titles[i],
            label_visibility="collapsed",
            key=f"article_select_{topic_key}",
        )
        selected_article = articles[chosen_idx]

        title_text = html.escape(str(selected_article.get("title", "")))
        summary_text = html.escape(str(selected_article.get("summary", "")).strip())
        article_url = selected_article.get("link") or "#"
        safe_url = html.escape(article_url, quote=True) if is_safe_url(article_url) else "#"
        safe_source = html.escape(str(selected_article.get("source", "Tòa soạn")))
        safe_time = html.escape(str(selected_article.get("published_at", "Mới cập nhật")))
        thumb_url = selected_article.get("thumbnail_url") or ""
        safe_thumb = html.escape(thumb_url, quote=True) if is_safe_url(thumb_url) else ""

        thumb_html = (
            f'<img src="{safe_thumb}" class="article-quote-thumb" alt="Thumbnail" referrerpolicy="no-referrer" onerror="this.style.display=\'none\';" />'
            if safe_thumb
            else ""
        )

        render_clean_html(
            f"""
            <div class="article-quote-card">
                {thumb_html}
                <div class="article-quote-body">
                    <div>
                        <div class="article-quote-title">{title_text}</div>
                        <div class="article-quote-text">{summary_text}</div>
                    </div>
                    <div class="article-quote-meta">
                        <span style="color:#64748B;">Nguồn: <strong>{safe_source}</strong> · {safe_time}</span>
                        <a href="{safe_url}" target="_blank" rel="noopener noreferrer" style="color:#4F46E5;text-decoration:none;font-weight:700;">
                            Đọc bài báo gốc trên {safe_source} ↗
                        </a>
                    </div>
                </div>
            </div>
            """
        )

    return selected_article


def _render_interactive_social_preview(
    raw_content: str,
    platform: str,
    tags: List[str],
    thumb_url: str,
) -> None:
    """Widget xem trước bài đăng tương tác thực tế với auto-resize và hiển thị ảnh nguyên vẹn."""
    missing_tags = [t for t in tags if t and t not in raw_content]
    full_copy_text = f"{raw_content}\n\n{' '.join(missing_tags)}".strip() if missing_tags else raw_content

    safe_body = html.escape(raw_content).replace("\n", "<br/>")
    tag_color = "#1877F2" if platform == "facebook" else "#4F46E5"
    safe_body = re.sub(
        r"(^|(?<=\s)|(?<=<br/>))(#[0-9A-Za-zÀ-ỹ_]+)",
        rf'\1<span style="color:{tag_color};font-weight:600;">\2</span>',
        safe_body,
    )
    extra_tags_html = (
        f'<div class="extra-tags">{html.escape(" ".join(missing_tags))}</div>'
        if missing_tags
        else ""
    )

    safe_thumb = html.escape(thumb_url, quote=True) if is_safe_url(thumb_url) else ""
    media_html = (
        f'<div class="media-wrap"><img src="{safe_thumb}" class="media-img" alt="Post media" referrerpolicy="no-referrer" onload="syncHeight()" onerror="this.parentElement.style.display=\'none\';syncHeight();" /></div>'
        if safe_thumb
        else ""
    )

    copy_json = (
        json.dumps(full_copy_text, ensure_ascii=True)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )

    is_fb = platform == "facebook"
    avatar_bg = "linear-gradient(135deg, #1877F2, #0C53B7)" if is_fb else "#0F172A"
    sub_meta = "Vừa xong · 🌐 Công khai" if is_fb else "@thepulsestudio · Vừa xong"
    card_border = "#CBD5E1" if is_fb else "#334155"
    plat_pill = "Facebook Feed" if is_fb else "Threads Post"

    # Chiều cao dự phòng an toàn để tránh bị cắt ảnh
    paragraphs = raw_content.splitlines() or [raw_content]
    wrapped_lines = sum(max(1, (len(p) + 38) // 39) for p in paragraphs)
    est_height = max(360, 260 + wrapped_lines * 24 + (420 if safe_thumb else 0))

    widget_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8" />
    <style>
        * {{ box-sizing: border-box; font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif; }}
        html, body {{ margin: 0; padding: 4px 2px 14px 2px; background: transparent; color: #0F172A; overflow: visible; }}
        .toolbar {{
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 10px; gap: 8px;
        }}
        .mode-group {{ display: flex; gap: 4px; background: #F1F5F9; padding: 3px; border-radius: 8px; }}
        .mode-btn {{
            border: none; background: transparent; color: #64748B; font-size: 11.5px;
            font-weight: 600; padding: 4px 10px; border-radius: 6px; cursor: pointer;
            transition: all 0.15s ease;
        }}
        .mode-btn.active {{ background: #FFFFFF; color: #0F172A; box-shadow: 0 1px 2px rgba(0,0,0,0.08); }}
        .copy-btn {{
            border: 1px solid #C7D2FE; background: #EEF2FF; color: #4338CA;
            font-size: 12px; font-weight: 700; padding: 5px 12px; border-radius: 8px;
            cursor: pointer; transition: all 0.16s ease;
        }}
        .copy-btn:hover {{ background: #4F46E5; color: #FFFFFF; border-color: #4F46E5; }}
        .copy-btn.copied {{ background: #10B981; color: #FFFFFF; border-color: #10B981; }}
        .card-wrap {{ display: flex; justify-content: center; }}
        .preview-card {{
            width: 100%; background: #FFFFFF; border: 1.5px solid {card_border};
            border-radius: 14px; padding: 14px 16px;
            box-shadow: 0 4px 14px rgba(15, 23, 42, 0.05);
            transition: max-width 0.25s cubic-bezier(0.22, 1, 0.36, 1);
        }}
        .preview-card.mobile {{ max-width: 340px; }}
        .header {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }}
        .author-row {{ display: flex; align-items: center; gap: 10px; }}
        .avatar {{
            width: 38px; height: 38px; border-radius: 50%; background: {avatar_bg};
            color: #FFFFFF; display: flex; align-items: center; justify-content: center;
            font-weight: 700; font-size: 13px; flex-shrink: 0;
        }}
        .name {{ font-weight: 700; font-size: 13.5px; color: #0F172A; }}
        .meta {{ font-size: 11.5px; color: #64748B; margin-top: 1px; }}
        .plat-badge {{
            font-size: 10.5px; font-weight: 700; color: #475569; background: #F1F5F9;
            padding: 2px 8px; border-radius: 999px;
        }}
        .body-text {{ font-size: 13.5px; line-height: 1.58; color: #1E293B; word-break: break-word; }}
        .extra-tags {{ margin-top: 8px; font-size: 12.5px; font-weight: 600; color: {tag_color}; }}
        .media-wrap {{
            margin-top: 11px; border-radius: 12px; border: 1px solid #E2E8F0;
            background: #F8FAFC; overflow: hidden; display: flex;
            justify-content: center; align-items: center;
        }}
        .media-img {{
            display: block; width: 100%; height: auto; max-height: 380px; object-fit: contain;
        }}
        .actions {{
            margin-top: 12px; padding-top: 8px; border-top: 1px solid #F1F5F9;
            display: flex; justify-content: space-around; gap: 6px;
        }}
        .act-btn {{
            flex: 1; border: none; background: transparent; color: #64748B;
            font-size: 12.5px; font-weight: 600; padding: 6px 8px; border-radius: 8px;
            cursor: pointer; transition: all 0.15s ease; white-space: nowrap;
        }}
        .act-btn:hover {{ background: #F1F5F9; color: #0F172A; }}
        .act-btn.liked {{ color: #1877F2; background: #EFF6FF; }}
    </style>
    </head>
    <body>
        <div class="toolbar">
            <div class="mode-group">
                <button class="mode-btn active" id="btnDesk" onclick="setMode('desktop')">🖥️ Desktop</button>
                <button class="mode-btn" id="btnMob" onclick="setMode('mobile')">📱 Mobile</button>
            </div>
            <button class="copy-btn" id="btnCopy" onclick="copyText()">📋 Sao chép bài đăng</button>
        </div>
        <div class="card-wrap">
            <div class="preview-card" id="card">
                <div class="header">
                    <div class="author-row">
                        <div class="avatar">PS</div>
                        <div>
                            <div class="name">The Pulse Studio</div>
                            <div class="meta">{html.escape(sub_meta)}</div>
                        </div>
                    </div>
                    <span class="plat-badge">{html.escape(plat_pill)}</span>
                </div>
                <div class="body-text">{safe_body}</div>
                {extra_tags_html}
                {media_html}
                <div class="actions">
                    <button class="act-btn" id="btnLike" onclick="toggleLike()">👍 Thích (<span id="likeCnt">128</span>)</button>
                    <button class="act-btn" onclick="pingAction(this, '💬 24 Bình luận')">💬 Bình luận (24)</button>
                    <button class="act-btn" onclick="pingAction(this, '↗️ Đã chia sẻ')">↗️ Chia sẻ</button>
                </div>
            </div>
        </div>
        <script>
            const RAW_TEXT = {copy_json};
            let liked = false;
            function syncHeight() {{
                const card = document.getElementById('card');
                const toolbar = document.querySelector('.toolbar');
                if (!card) return;
                const targetH = (toolbar ? toolbar.offsetHeight : 36) + card.offsetHeight + 44;
                const h = Math.max(280, Math.ceil(targetH));
                try {{
                        if (window.frameElement) {{
                        window.frameElement.style.height = h + 'px';
                        window.frameElement.setAttribute('height', String(h));
                        let p = window.frameElement.parentElement;
                        while (p && p !== document.parentElement && p.tagName !== 'SECTION') {{
                            if (p.style && p.style.height) {{ p.style.height = 'auto'; }}
                            p = p.parentElement;
                        }}
                    }}
                }} catch (e) {{}}
            }}
            function setMode(m) {{
                const card = document.getElementById('card');
                document.getElementById('btnDesk').classList.toggle('active', m === 'desktop');
                document.getElementById('btnMob').classList.toggle('active', m === 'mobile');
                card.classList.toggle('mobile', m === 'mobile');
                requestAnimationFrame(() => {{ syncHeight(); setTimeout(syncHeight, 260); }});
            }}
            function toggleLike() {{
                liked = !liked;
                const btn = document.getElementById('btnLike');
                const cnt = document.getElementById('likeCnt');
                btn.classList.toggle('liked', liked);
                cnt.textContent = liked ? '129' : '128';
            }}
            function pingAction(btn, label) {{
                const orig = btn.innerText;
                btn.innerText = label;
                setTimeout(() => {{ btn.innerText = orig; }}, 1100);
            }}
            async function copyText() {{
                const btn = document.getElementById('btnCopy');
                try {{
                    await navigator.clipboard.writeText(RAW_TEXT);
                }} catch (e) {{
                    const ta = document.createElement('textarea');
                    ta.value = RAW_TEXT;
                    document.body.appendChild(ta);
                    ta.select();
                    document.execCommand('copy');
                    document.body.removeChild(ta);
                }}
                btn.classList.add('copied');
                btn.innerText = '✓ Đã sao chép!';
                setTimeout(() => {{
                    btn.classList.remove('copied');
                    btn.innerText = '📋 Sao chép bài đăng';
                }}, 1800);
            }}
            window.addEventListener('load', syncHeight);
            if (window.ResizeObserver) {{
                new ResizeObserver(syncHeight).observe(document.getElementById('card'));
            }}
            setTimeout(syncHeight, 60);
            setTimeout(syncHeight, 320);
        </script>
    </body>
    </html>
    """
    components.html(widget_html, height=est_height, scrolling=False)


def render_post_editor_panel(selected_article: Optional[Dict[str, Any]]) -> Tuple[str, Dict[str, Any]]:
    """Render cột trái của Tab 2: Soạn thảo bài đăng và xem trước thực tế."""
    with st.container(border=True):
        render_clean_html(
            """
            <div class="panel-title">✍️ Xưởng Biên Tập Bài Đăng (AI Social Atelier)</div>
            <div class="panel-subtitle">Chọn nền tảng xuất bản, biên soạn tự động từ Gemini 3.8 Flash và kiểm soát dung lượng trực quan</div>
            """
        )

        if selected_article:
            st.caption(f"📰 **Nguồn tin đang chọn:** {selected_article.get('title', '')[:95]}")
        else:
            st.warning("Chưa có bài báo nguồn. Vui lòng chọn một bản tin ở Tab 1.")

        col_plat, col_style = st.columns([6, 6], gap="small")
        with col_plat:
            platform = st.radio(
                "Nền tảng xuất bản:",
                options=["facebook", "threads"],
                format_func=lambda x: "🔵 Facebook Post" if x == "facebook" else "⚫ Threads / X",
                horizontal=True,
                key="social_platform",
            )
        with col_style:
            style = st.selectbox(
                "Phong cách thể hiện:",
                options=["trend", "deep", "brief"],
                format_func=lambda x: "🔥 Bắt trend & viral" if x == "trend" else ("💡 Phân tích chuyên sâu" if x == "deep" else "⚡ Tin vắn cô đọng"),
                key="social_style",
            )

        btn_generate = st.button("✨ Soạn Bài Viết Tối Ưu", type="primary", key="btn_script_action", width="stretch")

        if btn_generate:
            if not selected_article:
                st.warning("Vui lòng chọn một bài báo nguồn trước khi tạo bài đăng!")
            else:
                plat_label = "Facebook" if platform == "facebook" else "Threads"
                with st.spinner(f"Đang gọi Gemini 3.8 Flash biên soạn bài đăng chuẩn {plat_label}..."):
                    try:
                        title = selected_article.get("title", "")
                        summary = selected_article.get("summary", "")
                        source_full = f"{title} {summary}".strip()

                        post_res = generate_social_post(
                            title=title,
                            summary=summary,
                            platform=platform,
                            style=style,
                        )
                        v1_eval = evaluate_post(post_res, source_full, platform=platform)

                        st.session_state.v1_post = post_res
                        st.session_state.v1_eval = v1_eval
                        st.session_state.v2_post = None
                        st.session_state.v2_eval = None
                        st.session_state.current_post_data = post_res
                        st.session_state["editorial_editor_textarea"] = post_res.get("full_post", "")

                        st.toast(f"Đã soạn xong bài {plat_label} (v1)! Điểm: {v1_eval.get('overall_score', 0)}/100", icon="✍️")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi khi soạn thảo bài đăng: {e}")

        content = st.text_area(
            "Nội dung bài đăng (Có thể chỉnh sửa trực tiếp):",
            height=215,
            placeholder="Nội dung bài đăng tối ưu sẽ xuất hiện tại đây sau khi bạn bấm '✨ Soạn Bài Viết Tối Ưu'...",
            key="editorial_editor_textarea",
        )

        words_now = len((content or "").split())
        ideal_min, ideal_max = (90, 220) if platform == "facebook" else (35, 85)
        ideal_hint = f"{ideal_min}–{ideal_max} từ"
        fill_pct = min(100.0, max(0.0, (words_now / ideal_max) * 100.0))
        bar_color = "#10B981" if ideal_min <= words_now <= ideal_max else ("#F59E0B" if words_now < ideal_min else "#F43F5E")

        render_clean_html(
            f"""
            <div class="word-meter-wrap">
                <div style="display:flex;justify-content:space-between;align-items:center;font-size:0.75rem;color:#64748B;">
                    <span>📝 Dung lượng: <strong style="color:#0F172A;">{words_now} từ</strong></span>
                    <span>Chuẩn {platform.title()}: <strong>{ideal_hint}</strong></span>
                </div>
                <div class="word-meter-bar-bg">
                    <div class="word-meter-bar-fill" style="width:{fill_pct:.1f}%;background:{bar_color};"></div>
                </div>
            </div>
            """
        )

        current_post = st.session_state.current_post_data
        if content and (not current_post or current_post.get("full_post") != content):
            current_post["full_post"] = content

    if content.strip():
        with st.container(border=True):
            render_clean_html(
                """
                <div class="panel-title">📱 Giao Diện Bài Đăng Thực Tế (Interactive Preview)</div>
                <div class="panel-subtitle">Chuyển đổi khung nhìn Desktop/Mobile, tương tác nút Thích và sao chép bài viết với hình ảnh trực quan</div>
                """
            )
            tags = current_post.get("hashtags", []) if current_post else []
            ref_thumb = selected_article.get("thumbnail_url") if selected_article else ""
            _render_interactive_social_preview(content.strip(), platform, tags, ref_thumb)

    return content, current_post
