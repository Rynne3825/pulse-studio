# TEST_INFRA — Pulse Studio Theme Presets & Viral Scripting Testing Infrastructure

## 1. Overview & Test Philosophy

Pulse Studio's video production engine upgrades introduce two core production tracks:
1. **Visual & Graphic Themes**: Expanded visual styling with 5 distinct presets (`vibrant`, `neon`, `tech`, `editorial`, `pastel`), dynamic TrueType typography, multi-scene color schemes, and theme-tailored FFmpeg motion graphics formulas.
2. **AI Viral Scripting & Detailed Image Prompts**: 3-part viral short video formula (Hook <=15 words & `?`, Retain 60-85 words, Payoff/CTA 15-25 words & `?`), 5-aspect cinematic image prompts (Subject, Lighting, Camera, Color Tone, Art Style), and deterministic offline fallback.

This test infrastructure follows a strict **opaque-box, progressive testability harness**:
- **Zero Facade Testing**: Every test asserts real behaviors, actual file existence, image dimensions, pixel properties, string constraints, and JSON schemas. No mock passes without exercising real logic.
- **Progressive Testability**: Tests verify interface contracts defined in `PROJECT.md` and `ORIGINAL_REQUEST.md`. Known baseline variances during concurrent worker implementation are handled gracefully with descriptive assertion failures.
- **Deterministic Offline Verification**: Tests run fully offline without external API keys or live network dependencies, exercising Pillow and FFmpeg local synthesizers.

---

## 2. Test Architecture & Environment

