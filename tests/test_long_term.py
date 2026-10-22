"""
Tests unitaires pour LongTermMemory (gestion des métadonnées vides et requêtes RAG).
"""
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

from memory.long_term import LongTermMemory


class TestLongTermMemory(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "chroma"

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("memory.long_term.chromadb.PersistentClient")
    @patch("memory.long_term.embedding_functions.SentenceTransformerEmbeddingFunction")
    def test_add_memory_with_empty_metadata_does_not_crash(self, mock_ef, mock_client_class):
        mock_collection = MagicMock()
        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_class.return_value = mock_client

        ltm = LongTermMemory(self.db_path)

        # Ajout avec metadata vide {} -> ne doit PAS envoyer [{}] à ChromaDB
        ltm.add_memory("id-1", "Résumé important", metadata={})

        mock_collection.add.assert_called_once_with(
            documents=["Résumé important"],
            metadatas=None,  # ChromaDB exige None si aucune métadonnée
            ids=["id-1"]
        )

    @patch("memory.long_term.chromadb.PersistentClient")
    @patch("memory.long_term.embedding_functions.SentenceTransformerEmbeddingFunction")
    def test_add_memory_with_valid_metadata(self, mock_ef, mock_client_class):
        mock_collection = MagicMock()
        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_class.return_value = mock_client

        ltm = LongTermMemory(self.db_path)
        ltm.add_memory("id-2", "Autre résumé", metadata={"date": "2026-10-22", "topic": "test"})

        mock_collection.add.assert_called_once_with(
            documents=["Autre résumé"],
            metadatas=[{"date": "2026-10-22", "topic": "test"}],
            ids=["id-2"]
        )

    @patch("memory.long_term.chromadb.PersistentClient")
    @patch("memory.long_term.embedding_functions.SentenceTransformerEmbeddingFunction")
    def test_query_relevant_memories_handles_empty_query(self, mock_ef, mock_client_class):
        ltm = LongTermMemory(self.db_path)
        res = ltm.query_relevant_memories("   ")
        self.assertEqual(res, [])

    @patch("memory.long_term.chromadb.PersistentClient")
    @patch("memory.long_term.embedding_functions.SentenceTransformerEmbeddingFunction")
    def test_query_relevant_memories_handles_none_metadata(self, mock_ef, mock_client_class):
        mock_collection = MagicMock()
        mock_collection.count.return_value = 1
        # ChromaDB retourne [None] pour les métadonnées si metadatas=None a été stocké
        mock_collection.query.return_value = {
            "documents": [["Contenu de mémoire"]],
            "metadatas": [[None]],
            "ids": [["id-3"]],
            "distances": [[0.5]]
        }
        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_class.return_value = mock_client

        ltm = LongTermMemory(self.db_path)
        memories = ltm.query_relevant_memories("test", top_k=1, distance_threshold=1.2)

        self.assertEqual(len(memories), 1)
        # Ne doit pas planter et doit fournir un dict vide {} au lieu de None
        self.assertEqual(memories[0]["metadata"], {})
        self.assertEqual(memories[0]["summary"], "Contenu de mémoire")


if __name__ == "__main__":
    unittest.main()
