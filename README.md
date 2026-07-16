# 🛍️ E-commerce RAG Chatbot

A retrieval-augmented shopping assistant that answers questions about a store's actual product catalog — and knows when to say "we don't carry that." Built as a portfolio project to demonstrate a production-style RAG pipeline: chunking, vector similarity search, grounded generation, confidence scoring, and a live web-search fallback for out-of-catalog queries.

Ask it "waistcoat price" and it answers from real product data. Ask it "best headphones" — a category the demo catalog doesn't stock — and it honestly says so, then offers what it found online instead. Ask it "what's the capital of France" and it politely declines, because it's scoped to this store only.

## Why this project

Most RAG demos stop at "retrieve chunks, ask an LLM." This one tackles the harder, more realistic problems:

- **Staying on-topic** — a two-layer guardrail (embedding similarity + LLM intent classification) keeps the bot from answering anything outside shopping, without relying on the system prompt alone.
- **Being honest about gaps** — rather than hallucinating a product that doesn't exist, low-confidence catalog matches trigger a live web search, clearly labeled as "found online" rather than blended into store inventory.
- **Measuring itself** — every answer ships with a confidence score, and a 👍/👎 feedback loop logs ratings against that score — the beginning of a real evaluation dataset, not just a demo toy.

## Features

- 🔍 **Semantic product search** over a ~5,000-product Flipkart catalog, chunked and embedded via Weaviate's hosted vectorizer
- 🎯 **Domain guardrail** — refuses off-topic questions, stays scoped to store/product/shipping/returns
- 🌐 **Live web fallback** — when the catalog has no match but the question is still shopping-related, falls back to Serper (Google search) + Pexels for a generic product image, visibly tagged "🌐 Online"
- 📊 **Confidence scoring** on every response, surfaced in the UI
- 👍👎 **Feedback logging** — ratings are only collected on genuine answers, not "I don't have that information" responses
- 💬 **Embeddable widget** — a self-contained chat bubble (vanilla JS, no framework) that drops into any storefront with a single `<script>` tag
- 🛒 **Demo storefront** included, with category filtering, to show the widget in a realistic e-commerce context

## Architecture

```
Customer message
      │
      ▼
Search product catalog (Weaviate embedding search)
      │
      ├── Confident match ──────────► Answer from catalog (Groq + product data)
      │
      ├── No match, but shopping ───► Search the web (Serper + Pexels)
      │
      └── Not shopping-related ─────► Politely decline
```

The routing decision uses **both** a similarity threshold and a fast secondary LLM classification — not similarity alone — since embedding similarity can't reliably distinguish "off-topic" from "on-topic but simply not in stock."

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI |
| LLM | Groq (`llama-3.3-70b-versatile`), temperature 0.1 |
| Vector DB | Weaviate Cloud (free sandbox), hosted `text2vec-weaviate` vectorizer |
| Web fallback | Serper.dev (Google search API) |
| Images | Pexels API |
| Product data | [Flipkart e-commerce sample dataset](https://www.kaggle.com/datasets/PromptCloudHQ/flipkart-products) (Kaggle) |
| Frontend | Vanilla HTML/CSS/JS, served same-origin from FastAPI (no CORS, no build step) |

## Project structure

```
backend/
├── app/
│   ├── main.py            # FastAPI routes: /chat, /products, /feedback
│   ├── config.py          # settings loaded from .env
│   ├── models.py          # Pydantic request/response schemas
│   ├── vector_store.py     # Weaviate client, embed + similarity search
│   ├── guardrails.py       # system prompt, refusal message, domain check
│   ├── rag_pipeline.py     # core routing logic (catalog / web / refuse)
│   ├── web_fallback.py     # Serper + Pexels integration
│   ├── feedback.py         # feedback logging
│   └── data_ingestion/     # Kaggle CSV loader + scraper
├── scripts/
│   └── ingest.py           # CLI: chunk + embed + upload to Weaviate
├── static/
│   ├── index.html          # demo storefront
│   ├── widget.js            # embeddable chat widget
│   └── widget.css
├── requirements.txt
└── .env.example
```

## Setup

**Requirements:** Python 3.11+ recommended, a free [Weaviate Cloud](https://console.weaviate.cloud) sandbox, a [Groq](https://console.groq.com) API key, and optionally [Serper](https://serper.dev) + [Pexels](https://www.pexels.com/api/) keys for the web fallback.

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in:

```
GROQ_API_KEY=
WEAVIATE_CLOUD_URL=
WEAVIATE_CLOUD_API_KEY=
SERPER_API_KEY=
PEXELS_API_KEY=
```

Ingest the product catalog (downloads are not automatic — grab the [Flipkart CSV from Kaggle](https://www.kaggle.com/datasets/PromptCloudHQ/flipkart-products) first):

```powershell
python scripts/ingest.py --source kaggle --csv "flipkart_com-ecommerce_sample.csv" --max-products 5000
```

Run the server:

```powershell
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000/`.

## Known limitations

- Broad browsing queries ("cheapest item," "under ₹500") rely on keyword-triggered catalog forcing rather than structured metadata filtering — a production version would filter on price/category fields directly in Weaviate.
- No multi-turn conversation memory — each message is handled independently, so follow-up questions like "any more options?" don't carry context yet.
- Product images depend on the original dataset's links (many are dead, from Flipkart's old CDN) with a Pexels fallback — not exact product photography.

## Roadmap

- [ ] Multi-turn conversation memory
- [ ] Structured price/category filtering for browsing-style queries
- [ ] Admin dashboard for feedback stats and low-confidence query review
- [ ] Streaming responses from Groq for a snappier widget feel

## License

MIT
