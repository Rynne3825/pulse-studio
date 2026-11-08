"""
Empirical Adversarial Stress-Test Suite — Challenger 1
Focus:
- Extreme text inputs, unusual unicode/diacritics, massive headlines across all 5 themes
- Script generation edge cases (empty summaries, special characters, safe fallback)
- Fast repeated card rendering concurrency and stability
- SafeFallbackSynthesizer._generate_card robustness on invalid inputs
"""

import os
import sys
import gc
import re
import time
import shutil
import tempfile
import threading
import tracemalloc
import unittest
from pathlib import Path
from typing import Dict, List, Any, Optional
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.video.muse_integration import (
    SafeFallbackSynthesizer,
    THEME_PRESETS,
    find_ffmpeg_binary,
)
from src.ai.generator import (
    generate_tiktok_script,
    safe_script_fallback,
    self_healing_json_parser,
    TIKTOK_SYSTEM_PROMPT,
)
from src.models.content_evaluator import (
    evaluate_tiktok_script,
    VIRAL_HOOK_KEYWORDS,
    VIRAL_CTA_KEYWORDS,
)

ALL_THEMES = ["editorial", "vibrant", "neon", "tech", "pastel"]


class TestThemeExtremeInputs(unittest.TestCase):
    """Stress tests on card generation across all 5 themes with extreme inputs."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="challenger_theme_")
        self.synth = SafeFallbackSynthesizer()

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_all_five_themes_massive_headline_5000_chars(self) -> None:
        """Card generation must succeed across all 5 themes with massive 5000-char headline."""
        massive_headline = " ".join(["Cảnh báo thông tin khẩn cấp về an ninh mạng toàn cầu!"] * 100)
        self.assertGreater(len(massive_headline), 4000)

        for theme in ALL_THEMES:
            out_p = self.synth._generate_card(
                title="TIN KHẨN CẤP",
                headline=massive_headline,
                color=THEME_PRESETS[theme]["title_color"],
                ref_image_path=None,
                temp_dir=Path(self.temp_dir),
                scene_num=1,
                theme=theme
            )
            self.assertTrue(out_p.exists(), f"Card file missing for theme {theme}")
            with Image.open(out_p) as img:
                self.assertEqual(img.size, (720, 1280), f"Wrong dimensions for theme {theme}")

    def test_all_five_themes_giant_unbreakable_single_word(self) -> None:
        """Card generation must succeed with a 1500-char unbroken word without crashing text wrapping."""
        giant_word = "SUPER" + "A" * 1500 + "LONGWORD"
        for theme in ALL_THEMES:
            out_p = self.synth._generate_card(
                title="UNBREAKABLE",
                headline=giant_word,
                color=THEME_PRESETS[theme]["title_color"],
                ref_image_path=None,
                temp_dir=Path(self.temp_dir),
                scene_num=2,
                theme=theme
            )
            self.assertTrue(out_p.exists())
            with Image.open(out_p) as img:
                self.assertEqual(img.size, (720, 1280))

    def test_all_five_themes_complex_unicode_and_diacritics(self) -> None:
        """Card generation must render complex Vietnamese diacritics, Zalgo, CJK, RTL, and emojis without crashing."""
        complex_text = (
            "Cảnh báo đường, ngõ, phở, trắc nghiệm, khuất tất, bứt phá! "
            "Emoji: 🔥😱👀⚡🎉💥💀🤖 "
            "CJK: 这是一个测试 テストです 테스트입니다 "
            "RTL: مرحبا بالعالم שלום עולם "
            "Zalgo: H̴e̷l̸l̴o̶ ̸W̸o̴r̴l̵d̴ "
            "Symbols: ∀x∈ℝ ∑ ∫ √ ± ∛ ⊕ ⊗"
        )
        for theme in ALL_THEMES:
            out_p = self.synth._generate_card(
                title="UNICODE CHẤN ĐỘNG",
                headline=complex_text,
                color=THEME_PRESETS[theme]["title_color"],
                ref_image_path=None,
                temp_dir=Path(self.temp_dir),
                scene_num=3,
                theme=theme
            )
            self.assertTrue(out_p.exists())
            with Image.open(out_p) as img:
                self.assertEqual(img.size, (720, 1280))

    def test_theme_fallback_graceful_on_invalid_theme_name(self) -> None:
        """Unknown theme names must fallback to editorial theme without raising KeyError."""
        invalid_themes = ["cyber_dark", "matrix", "", "   ", None, 9999, object()]
        for idx, it in enumerate(invalid_themes):
            out_p = self.synth._generate_card(
                title="FALLBACK TEST",
                headline="Kiểm tra fallback an toàn khi truyền theme không tồn tại",
                color=None,
                ref_image_path=None,
                temp_dir=Path(self.temp_dir),
                scene_num=idx + 1,
                theme=it  # type: ignore
            )
            self.assertTrue(out_p.exists())
            with Image.open(out_p) as img:
                self.assertEqual(img.size, (720, 1280))

    def test_corrupted_and_unusual_reference_image_paths(self) -> None:
        """Corrupted, 0-byte, directory, or non-image files as ref_image_path must not crash _generate_card."""
        # 1. Non-existent file
        p_nonexistent = Path(self.temp_dir) / "does_not_exist.jpg"
        out1 = self.synth._generate_card("TEST", "Headline", None, p_nonexistent, Path(self.temp_dir), 1, "editorial")
        self.assertTrue(out1.exists())

        # 2. Directory as path
        p_dir = Path(self.temp_dir)
        out2 = self.synth._generate_card("TEST", "Headline", None, p_dir, Path(self.temp_dir), 2, "vibrant")
        self.assertTrue(out2.exists())

        # 3. 0-byte file
        p_empty = Path(self.temp_dir) / "empty.jpg"
        p_empty.write_bytes(b"")
        out3 = self.synth._generate_card("TEST", "Headline", None, p_empty, Path(self.temp_dir), 3, "neon")
        self.assertTrue(out3.exists())

        # 4. Text file masquerading as image
        p_corrupt = Path(self.temp_dir) / "corrupt.png"
        p_corrupt.write_text("THIS IS NOT A VALID PNG IMAGE CONTENT")
        out4 = self.synth._generate_card("TEST", "Headline", None, p_corrupt, Path(self.temp_dir), 4, "tech")
        self.assertTrue(out4.exists())

    def test_scene_num_boundary_values(self) -> None:
        """Scene progress dots should handle unusual scene_num values (0, -1, 5, 999) without IndexError."""
        for s_num in [0, -1, 4, 5, 999]:
            out = self.synth._generate_card("BOUNDARY", "Progress dots check", None, None, Path(self.temp_dir), s_num, "pastel")
            self.assertTrue(out.exists())


class TestCardRobustnessVulnerabilities(unittest.TestCase):
    """Empirical verification that _generate_card and scene card generation gracefully handle None or non-string inputs."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="challenger_vuln_")
        self.synth = SafeFallbackSynthesizer()

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_generate_card_none_title_handling(self) -> None:
        """Verify empirical behavior when title=None is passed: must render cleanly without crash."""
        out = self.synth._generate_card(
            title=None,  # type: ignore
            headline="Valid headline",
            color=None,
            ref_image_path=None,
            temp_dir=Path(self.temp_dir),
            scene_num=1,
            theme="editorial"
        )
        self.assertTrue(out.exists())
        with Image.open(out) as img:
            self.assertEqual(img.size, (720, 1280))

    def test_generate_card_none_headline_handling(self) -> None:
        """Verify empirical behavior when headline=None is passed: must render cleanly without crash."""
        out = self.synth._generate_card(
            title="Valid Title",
            headline=None,  # type: ignore
            color=None,
            ref_image_path=None,
            temp_dir=Path(self.temp_dir),
            scene_num=1,
            theme="editorial"
        )
        self.assertTrue(out.exists())
        with Image.open(out) as img:
            self.assertEqual(img.size, (720, 1280))

    def test_generate_card_non_string_types(self) -> None:
        """Verify empirical behavior when title/headline are integers: must coerce cleanly and render."""
        out1 = self.synth._generate_card(
            title=12345,  # type: ignore
            headline="Headline",
            color=None,
            ref_image_path=None,
            temp_dir=Path(self.temp_dir),
            scene_num=1,
            theme="editorial"
        )
        self.assertTrue(out1.exists())
        with Image.open(out1) as img:
            self.assertEqual(img.size, (720, 1280))

        out2 = self.synth._generate_card(
            title="Title",
            headline=12345,  # type: ignore
            color=None,
            ref_image_path=None,
            temp_dir=Path(self.temp_dir),
            scene_num=2,
            theme="editorial"
        )
        self.assertTrue(out2.exists())
        with Image.open(out2) as img:
            self.assertEqual(img.size, (720, 1280))

    def test_scene_with_none_values_crashes_card_generation(self) -> None:
        """Verify that scene dict with explicit None title/voice_text is safely guarded and renders."""
        scene = {"scene_num": 1, "title": None, "voice_text": None}
        sc_title = scene.get("title") or "Fallback Title"
        sc_text = scene.get("voice_text") or "Fallback Voice"

        self.assertEqual(sc_title, "Fallback Title")
        self.assertEqual(sc_text, "Fallback Voice")

        out = self.synth._generate_scene_card(
            scene_num=1,
            title=sc_title,
            headline=sc_text,
            color=(255, 0, 0),
            ref_image_path=None,
            temp_dir=Path(self.temp_dir),
            theme="editorial"
        )
        self.assertTrue(out.exists())
        with Image.open(out) as img:
            self.assertEqual(img.size, (720, 1280))

        # Also test direct pass of None into _generate_scene_card
        out_direct = self.synth._generate_scene_card(
            scene_num=1,
            title=None,  # type: ignore
            headline=None,  # type: ignore
            color=(255, 0, 0),
            ref_image_path=None,
            temp_dir=Path(self.temp_dir),
            theme="editorial"
        )
        self.assertTrue(out_direct.exists())


