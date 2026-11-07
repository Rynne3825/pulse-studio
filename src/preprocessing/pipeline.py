"""
Preprocessing Pipeline: Raw Facebook Dataset -> Engineered Feature Matrix.
Runs end-to-end cleaning, feature extraction, and target quartile binning.
"""

import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.preprocessing.feature_extractor import extract_features_from_post

LEVEL_LABELS = {0: "Thấp", 1: "Vừa", 2: "Cao", 3: "Viral"}


def run_pipeline(
    input_csv: str = None,
    output_csv: str = None,
    output_parquet: str = None
) -> pd.DataFrame:
    if input_csv is None:
        input_csv = str(PROJECT_ROOT / "data" / "raw" / "dataset.csv")
    if output_csv is None:
        output_csv = str(PROJECT_ROOT / "data" / "processed" / "features.csv")
    if output_parquet is None:
        output_parquet = str(PROJECT_ROOT / "data" / "processed" / "features.parquet")

    print(f"Loading raw dataset from: {input_csv}")
    df = pd.read_csv(input_csv)
    print(f"Loaded {len(df)} records.")

    # 1. Feature extraction loop
    extracted_rows = []
    for _, row in df.iterrows():
        feat = extract_features_from_post(
            content=str(row.get("content", "")),
            published_at=str(row.get("published_at", "")),
            topic_category=int(row.get("topic_category", 0)),
            thumbnail_url=str(row.get("thumbnail_url", ""))
        )
        extracted_rows.append(feat)

    feat_df = pd.DataFrame(extracted_rows)

    # 2. Merge metadata & ground-truth engagement metrics
    merged_df = pd.concat([
        df[["post_id", "page_name", "topic_name", "like_count", "comment_count", "share_count", "engagement_score"]],
        feat_df
    ], axis=1)

    # 3. Discretize target into 4 quartiles per topic (Domain-Adaptive Quartile Binning)
    # Ensures both Technology and Entertainment have balanced 0..3 class distributions
    def assign_quartiles(group: pd.DataFrame) -> pd.Series:
        scores = group["engagement_score"]
        # Use pandas qcut with rank method to handle duplicate values gracefully
        return pd.qcut(scores.rank(method="first"), q=4, labels=[0, 1, 2, 3]).astype(int)

    merged_df["engagement_level"] = merged_df.groupby("topic_category", group_keys=False).apply(assign_quartiles)
    merged_df["engagement_label"] = merged_df["engagement_level"].map(LEVEL_LABELS)

    # 4. Save processed dataset
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    merged_df.to_csv(output_csv, index=False, encoding="utf-8-sig")
    try:
        merged_df.to_parquet(output_parquet, index=False)
        print(f"Saved parquet to: {output_parquet}")
    except Exception as e:
        print(f"Parquet save warning: {e}")

    print("\n=== PREPROCESSING PIPELINE COMPLETED ===")
    print(f"Total processed records: {len(merged_df)}")
    print(f"Features generated ({len(feat_df.columns)}): {list(feat_df.columns)}")
    print("\nClass distribution (4 Engagement Levels):")
    print(merged_df["engagement_label"].value_counts())
    print("\nClass breakdown by topic:")
    print(pd.crosstab(merged_df["topic_name"], merged_df["engagement_label"]))

    return merged_df


if __name__ == "__main__":
    run_pipeline()
