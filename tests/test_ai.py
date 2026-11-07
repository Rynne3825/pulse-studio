"""
Unit test for Gemini AI Generator module.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.ai.generator import PROMPTS


def test_prompts_configured():
    for mode in ["rewrite", "trend", "deep", "brief"]:
        assert mode in PROMPTS, f"Missing {mode} prompt template."
        assert len(PROMPTS[mode]) > 20, f"{mode} prompt too short."
    print("test_prompts_configured: PASSED")


if __name__ == "__main__":
    test_prompts_configured()
    print("ALL AI GENERATOR TESTS PASSED SUCCESSFULLY.")
