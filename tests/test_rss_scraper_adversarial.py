"""
Adversarial Stress Test Suite for `rss_scraper.py` (Milestone M1).
Targets:
- `get_high_res_image_url`
- `extract_thumbnail_url`

Stress tests:
1. Malformed URLs, weird schemes (ftp, javascript, data, file), missing schemes
2. Complex nested HTML tags, entity unescaping, multiline tags, ReDoS resistance
3. Extreme/invalid inputs (None, primitives, objects, throwing descriptors)
4. Strict priority cascading (media_content > enclosures > raw_summary)
5. Zero crashes guaranteed under all inputs.
"""

import sys
import time
import html
import unittest
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import feedparser
from src.scraper.rss_scraper import get_high_res_image_url, extract_thumbnail_url


class MockSafeEntry:
    """Mock entry supporting object attribute access."""
    def __init__(self, media=None, enclosures=None):
        self.media_content = media
        self.enclosures = enclosures


class MockAttributeErrorEntry:
    """Mock entry where attribute access triggers AttributeError."""
    @property
    def media_content(self):
        raise AttributeError("Simulated missing media_content")

    @property
    def enclosures(self):
        raise AttributeError("Simulated missing enclosures")


class TestAdversarialRssScraper(unittest.TestCase):
    """Adversarial stress-testing suite for rss_scraper.py."""

    # =========================================================================
    # 1. get_high_res_image_url
    # =========================================================================

    def test_get_high_res_non_string_types_immunity(self):
        """Stress-test non-string and primitive types: must return '' and never crash."""
        bad_types = [
            None,
            0,
            123,
            -1,
            3.14159,
            True,
            False,
            [],
            [1, "https://kenh14cdn.com/zoom/600_315/pic.jpg"],
            {},
            {"url": "https://kenh14cdn.com/zoom/600_315/pic.jpg"},
            (1, 2),
            {1, 2},
            b"https://kenh14cdn.com/zoom/600_315/pic.jpg",
            object(),
            ValueError("adversarial_error"),
        ]
        for val in bad_types:
            with self.subTest(val=val):
                res = get_high_res_image_url(val)
                self.assertEqual(res, "", f"Expected '' for non-string input {type(val)}, got {repr(res)}")

    def test_get_high_res_whitespace_and_control_chars(self):
        """Test blank, whitespace, and special unicode control strings."""
        cases = [
            "",
            " ",
            "    ",
            "\t\n\r\v\f",
            " \t \n ",
        ]
        for s in cases:
            with self.subTest(s=s):
                self.assertEqual(get_high_res_image_url(s), "")

    def test_get_high_res_cdn_zoom_variations(self):
        """Test regex zoom stripping across real and weird CDN patterns."""
        cases = [
            # Standard Kenh14
            ("https://kenh14cdn.com/zoom/600_315/2033/pic.jpg", "https://kenh14cdn.com/2033/pic.jpg"),
            # Standard GenK
            ("https://genk.mediacdn.vn/zoom/700_438/1392/pic.jpg", "https://genk.mediacdn.vn/1392/pic.jpg"),
            # CafeF / VcCorp
            ("https://cafefcdn.com/zoom/280_175/pr/2023/photo.jpg", "https://cafefcdn.com/pr/2023/photo.jpg"),
            # Single digit zoom
            ("https://cdn.com/zoom/1_1/pic.jpg", "https://cdn.com/pic.jpg"),
            # Large numbers
            ("https://cdn.com/zoom/99999_88888/pic.jpg", "https://cdn.com/pic.jpg"),
            # Already high-res
            ("https://kenh14cdn.com/2033/pic.jpg", "https://kenh14cdn.com/2033/pic.jpg"),
            # Non-matching zoom formats
            ("https://cdn.com/zoom/600x315/pic.jpg", "https://cdn.com/zoom/600x315/pic.jpg"),
            ("https://cdn.com/zoom/abc_def/pic.jpg", "https://cdn.com/zoom/abc_def/pic.jpg"),
            ("https://cdn.com/zoom/600_315", "https://cdn.com/zoom/600_315"),
            # Padding whitespace
            ("  https://kenh14cdn.com/zoom/600_315/2033/pic.jpg  ", "https://kenh14cdn.com/2033/pic.jpg"),
            # Preserves query params and fragments
            ("https://cdn.com/zoom/600_315/pic.jpg?w=800&q=90", "https://cdn.com/pic.jpg?w=800&q=90"),
            ("https://cdn.com/zoom/600_315/pic.jpg#hero", "https://cdn.com/pic.jpg#hero"),
        ]
        for input_url, expected in cases:
            with self.subTest(input_url=input_url):
                self.assertEqual(get_high_res_image_url(input_url), expected)

    def test_get_high_res_malformed_urls_and_long_strings(self):
        """Test malformed URLs, unicode paths, and gigantic payloads without crashing."""
        long_str = "https://cdn.com/zoom/600_315/" + ("x" * 50000) + ".jpg"
        expected_long = "https://cdn.com/" + ("x" * 50000) + ".jpg"

        cases = [
            ("kenh14cdn.com/zoom/600_315/2033/pic.jpg", "kenh14cdn.com/2033/pic.jpg"),
            ("/", "/"),
            ("///", "///"),
            ("/zoom/600_315/pic.jpg", "/pic.jpg"),
            ("https://cdn.vn/zoom/600_315/ảnh-đẹp.jpg", "https://cdn.vn/ảnh-đẹp.jpg"),
            (long_str, expected_long),
        ]
        for input_url, expected in cases:
            with self.subTest(input_url=input_url[:40]):
                self.assertEqual(get_high_res_image_url(input_url), expected)

    # =========================================================================
    # 2. extract_thumbnail_url
    # =========================================================================

    def test_extract_thumbnail_null_primitive_inputs(self):
        """Test completely invalid or empty inputs to extract_thumbnail_url."""
        invalid_entries = [
            (None, ""),
            (None, None),
            (123, ""),
            ("string", ""),
            ([], ""),
            (False, ""),
            (True, ""),
            ({}, ""),
            ({}, 123),
            ({}, ["<img src='https://cdn.com/pic.jpg'>"]),
            ({}, {"summary": "test"}),
        ]
        for entry, summary in invalid_entries:
            with self.subTest(entry=entry, summary=summary):
                self.assertEqual(extract_thumbnail_url(entry, summary), "")

    def test_extract_thumbnail_entry_attribute_error_immunity(self):
        """Entry with throwing property must fall back safely and return ''."""
        entry = MockAttributeErrorEntry()
        self.assertEqual(extract_thumbnail_url(entry, ""), "")

    def test_extract_thumbnail_media_content_adversarial(self):
        """Adversarially test Priority 1 (media_content)."""
        cases = [
            ("not a list (dict)", {"media_content": {"url": "https://cdn.com/pic.jpg"}}, ""),
            ("not a list (str)", {"media_content": "https://cdn.com/pic.jpg"}, ""),
            ("list of invalid types", {"media_content": [None, 123, "test", {}]}, ""),
            ("url is None", {"media_content": [{"url": None}]}, ""),
            ("url is int", {"media_content": [{"url": 12345}]}, ""),
            ("url is empty string", {"media_content": [{"url": ""}]}, ""),
            ("url is whitespace", {"media_content": [{"url": "   "}]}, ""),
            ("scheme ftp", {"media_content": [{"url": "ftp://cdn.com/pic.jpg"}]}, ""),
            ("scheme javascript", {"media_content": [{"url": "javascript:alert(1)"}]}, ""),
            ("scheme data", {"media_content": [{"url": "data:image/png;base64,abc"}]}, ""),
            ("scheme file", {"media_content": [{"url": "file:///etc/passwd"}]}, ""),
            ("valid http", {"media_content": [{"url": "http://cdn.com/pic.jpg"}]}, "http://cdn.com/pic.jpg"),
            ("valid https with zoom", {"media_content": [{"url": "https://kenh14cdn.com/zoom/600_315/2033/pic.jpg"}]}, "https://kenh14cdn.com/2033/pic.jpg"),
            ("multiple items (first invalid, second valid)", {"media_content": [{"url": "ftp://bad.com"}, {"url": "https://cdn.com/valid.jpg"}]}, "https://cdn.com/valid.jpg"),
            ("object items with .url", MockSafeEntry(media=[type("MediaObj", (), {"url": "https://cdn.com/obj.jpg"})()]), "https://cdn.com/obj.jpg"),
        ]
        for label, entry, expected in cases:
            with self.subTest(label=label):
                self.assertEqual(extract_thumbnail_url(entry, ""), expected)

    def test_extract_thumbnail_enclosures_adversarial(self):
        """Adversarially test Priority 2 (enclosures)."""
        cases = [
            ("not a list", {"enclosures": "string"}, ""),
            ("list of invalid items", {"enclosures": [None, 123, "foo", {}]}, ""),
            ("missing href", {"enclosures": [{"type": "image/jpeg"}]}, ""),
            ("missing type", {"enclosures": [{"href": "https://cdn.com/pic.jpg"}]}, ""),
            ("href is None", {"enclosures": [{"href": None, "type": "image/jpeg"}]}, ""),
            ("type is None", {"enclosures": [{"href": "https://cdn.com/pic.jpg", "type": None}]}, ""),
            ("podcast audio", {"enclosures": [{"href": "https://cdn.com/pod.mp3", "type": "audio/mpeg"}]}, ""),
            ("video mp4", {"enclosures": [{"href": "https://cdn.com/v.mp4", "type": "video/mp4"}]}, ""),
            ("pdf document", {"enclosures": [{"href": "https://cdn.com/d.pdf", "type": "application/pdf"}]}, ""),
            ("valid image/jpeg", {"enclosures": [{"href": "https://cdn.com/pic.jpg", "type": "image/jpeg"}]}, "https://cdn.com/pic.jpg"),
            ("uppercase type IMAGE/PNG", {"enclosures": [{"href": "https://cdn.com/pic.png", "type": "IMAGE/PNG"}]}, "https://cdn.com/pic.png"),
            ("image/webp with zoom", {"enclosures": [{"href": "https://genk.mediacdn.vn/zoom/700_438/pic.webp", "type": "image/webp"}]}, "https://genk.mediacdn.vn/pic.webp"),
            ("invalid scheme ftp", {"enclosures": [{"href": "ftp://cdn.com/pic.jpg", "type": "image/jpeg"}]}, ""),
            ("multiple (audio then image)", {"enclosures": [{"href": "https://cdn.com/p.mp3", "type": "audio/mpeg"}, {"href": "https://cdn.com/pic.jpg", "type": "image/jpeg"}]}, "https://cdn.com/pic.jpg"),
            ("object items with attributes", MockSafeEntry(enclosures=[type("EncObj", (), {"href": "https://cdn.com/enc.jpg", "type": "image/png"})()]), "https://cdn.com/enc.jpg"),
        ]
        for label, entry, expected in cases:
            with self.subTest(label=label):
                self.assertEqual(extract_thumbnail_url(entry, ""), expected)

    def test_extract_thumbnail_raw_summary_adversarial(self):
        """Adversarially test Priority 3 (regex extraction from raw_summary)."""
        cases = [
            ("no img tag", "<div><p>Simple text without any image</p></div>", ""),
            ("standard double quotes", '<img src="https://kenh14cdn.com/zoom/600_315/2033/pic.jpg">', "https://kenh14cdn.com/2033/pic.jpg"),
            ("standard single quotes", "<img src='https://genk.mediacdn.vn/zoom/700_438/1392/pic.jpg'>", "https://genk.mediacdn.vn/1392/pic.jpg"),
            ("uppercase IMG SRC", '<IMG SRC="https://cdn.com/PIC.JPG">', "https://cdn.com/PIC.JPG"),
            ("attributes before and after", '<img alt="Ảnh" class="thumb" src="https://cdn.com/pic.jpg" width="600">', "https://cdn.com/pic.jpg"),
            ("multiline formatted tag", """<div class="test">
                <img
                    class="hero"
                    src="https://kenh14cdn.com/zoom/600_315/2033/hero.jpg"
                    alt="Hero"
                />
            </div>""", "https://kenh14cdn.com/2033/hero.jpg"),
            ("deeply nested HTML", "<div><section><article><p><span><a><img src='https://cdn.com/nested.jpg'/></a></span></p></article></section></div>", "https://cdn.com/nested.jpg"),
            ("escaped HTML entities in query", '<img src="https://cdn.com/pic.jpg?w=600&amp;h=400&amp;format=webp">', "https://cdn.com/pic.jpg?w=600&h=400&format=webp"),
            ("invalid scheme javascript", '<img src="javascript:alert(\'XSS\')">', ""),
            ("invalid scheme data URI", '<img src="data:image/png;base64,iVBORw0KGgo=">', ""),
            ("relative path in img", '<img src="/static/images/logo.png">', ""),
            ("empty src", '<img src="">', ""),
            ("whitespace src", '<img src="   ">', ""),
            ("multiple: first is relative, second is http", '<img src="/pixel.gif"><img src="https://cdn.com/valid.jpg">', "https://cdn.com/valid.jpg"),
            ("multiple: first is javascript, second is http", '<img src="javascript:void(0)"><img src="https://cdn.com/valid.jpg">', "https://cdn.com/valid.jpg"),
        ]
        for label, summary, expected in cases:
            with self.subTest(label=label):
                self.assertEqual(extract_thumbnail_url({}, summary), expected)

    def test_extract_thumbnail_priority_cascade(self):
        """Verify strict priority cascading: media_content > enclosures > raw_summary."""
        p1 = {"media_content": [{"url": "https://cdn.com/p1.jpg"}], "enclosures": [{"href": "https://cdn.com/p2.jpg", "type": "image/jpeg"}]}
        summary = '<img src="https://cdn.com/p3.jpg">'
        # P1 present & valid -> P1 wins
        self.assertEqual(extract_thumbnail_url(p1, summary), "https://cdn.com/p1.jpg")

        # P1 invalid -> P2 wins
        p2 = {"media_content": [{"url": "ftp://bad.com"}], "enclosures": [{"href": "https://cdn.com/p2.jpg", "type": "image/jpeg"}]}
        self.assertEqual(extract_thumbnail_url(p2, summary), "https://cdn.com/p2.jpg")

        # P1 empty and P2 audio -> P3 wins
        p3 = {"media_content": [], "enclosures": [{"href": "https://cdn.com/pod.mp3", "type": "audio/mpeg"}]}
        self.assertEqual(extract_thumbnail_url(p3, summary), "https://cdn.com/p3.jpg")

        # All 3 invalid -> returns ""
        p_all_bad = {"media_content": [{"url": "javascript:1"}], "enclosures": [{"href": "https://cdn.com/a.mp3", "type": "audio/mpeg"}]}
        summary_bad = '<img src="data:image/png;base64,123">'
        self.assertEqual(extract_thumbnail_url(p_all_bad, summary_bad), "")

    def test_extract_thumbnail_performance_and_redos(self):
        """Stress-test regex engine against ReDoS and gigantic inputs (must run < 0.2s)."""
        redos_cases = [
            ("<img " + ("attr=\"val\" " * 3000) + 'src="https://cdn.com/stress1.jpg">', "https://cdn.com/stress1.jpg"),
            ("<img " + ("a" * 20000) + " src=\"https://cdn.com/stress2.jpg\">", "https://cdn.com/stress2.jpg"),
            ("<div>" + ("<p>No image here</p>" * 2000) + "</div>", ""),
            (("<img src=''> " * 1000) + '<img src="https://cdn.com/final.jpg">', "https://cdn.com/final.jpg"),
        ]
        start_time = time.perf_counter()
        for summary, expected in redos_cases:
            res = extract_thumbnail_url({}, summary)
            self.assertEqual(res, expected)
        elapsed = time.perf_counter() - start_time
        self.assertLess(elapsed, 0.2, f"ReDoS stress test took too long: {elapsed:.4f}s")

    def test_extract_thumbnail_feedparser_integration(self):
        """Integration test with simulated feedparser output from real XML."""
        xml_sample = """<?xml version="1.0" encoding="utf-8"?>
        <rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
          <channel>
            <title>Kenh14 Star RSS</title>
            <item>
              <title>Tin sao 1 Enclosure</title>
              <link>https://kenh14.vn/tin-1.chn</link>
              <description><![CDATA[<img src="https://kenh14cdn.com/zoom/600_315/2033/pic1.jpg" />Mô tả]]></description>
              <enclosure url="https://kenh14cdn.com/zoom/600_315/2033/pic1.jpg" type="image/jpeg" length="12345" />
            </item>
            <item>
              <title>Tin sao 2 MediaContent</title>
              <link>https://kenh14.vn/tin-2.chn</link>
              <description><![CDATA[Không có ảnh trong mô tả]]></description>
              <media:content url="https://kenh14cdn.com/zoom/600_315/2033/pic2.jpg" medium="image" />
            </item>
          </channel>
        </rss>
        """
        feed = feedparser.parse(xml_sample)
        self.assertEqual(len(feed.entries), 2)
        e1 = feed.entries[0]
        self.assertEqual(extract_thumbnail_url(e1, e1.get("summary", "")), "https://kenh14cdn.com/2033/pic1.jpg")
        e2 = feed.entries[1]
        self.assertEqual(extract_thumbnail_url(e2, e2.get("summary", "")), "https://kenh14cdn.com/2033/pic2.jpg")


if __name__ == "__main__":
    unittest.main()
