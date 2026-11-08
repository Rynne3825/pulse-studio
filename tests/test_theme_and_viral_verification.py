"""
Bộ kiểm thử toàn diện E2E: Đa dạng hóa Theme Đồ họa & Kịch bản Viral 3 Phần (Requirement 1, 2, 3).
Tuân thủ phương pháp luận 4-Tier (Tier 1: Feature Coverage, Tier 2: Boundary & Corner Cases,
Tier 3: Cross-Feature Combinations, Tier 4: Real-World Application Scenarios).
Sử dụng chuẩn unittest.TestCase (không phụ thuộc pytest).
"""

import os
import sys
import re
import time
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Dict, Any, List, Optional
from unittest.mock import patch, MagicMock
from PIL import Image

# Đảm bảo import được src khi chạy script trực tiếp
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.video.muse_integration import (
    SafeFallbackSynthesizer,
    generate_tiktok_video,
    find_ffmpeg_binary,
)
try:
    from src.video.muse_integration import THEME_PRESETS
except ImportError:
    THEME_PRESETS = None

from src.ai.generator import (
    generate_tiktok_script,
    safe_script_fallback,
    TIKTOK_SYSTEM_PROMPT,
)
from src.models.content_evaluator import (
    evaluate_tiktok_script,
    VIRAL_HOOK_KEYWORDS,
    VIRAL_CTA_KEYWORDS,
)

REQUIRED_THEMES = ["vibrant", "neon", "tech", "editorial", "pastel"]


