"""
Bộ kiểm thử đối kháng (Adversarial Challenge & Stress Harness) cho Milestone M2:
Định tuyến Dual-Engine (Gemini / Muse AI) & Cơ chế Dự phòng Phân cấp (Hierarchical Fallback).
Mô phỏng:
- Connection Refusals (ECONNREFUSED)
- Timeouts (Connect / Read)
- HTTP 400, 404, 429, 500, 502, 503
- Network Drops & Socket Reset (ChunkedEncodingError, ProtocolError)
- Invalid Model Names & Candidate Exhaustion
- Corrupted 200 OK Payloads (HTML Cloudflare, Empty Choices, Null Content)
- DNS Failure & Black Hole Ports
- Hierarchical Fallback (Muse -> Gemini -> Safe Script)
"""

import os
import sys
import json
import socket
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import requests
from src.ai.generator import (
    generate_tiktok_script,
    safe_script_fallback,
    detect_router_base_url,
    is_port_reachable,
    execute_chat_completion,
    resolve_model_candidates
)


def mock_response(status_code: int = 200, json_body: Any = None, raw_text: str = "") -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    if json_body is not None:
        raw_text = json.dumps(json_body, ensure_ascii=False)
        resp.json.return_value = json_body
    else:
        try:
            resp.json.return_value = json.loads(raw_text)
        except Exception:
            resp.json.side_effect = json.JSONDecodeError("Invalid JSON", raw_text, 0)
    resp.text = raw_text
    resp.content = raw_text.encode("utf-8")
    return resp


def make_valid_chat_completion(model: str = "ag/gemini-3.8-flash-low") -> Dict[str, Any]:
    content = {
        "hook": "Sự thật chấn động đằng sau thủ đoạn lừa đảo ngân hàng?",
        "body": "Kẻ gian sử dụng thiết bị BTS giả mạo để mạo danh tin nhắn thương hiệu ngân hàng uy tín, chiếm đoạt tiền tỉ trong chớp mắt. Người dân cần hết sức cảnh giác.",
        "cta": "Bạn có từng nhận được tin nhắn mạo danh này chưa? Hãy chia sẻ ngay dưới phần bình luận nhé!",
        "hashtags": ["#bocme", "#canhbao", "#trending", "#tiktoknews"],
        "full_script": "Sự thật chấn động đằng sau thủ đoạn lừa đảo ngân hàng? Kẻ gian sử dụng thiết bị BTS giả mạo để mạo danh tin nhắn thương hiệu ngân hàng uy tín, chiếm đoạt tiền tỉ trong chớp mắt. Người dân cần hết sức cảnh giác. Bạn có từng nhận được tin nhắn mạo danh này chưa? Hãy chia sẻ ngay dưới phần bình luận nhé! #bocme #canhbao #trending #tiktoknews",
        "muse_visual_prompt": "Vertical 9:16 aspect ratio video, dramatic cinematic lighting, investigative realism, moody atmosphere, photorealistic 4K, cinematic slow dolly push-in."
    }
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 1730950000,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": json.dumps(content)
                },
                "finish_reason": "stop"
            }
        ]
    }


