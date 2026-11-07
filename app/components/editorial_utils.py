"""
THE PULSE EDITORIAL - TIỆN ÍCH DÙNG CHUNG (UTILITIES)
Chứa các hàm tiện ích kiểm tra an toàn URL và xử lý render HTML chuẩn xác.
"""

import re
from urllib.parse import urlsplit
import streamlit as st

DISALLOWED_HOSTS = {"127.0.0.1", "localhost", "0.0.0.0", "169.254.169.254"}


def is_safe_url(url: str) -> bool:
    """Kiểm tra URL hợp lệ tránh mã độc javascript:, data: và SSRF."""
    if not isinstance(url, str) or not url.strip():
        return False
    try:
        parts = urlsplit(url.strip())
        if parts.scheme not in ("http", "https"):
            return False
        hostname = (parts.hostname or "").lower()
        if not hostname or hostname in DISALLOWED_HOSTS or hostname.startswith("192.168."):
            return False
        return True
    except Exception:
        return False


def render_clean_html(raw_html: str) -> None:
    """
    Render HTML an toàn, loại bỏ thẻ nhúng thực thi mã và
    triệt tiêu lỗi Markdown hiểu nhầm thụt lề thành code block.
    """
    cleaned = re.sub(r"<!--[\s\S]*?-->", "", raw_html)
    cleaned = re.sub(r"<\s*(script|iframe|embed|object|meta|link)[^>]*>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"on\w+\s*=", "data-blocked=", cleaned, flags=re.IGNORECASE)
    cleaned_lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    st.markdown("".join(cleaned_lines), unsafe_allow_html=True)
