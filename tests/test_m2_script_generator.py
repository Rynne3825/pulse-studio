"""
Bộ kiểm thử tự động Milestone M2: Dual-Engine Script Generator & Self-Healing JSON Parser.
Xác minh toàn diện cơ chế Mocking mạng, xử lý dị dạng phản hồi LLM, và tuân thủ Contract 2.

Lệnh thực thi:
    D:\\social-media-engagement\\.venv\\Scripts\\python.exe tests/test_m2_script_generator.py
    D:\\social-media-engagement\\.venv\\Scripts\\python.exe -m unittest tests.test_m2_script_generator
"""

import os
import sys
import json
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from typing import Dict, Any, List

# Đảm bảo import được các module từ thư mục gốc dự án
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ai.generator import (
    generate_tiktok_script,
    parse_script_json,
    self_healing_json_parser,
    safe_script_fallback,
    detect_router_base_url,
    TikTokScriptOutput
)


def create_mock_response(status_code: int = 200, json_body: Any = None, raw_text: str = "") -> MagicMock:
    """Helper tạo đối tượng phản hồi Mock của requests đầy đủ thuộc tính chuẩn."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code

    if json_body is not None:
        raw_text = json.dumps(json_body, ensure_ascii=False)
        mock_resp.json.return_value = json_body
    else:
        try:
            mock_resp.json.return_value = json.loads(raw_text)
        except Exception:
            mock_resp.json.side_effect = json.JSONDecodeError("Invalid JSON", raw_text, 0)

    mock_resp.text = raw_text
    mock_resp.content = raw_text.encode("utf-8")
    return mock_resp


def make_chat_completion_response(content_str: str, model: str = "ag/gemini-3.8-flash-low") -> Dict[str, Any]:
    """Helper đóng gói nội dung vào payload OpenAI-compatible /v1/chat/completions."""
    return {
        "id": "chatcmpl-test-mock-id",
        "object": "chat.completion",
        "created": 1730950000,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content_str
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {"prompt_tokens": 150, "completion_tokens": 180, "total_tokens": 330}
    }


SAMPLE_CANONICAL_SCRIPT_JSON = {
    "hook": "Mất sạch 2 tỷ trong đêm vì một tin nhắn ngân hàng!",
    "body": "Đừng vội tin tin nhắn mang tên ngân hàng. Kẻ gian dùng trạm BTS giả mạo, phát sóng đè mạng viễn thông rồi gửi SMS Brandname chuẩn xác vào máy bạn. Chỉ cần bấm vào link độc và nhập OTP, tiền trong tài khoản sẽ bốc hơi trong 30 giây.",
    "cta": "Mất tiền do người dùng nhẹ dạ hay do nhà mạng buông lỏng quản lý trạm phát sóng lậu? Để lại ý kiến ngay!",
    "hashtags": ["#bocme", "#canhbaoluadao", "#smslua", "#tiktoknews"],
    "full_script": "Mất sạch 2 tỷ trong đêm vì một tin nhắn ngân hàng! Đừng vội tin tin nhắn mang tên ngân hàng. Kẻ gian dùng trạm BTS giả mạo, phát sóng đè mạng viễn thông rồi gửi SMS Brandname chuẩn xác vào máy bạn. Chỉ cần bấm vào link độc và nhập OTP, tiền trong tài khoản sẽ bốc hơi trong 30 giây. Mất tiền do người dùng nhẹ dạ hay do nhà mạng buông lỏng quản lý trạm phát sóng lậu? Để lại ý kiến ngay! #bocme #canhbaoluadao #smslua #tiktoknews",
    "muse_visual_prompt": "Vertical 9:16 cinematic shot, hyperrealistic 4K, dark moody room, glowing smartphone screen displaying fake bank SMS warning, dramatic backlight, shallow depth of field."
}


class Contract2AssertionMixin:
    """Mixin cung cấp hàm kiểm tra tính toàn vẹn và bất biến của Contract 2."""

    def assert_contract_2_invariants(self, result: Dict[str, Any], expected_engine: str = "gemini"):
        self.assertIsInstance(result, dict, "Kết quả trả về phải là Dict[str, Any]")

        # 1. Kiểm tra sự hiện diện của các trường bắt buộc
        required_keys = {"hook", "body", "cta", "hashtags", "full_script", "muse_visual_prompt", "engine_used", "model_name"}
        for k in required_keys:
            self.assertIn(k, result, f"Thiếu trường bắt buộc '{k}' trong TikTokScriptOutput")

        # 2. Kiểm tra kiểu dữ liệu và tính không rỗng
        self.assertIsInstance(result["hook"], str, "hook phải là str")
        self.assertGreater(len(result["hook"].strip()), 0, "hook không được để trống")

        self.assertIsInstance(result["body"], str, "body phải là str")
        self.assertGreater(len(result["body"].strip()), 0, "body không được để trống")

        self.assertIsInstance(result["cta"], str, "cta phải là str")
        self.assertGreater(len(result["cta"].strip()), 0, "cta không được để trống")

        self.assertIsInstance(result["hashtags"], list, "hashtags phải là List[str]")
        self.assertGreaterEqual(len(result["hashtags"]), 1, "hashtags phải có ít nhất 1 phần tử")
        for tag in result["hashtags"]:
            self.assertIsInstance(tag, str, "Mỗi hashtag phải là chuỗi")
            self.assertTrue(tag.startswith("#"), f"Hashtag '{tag}' phải bắt đầu bằng ký tự '#'")

        self.assertIsInstance(result["full_script"], str, "full_script phải là str")
        self.assertIn(result["hook"], result["full_script"], "full_script phải chứa hook")

        self.assertIsInstance(result["muse_visual_prompt"], str, "muse_visual_prompt phải là str")
        self.assertGreater(len(result["muse_visual_prompt"].strip()), 10, "muse_visual_prompt quá ngắn")
        prompt_lower = result["muse_visual_prompt"].lower()
        self.assertTrue(
            ("9:16" in prompt_lower) or ("vertical" in prompt_lower),
            "muse_visual_prompt phải chứa từ khóa khung hình dọc '9:16' hoặc 'vertical'"
        )

        self.assertEqual(result["engine_used"], expected_engine, f"engine_used phải là '{expected_engine}'")
        self.assertIsInstance(result["model_name"], str, "model_name phải là str")
        self.assertGreater(len(result["model_name"].strip()), 0, "model_name không được để trống")

        # 3. Kiểm tra ranh giới số lượng từ (Pacing & Style Bounds)
        hook_words = len(result["hook"].split())
        self.assertLessEqual(hook_words, 25, f"Hook vượt quá ranh giới an toàn 25 từ (thực tế: {hook_words} từ)")

        body_words = len(result["body"].split())
        self.assertGreaterEqual(body_words, 30, f"Body quá ngắn dưới 30 từ (thực tế: {body_words} từ)")
        self.assertLessEqual(body_words, 150, f"Body quá dài trên 150 từ (thực tế: {body_words} từ)")


class TestDualEngineRoutingAndErrors(unittest.TestCase, Contract2AssertionMixin):
    """Suite 1: Kiểm thử cơ chế định tuyến Dual-Engine và xử lý sự cố mạng."""

    @patch("requests.post")
    def test_routing_gemini_engine_success(self, mock_post):
        """T1.1: Định tuyến thành công qua Gemini Router."""
        payload_str = json.dumps(SAMPLE_CANONICAL_SCRIPT_JSON)
        mock_post.return_value = create_mock_response(
            status_code=200,
            json_body=make_chat_completion_response(payload_str, model="ag/gemini-3.8-flash-low")
        )

        res = generate_tiktok_script(
            title="Cảnh báo giả mạo SMS ngân hàng",
            summary="Thủ đoạn dùng trạm BTS giả gửi tin nhắn lừa đảo.",
            engine="gemini"
        )
        self.assert_contract_2_invariants(res, expected_engine="gemini")
        self.assertEqual(mock_post.call_count, 1)
        call_args, call_kwargs = mock_post.call_args
        self.assertIn("/chat/completions", call_args[0])
        self.assertEqual(call_kwargs["json"]["stream"], False)

    @patch("requests.post")
    def test_routing_muse_engine_success(self, mock_post):
        """T1.2: Định tuyến thành công qua Muse AI Chat endpoint."""
        payload_str = json.dumps(SAMPLE_CANONICAL_SCRIPT_JSON)
        mock_post.return_value = create_mock_response(
            status_code=200,
            json_body=make_chat_completion_response(payload_str, model="oc/muse-spark-1.3-contributor-free")
        )

        res = generate_tiktok_script(
            title="Cảnh báo giả mạo SMS ngân hàng",
            summary="Thủ đoạn dùng trạm BTS giả gửi tin nhắn lừa đảo.",
            engine="muse"
        )
        self.assert_contract_2_invariants(res, expected_engine="muse")
        self.assertIn("muse", res["model_name"].lower())

    def test_invalid_engine_raises_value_error(self):
        """T1.3: Chọn sai engine ném lỗi ValueError rõ ràng."""
        with self.assertRaises(ValueError):
            generate_tiktok_script("Tiêu đề", "Tóm tắt", engine="unsupported_engine_xyz")

    @patch("requests.post")
    def test_network_connection_error_handling(self, mock_post):
        """T1.4: Xử lý an toàn khi mất kết nối mạng hoặc port bị đóng (ConnectionError)."""
        import requests
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

        with self.assertRaises(RuntimeError) as ctx:
            generate_tiktok_script("Tiêu đề", "Tóm tắt", engine="gemini")
        self.assertIn("kết nối", str(ctx.exception).lower())

    @patch("requests.post")
    def test_network_timeout_error_handling(self, mock_post):
        """T1.5: Xử lý an toàn khi Gateway quá tải hoặc hết thời gian chờ (Timeout)."""
        import requests
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out after 30s")

        with self.assertRaises(RuntimeError) as ctx:
            generate_tiktok_script("Tiêu đề", "Tóm tắt", engine="gemini")
        self.assertIn("thời gian", str(ctx.exception).lower())

    @patch("requests.post")
    def test_http_400_model_unavailable_error(self, mock_post):
        """T1.6: Xử lý phản hồi lỗi HTTP 400 (Model is unavailable như thực nghiệm)."""
        err_body = {
            "error": {
                "message": "Upstream request failed: Model is unavailable.",
                "type": "invalid_request_error",
                "code": "bad_request"
            }
        }
        mock_post.return_value = create_mock_response(status_code=400, json_body=err_body)

        with self.assertRaises(RuntimeError) as ctx:
            generate_tiktok_script("Tiêu đề", "Tóm tắt", engine="muse")
        self.assertIn("400", str(ctx.exception))

    @patch("requests.post")
    def test_http_429_rate_limit_error(self, mock_post):
        """T1.7: Xử lý phản hồi lỗi HTTP 429 (Rate Limited / Quota Exceeded)."""
        mock_post.return_value = create_mock_response(status_code=429, json_body={"error": "Too Many Requests"})

        with self.assertRaises(RuntimeError) as ctx:
            generate_tiktok_script("Tiêu đề", "Tóm tắt", engine="gemini")
        self.assertIn("429", str(ctx.exception))

    @patch("requests.post")
    def test_muse_fallback_to_gemini_success(self, mock_post):
        """T1.8: Khi Muse gặp lỗi HTTP 400, tự động chuyển đổi sang Gemini 3.8 Flash thành công."""
        payload_str = json.dumps(SAMPLE_CANONICAL_SCRIPT_JSON)

        def mock_side_effect(*args, **kwargs):
            model = kwargs.get("json", {}).get("model", "")
            if "muse" in model.lower():
                return create_mock_response(status_code=400, json_body={"error": "Model unavailable"})
            return create_mock_response(
                status_code=200,
                json_body=make_chat_completion_response(payload_str, model="ag/gemini-3.8-flash-low")
            )

        mock_post.side_effect = mock_side_effect

        res = generate_tiktok_script(
            title="Cảnh báo giả mạo SMS ngân hàng",
            summary="Thủ đoạn dùng trạm BTS giả gửi tin nhắn lừa đảo.",
            engine="muse"
        )
        self.assertEqual(res["engine_used"], "muse (fallback: gemini)")
        self.assertIn("gemini", res["model_name"].lower())
        self.assertIn("Mất sạch", res["hook"])

    @patch("requests.post")
    def test_offline_safe_script_fallback(self, mock_post):
        """T1.9: Khi offline hoàn toàn và bật safe_fallback, trả về kịch bản tất định Contract 2."""
        import requests
        mock_post.side_effect = requests.exceptions.ConnectionError("Offline host unreachable")

        res = generate_tiktok_script(
            title="Vụ bắt giữ trạm phát sóng lậu",
            summary="Cơ quan chức năng đã thu giữ thiết bị BTS lậu.",
            engine="gemini",
            safe_fallback=True
        )
        self.assertEqual(res["engine_used"], "gemini (offline_fallback)")
        self.assertEqual(res["model_name"], "deterministic-fallback")
        self.assertIn("Sự thật chấn động", res["hook"])
        self.assertIn("Vertical 9:16", res["muse_visual_prompt"])
        self.assertGreaterEqual(len(res["hashtags"]), 4)


class TestSelfHealingJsonParser(unittest.TestCase):
    """Suite 2: Kiểm thử bộ giải mã JSON tự phục hồi trước 9 ca biên LLM dị dạng."""

    def test_p1_clean_canonical_json(self):
        """T2.1: Giải mã chính xác JSON chuẩn mực."""
        raw = json.dumps(SAMPLE_CANONICAL_SCRIPT_JSON)
        res = parse_script_json(raw)
        self.assertEqual(res["hook"], SAMPLE_CANONICAL_SCRIPT_JSON["hook"])
        self.assertEqual(res["hashtags"], SAMPLE_CANONICAL_SCRIPT_JSON["hashtags"])

    def test_p2_markdown_code_fence_with_json_tag(self):
        """T2.2: Bóc tách thành công chuỗi được bao bọc bởi ```json ... ```."""
        raw = f"```json\n{json.dumps(SAMPLE_CANONICAL_SCRIPT_JSON, indent=2)}\n```"
        res = parse_script_json(raw)
        self.assertEqual(res["hook"], SAMPLE_CANONICAL_SCRIPT_JSON["hook"])
        self.assertEqual(res["cta"], SAMPLE_CANONICAL_SCRIPT_JSON["cta"])

    def test_p3_markdown_code_fence_without_tag(self):
        """T2.3: Bóc tách thành công chuỗi được bao bọc bởi ``` ... ``` thuần."""
        raw = f"```\n{json.dumps(SAMPLE_CANONICAL_SCRIPT_JSON)}\n```"
        res = parse_script_json(raw)
        self.assertEqual(res["body"], SAMPLE_CANONICAL_SCRIPT_JSON["body"])

    def test_p4_conversational_preamble_and_postamble(self):
        """T2.4: Bóc tách thành công khi có lời chào mở đầu và kết thúc bên ngoài JSON."""
        raw = (
            "Dưới đây là kịch bản TikTok Review / Bóc Mẽ 4 phân cảnh được tối ưu hóa:\n\n"
            f"{json.dumps(SAMPLE_CANONICAL_SCRIPT_JSON)}\n\n"
            "Chúc bạn làm video đạt triệu view và lên xu hướng!"
        )
        res = parse_script_json(raw)
        self.assertEqual(res["hook"], SAMPLE_CANONICAL_SCRIPT_JSON["hook"])
        self.assertEqual(res["muse_visual_prompt"], SAMPLE_CANONICAL_SCRIPT_JSON["muse_visual_prompt"])

    def test_p5_trailing_commas_in_objects_and_arrays(self):
        """T2.5: Tự động loại bỏ dấu phẩy thừa ở cuối dict và list (lỗi phổ biến của LLM)."""
        raw = """
        {
          "hook": "Tin chấn động!",
          "body": "Nội dung bóc mẽ sự thật cực kỳ chi tiết.",
          "cta": "Bạn có tin không?",
          "hashtags": ["#bocme", "#trending", ],
          "muse_visual_prompt": "Vertical 9:16 cinematic shot",
        }
        """
        res = parse_script_json(raw)
        self.assertEqual(res["hook"], "Tin chấn động!")
        self.assertEqual(res["hashtags"], ["#bocme", "#trending"])

    def test_p6_alias_key_call_to_action_mapped_to_cta(self):
        """T2.6: Tự động ánh xạ khóa 'call_to_action' sang 'cta' đảm bảo tương thích ngược."""
        raw = """
        {
          "hook": "Cảnh báo nóng!",
          "body": "Chiêu trò mới nhắm vào tài khoản trực tuyến.",
          "call_to_action": "Bình luận ngay để cùng thảo luận!",
          "hashtags": ["#canhbao"],
          "muse_visual_prompt": "Vertical 9:16 neon background"
        }
        """
        res = parse_script_json(raw)
        self.assertEqual(res["cta"], "Bình luận ngay để cùng thảo luận!")

    def test_p7_hashtags_as_comma_separated_string(self):
        """T2.7: Tự động chuyển đổi hashtags dạng chuỗi phẩy về danh sách List[str]."""
        raw = """
        {
          "hook": "Tin giật gân!",
          "body": "Bóc mẽ chiêu trò thao túng tâm lý.",
          "cta": "Để lại ý kiến ngay!",
          "hashtags": "#bocme, #tamly, #viral",
          "muse_visual_prompt": "Vertical 9:16 dark room"
        }
        """
        res = parse_script_json(raw)
        self.assertIsInstance(res["hashtags"], list)
        self.assertIn("#bocme", res["hashtags"])
        self.assertIn("#tamly", res["hashtags"])

    def test_p8_truncated_json_regex_fallback(self):
        """T2.8: Cứu hộ bằng Regex khi JSON bị cắt cụt do chạm token limit."""
        raw = """
        {
          "hook": "Mất trắng tiền tỷ vì thủ đoạn này!",
          "body": "Kẻ lừa đảo đã dùng thủ thuật tinh vi để chiếm đoạt tài khoản...",
          "cta": "Bạn đã từng gặp trư
        """
        res = parse_script_json(raw)
        self.assertEqual(res["hook"], "Mất trắng tiền tỷ vì thủ đoạn này!")
        self.assertTrue(res["body"].startswith("Kẻ lừa đảo"))
        self.assertIsInstance(res.get("cta", ""), str)
        self.assertIsInstance(res.get("hashtags", []), list)

    def test_p9_pure_prose_non_json_safe_degradation(self):
        """T2.9: Phản hồi thuần văn xuôi không chứa JSON được phân giải an toàn hoặc báo lỗi chuẩn."""
        raw = "Xin lỗi, tôi không thể tạo kịch bản theo yêu cầu này vì vi phạm chính sách."
        res = parse_script_json(raw)
        self.assertIsInstance(res, dict)
        for k in ("hook", "body", "cta", "hashtags", "muse_visual_prompt"):
            self.assertIn(k, res)


class TestContract2Compliance(unittest.TestCase, Contract2AssertionMixin):
    """Suite 3: Kiểm thử chất lượng biên tập kịch bản và sự toàn vẹn của Contract 2."""

    @patch("requests.post")
    def test_full_script_synthesis_when_omitted(self, mock_post):
        """T3.1: Tự động tổng hợp full_script nếu LLM quên sinh trường này."""
        partial_json = dict(SAMPLE_CANONICAL_SCRIPT_JSON)
        del partial_json["full_script"]

        mock_post.return_value = create_mock_response(
            status_code=200,
            json_body=make_chat_completion_response(json.dumps(partial_json))
        )

        res = generate_tiktok_script("Tiêu đề", "Tóm tắt", engine="gemini")
        self.assert_contract_2_invariants(res, expected_engine="gemini")
        self.assertIn(res["hook"], res["full_script"])
        self.assertIn(res["body"], res["full_script"])
        self.assertIn(res["cta"], res["full_script"])

    @patch("requests.post")
    def test_hashtags_normalized_with_hash_prefix(self, mock_post):
        """T3.2: Tự động chuẩn hóa bổ sung dấu '#' nếu LLM trả về từ khóa thiếu dấu thăng."""
        bad_tags_json = dict(SAMPLE_CANONICAL_SCRIPT_JSON)
        bad_tags_json["hashtags"] = ["bocme", "trending", "tiktoknews"]

        mock_post.return_value = create_mock_response(
            status_code=200,
            json_body=make_chat_completion_response(json.dumps(bad_tags_json))
        )

        res = generate_tiktok_script("Tiêu đề", "Tóm tắt", engine="gemini")
        for tag in res["hashtags"]:
            self.assertTrue(tag.startswith("#"), f"Thẻ '{tag}' chưa được thêm tiền tố '#'")

    @patch("requests.post")
    def test_muse_visual_prompt_vertical_specification(self, mock_post):
        """T3.3: Visual Prompt luôn bắt buộc có chỉ định khung hình dọc 9:16."""
        mock_post.return_value = create_mock_response(
            status_code=200,
            json_body=make_chat_completion_response(json.dumps(SAMPLE_CANONICAL_SCRIPT_JSON))
        )

        res = generate_tiktok_script("Tiêu đề", "Tóm tắt", engine="gemini")
        prompt = res["muse_visual_prompt"]
        self.assertTrue(
            ("9:16" in prompt) or ("vertical" in prompt.lower()),
            "Visual Prompt bắt buộc phải có từ khóa '9:16' hoặc 'vertical' cho Muse AI"
        )


class TestM1ToM2PipelineIntegration(unittest.TestCase, Contract2AssertionMixin):
    """Suite 4: Kiểm thử liên kết luồng dữ liệu thông suốt từ Milestone M1 sang M2."""

    @patch("requests.post")
    def test_article_item_piped_into_script_generator(self, mock_post):
        """T4.1: Nhận trực tiếp đối tượng ArticleItem từ M1 và sinh kịch bản thành công."""
        sample_article_m1 = {
            "title": "Thủ đoạn lập trạm BTS giả mạo phát tán tin nhắn ngân hàng",
            "summary": "Công an Hà Nội vừa bắt giữ ổ nhóm chuyên dùng xe máy chở trạm BTS mini phát tán SMS lừa đảo hàng triệu người.",
            "link": "https://genk.vn/thu-doan-bts-gia.chn",
            "thumbnail_url": "https://genk.mediacdn.vn/139269124445442048/2026/11/6/photo.png",
            "published_at": "2026-11-06T10:00:00Z",
            "source": "GenK",
            "topic_category": 1,
            "topic_name": "CongNghe"
        }

        mock_post.return_value = create_mock_response(
            status_code=200,
            json_body=make_chat_completion_response(json.dumps(SAMPLE_CANONICAL_SCRIPT_JSON))
        )

        res = generate_tiktok_script(
            title=sample_article_m1["title"],
            summary=sample_article_m1["summary"],
            engine="gemini"
        )
        self.assert_contract_2_invariants(res, expected_engine="gemini")
        self.assertGreater(len(res["full_script"]), 50)


if __name__ == "__main__":
    unittest.main()
