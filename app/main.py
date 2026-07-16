import json
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.models import ChatRequest, ChatResponse, FeedbackRequest
from app.rag_pipeline import answer_query
from app.feedback import save_feedback, feedback_stats
from app.vector_store import close_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    close_client()


app = FastAPI(title="E-commerce RAG Chatbot API", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/products")
def get_products():
    path = settings.PRODUCTS_CATALOG_PATH
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not settings.GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not configured on the server.")
    try:
        result = answer_query(req.query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return result


@app.post("/feedback")
def feedback(req: FeedbackRequest):
    record = save_feedback(req)
    return {"status": "saved", "record": record}


@app.get("/feedback/stats")
def feedback_stats_endpoint():
    return feedback_stats()


# Serve the storefront widget + demo page from the SAME origin as the API.
# This means no CORS, no separate frontend server, no file:// browser
# restrictions - just open http://localhost:8000/ once uvicorn is running.
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
