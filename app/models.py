# app/models.py
from pydantic import BaseModel, Field
from typing import Optional
import uuid

class AskRequest(BaseModel):
    """Corps de la requête POST /ask."""
    question: str = Field(
        ...,
        min_length=5,
        max_length=1000,
        description="La question à poser à l’agent"
    )
    session_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="ID de session pour la mémoire (auto-généré si absent)"
    )
    api_key: str = Field(
        ...,
        description="Clé d’API pour l’authentification"
    )

class Source(BaseModel):
    """Source citée dans la réponse."""
    source: str
    score: float

class AskResponse(BaseModel):
    """Corps de la réponse POST /ask."""
    answer: str
    sources: list[Source]
    session_id: str
    latency_ms: float

class IndexRequest(BaseModel):
    """Corps de la requête POST /index (indexer un document)."""
    text: str = Field(..., min_length=50)
    doc_id: str
    title: str
    api_key: str

class StatsResponse(BaseModel):
    """Réponse du tableau de bord GET /stats."""
    period_hours: int
    total_requests: int
    blocked_requests: int
    block_rate_pct: float
    avg_latency_ms: float
    p95_latency_ms: float
    total_tokens_used: int