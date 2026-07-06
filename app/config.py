# app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict 

class Settings(BaseSettings):
    """
    Paramètres de configuration lus depuis le fichier .env.
    Pydantic valide automatiquement les types.
    """
    # Base de données
    database_url: str

    # LLM
    ollama_base_url: str = "http://localhost:11434"
    llm_model: str = "mistral"

    # ChromaDB
    chroma_persist_dir: str = "./chroma_db"

    # Sécurité
    api_key: str
    max_tokens_per_request: int = 500
    max_requests_per_minute: int = 20

    #class Config:
    #    env_file = ".env"
    #    env_file_encoding = "utf-8"
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

# Instance globale importée par tous les modules
settings = Settings()