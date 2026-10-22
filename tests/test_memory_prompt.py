"""
Tests unitaires pour MemoryManager et la construction dynamique du prompt.
"""
import unittest
from unittest.mock import MagicMock
from config.settings import Settings
from memory.memory_manager import MemoryManager


class TestMemoryPrompt(unittest.TestCase):

    def setUp(self):
        self.settings = MagicMock(spec=Settings)
        self.settings.SHORT_TERM_MAX_TURNS = 5
        self.settings.CHROMA_DB_PATH = ":memory:"
        self.settings.SQLITE_DB_PATH = ":memory:"
        self.settings.RAG_SIMILARITY_THRESHOLD = 1.2
        self.settings.SUMMARIZE_EVERY_N_TURNS = 8

    def test_dynamic_datetime_in_prompt(self):
        # On mock ChromaDB pour ne pas charger les modèles lourds en test
        mm = MemoryManager.__new__(MemoryManager)
        mm.settings = self.settings
        mm.session_id = "test-session"
        mm.action_manager = None
        mm.base_system_prompt = "Tu es Jarvis."
        mm.persona = "Iron Man AI"

        prompt = mm._build_initial_prompt()

        # Vérifier que le contexte temporel est présent
        self.assertIn("--- CONTEXTE TEMPOREL ---", prompt)
        self.assertIn("Date :", prompt)
        self.assertIn("Heure :", prompt)
        self.assertIn("--- IDENTITÉ DE L'IA (PERSONA) ---", prompt)
        self.assertIn("Iron Man AI", prompt)


if __name__ == "__main__":
    unittest.main()
