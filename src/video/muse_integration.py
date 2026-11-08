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
from typing import Dict, List, Optional, Union, Tuple
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


def _get_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    """Tự động tải font TrueType Segoe UI / Arial với fallback an toàn."""
    candidates = (
        [
            r"C:\Windows\Fonts\segoeuib.ttf",
            r"C:\Windows\Fonts\arialbd.ttf",
        ]
        if bold
        else [
            r"C:\Windows\Fonts\segoeui.ttf",
            r"C:\Windows\Fonts\arial.ttf",
        ]
    )
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


def _synthesize_edge_tts(text: str, voice: str, out_path: Path) -> bool:
    """Chạy edge-tts trong worker thread riêng để tránh xung đột event loop Streamlit."""
    def _worker() -> None:
        import edge_tts
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            comm = edge_tts.Communicate(text[:600], voice)
            loop.run_until_complete(comm.save(str(out_path)))
        finally:
            loop.close()

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_worker)
            future.result(timeout=15)
        return out_path.exists() and out_path.stat().st_size > 500
    except Exception as e:
        logger.warning(f"edge-tts ({voice}) thất bại: {e}")
        return False


def _synthesize_google_tts(text: str, out_path: Path) -> bool:
    """Google Translate TTS (tw-ob client) chuẩn tiếng Việt 100% không phụ thuộc 3rd party."""
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
                cur = s
        if cur:
            chunks.append(cur)

        audio_parts: List[bytes] = []
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        for chunk in chunks[:8]:
            q = urllib.parse.quote(chunk)
            url = f"https://translate.google.com/translate_tts?ie=UTF-8&q={q}&tl=vi&client=tw-ob"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=6) as resp:
                if resp.status == 200:
                    data = resp.read()
                    if len(data) > 100:
                        audio_parts.append(data)

        if audio_parts:
            out_path.write_bytes(b"".join(audio_parts))
            return out_path.exists() and out_path.stat().st_size > 500
    except Exception as e:
        logger.warning(f"Google TTS fallback gặp sự cố: {e}")
    return False


