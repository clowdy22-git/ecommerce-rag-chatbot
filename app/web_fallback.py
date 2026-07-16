import requests
from app.config import settings


def _get_pexels_image(query: str) -> str:
    if not settings.PEXELS_API_KEY:
        return ""
    try:
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": settings.PEXELS_API_KEY},
            params={"query": query, "per_page": 1},
            timeout=10,
        )
        resp.raise_for_status()
        photos = resp.json().get("photos", [])
        if photos:
            return photos[0]["src"]["medium"]
    except Exception:
        pass
    return ""


def search_web_products(query: str, max_results: int = 3) -> list:
    """Search the web for a product our catalog doesn't have, via Serper.dev."""
    if not settings.SERPER_API_KEY:
        return []

    try:
        resp = requests.post(
            "https://google.serper.dev/search",
            headers={
                "X-API-KEY": settings.SERPER_API_KEY,
                "Content-Type": "application/json",
            },
            json={"q": f"buy {query} price", "gl": "in"},
            timeout=10,
        )
        resp.raise_for_status()
        items = resp.json().get("organic", [])[:max_results]
    except Exception:
        return []

    fallback_image = _get_pexels_image(query)

    return [
        {
            "title": item.get("title", ""),
            "url": item.get("link", ""),
            "snippet": item.get("snippet", ""),
            "image_url": fallback_image,
        }
        for item in items
    ]