class TestTier1FeatureCoverage(unittest.TestCase):
    """
    Tier 1: Kiểm thử độ bao phủ tính năng (Feature Coverage >= 5 tests / feature category).
    Bao gồm 5 danh mục:
    1. 5 Theme Presets (F1)
    2. Theme Card Generator (F2)
    3. Viral 3-Part Scripting (F3)
    4. 5-Aspect Detailed Image Prompts (F4)
    5. Full Offline Fallback Synthesis (F5)
    """

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="pulse_tier1_")
        self.synthesizer = SafeFallbackSynthesizer()

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # --------------------------------------------------------------------------
    # Category 1: 5 Theme Presets (Feature F1)
    # --------------------------------------------------------------------------
    def test_f1_theme_presets_all_five_exist(self) -> None:
        """F1.1: Xác minh THEME_PRESETS tồn tại và chứa đủ 5 themes chuẩn."""
        self.assertIsNotNone(
            THEME_PRESETS,
            "THEME_PRESETS phải được định nghĩa và export trong src.video.muse_integration"
        )
        self.assertIsInstance(THEME_PRESETS, dict)
        for theme_name in REQUIRED_THEMES:
            self.assertIn(
                theme_name,
                THEME_PRESETS,
                f"Theme preset '{theme_name}' phải tồn tại trong THEME_PRESETS"
            )

    def test_f1_theme_presets_attribute_schema(self) -> None:
        """F1.2: Xác minh mỗi theme preset chứa đầy đủ các thuộc tính màu sắc, font, scene, motion."""
        self.assertIsNotNone(THEME_PRESETS)
        for theme_name in REQUIRED_THEMES:
            cfg = THEME_PRESETS[theme_name]
            self.assertIsInstance(cfg, dict, f"Theme '{theme_name}' phải là dictionary")
            self.assertTrue(
                any(k in cfg for k in ["bg_top", "bg_start", "bg_gradient_start"]),
                f"Theme '{theme_name}' thiếu cấu hình gradient bắt đầu (bg_top/bg_start)"
            )
            self.assertTrue(
                any(k in cfg for k in ["bg_bottom", "bg_end", "bg_gradient_end"]),
                f"Theme '{theme_name}' thiếu cấu hình gradient kết thúc (bg_bottom/bg_end)"
            )
            self.assertTrue(
                any(k in cfg for k in ["text_headline", "headline_text", "headline_color"]),
                f"Theme '{theme_name}' thiếu màu sắc chữ headline"
            )
            self.assertTrue(
                any(k in cfg for k in ["scene_colors", "colors", "accents"]),
                f"Theme '{theme_name}' thiếu cấu hình màu phân cảnh (scene_colors)"
            )
            self.assertTrue(
                any(k in cfg for k in ["motion_zoompan", "motions", "motion_formulas"]),
                f"Theme '{theme_name}' thiếu công thức chuyển động FFmpeg motion zoompan"
            )

    def test_f1_theme_presets_distinct_color_palettes(self) -> None:
        """F1.3: Xác minh các theme có bảng màu nền khác biệt, không bị đơn sắc tối đồng nhất."""
        self.assertIsNotNone(THEME_PRESETS)
        bg_colors = set()
        for theme_name in REQUIRED_THEMES:
            cfg = THEME_PRESETS[theme_name]
            bg_key = next((k for k in ["bg_top", "bg_start", "bg_gradient_start"] if k in cfg), None)
            self.assertIsNotNone(bg_key, f"Theme '{theme_name}' thiếu key màu nền")
            val = cfg[bg_key]
            # Chuẩn hóa về tuple nếu là list hoặc hex
            if isinstance(val, (list, tuple)):
                bg_colors.add(tuple(val[:3]))
            else:
                bg_colors.add(str(val))
        self.assertGreaterEqual(
            len(bg_colors), 4,
            "Tối thiểu 4/5 themes phải có màu nền khởi đầu khác biệt nhau hoàn toàn"
        )

    def test_f1_theme_presets_scene_colors_count(self) -> None:
        """F1.4: Xác minh mỗi theme định nghĩa tối thiểu 4 màu sắc phân cảnh cho 4-scene storyboard."""
        self.assertIsNotNone(THEME_PRESETS)
        for theme_name in REQUIRED_THEMES:
            cfg = THEME_PRESETS[theme_name]
            sc_key = next((k for k in ["scene_colors", "colors", "accents"] if k in cfg), None)
            self.assertIsNotNone(sc_key)
            scene_colors = cfg[sc_key]
            self.assertIsInstance(scene_colors, (list, tuple))
            self.assertGreaterEqual(
                len(scene_colors), 4,
                f"Theme '{theme_name}' phải có tối thiểu 4 scene_colors cho Hook, Retain p1, Retain p2, CTA"
            )

    def test_f1_theme_presets_motion_zoompan_syntax(self) -> None:
        """F1.5: Xác minh công thức FFmpeg zoompan của mỗi theme chứa cú pháp zoompan hợp lệ."""
        self.assertIsNotNone(THEME_PRESETS)
        for theme_name in REQUIRED_THEMES:
            cfg = THEME_PRESETS[theme_name]
            m_key = next((k for k in ["motion_zoompan", "motions", "motion_formulas"] if k in cfg), None)
            self.assertIsNotNone(m_key)
            motion_val = cfg[m_key]
            if isinstance(motion_val, list):
                self.assertGreaterEqual(len(motion_val), 1)
                sample = str(motion_val[0])
            else:
                sample = str(motion_val)
            self.assertIn("zoom", sample.lower(), f"Theme '{theme_name}' motion formula phải chứa biến 'zoom'")

    # --------------------------------------------------------------------------
    # Category 2: Theme Card Generator (Feature F2)
    # --------------------------------------------------------------------------
    def test_f2_card_dimensions_all_five_themes(self) -> None:
        """F2.1: Tạo card đồ họa cho toàn bộ 5 themes và xác minh kích thước chuẩn 720x1280."""
        for i, theme_name in enumerate(REQUIRED_THEMES, 1):
            card_path = self.synthesizer._generate_card(
                title=f"Theme Test {theme_name.upper()}",
                headline=f"Xác minh card đồ họa hiển thị chuẩn phong cách {theme_name}.",
                color=(255, 67, 101),
                ref_image_path=None,
                temp_dir=Path(self.temp_dir),
                scene_num=i,
                theme=theme_name
            )
            card_p = Path(card_path)
            self.assertTrue(card_p.exists(), f"Card file cho theme '{theme_name}' không tồn tại")
            with Image.open(card_p) as img:
                self.assertEqual(
                    img.size, (720, 1280),
                    f"Kích thước card theme '{theme_name}' phải đúng 720x1280, nhận được {img.size}"
                )

    def test_f2_card_image_format_and_filesize(self) -> None:
        """F2.2: Xác minh file card tạo ra là ảnh hợp lệ (PNG/JPEG) có dung lượng > 5KB."""
        card_path = self.synthesizer._generate_card(
            title="Format Verification",
            headline="Kiểm tra định dạng và dung lượng ảnh card đồ họa.",
            color=(0, 240, 255),
            ref_image_path=None,
            temp_dir=Path(self.temp_dir),
            scene_num=1,
            theme="neon"
        )
        card_p = Path(card_path)
        self.assertTrue(card_p.exists())
        self.assertGreater(card_p.stat().st_size, 5000, "Dung lượng card phải lớn hơn 5KB")
        with Image.open(card_p) as img:
            self.assertIn(img.format.upper(), ["PNG", "JPEG", "JPG"])

    def test_f2_card_backward_compatibility_signature(self) -> None:
        """F2.3: Gọi _generate_card với chữ ký cũ (không truyền theme) vẫn chạy thành công."""
        # Chữ ký cũ 6 tham số: (title, headline, color, ref_image_path, temp_dir, scene_num)
        card_path = self.synthesizer._generate_card(
            "Legacy Signature Title",
            "Nội dung kiểm thử tương thích ngược chữ ký hàm _generate_card.",
            (212, 175, 55),
            None,
            Path(self.temp_dir),
            scene_num=1
        )
        card_p = Path(card_path)
        self.assertTrue(card_p.exists())
        with Image.open(card_p) as img:
            self.assertEqual(img.size, (720, 1280))

    def test_f2_card_with_reference_image(self) -> None:
        """F2.4: Tạo card kết hợp ảnh tham chiếu cục bộ thành công."""
        # Tạo ảnh tham chiếu mẫu 400x300
        ref_path = Path(self.temp_dir) / "sample_ref.jpg"
        dummy_img = Image.new("RGB", (400, 300), (45, 120, 210))
        dummy_img.save(ref_path, "JPEG")

        card_path = self.synthesizer._generate_card(
            title="Ref Image Test",
            headline="Card với ảnh tham chiếu tiêu điểm và nền mờ.",
            color=(16, 185, 129),
            ref_image_path=ref_path,
            temp_dir=Path(self.temp_dir),
            scene_num=2,
            theme="tech"
        )
        self.assertTrue(Path(card_path).exists())

    def test_f2_card_without_reference_image(self) -> None:
        """F2.5: Tạo card khi không có ảnh tham chiếu sử dụng gradient nền đa sắc mượt mà."""
        card_path = self.synthesizer._generate_card(
            title="Gradient Only",
            headline="Card đồ họa thuần gradient không phụ thuộc ảnh nguồn.",
            color=(194, 65, 12),
            ref_image_path=None,
            temp_dir=Path(self.temp_dir),
            scene_num=3,
            theme="editorial"
        )
        self.assertTrue(Path(card_path).exists())
        with Image.open(card_path) as img:
            # Kiểm tra pixel góc trên và góc dưới không bị giống hệt nhau (xác nhận có gradient)
            top_pixel = img.getpixel((360, 50))[:3]
            bottom_pixel = img.getpixel((360, 1200))[:3]
            # Trên và dưới phải có biến thiên màu sắc
            diff = sum(abs(t - b) for t, b in zip(top_pixel, bottom_pixel))
            self.assertGreater(diff, 0, "Gradient nền phải có sự biến thiên màu sắc giữa đỉnh và đáy card")

    # --------------------------------------------------------------------------
    # Category 3: Viral 3-Part Scripting (Feature F3)
    # --------------------------------------------------------------------------
    def test_f3_script_hook_conformance(self) -> None:
        """F3.1: Xác minh Hook <= 15 từ, kết thúc bằng dấu '?', chứa từ khóa viral hook."""
        script = safe_script_fallback(
            title="Thủ đoạn lừa đảo giả mạo ngân hàng qua tin nhắn SMS",
            summary="Kẻ gian sử dụng thiết bị trạm phát sóng giả để đánh cắp tiền."
        )
        hook = script.get("hook", "").strip()
        words = hook.split()
        self.assertLessEqual(len(words), 15, f"Hook phải <= 15 từ (thực tế: {len(words)} từ: '{hook}')")
        self.assertTrue(hook.endswith("?"), f"Hook phải kết thúc bằng dấu hỏi '?' (thực tế: '{hook}')")
        matched = [kw for kw in VIRAL_HOOK_KEYWORDS if kw in hook.lower()]
        self.assertGreater(
            len(matched), 0,
            f"Hook '{hook}' phải chứa ít nhất 1 từ khóa giật gân/bóc mẽ trong VIRAL_HOOK_KEYWORDS"
        )

    def test_f3_script_retain_conformance(self) -> None:
        """F3.2: Xác minh Retain (Scene 2 & 3 hoặc body) có độ dài 60 - 85 từ tối ưu nhịp thoại."""
        script = safe_script_fallback(
            title="Cảnh báo an toàn dữ liệu số cá nhân",
            summary="Hàng triệu tài khoản bị rò rỉ do đặt mật khẩu quá đơn giản."
        )
        body = script.get("body", "").strip()
        body_words = len(body.split())

        # Nếu scenes được phân bổ, kiểm tra tổng từ Scene 2 + Scene 3
        scenes = script.get("scenes", [])
        if len(scenes) >= 3:
            scene2_words = len(str(scenes[1].get("voice_text", "")).split())
            scene3_words = len(str(scenes[2].get("voice_text", "")).split())
            retain_words = scene2_words + scene3_words
            self.assertTrue(
                (60 <= body_words <= 85) or (60 <= retain_words <= 85),
                f"Retain phải có tổng từ trong khoảng 60-85 từ (body={body_words}, scenes 2+3={retain_words})"
            )
        else:
            self.assertGreaterEqual(body_words, 60, "Retain body phải >= 60 từ")
            self.assertLessEqual(body_words, 85, "Retain body phải <= 85 từ")

    def test_f3_script_cta_conformance(self) -> None:
        """F3.3: Xác minh CTA có độ dài 15 - 25 từ, kết thúc bằng '?', chứa từ khóa viral CTA."""
        script = safe_script_fallback(
            title="Đánh giá xu hướng mua sắm trực tuyến mới",
            summary="Người tiêu dùng thắt chặt chi tiêu và tìm kiếm giá trị thực tế."
        )
        cta = script.get("cta", "").strip()
        words = cta.split()
        self.assertGreaterEqual(len(words), 15, f"CTA phải >= 15 từ (thực tế: {len(words)} từ: '{cta}')")
        self.assertLessEqual(len(words), 25, f"CTA phải <= 25 từ (thực tế: {len(words)} từ: '{cta}')")
        self.assertTrue(cta.endswith("?"), f"CTA phải kết thúc bằng dấu hỏi '?' (thực tế: '{cta}')")
        matched = [kw for kw in VIRAL_CTA_KEYWORDS if kw in cta.lower()]
        self.assertGreater(
            len(matched), 0,
            f"CTA '{cta}' phải chứa ít nhất 1 từ khóa kêu gọi tương tác/tranh luận trong VIRAL_CTA_KEYWORDS"
        )

    def test_f3_script_four_scenes_structure(self) -> None:
        """F3.4: Xác minh kịch bản chứa chính xác 4 phân cảnh với đầy đủ metadata bắt buộc."""
        script = safe_script_fallback(
            title="Sự thật về các gói cước 5G tại Việt Nam",
            summary="Tốc độ thực tế có thực sự vượt trội như quảng cáo?"
        )
        scenes = script.get("scenes", [])
        self.assertEqual(len(scenes), 4, "Kịch bản phải gồm đúng 4 phân cảnh (Hook, Retain p1, Retain p2, CTA)")
        for i, sc in enumerate(scenes, 1):
            self.assertEqual(sc.get("scene_num"), i)
            self.assertTrue(sc.get("title"), f"Scene {i} thiếu title")
            self.assertGreater(int(sc.get("duration_sec", 0)), 0, f"Scene {i} duration_sec phải > 0")
            self.assertTrue(sc.get("voice_text"), f"Scene {i} thiếu voice_text")
            self.assertTrue(sc.get("visual_prompt"), f"Scene {i} thiếu visual_prompt")
            self.assertTrue(sc.get("camera_motion"), f"Scene {i} thiếu camera_motion")

    def test_f3_script_hashtags_and_full_script(self) -> None:
        """F3.5: Xác minh kịch bản có tối thiểu 4 hashtags và full_script kết nối đầy đủ các phần."""
        script = safe_script_fallback("Tiêu đề tin tức", "Tóm tắt sự kiện nổi bật.")
        tags = script.get("hashtags", [])
        self.assertGreaterEqual(len(tags), 4, "Phải có ít nhất 4 hashtags")
        for tag in tags:
            self.assertTrue(tag.startswith("#"), f"Hashtag '{tag}' phải bắt đầu bằng '#'")
        full_script = script.get("full_script", "")
        self.assertIn(script.get("hook", ""), full_script)
        self.assertIn(script.get("cta", ""), full_script)

    # --------------------------------------------------------------------------
    # Category 4: 5-Aspect Detailed Image Prompts (Feature F4)
    # --------------------------------------------------------------------------
    def test_f4_image_prompts_aspect_ratio_prefix(self) -> None:
        """F4.1: Xác minh mọi visual_prompt bắt đầu bằng 'Vertical 9:16 aspect ratio video'."""
        script = safe_script_fallback("Tin nóng công nghệ AI", "Ra mắt mô hình xử lý đa phương thức mới.")
        scenes = script.get("scenes", [])
        for i, sc in enumerate(scenes, 1):
            prompt = sc.get("visual_prompt", "")
            self.assertTrue(
                prompt.startswith("Vertical 9:16 aspect ratio video"),
                f"Scene {i} visual_prompt '{prompt}' phải bắt đầu bằng 'Vertical 9:16 aspect ratio video'"
            )

    def test_f4_image_prompts_five_aspects_detail(self) -> None:
        """F4.2: Xác minh prompt hình ảnh bao quát 5 khía cạnh điện ảnh (Chủ thể, Ánh sáng, Góc máy, Màu sắc, Phong cách)."""
        script = safe_script_fallback("Phát hiện lỗ hổng bảo mật nghiêm trọng", "Hacker khai thác tấn công máy chủ.")
        scenes = script.get("scenes", [])
        for i, sc in enumerate(scenes, 1):
            detail = sc.get("image_prompt_detail")
            prompt_str = sc.get("visual_prompt", "").lower()

            if isinstance(detail, dict) and detail:
                # Nếu có cấu trúc bóc tách chi tiết:
                self.assertTrue(detail.get("subject"), f"Scene {i} thiếu subject trong image_prompt_detail")
                self.assertTrue(detail.get("lighting"), f"Scene {i} thiếu lighting trong image_prompt_detail")
                self.assertTrue(
                    detail.get("camera_angle") or detail.get("camera"),
                    f"Scene {i} thiếu camera_angle trong image_prompt_detail"
                )
                self.assertTrue(
                    detail.get("color_tone") or detail.get("color"),
                    f"Scene {i} thiếu color_tone trong image_prompt_detail"
                )
                self.assertTrue(
                    detail.get("art_style") or detail.get("style"),
                    f"Scene {i} thiếu art_style trong image_prompt_detail"
                )
            else:
                # Nếu là chuỗi tổng hợp: phải chứa từ khóa ánh sáng, góc máy/camera, độ phân giải/phong cách
                has_lighting = any(w in prompt_str for w in ["lighting", "light", "chiaroscuro", "shadows", "glow"])
                has_camera = any(w in prompt_str for w in ["shot", "angle", "close-up", "view", "camera", "focus"])
                has_style = any(w in prompt_str for w in ["photorealistic", "4k", "8k", "documentary", "cinematic", "realism"])
                self.assertTrue(
                    has_lighting and has_camera and has_style,
                    f"Scene {i} visual_prompt '{sc.get('visual_prompt')}' phải thể hiện các yếu tố ánh sáng, góc máy và phong cách"
                )

    def test_f4_image_prompts_english_only(self) -> None:
        """F4.3: Xác minh visual_prompt được cấu trúc bằng tiếng Anh chuẩn cho AI image/video models."""
        script = safe_script_fallback("Real Estate Speculation Crisis", "Housing prices inflated unnaturally.")
        scenes = script.get("scenes", [])
        vietnamese_diacritic_pattern = re.compile(r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]", re.IGNORECASE)
        for i, sc in enumerate(scenes, 1):
            prompt = sc.get("visual_prompt", "")
            self.assertTrue(
                prompt.startswith("Vertical 9:16 aspect ratio video"),
                f"Scene {i} visual_prompt '{prompt}' phải bắt đầu bằng 'Vertical 9:16 aspect ratio video'"
            )
            self.assertFalse(
                vietnamese_diacritic_pattern.search(prompt),
                f"Scene {i} visual_prompt '{prompt}' không được chứa ký tự tiếng Việt có dấu khi đầu vào là tiếng Anh"
            )
            # Xác minh các token điện ảnh tiếng Anh chuẩn
            prompt_lower = prompt.lower()
            self.assertTrue(
                any(tok in prompt_lower for tok in ["lighting", "shot", "angle", "palette", "realism", "cinematic"]),
                f"Scene {i} visual_prompt phải chứa các thuật ngữ điện ảnh tiếng Anh chuẩn"
            )

    def test_f4_image_prompts_camera_motion_mapping(self) -> None:
        """F4.4: Xác minh camera_motion trong từng phân cảnh thuộc danh mục chuyển động hợp lệ."""
        script = safe_script_fallback("Bão giá thị trường vàng", "Giá vàng liên tục lập đỉnh mới trong tuần qua.")
        valid_motions = [
            "slow dolly push-in", "pan left to right", "slow tilt down", "center focal hold",
            "dolly in", "pan right", "tilt down", "static"
        ]
        scenes = script.get("scenes", [])
        for i, sc in enumerate(scenes, 1):
            motion = sc.get("camera_motion", "").lower().strip()
            self.assertTrue(
                any(vm in motion for vm in valid_motions),
                f"Scene {i} camera_motion '{motion}' không khớp danh mục chuyển động camera tiêu chuẩn"
            )

    def test_f4_cinematography_locks_presence(self) -> None:
        """F4.5: Xác minh cinematography_locks chứa đủ 5 khóa phong cách điện ảnh."""
        script = safe_script_fallback("Khám phá công nghệ pin mới", "Thời lượng pin tăng gấp 3 lần.")
        locks = script.get("cinematography_locks", {})
        self.assertIsInstance(locks, dict)
        self.assertTrue(locks.get("style_lock"), "Thiếu style_lock")
        self.assertTrue(locks.get("char_lock"), "Thiếu char_lock")
        self.assertTrue(locks.get("set_lock"), "Thiếu set_lock")
        self.assertTrue(locks.get("video_suffix"), "Thiếu video_suffix")
        self.assertTrue(locks.get("negative_prompt"), "Thiếu negative_prompt")

    # --------------------------------------------------------------------------
    # Category 5: Full Offline Fallback Synthesis (Feature F5)
    # --------------------------------------------------------------------------
    def test_f5_offline_script_fallback_deterministic(self) -> None:
        """F5.1: safe_script_fallback chạy ngoại tuyến 100% không cần API key và trả về kết quả tất định."""
        t = "Nghi vấn rò rỉ đề thi tốt nghiệp"
        s = "Cơ quan công an đang xác minh thông tin lan truyền trên mạng."
        res1 = safe_script_fallback(t, s)
        res2 = safe_script_fallback(t, s)
        self.assertEqual(res1.get("hook"), res2.get("hook"), "safe_script_fallback phải tất định cho cùng một đầu vào")
        self.assertEqual(res1.get("cta"), res2.get("cta"))

    def test_f5_offline_generator_safe_mode(self) -> None:
        """F5.2: generate_tiktok_script kích hoạt an toàn fallback khi router offline hoặc safe_fallback=True."""
        # Giả lập router không phản hồi bằng url không hợp lệ
        with patch("src.ai.generator.detect_router_base_url", return_value="http://127.0.0.1:99999/v1"):
            res = generate_tiktok_script(
                title="Sự cố sập mạng viễn thông diện rộng",
                summary="Hàng triệu thuê bao mất liên lạc trong nhiều giờ.",
                engine="gemini",
                safe_fallback=True
            )
            self.assertIsNotNone(res)
            self.assertTrue(res.get("hook"))
            self.assertTrue(res.get("body"))
            self.assertTrue(res.get("cta"))

    def test_f5_offline_card_synthesis_no_network(self) -> None:
        """F5.3: SafeFallbackSynthesizer._generate_card vận hành hoàn toàn ngoại tuyến qua Pillow."""
        card_path = self.synthesizer._generate_card(
            title="Offline Card",
            headline="Vẽ card ngoại tuyến không cần kết nối internet.",
            color=(59, 130, 246),
            ref_image_path=None,
            temp_dir=Path(self.temp_dir),
            scene_num=1,
            theme="tech"
        )
        self.assertTrue(Path(card_path).exists())

    def test_f5_offline_voiceover_resilience(self) -> None:
        """F5.4: synthesize_voiceover rơi vào fallback an toàn không gây unhandled exception khi ngắt kết nối."""
        out_mp3 = Path(self.temp_dir) / "offline_voice.mp3"
        with patch("src.video.muse_integration._synthesize_edge_tts", return_value=False), \
             patch("src.video.muse_integration._synthesize_google_tts", return_value=False):
            # Khi cả edge và google đều offline, hệ thống tự động sinh silent mp3 an toàn
            from src.video.muse_integration import synthesize_voiceover
            ok = synthesize_voiceover("Thử nghiệm ngắt kết nối mạng toàn phần.", out_mp3)
            self.assertTrue(out_mp3.exists(), "File MP3 fallback phải tồn tại ngay cả khi ngắt kết nối")

    def test_f5_offline_video_synthesis_short_render(self) -> None:
        """F5.5: SafeFallbackSynthesizer.synthesize render video 2s ngoại tuyến thành công với theme custom."""
        script_data = safe_script_fallback("Tin nhanh 24h", "Bản tin tổng hợp ngắn.")
        # Thử render video ngắn 2s với theme neon
        res = self.synthesizer.synthesize(
            script_data=script_data,
            ref_image_url=None,
            duration=2,
            theme="neon"
        )
        self.assertEqual(res.get("status"), "success")
        self.assertEqual(res.get("mode"), "fallback")
        video_p = Path(res.get("video_path", ""))
        self.assertTrue(video_p.exists())
        self.assertGreater(video_p.stat().st_size, 1000)


