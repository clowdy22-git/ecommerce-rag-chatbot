"""
Run this once (and whenever your catalog changes) to populate Weaviate.

Usage:
    python scripts/ingest.py --source scrape
    python scripts/ingest.py --source kaggle --csv path/to/products.csv
    python scripts/ingest.py --source both --csv path/to/products.csv
"""
import argparse
import json
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.chunking import chunk_text, build_product_document
from app.vector_store import upsert_chunks, ensure_collection
from app.data_ingestion.scraper import scrape_products
from app.data_ingestion.kaggle_loader import load_kaggle_csv
from app.config import settings


def save_products_catalog(products: list, max_items: int = 60):
    seen_titles = set()
    catalog = []
    for p in products:
        title = p.get("title", "").strip()
        if not title or title in seen_titles:
            continue
        if not p.get("image_url"):
            continue
        seen_titles.add(title)
        catalog.append({
            "title": title,
            "price": p.get("price") or "",
            "image_url": p.get("image_url", ""),
            "url": p.get("url", ""),
            "category": p.get("category", ""),
        })
        if len(catalog) >= max_items:
            break

    os.makedirs(os.path.dirname(settings.PRODUCTS_CATALOG_PATH), exist_ok=True)
    with open(settings.PRODUCTS_CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(catalog)} products to {settings.PRODUCTS_CATALOG_PATH}")


def products_to_chunk_records(products: list) -> list:
    records = []
    for product in products:
        doc = build_product_document(product)
        pieces = chunk_text(doc)
        for piece in pieces:
            records.append({
                "text": piece,
                "product_id": product.get("product_id", ""),
                "product_title": product.get("title", ""),
                "category": product.get("category", ""),
                "url": product.get("url", ""),
                "image_url": product.get("image_url", ""),
                "price": product.get("price", "") or "",
            })
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["scrape", "kaggle", "both"], default="scrape")
    parser.add_argument("--csv", help="Path to Kaggle CSV (required if source=kaggle/both)")
    parser.add_argument("--max-products", type=int, default=5000)
    args = parser.parse_args()

    products = []

    if args.source in ("scrape", "both"):
        print("Scraping demo products...")
        try:
            scraped = scrape_products(max_products=args.max_products)
            print(f"  -> got {len(scraped)} products from scraping")
            products.extend(scraped)
        except Exception as e:
            print(f"  scraping failed ({e}); continuing with other sources if any")

    if args.source in ("kaggle", "both"):
        if not args.csv:
            print("--csv is required for source=kaggle/both")
        else:
            print(f"Loading Kaggle CSV: {args.csv}")
            kaggle_products = load_kaggle_csv(args.csv, max_rows=args.max_products)
            print(f"  -> got {len(kaggle_products)} products from CSV")
            products.extend(kaggle_products)

    if not products:
        print("No products loaded from any source. Nothing to ingest.")
        return

    print(f"Total products: {len(products)}. Saving product catalog for storefront display...")
    save_products_catalog(products)

    print("Chunking...")
    records = products_to_chunk_records(products)
    print(f"Total chunks: {len(records)}. Ensuring Weaviate collection exists...")
    ensure_collection()

    print("Upserting into Weaviate (it embeds the text server-side, no local model needed)...")
    upsert_chunks(records)
    print("Done. Your chatbot's knowledge base is ready.")


if __name__ == "__main__":
    main()
