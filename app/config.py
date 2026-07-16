import os
from dotenv import load_dotenv

load_dotenv()


def _clean(value: str) -> str:
    """Defensively strip stray quotes/whitespace that sometimes end up in
    .env values when editing by hand (a very common source of confusing
    'invalid API key' style errors)."""
    if value is None:
        return ""
    v = value.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
        v = v[1:-1].strip()
    return v


def _clean_url(value: str) -> str:
    v = _clean(value)
    if v and not v.startswith("http://") and not v.startswith("https://"):
        v = "https://" + v
    return v.rstrip("/")


class Settings:
    # Groq
    GROQ_API_KEY: str = _clean(os.getenv("GROQ_API_KEY", ""))
    # Web fallback (for products not in our catalog)
    GOOGLE_API_KEY: str = _clean(os.getenv("GOOGLE_API_KEY", ""))
    GOOGLE_CSE_ID: str = _clean(os.getenv("GOOGLE_CSE_ID", ""))
    PEXELS_API_KEY: str = _clean(os.getenv("PEXELS_API_KEY", ""))
    SERPER_API_KEY: str = _clean(os.getenv("SERPER_API_KEY", ""))
    GROQ_MODEL: str = _clean(os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"))
    GROQ_TEMPERATURE: float = float(_clean(os.getenv("GROQ_TEMPERATURE", "0.1")) or "0.1")
    GROQ_MAX_TOKENS: int = int(_clean(os.getenv("GROQ_MAX_TOKENS", "800")) or "800")

    # Weaviate Cloud
    WEAVIATE_CLOUD_URL: str = _clean_url(os.getenv("WEAVIATE_CLOUD_URL", ""))
    WEAVIATE_CLOUD_API_KEY: str = _clean(os.getenv("WEAVIATE_CLOUD_API_KEY", ""))
    COLLECTION_NAME: str = "ProductChunk"

    # Chunking / retrieval
    CHUNK_SIZE: int = int(_clean(os.getenv("CHUNK_SIZE", "300")) or "300")
    CHUNK_OVERLAP: int = int(_clean(os.getenv("CHUNK_OVERLAP", "50")) or "50")
    TOP_K: int = int(_clean(os.getenv("TOP_K", "10")) or "10")
    SIMILARITY_THRESHOLD: float = float(_clean(os.getenv("SIMILARITY_THRESHOLD", "0.3")) or "0.3")

    # Feedback log
    FEEDBACK_LOG_PATH: str = os.path.join(os.path.dirname(__file__), "..", "feedback_log.jsonl")

    # Product catalog cache (for the storefront grid)
    PRODUCTS_CATALOG_PATH: str = os.path.join(os.path.dirname(__file__), "..", "data", "products.json")


settings = Settings()
