"""
Tầng Tạo Sinh Video TikTok 9:16 Tích Hợp Muse AI REST API và Safe Fallback Engine.
Tuân thủ hợp đồng Contract 4 và đặc tả giao thức czg86389-hub/muse2api.
"""

import os
import re
import time
import shutil
import hashlib
import logging
import tempfile
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Union
from pathlib import Path

import requests
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

load_dotenv()
logger = logging.getLogger(__name__)

# Thư mục lưu trữ video đầu ra (đảm bảo tuyệt đối trỏ về project root)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = BASE_DIR / "data" / "output_videos"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def find_ffmpeg_binary() -> str:
    """Tự động tìm kiếm binary FFmpeg theo thứ tự ưu tiên."""
    # 1. Biến môi trường
    env_bin = os.getenv("FFMPEG_BINARY") or os.getenv("FFMPEG_PATH")
    if env_bin and os.path.isfile(env_bin):
        return env_bin

    # 2. PATH hệ thống
    which_bin = shutil.which("ffmpeg")
    if which_bin:
        return which_bin

    # 3. Đường dẫn WinGet / Windows thông dụng
    candidates = [
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links\ffmpeg.exe"),
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe"
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c

    # Dự phòng cuối
    return "ffmpeg"


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

        # Cấu trúc payload chuẩn czg86389-hub/muse2api
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
                # Trích xuất video_url từ các vị trí cấu trúc phản hồi khả dĩ
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
    """Bộ máy tạo video 9:16 dự phòng nội bộ sử dụng FFmpeg, PIL và Subtitles."""

    def __init__(self) -> None:
        self.ffmpeg_bin = find_ffmpeg_binary()

    def _generate_background_image(
        self,
        ref_image_url: Optional[str],
        temp_dir: Path,
        title: str = "TIN TỨC XU HƯỚNG TIKTOK"
    ) -> Path:
        """Chuẩn bị ảnh nền dọc 9:16 (720x1280). Tải ảnh gốc nếu có, hoặc tự sinh Dark Studio Card."""
        bg_path = temp_dir / "background_9_16.png"

        # Thử tải ảnh gốc từ URL
        if ref_image_url and ref_image_url.strip():
            try:
                resp = requests.get(ref_image_url.strip(), timeout=6)
                if resp.status_code == 200:
                    src_img_path = temp_dir / "downloaded_raw.jpg"
                    with open(src_img_path, "wb") as f:
                        f.write(resp.content)

                    with Image.open(src_img_path) as img:
                        img = img.convert("RGB")
                        # Tạo khung nền 720x1280 mờ ảo (Blurred Backdrop) và đặt ảnh thật sắc nét ở giữa
                        canvas = Image.new("RGB", (720, 1280), (15, 23, 42))
                        
                        # Scale ảnh vừa vặn chiều rộng 720
                        scale = 720.0 / img.width
                        new_h = int(img.height * scale)
                        resized_img = img.resize((720, new_h), Image.Resampling.LANCZOS)
                        
                        # Đặt ở vị trí trung tâm dọc
                        offset_y = max(0, (1280 - new_h) // 2)
                        canvas.paste(resized_img, (0, offset_y))
                        canvas.save(bg_path, "PNG")
                        return bg_path
            except Exception as e:
                logger.warning(f"Không tải được ảnh gốc từ {ref_image_url}: {e}. Chuyển sang vẽ Card đồ họa.")

        # Tự sinh Dark Studio Graphic Card bằng PIL
        img = Image.new("RGB", (720, 1280), (15, 23, 42))  # Slate dark #0F172A
        draw = ImageDraw.Draw(img)

        # Header Badge
        draw.rectangle([(60, 80), (660, 160)], fill=(30, 41, 59), outline=(245, 158, 11), width=3)
        draw.text((80, 105), "THE PULSE EDITORIAL — TIKTOK RADAR", fill=(245, 158, 11))

        # Khung viền trung tâm
        draw.rounded_rectangle([(60, 220), (660, 1000)], radius=24, fill=(24, 24, 37), outline=(51, 65, 85), width=2)
        
        # Tiêu đề & Icon cảnh báo
        draw.text((100, 280), "[TIÊU ĐIỂM BÓC MẼ]", fill=(239, 68, 68))
        clean_title = re.sub(r"\s+", " ", title)[:80]
        # Chia dòng tiêu đề
        words = clean_title.split()
        lines = []
        cur_line = []
        for w in words:
            cur_line.append(w)
            if len(" ".join(cur_line)) > 24:
                lines.append(" ".join(cur_line))
                cur_line = []
        if cur_line:
            lines.append(" ".join(cur_line))

        y_text = 360
        for line in lines[:4]:
            draw.text((100, y_text), line, fill=(255, 255, 255))
            y_text += 50

        # Footer Accent
        draw.text((100, 920), "#ThePulseEditorial  #TikTokTrending", fill=(148, 163, 184))
        img.save(bg_path, "PNG")
        return bg_path

    def _generate_ass_subtitle(
        self,
        script_data: Dict[str, Union[str, List[str]]],
        total_duration: float,
        temp_dir: Path
    ) -> Path:
        """Tạo file phụ đề ASS chuẩn phong cách TikTok chữ vàng viền đen."""
        ass_path = temp_dir / "tiktok_captions.ass"

        hook = str(script_data.get("hook", "")).strip() or "SỰ THẬT CHẤN ĐỘNG CẦN BÓC MẼ!"
        body = str(script_data.get("body", "")).strip() or "Cụ thể vấn đề đang diễn biến phức tạp..."
        cta = str(script_data.get("cta", "")).strip() or "Bạn nghĩ sao về điều này? Hãy để lại ý kiến!"

        # Phân chia mốc thời gian: Hook (0-3s), Body (3s - D-2s), CTA (D-2s - D)
        t_hook_end = min(3.0, total_duration * 0.3)
        t_body_end = max(t_hook_end + 1.0, total_duration - 2.5)

        def fmt_time(sec: float) -> str:
            m = int(sec // 60)
            s = int(sec % 60)
            cs = int((sec - int(sec)) * 100)
            return f"0:{m:02d}:{s:02d}.{cs:02d}"

        ass_content = f"""[Script Info]
Title: TikTok Styled Subtitles
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: HookStyle,Arial,48,&H0000FFFF,&H00000000,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,2,5,40,40,200,1
Style: BodyStyle,Arial,40,&H00FFFFFF,&H00000000,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,40,40,240,1
Style: CTAStyle,Arial,42,&H0000E5FF,&H00000000,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,2,2,40,40,240,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,{fmt_time(0.0)},{fmt_time(t_hook_end)},HookStyle,,0,0,0,,{{\\an5\\b1}}{hook.upper()}
Dialogue: 0,{fmt_time(t_hook_end)},{fmt_time(t_body_end)},BodyStyle,,0,0,0,,{{\\an2}}{body}
Dialogue: 0,{fmt_time(t_body_end)},{fmt_time(total_duration)},CTAStyle,,0,0,0,,{{\\an2\\b1}}{cta}
"""
        with open(ass_path, "w", encoding="utf-8") as f:
            f.write(ass_content)
        return ass_path

    def synthesize(
        self,
        script_data: Dict[str, Union[str, List[str]]],
        ref_image_url: Optional[str] = None,
        duration: int = 5
    ) -> Dict[str, Union[str, float]]:
        """Tổng hợp video MP4 9:16 dự phòng siêu tốc với FFmpeg (< 1s)."""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_file = OUTPUT_DIR / f"fallback_{ts}_{duration}s.mp4"

        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            title = str(script_data.get("hook", "TIN NÓNG MẠNG XÃ HỘI"))

            # 1. Sinh ảnh nền 9:16
            bg_img = self._generate_background_image(ref_image_url=ref_image_url, temp_dir=tmp_dir, title=title)

            # 2. Sinh phụ đề ASS
            ass_file = self._generate_ass_subtitle(script_data=script_data, total_duration=float(duration), temp_dir=tmp_dir)
            ass_path_escaped = str(ass_file).replace("\\", "/").replace(":", "\\:")

            # 3. Lệnh FFmpeg Pan-Zoom + Audio + Subtitle
            # Dùng bộ lọc zoompan nhẹ nhàng tạo chuyển động video TikTok
            # và tích hợp filter subtitles
            total_frames = int(duration * 25)
            cmd = [
                self.ffmpeg_bin,
                "-y",
                "-loop", "1",
                "-i", str(bg_img),
                "-f", "lavfi",
                "-i", f"anullsrc=r=44100:cl=stereo",
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
                    # Nếu bộ lọc subtitles bị lỗi do font, fallback sang lệnh video không subtitle
                    logger.warning(f"Lỗi render phụ đề ASS ({proc.stderr[:150]}). Chuyển sang render video gốc.")
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
            "message": "Video tạo thành công qua Safe Fallback Engine (FFmpeg 9:16 + TikTok Dynamic Subtitles)"
        }


def generate_tiktok_video(
    visual_prompt: str,
    reference_image_url: Optional[str] = None,
    script_data: Optional[Dict[str, Union[str, List[str]]]] = None,
    mode: str = "auto",
    duration: int = 5
) -> Dict[str, Union[str, float]]:
    """
    Entrypoint điều phối tạo video TikTok dọc 9:16 (Façade chính cho giao diện Streamlit).
    mode:
      - 'auto': Thử gọi Muse AI trước; nếu chưa cấu hình hoặc gặp lỗi thì tự động chuyển sang Safe Fallback.
      - 'muse_api': Ép buộc gọi qua Muse AI REST API.
      - 'fallback': Ép buộc chạy Safe Fallback Engine nội bộ.
    """
    script_dict = script_data or {
        "hook": "SỰ THẬT VỀ TREND NÓNG NÀY!",
        "body": visual_prompt[:150],
        "cta": "Bạn nghĩ sao? Hãy để lại ý kiến bên dưới!"
    }

    client = MuseAIClient()
    fallback_engine = SafeFallbackSynthesizer()

    # Chế độ ép buộc Fallback
    if mode == "fallback":
        return fallback_engine.synthesize(script_data=script_dict, ref_image_url=reference_image_url, duration=duration)

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
            logger.warning(f"Muse AI API gặp sự cố: {e}. Kích hoạt Safe Fallback Engine ngay lập tức!")

    # Fallback an toàn mặc định
    return fallback_engine.synthesize(script_data=script_dict, ref_image_url=reference_image_url, duration=duration)
