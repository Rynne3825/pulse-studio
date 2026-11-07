"""
Bộ kiểm thử tự động Milestone M1: Trend Radar & High-Res Scraper.
Kiểm thử chi tiết các ca biên (edge cases) và xác nhận Contract 1.
Chạy bằng: D:\pulse-studio\.venv\Scripts\python.exe -m unittest tests/test_m1_trend_radar.py
"""

import sys
import unittest
from pathlib import Path
from typing import Dict, Any, List

# Thêm đường dẫn thư mục gốc dự án
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.scraper.rss_scraper import (
    clean_html_text,
    get_high_res_image_url,
    extract_thumbnail_url,
    fetch_trending_news,
    RSS_CONFIG
)
from src.preprocessing.trend_extractor import (
    extract_trending_topics,
    VIETNAMESE_STOPWORDS
)


class TestRssScraperEdgeCases(unittest.TestCase):
    """Kiểm thử các ca biên của module rss_scraper.py."""

    def test_get_high_res_image_url_kenh14_zoom(self):
        """T1.1: Làm sạch tiền tố zoom CDN Kenh14."""
        url = "https://kenh14cdn.com/zoom/600_315/203336854389633024/2026/11/7/avatar.jpg"
        expected = "https://kenh14cdn.com/203336854389633024/2026/11/7/avatar.jpg"
        self.assertEqual(get_high_res_image_url(url), expected)

    def test_get_high_res_image_url_genk_zoom(self):
        """T1.2: Làm sạch tiền tố zoom CDN GenK."""
        url = "https://genk.mediacdn.vn/zoom/700_438/139269124445442048/2026/11/6/photo.png"
        expected = "https://genk.mediacdn.vn/139269124445442048/2026/11/6/photo.png"
        self.assertEqual(get_high_res_image_url(url), expected)

    def test_get_high_res_image_url_non_zoom(self):
        """T1.3: URL ngoài không chứa zoom được giữ nguyên."""
        url = "https://images.unsplash.com/photo-1518770660439-4636190af475"
        self.assertEqual(get_high_res_image_url(url), url)

    def test_get_high_res_image_url_edge_inputs(self):
        """T1.4: Xử lý an toàn khi URL rỗng, None, khoảng trắng hoặc sai kiểu dữ liệu."""
        self.assertEqual(get_high_res_image_url(""), "")
        self.assertEqual(get_high_res_image_url(None), "")
        self.assertEqual(get_high_res_image_url("   "), "")
        self.assertEqual(get_high_res_image_url(123), "")
        self.assertEqual(get_high_res_image_url([]), "")

    def test_extract_thumbnail_priority_1_media_content(self):
        """T2.1: Ưu tiên 1 lấy ảnh từ media_content."""
        entry = {
            "media_content": [{"url": "https://kenh14cdn.com/zoom/600_315/pic1.jpg"}],
            "enclosures": [{"href": "https://kenh14cdn.com/zoom/600_315/pic2.jpg", "type": "image/jpeg"}],
        }
        summary = '<p><img src="https://kenh14cdn.com/zoom/600_315/pic3.jpg" /></p>'
        result = extract_thumbnail_url(entry, summary)
        self.assertEqual(result, "https://kenh14cdn.com/pic1.jpg")

    def test_extract_thumbnail_priority_2_enclosures(self):
        """T2.2: Ưu tiên 2 lấy ảnh từ enclosures khi không có media_content."""
        entry = {
            "enclosures": [{"href": "https://genk.mediacdn.vn/zoom/700_438/pic2.jpg", "type": "image/jpeg"}]
        }
        summary = '<p><img src="https://genk.mediacdn.vn/zoom/700_438/pic3.jpg" /></p>'
        result = extract_thumbnail_url(entry, summary)
        self.assertEqual(result, "https://genk.mediacdn.vn/pic2.jpg")

    def test_extract_thumbnail_ignore_non_image_enclosure(self):
        """T2.3: Bỏ qua enclosure audio/video, fallback sang img trong summary."""
        entry = {
            "enclosures": [{"href": "https://example.com/podcast.mp3", "type": "audio/mpeg"}]
        }
        summary = '<p><img src="https://genk.mediacdn.vn/zoom/700_438/valid.jpg" /></p>'
        result = extract_thumbnail_url(entry, summary)
        self.assertEqual(result, "https://genk.mediacdn.vn/valid.jpg")

    def test_extract_thumbnail_priority_3_summary_img_html_entities(self):
        """T2.4: Bóc tách ảnh từ thẻ img trong summary và giải mã HTML entities."""
        entry = {}
        summary = '<p>Tin vắn</p><img src="https://kenh14cdn.com/zoom/600_315/avatar.jpg?w=800&amp;q=90" />'
        result = extract_thumbnail_url(entry, summary)
        self.assertEqual(result, "https://kenh14cdn.com/avatar.jpg?w=800&q=90")

    def test_extract_thumbnail_no_image_returns_empty_string(self):
        """T2.5: Trả về chuỗi rỗng khi không có ảnh nào, tuyệt đối không trả None."""
        entry = {}
        summary = "<p>Bài viết chỉ chứa nội dung văn bản thuần túy.</p>"
        result = extract_thumbnail_url(entry, summary)
        self.assertEqual(result, "")

    def test_extract_thumbnail_insecure_schemes(self):
        """T2.6: Từ chối các URL không an toàn như javascript hoặc data:image."""
        entry = {}
        summary = '<img src="javascript:alert(1)" /><img src="data:image/png;base64,iVBORw0KGgoAAA..." />'
        result = extract_thumbnail_url(entry, summary)
        self.assertEqual(result, "")

    def test_fetch_trending_news_invalid_topic_raises_error(self):
        """T3.1: Ném ValueError khi chọn sai topic."""
        with self.assertRaises(ValueError):
            fetch_trending_news(topic="ChungKhoan")

    def test_fetch_trending_news_contract_compliance(self):
        """T3.2: Xác nhận danh sách trả về tuân thủ 100% ArticleItem Contract 1."""
        articles = fetch_trending_news("CongNghe", limit=3)
        self.assertIsInstance(articles, list)
        if articles:  # Nếu có kết nối Internet
            item = articles[0]
            required_keys = {"title", "summary", "link", "thumbnail_url", "published_at", "source", "topic_category", "topic_name"}
            self.assertTrue(required_keys.issubset(item.keys()))
            self.assertIsInstance(item["title"], str)
            self.assertIsInstance(item["summary"], str)
            self.assertIsInstance(item["link"], str)
            self.assertIsInstance(item["thumbnail_url"], str)
            self.assertIsInstance(item["published_at"], str)
            self.assertIsInstance(item["source"], str)
            self.assertIsInstance(item["topic_category"], int)
            self.assertIn(item["topic_category"], [0, 1])
            self.assertEqual(item["topic_name"], "CongNghe")


