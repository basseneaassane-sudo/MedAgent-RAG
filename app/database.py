# app/database.py
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float
#from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from app.config import settings

# Connexion au moteur PostgreSQL
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # vérifie la connexion avant chaque requête
    pool_size=5,         # 5 connexions simultanées max
    max_overflow=10
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Conversation(Base):
    """Table stockant l'historique des conversations."""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), index=True, nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    sources = Column(Text)  # JSON sérialisé
    created_at = Column(DateTime, default=datetime.utcnow)


class RequestLog(Base):
    """Table de monitoring : latence, tokens, blocages."""
    __tablename__ = "request_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100))
    latency_ms = Column(Float)  # temps de réponse en ms
    tokens_used = Column(Integer, default=0)
    blocked = Column(Integer, default=0)  # 1 si bloqué par sécurité
    reason = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)


def create_tables():
    """Crée toutes les tables si elles n'existent pas."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Générateur de session utilisé par FastAPI via Depends()."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Test rapide : python -m app.database
if __name__ == "__main__":
    create_tables()
    print("Tables créées avec succès dans PostgreSQL !")