class TestTier2BoundaryAndCorners(unittest.TestCase):
    """
    Tier 2: Kiểm thử trường hợp biên và góc cạnh (Boundary & Corner Cases >= 5 tests).
    Kiểm tra độ chịu lỗi trước dữ liệu đầu vào cực đoan, chuỗi rỗng, lỗi theme, ký tự đặc biệt.
    """

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="pulse_tier2_")
        self.synthesizer = SafeFallbackSynthesizer()

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_tier2_empty_or_whitespace_inputs(self) -> None:
        """Tier 2.1: Chuỗi tiêu đề và tóm tắt rỗng hoặc chỉ có khoảng trắng không làm sập hệ thống."""
        res = safe_script_fallback("", "   \n\t  ")
        self.assertTrue(res.get("hook"), "Hook không được rỗng khi input rỗng")
        self.assertTrue(res.get("body"), "Body không được rỗng khi input rỗng")
        self.assertTrue(res.get("cta"), "CTA không được rỗng khi input rỗng")

        card_path = self.synthesizer._generate_card(
            title="",
            headline="   ",
            color=(255, 67, 101),
            ref_image_path=None,
            temp_dir=Path(self.temp_dir),
            scene_num=1,
            theme="vibrant"
        )
        self.assertTrue(Path(card_path).exists())

    def test_tier2_extreme_text_lengths(self) -> None:
        """Tier 2.2: Tiêu đề siêu dài (500 ký tự) và headline siêu dài (1000 ký tự) tự động ngắt dòng không crash."""
        super_long_title = "CẢNH BÁO " * 50
        super_long_headline = "Đây là bản tin đặc biệt khẩn cấp có độ dài cực lớn nhằm kiểm tra thuật toán ngắt dòng chữ tự động của card đồ họa. " * 15

        card_path = self.synthesizer._generate_card(
            title=super_long_title,
            headline=super_long_headline,
            color=(0, 240, 255),
            ref_image_path=None,
            temp_dir=Path(self.temp_dir),
            scene_num=1,
            theme="neon"
        )
        card_p = Path(card_path)
        self.assertTrue(card_p.exists())
        with Image.open(card_p) as img:
            self.assertEqual(img.size, (720, 1280))

    def test_tier2_invalid_theme_name_graceful_fallback(self) -> None:
        """Tier 2.3: Truyền tên theme không tồn tại tự động fallback về theme mặc định mà không ném KeyError."""
        for invalid_name in ["unknown_cyberpunk", "", "null_theme", None]:
            card_path = self.synthesizer._generate_card(
                title="Invalid Theme Test",
                headline="Kiểm tra fallback an toàn khi tên theme bị sai lệch.",
                color=(212, 175, 55),
                ref_image_path=None,
                temp_dir=Path(self.temp_dir),
                scene_num=1,
                theme=invalid_name
            )
            self.assertTrue(
                Path(card_path).exists(),
                f"Phải tạo được card thành công khi truyền theme='{invalid_name}'"
            )

    def test_tier2_complex_vietnamese_diacritics(self) -> None:
        """Tier 2.4: Bộ ký tự tiếng Việt phức tạp render chuẩn xác trên card đồ họa không lỗi glyph."""
        complex_vn = "Bứt phá ngoạn mục: Khởi sắc đường lối trắc nghiệm, giải quyết khuất tất ở ngõ phở cổ."
        card_path = self.synthesizer._generate_card(
            title=complex_vn,
            headline=complex_vn,
            color=(194, 65, 12),
            ref_image_path=None,
            temp_dir=Path(self.temp_dir),
            scene_num=1,
            theme="editorial"
        )
        self.assertTrue(Path(card_path).exists())

    def test_tier2_missing_or_corrupted_ref_image(self) -> None:
        """Tier 2.5: Đường dẫn ảnh tham chiếu không tồn tại hoặc file hỏng tự động chuyển sang nền gradient."""
        fake_path = Path(self.temp_dir) / "non_existent_file.png"
        corrupted_path = Path(self.temp_dir) / "corrupted.jpg"
        corrupted_path.write_text("NOT AN IMAGE DATA")

        for bad_p in [fake_path, corrupted_path]:
            card_path = self.synthesizer._generate_card(
                title="Bad Image Fallback",
                headline="Card vẫn tạo thành công khi file ảnh tham chiếu bị lỗi.",
                color=(167, 139, 250),
                ref_image_path=bad_p,
                temp_dir=Path(self.temp_dir),
                scene_num=1,
                theme="pastel"
            )
            self.assertTrue(Path(card_path).exists())

    def test_tier2_script_missing_keys_safe_defaults(self) -> None:
        """Tier 2.6: Dữ liệu script_data bị thiếu trường scenes hoặc hashtags khi gọi synthesize không gây lỗi."""
        sparse_script = {
            "hook": "CẢNH BÁO LỪA ĐẢO MỚI?",
            "body": "Nội dung ngắn gọn cảnh báo về thủ đoạn lừa đảo.",
            "cta": "Hãy chia sẻ để bạn bè cảnh giác?"
        }
        res = self.synthesizer.synthesize(
            script_data=sparse_script,
            ref_image_url=None,
            duration=2,
            theme="editorial"
        )
        self.assertEqual(res.get("status"), "success")


