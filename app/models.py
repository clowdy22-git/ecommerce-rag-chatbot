from pydantic import BaseModel, Field
from typing import List, Optional


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    session_id: Optional[str] = "anonymous"


class SourceChunk(BaseModel):
    text: str
    product_title: str
    similarity: float
    image_url: Optional[str] = ""
    price: Optional[str] = ""
    url: Optional[str] = ""
    is_web: Optional[bool] = False


class ChatResponse(BaseModel):
    answer: str
    confidence: float
    in_domain: bool
    sources: List[SourceChunk]
    message_id: str
    answer_source: Optional[str] = "catalog"
    has_answer: Optional[bool] = True


class FeedbackRequest(BaseModel):
    message_id: str
    session_id: Optional[str] = "anonymous"
    query: str
    answer: str
    confidence: float
    rating: str = Field(..., pattern="^(up|down)$")
    comment: Optional[str] = None
