# Project: Pulse Studio Video Generation Pipeline Modernization

## Architecture
Pulse Studio is an automated vertical video (TikTok / Shorts / Reels 720x1280) production system.
The core engine consists of:
- **TTS Synthesis Engine** (`src/video/muse_integration.py:synthesize_voiceover`): Converts script text to speech using `edge-tts` (Vietnamese neural voice `vi-VN-HoaiMyNeural` / `vi-VN-NamMinhNeural`) with thread-isolated event loop and Google Translate TTS fallback.
- **Card Graphic Engine** (`src/video/muse_integration.py:_generate_card`): Renders visual cards using PIL with Windows TrueType fonts (`Segoe UI`, `Arial`), implementing a 3-tier visual hierarchy (Badge Pill, Headline, Focal Graphic Frame, Editorial Card).
- **Video Motion & Multiplex Engine** (`src/video/muse_integration.py:SafeFallbackSynthesizer.synthesize`): Orchestrates FFmpeg single-pass filter complex with smoothstep zoompan easing, dynamic sidechain BGM ducking (-12dB), full audio padding (`apad`), and ASS subtitle rendering to export production-ready H.264/AAC MP4.
- **E2E Testing Harness** (`tests/test_e2e_video_pipeline.py`): Automated 4-tier test runner verifying audio waveform duration, speech audibility, card rendering, and multi-scene MP4 output.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | F1: Thread-Isolated Edge-TTS Engine | Dedicated thread runner with `asyncio.new_event_loop()`, removing 600-char truncation and event loop clash | M1-AUDIO | Survey 1 |
| 2 | F2: Vietnamese Fallback TTS | Online Google Translate TTS fallback (`tl=vi`) + local retry resilience, avoiding English SAPI | M1-AUDIO | Survey 1, 3 |
| 3 | F3: FFmpeg Audio Mixing & Ducking Filters | `sidechaincompress` ducking (-12dB), `apad` silence padding to prevent premature audio cutoff, `amix` with `normalize=0` | M1-AUDIO | Survey 1, 2, 3 |
| 4 | F4: Dependency & Packaging Integrity | Add `edge-tts>=7.0.0` to `requirements.txt` | M1-AUDIO | Survey 1 |
| 5 | F5: TrueType Typography & Vietnamese Font Rendering | Load TrueType fonts (`Segoe UI / Arial`), dynamic text wrapping, eliminating tofu characters (`?`) | M2-VISUAL | Survey 2, 3 |
| 6 | F6: TikTok Studio Card Visual Layout | 3-tier visual layout (Badge Pill, Headline, Focal Graphic Frame, Glassmorphism Card) | M2-VISUAL | Survey 2 |
| 7 | F7: Smoothstep Easing Zoompan Motion | Film-grade ease-in-out smoothstep zoompan formulas removing integer-pixel judder | M2-VISUAL | Survey 2 |
| 8 | F8: Single-Pass FFmpeg Pipeline Acceleration | Unify multi-subprocess cascade into single-pass `filter_complex` (accelerate render 7.4x) | M2-VISUAL | Survey 2 |
| 9 | F9: Subtitle & Card Collision Elimination | Reposition ASS subtitle margins and alignment to lower third to prevent collision with card content | M2-VISUAL | Survey 2 |
| 10 | F10: Comprehensive E2E Testing Infrastructure | 4-tier opaque-box automated test suite verifying audio, visual, and full 20s render | E2E-TEST | Survey 3 |
| 11 | F11: Full End-to-End Pipeline Render Verification | 20s production video export, H.264/AAC conformance, synchronized duration, speech audibility over ducked BGM | M3-INTEGRATION | Survey 1, 2, 3 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 0 | E2E-TEST | Design & implement 4-tier E2E test suite (`tests/test_e2e_video_pipeline.py`), verify test runner, publish `TEST_READY.md` | none | PLANNED |
| 1 | M1-AUDIO | Refactor `synthesize_voiceover` (thread-isolated edge-tts, Vietnamese fallback), FFmpeg audio filterchain (`sidechaincompress`, `apad`, `normalize=0`), update `requirements.txt` | none | PLANNED |
| 2 | M2-VISUAL | Refactor `_generate_card` (TrueType typography, layout hierarchy), smoothstep motion formulas, ASS subtitle repositioning, single-pass FFmpeg pipeline | none | PLANNED |
| 3 | M3-INTEGRATION | Integrate Audio & Visual pipelines into production render, pass 100% E2E tests (Tiers 1-4), execute Tier 5 adversarial hardening | E2E-TEST, M1-AUDIO, M2-VISUAL | PLANNED |