class TestScriptGenerationStress(unittest.TestCase):
    """Stress tests on viral script fallback and self-healing parser under extreme adversarial conditions."""

    def test_safe_script_fallback_none_and_empty_inputs(self) -> None:
        """safe_script_fallback must produce valid 3-part viral script on None, empty, and whitespace inputs."""
        test_inputs = [
            (None, None),
            ("", ""),
            ("   \t\n  ", "   \r\n "),
            ("A" * 20000, "B" * 50000),
            ("<script>alert('xss')</script>", "'; DROP TABLE users; --"),
            ("H̴e̷l̸l̴o̶", "đường ngõ phở trắc nghiệm khuất tất"),
        ]

        for title, summary in test_inputs:
            script = safe_script_fallback(title, summary, engine="gemini")
            self.assertIsInstance(script, dict)

            # 1. Hook assertions
            hook = str(script.get("hook", ""))
            hook_words = hook.split()
            self.assertLessEqual(len(hook_words), 15, f"Hook exceeds 15 words: '{hook}'")
            self.assertTrue(hook.endswith("?"), f"Hook must end with '?': '{hook}'")
            has_hook_kw = any(kw.lower() in hook.lower() for kw in VIRAL_HOOK_KEYWORDS)
            self.assertTrue(has_hook_kw, f"Hook missing viral keyword: '{hook}'")

            # 2. Retain Body assertions
            body = str(script.get("body", ""))
            body_words = body.split()
            self.assertGreaterEqual(len(body_words), 60, f"Body has < 60 words ({len(body_words)}): '{body}'")
            self.assertLessEqual(len(body_words), 85, f"Body has > 85 words ({len(body_words)}): '{body}'")

            # 3. Payoff CTA assertions
            cta = str(script.get("cta", ""))
            cta_words = cta.split()
            self.assertGreaterEqual(len(cta_words), 15, f"CTA has < 15 words ({len(cta_words)}): '{cta}'")
            self.assertLessEqual(len(cta_words), 25, f"CTA has > 25 words ({len(cta_words)}): '{cta}'")
            self.assertTrue(cta.endswith("?"), f"CTA must end with '?': '{cta}'")
            has_cta_kw = any(kw.lower() in cta.lower() for kw in VIRAL_CTA_KEYWORDS)
            self.assertTrue(has_cta_kw, f"CTA missing viral keyword: '{cta}'")

            # 4. Scenes assertions
            scenes = script.get("scenes", [])
            self.assertEqual(len(scenes), 4, "Must have exactly 4 scenes")
            for idx, sc in enumerate(scenes, 1):
                self.assertEqual(sc.get("scene_num"), idx)
                vp = str(sc.get("visual_prompt", ""))
                self.assertTrue(
                    vp.startswith("Vertical 9:16 aspect ratio video, "),
                    f"Scene {idx} visual_prompt missing required 9:16 prefix: {vp}"
                )
                ipd = sc.get("image_prompt_detail", {})
                self.assertIsInstance(ipd, dict)
                for req_key in ("subject", "lighting", "camera_angle", "color_tone", "art_style"):
                    self.assertIn(req_key, ipd)
                    self.assertTrue(len(str(ipd[req_key]).strip()) > 0)

            # 5. Cinematography Locks assertions
            locks = script.get("cinematography_locks", {})
            self.assertIsInstance(locks, dict)
            for lk in ("style_lock", "char_lock", "set_lock", "video_suffix", "negative_prompt"):
                self.assertIn(lk, locks)

    def test_self_healing_json_parser_adversarial_payloads(self) -> None:
        """7-tier parser must recover from truncated, single-quoted, conversational, and null-laden responses."""
        adversarial_payloads = [
            # Truncated JSON
            '{"hook": "Sự thật chấn động đằng sau?", "body": "Chi tiết...", "scenes": [',
            # Single-quoted dict
            "{'hook': 'Cảnh báo lừa đảo tinh vi?', 'body': 'Thủ đoạn nguy hiểm...', 'cta': 'Bạn nghĩ sao về điều này?'}",
            # Trailing commas
            '{"hook": "Bí mật bất ngờ bị lộ?", "body": "Nội dung...", "cta": "Ý kiến bạn ra sao?",}',
            # Conversational text without JSON
            "Xin chào! Đây là kịch bản tôi soạn:\nHook: Cảnh báo sự thật chấn động?\nBody: Nội dung bóc mẽ...\nCTA: Bạn nghĩ sao?",
            # JSON with null values
            '{"hook": null, "body": null, "cta": null, "scenes": null, "hashtags": null}',
            # JSON with corrupted scene objects
            '{"hook": "Sự thật?", "scenes": ["invalid", 123, null]}',
            # Empty text
            "",
            # None input
            None,
        ]

        for payload in adversarial_payloads:
            parsed = self_healing_json_parser(payload, "Test Title", "Test Summary")
            self.assertIsInstance(parsed, dict)
            self.assertTrue(len(str(parsed.get("hook", ""))) > 0)
            self.assertTrue(len(str(parsed.get("body", ""))) > 0)
            self.assertTrue(len(str(parsed.get("cta", ""))) > 0)
            self.assertEqual(len(parsed.get("scenes", [])), 4)

    def test_generate_tiktok_script_engine_validation(self) -> None:
        """generate_tiktok_script must reject invalid engine names with ValueError."""
        with self.assertRaises(ValueError):
            generate_tiktok_script("Title", "Summary", engine="invalid_engine")

    def test_generate_tiktok_script_offline_safe_fallback(self) -> None:
        """generate_tiktok_script with safe_fallback=True must succeed deterministically offline when AI calls fail."""
        with patch("src.ai.generator.execute_chat_completion", side_effect=RuntimeError("Simulated network outage")):
            res = generate_tiktok_script("Title", "Summary", engine="gemini", safe_fallback=True)
            self.assertIsInstance(res, dict)
            self.assertEqual(len(res.get("scenes", [])), 4)
            self.assertIn("offline_fallback", res.get("engine_used", ""))