| Component | Specification | Location |
|---|---|---|
| **Python Runtime** | Python 3.11.9 (64-bit AMD64) | `D:\pulse-studio\.venv\Scripts\python.exe` |
| **FFmpeg Binary** | FFmpeg 8.0.1 full build (gyan.dev) | `C:\Users\Rynne\AppData\Local\Microsoft\WinGet\Links\ffmpeg.EXE` |
| **FFprobe Binary** | FFprobe 8.0.1 full build (gyan.dev) | `C:\Users\Rynne\AppData\Local\Microsoft\WinGet\Links\ffprobe.exe` |
| **Test Runner** | Standard Library `unittest` (`pytest` not in `.venv`) | `tests/test_theme_and_viral_verification.py` |
| **System Fonts** | Segoe UI, Bahnschrift, Consolas, Georgia, Arial | `C:\Windows\Fonts\` |
| **Image Engine** | Pillow (PIL) >= 10.0.0 | `PIL.Image`, `PIL.ImageDraw`, `PIL.ImageFont` |
| **Output Storage** | Isolated Temporary Directories | `tempfile.TemporaryDirectory` |

---

## 3. Feature Inventory Coverage Matrix

| Feature ID | Feature Name | Test Tier | Test Class & Method Group | Success Criteria |
|---|---|---|---|---|
| **F1** | 5 Theme Presets | Tier 1 | `TestTier1FeatureCoverage.test_f1_*` | Presets `vibrant`, `neon`, `tech`, `editorial`, `pastel` exist in `THEME_PRESETS` with valid color, font, scene, and motion attributes. |
| **F2** | Theme Card Generator | Tier 1, Tier 2 | `TestTier1FeatureCoverage.test_f2_*`<br>`TestTier2BoundaryAndCorners.test_f2_*` | `_generate_card` renders 720x1280 image file (>5KB) for every theme, supports backward-compatible signature. |
| **F3** | Viral 3-Part Scripting | Tier 1, Tier 2 | `TestTier1FeatureCoverage.test_f3_*`<br>`TestTier2BoundaryAndCorners.test_f3_*` | Hook (<=15 words, ends with `?`, viral trigger keywords), Retain (60-85 words, 2 scenes), Payoff/CTA (15-25 words, ends with `?`, viral CTA keywords). |
| **F4** | 5-Aspect Detailed Image Prompts | Tier 1 | `TestTier1FeatureCoverage.test_f4_*` | Each scene includes `visual_prompt` starting with `"Vertical 9:16 aspect ratio video, "` and covers Subject, Lighting, Camera, Color Tone, Art Style. |
| **F5** | Full Offline Fallback Synthesis | Tier 1, Tier 2 | `TestTier1FeatureCoverage.test_f5_*`<br>`TestTier2BoundaryAndCorners.test_f5_*` | `safe_script_fallback` and `SafeFallbackSynthesizer` operate deterministically with zero network and no API key. |
| **F6** | Boundary & Corner Robustness | Tier 2 | `TestTier2BoundaryAndCorners.test_tier2_*` | Empty strings, long text (>500 chars), invalid theme names, Vietnamese diacritics, missing keys handled safely. |
| **F7** | Cross-Feature Combinations | Tier 3 | `TestTier3CrossFeatureCombinations.test_tier3_*` | Theme + viral script montage (4 cards), light vs dark theme contrast, instant preview speed (<0.2s), script-to-video pipe. |
| **F8** | Production Editorial Pipeline | Tier 4 | `TestTier4RealWorldWorkloads.test_tier4_*` | End-to-end news processing: article -> viral script -> 4 cards -> montage video synthesis -> content evaluator S-rank. |

---

## 4. Four-Tier Test Structure

### Tier 1: Feature Coverage (>=5 tests per feature category)

#### Category 1: 5 Theme Presets (`test_f1_*`)
1. `test_f1_theme_presets_all_five_exist`: Verifies `vibrant`, `neon`, `tech`, `editorial`, `pastel` all exist as keys in `THEME_PRESETS`.
2. `test_f1_theme_presets_attribute_schema`: Each preset contains `name`, `bg_top` (or `bg_start`), `bg_bottom` (or `bg_end`), `text_headline` (or `headline_text`), `card_outline` (or `border`), `scene_colors`, and `motion_zoompan` (or `motions`).
3. `test_f1_theme_presets_distinct_color_palettes`: Palettes across themes are visually distinct (not all identical RGB values).
4. `test_f1_theme_presets_scene_colors_count`: Each theme defines at least 4 scene colors for 4-scene storyboard mapping.
5. `test_f1_theme_presets_motion_zoompan_syntax`: FFmpeg motion expressions contain valid zoompan tokens (`zoom`, `d=`, `s=720x1280`, `fps=25`).

#### Category 2: Theme Card Generator (`test_f2_*`)
6. `test_f2_card_dimensions_all_five_themes`: Generates cards across all 5 themes and verifies exact dimensions `720x1280` via PIL.
7. `test_f2_card_image_format_and_filesize`: Verifies output format is a valid image file (PNG or JPEG) with size > 5KB.
8. `test_f2_card_backward_compatibility_signature`: Verifies calling `_generate_card(title, headline, color, ref_image_path, temp_dir, scene_num)` without `theme` uses safe default without error.
9. `test_f2_card_with_reference_image`: Card generation succeeds with local image file as reference image (central frame + blurred backdrop).
10. `test_f2_card_without_reference_image`: Card generation succeeds with `ref_image_path=None` using vertical theme gradient.

#### Category 3: Viral 3-Part Scripting (`test_f3_*`)
11. `test_f3_script_hook_conformance`: Hook word count is <= 15 words, ends with `?`, and includes viral trigger keywords (`sự thật`, `bóc mẽ`, `chấn động`, `cực sốc`, `lừa đảo`, `cảnh báo`, `bí mật`, `bất ngờ`, `đừng vội`, `tiết lộ`).
12. `test_f3_script_retain_conformance`: Retain section (Scene 2 & Scene 3) word count is between 60 and 85 words, covering mechanism and evidence.
13. `test_f3_script_cta_conformance`: Payoff/CTA word count is between 15 and 25 words, ends with `?`, and includes viral CTA keywords (`bình luận`, `nghĩ sao`, `ý kiến`, `chia sẻ`, `thảo luận`).
14. `test_f3_script_four_scenes_structure`: Output contains exactly 4 scenes with sequential `scene_num` (1 to 4), distinct `title`, `duration_sec`, `voice_text`, `camera_motion`, and `visual_prompt`.
15. `test_f3_script_hashtags_and_full_script`: Output contains at least 4 hashtags and `full_script` assembling Hook, Body, CTA, and hashtags.

#### Category 4: 5-Aspect Detailed Image Prompts (`test_f4_*`)
16. `test_f4_image_prompts_aspect_ratio_prefix`: Every scene's `visual_prompt` begins with `"Vertical 9:16 aspect ratio video"`.
17. `test_f4_image_prompts_five_aspects_detail`: Scene `visual_prompt` or `image_prompt_detail` includes Subject, Lighting, Camera, Color Tone, and Art Style specifications.
18. `test_f4_image_prompts_english_only`: Visual prompts are strictly in English for generative engine compatibility.
19. `test_f4_image_prompts_camera_motion_mapping`: Camera motions match standard cinematic motions (`slow dolly push-in`, `pan left to right`, `slow tilt down`, `center focal hold`).
20. `test_f4_cinematography_locks_presence`: `cinematography_locks` dictionary contains `style_lock`, `char_lock`, `set_lock`, `video_suffix`, `negative_prompt`.

#### Category 5: Full Offline Fallback Synthesis (`test_f5_*`)
21. `test_f5_offline_script_fallback_deterministic`: `safe_script_fallback(title, summary)` produces complete valid script without network.
22. `test_f5_offline_generator_safe_mode`: `generate_tiktok_script(..., safe_fallback=True)` returns valid script when router/gateway is unreachable.
23. `test_f5_offline_card_synthesis_no_network`: `SafeFallbackSynthesizer._generate_card` runs completely offline with Pillow.
24. `test_f5_offline_voiceover_resilience`: Voiceover falls back safely without unhandled exceptions.
25. `test_f5_offline_video_synthesis_short_render`: `SafeFallbackSynthesizer.synthesize` completes short render (duration=2s) with custom theme offline.

---

### Tier 2: Boundary & Corner Cases (>=5 tests)

26. `test_tier2_empty_or_whitespace_inputs`: Empty string or whitespace title/summary produces safe fallback without crash.
27. `test_tier2_extreme_text_lengths`: Extremely long title (500 chars) and headline (1000 chars) wrap cleanly in `_generate_card` without overflow error.
28. `test_tier2_invalid_theme_name_graceful_fallback`: Invalid theme name (e.g., `"unknown_theme"`, `""`, `None`) gracefully falls back to default theme without raising `KeyError`.
29. `test_tier2_complex_vietnamese_diacritics`: Complex Vietnamese characters (`đường, ngõ, phở, trắc nghiệm, khuất tất, khởi sắc, bứt phá`) render without font glyph corruption or encoding errors.
30. `test_tier2_missing_or_corrupted_ref_image`: Non-existent or corrupted file path for `ref_image_path` falls back smoothly to theme gradient background.
31. `test_tier2_script_missing_keys_safe_defaults`: Missing fields in script dictionary passed to `synthesize` are safely handled by default fallbacks.

---

### Tier 3: Cross-Feature Combinations (>=4 tests)

32. `test_tier3_theme_and_viral_script_montage`: End-to-end combination: `safe_script_fallback` generates 4-scene script, and `_generate_card` renders 4 cards with matching theme scene colors.
33. `test_tier3_theme_color_and_headline_contrast`: Verifies that light themes (`editorial`, `pastel`) use dark typography (`#18181B` or dark slate) and dark themes (`neon`, `tech`, `vibrant`) use high-luminance typography (`#FFFFFF` or neon white) for WCAG readability.
34. `test_tier3_all_themes_instant_card_preview`: Simulates Streamlit UI card preview button across all 5 themes, verifying execution latency under 0.2s per card.
35. `test_tier3_offline_generator_to_synthesizer_pipeline`: Chained pipeline execution: `safe_script_fallback` -> `SafeFallbackSynthesizer.synthesize(..., theme="tech")`.

