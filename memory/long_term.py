import logging
from pathlib import Path
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)

class LongTermMemory:
    """
    Mémoire Épisodique de JARVIS.
    Stocke les résumés de conversation sous forme vectorielle pour la recherche par similarité (RAG).
    Utilise ChromaDB et le modèle d'embedding 'paraphrase-multilingual-MiniLM-L12-v2'.
    
    Intègre un seuil de similarité (distance_threshold) pour rejeter les documents
    non pertinents et éviter la pollution du contexte LLM.
    """

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = str(db_path)
        
        # Initialisation du client ChromaDB local
        self.client = chromadb.PersistentClient(
            path=self.db_path,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Initialisation de la fonction d'embedding (s'exécute localement)
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="paraphrase-multilingual-MiniLM-L12-v2"
        )
        
        # Récupération ou création de la collection
        self.collection_name = "jarvis_memories"
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_fn,
            metadata={"description": "JARVIS long-term episodic memory"}
        )
        
        logger.info(f"[LongTermMemory] ChromaDB initialisé dans {self.db_path}. "
                    f"Collection '{self.collection_name}' a {self.collection.count()} éléments.")

    def add_memory(self, memory_id: str, summary: str, metadata: dict = None) -> None:
        """
        Ajoute un résumé de session dans la base de données vectorielle.
        
        Args:
            memory_id: Un identifiant unique (ex: UUID ou Chroma ID).
            summary: Le texte du résumé généré par le LLM.
            metadata: Dictionnaire de métadonnées optionnelles (ex: date, topics).
        """
        if not metadata:
            metadata = {}
            
        self.collection.add(
            documents=[summary],
            metadatas=[metadata],
            ids=[memory_id]
        )
        logger.debug(f"[LongTermMemory] Mémoire '{memory_id}' ajoutée.")

    def query_relevant_memories(
        self, 
        query_text: str, 
        top_k: int = 3, 
        distance_threshold: float = 1.2
    ) -> list[dict]:
        """
        Recherche les mémoires les plus pertinentes par rapport au texte fourni.
        
        Applique un seuil de distance pour rejeter les résultats non pertinents.
        ChromaDB utilise la distance L2 par défaut : 
        - 0.0 = identique
        - < 1.0 = très similaire
        - 1.0-1.5 = potentiellement pertinent
        - > 1.5 = probablement non pertinent
        
        Args:
            query_text: La requête de l'utilisateur (ou contexte récent).
            top_k: Nombre de résultats à retourner.
            distance_threshold: Distance maximale acceptable (défaut 1.2).
                                Les documents plus éloignés sont rejetés.
            
        Returns:
            Une liste de dictionnaires contenant 'id', 'summary', 'metadata', 'distance'.
        """
        if self.collection.count() == 0:
            return []

        results = self.collection.query(
            query_texts=[query_text],
            n_results=min(top_k, self.collection.count()),
            include=["documents", "metadatas", "distances"]
        )
        
        memories = []
        if results and results["documents"] and len(results["documents"]) > 0:
            docs = results["documents"][0]
            metadatas = results["metadatas"][0] if results["metadatas"] else [{}] * len(docs)
            ids = results["ids"][0]
            distances = results["distances"][0] if results.get("distances") else [0.0] * len(docs)
            
            for doc, meta, doc_id, distance in zip(docs, metadatas, ids, distances):
                # Filtrage par seuil de similarité
                if distance > distance_threshold:
                    logger.info(
                        f"[LongTermMemory] Document rejeté (distance={distance:.3f} > seuil={distance_threshold}) : "
                        f"'{doc[:80]}...' — NON PERTINENT pour la requête '{query_text[:50]}'"
                    )
                    continue
                    
                memories.append({
                    "id": doc_id,
                    "summary": doc,
                    "metadata": meta,
                    "distance": distance
                })
                logger.debug(
                    f"[LongTermMemory] Document accepté (distance={distance:.3f}) : '{doc[:60]}...'"
                )
                
        logger.info(
            f"[LongTermMemory] Requête '{query_text[:50]}' → "
            f"{len(memories)} mémoire(s) pertinente(s) retournée(s) "
            f"(seuil: {distance_threshold})"
        )
        return memories
