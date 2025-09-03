import pandas as pd
from pathlib import Path
from typing import Dict, Any

# Path to the local CSV dataset
DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "sample_hdb_resale.csv"

def load_local_resale_data() -> pd.DataFrame:
    """
    Load the local resale flat transactions dataset into a pandas DataFrame.
    """
    df = pd.read_csv(DATA_PATH)
    # Ensure correct dtypes
    df["month"] = pd.to_datetime(df["month"], errors="coerce")
    df["resale_price"] = pd.to_numeric(df["resale_price"], errors="coerce")
    return df

def get_resale_transactions(
    town: str = None,
    flat_type: str = None,
    months_window: int = 12
) -> Dict[str, Any]:
    """
    Retrieve resale transactions filtered by town, flat type, and recent months window.
    """
    df = load_local_resale_data()

    # Filter by town (case-insensitive)
    if town:
        df = df[df["town"].str.lower() == town.lower()]

    # Filter by flat_type (case-insensitive)
    if flat_type:
        df = df[df["flat_type"].str.lower() == flat_type.lower()]

    # Apply months_window filter
    if months_window and not df.empty:
        latest_month = df["month"].max()
        cutoff = latest_month - pd.DateOffset(months=months_window)
        df = df[df["month"] >= cutoff]

    # Convert result to dict
    records = df.sort_values("month", ascending=False).to_dict(orient="records")

    return {"transactions": records}


