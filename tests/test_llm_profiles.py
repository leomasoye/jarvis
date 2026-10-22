"""
Tests unitaires pour les profils de génération adaptatifs et le cache de modèles.
"""
import unittest
import time
from unittest.mock import MagicMock, patch

from ai.llm_manager import LLMManager


class TestLLMProfiles(unittest.TestCase):

    def setUp(self):
        self.settings = MagicMock()
        self.settings.OLLAMA_MODEL_FAST = "llama3.2"
        self.settings.OLLAMA_MODEL_ADVANCED = "qwen2.5"
        self.settings.OLLAMA_BASE_URL = "http://localhost:11434"
        self.bridge = MagicMock()

    @patch("ai.llm_manager.LLMThread")
    def test_detect_generation_profile(self, mock_thread_class):
        mgr = LLMManager(self.settings, self.bridge)

        # Code
        self.assertEqual(mgr._detect_generation_profile("écris une fonction python pour trier une liste", False), "code")
        self.assertEqual(mgr._detect_generation_profile("debug cette erreur de script terminal", False), "code")

        # Factual
        self.assertEqual(mgr._detect_generation_profile("cherche la météo de demain", False), "factual")
        self.assertEqual(mgr._detect_generation_profile("quelle est la date d'aujourd'hui ?", False), "factual")
        self.assertEqual(mgr._detect_generation_profile("du blabla", True), "factual") # is_action_result

        # Creative
        self.assertEqual(mgr._detect_generation_profile("invente une histoire de science-fiction", False), "creative")
        self.assertEqual(mgr._detect_generation_profile("raconte une blague", False), "creative")

        # Conversational (défaut)
        self.assertEqual(mgr._detect_generation_profile("comment vas-tu ce matin ?", False), "conversational")

    @patch("ai.llm_manager.LLMThread")
    @patch("ai.llm_manager.ollama.Client")
    def test_models_cache_ttl(self, mock_client_class, mock_thread_class):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.models = [MagicMock(model="llama3.2:latest"), MagicMock(model="qwen2.5:latest")]
        mock_client.list.return_value = mock_response
        mock_client_class.return_value = mock_client

        mgr = LLMManager(self.settings, self.bridge)
        mgr.CACHE_TTL_MODELS = 10.0

        # Premier appel -> appelle l'API Ollama
        models1 = mgr.get_available_models()
        self.assertEqual(len(models1), 2)
        self.assertEqual(mock_client.list.call_count, 1)

        # Deuxième appel immédiat -> utilise le cache, pas d'appel API supplémentaire
        models2 = mgr.get_available_models()
        self.assertEqual(len(models2), 2)
        self.assertEqual(mock_client.list.call_count, 1)

        # Force refresh -> nouvel appel API
        models3 = mgr.get_available_models(force_refresh=True)
        self.assertEqual(len(models3), 2)
        self.assertEqual(mock_client.list.call_count, 2)


if __name__ == "__main__":
    unittest.main()
