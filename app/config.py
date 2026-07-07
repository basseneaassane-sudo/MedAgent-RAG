# app/config.py
# app/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuration centralisée de l'application.
    Les valeurs sont lues depuis les variables d'environnement
    (fichier .env ou docker-compose.yml).
    """
    
    # Base de données (construite ou directe)
    database_url: str = "postgresql://medagent:medagent123@db:5432/medagentdb"
    
    # LLM Ollama
    ollama_base_url: str = "http://localhost:11434"
    llm_model: str = "qwen2.5:3b"
    
    # Sécurité
    api_key: str = "dev-key-change-me"
    
    # Limites
    max_tokens_per_request: int = 500
    max_requests_per_minute: int = 20
    
    # ChromaDB
    chroma_persist_dir: str = "./chroma_db"

    # Configuration Pydantic : lit le .env ET accepte les variables d'env
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # ← ignore les variables non déclarées
        env_prefix="",   # ← pas de préfixe requis
    )


# Instance singleton utilisée partout dans l'application
settings = Settings()


#************old working***************
'''from pydantic_settings import BaseSettings, SettingsConfigDict

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
settings = Settings()'''