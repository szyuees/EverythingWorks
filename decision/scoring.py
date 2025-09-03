import pandas as pd
from typing import Dict, Any

def normalize_column(series: pd.Series) -> pd.Series:
    """
    Normalize a numeric pandas Series to the range [0, 1].
    """
    if series.empty:
        return series
    return (series - series.min()) / (series.max() - series.min() + 1e-9)


def score_flats(df: pd.DataFrame, weights: Dict[str, float] = None) -> pd.DataFrame:
    """
    Apply decision scoring on HDB resale flats dataset.

    Parameters:
    - df: DataFrame with columns [month, town, flat_type, block, street_name,
                                  storey_range, floor_area, flat_model,
                                  lease_commence_date, remaining_lease, resale_price]
    - weights: dict specifying relative importance of features. 
               Defaults: {"resale_price": 0.4, "floor_area": 0.3, "remaining_lease": 0.3}

    Returns:
    - DataFrame with an extra column 'score' (higher = better).
    """
    if weights is None:
        weights = {"resale_price": 0.4, "floor_area": 0.3, "remaining_lease": 0.3}

    # Normalize features
    df = df.copy()
    df["price_norm"] = 1 - normalize_column(df["resale_price"])  # lower price = better
    df["area_norm"] = normalize_column(df["floor_area"])
    df["lease_norm"] = normalize_column(df["remaining_lease"])

    # Weighted sum
    df["score"] = (
        weights["resale_price"] * df["price_norm"]
        + weights["floor_area"] * df["area_norm"]
        + weights["remaining_lease"] * df["lease_norm"]
    )

    # Sort by score
    df = df.sort_values("score", ascending=False)

    return df
