"""
Giai đoạn 4: Thu thập tin tức xu hướng (Trending News Scraper) qua giao thức RSS.
Nguồn dữ liệu:
- Giải trí (Showbiz): Kenh14 Star (https://kenh14.vn/star.rss)
- Công nghệ & Số hóa: GenK ICT (https://genk.vn/rss/tin-ict.rss)
"""

import re
import html
import logging
import requests
import feedparser
from typing import List, Dict, Any
try:
    from typing import TypedDict
except ImportError:
    from typing_extensions import TypedDict


class ArticleItem(TypedDict):
    title: str
    summary: str
    link: str
    thumbnail_url: str
    published_at: str
    source: str
    topic_category: int
    topic_name: str


logger = logging.getLogger(__name__)

# Danh mục các kênh RSS chính thức tương ứng 2 lĩnh vực
RSS_CONFIG = {
    "GiaiTri": {
        "url": "https://kenh14.vn/star.rss",
        "fallback_url": "https://kenh14.vn/rss/home.rss",
        "source": "Kenh14",
        "topic_category": 0,
        "name": "Giải trí & Showbiz"
    },
    "CongNghe": {
        "url": "https://genk.vn/rss/tin-ict.rss",
        "fallback_url": "https://genk.vn/rss/home.rss",
        "source": "GenK",
        "topic_category": 1,
        "name": "Công nghệ & Số hóa"
    }
}

# Header giả lập trình duyệt để tránh bị chặn IP
HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}


def clean_html_text(raw_html: str) -> str:
    """Loại bỏ thẻ HTML và chuẩn hóa thực thể ký tự."""
    if not isinstance(raw_html, str):
        return ""
    # Xóa các thẻ HTML <tag>
    text = re.sub(r"<[^>]+>", " ", raw_html)
    # Giải mã HTML entities như &amp;, &quot;, &nbsp;
    text = html.unescape(text)
    # Xóa khoảng trắng thừa
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def get_high_res_image_url(url: str) -> str:
    """
    Loại bỏ các tiền tố crop/zoom nhỏ của CDN báo chí (Kenh14, GenK) để lấy ảnh gốc sắc nét.
    Ví dụ:
    - https://kenh14cdn.com/zoom/600_315/2033/pic.jpg -> https://kenh14cdn.com/2033/pic.jpg
    - https://genk.mediacdn.vn/zoom/700_438/1392/pic.jpg -> https://genk.mediacdn.vn/1392/pic.jpg
    """
    if not url or not isinstance(url, str):
        return ""
    url = url.strip()
    if not url:
        return ""
    return re.sub(r"/zoom/\d+_\d+/", "/", url)


def extract_thumbnail_url(entry: Any, raw_summary: str = "") -> str:
    """
    Trích xuất URL ảnh đại diện chất lượng cao của bài báo từ RSS entry theo 3 mức ưu tiên:
    1. entry.media_content (thuộc tính url)
    2. entry.enclosures (thuộc tính href khi type chứa 'image')
    3. Thẻ <img ... src="..."> bên trong raw_summary
    Tự động chuẩn hóa qua get_high_res_image_url để loại bỏ crop zoom CDN.
    Trả về "" nếu không tìm thấy ảnh hợp lệ (an toàn, không crash).
    """
    url = ""

    # Ưu tiên 1: media_content
    if entry:
        media_list = entry.get("media_content") if isinstance(entry, dict) else getattr(entry, "media_content", None)
        if media_list and isinstance(media_list, (list, tuple)):
            for media in media_list:
                m_url = ""
                if isinstance(media, dict) and media.get("url"):
                    m_url = str(media["url"]).strip()
                elif hasattr(media, "url") and getattr(media, "url", None):
                    m_url = str(media.url).strip()
                if m_url and (m_url.startswith("http://") or m_url.startswith("https://")):
                    url = m_url
                    break

    # Ưu tiên 2: enclosures (type image)
    if not url and entry:
        enc_list = entry.get("enclosures") if isinstance(entry, dict) else getattr(entry, "enclosures", None)
        if enc_list and isinstance(enc_list, (list, tuple)):
            for enc in enc_list:
                href = ""
                enc_type = ""
                if isinstance(enc, dict):
                    href = str(enc.get("href", "")).strip()
                    enc_type = str(enc.get("type", "")).lower()
                elif hasattr(enc, "href"):
                    href = str(getattr(enc, "href", "")).strip()
                    enc_type = str(getattr(enc, "type", "")).lower()
                if href and "image" in enc_type and (href.startswith("http://") or href.startswith("https://")):
                    url = href
                    break

    # Ưu tiên 3: Regex <img ... src="..."> trong raw_summary
    if not url and raw_summary and isinstance(raw_summary, str):
        for img_match in re.finditer(r'<img[^>]+src=["\']([^"\']+)["\']', raw_summary, re.IGNORECASE):
            raw_url = html.unescape(img_match.group(1)).strip()
            if raw_url.startswith("http://") or raw_url.startswith("https://"):
                url = raw_url
                break

    # Kiểm tra giao thức hợp lệ và làm sạch CDN zoom
    if url and (url.startswith("http://") or url.startswith("https://")):
        return get_high_res_image_url(url)

    return ""