class TestTier3CrossFeatureCombinations(unittest.TestCase):
    """
    Tier 3: Kiểm thử kết hợp chéo tính năng (Cross-Feature Combinations >= 4 tests).
    Kiểm tra tương tác giữa Theme Presets, Viral Script Montage, Card Preview, và Video Synthesis.
    """

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="pulse_tier3_")
        self.synthesizer = SafeFallbackSynthesizer()

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_tier3_theme_and_viral_script_montage(self) -> None:
        """Tier 3.1: Kết hợp Script Viral sinh bởi safe_script_fallback với render 4 scene cards theo theme."""
        script = safe_script_fallback(
            title="Chiêu trò mạo danh bác sĩ bán thực phẩm chức năng",
            summary="Hàng loạt trang mạng sử dụng hình ảnh giả mạo để trục lợi người bệnh."
        )
        scenes = script.get("scenes", [])
        self.assertEqual(len(scenes), 4)

        # Render 4 cards tương ứng với 4 phân cảnh của script sử dụng theme neon
        generated_cards = []
        for sc in scenes:
            num = sc.get("scene_num", 1)
            p = self.synthesizer._generate_card(
                title=sc.get("title", f"Scene {num}"),
                headline=sc.get("voice_text", ""),
                color=(0, 240, 255),
                ref_image_path=None,
                temp_dir=Path(self.temp_dir),
                scene_num=num,
                theme="neon"
            )
            generated_cards.append(Path(p))

        self.assertEqual(len(generated_cards), 4)
        for p in generated_cards:
            self.assertTrue(p.exists())
            with Image.open(p) as img:
                self.assertEqual(img.size, (720, 1280))

    def test_tier3_theme_color_and_headline_contrast(self) -> None:
        """Tier 3.2: Xác minh tương phản màu chữ headline: theme nền sáng dùng chữ tối, theme nền tối dùng chữ sáng."""
        self.assertIsNotNone(THEME_PRESETS)
        # Theme editorial và pastel là phong cách nền sáng/ivory/lavender
        # Theme neon, tech, vibrant là phong cách nền tối
        for theme_name in ["neon", "tech", "vibrant"]:
            cfg = THEME_PRESETS[theme_name]
            h_key = next((k for k in ["text_headline", "headline_text", "headline_color"] if k in cfg), None)
            if h_key:
                val = cfg[h_key]
                # Nếu là RGB tuple, tính độ sáng (luminance)
                if isinstance(val, (list, tuple)) and len(val) >= 3:
                    lum = 0.299 * val[0] + 0.587 * val[1] + 0.114 * val[2]
                    self.assertGreater(lum, 180, f"Theme tối '{theme_name}' phải có màu headline sáng (lum={lum})")

    def test_tier3_all_themes_instant_card_preview(self) -> None:
        """Tier 3.3: Mô phỏng nút Xem trước Card trên Streamlit: tạo card cho cả 5 themes với độ trễ < 0.3s/card."""
        times = []
        for i, theme_name in enumerate(REQUIRED_THEMES, 1):
            t_start = time.perf_counter()
            card_path = self.synthesizer._generate_card(
                title=f"Instant Preview {theme_name.title()}",
                headline="Xem trước card đồ họa cực nhanh phục vụ giao diện người dùng.",
                color=(255, 67, 101),
                ref_image_path=None,
                temp_dir=Path(self.temp_dir),
                scene_num=i,
                theme=theme_name
            )
            elapsed = time.perf_counter() - t_start
            times.append(elapsed)
            self.assertTrue(Path(card_path).exists())

        avg_time = sum(times) / len(times)
        self.assertLess(
            avg_time, 0.3,
            f"Thời gian trung bình sinh card xem trước phải < 0.3 giây (thực tế: {avg_time:.3f}s)"
        )

    def test_tier3_offline_generator_to_synthesizer_pipeline(self) -> None:
        """Tier 3.4: Chạy chuỗi quy trình khép kín: safe_script_fallback -> synthesize(duration=2, theme='tech')."""
        script_data = safe_script_fallback(
            title="Xu hướng trí tuệ nhân tạo tạo sinh trong năm 2026",
            summary="Ứng dụng AI len lỏi vào từng quy trình sản xuất nội dung số."
        )
        res = self.synthesizer.synthesize(
            script_data=script_data,
            ref_image_url=None,
            duration=2,
            theme="tech"
        )
        self.assertEqual(res.get("status"), "success")
        self.assertTrue(Path(res.get("video_path", "")).exists())


