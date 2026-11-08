"""
Comprehensive 4-Tier Opaque-Box E2E Test Suite for Pulse Studio Video Pipeline.

Complies with PROJECT.md architecture and interface contracts:
- Tier 1: Feature Coverage (>=5 tests per feature: TTS synthesis, fallback, card generation, audio ducking, MP4 export)
- Tier 2: Boundary & Corner Cases (>=5 tests: empty text, long text >1000 chars, Vietnamese diacritics, short durations, offline fallback)
- Tier 3: Cross-Feature Combinations (card montage + voiceover + BGM ducking + ASS subtitles)
- Tier 4: Real-World Workloads (complete 20s TikTok production render, H.264/AAC verification, duration sync, speech audibility)
"""

import os
import re
import sys
import json
import shutil
import tempfile
import unittest
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Union
from unittest.mock import patch, MagicMock

import requests

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PIL import Image, ImageDraw

from src.video.muse_integration import (
    synthesize_voiceover,
    _synthesize_edge_tts,
    _synthesize_google_tts,
    SafeFallbackSynthesizer,
    generate_tiktok_video,
    find_ffmpeg_binary,
    _get_font,
)


def find_ffprobe_binary() -> str:
    """Find ffprobe binary on host system."""
    env_bin = os.getenv("FFPROBE_BINARY") or os.getenv("FFPROBE_PATH")
    if env_bin and os.path.isfile(env_bin):
        return env_bin
    which_bin = shutil.which("ffprobe")
    if which_bin:
        return which_bin
    candidates = [
        r"C:\Users\Rynne\AppData\Local\Microsoft\WinGet\Links\ffprobe.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links\ffprobe.exe"),
        r"C:\ffmpeg\bin\ffprobe.exe",
        r"C:\Program Files\ffmpeg\bin\ffprobe.exe",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return "ffprobe"


