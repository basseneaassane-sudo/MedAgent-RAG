# app/main.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import json

from app.models import AskRequest, AskResponse, IndexRequest, StatsResponse
from app.database import get_db, create_tables, Conversation
from app.agent import med_agent
from app.security import validate_request, verify_api_key
from app.monitoring import RequestTimer, log_request, get_dashboard_stats
from app.vector_store import index_document, index_your_papers

# INITIALISATION
app = FastAPI(
    title="MedAgent API",
    description="Agent RAG pour la recherche médicale sur la Drépanocytose",
    version="1.0.0",
    docs_url="/docs",  # interface Swagger sur http://localhost:8000/docs
    redoc_url="/redoc"
)

# Autoriser les appels depuis n’importe quel navigateur (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    """Initialise les tables PostgreSQL au démarrage de l’API."""
    create_tables()
    print("MedAgent API démarrée - PostgreSQL initialisé.")


# ROUTES

@app.get("/health")
def health_check():
    """
    Route de santé vérifier que l’API tourne.
    Appelée par les load balancers et les outils de monitoring.
    """
    return {"status": "ok", "version": "1.0.0"}


@app.post("/ask", response_model=AskResponse)
def ask_question(request: AskRequest, db: Session = Depends(get_db)):
    """
    Route principale : poser une question à l’agent MedAgent.
    L’agent cherche dans les articles indexés et répond avec les sources.
    """
    # Validation complète (API key + rate limit + longueur + injection)
    is_valid, error = validate_request(
        request.question, request.session_id, request.api_key
    )

    if not is_valid:
        # Logguer la tentative bloquée pour le monitoring
        log_request(db, request.session_id, 0, blocked=True, reason=error)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Requête refusée : {error}"
        )

    # Mesurer la latence totale
    with RequestTimer() as timer:
        result = med_agent.answer(request.question, request.session_id)

    # Estimation du nombre de tokens utilisés
    tokens_used = (len(request.question) + len(result["answer"])) // 4

    # Persister la conversation dans PostgreSQL
    conv = Conversation(
        session_id=request.session_id,
        question=request.question,
        answer=result["answer"],
        sources=json.dumps(result["sources"])
    )
    db.add(conv)
    db.commit()

    # Logger les métriques
    log_request(db, request.session_id, timer.latency_ms, tokens_used)

    return AskResponse(
        answer=result["answer"],
        sources=result["sources"],
        session_id=request.session_id,
        latency_ms=round(timer.latency_ms, 1)
    )


@app.get("/history/{session_id}")
def get_history(session_id: str, db: Session = Depends(get_db)):
    """Récupère l’historique complet d’une session de conversation."""
    conversations = (
        db.query(Conversation)
        .filter(Conversation.session_id == session_id)
        .order_by(Conversation.created_at)
        .all()
    )
    return [
        {
            "question": c.question,
            "answer": c.answer,
            "sources": json.loads(c.sources) if c.sources else [],
            "created_at": c.created_at.isoformat()
        }
        for c in conversations
    ]


@app.post("/index")
def index_document_route(request: IndexRequest, db: Session = Depends(get_db)):
    """Indexe un document dans ChromaDB via l’API."""
    if not verify_api_key(request.api_key):
        raise HTTPException(status_code=401, detail="API key invalide")

    index_document(request.text, request.doc_id, {"title": request.title})
    return {"message": f"Document '{request.doc_id}' indexé avec succès"}


@app.post("/index/papers")
def index_all_papers(api_key: str):
    """Indexe tous les articles du dossier data/articles/ (fichiers .txt)."""
    if not verify_api_key(api_key):
        raise HTTPException(status_code=401, detail="API key invalide")
    count = index_your_papers()
    return {"message": f"{count} chunks indexés depuis data/articles/"}


@app.get("/stats", response_model=StatsResponse)
def get_stats(api_key: str, hours: int = 24, db: Session = Depends(get_db)):
    """Tableau de bord monitoring : latence, tokens, taux de blocage."""
    if not verify_api_key(api_key):
        raise HTTPException(status_code=401, detail="API key invalide")
    return get_dashboard_stats(db, hours)


@app.delete("/session/{session_id}/memory")
def clear_session_memory(session_id: str, api_key: str):
    """Efface la mémoire de conversation d’une session."""
    if not verify_api_key(api_key):
        raise HTTPException(status_code=401, detail="API key invalide")
    med_agent.clear_memory(session_id)
    return {"message": f"Mémoire de la session '{session_id}' effacée"}