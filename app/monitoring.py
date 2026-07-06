# app/monitoring.py
import time
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.database import RequestLog


class RequestTimer:
    """
    Context manager pour mesurer précisément la latence.
    Usage :
        with RequestTimer() as timer:
            result = do_something()
        print(timer.latency_ms) # en millisecondes
    """
    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.latency_ms = (time.perf_counter() - self.start) * 1000


def log_request(db: Session,
                session_id: str,
                latency_ms: float,
                tokens_used: int = 0,
                blocked: bool = False,
                reason: str = ""):
    """Enregistre les métriques d'une requête dans PostgreSQL."""
    log = RequestLog(
        session_id=session_id,
        latency_ms=latency_ms,
        tokens_used=tokens_used,
        blocked=1 if blocked else 0,
        reason=reason
    )
    db.add(log)
    db.commit()


def get_dashboard_stats(db: Session, hours: int = 24) -> dict:
    """
    Calcule les métriques clés pour le tableau de bord.
    Couvre les KPIs typiques d'une application IA en production :
    - latence (moyenne, P95)
    - taux de blocage (requêtes suspectes)
    - consommation de tokens
    """
    since = datetime.utcnow() - timedelta(hours=hours)
    logs = (db.query(RequestLog)
            .filter(RequestLog.created_at >= since)
            .all())

    if not logs:
        return {"message": "Aucune donnée", "period_hours": hours}

    total = len(logs)
    blocked = sum(1 for l in logs if l.blocked)
    valid = [l for l in logs if not l.blocked]
    latencies = sorted([l.latency_ms for l in valid]) if valid else [0]
    tokens = [l.tokens_used for l in valid] if valid else [0]

    p95_idx = int(len(latencies) * 0.95)

    return {
        "period_hours": hours,
        "total_requests": total,
        "successful_requests": len(valid),
        "blocked_requests": blocked,
        "block_rate_pct": round(blocked / total * 100, 1),
        "avg_latency_ms": round(sum(latencies) / len(latencies), 1),
        "max_latency_ms": round(max(latencies), 1),
        "p95_latency_ms": round(latencies[p95_idx], 1),
        "total_tokens_used": sum(tokens),
        "avg_tokens_per_request": round(sum(tokens) / len(tokens), 1),
    }