def probe_media(file_path: Union[str, Path]) -> Dict[str, Any]:
    """Execute ffprobe and parse output JSON for stream details."""
    ffprobe_bin = find_ffprobe_binary()
    cmd = [
        ffprobe_bin,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(file_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(res.stdout)


def probe_audio_volume(file_path: Union[str, Path]) -> Tuple[Optional[float], Optional[float]]:
    """Execute ffmpeg volumedetect filter to extract mean_volume and max_volume in dB."""
    ffmpeg_bin = find_ffmpeg_binary()
    null_sink = "NUL" if os.name == "nt" else "/dev/null"
    cmd = [
        ffmpeg_bin,
        "-i", str(file_path),
        "-af", "volumedetect",
        "-vn", "-sn", "-dn",
        "-f", "null", null_sink,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    mean_match = re.search(r"mean_volume:\s*([-0-9.]+)\s*dB", res.stderr)
    max_match = re.search(r"max_volume:\s*([-0-9.]+)\s*dB", res.stderr)
    mean_vol = float(mean_match.group(1)) if mean_match else None
    max_vol = float(max_match.group(1)) if max_match else None
    return mean_vol, max_vol


def generate_card_adaptive(
    synthesizer: SafeFallbackSynthesizer,
    title: str,
    headline: str,
    color: Tuple[int, int, int],
    ref_image_path: Optional[Path],
    temp_dir: Path,
    scene_num: int = 1,
) -> Path:
    """Adaptive card generator supporting both M2 refactored and baseline interfaces."""
    import inspect
    sig = inspect.signature(synthesizer._generate_card)
    params = list(sig.parameters.keys())
    if "scene" in params:
        scene_dict = {"text": headline, "type": "editorial", "visual_query": title}
        hex_color = f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
        return synthesizer._generate_card(
            scene=scene_dict,
            idx=scene_num,
            total=4,
            title=title,
            base_color=hex_color,
            temp_dir=temp_dir,
        )
    return synthesizer._generate_card(
        title=title,
        headline=headline,
        color=color,
        ref_image_path=ref_image_path,
        temp_dir=temp_dir,
        scene_num=scene_num,
    )


# ==============================================================================
# TIER 1: FEATURE COVERAGE (>=5 tests per feature)
# ==============================================================================

class TestTier1FeatureCoverage(unittest.TestCase):
    """
    Tier 1: Feature Coverage (>=5 tests per feature).
    Validates isolated units: TTS Synthesis, Fallback, Card Generation, Audio Ducking, MP4 Export.
    """

    def setUp(self):
        self.temp_dir_obj = tempfile.TemporaryDirectory()
        self.temp_dir = Path(self.temp_dir_obj.name)
        self.synthesizer = SafeFallbackSynthesizer()
        self.sample_text = "Hà Nội mùa thu tuyệt đẹp với những con phố rợp bóng cây xanh."

    def tearDown(self):
        self.temp_dir_obj.cleanup()

    # --- Feature 1: TTS Synthesis (5 tests) ---

    def test_f1_tts_primary_voice_generates_valid_mp3(self):
        """F1.1: Primary voice (vi-VN-HoaiMyNeural) generates valid MP3 > 1KB."""
        out_path = self.temp_dir / "voice_primary.mp3"
        success = synthesize_voiceover(self.sample_text, out_path, voice="vi-VN-HoaiMyNeural")
        self.assertTrue(success, "Voiceover synthesis should succeed with primary voice")
        self.assertTrue(out_path.exists(), "Output file must exist on disk")
        self.assertGreater(out_path.stat().st_size, 1000, "MP3 file size must be > 1000 bytes")

    def test_f1_tts_secondary_voice_generates_valid_mp3(self):
        """F1.2: Secondary voice (vi-VN-NamMinhNeural) generates valid MP3 > 1KB."""
        out_path = self.temp_dir / "voice_secondary.mp3"
        success = synthesize_voiceover(self.sample_text, out_path, voice="vi-VN-NamMinhNeural")
        self.assertTrue(success, "Voiceover synthesis should succeed with secondary voice")
        self.assertTrue(out_path.exists(), "Output file must exist on disk")
        self.assertGreater(out_path.stat().st_size, 1000, "MP3 file size must be > 1000 bytes")

    def test_f1_tts_audio_format_validity(self):
        """F1.3: Probing synthesized audio confirms MP3 audio container format."""
        out_path = self.temp_dir / "voice_format.mp3"
        synthesize_voiceover(self.sample_text, out_path)
        self.assertTrue(out_path.exists())
        info = probe_media(out_path)
        format_name = info.get("format", {}).get("format_name", "")
        self.assertTrue("mp3" in format_name or "audio" in format_name, f"Expected MP3 format, got {format_name}")
        self.assertGreaterEqual(len(info.get("streams", [])), 1, "Must contain at least 1 stream")

    def test_f1_tts_positive_audio_duration(self):
        """F1.4: Synthesized audio duration is positive and proportional to text."""
        out_path = self.temp_dir / "voice_duration.mp3"
        synthesize_voiceover(self.sample_text, out_path)
        info = probe_media(out_path)
        dur = float(info.get("format", {}).get("duration", 0.0))
        self.assertGreater(dur, 1.0, f"Spoken sentence duration should be > 1.0s, got {dur}")
        self.assertLess(dur, 15.0, f"Spoken sentence duration should be < 15.0s, got {dur}")

    def test_f1_tts_return_code_contract(self):
        """F1.5: synthesize_voiceover strictly returns boolean True on success."""
        out_path = self.temp_dir / "voice_contract.mp3"
        result = synthesize_voiceover("Thử nghiệm hợp đồng giao tiếp.", out_path)
        self.assertIsInstance(result, bool)
        self.assertTrue(result)

    # --- Feature 2: Fallback Mechanism (5 tests) ---

    def test_f2_fallback_secondary_voice_on_primary_failure(self):
        """F2.1: Secondary edge-tts voice activates when primary voice fails."""
        out_path = self.temp_dir / "voice_fallback_sec.mp3"
        call_voices = []

        real_edge_tts = _synthesize_edge_tts

        def mock_edge_tts(text, voice, path):
            call_voices.append(voice)
            if voice == "vi-VN-HoaiMyNeural":
                return False  # Primary fails
            return real_edge_tts(text, voice, path)

        with patch("src.video.muse_integration._synthesize_edge_tts", side_effect=mock_edge_tts):
            success = synthesize_voiceover(self.sample_text, out_path, voice="vi-VN-HoaiMyNeural")

        self.assertTrue(success, "Should succeed via secondary voice fallback")
        self.assertIn("vi-VN-NamMinhNeural", call_voices, "Secondary voice must be attempted")
        self.assertTrue(out_path.exists())
        self.assertGreater(out_path.stat().st_size, 500)

    def test_f2_fallback_google_tts_on_edge_failure(self):
        """F2.2: Google Translate TTS fallback activates when all edge-tts attempts fail."""
        out_path = self.temp_dir / "voice_fallback_google.mp3"

        # Force both edge-tts attempts to fail
        with patch("src.video.muse_integration._synthesize_edge_tts", return_value=False):
            success = synthesize_voiceover("Bản tin dự phòng khẩn cấp tiếng Việt.", out_path)

        self.assertTrue(success, "Should succeed via Google TTS fallback")
        self.assertTrue(out_path.exists())
        self.assertGreater(out_path.stat().st_size, 500)

    def test_f2_fallback_graceful_exception_handling(self):
        """F2.3: synthesize_voiceover handles edge-tts exceptions without crashing."""
        out_path = self.temp_dir / "voice_exception.mp3"

        with patch("edge_tts.Communicate.save", side_effect=ConnectionResetError("Simulated socket drop")):
            with patch("requests.get", side_effect=requests.RequestException("Google TTS down")):
                try:
                    result = synthesize_voiceover("Kiểm tra xử lý ngoại lệ.", out_path)
                except Exception as e:
                    self.fail(f"synthesize_voiceover raised uncaught exception: {e}")
                self.assertFalse(result, "Should return False when all speech engines fail")
                self.assertTrue(out_path.exists(), "Terminal fallback should generate silent MP3")

    def test_f2_fallback_google_tts_vietnamese_diacritics(self):
        """F2.4: Google TTS fallback directly handles heavy Vietnamese diacritics."""
        out_path = self.temp_dir / "google_tts_direct.mp3"
        text = "Trường Đại học Quốc gia, đường Nguyễn Trãi, phở bò đặc biệt."
        ok = _synthesize_google_tts(text, out_path)
        self.assertTrue(ok, "Google TTS must synthesize Vietnamese diacritics")
        self.assertTrue(out_path.exists())
        self.assertGreater(out_path.stat().st_size, 500)

    def test_f2_fallback_all_engines_fail_safe_return(self):
        """F2.5: Returns False without raising when both edge-tts and Google TTS fail, generating terminal silent MP3."""
        out_path = self.temp_dir / "all_fail.mp3"
        with patch("src.video.muse_integration._synthesize_edge_tts", return_value=False):
            with patch("src.video.muse_integration._synthesize_google_tts", return_value=False):
                ret = synthesize_voiceover("Không thể tạo âm thanh", out_path)
                self.assertFalse(ret)
                self.assertTrue(out_path.exists(), "Terminal fallback must create silent audio to prevent pipeline crash")
                self.assertGreater(out_path.stat().st_size, 500)

    # --- Feature 3: Card Graphic Generation (5 tests) ---

    def test_f3_card_dimensions_and_format(self):
        """F3.1: Card generator exports 720x1280 resolution PNG image."""
        card_p = generate_card_adaptive(
            self.synthesizer,
            title="XU HƯỚNG CÔNG NGHỆ",
            headline="Trí tuệ nhân tạo phát triển vượt bậc tại Việt Nam",
            color=(239, 68, 68),
            ref_image_path=None,
            temp_dir=self.temp_dir,
            scene_num=1,
        )
        self.assertTrue(card_p.exists(), "Generated card must exist on disk")
        with Image.open(card_p) as img:
            self.assertEqual(img.size, (720, 1280), "Card dimensions must be 720x1280 (9:16)")
            self.assertEqual(img.format, "PNG", "Card format must be PNG")

    def test_f3_card_visual_components_present(self):
        """F3.2: Card image is non-blank with sufficient color depth and file size."""
        card_p = generate_card_adaptive(
            self.synthesizer,
            title="ĐIỂM TIN SÁNG",
            headline="Thị trường số ghi nhận kỷ lục mới",
            color=(59, 130, 246),
            ref_image_path=None,
            temp_dir=self.temp_dir,
            scene_num=2,
        )
        self.assertGreater(card_p.stat().st_size, 25000, "Card PNG must be > 25KB")
        with Image.open(card_p) as img:
            extrema = img.getextrema()
            # RGB mode has 3 bands, each should have variation
            for band in extrema:
                self.assertNotEqual(band[0], band[1], "Image band must not be monochrome flat")

    def test_f3_card_vietnamese_diacritic_rendering(self):
        """F3.3: Card generator renders all Vietnamese diacritics without font error."""
        headline = "Đường phố Hà Nội rực rỡ cờ hoa, trắc nghiệm lịch sử vẻ vang."
        try:
            card_p = generate_card_adaptive(
                self.synthesizer,
                title="VĂN HÓA TRUYỀN THỐNG",
                headline=headline,
                color=(168, 85, 247),
                ref_image_path=None,
                temp_dir=self.temp_dir,
                scene_num=3,
            )
            self.assertTrue(card_p.exists())
        except Exception as e:
            self.fail(f"Card generation failed on Vietnamese diacritics: {e}")

    def test_f3_card_dynamic_text_wrapping(self):
        """F3.4: Dynamic text wrapping handles lengthy headline without throwing exception."""
        long_headline = (
            "Dự án đường sắt đô thị đoạn trên cao chính thức vận hành thương mại "
            "phục vụ hàng vạn lượt người dân Thủ đô mỗi ngày với chất lượng hiện đại "
            "và tốc độ nhanh chóng vượt mong đợi."
        )
        card_p = generate_card_adaptive(
            self.synthesizer,
            title="GIAO THÔNG ĐÔ THỊ",
            headline=long_headline,
            color=(245, 158, 11),
            ref_image_path=None,
            temp_dir=self.temp_dir,
            scene_num=4,
        )
        self.assertTrue(card_p.exists())
        with Image.open(card_p) as img:
            self.assertEqual(img.size, (720, 1280))

    def test_f3_card_with_reference_image(self):
        """F3.5: Ingesting reference image generates composited card with blur backdrop."""
        ref_img_path = self.temp_dir / "sample_ref.jpg"
        test_img = Image.new("RGB", (600, 400), color=(180, 50, 50))
        draw = ImageDraw.Draw(test_img)
        draw.rectangle([(50, 50), (550, 350)], fill=(50, 180, 50))
        test_img.save(ref_img_path, "JPEG")

        card_p = generate_card_adaptive(
            self.synthesizer,
            title="ẢNH NGUỒN TỰ ĐỘNG",
            headline="Phân tích bố cục đồ họa kết hợp ảnh nền",
            color=(34, 197, 94),
            ref_image_path=ref_img_path,
            temp_dir=self.temp_dir,
            scene_num=1,
        )
        self.assertTrue(card_p.exists())
        self.assertGreater(card_p.stat().st_size, 35000)

    # --- Feature 4: Audio Ducking & Mixing Filter Logic (5 tests) ---

    def test_f4_audio_ducking_filter_syntax_validity(self):
        """F4.1: FFmpeg audio mixing filtergraph compiles and executes without syntax error."""
        voice_p = self.temp_dir / "voice_sample.mp3"
        synthesize_voiceover("Thử nghiệm bộ lọc âm thanh.", voice_p)
        self.assertTrue(voice_p.exists())

        out_mix = self.temp_dir / "mixed_audio.aac"
        ffmpeg_bin = find_ffmpeg_binary()
        filter_complex = (
            "[1:a][2:a]amix=inputs=2:duration=first:normalize=0,volume=0.08[bgm];"
            "[0:a]volume=1.8[vce];"
            "[vce][bgm]amix=inputs=2:duration=first:dropout_transition=2:normalize=0[a]"
        )
        cmd = [
            ffmpeg_bin, "-y",
            "-i", str(voice_p),
            "-f", "lavfi", "-i", "anoisesrc=c=pink:r=44100:a=0.012,lowpass=f=200",
            "-f", "lavfi", "-i", "sine=f=50:r=44100",
            "-filter_complex", filter_complex,
            "-map", "[a]",
            "-c:a", "aac", "-b:a", "128k",
            "-t", "4",
            str(out_mix),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"FFmpeg amix filter failed: {res.stderr}")
        self.assertTrue(out_mix.exists())

    def test_f4_audio_ducking_speech_audibility(self):
        """F4.2: Mixed audio volume preserves speech audibility (max_volume >= -15.0 dB)."""
        voice_p = self.temp_dir / "voice_sample.mp3"
        synthesize_voiceover("Âm lượng giọng đọc phải rõ ràng, vượt trội so với âm nền.", voice_p)
        out_mix = self.temp_dir / "audible_mix.aac"
        ffmpeg_bin = find_ffmpeg_binary()

        filter_complex = (
            "[1:a][2:a]amix=inputs=2:duration=first:normalize=0,volume=0.08[bgm];"
            "[0:a]volume=1.8[vce];"
            "[vce][bgm]amix=inputs=2:duration=first:dropout_transition=2:normalize=0[a]"
        )
        cmd = [
            ffmpeg_bin, "-y",
            "-i", str(voice_p),
            "-f", "lavfi", "-i", "anoisesrc=c=pink:r=44100:a=0.01,lowpass=f=200",
            "-f", "lavfi", "-i", "sine=f=50:r=44100",
            "-filter_complex", filter_complex,
            "-map", "[a]",
            "-c:a", "aac",
            "-t", "5",
            str(out_mix),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        mean_vol, max_vol = probe_audio_volume(out_mix)
        self.assertIsNotNone(max_vol)
        self.assertGreaterEqual(max_vol, -15.0, f"Speech peak volume should be >= -15.0 dB, got {max_vol}")

    def test_f4_audio_ducking_apad_duration_matching(self):
        """
        F4.3: Audio duration matches intended video length when voiceover is shorter.
        NOTE: In baseline implementation, 'duration=first' causes premature audio cutoff.
        This test asserts full duration matching per PROJECT.md interface contract.
        """
        voice_p = self.temp_dir / "voice_short.mp3"
        # 1-second text into a 6-second container
        synthesize_voiceover("Alo.", voice_p)
        target_dur = 6.0
        out_mix = self.temp_dir / "padded_mix.aac"
        ffmpeg_bin = find_ffmpeg_binary()

        # Contract filter with apad
        filter_complex = (
            f"[0:a]apad=whole_dur={target_dur}[vce];"
            "[1:a][2:a]amix=inputs=2:duration=first:normalize=0,volume=0.08[bgm];"
            "[vce][bgm]amix=inputs=2:duration=first:normalize=0[a]"
        )
        cmd = [
            ffmpeg_bin, "-y",
            "-i", str(voice_p),
            "-f", "lavfi", "-i", "anoisesrc=c=pink:r=44100:a=0.01,lowpass=f=200",
            "-f", "lavfi", "-i", "sine=f=50:r=44100",
            "-filter_complex", filter_complex,
            "-map", "[a]",
            "-c:a", "aac",
            "-t", str(target_dur),
            str(out_mix),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and out_mix.exists():
            info = probe_media(out_mix)
            actual_dur = float(info.get("format", {}).get("duration", 0.0))
            self.assertAlmostEqual(actual_dur, target_dur, delta=0.5)
        else:
            self.fail(f"Audio padding filter failed to execute: {res.stderr}")

    def test_f4_audio_ducking_stereo_44k_conformance(self):
        """F4.4: Audio stream output is 44.1kHz stereo."""
        voice_p = self.temp_dir / "voice_stereo.mp3"
        synthesize_voiceover("Kiểm tra thông số kỹ thuật âm thanh stereo.", voice_p)
        out_mix = self.temp_dir / "stereo_mix.aac"
        ffmpeg_bin = find_ffmpeg_binary()

        cmd = [
            ffmpeg_bin, "-y",
            "-i", str(voice_p),
            "-c:a", "aac",
            "-ar", "44100",
            "-ac", "2",
            "-t", "2",
            str(out_mix),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        info = probe_media(out_mix)
        stream = info["streams"][0]
        self.assertEqual(int(stream.get("sample_rate", 0)), 44100)
        self.assertEqual(int(stream.get("channels", 0)), 2)

    def test_f4_audio_ducking_sidechain_attenuation(self):
        """F4.5: Sidechain compression filter syntax executes successfully."""
        ffmpeg_bin = find_ffmpeg_binary()
        out_mix = self.temp_dir / "sidechain_test.aac"
        # Test sidechaincompress syntax: input 0 is BGM, input 1 is voice trigger
        filter_complex = "[0:a][1:a]sidechaincompress=threshold=0.08:ratio=4:attack=50:release=300[a]"
        cmd = [
            ffmpeg_bin, "-y",
            "-f", "lavfi", "-i", "anoisesrc=c=pink:r=44100:a=0.1",
            "-f", "lavfi", "-i", "sine=f=440:r=44100:d=2",
            "-filter_complex", filter_complex,
            "-map", "[a]",
            "-c:a", "aac",
            "-t", "2",
            str(out_mix),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"sidechaincompress execution failed: {res.stderr}")
        self.assertTrue(out_mix.exists())

    # --- Feature 5: MP4 Container & Video Export (5 tests) ---

    def test_f5_mp4_faststart_movflags(self):
        """F5.1: Exported MP4 includes faststart / isom major brand for web playback."""
        res = self.synthesizer.synthesize(
            script_data={"hook": "Thử nghiệm FastStart"},
            duration=2,
        )
        video_path = res.get("video_path")
        self.assertTrue(os.path.exists(video_path))
        info = probe_media(video_path)
        format_info = info.get("format", {})
        tags = format_info.get("tags", {})
        major_brand = tags.get("major_brand", "")
        self.assertTrue(
            major_brand in ("isom", "mp42", "avc1"),
            f"Expected web-compatible brand, got {major_brand}",
        )

    def test_f5_mp4_video_codec_h264(self):
        """F5.2: Stream 0 is encoded with H.264 (avc1) codec."""
        res = self.synthesizer.synthesize(
            script_data={"hook": "Thử nghiệm Codec H264"},
            duration=2,
        )
        info = probe_media(res["video_path"])
        v_stream = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
        self.assertIsNotNone(v_stream, "Must have a video stream")
        self.assertEqual(v_stream["codec_name"], "h264")

    def test_f5_mp4_audio_codec_aac(self):
        """F5.3: Stream 1 is encoded with AAC codec."""
        res = self.synthesizer.synthesize(
            script_data={"hook": "Thử nghiệm Codec AAC"},
            duration=2,
        )
        info = probe_media(res["video_path"])
        a_stream = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
        self.assertIsNotNone(a_stream, "Must have an audio stream")
        self.assertEqual(a_stream["codec_name"], "aac")

    def test_f5_mp4_frame_dimensions_and_rate(self):
        """F5.4: Video dimensions are 720x1280 and framerate is 25 fps."""
        res = self.synthesizer.synthesize(
            script_data={"hook": "Thử nghiệm Kích thước Khung hình"},
            duration=2,
        )
        info = probe_media(res["video_path"])
        v_stream = next(s for s in info["streams"] if s["codec_type"] == "video")
        self.assertEqual(int(v_stream["width"]), 720)
        self.assertEqual(int(v_stream["height"]), 1280)
        self.assertEqual(v_stream["r_frame_rate"], "25/1")

    def test_f5_mp4_pixel_format_yuv420p(self):
        """F5.5: Video stream pixel format is yuv420p for standard mobile compatibility."""
        res = self.synthesizer.synthesize(
            script_data={"hook": "Thử nghiệm Pixel Format"},
            duration=2,
        )
        info = probe_media(res["video_path"])
        v_stream = next(s for s in info["streams"] if s["codec_type"] == "video")
        self.assertEqual(v_stream["pix_fmt"], "yuv420p")


# ==============================================================================
# TIER 2: BOUNDARY & CORNER CASES (>=5 tests)
# ==============================================================================

class TestTier2BoundaryAndCorners(unittest.TestCase):
    """
    Tier 2: Boundary & Corner Cases.
    Tests extreme inputs: empty text, long scripts (>1000 chars), diacritics, durations, offline faults.
    """

    def setUp(self):
        self.temp_dir_obj = tempfile.TemporaryDirectory()
        self.temp_dir = Path(self.temp_dir_obj.name)
        self.synthesizer = SafeFallbackSynthesizer()

    def tearDown(self):
        self.temp_dir_obj.cleanup()

    def test_tier2_empty_or_whitespace_script(self):
        """T2.1: Empty or whitespace-only script text safely returns False without raising."""
        out_p = self.temp_dir / "empty.mp3"
        self.assertFalse(synthesize_voiceover("", out_p))
        self.assertFalse(synthesize_voiceover("   \t\n  ", out_p))
        self.assertFalse(out_p.exists())

    def test_tier2_long_script_over_1000_chars(self):
        """T2.2: Script text > 1000 characters is synthesized without crash or unhandled error."""
        long_text = (
            "Kính thưa quý vị độc giả, hôm nay chúng tôi xin trân trọng giới thiệu một bức tranh toàn cảnh "
            "về sự chuyển dịch công nghệ trong kỷ nguyên mới. Hàng loạt doanh nghiệp tại khu vực Đông Nam Á "
            "đang tích cực ứng dụng các mô hình trí tuệ nhân tạo tạo sinh nhằm nâng cao năng suất lao động. "
            "Tại Việt Nam, các kỹ sư phần mềm không ngừng sáng tạo, phát triển các giải pháp đột phá "
            "từ phân tích dữ liệu lớn, xử lý ngôn ngữ tự nhiên cho đến tự động hóa quy trình sản xuất nội dung số. "
            "Đây là minh chứng rõ ràng cho tinh thần vươn lên, bắt nhịp xu thế công nghệ toàn cầu. "
            "Chúng ta hoàn toàn có quyền tin tưởng vào một tương lai tươi sáng, nơi các sản phẩm công nghệ "
            "Make in Viet Nam vươn tầm thế giới, khẳng định trí tuệ và bản lĩnh của con người Việt Nam. "
            "Bên cạnh đó, việc xây dựng cơ sở hạ tầng số hiện đại, bảo mật thông tin và đào tạo nguồn nhân lực "
            "chất lượng cao là những trụ cột then chốt giúp đất nước bứt phá mạnh mẽ trong cuộc cách mạng công nghiệp lần thứ tư. "
            "Mỗi cá nhân, mỗi tổ chức hãy cùng chung tay hành động vì một Việt Nam số thịnh vượng và vững bền. "
            "Cảm ơn quý vị đã luôn đồng hành và theo dõi những bước tiến vượt bậc này trong suốt thời gian qua. "
            "Chúng tôi cam kết sẽ tiếp tục nghiên cứu và mang tới những giải pháp trí tuệ nhân tạo tối ưu nhất, "
            "góp phần phụng sự cộng đồng công nghệ Việt Nam ngày càng phát triển vững chắc hơn nữa."
        )
        self.assertGreater(len(long_text), 1000, "Text must exceed 1000 characters")
        out_p = self.temp_dir / "long_script.mp3"
        ok = synthesize_voiceover(long_text, out_p)
        self.assertTrue(ok, "Long script should synthesize successfully")
        self.assertTrue(out_p.exists())
        self.assertGreater(out_p.stat().st_size, 5000)

    def test_tier2_complex_vietnamese_diacritics(self):
        """T2.3: Text containing all Vietnamese vowels and tone marks renders across card and TTS."""
        diacritics_text = "Học sinh Trường THPT Chuyên, đường Nguyễn Trãi, phở bò, khuất tất, khởi sắc, bứt phá!"
        # 1. Test TTS
        out_voice = self.temp_dir / "diacritics.mp3"
        ok_voice = synthesize_voiceover(diacritics_text, out_voice)
        self.assertTrue(ok_voice)
        self.assertGreater(out_voice.stat().st_size, 1000)

        # 2. Test Card
        card_p = generate_card_adaptive(
            self.synthesizer,
            title="TIẾNG VIỆT CÓ DẤU",
            headline=diacritics_text,
            color=(239, 68, 68),
            ref_image_path=None,
            temp_dir=self.temp_dir,
            scene_num=1,
        )
        self.assertTrue(card_p.exists())
        with Image.open(card_p) as img:
            self.assertEqual(img.size, (720, 1280))

    def test_tier2_short_duration_boundaries(self):
        """T2.4: Ultra-short durations (1s, 2s) successfully route to fast single-scene bypass."""
        for dur in (1, 2):
            res = self.synthesizer.synthesize(
                script_data={"hook": f"Short duration {dur}s test"},
                duration=dur,
            )
            self.assertEqual(res["status"], "success")
            self.assertTrue(os.path.exists(res["video_path"]))
            info = probe_media(res["video_path"])
            vid_dur = float(info.get("format", {}).get("duration", 0.0))
            self.assertAlmostEqual(vid_dur, float(dur), delta=0.5)

    def test_tier2_duration_boundary_transition(self):
        """T2.5: Duration 9s routes to fast single-scene, duration 10s routes to montage."""
        res_9 = self.synthesizer.synthesize(
            script_data={"hook": "Fast single scene boundary"},
            duration=9,
        )
        self.assertEqual(res_9["status"], "success")
        self.assertIn("Single-Scene", res_9.get("message", ""))

        res_10 = self.synthesizer.synthesize(
            script_data={"hook": "Multi-scene montage boundary"},
            duration=10,
        )
        self.assertEqual(res_10["status"], "success")
        self.assertIn("Multi-Scene", res_10.get("message", ""))

    def test_tier2_offline_socket_failure_simulation(self):
        """T2.6: Simulated network socket disconnect recovers safely without uncaught crash."""
        out_p = self.temp_dir / "socket_offline.mp3"

        with patch("edge_tts.Communicate.save", side_effect=OSError("Network unreachable [Errno 101]")):
            with patch("requests.get", side_effect=requests.RequestException("Network unreachable")):
                try:
                    result = synthesize_voiceover("Thử nghiệm lỗi kết nối mạng.", out_p)
                except Exception as e:
                    self.fail(f"Pipeline crashed on socket disconnect: {e}")
                self.assertFalse(result, "Should safely return False on offline failure")
                self.assertTrue(out_p.exists(), "Terminal fallback should generate silent MP3")

    def test_tier2_missing_reference_image_fallback(self):
        """T2.7: Providing non-existent ref_image_path cleanly falls back to gradient background."""
        non_existent_img = self.temp_dir / "does_not_exist_9999.jpg"
        card_p = generate_card_adaptive(
            self.synthesizer,
            title="FALLBACK GRADIENT",
            headline="Ảnh tham chiếu không tồn tại, tự động chuyển về nền màu",
            color=(139, 92, 246),
            ref_image_path=non_existent_img,
            temp_dir=self.temp_dir,
            scene_num=1,
        )
        self.assertTrue(card_p.exists())
        with Image.open(card_p) as img:
            self.assertEqual(img.size, (720, 1280))


# ==============================================================================
# TIER 3: CROSS-FEATURE COMBINATIONS
# ==============================================================================

class TestTier3CrossFeatureCombinations(unittest.TestCase):
    """
    Tier 3: Cross-Feature Combinations.
    Tests end-to-end multi-scene montage: cards + voiceover + BGM ducking + ASS subtitles.
    """

    def setUp(self):
        self.temp_dir_obj = tempfile.TemporaryDirectory()
        self.temp_dir = Path(self.temp_dir_obj.name)
        self.synthesizer = SafeFallbackSynthesizer()

    def tearDown(self):
        self.temp_dir_obj.cleanup()

    def test_tier3_multiscene_card_montage_integration(self):
        """T3.1: 4 visual scene cards linked into multi-scene pipeline with distinct colors and headlines."""
        custom_script = {
            "scenes": [
                {"scene_num": 1, "title": "Cảnh 1 - Mở đầu", "voice_text": "Chào mừng bạn đến với chương trình."},
                {"scene_num": 2, "title": "Cảnh 2 - Bóc tách", "voice_text": "Nội dung phân tích thực tế chi tiết."},
                {"scene_num": 3, "title": "Cảnh 3 - Bằng chứng", "voice_text": "Các số liệu chứng minh rất thuyết phục."},
                {"scene_num": 4, "title": "Cảnh 4 - Kêu gọi", "voice_text": "Hãy để lại bình luận bên dưới nhé."},
            ]
        }
        res = self.synthesizer.synthesize(
            script_data=custom_script,
            duration=12,
        )
        self.assertEqual(res["status"], "success")
        self.assertTrue(os.path.exists(res["video_path"]))
        info = probe_media(res["video_path"])
        self.assertGreaterEqual(len(info["streams"]), 2)

    def test_tier3_synchronized_ass_subtitles(self):
        """T3.2: Generated ASS subtitle file contains headers, styles, and non-overlapping scene timings."""
        scene_timings = [
            (0.0, 3.0, "HookStyle", r"{\an5\b1}CẢNH BÁO XU HƯỚNG MỚI!"),
            (3.0, 7.0, "BodyStyle", r"{\an2}Nội dung phân tích diễn biến chi tiết."),
            (7.0, 10.0, "EvidStyle", r"{\an2}Bằng chứng số liệu xác thực."),
            (10.0, 14.0, "CTAStyle", r"{\an2\b1}Hãy đăng ký kênh ngay hôm nay!"),
        ]
        ass_path = self.synthesizer._generate_multiscene_ass(scene_timings, self.temp_dir)
        self.assertTrue(ass_path.exists())

        content = ass_path.read_text(encoding="utf-8")
        self.assertIn("[Script Info]", content)
        self.assertIn("[V4+ Styles]", content)
        self.assertIn("HookStyle", content)
        self.assertIn("BodyStyle", content)
        self.assertIn("EvidStyle", content)
        self.assertIn("CTAStyle", content)
        self.assertIn("Dialogue: 0,0:00:00.00,0:00:03.00,HookStyle", content)
        self.assertIn("Dialogue: 0,0:00:10.00,0:00:14.00,CTAStyle", content)

    def test_tier3_voiceover_failure_pipeline_resilience(self):
        """T3.3: Multi-scene render succeeds with ambient BGM even if voiceover synthesis fails."""
        with patch("src.video.muse_integration.synthesize_voiceover", return_value=False):
            res = self.synthesizer.synthesize(
                script_data={"hook": "Thử nghiệm khi voiceover lỗi"},
                duration=10,
            )
            self.assertEqual(res["status"], "success")
            self.assertTrue(os.path.exists(res["video_path"]))
            info = probe_media(res["video_path"])
            # Video must still have valid audio stream (ambient BGM)
            a_stream = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
            self.assertIsNotNone(a_stream)

    def test_tier3_combined_ducking_over_multiscene_visual(self):
        """T3.4: Multi-scene render multiplexes video, voiceover, and BGM into valid container."""
        res = self.synthesizer.synthesize(
            script_data={
                "hook": "BẢN TIN CÔNG NGHỆ NHANH",
                "body": "Trí tuệ nhân tạo đang làm thay đổi toàn bộ quy trình làm việc hiện đại.",
                "cta": "Bấm theo dõi để cập nhật thêm!",
            },
            duration=12,
        )
        self.assertEqual(res["status"], "success")
        info = probe_media(res["video_path"])
        v_stream = next(s for s in info["streams"] if s["codec_type"] == "video")
        a_stream = next(s for s in info["streams"] if s["codec_type"] == "audio")
        self.assertEqual(v_stream["codec_name"], "h264")
        self.assertEqual(a_stream["codec_name"], "aac")

    def test_tier3_reference_image_end_to_end(self):
        """T3.5: Multi-scene render handles remote image URL download and card integration."""
        sample_img = self.temp_dir / "online_mock.jpg"
        img = Image.new("RGB", (720, 720), color=(30, 60, 90))
        img.save(sample_img, "JPEG")

        # Mock download to return this local file
        with patch.object(self.synthesizer, "_download_image", return_value=sample_img):
            res = self.synthesizer.synthesize(
                script_data={"hook": "Thử nghiệm ảnh nền đa phân cảnh"},
                ref_image_url="http://mock.test/sample.jpg",
                duration=10,
            )
            self.assertEqual(res["status"], "success")
            self.assertTrue(os.path.exists(res["video_path"]))


# ==============================================================================
# TIER 4: REAL-WORLD WORKLOAD (Complete 20s TikTok Production Render)
# ==============================================================================

class TestTier4RealWorldWorkloads(unittest.TestCase):
    """
    Tier 4: Real-World Workloads.
    Renders full 20-second TikTok vertical video and verifies H.264/AAC, duration sync, and speech audibility.
    """

    @classmethod
    def setUpClass(cls):
        """Render one full 20s production video to share across verification tests."""
        cls.synthesizer = SafeFallbackSynthesizer()
        cls.script_data = {
            "hook": "CẢNH BÁO BẢO MẬT KHẨN CẤP!",
            "body": "Nhiều người dùng bất ngờ bị chiếm đoạt tài khoản do bấm vào các liên kết độc hại trên mạng xã hội. Các chuyên gia khuyến cáo tuyệt đối không chia sẻ mã xác thực.",
            "cta": "Hãy chia sẻ ngay cho bạn bè và người thân!",
            "scenes": [
                {"scene_num": 1, "title": "Cảnh báo khẩn cấp", "voice_text": "Cảnh báo bảo mật tài khoản khẩn cấp trên mạng xã hội."},
                {"scene_num": 2, "title": "Chiêu trò tinh vi", "voice_text": "Đối tượng giả danh gửi liên kết trúng thưởng để đánh cắp mã OTP."},
                {"scene_num": 3, "title": "Thiệt hại thực tế", "voice_text": "Nhiều nạn nhân đã bị phong tỏa tài khoản trong tích tắc."},
                {"scene_num": 4, "title": "Biện pháp phòng ngừa", "voice_text": "Tuyệt đối không nhấp link lạ và bật xác thực hai bước ngay hôm nay."},
            ]
        }
        cls.target_duration = 20
        cls.render_result = cls.synthesizer.synthesize(
            script_data=cls.script_data,
            duration=cls.target_duration,
            voice="vi-VN-HoaiMyNeural",
        )
        cls.video_path = cls.render_result.get("video_path")
        cls.media_info = probe_media(cls.video_path)

    def test_tier4_full_20s_production_render_conformance(self):
        """T4.1: Complete 20-second TikTok production render conforms to H.264/AAC and 720x1280."""
        self.assertEqual(self.render_result.get("status"), "success")
        self.assertTrue(os.path.exists(self.video_path), f"File {self.video_path} must exist")
        self.assertGreater(os.path.getsize(self.video_path), 500000, "20s video must be > 500KB")

        v_stream = next((s for s in self.media_info["streams"] if s["codec_type"] == "video"), None)
        a_stream = next((s for s in self.media_info["streams"] if s["codec_type"] == "audio"), None)

        self.assertIsNotNone(v_stream, "Must contain a video stream")
        self.assertIsNotNone(a_stream, "Must contain an audio stream")

        self.assertEqual(v_stream["codec_name"], "h264")
        self.assertEqual(v_stream["codec_tag_string"], "avc1")
        self.assertEqual(int(v_stream["width"]), 720)
        self.assertEqual(int(v_stream["height"]), 1280)
        self.assertEqual(v_stream["r_frame_rate"], "25/1")
        self.assertEqual(v_stream["pix_fmt"], "yuv420p")

        self.assertEqual(a_stream["codec_name"], "aac")
        self.assertEqual(a_stream["codec_tag_string"], "mp4a")

    def test_tier4_audio_video_duration_synchronization(self):
        """
        T4.2: Audio duration matches video duration within 0.5s tolerance.
        CRITICAL: Detects premature audio cutoff defect caused by 'amix duration=first' without apad.
        """
        v_stream = next(s for s in self.media_info["streams"] if s["codec_type"] == "video")
        a_stream = next(s for s in self.media_info["streams"] if s["codec_type"] == "audio")

        v_dur = float(v_stream.get("duration") or self.media_info["format"].get("duration", 0.0))
        a_dur = float(a_stream.get("duration", 0.0))

        diff = abs(v_dur - a_dur)
        self.assertLessEqual(
            diff,
            0.5,
            f"Premature audio cutoff detected! Video duration: {v_dur:.2f}s, Audio duration: {a_dur:.2f}s, Delta: {diff:.2f}s",
        )

    def test_tier4_speech_audibility_over_ducked_bgm(self):
        """T4.3: Speech volume is audible over ducked BGM (mean_volume >= -35.0 dB, max_volume >= -15.0 dB)."""
        mean_vol, max_vol = probe_audio_volume(self.video_path)
        self.assertIsNotNone(mean_vol, "Mean volume must be measurable")
        self.assertIsNotNone(max_vol, "Max volume must be measurable")

        self.assertGreaterEqual(
            mean_vol,
            -35.0,
            f"Audio overall volume is too low/muted! mean_volume: {mean_vol:.1f} dB",
        )
        self.assertGreaterEqual(
            max_vol,
            -15.0,
            f"Speech peak volume is too quiet/suppressed! max_volume: {max_vol:.1f} dB",
        )

    def test_tier4_facade_generate_tiktok_video(self):
        """T4.4: Top-level facade generate_tiktok_video() successfully produces 15s video in fallback mode."""
        res = generate_tiktok_video(
            visual_prompt="Tin tức kinh tế mới nhất trong ngày",
            mode="fallback",
            duration=15,
        )
        self.assertEqual(res["status"], "success")
        vid_p = res.get("video_path")
        self.assertTrue(os.path.exists(vid_p))
        self.assertGreater(os.path.getsize(vid_p), 400000)
        info = probe_media(vid_p)
        self.assertEqual(len([s for s in info["streams"] if s["codec_type"] in ("video", "audio")]), 2)


# ==============================================================================
# MAIN TEST RUNNER
# ==============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print(" PULSE STUDIO E2E VIDEO PIPELINE TEST SUITE (TIERS 1 - 4)")
    print("=" * 80)
    runner = unittest.TextTestRunner(verbosity=2)
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    result = runner.run(suite)
    sys.exit(not result.wasSuccessful())
