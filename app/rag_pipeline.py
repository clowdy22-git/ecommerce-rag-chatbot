_CATALOG_FORCE_KEYWORDS = [
    "cheapest", "cheap", "under ", "below ", "less than",
    "budget", "affordable", "lowest price", "here", "you have",
    "you sell", "your store", "in stock",
]


def _force_catalog_mode(query: str) -> bool:
    q = query.lower()
    return any(kw in q for kw in _CATALOG_FORCE_KEYWORDS)
import uuid
from groq import Groq

from app.config import settings
from app.vector_store import similarity_search
from app.guardrails import SYSTEM_PROMPT, REFUSAL_MESSAGE, build_context, is_in_domain
from app.web_fallback import search_web_products

_NO_INFO_PHRASES = [
    "don't have that information",
    "don't have this information",
    "do not have that information",
    "do not have this information",
    "no information about",
    "couldn't find any information",
    "could not find any information",
    "contact support for",
    "i don't have specific",
    "i don't have details",
]


def _is_real_answer(answer: str) -> bool:
    lowered = answer.lower()
    return not any(phrase in lowered for phrase in _NO_INFO_PHRASES)

_groq_client = None


def get_groq_client() -> Groq:
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=settings.GROQ_API_KEY)
    return _groq_client


def is_shopping_related(query: str) -> bool:
    """Fast classification: is this a product/shopping question at all
    (even for something we don't stock), vs unrelated chit-chat?"""
    client = get_groq_client()
    try:
        completion = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            temperature=0,
            max_tokens=5,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Reply with exactly one word: YES or NO. Is the user's "
                        "message asking about buying, finding, comparing, or "
                        "getting info on a physical product (even one this store "
                        "doesn't sell)? Say NO for anything unrelated to shopping."
                    ),
                },
                {"role": "user", "content": query},
            ],
        )
        return completion.choices[0].message.content.strip().upper().startswith("Y")
    except Exception:
        return False


def build_web_answer(query: str, web_results: list) -> str:
    context = "\n".join(
        f"- {r['title']}: {r['snippet']} ({r['url']})" for r in web_results
    ) or "(no results found)"

    prompt = (
        "You are a shopping assistant. The user asked about a product this "
        "store does not carry. Using ONLY the web results below, write a "
        "short, honest 2-3 sentence answer. Clearly say this item isn't sold "
        "by our store, but share what you found online. Never invent details "
        f"not present below.\n\nWEB RESULTS:\n{context}"
    )

    client = get_groq_client()
    completion = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        temperature=settings.GROQ_TEMPERATURE,
        max_tokens=settings.GROQ_MAX_TOKENS,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": query},
        ],
    )
    return completion.choices[0].message.content.strip()


def answer_query(query: str) -> dict:
    message_id = str(uuid.uuid4())

    chunks = similarity_search(query, top_k=settings.TOP_K)
    confidence = round(chunks[0]["similarity"], 4) if chunks else 0.0
    in_catalog = is_in_domain(chunks, settings.SIMILARITY_THRESHOLD) or (
        _force_catalog_mode(query) and len(chunks) > 0
    )

    # 1. Strong catalog match -> answer from our own product data
    if in_catalog:
        context = build_context(chunks)
        system_prompt = SYSTEM_PROMPT.format(context=context)

        client = get_groq_client()
        completion = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            temperature=settings.GROQ_TEMPERATURE,
            max_tokens=settings.GROQ_MAX_TOKENS,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
        )
        answer = completion.choices[0].message.content.strip()

        sources = [
            {
                "text": c["text"],
                "product_title": c["product_title"],
                "similarity": c["similarity"],
                "image_url": c.get("image_url", ""),
                "price": c.get("price", ""),
                "url": c.get("url", ""),
                "is_web": False,
            }
            for c in chunks
        ]

        return {
            "answer": answer,
            "confidence": confidence,
            "in_domain": True,
            "has_answer": False,
            "sources": sources,
            "message_id": message_id,
            "answer_source": "catalog",
        }
        
    # 2. Not in our catalog - is it even a shopping question?
    if not is_shopping_related(query):
        return {
            "answer": REFUSAL_MESSAGE,
            "confidence": confidence,
            "in_domain": False,
            "sources": [],
            "message_id": message_id,
            "answer_source": "refused",
        }

    # 3. Shopping-related but not in our catalog -> web fallback
    web_results = search_web_products(query)
    if not web_results:
        return {
            "answer": (
                "We don't carry that item, and I couldn't find anything "
                "online just now either. Could you try rephrasing, or ask "
                "about something else we might stock?"
            ),
            "confidence": confidence,
            "in_domain": False,
            "sources": [],
            "message_id": message_id,
            "answer_source": "web_empty",
        }

    answer = build_web_answer(query, web_results)
    sources = [
        {
            "text": r["snippet"],
            "product_title": r["title"],
            "similarity": 0.0,
            "image_url": r.get("image_url", ""),
            "price": "",
            "url": r.get("url", ""),
            "is_web": True,
        }
        for r in web_results
    ]

    return {
        "answer": answer,
        "confidence": confidence,
        "in_domain": True,
        "has_answer": False,
        "sources": sources,
        "message_id": message_id,
        "answer_source": "web",
    }