class AdversarialDualEngineTests(unittest.TestCase):
    """Suite 1: Mô phỏng lỗi mạng nghiêm trọng trên Muse và xác minh Fallback sang Gemini."""

    @patch("requests.post")
    def test_muse_connection_refused_falls_back_to_gemini(self, mock_post):
        """Muse gặp Connection Refused -> Fallback sang Gemini thành công."""
        def side_effect(*args, **kwargs):
            model = kwargs.get("json", {}).get("model", "")
            if "muse" in model.lower():
                raise requests.exceptions.ConnectionError("Connection refused by target host")
            return mock_response(200, make_valid_chat_completion(model="ag/gemini-3.8-flash-medium"))

        mock_post.side_effect = side_effect
        res = generate_tiktok_script("Tin nóng", "Tóm tắt tin tức", engine="muse")
        self.assertEqual(res["engine_used"], "muse (fallback: gemini)")
        self.assertIn("gemini", res["model_name"])
        self.assertTrue(len(res["hook"]) > 0)
        self.assertIn("9:16", res["muse_visual_prompt"])

    @patch("requests.post")
    def test_muse_timeout_falls_back_to_gemini(self, mock_post):
        """Muse bị Timeout (ConnectTimeout / ReadTimeout) -> Fallback sang Gemini thành công."""
        def side_effect(*args, **kwargs):
            model = kwargs.get("json", {}).get("model", "")
            if "muse" in model.lower():
                raise requests.exceptions.Timeout("Read timed out after 35 seconds")
            return mock_response(200, make_valid_chat_completion(model="ag/gemini-3.8-flash-low"))

        mock_post.side_effect = side_effect
        res = generate_tiktok_script("Tin nóng", "Tóm tắt tin tức", engine="muse")
        self.assertEqual(res["engine_used"], "muse (fallback: gemini)")
        self.assertIn("gemini", res["model_name"])

    @patch("requests.post")
    def test_muse_http_400_falls_back_to_gemini(self, mock_post):
        """Muse gặp HTTP 400 (Model is unavailable) -> Fallback sang Gemini thành công."""
        def side_effect(*args, **kwargs):
            model = kwargs.get("json", {}).get("model", "")
            if "muse" in model.lower():
                return mock_response(400, {"error": {"message": "Model is unavailable", "code": "bad_request"}})
            return mock_response(200, make_valid_chat_completion(model="ag/gemini-3.8-flash-low"))

        mock_post.side_effect = side_effect
        res = generate_tiktok_script("Tin nóng", "Tóm tắt tin tức", engine="muse")
        self.assertEqual(res["engine_used"], "muse (fallback: gemini)")

    @patch("requests.post")
    def test_muse_http_404_not_found_falls_back_to_gemini(self, mock_post):
        """Muse gặp HTTP 404 Not Found (Endpoint hoặc model không tồn tại) -> Fallback sang Gemini."""
        def side_effect(*args, **kwargs):
            model = kwargs.get("json", {}).get("model", "")
            if "muse" in model.lower():
                return mock_response(404, {"error": "Endpoint not found"})
            return mock_response(200, make_valid_chat_completion(model="ag/gemini-3.8-flash-low"))

        mock_post.side_effect = side_effect
        res = generate_tiktok_script("Tin nóng", "Tóm tắt tin tức", engine="muse")
        self.assertEqual(res["engine_used"], "muse (fallback: gemini)")

    @patch("requests.post")
    def test_muse_http_500_502_503_falls_back_to_gemini(self, mock_post):
        """Muse gặp HTTP 500 / 502 Bad Gateway / 503 -> Fallback sang Gemini."""
        for code in [500, 502, 503]:
            def side_effect(*args, **kwargs):
                model = kwargs.get("json", {}).get("model", "")
                if "muse" in model.lower():
                    return mock_response(code, {"error": f"Server Error {code}"})
                return mock_response(200, make_valid_chat_completion(model="ag/gemini-3.8-flash-low"))

            mock_post.side_effect = side_effect
            res = generate_tiktok_script("Tin nóng", "Tóm tắt tin tức", engine="muse")
            self.assertEqual(res["engine_used"], "muse (fallback: gemini)")

    @patch("requests.post")
    def test_muse_http_429_rate_limit_falls_back_to_gemini(self, mock_post):
        """Muse gặp HTTP 429 Rate Limit -> Fallback sang Gemini."""
        def side_effect(*args, **kwargs):
            model = kwargs.get("json", {}).get("model", "")
            if "muse" in model.lower():
                return mock_response(429, {"error": "Quota exceeded / Rate limited"})
            return mock_response(200, make_valid_chat_completion(model="ag/gemini-3.8-flash-low"))

        mock_post.side_effect = side_effect
        res = generate_tiktok_script("Tin nóng", "Tóm tắt tin tức", engine="muse")
        self.assertEqual(res["engine_used"], "muse (fallback: gemini)")

    @patch("requests.post")
    def test_muse_network_drop_chunked_encoding_error(self, mock_post):
        """Mất kết nối giữa chừng (ChunkedEncodingError / socket drop) trên Muse -> Fallback sang Gemini."""
        def side_effect(*args, **kwargs):
            model = kwargs.get("json", {}).get("model", "")
            if "muse" in model.lower():
                raise requests.exceptions.ChunkedEncodingError("Response payload dropped mid-stream")
            return mock_response(200, make_valid_chat_completion(model="ag/gemini-3.8-flash-low"))

        mock_post.side_effect = side_effect
        res = generate_tiktok_script("Tin nóng", "Tóm tắt tin tức", engine="muse")
        self.assertEqual(res["engine_used"], "muse (fallback: gemini)")