def fetch_trending_news(topic: str = "CongNghe", limit: int = 15) -> List[Dict[str, Any]]:
    """
    Cào tin tức xu hướng theo chủ đề (thời gian thực ~0.5 giây).
    
    Tham số:
    - topic: 'CongNghe' hoặc 'GiaiTri'
    - limit: Số lượng bài viết muốn lấy (mặc định 15 bài mới nhất)
    
    Trả về: Danh sách các bài báo có đủ tiêu đề, tóm tắt, link gốc, ảnh đại diện
    """
    if topic not in RSS_CONFIG:
        raise ValueError(f"Chủ đề không hợp lệ! Vui lòng chọn 'CongNghe' hoặc 'GiaiTri'.")
        
    cfg = RSS_CONFIG[topic]
    articles = []
    
    # 1. Tải nội dung RSS feed (thử link chính, nếu lỗi dùng fallback)
    target_url = cfg["url"]
    feed = None
    try:
        resp = requests.get(target_url, headers=HTTP_HEADERS, timeout=6)
        if resp.status_code == 200:
            feed = feedparser.parse(resp.content)
    except Exception as e:
        logger.warning("Lỗi khi tải %s: %s. Thử fallback URL...", target_url, e)
        
    if not feed or not feed.entries:
        try:
            resp = requests.get(cfg["fallback_url"], headers=HTTP_HEADERS, timeout=6)
            feed = feedparser.parse(resp.content)
        except Exception as e:
            logger.warning("Fallback URL cũng thất bại: %s", e)
            return []

    # 2. Xử lý từng bài báo trong danh sách
    for entry in feed.entries[:limit]:
        title = clean_html_text(entry.get("title", ""))
        raw_summary = entry.get("summary", "")
        clean_summary = clean_html_text(raw_summary)
        link = entry.get("link", "")
        published_at = entry.get("published", "")
        
        thumbnail_url = extract_thumbnail_url(entry, raw_summary)
        
        # Chỉ nhận bài báo có tiêu đề rõ ràng
        if len(title) > 10:
            articles.append({
                "title": title,
                "summary": clean_summary,
                "link": link,
                "thumbnail_url": thumbnail_url,
                "published_at": published_at,
                "source": cfg["source"],
                "topic_category": cfg["topic_category"],
                "topic_name": topic
            })
            
    return articles


def fetch_all_trending(limit_per_topic: int = 10) -> Dict[str, List[Dict[str, Any]]]:
    """Cào đồng thời tin xu hướng từ cả 2 lĩnh vực Giải trí và Công nghệ."""
    return {
        "GiaiTri": fetch_trending_news("GiaiTri", limit=limit_per_topic),
        "CongNghe": fetch_trending_news("CongNghe", limit=limit_per_topic)
    }


if __name__ == "__main__":
    print("=" * 60)
    print("KIỂM TRA CÀO TIN TỨC XU HƯỚNG THỜI GIAN THỰC (GIAI ĐOẠN 4)")
    print("=" * 60)
    
    for t in ["GiaiTri", "CongNghe"]:
        news = fetch_trending_news(t, limit=3)
        print(f"\n--- Nguồn: {t} ({len(news)} bài) ---")
        for i, item in enumerate(news, 1):
            print(f"[{i}] {item['title']}")
            print(f"    Mô tả: {item['summary'][:100]}...")
            print(f"    Ảnh:   {item['thumbnail_url']}")
            print(f"    Link:  {item['link']}")
