# Project: Pulse Studio Video Production System Upgrade

## Architecture
- **Layer 1: AI Scripting & Visual Prompt Engine** (`src/ai/generator.py`):
  Generates viral 3-part scripts (Hook, Retain, Payoff/CTA) with 5-aspect cinematic image prompts (Subject, Lighting, Camera, Color Tone, Art Style). Features both live AI API generation (Gemini) and deterministic offline fallback (`safe_script_fallback`).
- **Layer 2: Video & Graphic Card Synthesizer** (`src/video/muse_integration.py`):
  Renders 720x1280 graphic cards using 5 distinct theme presets (Vibrant, Neon, Tech, Editorial, Pastel) with TrueType typography, color swatches, 4-scene color schemes, and FFmpeg zoompan motion effects. Supports full local offline synthesis via Pillow + FFmpeg.
- **Layer 3: UI & Editorial Atelier** (`app/components/editorial_atelier.py`):
  Streamlit interface providing theme selection (`video_theme_select`), color preview swatches, instant card preview button (<0.1s / ~31ms), and integration with video generation pipeline.
- **Layer 4: Verification & Automated Test Suite** (`tests/test_theme_and_viral_verification.py`, `tests/test_challenger_stress_verification.py`):
  Comprehensive test suite verifying all 5 themes, card image generation, motion graphics parameters, viral 3-part script structures, and offline fallback compatibility (214/214 tests pass).

## Feature Inventory
| # | Feature | Description | Milestone | Source | Status |
|---|---------|-------------|-----------|--------|--------|
| 1 | 5 Theme Presets | Implement `THEME_PRESETS` (Vibrant, Neon, Tech, Editorial, Pastel) with backgrounds, fonts, and colors | M1 | Survey 1 & 3 | DONE |
| 2 | Theme Card Generation | Upgrade `SafeFallbackSynthesizer._generate_card` to render 720x1280 cards using selected theme | M1 | Survey 1 & 3 | DONE |
| 3 | Motion Graphics Effects | Custom FFmpeg zoompan formulas per theme for dynamic scene transitions | M1 | Survey 1 | DONE |
| 4 | Streamlit Theme Selection & Preview | Add theme selectbox, color swatches, and instant card preview button in `editorial_atelier.py` | M1 | Survey 1 | DONE |
| 5 | Viral 3-Part Scripting | Optimize `TIKTOK_SYSTEM_PROMPT` & fallback for Hook (0-3s), Retain (4-15s), Payoff/CTA (16-20s) | M2 | Survey 2 | DONE |
| 6 | 5-Aspect Detailed Image Prompts | Generate visual prompts with Subject, Lighting, Camera Angle, Color Tone, Art Style | M2 | Survey 2 | DONE |
| 7 | Offline Script & Card Fallback | Ensure offline mode works deterministically without API key or network | M1, M2 | Survey 3 | DONE |
| 8 | Automated Verification Test Suite | Automated test suite in `tests/` verifying all themes, script structures, and fallback | M3 | Survey 3 & E2E Track | DONE |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Visual & Graphic Themes | Implement 5 theme presets, card renderer, motion graphics, and UI preview | None | DONE |
| M2 | Viral Script & Image Prompts | Implement 3-part viral script structure and detailed 5-aspect image prompts | None | DONE |
| M3 | Final E2E Verification & Integration | Run automated tests for all themes, viral scripts, offline fallback, and full regression | M1, M2 | DONE |

## Interface Contracts
### `src/video/muse_integration.py` ↔ Consumers
- `SafeFallbackSynthesizer._generate_card(title, headline, color, ref_image_path, temp_dir, scene_num=1, theme="editorial") -> str`:
  Returns path to generated 720x1280 JPEG/PNG image.
  Maintains backward-compatible parameter ordering with defensive string coercion (`safe_title = str(title or "").strip()`, `safe_headline = str(headline or "").strip()`).
- `THEME_PRESETS`: Dictionary keyed by theme names (`editorial`, `vibrant`, `neon`, `tech`, `pastel`) containing `name`, `font_family`, `title_color`, `headline_color`, `meta_color`, `bg_gradient_start`, `bg_gradient_end`, `banner_bg`, `banner_border`, `panel_bg`, `panel_border`, `card_border`, `scene_colors`, `motions`, `single_motion`, `swatches`.
- `SafeFallbackSynthesizer.synthesize(script_data, audio_path, output_path, theme="editorial") -> str`:
  Accepts optional `theme` keyword argument, passes to card generator and applies theme-specific zoompan camera motion.

### `src/ai/generator.py` ↔ Downstream Synthesizers & Evaluators
- `generate_tiktok_script(title: str, summary: str, engine: str = "gemini", safe_fallback: bool = False) -> TikTokScriptOutput`:
  Returns dict matching `TikTokScriptOutput` with `hook`, `body`, `cta`, `scenes`, `hashtags`, `full_script`, `muse_visual_prompt`.
  Each item in `scenes` has `scene_num`, `title`, `duration_sec`, `voice_text`, `camera_motion`, `visual_prompt`, and `image_prompt_detail`.
  Preserves `"Scene 1 - Hook"` and `"Vertical 9:16 aspect ratio video"` in system prompt for test compatibility.
- `safe_script_fallback(title: str, summary: str, engine: str = "gemini") -> TikTokScriptOutput`:
  Produces valid viral 3-part script and detailed image prompts deterministically offline.

## Code Layout
- `src/video/muse_integration.py`: Visual themes, card synthesis, motion graphics, audio ducking
- `app/components/editorial_atelier.py`: Streamlit UI, theme selector, swatches, instant preview button
- `src/ai/generator.py`: Viral 3-part script generator, 5-aspect prompt generator, safe fallback
- `tests/test_theme_and_viral_verification.py`: 39 E2E test cases across 4 tiers
- `tests/test_challenger_stress_verification.py`: 18 empirical stress test cases
