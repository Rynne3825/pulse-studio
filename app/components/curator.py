"""
THE PULSE STUDIO - BAN GIÁM TUYỂN (CURATOR), TỐI ƯU KHÉP KÍN & PHÒNG THÍ NGHIỆM KHÓA LUẬN
- Cột phải Tab 2: SVG Radial Gauge, SVG Radar 4 trục, Altair Bar Chart, Checklist & Nút Tối Ưu Hạng S
- Tab 3: Thực nghiệm định lượng v1 vs v2, bảng số liệu đối chứng & xuất file báo cáo CSV/Markdown
"""

import json
import html
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

import pandas as pd
import streamlit as st

from src.ai.generator import refine_post
from src.eval.scorer import evaluate_post
from app.components.utils import (
    render_clean_html,
    is_positive_feedback,
    resolve_active_evaluation,
    STANDARD_PILLARS,
)
from app.components.charts import (
    build_radial_gauge_html,
    build_radar_svg_html,
    build_four_pillars_altair,
    build_experiment_trend_altair,
)

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
EXPERIMENT_HISTORY_PATH = PROJECT_ROOT / "data" / "experiment_history.json"


def load_experiment_history() -> List[Dict[str, Any]]:
    """Nạp lịch sử thực nghiệm từ file JSON."""
    if not EXPERIMENT_HISTORY_PATH.exists():
        return []
    try:
        with open(EXPERIMENT_HISTORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as exc:
        logger.warning("Không thể đọc experiment_history.json: %s", exc)
        return []


def save_experiment_record(record: Dict[str, Any]) -> None:
    """Lưu bổ sung một bản ghi thực nghiệm vào data/experiment_history.json."""
    try:
        EXPERIMENT_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        existing = load_experiment_history()
        existing.append(record)
        with open(EXPERIMENT_HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        logger.warning("Không thể lưu experiment_history.json: %s", exc)


def clear_experiment_history() -> None:
    """Xóa nhật ký thực nghiệm khi người dùng muốn thiết lập lại."""
    st.session_state.experiment_history = []
    try:
        if EXPERIMENT_HISTORY_PATH.exists():
            EXPERIMENT_HISTORY_PATH.unlink()
    except Exception as exc:
        logger.warning("Không thể xóa experiment_history.json: %s", exc)


def _sanitize_csv_cell(val: Any) -> Any:
    """Trung hòa nguy cơ CSV Formula Injection khi xuất file mở bằng Excel."""
    if isinstance(val, str) and val and val[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{val}"
    return val


def format_markdown_report(history: List[Dict[str, Any]]) -> str:
    """Tạo bảng Markdown học thuật phục vụ chương thực nghiệm khóa luận."""
    lines = [
        "# Báo Cáo Thực Nghiệm Tối Ưu Hóa Bài Đăng Mạng Xã Hội (The Pulse Studio)",
        "",
        "| STT | Thời gian | Chuyên mục | Tiêu đề bài báo | Nền tảng | Điểm v1 | Điểm v2 | Δ Cải thiện |",
        "|---:|---|---|---|---|---:|---:|---:|",
    ]
    for idx, row in enumerate(history, 1):
        title_clean = str(row.get("article_title", "")).replace("|", "/")
        delta = float(row.get("delta", 0.0))
        lines.append(
            f"| {idx} | {row.get('timestamp', '')} | {row.get('topic', '')} | "
            f"{title_clean} | {str(row.get('platform', '')).upper()} | "
            f"{row.get('score_v1', 0.0)} | {row.get('score_v2', 0.0)} | {delta:+.1f} |"
        )
    if history:
        avg_v1 = round(sum(float(r.get("score_v1", 0.0)) for r in history) / len(history), 2)
        avg_v2 = round(sum(float(r.get("score_v2", 0.0)) for r in history) / len(history), 2)
        avg_delta = round(avg_v2 - avg_v1, 2)
        lines.extend([
            "",
            f"**Thống kê tổng quan ({len(history)} mẫu thử):** Điểm trung bình trước tối ưu = **{avg_v1}**, "
            f"sau tối ưu = **{avg_v2}**, mức cải thiện trung bình = **{avg_delta:+.2f} điểm**.",
        ])
    return "\n".join(lines)


def render_curator_panel(
    content: str,
    selected_article: Optional[Dict[str, Any]],
    topic_key: str,
    post_data: Optional[Dict[str, Any]] = None,
) -> None:
    """Render cột phải của Tab 2: Vòng đo điểm, Radar mạng nhện, Checklist & Tối ưu khép kín."""
    if "experiment_history" not in st.session_state:
        st.session_state.experiment_history = load_experiment_history()

    platform = st.session_state.get("social_platform", "facebook")
    source_title = selected_article.get("title", "") if selected_article else ""
    source_summary = selected_article.get("summary", "") if selected_article else ""
    source_full = f"{source_title} {source_summary}".strip()

    v1_post = st.session_state.get("v1_post")
    v1_eval = st.session_state.get("v1_eval")
    v2_post = st.session_state.get("v2_post")
    v2_eval = st.session_state.get("v2_eval")
    clean_content = (content or "").strip()

    active_eval, delta_live = resolve_active_evaluation(content, selected_article)
    overall_score = float(active_eval.get("overall_score", 0.0))
    grade = active_eval.get("grade", "C")
    grade_title = active_eval.get("grade_title", "CẦN TỐI ƯU")
    grade_color = active_eval.get("grade_color", "#F43F5E")
    breakdown = active_eval.get("breakdown", {})
    metrics = active_eval.get("metrics", {})
    checklist = active_eval.get("actionable_checklist", [])

    with st.container(border=True):
        if clean_content and overall_score >= 85.0:
            delta_tag = f" (+{delta_live:.1f} điểm)" if (delta_live is not None and delta_live > 0) else ""
            render_clean_html(
                f"""
                <div class="grade-s-celebration">
                    <div style="font-size:0.84rem;font-weight:700;color:#065F46;">
                        🏆 CHÚC MỪNG! Bài viết đã đạt chuẩn HẠNG S · SIÊU TIỀM NĂNG LAN TỎA{delta_tag}
                    </div>
                    <span style="background:#10B981;color:#FFFFFF;font-size:0.72rem;font-weight:700;padding:4px 12px;border-radius:999px;white-space:nowrap;flex-shrink:0;">
                        READY TO PUBLISH
                    </span>
                </div>
                """
            )

        plat_badge = "🔵 Facebook Post" if platform == "facebook" else "⚫ Threads / X"
        version_badge = "v2 · ĐÃ TỐI ƯU" if (v2_eval and active_eval is v2_eval) else ("v1 · BẢN NHÁP" if clean_content else "CHƯA CÓ BÀI VIẾT")

        render_clean_html(
            f"""
            <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:0.5rem;flex-wrap:wrap;margin-bottom:0.65rem;">
                <div>
                    <div class="panel-title">🎯 Ban Giám Tuyển &amp; Đo Lường Tường Minh (XAI)</div>
                    <div class="panel-subtitle">Chấm điểm trực quan {html.escape(plat_badge)} trên 4 trụ cột toán học</div>
                </div>
                <span style="background:#EEF2FF;color:#4338CA;font-size:0.72rem;font-weight:700;padding:4px 10px;border-radius:999px;border:1px solid #C7D2FE;">
                    {version_badge}
                </span>
            </div>
            """
        )

        col_gauge, col_radar = st.columns([5, 7], gap="small")
        with col_gauge:
            render_clean_html(build_radial_gauge_html(overall_score, grade, grade_title, grade_color, version_badge))
        with col_radar:
            v1_b = v1_eval.get("breakdown") if (v1_eval and v2_eval) else None
            render_clean_html(build_radar_svg_html(breakdown, breakdown_v1=v1_b))

        v1_break = v1_eval.get("breakdown") if (v1_eval and v2_eval) else None
        st.altair_chart(build_four_pillars_altair(breakdown, breakdown_v1=v1_break), width="stretch")

        hook_kws = metrics.get("hook_keywords", [])
        cta_kws = metrics.get("cta_keywords", [])
        hook_str = ", ".join(hook_kws) if hook_kws else "Chưa có"
        cta_str = ", ".join(cta_kws) if cta_kws else "Chưa có"

        render_clean_html(
            f"""
            <div class="telemetry-grid">
                <div class="telemetry-tile">
                    <div class="telemetry-k">📝 Độ dài thực tế</div>
                    <div class="telemetry-v">{metrics.get('word_count', 0)} từ</div>
                </div>
                <div class="telemetry-tile">
                    <div class="telemetry-k">📐 Cosine bám tin gốc</div>
                    <div class="telemetry-v">{metrics.get('cosine_raw', 0.0):.3f}</div>
                </div>
                <div class="telemetry-tile">
                    <div class="telemetry-k">⚡ Từ khóa Hook</div>
                    <div class="telemetry-v" title="{html.escape(hook_str)}">{html.escape(hook_str)}</div>
                </div>
                <div class="telemetry-tile">
                    <div class="telemetry-k">💬 Từ khóa CTA</div>
                    <div class="telemetry-v" title="{html.escape(cta_str)}">{html.escape(cta_str)}</div>
                </div>
            </div>
            """
        )

        render_clean_html(
            """
            <div style="margin-top:1rem;margin-bottom:0.45rem;">
                <div class="panel-title">⚡ Vòng Lặp Phản Hồi &amp; Tối Ưu Khép Kín</div>
                <div class="panel-subtitle">Hệ thống tự động phát hiện khuyến nghị và yêu cầu Gemini 3.8 Flash viết lại đạt Hạng S</div>
            </div>
            """
        )

        for item in checklist:
            is_good = is_positive_feedback(item)
            icon = "✅" if is_good else "💡"
            bg_color = "#F0FDF4" if is_good else "#FFFBEB"
            border_color = "#BBF7D0" if is_good else "#FDE68A"
            text_color = "#166534" if is_good else "#92400E"
            render_clean_html(
                f"""
                <div class="checklist-pill" style="background:{bg_color};border:1px solid {border_color};color:{text_color};">
                    {icon} {html.escape(str(item))}
                </div>
                """
            )

        btn_optimize = st.button("⚡ Tự Động Tối Ưu Lên Hạng S", type="primary", key="btn_refine_post", width="stretch")

        if btn_optimize:
            if not clean_content:
                st.warning("Vui lòng soạn hoặc nhập nội dung bài viết trước khi tối ưu hóa!")
            else:
                with st.spinner("Đang chạy vòng lặp phản hồi khép kín cùng Gemini 3.8 Flash để nâng cấp bài đăng..."):
                    try:
                        baseline_eval = v1_eval if v1_eval else active_eval
                        if not v1_eval:
                            st.session_state.v1_post = post_data or {"full_post": clean_content, "platform": platform}
                            st.session_state.v1_eval = baseline_eval

                        flaws = [it for it in checklist if not is_positive_feedback(it)]
                        if not flaws:
                            flaws = checklist

                        v2_res = refine_post(
                            original_post=clean_content,
                            feedback_checklist=flaws,
                            platform=platform,
                            title=source_title,
                            summary=source_summary,
                        )
                        v2_eval_res = evaluate_post(v2_res, source_full, platform=platform)

                        st.session_state.v2_post = v2_res
                        st.session_state.v2_eval = v2_eval_res
                        st.session_state.current_post_data = v2_res
                        st.session_state["_pending_editor_text"] = v2_res.get("full_post", "")

                        score_v1 = float(baseline_eval.get("overall_score", 0.0))
                        score_v2 = float(v2_eval_res.get("overall_score", 0.0))
                        delta = round(score_v2 - score_v1, 1)

                        record = {
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "topic": topic_key,
                            "article_title": (source_title or "Bài viết tùy chỉnh")[:60],
                            "platform": platform,
                            "score_v1": score_v1,
                            "score_v2": score_v2,
                            "delta": delta,
                        }
                        st.session_state.experiment_history.append(record)
                        save_experiment_record(record)

                        st.toast(f"Đã tối ưu lên v2! Điểm: {score_v1} → {score_v2} ({delta:+.1f})", icon="⚡")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Lỗi trong quá trình tối ưu khép kín: {exc}")

        if v1_eval and v2_eval:
            s1_tot = float(v1_eval.get("overall_score", 0.0))
            s2_tot = float(v2_eval.get("overall_score", 0.0))
            delta_tot = round(s2_tot - s1_tot, 1)
            pill_cls = "delta-pill-pos" if delta_tot > 0 else "delta-pill-neutral"

            render_clean_html(
                f"""
                <div style="margin-top:1rem;margin-bottom:0.5rem;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.5rem;">
                    <strong style="font-size:0.88rem;color:#0F172A;">📊 Đối Chiếu Trước vs Sau Tối Ưu (Δ Score)</strong>
                    <span class="{pill_cls}">{s1_tot:.1f} → {s2_tot:.1f} ({delta_tot:+.1f} điểm)</span>
                </div>
                """
            )

            b1 = v1_eval.get("breakdown", {})
            b2 = v2_eval.get("breakdown", {})
            diff_rows = [
                {
                    "Trụ cột đánh giá": label,
                    "v1 (Trước)": float(b1.get(key, 0.0)),
                    "v2 (Sau)": float(b2.get(key, 0.0)),
                    "Δ Cải thiện": round(float(b2.get(key, 0.0)) - float(b1.get(key, 0.0)), 1),
                }
                for label, key in STANDARD_PILLARS
            ]
            diff_rows.append({
                "Trụ cột đánh giá": "⭐ TỔNG ĐIỂM VIRAL",
                "v1 (Trước)": s1_tot,
                "v2 (Sau)": s2_tot,
                "Δ Cải thiện": delta_tot,
            })
            st.dataframe(
                pd.DataFrame(diff_rows),
                hide_index=True,
                width="stretch",
                column_config={
                    "v1 (Trước)": st.column_config.NumberColumn(format="%.1f"),
                    "v2 (Sau)": st.column_config.NumberColumn(format="%.1f"),
                    "Δ Cải thiện": st.column_config.NumberColumn(format="%+.1f"),
                },
            )

            if v1_post and v2_post:
                with st.expander("🔍 So sánh Hook & CTA (Trước v1 vs Sau v2)", expanded=False):
                    c1, c2 = st.columns(2, gap="small")
                    with c1:
                        st.markdown("**Bản nháp v1:**")
                        st.caption(f"Hook: {v1_post.get('hook', '')}")
                        st.caption(f"CTA: {v1_post.get('cta', '')}")
                    with c2:
                        st.markdown("**Bản tối ưu v2:**")
                        st.caption(f"Hook: {v2_post.get('hook', '')}")
                        st.caption(f"CTA: {v2_post.get('cta', '')}")


def render_experiment_lab_tab() -> None:
    """Render Tab 3: Biểu đồ tăng trưởng thực nghiệm, bảng lịch sử & xuất file báo cáo khóa luận."""
    if "experiment_history" not in st.session_state:
        st.session_state.experiment_history = load_experiment_history()

    history = st.session_state.get("experiment_history", [])

    with st.container(border=True):
        col_hd, col_clr = st.columns([9.5, 2.5], gap="small")
        with col_hd:
            render_clean_html(
                """
                <div class="panel-title">🧪 Phòng Thí Nghiệm &amp; Nhật Ký Thực Nghiệm Khóa Luận</div>
                <div class="panel-subtitle">Lưu vết định lượng mức cải thiện Δ Score qua từng lượt chạy để đưa vào Chương Thực Nghiệm</div>
                """
            )
        with col_clr:
            if history and st.button("🗑️ Xóa Nhật Ký", type="secondary", key="btn_clear_history", width="stretch"):
                clear_experiment_history()
                st.toast("Đã làm sạch nhật ký thực nghiệm!", icon="🗑️")
                st.rerun()

        if not history:
            st.info(
                "Chưa có dữ liệu thực nghiệm nào. Hãy chọn một bài báo ở Tab 1, sang Tab 2 soạn bài nháp (v1) rồi bấm "
                "'⚡ Tự Động Tối Ưu Lên Hạng S' để hệ thống tự động ghi nhận bảng số liệu đối chứng tại đây."
            )
            return

        avg_v1 = round(sum(float(r.get("score_v1", 0.0)) for r in history) / len(history), 2)
        avg_v2 = round(sum(float(r.get("score_v2", 0.0)) for r in history) / len(history), 2)
        avg_delta = round(avg_v2 - avg_v1, 2)

        render_clean_html(
            f"""
            <div class="kpi-grid" style="margin-top:0.5rem;margin-bottom:0.2rem;">
                <div class="kpi-card" style="--kpi-accent:#4F46E5;">
                    <div class="kpi-label"><span>🧪 Tổng mẫu thử nghiệm</span></div>
                    <div class="kpi-value">{len(history)} bài</div>
                </div>
                <div class="kpi-card" style="--kpi-accent:#64748B;">
                    <div class="kpi-label"><span>📝 Điểm TB Trước (v1)</span></div>
                    <div class="kpi-value">{avg_v1:.1f} đ</div>
                </div>
                <div class="kpi-card" style="--kpi-accent:#10B981;">
                    <div class="kpi-label"><span>🏆 Điểm TB Sau (v2)</span></div>
                    <div class="kpi-value" style="color:#059669;">{avg_v2:.1f} đ</div>
                </div>
                <div class="kpi-card" style="--kpi-accent:#6366F1;">
                    <div class="kpi-label"><span>📈 Mức tăng trưởng TB (Δ)</span></div>
                    <div class="kpi-value" style="color:#4F46E5;">{avg_delta:+.1f} đ</div>
                </div>
            </div>
            """
        )

    col_chart, col_table = st.columns([6, 6], gap="large")
    with col_chart:
        with st.container(border=True):
            render_clean_html(
                """
                <div class="panel-title">📈 Biểu Đồ Cải Thiện Điểm Số (v1 → v2)</div>
                <div class="panel-subtitle">Đường nét đứt màu xanh thể hiện ngưỡng chuẩn Hạng S (85 điểm)</div>
                """
            )
            st.altair_chart(build_experiment_trend_altair(history), width="stretch")

    with col_table:
        with st.container(border=True):
            render_clean_html(
                """
                <div class="panel-title">📋 Bảng Số Liệu Đối Chứng &amp; Xuất File Báo Cáo</div>
                <div class="panel-subtitle">Tải trực tiếp file CSV (Excel) hoặc Markdown để dán vào báo cáo khóa luận</div>
                """
            )
            df_hist = pd.DataFrame(history)
            df_display = pd.DataFrame([
                {
                    "Thời gian": str(r.get("timestamp", ""))[11:16] or str(r.get("timestamp", "")),
                    "Chủ đề": str(r.get("topic", "")),
                    "Tiêu đề tin gốc": str(r.get("article_title", ""))[:38] + ("…" if len(str(r.get("article_title", ""))) > 38 else ""),
                    "Kênh": str(r.get("platform", "")).upper()[:2],
                    "v1": float(r.get("score_v1", 0.0)),
                    "v2": float(r.get("score_v2", 0.0)),
                    "Δ": round(float(r.get("delta", 0.0)), 1),
                }
                for r in history
            ])
            st.dataframe(
                df_display,
                hide_index=True,
                width="stretch",
                column_config={
                    "v1": st.column_config.NumberColumn(format="%.1f"),
                    "v2": st.column_config.ProgressColumn("v2", min_value=0, max_value=100, format="%.1f"),
                    "Δ": st.column_config.NumberColumn(format="%+.1f"),
                },
            )

            df_safe_csv = df_hist.copy()
            for col in df_safe_csv.select_dtypes(include=["object"]).columns:
                df_safe_csv[col] = df_safe_csv[col].map(_sanitize_csv_cell)
            csv_bytes = df_safe_csv.to_csv(index=False).encode("utf-8-sig")
            md_str = format_markdown_report(history)

            col_dl1, col_dl2 = st.columns(2, gap="small")
            with col_dl1:
                st.download_button(
                    label="📥 Tải Bảng Thực Nghiệm (.CSV)",
                    data=csv_bytes,
                    file_name="experiment_history.csv",
                    mime="text/csv",
                    key="btn_download_csv",
                    width="stretch",
                )
            with col_dl2:
                st.download_button(
                    label="📥 Tải Báo Cáo Kỷ Yếu (.MD)",
                    data=md_str.encode("utf-8"),
                    file_name="experiment_report.md",
                    mime="text/markdown",
                    key="btn_download_md",
                    width="stretch",
                )