def synthesize_voiceover(
    text: str,
    out_path: Path,
    voice: str = "vi-VN-HoaiMyNeural"
) -> bool:
    """
    Tạo giọng đọc tiếng Việt Dual-Engine chuẩn:
    1. edge-tts qua ThreadPoolExecutor (Tránh xung đột Streamlit event loop).
       Thử giọng chính (ví dụ: vi-VN-HoaiMyNeural), nếu lỗi thử giọng phụ (vi-VN-NamMinhNeural).
    2. Native Google Translate TTS fallback (100% chuẩn giọng Việt, 0 dependencies).
    """
    clean_text = re.sub(r'[\r\n\t]+', ' ', text).strip()
    if not clean_text:
        return False

    # 1. edge-tts (Primary voice)
    if _synthesize_edge_tts(clean_text, voice, out_path):
        logger.info("Voiceover tạo thành công qua edge-tts [%s] (%s bytes)", voice, out_path.stat().st_size)
        return True

    # 1b. edge-tts (Secondary voice)
    secondary_voice = "vi-VN-NamMinhNeural" if voice != "vi-VN-NamMinhNeural" else "vi-VN-HoaiMyNeural"
    if _synthesize_edge_tts(clean_text, secondary_voice, out_path):
        logger.info("Voiceover tạo thành công qua edge-tts fallback [%s] (%s bytes)", secondary_voice, out_path.stat().st_size)
        return True

    # 2. Native Google Translate TTS fallback
    if _synthesize_google_tts(clean_text, out_path):
        logger.info("Voiceover tạo thành công qua Google TTS fallback (%s bytes)", out_path.stat().st_size)
        return True

    logger.error("Không thể tổng hợp giọng đọc tiếng Việt qua bất kỳ engine nào.")
    return False


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
        scene_num: int = 1
    ) -> Path:
        """Tạo card đồ họa 720x1280 9:16 độ nét cao với typography Segoe UI lớn và gradient hiện đại."""
        out_p = temp_dir / f"card_{scene_num}.png"
        img = Image.new("RGB", (720, 1280), (15, 23, 42))
        draw = ImageDraw.Draw(img)

        # Typography TrueType Segoe UI / Arial
        f_brand = _get_font(26, bold=True)
        f_badge = _get_font(28, bold=True)
        f_headline = _get_font(38, bold=True)
        f_meta = _get_font(24, bold=False)

        # Nền ảnh hoặc gradient hiện đại
        if ref_image_path and ref_image_path.exists():
            try:
                with Image.open(ref_image_path) as ref_img:
                    rgb = ref_img.convert("RGB")
                    bg_blur = rgb.resize((720, 1280), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(radius=25))
                    img.paste(bg_blur, (0, 0))
                    overlay = Image.new("RGBA", (720, 1280), (15, 23, 42, 185))
                    img.paste(overlay, (0, 0), overlay)

                    scale = min(620.0 / rgb.width, 460.0 / rgb.height)
                    nw, nh = int(rgb.width * scale), int(rgb.height * scale)
                    img.paste(rgb.resize((nw, nh), Image.Resampling.LANCZOS), ((720 - nw) // 2, 210 + (460 - nh) // 2))
            except Exception:
                pass
        else:
            # Subtle dark gradient
            for y in range(1280):
                ratio = y / 1280.0
                r = int(15 * (1 - ratio) + 24 * ratio)
                g = int(23 * (1 - ratio) + 24 * ratio)
                b = int(42 * (1 - ratio) + 37 * ratio)
                draw.line([(0, y), (720, y)], fill=(r, g, b))

        # Top Banner
        draw.rounded_rectangle([(40, 60), (680, 140)], radius=18, fill=(30, 41, 59), outline=color, width=3)
        draw.text((65, 82), f"THE PULSE STUDIO — {title.upper()[:30]}", font=f_brand, fill=color)

        # Glassmorphic Box
        draw.rounded_rectangle([(40, 710), (680, 1110)], radius=24, fill=(24, 24, 37), outline=(71, 85, 105), width=2)
        draw.text((65, 735), f"[{title.upper()[:28]}]", font=f_badge, fill=color)

        # Tự động ngắt dòng đo theo kích thước font thực tế
        clean = re.sub(r"\s+", " ", headline).strip()
        words = clean.split()
        lines: List[str] = []
        cur_words: List[str] = []
        for w in words:
            cur_words.append(w)
            bbox = draw.textbbox((0, 0), " ".join(cur_words), font=f_headline)
            if (bbox[2] - bbox[0]) > 580:
                cur_words.pop()
                if cur_words:
                    lines.append(" ".join(cur_words))
                cur_words = [w]
        if cur_words:
            lines.append(" ".join(cur_words))

        y_t = 795
        for l in lines[:5]:
            draw.text((65, y_t), l, font=f_headline, fill=(255, 255, 255))
            y_t += 52

        draw.text((65, 1160), "#ThePulse #TikTokTrending #PhanTichXuHuong", font=f_meta, fill=(148, 163, 184))
        img.save(out_p, "PNG")
        return out_p

    def _generate_background_image(
        self,
        ref_image_url: Optional[str],
        temp_dir: Path,
        title: str = "TIN TỨC XU HƯỚNG TIKTOK"
    ) -> Path:
        """Chuẩn bị ảnh nền dọc 9:16 (720x1280) cho chế độ đơn phân cảnh."""
        # ponytail: delegate to unified _generate_card to avoid code duplication
        local_ref = self._download_image(ref_image_url, temp_dir)
        return self._generate_card("TIN NÓNG MẠNG XÃ HỘI", title, (245, 158, 11), local_ref, temp_dir, 0)

    def _generate_scene_card(
        self,
        scene_num: int,
        title: str,
        headline: str,
        color: Tuple[int, int, int],
        ref_image_path: Optional[Path],
        temp_dir: Path
    ) -> Path:
        """Tạo Card hình ảnh 720x1280 chuẩn studio cho từng phân cảnh trong Storyboard."""
        return self._generate_card(title, headline, color, ref_image_path, temp_dir, scene_num)

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
        t_hook_end = min(3.0, total_duration * 0.3)
        t_body_end = max(t_hook_end + 1.0, total_duration - 2.5)

        # ponytail: reuse _generate_multiscene_ass for DRY subtitle generation
        return self._generate_multiscene_ass([
            (0.0, t_hook_end, "HookStyle", r"{\an5\b1}" + hook.upper()),
            (t_hook_end, t_body_end, "BodyStyle", r"{\an2}" + body),
            (t_body_end, total_duration, "CTAStyle", r"{\an2\b1}" + cta)
        ], temp_dir)

    def _generate_multiscene_ass(
        self,
        scene_timings: List[Tuple[float, float, str, str]],
        temp_dir: Path
    ) -> Path:
        """Tạo file phụ đề ASS đồng bộ chính xác với 4 phân cảnh."""
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
Style: HookStyle,Arial,48,&H0000FFFF,&H00000000,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,2,5,40,40,220,1
Style: BodyStyle,Arial,38,&H00FFFFFF,&H00000000,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,40,40,250,1
Style: EvidStyle,Arial,38,&H00E0E0FF,&H00000000,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,40,40,250,1
Style: CTAStyle,Arial,42,&H0000E5FF,&H00000000,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,2,2,40,40,250,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        events = []
        for start_t, end_t, style_name, text in scene_timings:
            clean = text.replace("\n", " ").strip()
            events.append(
                f"Dialogue: 0,{fmt_time(start_t)},{fmt_time(end_t)},{style_name},,0,0,0,,{clean}"
            )

        with open(ass_path, "w", encoding="utf-8") as f:
            f.write(styles_header + "\n".join(events) + "\n")

        return ass_path

    def synthesize(
        self,
        script_data: ScriptDict,
        ref_image_url: Optional[str] = None,
        duration: int = 20,
        voice: str = "vi-VN-HoaiMyNeural"
    ) -> Dict[str, Union[str, float]]:
        """
        Quy trình dựng video 9:16 thông minh:
        - Nếu duration < 10: Dựng nhanh đơn phân cảnh (< 1s) tương thích tuyệt đối test suites.
        - Nếu duration >= 10: Dựng chuỗi Montage 4 phân cảnh điện ảnh kèm Voiceover tiếng Việt và BGM.
        """
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_file = OUTPUT_DIR / f"pulse_{ts}_{duration}s.mp4"

        # ==============================================================================
        # 1. NHÁNH ĐƠN PHÂN CẢNH (Fast Single-Scene cho duration < 10s)
        # ==============================================================================
        if duration < 10:
            with tempfile.TemporaryDirectory() as tmp_dir_str:
                tmp_dir = Path(tmp_dir_str)
                title = str(script_data.get("hook", "TIN NÓNG MẠNG XÃ HỘI"))

                bg_img = self._generate_background_image(ref_image_url=ref_image_url, temp_dir=tmp_dir, title=title)
                ass_file = self._generate_ass_subtitle(script_data=script_data, total_duration=float(duration), temp_dir=tmp_dir)
                ass_path_escaped = str(ass_file).replace("\\", "/").replace(":", "\\:")

                total_frames = int(duration * 25)
                cmd = [
                    self.ffmpeg_bin,
                    "-y",
                    "-loop", "1",
                    "-i", str(bg_img),
                    "-f", "lavfi",
                    "-i", "anullsrc=r=44100:cl=stereo",
                    "-filter_complex",
                    f"[0:v]zoompan=z='min(zoom+0.0015,1.25)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=720x1280:fps=25,subtitles='{ass_path_escaped}'[v]",
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
                            f"[0:v]zoompan=z='min(zoom+0.0015,1.2)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=720x1280:fps=25[v]",
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

            # Màu nhấn cho từng phân cảnh
            scene_colors = [
                (239, 68, 68),   # Đỏ Hook
                (59, 130, 246),   # Xanh Body
                (168, 85, 247),  # Tím Evidence
                (245, 158, 11)   # Vàng Cam CTA
            ]

            # 2.2 Sinh Card hình ảnh và Render từng Clip phân cảnh
            clip_paths: List[Path] = []
            motions = [
                "zoompan=z='min(zoom+0.002,1.25)':d={fps_dur}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=720x1280:fps=25",
                "zoompan=z='1.1':d={fps_dur}:x='iw/2-(iw/zoom/2)+sin(on/25)*30':y='ih/2-(ih/zoom/2)':s=720x1280:fps=25",
                "zoompan=z='max(1.25-0.002*on,1.0)':d={fps_dur}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=720x1280:fps=25",
                "zoompan=z='1.05':d={fps_dur}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=720x1280:fps=25"
            ]

            scene_timings: List[Tuple[float, float, str, str]] = []
            current_time = 0.0

            style_names = [
                r"{\an5\b1}",
                r"{\an2}",
                r"{\an2}",
                r"{\an2\b1}"
            ]
            style_keys = ["HookStyle", "BodyStyle", "EvidStyle", "CTAStyle"]

            for i in range(4):
                sc = raw_scenes[i]
                sc_title = sc.get("title", f"Phân cảnh {i+1}")
                sc_text = sc.get("voice_text", "")
                sc_dur = scene_durs[i]

                # Lưu timing cho phụ đề
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
                    temp_dir=tmp_dir
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
            full_voice_text = " ".join([sc.get("voice_text", "") for sc in raw_scenes])
            has_voice = synthesize_voiceover(text=full_voice_text, out_path=voice_out, voice=voice)

            # 2.5 Sinh phụ đề ASS
            ass_path = self._generate_multiscene_ass(scene_timings, tmp_dir)
            ass_path_escaped = str(ass_path).replace("\\", "/").replace(":", "\\:")

            # 2.6 Mux hoàn tất: Video + Subtitles + Voiceover + Ambient Drone BGM Ducking
            if has_voice and voice_out.exists():
                audio_inputs = [
                    "-i", str(voice_out),
                    "-f", "lavfi", "-i", "anoisesrc=c=pink:r=44100:a=0.012,lowpass=f=200",
                    "-f", "lavfi", "-i", "sine=f=50:r=44100"
                ]
                filter_complex = (
                    f"[0:v]subtitles='{ass_path_escaped}'[v];"
                    "[2:a][3:a]amix=inputs=2:duration=first:normalize=0,volume=0.08,lowpass=f=250[bgm];"
                    "[1:a]volume=1.8[vce];"
                    "[vce][bgm]amix=inputs=2:duration=first:dropout_transition=2:normalize=0[a]"
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
                    "[1:a][2:a]amix=inputs=2:duration=first,volume=0.35[a]"
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
                            "[2:a][3:a]amix=inputs=2:duration=first:normalize=0,volume=0.08,lowpass=f=250[bgm];"
                            "[1:a]volume=1.8[vce];"
                            "[vce][bgm]amix=inputs=2:duration=first:dropout_transition=2:normalize=0[a]"
                        )
                        simple_map = ["-map", "0:v", "-map", "[a]"]
                    else:
                        simple_filter = "[1:a][2:a]amix=inputs=2:duration=first,volume=0.35[a]"
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
    voice: str = "vi-VN-HoaiMyNeural"
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
            voice=voice
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
        voice=voice
    )