class TestCardRenderingConcurrencyAndStability(unittest.TestCase):
    """Stress tests on concurrency, throughput, and memory stability during card rendering."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="challenger_conc_")
        self.synth = SafeFallbackSynthesizer()

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_concurrent_card_rendering_20_threads_100_cards(self) -> None:
        """20 concurrent threads rendering 100 cards across all 5 themes simultaneously."""
        num_cards = 100
        max_workers = 20

        def render_worker(card_id: int) -> Path:
            theme = ALL_THEMES[card_id % len(ALL_THEMES)]
            card_tmp = Path(self.temp_dir) / f"worker_{card_id}"
            card_tmp.mkdir(parents=True, exist_ok=True)
            return self.synth._generate_card(
                title=f"CARD #{card_id}",
                headline=f"Nội dung phân cảnh đồng thời số {card_id} theo phong cách theme {theme}",
                color=THEME_PRESETS[theme]["title_color"],
                ref_image_path=None,
                temp_dir=card_tmp,
                scene_num=(card_id % 4) + 1,
                theme=theme
            )

        t_start = time.perf_counter()
        results: List[Path] = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(render_worker, i) for i in range(num_cards)]
            for f in as_completed(futures):
                results.append(f.result())
        t_elapsed = time.perf_counter() - t_start

        self.assertEqual(len(results), num_cards, "All 100 cards must be rendered")
        for p in results:
            self.assertTrue(p.exists(), f"Card output file missing: {p}")
            self.assertGreater(p.stat().st_size, 5000, f"Card file too small: {p}")

        throughput = num_cards / t_elapsed
        self.assertGreater(throughput, 10.0, f"Throughput too low: {throughput:.1f} cards/sec")

    def test_rapid_sequential_card_rendering_latency(self) -> None:
        """Rapid sequential rendering of 25 cards must maintain average latency < 200ms per card."""
        latencies: List[float] = []
        for i in range(25):
            theme = ALL_THEMES[i % len(ALL_THEMES)]
            t0 = time.perf_counter()
            out = self.synth._generate_card(
                title="LATENCY TEST",
                headline="Kiểm tra độ trễ kết xuất tức thì phục vụ live preview UI",
                color=THEME_PRESETS[theme]["title_color"],
                ref_image_path=None,
                temp_dir=Path(self.temp_dir),
                scene_num=(i % 4) + 1,
                theme=theme
            )
            latencies.append(time.perf_counter() - t0)
            self.assertTrue(out.exists())

        avg_latency = sum(latencies) / len(latencies)
        self.assertLess(avg_latency, 0.20, f"Average latency too high: {avg_latency*1000:.1f}ms")

    def test_memory_stability_across_repeated_renders(self) -> None:
        """Repeated rendering of 60 cards must not cause memory leaks."""
        gc.collect()
        tracemalloc.start()
        snapshot1 = tracemalloc.take_snapshot()

        for i in range(60):
            theme = ALL_THEMES[i % len(ALL_THEMES)]
            self.synth._generate_card(
                title="MEM TEST",
                headline=f"Memory leak inspection card index {i}",
                color=THEME_PRESETS[theme]["title_color"],
                ref_image_path=None,
                temp_dir=Path(self.temp_dir),
                scene_num=(i % 4) + 1,
                theme=theme
            )

        gc.collect()
        snapshot2 = tracemalloc.take_snapshot()
        top_stats = snapshot2.compare_to(snapshot1, 'lineno')
        total_growth_kb = sum(stat.size_diff for stat in top_stats) / 1024
        tracemalloc.stop()

        # Memory growth should not exceed 30MB across 60 renders
        self.assertLess(total_growth_kb, 30 * 1024, f"Memory growth too high: {total_growth_kb:.1f}KB")


class TestContentEvaluatorAdversarialCheck(unittest.TestCase):
    """Check how content_evaluator grades fallback and edge case scripts."""

    def test_fallback_script_achieves_passing_evaluator_score(self) -> None:
        """safe_script_fallback outputs must achieve >= 65 score in evaluate_tiktok_script."""
        cases = [
            ("Lừa đảo chuyển khoản ngân hàng", "Các đối tượng giả mạo tin nhắn SMS Brandname của ngân hàng để chiếm đoạt tài khoản"),
            ("Chíp bán dẫn 2nm AI", "Bước đột phá công nghệ mới giúp tăng gấp đôi hiệu năng xử lý tác vụ trí tuệ nhân tạo"),
            ("Bản tin vắn", "Tóm tắt ngắn gọn"),
        ]

        for title, summary in cases:
            script = safe_script_fallback(title, summary)
            source_text = f"{title} {summary}"
            eval_res = evaluate_tiktok_script(script, source_text)
            self.assertGreaterEqual(
                eval_res["overall_score"],
                65.0,
                f"Score {eval_res['overall_score']} below threshold 65 for title '{title}'. Breakdown: {eval_res['breakdown']}"
            )
            self.assertIn(eval_res["grade"], ["S", "A", "B"])


if __name__ == "__main__":
    unittest.main()