class TestTier4RealWorldScenarios(unittest.TestCase):
    """
    Tier 4: Kiểm thử kịch bản thực tế (Real-World Application Scenarios >= 4 tests).
    Kiểm thử quy trình xuất bản tin tức thật, đánh giá chấm điểm viral S-rank, và tích hợp UI.
    """

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="pulse_tier4_")
        self.synthesizer = SafeFallbackSynthesizer()

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_tier4_editorial_banking_scam_scenario(self) -> None:
        """Tier 4.1: Kịch bản Báo chí Điều tra - Vụ án lừa đảo SMS mạo danh ngân hàng (Theme: Editorial)."""
        article_title = "Cảnh báo khẩn cấp: Chiêu trò gửi tin nhắn SMS brandname giả mạo ngân hàng"
        article_summary = (
            "Kẻ gian sử dụng thiết bị phát sóng BTS giả mạo để chèn tin nhắn lừa đảo vào luồng tin nhắn chính thức "
            "của ngân hàng, dụ người dùng bấm vào đường link lạ để đánh cắp mã OTP và chiếm đoạt tiền trong tài khoản."
        )

        # 1. Sinh kịch bản Viral 3 phần
        script = safe_script_fallback(article_title, article_summary)

        # Kiểm tra Hook
        hook = script.get("hook", "")
        self.assertLessEqual(len(hook.split()), 15)
        self.assertTrue(hook.endswith("?"))

        # Kiểm tra Retain
        body = script.get("body", "")
        self.assertTrue(60 <= len(body.split()) <= 85)

        # Kiểm tra CTA
        cta = script.get("cta", "")
        self.assertTrue(15 <= len(cta.split()) <= 25)
        self.assertTrue(cta.endswith("?"))

        # 2. Sinh card đồ họa 4 phân cảnh với theme Editorial
        for i, sc in enumerate(script.get("scenes", []), 1):
            card_p = self.synthesizer._generate_card(
                title=sc.get("title", f"Scene {i}"),
                headline=sc.get("voice_text", ""),
                color=(194, 65, 12),
                ref_image_path=None,
                temp_dir=Path(self.temp_dir),
                scene_num=i,
                theme="editorial"
            )
            self.assertTrue(Path(card_p).exists())

    def test_tier4_tech_ai_breakthrough_scenario(self) -> None:
        """Tier 4.2: Kịch bản Tin Công Nghệ Cao - Đột phá chip xử lý AI 2nm (Theme: Tech)."""
        article_title = "Đột phá kiến trúc vi xử lý AI 2nm thế hệ mới tăng tốc độ xử lý gấp 5 lần"
        article_summary = (
            "Các nhà nghiên cứu công bố kiến trúc bán dẫn mới cho phép thực thi mô hình ngôn ngữ lớn "
            "trực tiếp trên thiết bị di động với mức tiêu thụ năng lượng giảm tới 40%."
        )
        script = safe_script_fallback(article_title, article_summary)
        # Render video ngắn hoàn chỉnh với theme tech
        res = self.synthesizer.synthesize(
            script_data=script,
            ref_image_url=None,
            duration=2,
            theme="tech"
        )
        self.assertEqual(res.get("status"), "success")
        video_p = Path(res.get("video_path", ""))
        self.assertTrue(video_p.exists())
        self.assertGreater(video_p.stat().st_size, 5000)

    def test_tier4_content_evaluator_s_rank_verification(self) -> None:
        """Tier 4.3: Chấm điểm kịch bản viral sinh bởi safe_script_fallback đạt hạng cao (>= 75 điểm)."""
        news_title = "Cảnh báo bẫy lừa đảo việc làm online tại nhà thu nhập cao"
        news_summary = (
            "Nhiều nạn nhân bị lừa hàng trăm triệu đồng khi tham gia các hội nhóm làm nhiệm vụ chốt đơn ảo "
            "với lời hứa hẹn hoa hồng hấp dẫn nhưng sau đó bị khóa tài khoản."
        )
        script = safe_script_fallback(news_title, news_summary)
        source_text = f"{news_title}\n\n{news_summary}"

        eval_result = evaluate_tiktok_script(script, source_text)
        overall_score = eval_result.get("overall_score", 0.0)
        grade = eval_result.get("grade", "")

        self.assertGreaterEqual(
            overall_score, 75.0,
            f"Điểm số tiềm năng viral của kịch bản phải >= 75 (nhận được: {overall_score:.1f}, Grade: {grade})"
        )
        self.assertIn(grade, ["S", "A"], f"Xếp hạng viral phải là Hạng S hoặc Hạng A (nhận được: {grade})")

    def test_tier4_ui_atelier_theme_integration(self) -> None:
        """Tier 4.4: Xác minh các theme tương thích hoàn toàn với danh sách tùy chọn của UI editorial_atelier."""
        # Kiểm tra generate_tiktok_video chấp nhận tham số theme
        script_data = safe_script_fallback("Kiểm thử giao diện", "Xác minh tích hợp tham số theme.")
        res = generate_tiktok_video(
            visual_prompt="Vertical 9:16 aspect ratio video, test cinematic lighting",
            reference_image_url=None,
            script_data=script_data,
            mode="fallback",
            duration=2,
            theme="vibrant"
        )
        self.assertEqual(res.get("status"), "success")
        self.assertTrue(Path(res.get("video_path", "")).exists())


if __name__ == "__main__":
    unittest.main()