class AdversarialCandidateRetryTests(unittest.TestCase):
    """Suite 2: Kiểm thử cơ chế xoay vòng Model Candidates."""

    @patch("requests.post")
    def test_gemini_candidate_retry_sequence(self, mock_post):
        """Gemini thử model 1 bị 400, model 2 bị 500, model 3 thành công 200."""
        calls = []

        def side_effect(*args, **kwargs):
            model = kwargs.get("json", {}).get("model", "")
            calls.append(model)
            if len(calls) == 1:
                return mock_response(400, {"error": "Model 1 unavailable"})
            elif len(calls) == 2:
                return mock_response(500, {"error": "Model 2 crashed"})
            return mock_response(200, make_valid_chat_completion(model=model))

        mock_post.side_effect = side_effect
        res = generate_tiktok_script("Tin nóng", "Tóm tắt", engine="gemini")
        self.assertGreaterEqual(len(calls), 3)
        self.assertEqual(res["engine_used"], "gemini")
        self.assertEqual(res["model_name"], calls[2])


class AdversarialCorrupt200PayloadTests(unittest.TestCase):
    """Suite 3: Gateway trả HTTP 200 nhưng payload dị dạng, HTML hoặc cấu trúc rỗng."""

    @patch("requests.post")
    def test_cloudflare_html_on_200_falls_back(self, mock_post):
        """Gateway trả 200 nhưng chứa HTML Cloudflare (JSONDecodeError)."""
        html_text = "<!DOCTYPE html><html><body>Error 521 Web server is down</body></html>"
        calls = []

        def side_effect(*args, **kwargs):
            model = kwargs.get("json", {}).get("model", "")
            calls.append(model)
            if len(calls) <= 2:
                return mock_response(200, raw_text=html_text)
            return mock_response(200, make_valid_chat_completion(model=model))

        mock_post.side_effect = side_effect
        res = generate_tiktok_script("Tin nóng", "Tóm tắt", engine="gemini")
        self.assertEqual(res["engine_used"], "gemini")

    @patch("requests.post")
    def test_empty_choices_list_on_200(self, mock_post):
        """Gateway trả 200 với choices=[] (IndexError) -> Chuyển sang model kế tiếp."""
        calls = []

        def side_effect(*args, **kwargs):
            model = kwargs.get("json", {}).get("model", "")
            calls.append(model)
            if len(calls) == 1:
                return mock_response(200, json_body={"id": "x", "choices": []})
            return mock_response(200, make_valid_chat_completion(model=model))

        mock_post.side_effect = side_effect
        res = generate_tiktok_script("Tin nóng", "Tóm tắt", engine="gemini")
        self.assertEqual(res["engine_used"], "gemini")

    @patch("requests.post")
    def test_null_content_message(self, mock_post):
        """Gateway trả 200 với message content = null -> Parser điền safe defaults, không crash."""
        payload = {
            "id": "x",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": None}}]
        }
        mock_post.return_value = mock_response(200, json_body=payload)
        res = generate_tiktok_script("Tin nhắn lừa đảo", "Kẻ gian lừa tiền nạn nhân", engine="gemini")
        self.assertIn("Tin nhắn lừa đảo", res["hook"])
        self.assertTrue(len(res["body"]) > 20)
        self.assertIn("9:16", res["muse_visual_prompt"])


