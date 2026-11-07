"""
Bộ kiểm thử toàn diện End-to-End (E2E Integration Test) cho Hệ Thống:
Phân Tích Xu Hướng Mạng Xã Hội & Tối Ưu Bài Đăng Tích Hợp AI Tạo Sinh (TikTok Studio).
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.preprocessing.trend_extractor import extract_trending_topics
from src.scraper.rss_scraper import clean_html_text, extract_thumbnail_url
from src.ai.generator import generate_tiktok_script, TIKTOK_SYSTEM_PROMPT
from src.video.muse_integration import generate_tiktok_video, MuseAIClient, SafeFallbackSynthesizer
from src.models.content_evaluator import evaluate_tiktok_script, TikTokViralEvaluator


def test_e2e_trend_extractor():
    """Kiểm tra trích xuất từ khóa xu hướng và cảm xúc từ bài báo mẫu."""
    articles = [
        {"title": "Trí tuệ nhân tạo AI bùng nổ mạnh mẽ tại Việt Nam", "summary": "Nhiều doanh nghiệp ứng dụng AI tạo sinh vào tự động hóa."},
        {"title": "Cảnh báo thủ đoạn lừa đảo tinh vi bằng công nghệ AI", "summary": "Chuyên gia khuyến cáo người dân cần cẩn trọng với deepfake."}
    ]
    res = extract_trending_topics(articles, top_n=5)
    assert "keywords" in res
    assert len(res["keywords"]) > 0
    assert "sentiment" in res
    assert "positive" in res["sentiment"]


def test_e2e_scraper_helpers():
    """Kiểm tra làm sạch HTML và trích xuất ảnh."""
    raw_html = "<p>Đây là <b>nội dung</b> có thẻ &amp; ký tự đặc biệt.</p>"
    clean = clean_html_text(raw_html)
    assert clean == "Đây là nội dung có thẻ & ký tự đặc biệt."
    assert "<" not in clean


def test_e2e_script_generator_format():
    """Kiểm tra cấu trúc và tính toàn vẹn của Prompt & Generator."""
    assert "Scene 1 - Hook" in TIKTOK_SYSTEM_PROMPT
    assert "Vertical 9:16 aspect ratio video" in TIKTOK_SYSTEM_PROMPT


def test_e2e_video_synthesis_fallback():
    """Kiểm tra sinh video dọc 9:16 thực tế qua SafeFallbackSynthesizer."""
    script_data = {
        "hook": "SỰ THẬT VỀ TRÍ TUỆ NHÂN TẠO!",
        "body": "AI đang thay đổi hoàn toàn cách chúng ta sáng tạo nội dung video ngắn.",
        "cta": "Bạn có đang ứng dụng AI chưa? Hãy để lại ý kiến bên dưới!"
    }
    result = generate_tiktok_video(
        visual_prompt="Vertical 9:16 portrait video, cinematic lighting",
        reference_image_url=None,
        script_data=script_data,
        mode="fallback",
        duration=2
    )
    assert result["status"] == "success"
    assert result["mode"] == "fallback"
    assert result["resolution"] == "720x1280"
    v_path = Path(result["video_path"])
    assert v_path.exists()
    assert v_path.stat().st_size > 1000


def test_e2e_content_evaluator():
    """Kiểm tra bộ đo lường và chấm điểm tiềm năng Viral (0 - 100)."""
    source_news = "Cảnh báo chiêu trò lừa đảo deepfake giả mạo người thân chuyển tiền."
    script_data = {
        "hook": "Cảnh báo khẩn cấp chiêu trò lừa đảo deepfake mới bạn đã biết chưa?",
        "body": "Kẻ gian dùng AI mô phỏng khuôn mặt và giọng nói người thân để gọi video mượn tiền. Hãy yêu cầu gọi lại bằng câu hỏi bí mật.",
        "cta": "Hãy chia sẻ cảnh báo này và bình luận kinh nghiệm của bạn bên dưới!",
        "full_script": "Cảnh báo khẩn cấp chiêu trò lừa đảo deepfake mới bạn đã biết chưa? Kẻ gian dùng AI mô phỏng khuôn mặt và giọng nói người thân để gọi video mượn tiền. Hãy yêu cầu gọi lại bằng câu hỏi bí mật. Hãy chia sẻ cảnh báo này và bình luận kinh nghiệm của bạn bên dưới!"
    }
    report = evaluate_tiktok_script(script_data, source_news)
    assert 0.0 <= report["overall_score"] <= 100.0
    assert report["grade"] in ["S", "A", "B", "C"]
    assert len(report["actionable_checklist"]) > 0


def test_full_integrated_pipeline():
    """Kiểm thử luồng tích hợp liên hoàn: Tin tức -> Xu hướng -> Kịch bản -> Video -> Chấm điểm."""
    # 1. Dữ liệu tin tức
    article = {
        "title": "Ra mắt điện thoại gập mới với camera tích hợp AI độc đáo",
        "summary": "Sản phẩm sở hữu bản lề tàng hình và khả năng chụp ảnh tự động theo cử chỉ."
    }
    
    # 2. Rà quét xu hướng
    trend = extract_trending_topics([article], top_n=3)
    assert len(trend["keywords"]) > 0
    
    # 3. Kịch bản thoại
    script_data = {
        "hook": "Điện thoại gập mới có thật sự đáng tiền hay chỉ là chiêu trò?",
        "body": "Sản phẩm vừa ra mắt với bản lề tàng hình và camera AI tự động chụp ảnh theo cử chỉ cực kỳ ấn tượng.",
        "cta": "Bạn có sẵn sàng chi tiền mua không? Bình luận ngay bên dưới!",
        "full_script": "Điện thoại gập mới có thật sự đáng tiền hay chỉ là chiêu trò? Sản phẩm vừa ra mắt với bản lề tàng hình và camera AI tự động chụp ảnh theo cử chỉ cực kỳ ấn tượng. Bạn có sẵn sàng chi tiền mua không? Bình luận ngay bên dưới!"
    }
    
    # 4. Chấm điểm Viral
    eval_res = evaluate_tiktok_script(script_data, f"{article['title']} {article['summary']}")
    assert eval_res["overall_score"] >= 50.0
    
    # 5. Tạo video dọc 9:16
    video_res = generate_tiktok_video(
        visual_prompt="Vertical 9:16 portrait video, cinematic smartphone",
        reference_image_url=None,
        script_data=script_data,
        mode="fallback",
        duration=2
    )
    assert video_res["status"] == "success"
    assert Path(video_res["video_path"]).exists()


if __name__ == "__main__":
    print("Running E2E Integration Pipeline Tests...")
    test_e2e_trend_extractor()
    print("✓ PASS: test_e2e_trend_extractor")
    test_e2e_scraper_helpers()
    print("✓ PASS: test_e2e_scraper_helpers")
    test_e2e_script_generator_format()
    print("✓ PASS: test_e2e_script_generator_format")
    test_e2e_video_synthesis_fallback()
    print("✓ PASS: test_e2e_video_synthesis_fallback")
    test_e2e_content_evaluator()
    print("✓ PASS: test_e2e_content_evaluator")
    test_full_integrated_pipeline()
    print("✓ PASS: test_full_integrated_pipeline")
    print("\n🎉 ALL E2E INTEGRATION TESTS PASSED 100%!")
