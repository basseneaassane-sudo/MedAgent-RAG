# app/vector_store.py
import chromadb
from chromadb.utils import embedding_functions
from pathlib import Path
from app.config import settings
#from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_text_splitters import RecursiveCharacterTextSplitter
import fitz  # PyMuPDF pour lire les PDF

# AXE 1 : Modèle d'embedding multilingue (bien meilleur pour le français médical)
# all-MiniLM-L6-v2 est anglais. On passe sur un modèle qui comprend le français.
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

def get_chroma_client():
    """Client ChromaDB persistant sur disque."""
    return chromadb.PersistentClient(path=settings.chroma_persist_dir)


def get_collection():
    """Retourne (ou crée) la collection de documents médicaux."""
    client = get_chroma_client()
    embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )
    return client.get_or_create_collection(
        name="medical_papers",
        embedding_function=embedding_func,
        metadata={"hnsw:space": "cosine"}
    )


def index_document(text: str, doc_id: str, metadata: dict = {}):
    """
    Indexe un document dans ChromaDB.
    AXE 2 : Utilise un découpage sémantique (RecursiveCharacterTextSplitter).
    Il coupe aux points et aux paragraphes en priorité pour ne pas couper les phrases.
    """
    collection = get_collection()
    
    # Configuration du découpage intelligent
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,      # ~200-250 mots par chunk
        chunk_overlap=100,    # Chevauchement pour garder le contexte
        separators=["\n\n", "\n", ". ", " ", ""] # Priorité de découpe
    )
    
    chunks_text = text_splitter.split_text(text)
    
    chunks, ids, metadatas = [], [], []

    for i, chunk in enumerate(chunks_text):
        if len(chunk.strip()) > 50:  # ignorer les chunks trop courts
            chunk_id = f"{doc_id}_chunk_{i}"
            chunks.append(chunk)
            ids.append(chunk_id)
            metadatas.append({
                **metadata,
                "chunk_index": i,
                "doc_id": doc_id
            })

    if chunks:
        collection.add(documents=chunks, ids=ids, metadatas=metadatas)
        print(f"Indexé {len(chunks)} chunks pour '{doc_id}'")
    return len(chunks)


def search_similar(query: str, n_results: int = 3) -> list:
    """
    Recherche les passages les plus proches sémantiquement.
    Retourne une liste de dicts : {text, source, score}.
    """
    collection = get_collection()

    if collection.count() == 0:
        return [{"text": "Aucun document indexé.", "source": "system", "score": 0.0}]

    results = collection.query(
        query_texts=[query],
        n_results=min(n_results, collection.count()),
        include=["documents", "metadatas", "distances"]
    )

    return [
        {
            "text": doc,
            "source": meta.get("title", meta.get("doc_id", "inconnu")),
            "score": round(1 - dist, 3)
        }
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        )
    ]


def index_your_papers() -> int:
    """
    Indexe tous les fichiers .txt et .pdf du dossier data/articles/.
    AXE 3 : Gestion native des PDF via PyMuPDF (fitz).
    """
    articles_dir = Path("data/articles")
    articles_dir.mkdir(parents=True, exist_ok=True)

    indexed = 0
    for filepath in articles_dir.glob("*.*"):
        text = ""
        doc_id = filepath.stem  # nom du fichier sans extension
        
        # Lecture selon l'extension
        if filepath.suffix == ".txt":
            text = filepath.read_text(encoding="utf-8")
        elif filepath.suffix == ".pdf":
            try:
                doc = fitz.open(filepath)
                # Extraire le texte de chaque page
                text = "\n".join([page.get_text() for page in doc])
                doc.close()
            except Exception as e:
                print(f"Erreur lors de la lecture du PDF {filepath.name}: {e}")
                continue
        else:
            continue # Ignorer les autres formats

        if text:
            indexed += index_document(
                text, doc_id,
                {"title": doc_id.replace("_", " "), "type": "research_paper"}
            )

    print(f"Indexation terminée : {indexed} chunks dans {len(list(articles_dir.glob('*.*')))} fichiers.")
    return indexed


