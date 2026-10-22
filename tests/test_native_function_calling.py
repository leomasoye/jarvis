"""
Tests unitaires pour le Function Calling natif Ollama dans LLMThread et LLMManager.
"""
import unittest
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import QCoreApplication
from ai.llm_manager import LLMThread, LLMManager


class TestNativeFunctionCalling(unittest.TestCase):

    def setUp(self):
        # Assurer qu'une instance QCoreApplication existe pour les signaux Qt
        self.app = QCoreApplication.instance() or QCoreApplication([])

    @patch("ai.llm_manager.ollama.Client")
    def test_native_tool_call_emits_tool_call_detected(self, mock_client_class):
        # Simuler un chunk de réponse Ollama avec tool_calls natifs
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_func = MagicMock()
        mock_func.name = "web_search"
        mock_func.arguments = {"query": "météo Paris"}

        mock_tool_call = MagicMock()
        mock_tool_call.function = mock_func

        mock_msg = MagicMock()
        mock_msg.content = "Je vérifie cela pour vous."
        mock_msg.tool_calls = [mock_tool_call]

        mock_chunk = MagicMock()
        mock_chunk.message = mock_msg

        mock_client.chat.return_value = iter([mock_chunk])

        thread = LLMThread()
        thread.configure("http://localhost:11434")
        thread.set_tools([{"type": "function", "function": {"name": "web_search"}}])

        detected = []
        thread.tool_call_detected.connect(lambda full_resp, text_before: detected.append((full_resp, text_before)))

        thread._messages = [{"role": "user", "content": "Quelle est la météo ?"}]
        thread._model = "llama3.2"

        # Exécuter run() de façon synchrone dans le test
        thread.run()

        self.assertEqual(len(detected), 1)
        full_resp, text_before = detected[0]
        self.assertIn("web_search", full_resp)
        self.assertIn("météo Paris", full_resp)
        self.assertEqual(text_before, "Je vérifie cela pour vous.")

    @patch("ai.llm_manager.ollama.Client")
    def test_fallback_when_model_does_not_support_tools(self, mock_client_class):
        # Simuler une exception Ollama 'does not support tools' puis un fallback réussi
        import ollama
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Premier appel (avec tools) lève une ResponseError
        # Second appel (sans tools) réussit en texte brut
        mock_msg_fallback = MagicMock()
        mock_msg_fallback.content = "Bonjour ! Comment puis-je vous aider ?"
        mock_msg_fallback.tool_calls = None
        mock_chunk_fallback = MagicMock()
        mock_chunk_fallback.message = mock_msg_fallback

        mock_client.chat.side_effect = [
            ollama.ResponseError("model 'mistral:latest' does not support tools"),
            iter([mock_chunk_fallback])
        ]

        thread = LLMThread()
        thread.configure("http://localhost:11434")
        thread.set_tools([{"type": "function", "function": {"name": "web_search"}}])

        completed = []
        thread.response_complete.connect(lambda text: completed.append(text))

        thread._messages = [{"role": "user", "content": "Bonjour"}]
        thread._model = "mistral:latest"

        thread.run()

        # Doit avoir désactivé les outils natifs pour ce modèle et complété la réponse
        self.assertFalse(thread._native_tools_supported)
        self.assertEqual(len(completed), 1)
        self.assertIn("Bonjour", completed[0])


if __name__ == "__main__":
    unittest.main()