## Interface Contracts
### synthesize_voiceover Contract
- **Function**: `synthesize_voiceover(text: str, output_path: Union[str, Path], voice: str = "vi-VN-HoaiMyNeural") -> bool`
- **Inputs**:
  - `text`: Vietnamese script text (UTF-8, arbitrary length, no 600-char truncation).
  - `output_path`: Destination file path for generated MP3.
  - `voice`: Edge-TTS neural voice name.
- **Outputs**:
  - Returns `True` if audio successfully synthesized and written to disk with size > 1000 bytes.
  - Returns `False` only if all engines (edge-tts + fallback) fail; does not crash or raise uncaught exception.
- **Behavior**:
  - Primary: `edge_tts.Communicate` executed via worker thread with dedicated event loop. Retries up to 2 times on transient network error.
  - Secondary fallback: Google Translate TTS endpoint (`client=tw-ob`, `tl=vi`).
  - Terminal fallback: Silent MP3 generator of appropriate duration to avoid pipeline interruption.

### Card Generation Contract
- **Function**: `SafeFallbackSynthesizer._generate_card(scene: Dict[str, Any], idx: int, total: int, title: str, base_color: str, temp_dir: Path) -> Path`
- **Inputs**:
  - `scene`: Dict containing `text`, `type`, `visual_query`.
  - `idx`, `total`: Scene index (1-based) and count.
  - `title`: Video title string.
  - `base_color`: Theme hex/rgb color.
  - `temp_dir`: Temporary working directory.
- **Outputs**:
  - Path to generated 720x1280 PNG card image.
- **Behavior**:
  - Renders all Vietnamese diacritics crisply using `C:/Windows/Fonts/seguisb.ttf` / `arial.ttf`.
  - No text overflow; wraps text cleanly within designated card boundaries.

### FFmpeg Filtergraph Contract
- **Inputs to FFmpeg**:
  - `[0:v]`: Scene card image 1
  - `[1:v]`: Scene card image 2
  - `[2:v]`: Scene card image 3
  - `[3:v]`: Scene card image 4
  - `[4:a]`: Synthesized voiceover audio stream
  - `[5:a]`, `[6:a]`: BGM ambient sound streams (e.g. anoisesrc, sine)
- **Output Streams**:
  - `[v]`: Smoothstep zoompan + xfade scene transitions + ASS subtitle burn-in. Formatted to `yuv420p`, 720x1280, 25fps.
  - `[a]`: Voice padded with `apad` to total duration, BGM ducked by `sidechaincompress` during voice activity, mixed via `amix=inputs=2:duration=first:normalize=0:weights=1 1`. Formatted to 44.1kHz stereo AAC.
  - Output file: Valid MP4, audio stream duration == video stream duration.

## Code Layout
- `src/video/muse_integration.py`: Core video synthesis engine, card generator, audio mixer, FFmpeg runner. (Owned by Workers in M1 and M2).
- `requirements.txt`: Project Python dependencies. (Owned by Worker in M1).
- `tests/test_e2e_video_pipeline.py`: Comprehensive 4-tier E2E test suite. (Owned by Worker in E2E-TEST).
- `TEST_READY.md`: Signal file published by E2E Testing Track when test suite is complete.
- `tests/test_m3_muse_integration.py`: Existing unit tests.
- `tests/test_tiktok_pipeline.py`: Existing integration tests.