# Test rapide
if __name__ == "__main__":
    index_document(
        "La drépanocytose est une maladie génétique du globule rouge. "
        "YOLOv8 permet la détection automatique sur images microscopiques. "
        "DREPADetect a été accepté à MICCAI 2025. ",
        doc_id="test_drepanocytose",
        metadata={"title": "DREPADetect Test", "year": "2025"}
    )
    results = search_similar("détection drépanocytose YOLOv8")
    print("\nRésultats de recherche sémantique :")
    for r in results:
        print(f"[{r['score']}] {r['source']}:")
        print(f"  {r['text'][:120]}...")


#**************version précedente fonctionnelle********************
'''import chromadb
from chromadb.utils import embedding_functions
from pathlib import Path
from app.config import settings

# Modèle d’embedding : léger (150 MB), performant, gratuit et local
# ATTENTION : le nom du modèle ne doit pas contenir d'espaces
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def get_chroma_client():
    """Client ChromaDB persistant sur disque."""
    return chromadb.PersistentClient(path=settings.chroma_persist_dir)


def get_collection():
    """Retourne (ou crée) la collection de documents médicaux."""
    client = get_chroma_client()
    embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )
    return client.get_or_create_collection(
        name="medical_papers",  # Retiré les espaces autour du nom
        embedding_function=embedding_func,
        metadata={"hnsw:space": "cosine"}  # similarité cosinus
    )


def index_document(text: str, doc_id: str, metadata: dict = None):
    """
    Indexe un document dans ChromaDB.
    Découpe le texte en chunks de 500 mots avec chevauchement de 50 mots.
    """
    # Bonne pratique : éviter les arguments mutables par défaut (= {})
    metadata = metadata or {}
    
    collection = get_collection()
    words = text.split()
    chunk_size = 500
    overlap = 50
    chunks, ids, metadatas = [], [], []

    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i : i + chunk_size])
        if len(chunk.strip()) > 50:  # ignorer les chunks trop courts
            chunk_id = f"{doc_id}_chunk_{i}"
            chunks.append(chunk)
            ids.append(chunk_id)
            metadatas.append({
                **metadata,
                "chunk_index": i,
                "doc_id": doc_id
            })

    if chunks:
        collection.add(documents=chunks, ids=ids, metadatas=metadatas)
        print(f"Indexé {len(chunks)} chunks pour '{doc_id}'")
    return len(chunks)


def search_similar(query: str, n_results: int = 3) -> list:
    """
    Recherche les passages les plus proches sémantiquement.
    Retourne une liste de dicts : {text, source, score}.
    """
    collection = get_collection()

    # Note : Dans les versions récentes de ChromaDB, c'est collection.count (sans parenthèses)
    if collection.count() == 0:
        return [{"text": "Aucun document indexé.", "source": "system", "score": 0.0}]

    results = collection.query(
        query_texts=[query],
        n_results=min(n_results, collection.count()),
        include=["documents", "metadatas", "distances"]
    )

    return [
        {
            "text": doc,
            "source": meta.get("title", meta.get("doc_id", "inconnu")),
            "score": round(1 - dist, 3)  # distance cosine -> similarité
        }
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        )
    ]


def index_your_papers() -> int:
    """
    Indexe tous les fichiers .txt du dossier data/articles/.
    Copiez vos articles (copiez le texte de vos PDFs) dans ce dossier.
    """
    articles_dir = Path("data/articles")  # Retiré les espaces
    articles_dir.mkdir(parents=True, exist_ok=True)

    indexed = 0
    for filepath in articles_dir.glob("*.txt"):  # Retiré les espaces
        text = filepath.read_text(encoding="utf-8")
        doc_id = filepath.stem # nom du fichier sans extension
        indexed += index_document(
            text, doc_id,
            {"title": doc_id.replace("_", " "), "type": "research_paper"}
        )

    print(f"Indexation terminée : {indexed} chunks dans {len(list(articles_dir.glob('*.txt')))} articles.")
    return indexed


# Test rapide
if __name__ == "__main__":
    # Indexer un court exemple
    index_document(
        "La drépanocytose est une maladie génétique du globule rouge. "
        "YOLOv8 permet la détection automatique sur images microscopiques. "
        "DREPADetect a été accepté à MICCAI 2025.",
        doc_id="test_drepanocytose",
        metadata={"title": "DREPADetect Test", "year": "2025"}
    )
    # Rechercher
    results = search_similar("détection drépanocytose YOLOv8")
    print("\nRésultats de recherche sémantique :")
    for r in results:
        print(f"[{r['score']}] {r['source']} :")
        print(f"  {r['text'][:120]}... ")'''