class TestTrendExtractorEdgeCases(unittest.TestCase):
    """Kiểm thử các ca biên của module trend_extractor.py."""

    def test_extract_trending_topics_empty_feed(self):
        """T4.1: Danh sách bài báo rỗng trả về cấu trúc mặc định."""
        result = extract_trending_topics([])
        self.assertEqual(result["keywords"], [])
        self.assertEqual(result["sentiment"]["positive"], 50.0)
        self.assertEqual(result["sentiment"]["neutral"], 50.0)
        self.assertEqual(result["sentiment"]["negative"], 0.0)
        self.assertEqual(result["overall_tone"], "Chưa có dữ liệu")

    def test_extract_trending_topics_blank_and_whitespace(self):
        """T4.2: Bài báo chỉ chứa khoảng trắng hoặc ký tự đặc biệt."""
        articles = [
            {"title": "   ", "summary": "\n\t "},
            {"title": "--- ... !!!", "summary": "??? ,,, ;;; "}
        ]
        result = extract_trending_topics(articles)
        self.assertEqual(result["keywords"], [])
        self.assertEqual(result["overall_tone"], "Chưa có dữ liệu")

    def test_extract_trending_topics_stop_words_only(self):
        """T4.3: Văn bản chỉ gồm từ dừng tiếng Việt (bẫy ValueError của TF-IDF)."""
        articles = [
            {"title": "là của và", "summary": "những các có được trong cho với đã khi tại sẽ đến từ này về như"}
        ]
        # Không được để lọt ValueError
        result = extract_trending_topics(articles)
        self.assertEqual(result["keywords"], [])
        self.assertIn("positive", result["sentiment"])

    def test_extract_trending_topics_small_corpus_bounds(self):
        """T4.4: Tập dữ liệu nhỏ có ít từ vựng hơn top_n không gây IndexError."""
        articles = [
            {"title": "Chip Snapdragon", "summary": "Snapdragon hiệu năng cao"}
        ]
        result = extract_trending_topics(articles, top_n=8)
        self.assertIsInstance(result["keywords"], list)
        self.assertLessEqual(len(result["keywords"]), 8)
        # Kiểm tra cấu trúc tuple (từ khóa, điểm độ nóng)
        for kw, score in result["keywords"]:
            self.assertIsInstance(kw, str)
            self.assertIsInstance(score, float)
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 100.0)

        # Kiểm tra thứ tự sắp xếp giảm dần theo điểm độ nóng
        if len(result["keywords"]) >= 2:
            scores = [s for _, s in result["keywords"]]
            self.assertEqual(scores, sorted(scores, reverse=True))

    def test_extract_trending_topics_strong_positive_sentiment(self):
        """T5.1: Sắc thái tích cực vượt trội (>60%)."""
        articles = [
            {
                "title": "Sự kiện ra mắt siêu phẩm công nghệ tuyệt vời và đỉnh cao",
                "summary": "Mọi người đều vô cùng hào hứng, chúc mừng thành công xuất sắc và hạnh phúc."
            }
        ]
        result = extract_trending_topics(articles)
        self.assertGreater(result["sentiment"]["positive"], 60.0)
        self.assertEqual(result["overall_tone"], "Tích cực / Hào hứng đón nhận")

    def test_extract_trending_topics_strong_negative_sentiment(self):
        """T5.2: Sắc thái tiêu cực vượt trội (>30%)."""
        articles = [
            {
                "title": "Cảnh báo khẩn cấp đường dây lừa đảo trực tuyến tinh vi",
                "summary": "Công an đã bắt giữ nhóm đối tượng, vụ bê bối gây khủng hoảng và tai nạn nghiêm trọng."
            }
        ]
        result = extract_trending_topics(articles)
        self.assertGreater(result["sentiment"]["negative"], 30.0)
        self.assertEqual(result["overall_tone"], "Nóng bỏng / Nhiều tranh cãi trái chiều")

    def test_extract_trending_topics_balanced_sentiment(self):
        """T5.3: Sắc thái trung tính hoặc cân bằng."""
        articles = [
            {
                "title": "Bản tin cập nhật số liệu công nghệ phần mềm tuần qua",
                "summary": "Báo cáo chi tiết về tình hình triển khai hạ tầng mạng viễn thông."
            }
        ]
        result = extract_trending_topics(articles)
        self.assertEqual(result["overall_tone"], "Sôi động / Thu hút tương tác cao")

    def test_extract_trending_topics_100_percent_sum_invariant(self):
        """T5.4: Bất biến tổng tỷ lệ sắc thái luôn xấp xỉ 100.0%."""
        test_cases = [
            [],
            [{"title": "tuyệt vời", "summary": "xuất sắc"}],
            [{"title": "lừa đảo tệ hại", "summary": "thất vọng"}],
            [{"title": "vừa vui vừa buồn", "summary": "thành công nhưng gặp lỗi sự cố"}]
        ]
        for tc in test_cases:
            res = extract_trending_topics(tc)
            s = res["sentiment"]
            total = s["positive"] + s["neutral"] + s["negative"]
            self.assertAlmostEqual(total, 100.0, places=1, msg=f"Tổng không đạt 100%: {s}")


class TestEndToEndMilestone1(unittest.TestCase):
    """Kiểm thử tích hợp luồng dữ liệu thông suốt M1 (Contract 1)."""

    def test_m1_end_to_end_pipeline(self):
        """T6.1: Dữ liệu từ scraper chuyển tiếp trực tiếp vào trend_extractor."""
        articles = fetch_trending_news(topic="CongNghe", limit=5)
        self.assertIsInstance(articles, list)

        # Chạy phân tích xu hướng
        analysis = extract_trending_topics(articles, top_n=5)
        self.assertIn("keywords", analysis)
        self.assertIn("sentiment", analysis)
        self.assertIn("overall_tone", analysis)

        # Kiểm tra bất biến sắc thái
        s = analysis["sentiment"]
        total = s["positive"] + s["neutral"] + s["negative"]
        self.assertAlmostEqual(total, 100.0, places=1)


if __name__ == "__main__":
    unittest.main()
