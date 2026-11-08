"""
Bộ kiểm thử tự động cho Milestone M3: Tầng Tạo Sinh Video Muse AI & Safe Fallback Engine.
"""

import os
import sys
from unittest.mock import patch, MagicMock
from pathlib import Path

# Đảm bảo import được src khi chạy script trực tiếp
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.video.muse_integration import (
    find_ffmpeg_binary,
    MuseAIClient,
    SafeFallbackSynthesizer,
    generate_tiktok_video,
    synthesize_voiceover
)


def test_find_ffmpeg_binary():
    """Kiểm tra phát hiện binary FFmpeg trong hệ thống."""
    bin_path = find_ffmpeg_binary()
    assert bin_path is not None
    assert len(bin_path) > 0


def test_muse_client_unconfigured():
    """Kiểm tra Client khi chưa có API Key."""
    client = MuseAIClient(base_url="http://localhost:8000/v1", api_key="")
    assert client.is_configured() is False


def test_muse_client_configured():
    """Kiểm tra Client khi đã có API Key."""
    client = MuseAIClient(base_url="http://localhost:8000/v1", api_key="m2a_valid_token_test")
    assert client.is_configured() is True


@patch("src.video.muse_integration.requests.post")
def test_muse_create_video_task_success(mock_post):
    """Kiểm tra tạo task video qua Muse API."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "task_123456", "status": "queued"}
    mock_post.return_value = mock_resp

    client = MuseAIClient(api_key="test_key")
    task_id = client.create_video_task(
        prompt="Vertical 9:16 portrait video of news topic",
        ref_image_url="https://example.com/character.jpg",
        duration=5
    )
    assert task_id == "task_123456"
    assert mock_post.called


@patch("src.video.muse_integration.requests.get")
def test_muse_poll_task_status_success(mock_get):
    """Kiểm tra polling trạng thái task hoàn thành và trích xuất URL video."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "status": "succeeded",
        "result": {"url": "https://example.com/videos/video_out.mp4"}
    }
    mock_get.return_value = mock_resp

    client = MuseAIClient(api_key="test_key")
    v_url = client.poll_task_status("task_123456", timeout_seconds=5)
    assert v_url == "https://example.com/videos/video_out.mp4"


def test_safe_fallback_synthesizer_real_render(tmp_path):
    """Kiểm tra render video dọc 9:16 thực tế bằng SafeFallbackSynthesizer."""
    synthesizer = SafeFallbackSynthesizer()
    script_data = {
        "hook": "CẢNH BÁO LỪA ĐẢO TIKTOK NGUY HIỂM!",
        "body": "Thủ đoạn mạo danh thương hiệu tinh vi đang xuất hiện tràn lan.",
        "cta": "Hãy chia sẻ ngay cho bạn bè cùng biết!"
    }
    
    # Render video 2 giây thực tế
    result = synthesizer.synthesize(script_data=script_data, ref_image_url=None, duration=2)
    
    assert result["status"] == "success"
    assert result["mode"] == "fallback"
    assert result["resolution"] == "720x1280"
    assert result["duration"] == 2.0
    
    video_file = Path(result["video_path"])
    assert video_file.exists()
    assert video_file.stat().st_size > 1000  # Đã tạo file MP4 có dữ liệu thật


def test_generate_tiktok_video_auto_mode():
    """Kiểm tra hàm Façade cấp cao generate_tiktok_video ở chế độ auto."""
    script_data = {
        "hook": "ĐỪNG VỘI MUA KHI CHƯA BIẾT!",
        "body": "Đánh giá chi tiết sản phẩm hot nhất hôm nay.",
        "cta": "Bấm theo dõi để không bỏ lỡ tin mới!"
    }
    
    res = generate_tiktok_video(
        visual_prompt="Vertical 9:16 portrait video, cinematic lighting",
        reference_image_url=None,
        script_data=script_data,
        mode="auto",
        duration=2
    )
    assert res["status"] == "success"
    assert "video_path" in res
    assert Path(res["video_path"]).exists()


def test_synthesize_voiceover_edge_tts(tmp_path):
    """Kiểm tra tổng hợp giọng đọc tiếng Việt bằng edge-tts."""
    target_dir = Path(tmp_path) if tmp_path else Path(".")
    out_file = target_dir / "test_voice_edge.mp3"
    try:
        ok = synthesize_voiceover("Thử nghiệm giọng đọc tiếng Việt Hoài My.", out_file, voice="vi-VN-HoaiMyNeural")
        assert ok is True
        assert out_file.exists()
        assert out_file.stat().st_size > 1000
    finally:
        out_file.unlink(missing_ok=True)


def test_synthesize_voiceover_google_fallback(tmp_path):
    """Kiểm tra fallback sang Google Translate TTS khi edge-tts không phản hồi."""
    target_dir = Path(tmp_path) if tmp_path else Path(".")
    out_file = target_dir / "test_voice_fallback.mp3"
    try:
        with patch("src.video.muse_integration._synthesize_edge_tts", return_value=False):
            ok = synthesize_voiceover("Thử nghiệm giọng đọc dự phòng tiếng Việt.", out_file)
            assert ok is True
            assert out_file.exists()
            assert out_file.stat().st_size > 1000
    finally:
        out_file.unlink(missing_ok=True)


def test_synthesize_voiceover_terminal_fallback(tmp_path):
    """Kiểm tra terminal fallback âm thanh im lặng khi toàn bộ engine TTS lỗi mạng."""
    target_dir = Path(tmp_path) if tmp_path else Path(".")
    out_file = target_dir / "test_voice_silent.mp3"
    try:
        with patch("src.video.muse_integration._synthesize_edge_tts", return_value=False), \
             patch("src.video.muse_integration._synthesize_google_tts", return_value=False):
            ok = synthesize_voiceover("Thử nghiệm toàn bộ engine thất bại.", out_file)
            assert ok is False
            assert out_file.exists()
            assert out_file.stat().st_size > 500
    finally:
        out_file.unlink(missing_ok=True)


if __name__ == "__main__":
    print("Running M3 Tests...")
    test_find_ffmpeg_binary()
    print("PASS: test_find_ffmpeg_binary")
    test_muse_client_unconfigured()
    print("PASS: test_muse_client_unconfigured")
    test_muse_client_configured()
    print("PASS: test_muse_client_configured")
    test_muse_create_video_task_success()
    print("PASS: test_muse_create_video_task_success")
    test_muse_poll_task_status_success()
    print("PASS: test_muse_poll_task_status_success")
    test_safe_fallback_synthesizer_real_render(None)
    print("PASS: test_safe_fallback_synthesizer_real_render")
    test_generate_tiktok_video_auto_mode()
    print("PASS: test_generate_tiktok_video_auto_mode")
    test_synthesize_voiceover_edge_tts(None)
    print("PASS: test_synthesize_voiceover_edge_tts")
    test_synthesize_voiceover_google_fallback(None)
    print("PASS: test_synthesize_voiceover_google_fallback")
    test_synthesize_voiceover_terminal_fallback(None)
    print("PASS: test_synthesize_voiceover_terminal_fallback")
    print("=== ALL 10 M3 TESTS PASSED PERFECTLY! ===")


