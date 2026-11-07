"""
Text cleaning and normalization module for Vietnamese social media posts.
"""

import re
import unicodedata
from typing import Dict, List


def clean_text(text: str) -> str:
    """Clean URLs, redundant spaces, and normalize Unicode NFC."""
    if not isinstance(text, str):
        return ""
    
    # Strip URL links
    text = re.sub(r"https?://\S+|www\.\S+", "", text)
    
    # Normalize to Unicode NFC
    text = unicodedata.normalize("NFC", text)
    
    # Strip excessive repeated spaces and newlines
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    
    return text.strip()


def extract_hashtags(text: str) -> List[str]:
    """Extract all hashtags from post content."""
    if not isinstance(text, str):
        return []
    return re.findall(r"#\w+", text)


def extract_punctuation_counts(text: str) -> Dict[str, int]:
    """Count engagement-driving punctuation marks: ?, !, ..."""
    if not isinstance(text, str):
        return {"question_count": 0, "exclamation_count": 0, "ellipsis_count": 0}
    
    return {
        "question_count": len(re.findall(r"\?", text)),
        "exclamation_count": len(re.findall(r"!", text)),
        "ellipsis_count": len(re.findall(r"\.{3,}|…", text))
    }
