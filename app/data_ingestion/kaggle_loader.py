"""
Loads a Kaggle e-commerce product CSV. Recommended: search Kaggle for
"Flipkart Products" - has native INR pricing and image URLs.
"""
import pandas as pd
from typing import List, Dict, Optional

COLUMN_ALIASES = {
    "title": ["title", "product_name", "name"],
    "category": ["category", "product_category", "category_tree", "product_category_tree"],
    "price": ["price", "retail_price", "discounted_price"],
    "description": ["description", "product_description", "about_product"],
    "url": ["url", "product_url", "link"],
    "product_id": ["product_id", "uniq_id", "id", "pid"],
    "image_url": ["image", "image_url", "images", "product_image", "image_link"],
}


def _find_column(df: pd.DataFrame, aliases: List[str]) -> Optional[str]:
    for alias in aliases:
        for col in df.columns:
            if col.strip().lower() == alias:
                return col
    return None


def _format_inr(raw_value) -> Optional[str]:
    if raw_value is None or (isinstance(raw_value, float) and pd.isna(raw_value)):
        return None
    text = str(raw_value).strip()
    if not text or text.lower() == "nan":
        return None
    cleaned = text.replace("₹", "").replace("Rs.", "").replace("Rs", "").replace(",", "").strip()
    try:
        amount = float(cleaned)
        return f"\u20b9{amount:,.0f}"
    except ValueError:
        return text


def _first_image_url(raw_value) -> str:
    if raw_value is None or (isinstance(raw_value, float) and pd.isna(raw_value)):
        return ""
    text = str(raw_value).strip()
    if text.startswith("["):
        text = text.strip("[]")
        parts = [p.strip().strip('"').strip("'") for p in text.split(",")]
        return parts[0] if parts else ""
    return text


def load_kaggle_csv(csv_path: str, max_rows: int = 500) -> List[Dict]:
    df = pd.read_csv(csv_path)
    df.columns = [c.strip() for c in df.columns]

    resolved = {key: _find_column(df, aliases) for key, aliases in COLUMN_ALIASES.items()}

    if not resolved["title"]:
        raise ValueError(
            "Could not find a title/product name column in the CSV. "
            f"Columns found: {list(df.columns)}"
        )

    df = df.head(max_rows)
    products = []
    for i, row in df.iterrows():
        title = str(row[resolved["title"]]) if resolved["title"] and pd.notna(row[resolved["title"]]) else ""
        if not title:
            continue
        products.append({
            "product_id": str(row[resolved["product_id"]]) if resolved["product_id"] and pd.notna(row[resolved["product_id"]]) else f"kaggle-{i}",
            "title": title,
            "category": str(row[resolved["category"]]) if resolved["category"] and pd.notna(row[resolved["category"]]) else "",
            "price": _format_inr(row[resolved["price"]]) if resolved["price"] else None,
            "description": str(row[resolved["description"]]) if resolved["description"] and pd.notna(row[resolved["description"]]) else "",
            "url": str(row[resolved["url"]]) if resolved["url"] and pd.notna(row[resolved["url"]]) else "",
            "image_url": _first_image_url(row[resolved["image_url"]]) if resolved["image_url"] else "",
        })
    return products