---

### Tier 4: Real-World Application Scenarios (>=4 tests)

36. `test_tier4_editorial_banking_scam_scenario`: Real-world editorial news scenario (Banking SMS phishing warning): generates viral script, 4 cards with `editorial` theme, and validates all structural criteria.
37. `test_tier4_tech_ai_breakthrough_scenario`: Real-world technology news scenario (AI chip breakthrough): generates viral script with `tech` theme and renders short MP4 montage video verifying file validity.
38. `test_tier4_content_evaluator_s_rank_verification`: Evaluates generated viral script using `src.models.content_evaluator.evaluate_tiktok_script`, confirming overall score achieves Rank A/S (>= 75 points).
39. `test_tier4_ui_atelier_theme_integration`: Verifies UI helper logic for theme selection, preview swatch mapping, and pipeline invocation compatibility.

---

## 5. Execution Guide

Run full theme and viral verification suite:
```powershell
Set-Location "D:\pulse-studio"
& "D:\pulse-studio\.venv\Scripts\python.exe" -m unittest tests/test_theme_and_viral_verification.py
```

Run specific test tiers:
```powershell
# Tier 1: Feature Coverage (25 tests)
& "D:\pulse-studio\.venv\Scripts\python.exe" -m unittest tests.test_theme_and_viral_verification.TestTier1FeatureCoverage

# Tier 2: Boundary & Corner Cases (6 tests)
& "D:\pulse-studio\.venv\Scripts\python.exe" -m unittest tests.test_theme_and_viral_verification.TestTier2BoundaryAndCorners

# Tier 3: Cross-Feature Combinations (4 tests)
& "D:\pulse-studio\.venv\Scripts\python.exe" -m unittest tests.test_theme_and_viral_verification.TestTier3CrossFeatureCombinations

# Tier 4: Real-World Application Scenarios (4 tests)
& "D:\pulse-studio\.venv\Scripts\python.exe" -m unittest tests.test_theme_and_viral_verification.TestTier4RealWorldScenarios
```

Run full project regression suite:
```powershell
& "D:\pulse-studio\.venv\Scripts\python.exe" -m unittest discover -s tests -p "test_*.py"
```
