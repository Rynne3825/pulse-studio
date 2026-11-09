"""
Tầng Tạo Sinh Video TikTok 9:16 Tích Hợp Muse AI REST API và Studio Multi-Scene Synthesizer.
Tuân thủ hợp đồng Contract 4, đặc tả giao thức czg86389-hub/muse2api và HosiFlow 4-scene locks.
"""

import os
import re
import time
import shutil
import hashlib
import logging
import tempfile
import subprocess
import asyncio
import concurrent.futures
import urllib.request
import urllib.parse
from datetime import datetime
from typing import Dict, List, Optional, Union, Tuple, Any
from pathlib import Path

import requests
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFilter, ImageFont

load_dotenv()
logger = logging.getLogger(__name__)

ScriptDataValue = Union[str, int, float, List[Dict[str, Union[str, int]]], Dict[str, str], object]
ScriptDict = Dict[str, ScriptDataValue]

# Thư mục lưu trữ video đầu ra (đảm bảo tuyệt đối trỏ về project root)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = BASE_DIR / "data" / "output_videos"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def find_ffmpeg_binary() -> str:
    """Tự động tìm kiếm binary FFmpeg theo thứ tự ưu tiên."""
    env_bin = os.getenv("FFMPEG_BINARY") or os.getenv("FFMPEG_PATH")
    if env_bin and os.path.isfile(env_bin):
        return env_bin

    which_bin = shutil.which("ffmpeg")
    if which_bin:
        return which_bin

    candidates = [
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links\ffmpeg.exe"),
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe"
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c

    return "ffmpeg"


def _get_font(size: int, bold: bool = False, font_family: Optional[str] = None) -> ImageFont.ImageFont:
    """Tự động tải font TrueType Windows với fallback an toàn theo font_family."""
    family_candidates: Dict[str, Dict[str, List[str]]] = {
        "georgia": {
            "bold": [r"C:\Windows\Fonts\georgiab.ttf", r"C:\Windows\Fonts\georgia.ttf"],
            "regular": [r"C:\Windows\Fonts\georgia.ttf"],
        },
        "bahnschrift": {
            "bold": [r"C:\Windows\Fonts\bahnschrift.ttf"],
            "regular": [r"C:\Windows\Fonts\bahnschrift.ttf"],
        },
        "consola": {
            "bold": [r"C:\Windows\Fonts\consolab.ttf", r"C:\Windows\Fonts\consola.ttf"],
            "regular": [r"C:\Windows\Fonts\consola.ttf"],
        },
        "segoeui": {
            "bold": [r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\segoeui.ttf"],
            "regular": [r"C:\Windows\Fonts\segoeui.ttf"],
        },
        "arial": {
            "bold": [r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\arial.ttf"],
            "regular": [r"C:\Windows\Fonts\arial.ttf"],
        },
    }

    candidates: List[str] = []
    if font_family and font_family.lower() in family_candidates:
        fam = family_candidates[font_family.lower()]
        candidates.extend(fam["bold"] if bold else fam["regular"])

    # Fallback tiêu chuẩn Segoe UI / Arial
    fallback = (
        [r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\arialbd.ttf"]
        if bold
        else [r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf"]
    )
    for c in fallback:
        if c not in candidates:
            candidates.append(c)

    for c in candidates:
        if os.path.isfile(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                continue
    try:
        return ImageFont.load_default()
    except Exception:
        return ImageFont.load_default()


def _synthesize_edge_tts(text: str, voice: str, out_path: Path, max_retries: int = 2) -> bool:
    """Chạy edge-tts trong worker thread riêng với asyncio loop độc lập và cơ chế retry."""
    import edge_tts

    def _worker(target_file: Path) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            comm = edge_tts.Communicate(text, voice)
            loop.run_until_complete(comm.save(str(target_file)))
        finally:
            try:
                loop.close()
            except Exception:
                pass

    timeout = max(30.0, len(text) * 0.1)

    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                time.sleep(1.0 * attempt)
            if out_path.exists():
                out_path.unlink(missing_ok=True)

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_worker, out_path)
                future.result(timeout=timeout)

            if out_path.exists() and out_path.stat().st_size > 1000:
                return True
        except Exception as e:
            logger.warning("edge-tts (%s) lần thử %d thất bại: %s", voice, attempt + 1, e)
            if out_path.exists():
                out_path.unlink(missing_ok=True)

    return False


def _synthesize_google_tts(text: str, out_path: Path) -> bool:
    """Google Translate TTS (tw-ob client) chuẩn tiếng Việt 100% qua requests."""
    try:
        sentences = [s.strip() for s in re.split(r'[,.!?;\n]+', text) if s.strip()]
        if not sentences:
            return False

        chunks: List[str] = []
        cur = ""
        for s in sentences:
            if len(cur) + len(s) + 1 < 140:
                cur = f"{cur} {s}".strip()
            else:
                if cur:
                    chunks.append(cur)
                if len(s) >= 140:
                    words = s.split()
                    w_cur = ""
                    for w in words:
                        if len(w_cur) + len(w) + 1 < 140:
                            w_cur = f"{w_cur} {w}".strip()
                        else:
                            if w_cur:
                                chunks.append(w_cur)
                            w_cur = w
                    cur = w_cur
                else:
                    cur = s
        if cur:
            chunks.append(cur)

        audio_parts: List[bytes] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        for chunk in chunks:
            q = urllib.parse.quote(chunk)
            url = f"https://translate.google.com/translate_tts?ie=UTF-8&q={q}&tl=vi&client=tw-ob"
            chunk_success = False
            for retry in range(3):
                try:
                    resp = requests.get(url, headers=headers, timeout=10)
                    if resp.status_code == 200 and len(resp.content) > 100:
                        audio_parts.append(resp.content)
                        chunk_success = True
                        break
                except Exception as ex:
                    logger.warning("Google TTS chunk retry %d lỗi: %s", retry + 1, ex)
                    time.sleep(0.5)
            if not chunk_success:
                return False

        if audio_parts:
            out_path.write_bytes(b"".join(audio_parts))
            return out_path.exists() and out_path.stat().st_size > 1000
    except Exception as e:
        logger.warning("Google TTS fallback gặp sự cố: %s", e)
    return False


def _generate_silent_audio(out_path: Path, duration: float = 10.0) -> bool:
    """Tạo audio im lặng chuẩn MP3 qua FFmpeg làm terminal fallback tránh gián đoạn pipeline."""
    try:
        ffmpeg_bin = find_ffmpeg_binary()
        cmd = [
            ffmpeg_bin, "-y",
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-t", str(max(1.0, duration)),
            "-c:a", "libmp3lame", "-b:a", "128k",
            str(out_path)
        ]
        proc = subprocess.run(cmd, capture_output=True, timeout=10)
        return out_path.exists() and out_path.stat().st_size > 500
    except Exception as e:
        logger.warning("Không thể tạo audio im lặng fallback: %s", e)
        return False


def synthesize_voiceover(
    text: str,
    output_path: Optional[Union[str, Path]] = None,
    voice: str = "vi-VN-HoaiMyNeural",
    out_path: Optional[Union[str, Path]] = None
) -> bool:
    """
    Tạo giọng đọc tiếng Việt Dual-Engine chuẩn:
    1. edge-tts qua ThreadPoolExecutor (Tránh xung đột Streamlit event loop, retry 2 lần).
       Thử giọng chính (ví dụ: vi-VN-HoaiMyNeural), nếu lỗi thử giọng phụ (vi-VN-NamMinhNeural).
    2. Native Google Translate TTS fallback qua requests (100% chuẩn giọng Việt, 0 dependencies).
    3. Terminal fallback: Graceful silence MP3 tránh crash pipeline.
    """
    dest_path = output_path if output_path is not None else out_path
    if dest_path is None:
        raise ValueError("synthesize_voiceover yêu cầu chỉ định output_path hoặc out_path.")
    target_path = Path(dest_path)
    clean_text = re.sub(r'[\r\n\t]+', ' ', text).strip()
    if not clean_text:
        return False

    # 1. edge-tts (Primary voice)
    try:
        if _synthesize_edge_tts(clean_text, voice, target_path):
            logger.info("Voiceover tạo thành công qua edge-tts [%s] (%s bytes)", voice, target_path.stat().st_size)
            return True
    except Exception as e:
        logger.warning(f"edge-tts ({voice}) exception: {e}")

    # 1b. edge-tts (Secondary voice)
    secondary_voice = "vi-VN-NamMinhNeural" if voice != "vi-VN-NamMinhNeural" else "vi-VN-HoaiMyNeural"
    try:
        if _synthesize_edge_tts(clean_text, secondary_voice, target_path):
            logger.info("Voiceover tạo thành công qua edge-tts fallback [%s] (%s bytes)", secondary_voice, target_path.stat().st_size)
            return True
    except Exception as e:
        logger.warning(f"edge-tts ({secondary_voice}) exception: {e}")

    # 2. Native Google Translate TTS fallback
    try:
        if _synthesize_google_tts(clean_text, target_path):
            logger.info("Voiceover tạo thành công qua Google TTS fallback (%s bytes)", target_path.stat().st_size)
            return True
    except Exception as e:
        logger.warning(f"Google TTS fallback exception: {e}")

    # 3. Terminal fallback: Graceful silence MP3 generator
    logger.error("Không thể tổng hợp giọng đọc tiếng Việt qua edge-tts và Google TTS. Kích hoạt terminal fallback im lặng.")
    est_duration = max(3.0, len(clean_text.split()) / 3.0)
    _generate_silent_audio(target_path, duration=est_duration)
    return False


# ==============================================================================
# HỆ THỐNG PRESET THEME ĐỒ HỌA & VISUAL DỰNG VIDEO (MILESTONE 1)
# ==============================================================================
THEME_PRESETS: Dict[str, Dict[str, Any]] = {
    "editorial": {
        "id": "editorial",
        "name": "Editorial Classic",
        "description": "Tạp chí cổ điển, thanh lịch với tông trầm sang trọng và chữ có chân Georgia",
        "font_family": "georgia",
        "title_color": (245, 158, 11),       # Amber Gold
        "headline_color": (255, 255, 255),    # Pure White
        "meta_color": (148, 163, 184),        # Slate 400
        "bg_gradient_start": (15, 23, 42),    # Slate 900
        "bg_gradient_end": (24, 24, 37),      # Deep Charcoal
        "banner_bg": (30, 41, 59),            # Slate 800
        "banner_border": (245, 158, 11),      # Amber
        "panel_bg": (24, 24, 37),             # Charcoal
        "panel_border": (71, 85, 105),        # Slate 600
        "card_border": (245, 158, 11),        # Amber Accent
        "badge_bg": (30, 41, 59),
        "scene_colors": [
            (239, 68, 68),   # Đỏ Hook
            (59, 130, 246),  # Xanh Body
            (168, 85, 247),  # Tím Evidence
            (245, 158, 11),  # Vàng Cam CTA
        ],
        "motions": [
            "zoompan=z='min(zoom+0.0015,1.20)':d={fps_dur}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=720x1280:fps=25",
            "zoompan=z='1.1':d={fps_dur}:x='iw/2-(iw/zoom/2)+sin(on/30)*20':y='ih/2-(ih/zoom/2)':s=720x1280:fps=25",
            "zoompan=z='max(1.20-0.0015*on,1.0)':d={fps_dur}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=720x1280:fps=25",
            "zoompan=z='1.05':d={fps_dur}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=720x1280:fps=25",
        ],
        "single_motion": "zoompan=z='min(zoom+0.0015,1.25)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=720x1280:fps=25",
        "tags": "#ThePulse #TikTokTrending #PhanTichXuHuong",
        "swatches": ["#0F172A", "#F59E0B", "#FFFFFF", "#94A3B8"],
    },
    "vibrant": {
        "id": "vibrant",
        "name": "Vibrant Energy",
        "description": "Sôi động, kích thích thị giác với sắc đỏ cam bùng nổ và chuyển động nhịp độ cao",
        "font_family": "bahnschrift",
        "title_color": (255, 90, 60),        # Vibrant Coral/Orange
        "headline_color": (255, 255, 255),    # Pure White
        "meta_color": (251, 191, 36),         # Amber 400
        "bg_gradient_start": (45, 10, 20),    # Deep Crimson Red
        "bg_gradient_end": (20, 6, 28),       # Dark Plum
        "banner_bg": (65, 14, 28),            # Crimson Slate
        "banner_border": (255, 60, 60),       # Bright Coral
        "panel_bg": (38, 12, 26),             # Rich Burgundy
        "panel_border": (244, 63, 94),        # Rose 500
        "card_border": (255, 75, 43),         # Hot Orange
        "badge_bg": (60, 16, 28),
        "scene_colors": [
            (255, 59, 48),   # Hook Red
            (255, 149, 0),   # Body Orange
            (255, 204, 0),   # Evidence Gold
            (255, 45, 85),   # CTA Hot Pink
        ],
        "motions": [
            "zoompan=z='min(zoom+0.003,1.30)':d={fps_dur}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=720x1280:fps=25",
            "zoompan=z='1.15':d={fps_dur}:x='iw/2-(iw/zoom/2)+sin(on/15)*40':y='ih/2-(ih/zoom/2)':s=720x1280:fps=25",
            "zoompan=z='max(1.30-0.003*on,1.05)':d={fps_dur}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=720x1280:fps=25",
            "zoompan=z='min(zoom+0.002,1.2)':d={fps_dur}:x='iw/2-(iw/zoom/2)+cos(on/20)*25':y='ih/2-(ih/zoom/2)':s=720x1280:fps=25",
        ],
        "single_motion": "zoompan=z='min(zoom+0.0025,1.3)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=720x1280:fps=25",
        "tags": "#ThePulse #VibrantEnergy #TikTokViral #TrendingNow",
        "swatches": ["#FF3B30", "#FF9500", "#FFCC00", "#FF2D55"],
    },
    "neon": {
        "id": "neon",
        "name": "Neon Cyberpunk",
        "description": "Ánh sáng neon đêm tối, viền ngọc lam rực rỡ và magenta siêu thực",
        "font_family": "bahnschrift",
        "title_color": (0, 245, 255),         # Electric Cyan
        "headline_color": (255, 255, 255),    # Pure White
        "meta_color": (224, 86, 253),         # Neon Purple
        "bg_gradient_start": (8, 10, 26),     # Midnight Abyss
        "bg_gradient_end": (18, 6, 32),       # Dark Cyber Magenta
        "banner_bg": (16, 18, 42),            # Dark Indigo
        "banner_border": (0, 240, 255),       # Neon Cyan
        "panel_bg": (18, 14, 38),             # Dark Neon Purple
        "panel_border": (255, 0, 128),        # Hot Neon Pink
        "card_border": (0, 245, 255),         # Cyan Outline
        "badge_bg": (20, 20, 48),
        "scene_colors": [
            (0, 245, 255),   # Cyan Hook
            (255, 0, 128),   # Pink Body
            (189, 0, 255),   # Purple Evidence
            (0, 255, 136),   # Neon Green CTA
        ],
        "motions": [
            "zoompan=z='min(zoom+0.002,1.25)':d={fps_dur}:x='iw/2-(iw/zoom/2)+sin(on/20)*25':y='ih/2-(ih/zoom/2)':s=720x1280:fps=25",
            "zoompan=z='1.12':d={fps_dur}:x='iw/2-(iw/zoom/2)+cos(on/22)*25':s=720x1280:fps=25",
            "zoompan=z='max(1.25-0.002*on,1.0)':d={fps_dur}:x='iw/2-(iw/zoom/2)+sin(on/18)*30':y='ih/2-(ih/zoom/2)':s=720x1280:fps=25",
            "zoompan=z='1.08':d={fps_dur}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=720x1280:fps=25",
        ],
        "single_motion": "zoompan=z='min(zoom+0.002,1.25)':d={total_frames}:x='iw/2-(iw/zoom/2)+sin(on/25)*20':y='ih/2-(ih/zoom/2)':s=720x1280:fps=25",
        "tags": "#ThePulse #Cyberpunk #NeonVibes #TechTrending",
        "swatches": ["#00F5FF", "#FF0080", "#BD00FF", "#00FF88"],
    },
    "tech": {
        "id": "tech",
        "name": "Tech Futuristic",
        "description": "Giao diện kỹ thuật số tối giản, font Consolas monospace và sắc xanh công nghệ",
        "font_family": "consola",
        "title_color": (56, 189, 248),        # Sky Blue 400
        "headline_color": (241, 245, 249),    # Slate 100
        "meta_color": (52, 211, 153),         # Emerald 400
        "bg_gradient_start": (6, 18, 30),     # Dark Tech Teal
        "bg_gradient_end": (10, 28, 48),      # Deep Cobalt
        "banner_bg": (12, 32, 54),            # Tech Slate
        "banner_border": (14, 165, 233),      # Sky Blue 500
        "panel_bg": (10, 26, 44),             # Dark Cyan Panel
        "panel_border": (56, 189, 248),       # Sky Blue 400
        "card_border": (14, 165, 233),        # Tech Outline
        "badge_bg": (14, 38, 64),
        "scene_colors": [
            (14, 165, 233),  # Sky Blue Hook
            (16, 185, 129),  # Emerald Body
            (99, 102, 241),  # Indigo Evidence
            (245, 158, 11),  # Amber CTA
        ],
        "motions": [
            "zoompan=z='min(zoom+0.0018,1.22)':d={fps_dur}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=720x1280:fps=25",
            "zoompan=z='1.08':d={fps_dur}:x='iw/2-(iw/zoom/2)+on*0.5':y='ih/2-(ih/zoom/2)':s=720x1280:fps=25",
            "zoompan=z='max(1.22-0.0018*on,1.02)':d={fps_dur}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=720x1280:fps=25",
            "zoompan=z='1.05':d={fps_dur}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=720x1280:fps=25",
        ],
        "single_motion": "zoompan=z='min(zoom+0.0018,1.22)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=720x1280:fps=25",
        "tags": "#ThePulse #TechNews #AIInnovation #FutureTech",
        "swatches": ["#0EA5E9", "#10B981", "#6366F1", "#38BDF8"],
    },
    "pastel": {
        "id": "pastel",
        "name": "Pastel Soft",
        "description": "Tông màu ngọt ngào, dịu mắt, thân thiện và ấm áp với phong cách thanh thoát",
        "font_family": "segoeui",
        "title_color": (251, 146, 60),        # Peach 400
        "headline_color": (255, 255, 255),    # Pure White
        "meta_color": (147, 197, 253),        # Soft Sky Blue
        "bg_gradient_start": (36, 26, 44),    # Muted Plum
        "bg_gradient_end": (22, 28, 44),      # Twilight Lavender
        "banner_bg": (48, 38, 58),            # Soft Violet Slate
        "banner_border": (244, 114, 182),     # Soft Pink 400
        "panel_bg": (38, 32, 50),             # Soft Charcoal Lavender
        "panel_border": (192, 132, 252),      # Soft Purple 400
        "card_border": (244, 114, 182),       # Pink Outline
        "badge_bg": (52, 42, 64),
        "scene_colors": [
            (244, 114, 182), # Soft Pink Hook
            (192, 132, 252), # Soft Purple Body
            (147, 197, 253), # Soft Blue Evidence
            (251, 146, 60),  # Peach CTA
        ],
        "motions": [
            "zoompan=z='min(zoom+0.001,1.15)':d={fps_dur}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=720x1280:fps=25",
            "zoompan=z='1.06':d={fps_dur}:x='iw/2-(iw/zoom/2)+sin(on/35)*15':y='ih/2-(ih/zoom/2)':s=720x1280:fps=25",
            "zoompan=z='max(1.15-0.001*on,1.0)':d={fps_dur}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=720x1280:fps=25",
            "zoompan=z='1.04':d={fps_dur}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=720x1280:fps=25",
        ],
        "single_motion": "zoompan=z='min(zoom+0.001,1.15)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=720x1280:fps=25",
        "tags": "#ThePulse #PastelAesthetic #SoftLife #ViralTrends",
        "swatches": ["#F472B6", "#C084FC", "#93C5FD", "#FB923C"],
    },
}


class MuseAIClient:
    """Client giao tiếp với Muse AI Video Generation API (czg86389-hub/muse2api & proxy)."""

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None) -> None:
        raw_url = base_url or os.getenv("MUSE_BASE_URL", "http://localhost:8000/v1")
        self.base_url = raw_url.rstrip("/")
        self.api_key = api_key or os.getenv("MUSE_API_KEY", "")

    def is_configured(self) -> bool:
        """Kiểm tra xem Client đã có URL và API Key hợp lệ hay chưa."""
        return bool(self.api_key and self.api_key.strip())

    def create_video_task(
        self,
        prompt: str,
        ref_image_url: Optional[str] = None,
        duration: int = 5,
        aspect_ratio: str = "9:16"
    ) -> str:
        """Gửi yêu cầu tạo video (POST /v1/videos) và nhận task_id."""
        url = f"{self.base_url}/videos"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload: Dict[str, Union[str, int, List[Dict[str, str]]]] = {
            "prompt": prompt,
            "size": aspect_ratio,
            "duration": duration
        }
        if ref_image_url and ref_image_url.strip():
            payload["images"] = [{"url": ref_image_url.strip()}]

        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        if resp.status_code not in (200, 201, 202):
            raise RuntimeError(f"Muse API Error (HTTP {resp.status_code}): {resp.text}")

        data = resp.json()
        task_id = data.get("id") or data.get("task_id")
        if not task_id:
            raise ValueError(f"Muse API không trả về task_id hợp lệ: {data}")
        return str(task_id)

    def poll_task_status(self, task_id: str, timeout_seconds: int = 60, poll_interval: float = 2.0) -> str:
        """Lắng nghe trạng thái của task cho tới khi hoàn tất, trả về URL tải video."""
        url = f"{self.base_url}/videos/{task_id}"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                raise RuntimeError(f"Lỗi kiểm tra task (HTTP {resp.status_code}): {resp.text}")

            data = resp.json()
            status = str(data.get("status", "")).lower()

            if status in ("succeeded", "completed"):
                result = data.get("result") or {}
                video_url = (
                    (result.get("url") if isinstance(result, dict) else None)
                    or data.get("video_url")
                    or (data.get("video", {}).get("url") if isinstance(data.get("video"), dict) else None)
                )
                if not video_url and "data" in data and isinstance(data["data"], list) and data["data"]:
                    video_url = data["data"][0].get("url")

                if not video_url:
                    raise ValueError(f"Không tìm thấy URL video trong phản hồi thành công: {data}")
                return str(video_url)

            if status in ("failed", "error", "cancelled"):
                error_msg = data.get("error") or data.get("message") or "Unknown error"
                raise RuntimeError(f"Muse API sinh video thất bại ({status}): {error_msg}")

            time.sleep(poll_interval)

        raise TimeoutError(f"Quá thời gian chờ ({timeout_seconds}s) khi tạo video qua Muse API")

    def download_video(self, video_url: str) -> str:
        """Tải file video MP4 từ Muse API về lưu trữ cục bộ."""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        uid = hashlib.md5(video_url.encode()).hexdigest()[:8]
        out_file = OUTPUT_DIR / f"muse_{ts}_{uid}.mp4"

        with requests.get(video_url, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(out_file, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

        return str(out_file)

    def generate_video(
        self,
        prompt: str,
        ref_image_url: Optional[str] = None,
        duration: int = 5
    ) -> Dict[str, Union[str, float]]:
        """Quy trình tạo video hoàn chỉnh: Gửi task -> Polling -> Tải MP4."""
        task_id = self.create_video_task(prompt=prompt, ref_image_url=ref_image_url, duration=duration)
        video_url = self.poll_task_status(task_id=task_id)
        local_path = self.download_video(video_url)
        return {
            "status": "success",
            "video_path": local_path,
            "mode": "muse_api",
            "duration": float(duration),
            "resolution": "720x1280",
            "task_id": task_id,
            "message": "Video tạo sinh thành công qua Muse AI REST API"
        }


class SafeFallbackSynthesizer:
    """
    Bộ máy dựng video TikTok 9:16 Studio-Grade:
    - Chế độ đơn phân cảnh siêu tốc (< 1s) khi duration < 10s.
    - Chế độ Montage 4 phân cảnh (15s–25s) kết hợp chuyển động camera điện ảnh,
      giọng đọc AI tiếng Việt, âm hưởng nền BGM và phụ đề động chuẩn TikTok.
    """

    def __init__(self) -> None:
        self.ffmpeg_bin = find_ffmpeg_binary()

    def _download_image(self, url: Optional[str], temp_dir: Path) -> Optional[Path]:
        """Tải ảnh nguồn với timeout bảo vệ."""
        if not url or not url.strip():
            return None
        try:
            r = requests.get(url.strip(), timeout=5)
            if r.status_code == 200 and len(r.content) > 500:
                p = temp_dir / "downloaded_raw.jpg"
                p.write_bytes(r.content)
                return p
        except Exception:
            pass
        return None

    def _generate_card(
        self,
        title: str,
        headline: str,
        color: Tuple[int, int, int],
        ref_image_path: Optional[Path],
        temp_dir: Path,
        scene_num: int = 1,
        theme: str = "editorial"
    ) -> Path:
        """Tạo card đồ họa 720x1280 9:16 độ nét cao: phân tách tuyệt đối vùng hiển thị, ảnh động hóa theo phân cảnh, chống đè chữ."""
        out_p = Path(temp_dir) / f"card_{scene_num}.png"
        theme_key = theme.lower().strip() if isinstance(theme, str) else "editorial"
        theme_cfg = THEME_PRESETS.get(theme_key, THEME_PRESETS["editorial"])
        safe_title = str(title or "").strip()
        safe_headline = str(headline or "").strip()

        img = Image.new("RGB", (720, 1280), theme_cfg["bg_gradient_start"])
        draw = ImageDraw.Draw(img)

        # Typography TrueType theo theme font stack
        font_fam = theme_cfg.get("font_family", "segoeui")
        f_brand = _get_font(25, bold=True, font_family=font_fam)
        f_badge = _get_font(24, bold=True, font_family=font_fam)
        f_headline = _get_font(34, bold=True, font_family=font_fam)
        f_meta = _get_font(22, bold=False, font_family=font_fam)
        f_label = _get_font(18, bold=True, font_family=font_fam)

        # Màu nhấn: ưu tiên color do caller chỉ định nếu khác None
        accent_color = color if color is not None else theme_cfg["title_color"]

        # 1. NỀN TOÀN CẢNH (Ambient Background)
        ref_p = Path(ref_image_path) if ref_image_path else None
        has_ref = bool(ref_p and ref_p.exists())
        ref_img_rgb = None
        if has_ref:
            try:
                with Image.open(ref_p) as ref_img:
                    ref_img_rgb = ref_img.convert("RGB")
                    bg_blur = ref_img_rgb.resize((720, 1280), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(radius=30))
                    img.paste(bg_blur, (0, 0))
                    tint_r, tint_g, tint_b = theme_cfg["bg_gradient_start"]
                    overlay = Image.new("RGBA", (720, 1280), (tint_r, tint_g, tint_b, 195))
                    img.paste(overlay, (0, 0), overlay)
            except Exception:
                ref_img_rgb = None
                has_ref = False

        if not has_ref:
            # Gradient dọc mượt mà theo bảng màu của theme
            c_start = theme_cfg["bg_gradient_start"]
            c_end = theme_cfg["bg_gradient_end"]
            for y in range(1280):
                ratio = y / 1280.0
                r = int(c_start[0] * (1 - ratio) + c_end[0] * ratio)
                g = int(c_start[1] * (1 - ratio) + c_end[1] * ratio)
                b = int(c_start[2] * (1 - ratio) + c_end[2] * ratio)
                draw.line([(0, y), (720, y)], fill=(r, g, b))

        # Khung viền ngoài tổng thể (Outer Card Accent Border)
        card_border_color = theme_cfg.get("card_border", accent_color)
        draw.rounded_rectangle([(16, 16), (704, 1264)], radius=20, outline=card_border_color, width=2)

        # 2. KHUNG TIÊU ĐỀ TOP (Top Brand Banner: Y = 50..130)
        draw.rounded_rectangle([(40, 50), (680, 130)], radius=16, fill=theme_cfg["banner_bg"], outline=accent_color, width=2)
        draw.text((65, 75), f"THE PULSE STUDIO — {safe_title.upper()[:28]}", font=f_brand, fill=accent_color)

        # 3. SÂN KHẤU THỊ GIÁC ĐA DẠNG HÓA THEO PHÂN CẢNH (Visual Stage: Y = 145..665, 640x520)
        stage_w, stage_h = 640, 520
        stage_x, stage_y = 40, 145

        if ref_img_rgb:
            try:
                rw, rh = ref_img_rgb.width, ref_img_rgb.height
                if scene_num == 1:
                    # Phân cảnh 1: Hero Centered Shot (Toàn cảnh nổi bật)
                    scale = max(stage_w / rw, stage_h / rh)
                    nw, nh = int(rw * scale), int(rh * scale)
                    resized = ref_img_rgb.resize((nw, nh), Image.Resampling.LANCZOS)
                    cx, cy = (nw - stage_w) // 2, (nh - stage_h) // 2
                    stage_crop = resized.crop((cx, cy, cx + stage_w, cy + stage_h))
                    img.paste(stage_crop, (stage_x, stage_y))
                    # Badge góc ảnh
                    draw.rounded_rectangle([(stage_x + 15, stage_y + 15), (stage_x + 185, stage_y + 55)], radius=10, fill=(239, 68, 68), outline=(255, 255, 255), width=1)
                    draw.text((stage_x + 28, stage_y + 22), "HOT | TIÊU ĐIỂM", font=f_label, fill=(255, 255, 255))
                elif scene_num == 2:
                    # Phân cảnh 2: Investigative Zoom 1.7x (Cận cảnh góc trái điều tra)
                    zoom = 1.7
                    crop_w = max(40, int(rw / zoom))
                    crop_h = max(40, int(rh / zoom))
                    crop_x = 0
                    crop_y = int(rh * 0.1)
                    cropped_region = ref_img_rgb.crop((crop_x, crop_y, crop_x + crop_w, crop_y + crop_h))
                    stage_crop = cropped_region.resize((stage_w, stage_h), Image.Resampling.LANCZOS)
                    img.paste(stage_crop, (stage_x, stage_y))
                    # Scanlines nhẹ thể hiện phân tích
                    for sy in range(stage_y + 60, stage_y + stage_h - 20, 50):
                        draw.line([(stage_x, sy), (stage_x + stage_w, sy)], fill=(59, 130, 246, 75), width=1)
                    # Badge phân tích
                    draw.rounded_rectangle([(stage_x + 15, stage_y + 15), (stage_x + 250, stage_y + 55)], radius=10, fill=(59, 130, 246), outline=(255, 255, 255), width=1)
                    draw.text((stage_x + 28, stage_y + 22), "PHÂN TÍCH | CHI TIẾT", font=f_label, fill=(255, 255, 255))
                elif scene_num == 3:
                    # Phân cảnh 3: Evidence Zoom 1.7x (Cận cảnh góc phải dữ liệu)
                    zoom = 1.7
                    crop_w = max(40, int(rw / zoom))
                    crop_h = max(40, int(rh / zoom))
                    crop_x = max(0, rw - crop_w)
                    crop_y = int(rh * 0.15)
                    cropped_region = ref_img_rgb.crop((crop_x, crop_y, crop_x + crop_w, crop_y + crop_h))
                    stage_crop = cropped_region.resize((stage_w, stage_h), Image.Resampling.LANCZOS)
                    img.paste(stage_crop, (stage_x, stage_y))
                    # Badge bằng chứng
                    draw.rounded_rectangle([(stage_x + 15, stage_y + 15), (stage_x + 250, stage_y + 55)], radius=10, fill=(168, 85, 247), outline=(255, 255, 255), width=1)
                    draw.text((stage_x + 28, stage_y + 22), "KIỂM CHỨNG | DỮ LIỆU", font=f_label, fill=(255, 255, 255))
                else:
                    # Phân cảnh 4: Community Engagement Hub (Card tranh luận tương tác)
                    blur_stage = ref_img_rgb.resize((stage_w, stage_h), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(14))
                    img.paste(blur_stage, (stage_x, stage_y))
                    # Hộp đối thoại cộng đồng
                    draw.rounded_rectangle([(stage_x + 25, stage_y + 25), (stage_x + stage_w - 25, stage_y + stage_h - 25)], radius=18, fill=(15, 23, 42), outline=(245, 158, 11), width=2)
                    draw.text((stage_x + 45, stage_y + 50), "Ý KIẾN CỦA BẠN LÀ GÌ?", font=_get_font(28, bold=True, font_family=font_fam), fill=(245, 158, 11))
                    draw.text((stage_x + 45, stage_y + 95), "Tham gia tranh luận ngay cùng cộng đồng:", font=_get_font(20, bold=False, font_family=font_fam), fill=(226, 232, 240))
                    # Các chỉ số tương tác xã hội chuẩn typographic
                    social_pills = [
                        ("[ THÍCH ] 48.2K Người đồng tình quan điểm", (239, 68, 68)),
                        ("[ BÌNH LUẬN ] 3.8K Lượt thảo luận", (59, 130, 246)),
                        ("[ CHIA SẺ ] 12.5K Lượt chia sẻ phân tích", (34, 197, 94))
                    ]
                    sy_pill = stage_y + 140
                    for p_txt, p_col in social_pills:
                        draw.rounded_rectangle([(stage_x + 45, sy_pill), (stage_x + stage_w - 45, sy_pill + 40)], radius=10, fill=(30, 41, 59), outline=p_col, width=1)
                        draw.text((stage_x + 65, sy_pill + 9), p_txt, font=f_label, fill=(255, 255, 255))
                        sy_pill += 50
                    # Nút bấm hành động
                    draw.rounded_rectangle([(stage_x + 45, stage_y + 390), (stage_x + stage_w - 45, stage_y + 440)], radius=12, fill=(245, 158, 11), outline=(255, 255, 255), width=1)
                    draw.text((stage_x + 65, stage_y + 404), ">> BÌNH LUẬN NGAY DƯỚI VIDEO <<", font=_get_font(18, bold=True, font_family=font_fam), fill=(15, 23, 42))
            except Exception:
                pass
        else:
            # Procedural Graphics cho trường hợp không có ảnh nguồn
            draw.rounded_rectangle([(stage_x, stage_y), (stage_x + stage_w, stage_y + stage_h)], radius=16, fill=(15, 23, 42), outline=accent_color, width=2)
            if scene_num == 1:
                draw.text((stage_x + 30, stage_y + 35), "HOT | TIÊU ĐIỂM XU HƯỚNG MẠNG", font=f_badge, fill=accent_color)
                for r in (50, 90, 130, 170):
                    draw.ellipse([(stage_x + stage_w//2 - r, stage_y + 260 - r), (stage_x + stage_w//2 + r, stage_y + 260 + r)], outline=accent_color, width=2)
            elif scene_num == 2:
                draw.text((stage_x + 30, stage_y + 35), "PHÂN TÍCH | BÓC TÁCH DỮ LIỆU", font=f_badge, fill=accent_color)
                bar_heights = [120, 200, 260, 170, 230]
                for bi, bh in enumerate(bar_heights):
                    bx = stage_x + 80 + bi * 100
                    draw.rounded_rectangle([(bx, stage_y + 400 - bh), (bx + 55, stage_y + 400)], radius=6, fill=accent_color)
            elif scene_num == 3:
                draw.text((stage_x + 30, stage_y + 35), "KIỂM CHỨNG | DỮ LIỆU THỰC TẾ", font=f_badge, fill=accent_color)
                for line_i in range(5):
                    ly = stage_y + 110 + line_i * 65
                    draw.line([(stage_x + 60, ly), (stage_x + stage_w - 60, ly)], fill=(71, 85, 105), width=2)
            else:
                draw.text((stage_x + 30, stage_y + 35), "TRANH LUẬN | Ý KIẾN CỘNG ĐỒNG", font=f_badge, fill=accent_color)
                draw.rounded_rectangle([(stage_x + 50, stage_y + 150), (stage_x + stage_w - 50, stage_y + 350)], radius=16, fill=(30, 41, 59), outline=(245, 158, 11), width=2)
                draw.text((stage_x + 80, stage_y + 220), "BẠN ĐỒNG Ý HAY PHẢN ĐỐI?", font=_get_font(26, bold=True, font_family=font_fam), fill=(245, 158, 11))

        # Viền khung bảo vệ Visual Stage
        draw.rounded_rectangle([(stage_x, stage_y), (stage_x + stage_w, stage_y + stage_h)], radius=16, outline=accent_color, width=2)

        # 4. KHUNG TỔNG KẾT / ĐIỂM NHẤN (Highlight Panel: Y = 680..885 - Tối đa 2 dòng, TUYỆT ĐỐI KHÔNG TRÀN XUỐNG)
        draw.rounded_rectangle([(40, 680), (680, 885)], radius=18, fill=theme_cfg["panel_bg"], outline=theme_cfg["panel_border"], width=2)
        draw.text((65, 698), f"[{safe_title.upper()[:28]}]", font=f_badge, fill=accent_color)

        clean_hl = re.sub(r"\s+", " ", safe_headline).strip()
        words_hl = clean_hl.split()
        if len(words_hl) > 13:
            short_hl = " ".join(words_hl[:13]) + "..."
        else:
            short_hl = clean_hl

        # Gói tối đa 2 dòng cho khung điểm nhấn
        hl_lines: List[str] = []
        cur_w: List[str] = []
        for w in short_hl.split():
            cur_w.append(w)
            bbox = draw.textbbox((0, 0), " ".join(cur_w), font=f_headline)
            if (bbox[2] - bbox[0]) > 580:
                cur_w.pop()
                if cur_w:
                    hl_lines.append(" ".join(cur_w))
                cur_w = [w]
        if cur_w:
            hl_lines.append(" ".join(cur_w))

        y_hl = 745
        for l in hl_lines[:2]:
            draw.text((65, y_hl), l, font=f_headline, fill=theme_cfg["headline_color"])
            y_hl += 46

        # 5. KHAY PHỤ ĐỀ TRỰC TIẾP CHUYÊN DỤNG (Dedicated Subtitle Tray: Y = 920..1150)
        # Nơi FFmpeg hiển thị ASS subtitles (Alignment: 2, MarginV: 150). PIL KHÔNG vẽ chữ lên khay này!
        draw.rounded_rectangle([(40, 920), (680, 1150)], radius=20, fill=(15, 23, 42), outline=(255, 255, 255), width=1)
        # Nhãn khay phụ đề và hiệu ứng sóng âm thanh
        draw.text((65, 932), "PHỤ ĐỀ TRỰC TIẾP", font=f_label, fill=(148, 163, 184))
        for wave_i, wave_h in enumerate([8, 16, 22, 14, 18, 10]):
            wx = 610 + wave_i * 8
            draw.line([(wx, 946 - wave_h // 2), (wx, 946 + wave_h // 2)], fill=accent_color, width=2)

        # 6. METADATA VÀ TIẾN TRÌNH (Footer: Y = 1175..1215)
        tags_text = theme_cfg.get("tags", "#ThePulse #TikTokTrending #PhanTichXuHuong")
        draw.text((65, 1180), tags_text, font=f_meta, fill=theme_cfg["meta_color"])

        # Chỉ báo phân cảnh (Scene Progress Pips)
        for dot_i in range(1, 5):
            dot_x = 550 + (dot_i - 1) * 28
            dot_color = accent_color if dot_i == scene_num else theme_cfg["meta_color"]
            draw.ellipse([(dot_x, 1188), (dot_x + 12, 1200)], fill=dot_color)

        img.save(out_p, "PNG")
        return out_p

    def _generate_background_image(
        self,
        ref_image_url: Optional[str],
        temp_dir: Path,
        title: str = "TIN TỨC XU HƯỚNG TIKTOK",
        theme: str = "editorial"
    ) -> Path:
        """Chuẩn bị ảnh nền dọc 9:16 (720x1280) cho chế độ đơn phân cảnh theo theme."""
        # ponytail: delegate to unified _generate_card to avoid code duplication
        local_ref = self._download_image(ref_image_url, temp_dir)
        theme_cfg = THEME_PRESETS.get(theme.lower(), THEME_PRESETS["editorial"])
        return self._generate_card("TIN NÓNG MẠNG XÃ HỘI", title, theme_cfg["title_color"], local_ref, temp_dir, 0, theme=theme)

    def _generate_scene_card(
        self,
        scene_num: int,
        title: str,
        headline: str,
        color: Tuple[int, int, int],
        ref_image_path: Optional[Path],
        temp_dir: Path,
        theme: str = "editorial"
    ) -> Path:
        """Tạo Card hình ảnh 720x1280 chuẩn studio cho từng phân cảnh trong Storyboard theo theme."""
        return self._generate_card(title, headline, color, ref_image_path, temp_dir, scene_num, theme=theme)

    def _generate_ass_subtitle(
        self,
        script_data: ScriptDict,
        total_duration: float,
        temp_dir: Path
    ) -> Path:
        """Tạo file phụ đề ASS chuẩn TikTok cho chế độ đơn phân cảnh."""
        hook = str(script_data.get("hook", "")).strip() or "SỰ THẬT CHẤN ĐỘNG CẦN BÓC MẼ!"
        body = str(script_data.get("body", "")).strip() or "Cụ thể vấn đề đang diễn biến phức tạp..."
        cta = str(script_data.get("cta", "")).strip() or "Bạn nghĩ sao về điều này? Hãy để lại ý kiến!"
        t_hook_end = min(3.0, max(0.2, total_duration * 0.33))
        t_body_end = min(total_duration * 0.75, max(t_hook_end + 0.1, total_duration - 2.5))
        if t_body_end <= t_hook_end:
            t_body_end = t_hook_end + max(0.1, (total_duration - t_hook_end) * 0.5)
        if t_body_end >= total_duration:
            t_body_end = max(t_hook_end + 0.05, total_duration - 0.05)

        # ponytail: reuse _generate_multiscene_ass for DRY subtitle generation
        return self._generate_multiscene_ass([
            (0.0, t_hook_end, "HookStyle", r"{\an2\b1}" + hook.upper()),
            (t_hook_end, t_body_end, "BodyStyle", r"{\an2}" + body),
            (t_body_end, total_duration, "CTAStyle", r"{\an2\b1}" + cta)
        ], temp_dir)

    def _generate_multiscene_ass(
        self,
        scene_timings: List[Tuple[float, float, str, str]],
        temp_dir: Path
    ) -> Path:
        """Tạo file phụ đề ASS đồng bộ chính xác với 4 phân cảnh, căn chỉnh khay phụ đề chuyên dụng (Alignment: 2, MarginV: 150)."""
        ass_path = temp_dir / "multiscene_captions.ass"

        def fmt_time(sec: float) -> str:
            m = int(sec // 60)
            s = int(sec % 60)
            cs = int((sec - int(sec)) * 100)
            return f"0:{m:02d}:{s:02d}.{cs:02d}"

        styles_header = """[Script Info]
Title: TikTok Multi-Scene Subtitles
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: HookStyle,Arial,38,&H0000FFFF,&H00000000,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,2,2,60,60,130,1
Style: BodyStyle,Arial,34,&H00FFFFFF,&H00000000,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,2,2,60,60,130,1
Style: EvidStyle,Arial,34,&H00E0E0FF,&H00000000,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,2,2,60,60,130,1
Style: CTAStyle,Arial,36,&H0000E5FF,&H00000000,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,2,2,60,60,130,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        events = []
        for start_t, end_t, style_name, text in scene_timings:
            st = max(0.0, float(start_t))
            et = max(st + 0.05, float(end_t))
            clean = text.replace("\n", " ").strip()
            events.append(
                f"Dialogue: 0,{fmt_time(st)},{fmt_time(et)},{style_name},,0,0,0,,{clean}"
            )

        with open(ass_path, "w", encoding="utf-8") as f:
            f.write(styles_header + "\n".join(events) + "\n")

        return ass_path

    def synthesize(
        self,
        script_data: ScriptDict,
        ref_image_url: Optional[str] = None,
        duration: int = 20,
        voice: str = "vi-VN-HoaiMyNeural",
        theme: str = "editorial"
    ) -> Dict[str, Union[str, float]]:
        """
        Quy trình dựng video 9:16 thông minh:
        - Nếu duration < 10: Dựng nhanh đơn phân cảnh (< 1s) tương thích tuyệt đối test suites.
        - Nếu duration >= 10: Dựng chuỗi Montage 4 phân cảnh điện ảnh kèm Voiceover tiếng Việt và BGM.
        """
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_file = OUTPUT_DIR / f"pulse_{ts}_{duration}s.mp4"
        theme_key = theme.lower().strip() if isinstance(theme, str) else "editorial"
        theme_cfg = THEME_PRESETS.get(theme_key, THEME_PRESETS["editorial"])

        # ==============================================================================
        # 1. NHÁNH ĐƠN PHÂN CẢNH (Fast Single-Scene cho duration < 10s)
        # ==============================================================================
        if duration < 10:
            with tempfile.TemporaryDirectory() as tmp_dir_str:
                tmp_dir = Path(tmp_dir_str)
                title = str(script_data.get("hook", "TIN NÓNG MẠNG XÃ HỘI"))

                bg_img = self._generate_background_image(ref_image_url=ref_image_url, temp_dir=tmp_dir, title=title, theme=theme_key)
                ass_file = self._generate_ass_subtitle(script_data=script_data, total_duration=float(duration), temp_dir=tmp_dir)
                ass_path_escaped = str(ass_file).replace("\\", "/").replace(":", "\\:")

                total_frames = int(duration * 25)
                single_motion = theme_cfg.get(
                    "single_motion",
                    "zoompan=z='min(zoom+0.0015,1.25)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=720x1280:fps=25"
                ).format(total_frames=total_frames)

                cmd = [
                    self.ffmpeg_bin,
                    "-y",
                    "-loop", "1",
                    "-i", str(bg_img),
                    "-f", "lavfi",
                    "-i", "anullsrc=r=44100:cl=stereo",
                    "-filter_complex",
                    f"[0:v]{single_motion},subtitles='{ass_path_escaped}'[v]",
                    "-map", "[v]",
                    "-map", "1:a",
                    "-c:v", "libx264",
                    "-preset", "ultrafast",
                    "-tune", "stillimage",
                    "-pix_fmt", "yuv420p",
                    "-c:a", "aac",
                    "-b:a", "128k",
                    "-t", str(duration),
                    "-movflags", "+faststart",
                    str(out_file)
                ]

                try:
                    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=25)
                    if proc.returncode != 0:
                        cmd_simple = [
                            self.ffmpeg_bin,
                            "-y",
                            "-loop", "1",
                            "-i", str(bg_img),
                            "-f", "lavfi",
                            "-i", "anullsrc=r=44100:cl=stereo",
                            "-filter_complex",
                            f"[0:v]{single_motion}[v]",
                            "-map", "[v]",
                            "-map", "1:a",
                            "-c:v", "libx264",
                            "-preset", "ultrafast",
                            "-pix_fmt", "yuv420p",
                            "-c:a", "aac",
                            "-t", str(duration),
                            str(out_file)
                        ]
                        subprocess.run(cmd_simple, check=True, timeout=20)
                except Exception as e:
                    raise RuntimeError(f"Lỗi thực thi FFmpeg: {e}")

            if not out_file.exists() or out_file.stat().st_size == 0:
                raise RuntimeError(f"FFmpeg không xuất được file video: {out_file}")

            return {
                "status": "success",
                "video_path": str(out_file),
                "mode": "fallback",
                "duration": float(duration),
                "resolution": "720x1280",
                "message": "Video tạo thành công qua Safe Fallback Engine (Fast Single-Scene)"
            }

        # ==============================================================================
        # 2. NHÁNH STUDIO MULTI-SCENE MONTAGE (15s - 25s)
        # ==============================================================================
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)

            # 2.1 Chuẩn bị các phân cảnh
            raw_scenes = script_data.get("scenes")
            if not isinstance(raw_scenes, list) or len(raw_scenes) < 4:
                hook = str(script_data.get("hook", "CẢNH BÁO XU HƯỚNG MỚI?"))
                body = str(script_data.get("body", "Diễn biến thực tế đang gây chú ý..."))
                cta = str(script_data.get("cta", "Bạn nghĩ sao? Hãy bình luận!"))
                raw_scenes = [
                    {"scene_num": 1, "title": "Hook Giật Gân", "voice_text": hook, "camera_motion": "slow dolly push-in"},
                    {"scene_num": 2, "title": "Bóc Tách Sự Thật", "voice_text": body[:120], "camera_motion": "pan left to right"},
                    {"scene_num": 3, "title": "Bằng Chứng & Tác Động", "voice_text": body[120:] or "Tình tiết bất thường tiếp tục được làm sáng tỏ.", "camera_motion": "slow tilt down"},
                    {"scene_num": 4, "title": "Kêu Gọi Tranh Luận", "voice_text": cta, "camera_motion": "center focal hold"}
                ]

            # Phân bổ thời lượng cho 4 scenes
            # Tỉ lệ chuẩn TikTok: Hook ~20%, Body ~30%, Evidence ~25%, CTA ~25%
            dur_1 = max(3, int(duration * 0.20))
            dur_2 = max(4, int(duration * 0.30))
            dur_3 = max(3, int(duration * 0.25))
            dur_4 = max(3, duration - (dur_1 + dur_2 + dur_3))
            scene_durs = [dur_1, dur_2, dur_3, dur_4]

            # Tải ảnh nguồn nếu có
            ref_local_img: Optional[Path] = None
            if ref_image_url and ref_image_url.strip():
                try:
                    r_img = requests.get(ref_image_url.strip(), timeout=6)
                    if r_img.status_code == 200:
                        ref_local_img = tmp_dir / "ref_image_source.jpg"
                        with open(ref_local_img, "wb") as f:
                            f.write(r_img.content)
                except Exception:
                    ref_local_img = None

            # Màu nhấn cho từng phân cảnh theo theme
            scene_colors = theme_cfg.get("scene_colors", [
                (239, 68, 68),   # Đỏ Hook
                (59, 130, 246),  # Xanh Body
                (168, 85, 247),  # Tím Evidence
                (245, 158, 11)   # Vàng Cam CTA
            ])

            # 2.2 Sinh Card hình ảnh và Render từng Clip phân cảnh
            clip_paths: List[Path] = []
            motions = theme_cfg.get("motions", [
                "zoompan=z='min(zoom+0.002,1.25)':d={fps_dur}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=720x1280:fps=25",
                "zoompan=z='1.1':d={fps_dur}:x='iw/2-(iw/zoom/2)+sin(on/25)*30':y='ih/2-(ih/zoom/2)':s=720x1280:fps=25",
                "zoompan=z='max(1.25-0.002*on,1.0)':d={fps_dur}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=720x1280:fps=25",
                "zoompan=z='1.05':d={fps_dur}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=720x1280:fps=25"
            ])

            scene_timings: List[Tuple[float, float, str, str]] = []
            current_time = 0.0

            style_names = [
                r"{\an2\b1}",
                r"{\an2}",
                r"{\an2}",
                r"{\an2\b1}"
            ]
            style_keys = ["HookStyle", "BodyStyle", "EvidStyle", "CTAStyle"]

            for i in range(4):
                sc = raw_scenes[i]
                sc_title = sc.get("title") or f"Phân cảnh {i+1}"
                sc_text = sc.get("voice_text") or ""
                sc_dur = scene_durs[i]

                # Lưu timing cho phụ đề (Tự động chia nhỏ cue phụ đề nhịp nhanh TikTok nếu văn bản dài)
                words_sc = sc_text.split()
                if sc_dur >= 4.0 and len(words_sc) > 13:
                    mid = len(words_sc) // 2
                    c1 = " ".join(words_sc[:mid])
                    c2 = " ".join(words_sc[mid:])
                    dur1 = round(sc_dur / 2.0, 2)
                    scene_timings.append((
                        current_time,
                        current_time + dur1,
                        style_keys[i],
                        f"{style_names[i]}{c1}"
                    ))
                    scene_timings.append((
                        current_time + dur1,
                        current_time + sc_dur,
                        style_keys[i],
                        f"{style_names[i]}{c2}"
                    ))
                else:
                    scene_timings.append((
                        current_time,
                        current_time + sc_dur,
                        style_keys[i],
                        f"{style_names[i]}{sc_text}"
                    ))
                current_time += sc_dur

                card_path = self._generate_scene_card(
                    scene_num=i + 1,
                    title=sc_title,
                    headline=sc_text,
                    color=scene_colors[i],
                    ref_image_path=ref_local_img,
                    temp_dir=tmp_dir,
                    theme=theme_key
                )

                clip_p = tmp_dir / f"clip_scene_{i+1}.mp4"
                fps_dur = sc_dur * 25
                vf = motions[i].format(fps_dur=fps_dur)

                cmd_clip = [
                    self.ffmpeg_bin, "-y",
                    "-loop", "1", "-i", str(card_path),
                    "-vf", vf,
                    "-t", str(sc_dur),
                    "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                    str(clip_p)
                ]
                subprocess.run(cmd_clip, check=True, capture_output=True, timeout=20)
                clip_paths.append(clip_p)

            # 2.3 Ghép nối chuỗi clips (FFmpeg Concat Demuxer)
            concat_list = tmp_dir / "concat_list.txt"
            with open(concat_list, "w", encoding="utf-8") as f:
                for cp in clip_paths:
                    f.write(f"file '{cp.resolve().as_posix()}'\n")

            video_merged = tmp_dir / "video_merged.mp4"
            cmd_concat = [
                self.ffmpeg_bin, "-y",
                "-f", "concat", "-safe", "0", "-i", str(concat_list),
                "-c", "copy",
                str(video_merged)
            ]
            subprocess.run(cmd_concat, check=True, capture_output=True, timeout=20)

            # 2.4 Sinh Voiceover tiếng Việt (edge-tts / Windows SAPI)
            voice_out = tmp_dir / "voiceover.mp3"
            full_voice_text = " ".join([sc.get("voice_text") or "" for sc in raw_scenes])
            has_voice = synthesize_voiceover(text=full_voice_text, out_path=voice_out, voice=voice)

            # 2.5 Sinh phụ đề ASS
            ass_path = self._generate_multiscene_ass(scene_timings, tmp_dir)
            ass_path_escaped = str(ass_path).replace("\\", "/").replace(":", "\\:")

            # 2.6 Mux hoàn tất: Video + Subtitles + Voiceover + Dynamic Ducking BGM
            if has_voice and voice_out.exists():
                audio_inputs = [
                    "-i", str(voice_out),
                    "-f", "lavfi", "-i", "anoisesrc=c=pink:r=44100:a=0.012,lowpass=f=200",
                    "-f", "lavfi", "-i", "sine=f=50:r=44100"
                ]
                filter_complex = (
                    f"[0:v]subtitles='{ass_path_escaped}'[v];"
                    "[1:a]aformat=sample_rates=44100:channel_layouts=stereo,volume=1.5[vce_raw];"
                    "[vce_raw]asplit=2[vce_main][vce_sc];"
                    "[vce_main]apad[vce_pad];"
                    "[2:a][3:a]amix=inputs=2:duration=first,volume=0.35,aformat=sample_rates=44100:channel_layouts=stereo[bgm_raw];"
                    "[bgm_raw][vce_sc]sidechaincompress=threshold=0.08:ratio=4:attack=20:release=250[ducked_bgm];"
                    "[vce_pad][ducked_bgm]amix=inputs=2:duration=first:dropout_transition=0:weights=1 1[a]"
                )
                map_args = ["-map", "[v]", "-map", "[a]"]
            else:
                # Nếu không có giọng đọc, tạo âm hưởng BGM điện ảnh đơn thuần
                audio_inputs = [
                    "-f", "lavfi", "-i", "anoisesrc=c=pink:r=44100:a=0.02,lowpass=f=220",
                    "-f", "lavfi", "-i", "sine=f=55:r=44100"
                ]
                filter_complex = (
                    f"[0:v]subtitles='{ass_path_escaped}'[v];"
                    "[1:a][2:a]amix=inputs=2:duration=first:dropout_transition=0:weights=1 1,volume=0.35,aformat=sample_rates=44100:channel_layouts=stereo[a]"
                )
                map_args = ["-map", "[v]", "-map", "[a]"]

            final_cmd = [
                self.ffmpeg_bin, "-y",
                "-i", str(video_merged),
                *audio_inputs,
                "-filter_complex", filter_complex,
                *map_args,
                "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "128k",
                "-t", str(duration),
                "-movflags", "+faststart",
                str(out_file)
            ]

            try:
                proc = subprocess.run(final_cmd, capture_output=True, text=True, timeout=30)
                if proc.returncode != 0:
                    logger.warning("Bộ lọc phụ đề gặp lỗi, thử render không phụ đề: %s", proc.stderr[:150])
                    # Fallback bỏ subtitles nếu máy thiếu libass
                    if has_voice and voice_out.exists():
                        simple_filter = (
                            "[1:a]aformat=sample_rates=44100:channel_layouts=stereo,volume=1.5[vce_raw];"
                            "[vce_raw]asplit=2[vce_main][vce_sc];"
                            "[vce_main]apad[vce_pad];"
                            "[2:a][3:a]amix=inputs=2:duration=first,volume=0.35,aformat=sample_rates=44100:channel_layouts=stereo[bgm_raw];"
                            "[bgm_raw][vce_sc]sidechaincompress=threshold=0.08:ratio=4:attack=20:release=250[ducked_bgm];"
                            "[vce_pad][ducked_bgm]amix=inputs=2:duration=first:dropout_transition=0:weights=1 1[a]"
                        )
                        simple_map = ["-map", "0:v", "-map", "[a]"]
                    else:
                        simple_filter = (
                            "[1:a][2:a]amix=inputs=2:duration=first:dropout_transition=0:weights=1 1,volume=0.35,aformat=sample_rates=44100:channel_layouts=stereo[a]"
                        )
                        simple_map = ["-map", "0:v", "-map", "[a]"]

                    cmd_no_sub = [
                        self.ffmpeg_bin, "-y",
                        "-i", str(video_merged),
                        *audio_inputs,
                        "-filter_complex", simple_filter,
                        *simple_map,
                        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "128k",
                        "-t", str(duration),
                        str(out_file)
                    ]
                    subprocess.run(cmd_no_sub, check=True, timeout=25)
            except Exception as e:
                raise RuntimeError(f"Lỗi khi hoàn tất montage: {e}")

        if not out_file.exists() or out_file.stat().st_size == 0:
            raise RuntimeError(f"FFmpeg không xuất được file video: {out_file}")

        return {
            "status": "success",
            "video_path": str(out_file),
            "mode": "fallback",
            "duration": float(duration),
            "resolution": "720x1280",
            "message": "Video tạo thành công qua Studio Multi-Scene Synthesizer (4 Phân cảnh + Voiceover + BGM + Subtitles)"
        }


def generate_tiktok_video(
    visual_prompt: str,
    reference_image_url: Optional[str] = None,
    script_data: Optional[ScriptDict] = None,
    mode: str = "auto",
    duration: int = 20,
    voice: str = "vi-VN-HoaiMyNeural",
    theme: str = "editorial"
) -> Dict[str, Union[str, float]]:
    """
    Entrypoint điều phối tạo video TikTok dọc 9:16 (Façade chính cho giao diện Streamlit).
    mode:
      - 'auto': Thử gọi Muse AI trước; nếu chưa cấu hình hoặc gặp lỗi thì tự động chuyển sang Safe Fallback.
      - 'muse_api': Ép buộc gọi qua Muse AI REST API.
      - 'fallback': Ép buộc chạy Studio Multi-Scene Synthesizer nội bộ.
    """
    script_dict = script_data or {
        "hook": "SỰ THẬT VỀ TREND NÓNG NÀY?",
        "body": visual_prompt[:150],
        "cta": "Bạn nghĩ sao? Hãy để lại ý kiến bên dưới!"
    }

    client = MuseAIClient()
    fallback_engine = SafeFallbackSynthesizer()

    # Chế độ ép buộc Fallback
    if mode == "fallback":
        return fallback_engine.synthesize(
            script_data=script_dict,
            ref_image_url=reference_image_url,
            duration=duration,
            voice=voice,
            theme=theme
        )

    # Chế độ ép buộc Muse AI API
    if mode == "muse_api":
        if not client.is_configured():
            raise RuntimeError("MUSE_API_KEY chưa được cấu hình trong biến môi trường!")
        return client.generate_video(prompt=visual_prompt, ref_image_url=reference_image_url, duration=duration)

    # Chế độ Auto (Tự động thích ứng)
    if client.is_configured():
        try:
            logger.info("Đang thử tạo video qua Muse AI REST API...")
            return client.generate_video(prompt=visual_prompt, ref_image_url=reference_image_url, duration=duration)
        except Exception as e:
            logger.warning(f"Muse AI API gặp sự cố: {e}. Kích hoạt Studio Synthesizer ngay lập tức!")

    # Fallback an toàn mặc định
    return fallback_engine.synthesize(
        script_data=script_dict,
        ref_image_url=reference_image_url,
        duration=duration,
        voice=voice,
        theme=theme
    )
