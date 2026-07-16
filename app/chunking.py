"""
Simple word-based sliding-window chunker.
"""
from typing import List
from app.config import settings


def chunk_text(text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
    chunk_size = chunk_size or settings.CHUNK_SIZE
    overlap = overlap or settings.CHUNK_OVERLAP

    words = text.split()
    if not words:
        return []

    if len(words) <= chunk_size:
        return [text.strip()]

    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words).strip())
        if end >= len(words):
            break
        start = end - overlap

    return [c for c in chunks if c]


def build_product_document(product: dict) -> str:
    parts = []
    if product.get("title"):
        parts.append(f"Product: {product['title']}")
    if product.get("category"):
        parts.append(f"Category: {product['category']}")
    if product.get("price") is not None:
        parts.append(f"Price: {product['price']}")
    if product.get("attributes"):
        parts.append(f"Attributes: {product['attributes']}")
    if product.get("description"):
        parts.append(f"Description: {product['description']}")
    return "\n".join(parts)