class AdversarialHierarchicalFallbackTests(unittest.TestCase):
    """Suite 4: Kiểm thử phân cấp 3 tầng (Muse -> Gemini -> Safe Script) khi thảm họa mạng toàn diện."""

    @patch("requests.post")
    def test_muse_and_gemini_both_fail_with_safe_fallback_true(self, mock_post):
        """Cả Muse và Gemini đều sập, safe_fallback=True -> Safe Script cứu hộ thành công."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Total Network Blackout")

        res = generate_tiktok_script(
            title="Đường dây giả mạo quy mô lớn",
            summary="Công an triệt phá ổ nhóm công nghệ cao lừa đảo hàng trăm tỷ đồng.",
            engine="muse",
            safe_fallback=True
        )
        self.assertEqual(res["engine_used"], "muse (offline_fallback)")
        self.assertEqual(res["model_name"], "deterministic-fallback")
        self.assertIn("Sự thật chấn động", res["hook"])
        self.assertIn("Đường dây giả mạo quy mô lớn", res["hook"])
        self.assertIn("Vertical 9:16", res["muse_visual_prompt"])
        self.assertGreaterEqual(len(res["hashtags"]), 4)

    @patch("requests.post")
    def test_muse_and_gemini_both_fail_with_env_var(self, mock_post):
        """Cả Muse và Gemini đều sập, kích hoạt AI_SAFE_FALLBACK=1 trong môi trường -> Cứu hộ thành công."""
        mock_post.side_effect = requests.exceptions.Timeout("Global gateway timeout")

        with patch.dict(os.environ, {"AI_SAFE_FALLBACK": "1"}):
            res = generate_tiktok_script(
                title="Sự thật về sàn đầu tư ảo",
                summary="Hàng nghìn người sập bẫy cam kết lợi nhuận khủng 30% một tháng.",
                engine="muse"
            )
            self.assertEqual(res["engine_used"], "muse (offline_fallback)")
            self.assertEqual(res["model_name"], "deterministic-fallback")
            self.assertIn("Sự thật chấn động", res["hook"])

    @patch("requests.post")
    def test_default_safe_fallback_behavior_observation(self, mock_post):
        """
        Khảo sát hành vi mặc định khi không truyền safe_fallback và không có AI_SAFE_FALLBACK trong .env:
        Khi toàn bộ Muse và Gemini đều sập, hệ thống ném RuntimeError.
        Đây là điểm rủi ro cần báo cáo cho hội đồng & nhóm Streamlit UI.
        """
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AI_SAFE_FALLBACK", None)
            with self.assertRaises(RuntimeError) as ctx:
                generate_tiktok_script("Tiêu đề", "Tóm tắt", engine="muse")
            self.assertIn("kết nối", str(ctx.exception).lower())


class AdversarialNetworkDetectionTests(unittest.TestCase):
    """Suite 5: Kiểm thử độ bền của socket probe và detect_router_base_url."""

    def test_is_port_reachable_dns_failure(self):
        """Hostname không tồn tại trong DNS (socket.gaierror) -> trả về False trong <0.5s, không crash."""
        result = is_port_reachable("this-non-existent-hostname-12345.local", 20128, timeout=0.3)
        self.assertFalse(result)

    def test_is_port_reachable_closed_port(self):
        """Cổng đóng cục bộ -> trả về False nhanh chóng, không block."""
        result = is_port_reachable("127.0.0.1", 59999, timeout=0.2)
        self.assertFalse(result)

    @patch("src.ai.generator.is_port_reachable", return_value=False)
    def test_detect_router_all_ports_closed(self, mock_reachable):
        """Toàn bộ cổng 20128 và 8045 đóng -> detect_router_base_url trả về fallback URL, không treo."""
        url = detect_router_base_url()
        self.assertTrue(url.startswith("http://"))
        self.assertIn("/v1", url)


if __name__ == "__main__":
    unittest.main()
