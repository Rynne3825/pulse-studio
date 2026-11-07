"""
Unit test for real-time RSS scraper module (Kenh14 & GenK).
"""

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.scraper.rss_scraper import fetch_trending_news, fetch_all_trending, clean_html_text


def test_clean_html_text():
    raw_html = "<p>Tin <b>hot</b> nh&acirc;t h&ocirc;m nay &amp; ngay l&uacute;c n&agrave;y!</p>"
    cleaned = clean_html_text(raw_html)
    assert "<p>" not in cleaned and "<b>" not in cleaned, "HTML tags were not removed."
    assert "&amp;" not in cleaned, "HTML entities were not unescaped."
    print("test_clean_html_text: PASSED")


def test_live_rss_scraping():
    for topic in ["GiaiTri", "CongNghe"]:
        start_time = time.time()
        articles = fetch_trending_news(topic, limit=5)
        elapsed = time.time() - start_time
        
        print(f"\n[Testing {topic} RSS Feed]")
        print(f"-> Response time: {elapsed:.2f}s")
        assert len(articles) > 0, f"No articles fetched for topic: {topic}"
        print(f"-> Articles fetched: {len(articles)}")
        
        sample = articles[0]
        assert "title" in sample and len(sample["title"]) > 5, "Missing or invalid title."
        assert "link" in sample and sample["link"].startswith("http"), "Missing or invalid link."
        assert "summary" in sample and len(sample["summary"]) > 0, "Missing or invalid summary."
        assert "thumbnail_url" in sample, "Missing thumbnail_url key."
        assert sample["topic_name"] == topic, "Topic name mismatch."
        
        print(f"-> Sample Article Title: {sample['title'][:60]}...")
        print(f"-> Sample Thumbnail URL: {sample['thumbnail_url']}")
        print(f"-> Article source: {sample['source']}")
        print(f"test_live_rss_scraping ({topic}): PASSED")


def test_fetch_all_trending():
    all_news = fetch_all_trending(limit_per_topic=3)
    assert "GiaiTri" in all_news and len(all_news["GiaiTri"]) > 0, "Missing GiaiTri in fetch_all."
    assert "CongNghe" in all_news and len(all_news["CongNghe"]) > 0, "Missing CongNghe in fetch_all."
    print("\ntest_fetch_all_trending: PASSED")


if __name__ == "__main__":
    test_clean_html_text()
    test_live_rss_scraping()
    test_fetch_all_trending()
    print("\nALL RSS SCRAPER TESTS PASSED SUCCESSFULLY.")
