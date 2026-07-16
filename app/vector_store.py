"""
Vector store layer - uses Weaviate's own hosted embedding service
(text2vec-weaviate), which is enabled by default on Weaviate Cloud Sandbox
clusters. This means NO local embedding library (no PyTorch, no multi-GB
downloads, no Windows path-length issues) - Weaviate embeds text for us,
both at insert time and query time.

If you created your Weaviate Cloud cluster a while ago and text2vec-weaviate
isn't enabled, the easiest fix is to spin up a fresh free Sandbox cluster
(they come with it enabled by default) and update WEAVIATE_CLOUD_URL /
WEAVIATE_CLOUD_API_KEY in .env.
"""
from app.web_fallback import _get_pexels_image
import uuid
from typing import List, Dict, Optional

import weaviate
import weaviate.classes as wvc

from app.config import settings

_client = None


def get_client():
    global _client
    if _client is not None:
        return _client

    _client = weaviate.connect_to_weaviate_cloud(
        cluster_url=settings.WEAVIATE_CLOUD_URL,
        auth_credentials=weaviate.auth.AuthApiKey(settings.WEAVIATE_CLOUD_API_KEY),
        skip_init_checks=True,
    )
    return _client


def close_client():
    global _client
    if _client is not None:
        _client.close()
        _client = None


def ensure_collection():
    client = get_client()
    if client.collections.exists(settings.COLLECTION_NAME):
        return
    client.collections.create(
        name=settings.COLLECTION_NAME,
        vectorizer_config=wvc.config.Configure.Vectorizer.text2vec_weaviate(),
        properties=[
            wvc.config.Property(name="text", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="product_id", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="product_title", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="category", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="url", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="image_url", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="price", data_type=wvc.config.DataType.TEXT),
        ],
    )


def upsert_chunks(records: List[Dict]):
    """
    records: list of dicts with keys: text, product_id, product_title,
    category, url, image_url, price. Weaviate embeds `text` automatically.
    """
    ensure_collection()
    client = get_client()
    collection = client.collections.get(settings.COLLECTION_NAME)

    with collection.batch.dynamic() as batch:
        for record in records:
            batch.add_object(
                properties={
                    "text": record["text"],
                    "product_id": record.get("product_id", ""),
                    "product_title": record.get("product_title", ""),
                    "category": record.get("category", ""),
                    "url": record.get("url", ""),
                    "image_url": record.get("image_url", ""),
                    "price": record.get("price", "") or "",
                },
                uuid=uuid.uuid4(),
            )


def similarity_search(query: str, top_k: int = None) -> List[Dict]:
    """
    Returns list of {text, product_title, category, url, image_url, price, similarity}
    similarity is in [0, 1] (1 = closest match), derived from Weaviate's
    returned distance for near_text queries.
    """
    top_k = top_k or settings.TOP_K
    client = get_client()
    ensure_collection()
    collection = client.collections.get(settings.COLLECTION_NAME)

    response = collection.query.near_text(
        query=query,
        limit=top_k,
        return_metadata=wvc.query.MetadataQuery(distance=True),
    )

    hits = []
    for obj in response.objects:
        distance = obj.metadata.distance if obj.metadata.distance is not None else 1.0
        similarity = max(0.0, 1.0 - distance)
        title = obj.properties.get("product_title", "")
        original_image = obj.properties.get("image_url", "")

        # Flipkart's old CDN (flixcart.com) is largely dead - fall back to Pexels
        image_url = original_image
        if not image_url or "flixcart.com" in image_url:
            image_url = _get_pexels_image(title)

        hits.append({
            "text": obj.properties.get("text", ""),
            "product_title": title,
            "category": obj.properties.get("category", ""),
            "url": obj.properties.get("url", ""),
            "image_url": image_url,
            "price": obj.properties.get("price", ""),
            "similarity": round(similarity, 4),
        })
    return hits