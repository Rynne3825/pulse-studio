"""
THE PULSE STUDIO - TIỆN ÍCH DÙNG CHUNG & ĐÁNH GIÁ TRẠNG THÁI
- Bảo mật URL ảnh & liên kết nguồn (anti-SSRF / anti-XSS)
- Render HTML sạch không dính lỗi Markdown thụt lề
- Bóc tách thành phần bài viết và giải quyết đánh giá v1 / v2 đang hiệu lực
"""

import ipaddress
import re
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlsplit
import streamlit as st

from src.eval.scorer import evaluate_post

DISALLOWED_HOSTS = {"localhost", "localhost.localdomain", "metadata.google.internal"}

STANDARD_PILLARS = [
    ("1. Hook (25%)", "hook_score"),
    ("2. Độ bám tin Cosine (35%)", "trend_similarity_score"),
    ("3. Cấu trúc & Độ dài (20%)", "pacing_score"),
    ("4. Kêu gọi CTA (20%)", "cta_score"),
]


def _is_blocked_ip(ip_str: str) -> bool:
    try:
        ip_obj = ipaddress.ip_address(ip_str)
        return (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_link_local
            or ip_obj.is_multicast
            or ip_obj.is_reserved
            or ip_obj.is_unspecified
        )
    except ValueError:
        return False


def is_safe_url(url: str) -> bool:
    """Kiểm tra URL hợp lệ tránh mã độc javascript:, data: và SSRF tới IP nội bộ."""
    if not isinstance(url, str) or not url.strip():
        return False
    try:
        parts = urlsplit(url.strip())
        if parts.scheme not in ("http", "https"):
            return False
        if parts.username or parts.password:
            return False
        if parts.port not in (None, 80, 443):
            return False
        hostname = (parts.hostname or "").lower().strip(".")
        if not hostname or hostname in DISALLOWED_HOSTS:
            return False
        if _is_blocked_ip(hostname):
            return False
        return True
    except Exception:
        return False


def render_clean_html(raw_html: str) -> None:
    """Render HTML an toàn, triệt tiêu script/iframe nội tuyến và lỗi Markdown."""
    cleaned = re.sub(r"<!--[\s\S]*?-->", "", raw_html)
    cleaned = re.sub(r"<\s*(script|iframe|embed|object|meta|link)[^>]*>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"on\w+\s*=", "data-blocked=", cleaned, flags=re.IGNORECASE)
    cleaned_lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    st.markdown("".join(cleaned_lines), unsafe_allow_html=True)


def is_positive_feedback(item: str) -> bool:
    """Phân loại mục phản hồi thuộc nhóm đạt chuẩn (✅) hay cần cải thiện (💡)."""
    lower = str(item).lower()
    negative_cues = (
        "gợi ý:", "thiếu", "hơi dài", "hơi ngắn",
        "quá dài", "quá ngắn", "xa rời", "chưa có", "vượt ngưỡng",
    )
    if any(cue in lower for cue in negative_cues):
        return False
    positive_cues = (
        "hoàn hảo", "lý tưởng", "súc tích", "bám sát", "mạch lạc",
        "chứa từ khóa", "kêu gọi tương tác", "đặt câu hỏi", "có câu hỏi",
    )
    return any(cue in lower for cue in positive_cues)


def extract_post_parts(text: str) -> Dict[str, str]:
    """Tách tương đối hook, body, cta từ văn bản thuần do người dùng chỉnh sửa."""
    clean = (text or "").strip()
    if not clean:
        return {"hook": "", "body": "", "cta": "", "full_post": ""}

    lines = [ln.strip() for ln in clean.splitlines() if ln.strip()]
    non_tag_lines: List[str] = []
    for ln in lines:
        tokens = ln.split()
        if tokens and all(tok.startswith("#") for tok in tokens):
            continue
        non_tag_lines.append(ln)

    core_text = "\n".join(non_tag_lines) if non_tag_lines else clean
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", core_text) if s.strip()]

    hook = sentences[0] if sentences else clean[:60]
    cta = sentences[-1] if len(sentences) > 1 else ""
    body = " ".join(sentences[1:-1]) if len(sentences) > 2 else core_text
    return {
        "hook": hook,
        "body": body,
        "cta": cta,
        "full_post": clean,
    }


def resolve_active_evaluation(
    content: str,
    selected_article: Optional[Dict[str, Any]],
) -> Tuple[Dict[str, Any], Optional[float]]:
    """Xác định bộ đánh giá đang hiệu lực (v2, v1, hoặc bài viết đang sửa tay)."""
    platform = st.session_state.get("social_platform", "facebook")
    source_title = selected_article.get("title", "") if selected_article else ""
    source_summary = selected_article.get("summary", "") if selected_article else ""
    source_full = f"{source_title} {source_summary}".strip()

    v1_post = st.session_state.get("v1_post")
    v1_eval = st.session_state.get("v1_eval")
    v2_post = st.session_state.get("v2_post")
    v2_eval = st.session_state.get("v2_eval")

    clean_content = (content or "").strip()

    if v2_post and v2_eval and clean_content == str(v2_post.get("full_post", "")).strip():
        delta = (
            round(float(v2_eval.get("overall_score", 0.0)) - float(v1_eval.get("overall_score", 0.0)), 1)
            if v1_eval
            else None
        )
        return v2_eval, delta

    if v1_post and v1_eval and clean_content == str(v1_post.get("full_post", "")).strip():
        return v1_eval, None

    if clean_content:
        parsed_parts = extract_post_parts(clean_content)
        parsed_parts["platform"] = platform
        return evaluate_post(parsed_parts, source_full, platform=platform), None

    empty_eval = evaluate_post(
        {"hook": "", "body": "", "cta": "", "full_post": "", "platform": platform},
        source_full,
        platform=platform,
    )
    empty_eval["overall_score"] = 0.0
    empty_eval["breakdown"] = {
        "hook_score": 0.0,
        "trend_similarity_score": 0.0,
        "pacing_score": 0.0,
        "cta_score": 0.0,
    }
    return empty_eval, None
