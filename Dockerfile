FROM python:3.11-slim

# Répertoire de travail dans le conteneur
WORKDIR /app

# Copier et installer les dépendances en premier
# (Docker met en cache cette couche si requirements.txt n'a pas changé)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code source
COPY . .

# Créer les dossiers nécessaires
RUN mkdir -p data/articles chroma_db

# Port exposé par le conteneur
EXPOSE 8000

# Variables d’environnement par défaut (surchargées par docker-compose)
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Commande de démarrage
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]