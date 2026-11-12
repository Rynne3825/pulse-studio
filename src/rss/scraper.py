"""Thu thập tin tức xu hướng (M1) qua RSS 4 tòa soạn Việt Nam."""

import html
import logging
import re
from typing import Any, List, TypedDict

import feedparser
import requests

logger = logging.getLogger(__name__)

MAX_RSS_BYTES = 2 * 1024 * 1024
HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}


class ArticleItem(TypedDict):
    title: str
    summary: str
    link: str
    thumbnail_url: str
    published_at: str
    source: str
    topic_category: int
    topic_name: str


RSS_CONFIG = {
    "CongNghe": {
        "url": "https://genk.vn/rss/tin-ict.rss",
        "fallback_url": "https://genk.vn/rss/home.rss",
        "source": "GenK",
        "topic_category": 1,
        "name": "Công nghệ & Số hóa",
    },
    "GiaiTri": {
        "url": "https://kenh14.vn/star.rss",
        "fallback_url": "https://kenh14.vn/rss/home.rss",
        "source": "Kenh14",
        "topic_category": 0,
        "name": "Giải trí & Showbiz",
    },
    "KinhDoanh": {
        "url": "https://vnexpress.net/rss/kinh-doanh.rss",
        "fallback_url": "https://vnexpress.net/rss/thoi-su.rss",
        "source": "VnExpress",
        "topic_category": 2,
        "name": "Kinh doanh & Tài chính",
    },
    "DoiSong": {
        "url": "https://tuoitre.vn/rss/doi-song.rss",
        "fallback_url": "https://tuoitre.vn/rss/nhip-song-tre.rss",
        "source": "Tuổi Trẻ",
        "topic_category": 3,
        "name": "Đời sống & Xã hội",
    },
}


def clean_html_text(raw_html: str) -> str:
    """Giải mã HTML entities trước rồi loại bỏ thẻ HTML và khoảng trắng thừa."""
    if not isinstance(raw_html, str):
        return ""
    text = re.sub(r"<[^>]+>", " ", html.unescape(raw_html))
    return re.sub(r"\s+", " ", text).strip()


def get_high_res_image_url(url: str) -> str:
    """Loại bỏ tiền tố /zoom/W_H/ của CDN báo chí để lấy ảnh gốc phân giải cao."""
    if not isinstance(url, str) or not url.strip():
        return ""
    return re.sub(r"/zoom/\d+_\d+/", "/", url.strip())


def _attr(obj: Any, key: str) -> str:
    val = obj.get(key, "") if isinstance(obj, dict) else getattr(obj, key, "")
    return str(val or "").strip()


def _is_http(url: str) -> bool:
    return url.startswith(("http://", "https://"))


def extract_thumbnail_url(entry: Any, raw_summary: str = "") -> str:
    """Trích xuất URL ảnh gốc theo thứ tự: media_content > enclosures > <img> trong summary."""
    url = ""
    if entry:
        media_list = entry.get("media_content") if isinstance(entry, dict) else getattr(entry, "media_content", None)
        if isinstance(media_list, (list, tuple)):
            url = next((_attr(m, "url") for m in media_list if _is_http(_attr(m, "url"))), "")

        if not url:
            enc_list = entry.get("enclosures") if isinstance(entry, dict) else getattr(entry, "enclosures", None)
            if isinstance(enc_list, (list, tuple)):
                url = next(
                    (
                        _attr(e, "href")
                        for e in enc_list
                        if "image" in _attr(e, "type").lower() and _is_http(_attr(e, "href"))
                    ),
                    "",
                )

    if not url and isinstance(raw_summary, str) and raw_summary:
        for match in re.finditer(r'<img[^>]+src=["\']([^"\']+)["\']', raw_summary, re.IGNORECASE):
            candidate = html.unescape(match.group(1)).strip()
            if _is_http(candidate):
                url = candidate
                break

    return get_high_res_image_url(url) if _is_http(url) else ""


def fetch_trending_news(topic: str = "CongNghe", limit: int = 15) -> List[ArticleItem]:
    """Cào tin xu hướng theo chuyên mục trong RSS_CONFIG (tự động thử fallback URL)."""
    if not isinstance(topic, str) or topic not in RSS_CONFIG:
        valid = ", ".join(f"'{k}'" for k in RSS_CONFIG)
        raise ValueError(f"Chủ đề không hợp lệ! Vui lòng chọn một trong: {valid}.")
    if limit <= 0:
        return []

    cfg = RSS_CONFIG[topic]
    feed = None
    for target_url in (cfg["url"], cfg["fallback_url"]):
        try:
            resp = requests.get(target_url, headers=HTTP_HEADERS, timeout=6)
            if resp.status_code == 200 and len(resp.content) <= MAX_RSS_BYTES:
                parsed = feedparser.parse(resp.content)
                if getattr(parsed, "entries", None):
                    feed = parsed
                    break
        except Exception as exc:
            logger.warning("Lỗi tải RSS %s: %s", target_url, exc)

    if not feed or not getattr(feed, "entries", None):
        return []

    articles: List[ArticleItem] = []
    for entry in feed.entries[:limit]:
        title = clean_html_text(entry.get("title", ""))
        if len(title) <= 10:
            continue
        raw_summary = entry.get("summary", "")
        articles.append({
            "title": title,
            "summary": clean_html_text(raw_summary),
            "link": entry.get("link", ""),
            "thumbnail_url": extract_thumbnail_url(entry, raw_summary),
            "published_at": entry.get("published", ""),
            "source": cfg["source"],
            "topic_category": cfg["topic_category"],
            "topic_name": topic,
        })
    return articles
