import pandas as pd


def calculate_profit_by_order(df: pd.DataFrame) -> pd.DataFrame:
    """Add a Profit column: (List Price - cost price) * Quantity * (1 - Discount Percent / 100)"""
    df = df.copy()
    df["Profit"] = (df["List Price"] - df["cost price"]) * df["Quantity"] * (1 - df["Discount Percent"] / 100)
    return df


def calculate_most_profitable_region(df: pd.DataFrame) -> pd.DataFrame:
    """Return the single most profitable region and its total profit."""
    if df.empty:
        return pd.DataFrame(columns=["Region", "Profit"])
    by_region = df.groupby("Region", as_index=False)["Profit"].sum()
    return by_region.loc[[by_region["Profit"].idxmax()]]


def find_most_common_ship_method(df: pd.DataFrame) -> pd.DataFrame:
    """Return the most common Ship Mode for each Category."""
    return (
        df.groupby(["Category", "Ship Mode"])
        .size()
        .reset_index(name="Count")
        .sort_values("Count", ascending=False)
        .drop_duplicates(subset="Category")
        .drop(columns="Count")
        .reset_index(drop=True)
    )


def find_number_of_order_per_category(df: pd.DataFrame) -> pd.DataFrame:
    """Return order counts grouped by Category and Sub Category."""
    return (
        df.groupby(["Category", "Sub Category"])
        .size()
        .reset_index(name="Order Count")
    )
