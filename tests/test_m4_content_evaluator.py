"""
Bộ kiểm thử tự động cho Milestone M4: Tầng Đánh Giá & Tối Ưu Nội Dung (Viral Content Evaluator).
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.models.content_evaluator import (
    TikTokViralEvaluator,
    evaluate_tiktok_script
)


def test_hook_score_empty():
    evaluator = TikTokViralEvaluator()
    res = evaluator.calculate_hook_score("")
    assert res["score"] == 0.0


def test_hook_score_strong():
    evaluator = TikTokViralEvaluator()
    # Có từ khóa 'sự thật', có dấu hỏi '?', dưới 15 từ
    res = evaluator.calculate_hook_score("Sự thật chấn động về iPhone 16 bạn đã biết chưa?")
    assert res["score"] >= 90.0
    assert "sự thật" in res["matched_keywords"]
    assert res["word_count"] <= 15


def test_hook_score_long_penalty():
    evaluator = TikTokViralEvaluator()
    long_hook = "Đây là một câu mở đầu rất dài dòng và không có điểm nhấn gián tiếp khiến cho người xem cảm thấy vô cùng buồn ngủ và muốn lướt qua ngay lập tức"
    res = evaluator.calculate_hook_score(long_hook)
    assert res["word_count"] > 15
    assert res["score"] < 70.0


def test_trend_similarity_aligned():
    evaluator = TikTokViralEvaluator()
    source = "Apple ra mắt iPhone 16 với tính năng camera nút bấm mới và chip A18 Pro nâng cấp mạnh mẽ."
    script = "iPhone 16 vừa ra mắt với chip A18 Pro và nút bấm camera mới nhưng có đáng mua không?"
    res = evaluator.calculate_trend_similarity(source, script)
    assert res["score"] >= 50.0
    assert 0.0 <= res["cosine_raw"] <= 1.0


def test_pacing_score_optimal():
    evaluator = TikTokViralEvaluator()
    script = " ".join(["từ"] * 75)
    res = evaluator.calculate_pacing_score(script)
    assert res["score"] == 100.0
    assert res["word_count"] == 75


def test_pacing_score_too_short():
    evaluator = TikTokViralEvaluator()
    script = "Quá ngắn ngủi chỉ vài ba từ."
    res = evaluator.calculate_pacing_score(script)
    assert res["score"] < 50.0


def test_cta_score_strong():
    evaluator = TikTokViralEvaluator()
    res = evaluator.calculate_cta_score("Bạn nghĩ sao về điều này? Hãy để lại bình luận bên dưới nhé!")
    assert res["score"] >= 90.0
    assert len(res["matched_keywords"]) > 0


def test_evaluate_full_script():
    source_news = "Bộ Y tế cảnh báo nhiều vụ ngộ độc thực phẩm do vi khuẩn Clostridium botulinum trong thực phẩm đóng hộp."
    script_data = {
        "hook": "Cảnh báo khẩn cấp về ngộ độc thực phẩm botulinum nguy hiểm chết người!",
        "body": "Bộ Y tế vừa phát hiện nhiều ca ngộ độc nặng do sử dụng đồ hộp kém chất lượng. Độc tố này có thể gây tê liệt cơ hô hấp cực kỳ nhanh chóng.",
        "cta": "Bạn có hay ăn đồ hộp không? Hãy để lại bình luận và chia sẻ cảnh báo này ngay!",
        "full_script": "Cảnh báo khẩn cấp về ngộ độc thực phẩm botulinum nguy hiểm chết người! Bộ Y tế vừa phát hiện nhiều ca ngộ độc nặng do sử dụng đồ hộp kém chất lượng. Độc tố này có thể gây tê liệt cơ hô hấp cực kỳ nhanh chóng. Bạn có hay ăn đồ hộp không? Hãy để lại bình luận và chia sẻ cảnh báo này ngay!"
    }
    
    report = evaluate_tiktok_script(script_data, source_news)
    assert 0.0 <= report["overall_score"] <= 100.0
    assert report["grade"] in ["S", "A", "B", "C"]
    assert len(report["actionable_checklist"]) > 0
    assert "hook_score" in report["breakdown"]
    assert "trend_similarity_score" in report["breakdown"]
    assert "pacing_score" in report["breakdown"]
    assert "cta_score" in report["breakdown"]
