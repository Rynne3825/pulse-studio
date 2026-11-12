"""Tests for PostViralEvaluator (platform-adaptive Facebook / Threads scoring)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.eval.scorer import PostViralEvaluator, evaluate_post

SOURCE = "Giá vàng trong nước tăng mạnh phiên sáng nay, nhà đầu tư chú ý biến động giá vàng"


def _words(n: int) -> str:
    return " ".join(["từ"] * n)


def test_hook_empty():
    assert PostViralEvaluator().calculate_hook_score("")["score"] == 0.0


def test_hook_strong():
    res = PostViralEvaluator().calculate_hook_score("Sự thật chấn động về iPhone 16 bạn đã biết chưa?")
    assert res["score"] >= 90.0
    assert res["word_count"] <= 15


def test_cta_empty_and_strong():
    ev = PostViralEvaluator()
    assert ev.calculate_cta_score("")["score"] == 20.0
    strong = ev.calculate_cta_score("Bạn nghĩ sao? Hãy để lại bình luận nhé!")
    assert strong["score"] >= 80.0
    assert strong["matched_keywords"]


def test_cosine_similarity_relevant_vs_irrelevant():
    ev = PostViralEvaluator()
    rel = ev.calculate_trend_similarity(SOURCE, "Giá vàng tăng mạnh, nhà đầu tư theo dõi biến động giá vàng")
    irr = ev.calculate_trend_similarity(SOURCE, "Công thức nấu phở bò truyền thống ngon tuyệt")
    assert rel["score"] > irr["score"]
    assert 0.0 <= rel["cosine_raw"] <= 1.0


def test_pacing_platform_adaptive():
    ev = PostViralEvaluator()
    text = _words(60)
    threads = ev.calculate_pacing_score(text, platform="threads")["score"]
    facebook = ev.calculate_pacing_score(text, platform="facebook")["score"]
    assert threads == 100.0
    assert facebook < threads

    long_text = _words(75) + "\n" + _words(75)
    assert ev.calculate_pacing_score(long_text, platform="facebook")["score"] == 100.0
    assert ev.calculate_pacing_score(long_text, platform="threads")["score"] < 70.0
    assert ev.calculate_pacing_score("", platform="facebook")["score"] == 0.0


def _post(platform: str, words: int) -> dict:
    return {
        "hook": "Sự thật về giá vàng bạn chưa biết?",
        "body": _words(words),
        "cta": "Bạn nghĩ sao? Hãy để lại bình luận nhé!",
        "hashtags": ["#giavang"],
        "platform": platform,
    }


def test_evaluate_structure_and_weights():
    res = evaluate_post(_post("facebook", 120), SOURCE, platform="facebook")
    assert set(res["breakdown"]) == {"hook_score", "trend_similarity_score", "pacing_score", "cta_score"}
    b = res["breakdown"]
    expected = b["hook_score"] * 0.25 + b["trend_similarity_score"] * 0.35 + b["pacing_score"] * 0.20 + b["cta_score"] * 0.20
    assert abs(res["overall_score"] - round(expected, 1)) <= 0.11
    assert res["grade"] in {"S", "A", "B", "C"}
    assert isinstance(res["actionable_checklist"], list)
    assert res["metrics"]["platform"] == "facebook"


def test_evaluate_platform_difference():
    fb = evaluate_post(_post("facebook", 55), SOURCE, platform="facebook")
    th = evaluate_post(_post("threads", 55), SOURCE, platform="threads")
    assert th["breakdown"]["pacing_score"] > fb["breakdown"]["pacing_score"]


def test_evaluate_empty_post_is_low_grade():
    res = evaluate_post({"platform": "facebook"}, SOURCE)
    assert res["grade"] == "C"
    assert res["actionable_checklist"]

