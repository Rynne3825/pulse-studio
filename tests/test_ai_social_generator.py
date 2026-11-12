"""Unit tests for src/ai/generator.py (generate_social_post, refine_post, parser)."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ai import generator
from src.ai.generator import (
    generate_social_post,
    refine_post,
    resolve_model_candidates,
    safe_social_post_fallback,
    self_healing_json_parser,
)

REQUIRED_KEYS = {"hook", "body", "cta", "hashtags", "full_post", "platform", "style", "model_name", "engine_used"}

FB_JSON = {
    "hook": "Điều bất ngờ về AI",
    "body": "Đoạn 1.\n\nĐoạn 2.\n\nĐoạn 3.",
    "cta": "Bạn nghĩ sao về chuyện này?",
    "hashtags": ["#AI", "#CongNghe", "#Tin"],
    "full_post": "Điều bất ngờ về AI\n\nĐoạn 1.\n\nBạn nghĩ sao về chuyện này?\n\n#AI #CongNghe #Tin",
}


def _patched(raw: str):
    return patch.multiple(
        generator,
        detect_router_base_url=lambda: "http://127.0.0.1:20128/v1",
        execute_chat_completion=lambda *a, **k: (raw, "ag/gemini-3.8-flash-medium"),
    )


class TestModelCandidates:
    def test_only_gemini_38_flash(self):
        models = resolve_model_candidates()
        assert models
        assert all("gemini-3.8-flash" in m for m in models)
        assert not any("argon" in m or m == "agy" for m in models)


class TestGenerateSocialPost:
    @pytest.mark.parametrize("platform", ["facebook", "threads"])
    def test_contract(self, platform):
        with _patched(json.dumps(FB_JSON)):
            res = generate_social_post("Tiêu đề", "Tóm tắt", platform=platform, style="trend")
        assert REQUIRED_KEYS <= set(res)
        assert res["platform"] == platform
        assert res["engine_used"] == "gemini"
        assert isinstance(res["hashtags"], list)

    def test_markdown_fenced_json(self):
        with _patched("```json\n" + json.dumps(FB_JSON) + "\n```"):
            res = generate_social_post("T", "S")
        assert res["hook"] == FB_JSON["hook"]

    def test_gateway_failure_uses_fallback(self):
        def boom(*a, **k):
            raise RuntimeError("down")

        with patch.multiple(generator, detect_router_base_url=lambda: "http://x/v1", execute_chat_completion=boom):
            res = generate_social_post("Giá vàng tăng", "Giá vàng tăng mạnh", platform="threads")
        assert "offline_fallback" in res["engine_used"]
        assert res["full_post"].strip()

    def test_gateway_failure_raises_without_fallback(self):
        def boom(*a, **k):
            raise RuntimeError("down")

        with patch.multiple(generator, detect_router_base_url=lambda: "http://x/v1", execute_chat_completion=boom):
            with patch.dict("os.environ", {"AI_SAFE_FALLBACK": ""}):
                with pytest.raises(RuntimeError):
                    generate_social_post("T", "S", safe_fallback=False)


class TestRefinePost:
    def test_refine_returns_contract(self):
        with _patched(json.dumps(FB_JSON)):
            res = refine_post("bài cũ", ["Thiếu CTA"], platform="facebook", title="T", summary="S")
        assert REQUIRED_KEYS <= set(res)
        assert res["style"] == "optimized"
        assert res["platform"] == "facebook"

    def test_refine_threads(self):
        with _patched(json.dumps(FB_JSON)):
            res = refine_post("bài cũ", [], platform="threads")
        assert res["platform"] == "threads"


class TestParserEdgeCases:
    @pytest.mark.parametrize(
        "raw",
        ["", "   ", "not json at all", "{", "[]", "null", "{'hook': 'a', 'body': 'b', 'cta': 'c?',}"],
    )
    def test_never_crashes(self, raw):
        res = self_healing_json_parser(raw, "Tiêu đề", "Tóm tắt", "facebook")
        assert isinstance(res, dict)
        assert res.get("full_post", "").strip()
        assert isinstance(res.get("hashtags", []), list)

    def test_trailing_comma(self):
        res = self_healing_json_parser('{"hook": "H", "body": "B", "cta": "C?", "hashtags": ["#a"],}', "T", "S", "threads")
        assert res["hook"] == "H"

    def test_fallback_has_fields(self):
        res = safe_social_post_fallback("Tiêu đề", "Tóm tắt", platform="facebook", style="trend")
        assert REQUIRED_KEYS <= set(res)

