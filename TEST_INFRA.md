# TEST_INFRA — Pulse Studio Video Generation Pipeline Testing Infrastructure

## 1. Overview & Test Philosophy

Pulse Studio's automated video pipeline synthesizes vertical TikTok/Shorts (720x1280 9:16) videos using neural voiceover, typography card graphics, dynamic audio ducking, and motion video encoding.

This test infrastructure implements an **opaque-box, progressive testability harness**:
- **Zero Facade Testing**: Tests execute real system logic (audio synthesis, PIL card rendering, FFmpeg multiplexing) and inspect actual physical files on disk via `ffprobe`, `ffmpeg volumedetect`, and PIL image inspection.
- **Progressive Testability**: Tests verify interface contracts established in `PROJECT.md`. During intermediate milestone implementation, tests objectively expose known baseline defects (e.g., premature audio truncation, bitmap font degradation) and turn green upon milestone completion.
- **Deterministic Media Probing**: Audio loudness, stream codec tags, frame resolutions, and timestamp synchronization are verified deterministically without external test framework dependencies (using pure Python `unittest` and standard binaries).

---

## 2. Test Architecture & Environment

| Component | Specification | Location |
|---|---|---|
| **Python Runtime** | Python 3.11.9 (64-bit AMD64) | `D:\pulse-studio\.venv\Scripts\python.exe` |
| **FFmpeg Binary** | FFmpeg 8.0.1 full build (gyan.dev) | `C:\Users\Rynne\AppData\Local\Microsoft\WinGet\Links\ffmpeg.EXE` |
| **FFprobe Binary** | FFprobe 8.0.1 full build (gyan.dev) | `C:\Users\Rynne\AppData\Local\Microsoft\WinGet\Links\ffprobe.exe` |
| **Test Runner** | Standard Library `unittest` | `tests/test_e2e_video_pipeline.py` |
| **Fonts Available** | Segoe UI, Segoe UI Bold, Arial, Arial Bold | `C:\Windows\Fonts\` |
| **Output Test Artifacts**| Isolated Temp Directories & Video Out | `data/output_videos/`, `tempfile.TemporaryDirectory` |

---

## 3. Feature Inventory Coverage Matrix

Mapping features from `PROJECT.md` to test classes and test methods in `tests/test_e2e_video_pipeline.py`:

| Feature ID | Feature Name | Test Tier | Test Class & Target Methods | Status Criteria |
|---|---|---|---|---|
| **F1** | Thread-Isolated Edge-TTS Engine | Tier 1, Tier 2 | `TestTier1FeatureCoverage.test_f1_*`<br>`TestTier2BoundaryAndCorners.test_f1_*` | MP3 > 1KB, valid audio header, no event loop clash, >1000 char handling |
| **F2** | Vietnamese Fallback TTS | Tier 1, Tier 2 | `TestTier1FeatureCoverage.test_f2_*`<br>`TestTier2BoundaryAndCorners.test_f2_*` | Secondary voice fallback, Google Translate TTS fallback (`tl=vi`), offline socket resilience |
| **F3** | FFmpeg Audio Mixing & Ducking Filters | Tier 1, Tier 3, Tier 4 | `TestTier1FeatureCoverage.test_f3_*`<br>`TestTier3CrossFeatureCombinations.test_f3_*`<br>`TestTier4RealWorldWorkloads.test_f3_*` | `sidechaincompress` ducking, `amix normalize=0`, `apad` silence padding, speech audibility > -35dB |
| **F4** | Dependency & Packaging Integrity | Tier 1 | `TestTier1FeatureCoverage.test_f4_*` | `edge-tts` importable, Pillow TrueType support verified |
| **F5** | TrueType Typography & Font Rendering | Tier 1, Tier 2 | `TestTier1FeatureCoverage.test_f5_*`<br>`TestTier2BoundaryAndCorners.test_f5_*` | Font loading (`segoeui.ttf`/`arial.ttf`), complex diacritics (`đường, ngõ, phở, trắc nghiệm`), no tofu |
| **F6** | TikTok Studio Card Visual Layout | Tier 1 | `TestTier1FeatureCoverage.test_f6_*` | 720x1280 resolution, PNG format, badge pill, headline text wrapping, focal frame |
| **F7** | Smoothstep Easing Zoompan Motion | Tier 1, Tier 3 | `TestTier1FeatureCoverage.test_f7_*`<br>`TestTier3CrossFeatureCombinations.test_f7_*` | Valid filter syntax, smooth transition parameters, 25fps output |
| **F8** | Single-Pass FFmpeg Pipeline Acceleration | Tier 3, Tier 4 | `TestTier3CrossFeatureCombinations.test_f8_*`<br>`TestTier4RealWorldWorkloads.test_f8_*` | Multi-scene concat/pipeline execution within timeout limits |
| **F9** | Subtitle & Card Collision Elimination | Tier 1, Tier 3 | `TestTier1FeatureCoverage.test_f9_*`<br>`TestTier3CrossFeatureCombinations.test_f9_*` | ASS subtitle script generation, style headers (`HookStyle`, `BodyStyle`, `CTAStyle`), margin coordinates |
| **F10** | Comprehensive E2E Testing Infrastructure | Harness | `tests/test_e2e_video_pipeline.py` | Complete 4-tier executable test suite with automated runner |
| **F11** | Full End-to-End Pipeline Render Verification | Tier 4 | `TestTier4RealWorldWorkloads.test_f11_*` | 20s TikTok video, H.264 video + AAC audio, audio duration == video duration, speech audible over BGM |

---

## 4. Four-Tier Test Structure

### Tier 1: Feature Coverage (>=5 tests per feature)
Covers individual subsystem units in isolation with real parameters:
1. **TTS Synthesis (`test_f1_tts_*`)**:
   - `test_f1_tts_primary_voice_generates_valid_mp3`: HoaiMyNeural creates MP3 > 1KB.
   - `test_f1_tts_secondary_voice_generates_valid_mp3`: NamMinhNeural creates MP3 > 1KB.
   - `test_f1_tts_audio_format_validity`: Validated via `ffprobe` as audio/mp3.
   - `test_f1_tts_positive_audio_duration`: Duration > 0.5s matching spoken syllables.
   - `test_f1_tts_return_code_contract`: Returns boolean `True` on success.
2. **Fallback Mechanism (`test_f2_fallback_*`)**:
   - `test_f2_fallback_secondary_voice_on_primary_failure`: Fallback to secondary edge-tts voice.
   - `test_f2_fallback_google_tts_on_edge_failure`: Native Google Translate TTS fallback (`tl=vi`).
   - `test_f2_fallback_graceful_exception_handling`: Never crashes or raises uncaught exceptions.
   - `test_f2_fallback_google_tts_diacritics`: Correct audio output for accented Vietnamese sentences.
   - `test_f2_fallback_offline_terminal_handling`: Returns `False` or terminal fallback under simulated network isolation.
3. **Card Graphic Generation (`test_f5_f6_card_*`)**:
   - `test_f6_card_dimensions_and_format`: Exact 720x1280 PNG image.
   - `test_f6_card_visual_components_present`: Color palette, header banner, glassmorphic card box.
   - `test_f5_card_vietnamese_diacritic_rendering`: Renders Vietnamese diacritics without PIL glyph errors.
   - `test_f6_card_dynamic_text_wrapping`: Wraps multi-line sentences without text overflow.
   - `test_f6_card_with_reference_image`: Blurred background Lanczos downsampling + central focal frame.
4. **Audio Ducking & Mixing Filter Logic (`test_f3_audio_ducking_*`)**:
   - `test_f3_audio_ducking_filter_syntax_validity`: FFmpeg executes audio filtergraph without syntax errors.
   - `test_f3_audio_ducking_speech_audibility`: Voiceover level remains louder than background noise.
   - `test_f3_audio_ducking_apad_duration_matching`: Audio track padded to match full video length.
   - `test_f3_audio_ducking_stereo_44k_conformance`: Audio stream output is 44.1kHz stereo.
   - `test_f3_audio_ducking_sidechain_attenuation`: BGM drone attenuated during speech presence.
5. **MP4 Container & Video Export (`test_f11_mp4_export_*`)**:
   - `test_f11_mp4_faststart_movflags`: FastStart metadata present for mobile streaming.
   - `test_f11_mp4_video_codec_h264`: Stream 0 codec is `h264` (`avc1`).
   - `test_f11_mp4_audio_codec_aac`: Stream 1 codec is `aac` (`mp4a`).
   - `test_f11_mp4_frame_dimensions_and_rate`: 720x1280 resolution at 25 fps.
   - `test_f11_mp4_pixel_format_yuv420p`: Color space is `yuv420p`.

### Tier 2: Boundary & Corner Cases (>=5 tests)
Stress testing input extremes, network faults, and diacritics:
1. `test_f1_tier2_empty_or_whitespace_script`: Passing `""` or `"   \n\t  "` returns `False` gracefully.
2. `test_f1_tier2_long_script_over_1000_chars`: Script > 1000 chars processed without buffer overflow.
3. `test_f5_tier2_complex_vietnamese_diacritics`: Script with compound diacritics (`đường, ngõ, phở, trắc nghiệm, khuất tất, khởi sắc, bứt phá`) verified across TTS and card rendering.
4. `test_f8_tier2_short_duration_boundaries`: Sub-10s duration boundary (duration=2s, 5s) correctly routed to single-scene fast path.
5. `test_f2_tier2_offline_socket_failure_simulation`: Simulated network error triggers fallback without crashing.
6. `test_f6_tier2_missing_or_corrupted_reference_image`: Non-existent image file falls back to gradient background cleanly.

### Tier 3: Cross-Feature Combinations (>=4 tests)
Validates interactions between subsystems:
1. `test_tier3_multiscene_card_montage_integration`: 4 visual scene cards linked into multi-scene pipeline with distinct colors and headlines.
2. `test_tier3_synchronized_ass_subtitles`: ASS subtitle file contains correctly aligned timestamps for Hook, Body, and CTA matching scene durations.
3. `test_tier3_voiceover_failure_pipeline_resilience`: Multi-scene render succeeds with ambient BGM even if voiceover synthesis fails.
4. `test_tier3_combined_ducking_over_multiscene_visual`: Synchronized audio mix with ducked BGM correctly multiplexed into multi-scene video.

### Tier 4: Real-World Workload (>=4 tests)
Production-grade end-to-end video synthesis:
1. `test_tier4_full_20s_production_render`: Executes 20-second TikTok synthesis with realistic script; verifies H.264/AAC, 720x1280, 25fps via `ffprobe`.
2. `test_tier4_audio_video_duration_synchronization`: Verifies $|duration_{video} - duration_{audio}| \le 0.5s$, detecting premature cutoff defects.
3. `test_tier4_speech_audibility_over_ducked_bgm`: Runs `ffmpeg -af volumedetect`; confirms `mean_volume` is within audible range (>= -32dB) and `max_volume` >= -15dB.
4. `test_tier4_facade_generate_tiktok_video`: Verifies top-level facade `generate_tiktok_video()` returns valid dict with existing MP4 > 500KB.

---

## 5. Execution Instructions

Run full E2E test suite:
```powershell
& "D:\pulse-studio\.venv\Scripts\python.exe" tests/test_e2e_video_pipeline.py
```

Run specific tier:
```powershell
& "D:\pulse-studio\.venv\Scripts\python.exe" tests/test_e2e_video_pipeline.py TestTier1FeatureCoverage
& "D:\pulse-studio\.venv\Scripts\python.exe" tests/test_e2e_video_pipeline.py TestTier2BoundaryAndCorners
& "D:\pulse-studio\.venv\Scripts\python.exe" tests/test_e2e_video_pipeline.py TestTier3CrossFeatureCombinations
& "D:\pulse-studio\.venv\Scripts\python.exe" tests/test_e2e_video_pipeline.py TestTier4RealWorldWorkloads
```
