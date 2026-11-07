"""
Unit test for updated model training artifacts and inference pipeline.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.models.predict import predict_engagement, load_artifacts


def test_model_loading_and_prediction():
    # 1. Test model files and vectorizers exist and can be loaded
    model, tfidf, svd, features = load_artifacts()
    assert model is not None, "Model failed to load."
    assert tfidf is not None, "TF-IDF vectorizer failed to load."
    assert svd is not None, "SVD transformer failed to load."
    assert len(features) == 62, f"Expected 62 features, got {len(features)}"
    print("test_model_and_transformers_loading: PASSED")
    
    # 2. Test inference on sample post
    res = predict_engagement(
        content="Bất ngờ với tính năng AI mới của Google: Quá đỉnh chóp và tiện lợi! #AI #Google",
        published_at="2026-10-27T11:00:00.000Z",
        topic_category=1,
        thumbnail_url="https://example.com/thumbnail.png"
    )
    
    assert res["predicted_level"] in [0, 1, 2, 3], "Invalid predicted level."
    assert res["predicted_label"] in ["Thấp", "Vừa", "Cao", "Viral"], "Invalid predicted label."
    assert len(res["probabilities"]) == 4, "Expected 4 class probabilities."
    
    total_prob = sum(res["probabilities"].values())
    assert 99.0 <= total_prob <= 101.0, f"Probabilities sum out of range: {total_prob}"
    print("test_prediction_inference: PASSED")


if __name__ == "__main__":
    test_model_loading_and_prediction()
    print("ALL MODEL TESTS PASSED SUCCESSFULLY.")
