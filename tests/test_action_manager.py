"""
Tests unitaires pour ActionManager : validation des paramètres, exécution parallèle et déballage d'hallucinations.
"""
import unittest
import time
from unittest.mock import MagicMock

from ai.action_manager import ActionManager
from tools.base_tool import BaseTool, RiskLevel


class SlowSafeTool(BaseTool):
    name = "slow_safe"
    description = "Outil de test simulant un délai"
    risk_level = RiskLevel.SAFE
    parameters_schema = {
        "text": {"type": "string", "description": "Texte à traiter"},
        "delay": {"type": "integer", "description": "Délai en ms (optionnel)", "optional": True}
    }

    def execute(self, params):
        delay = params.get("delay", 50)
        time.sleep(delay / 1000.0)
        return f"Traité : {params.get('text')}"


class StrictTool(BaseTool):
    name = "strict_tool"
    description = "Outil exigeant un paramètre obligatoire"
    risk_level = RiskLevel.SAFE
    parameters_schema = {
        "required_key": {"type": "string", "description": "Clé requise"},
        "count": {"type": "integer", "description": "Nombre entier"}
    }

    def execute(self, params):
        return f"OK {params['required_key']} x {params['count']}"


class TestActionManagerAdvanced(unittest.TestCase):

    def setUp(self):
        self.bridge = MagicMock()
        self.am = ActionManager(self.bridge)
        self.am.register_tool(SlowSafeTool())
        self.am.register_tool(StrictTool())

    def test_validation_unwraps_hallucinated_dict(self):
        # Simule une hallucination du LLM : "text": {"type": "string", "value": "Bonjour"}
        raw_params = {
            "text": {"type": "string", "value": "Bonjour monde"}
        }
        tool = self.am.tools["slow_safe"]
        valid, cleaned, err = self.am.validate_and_sanitize_params(tool, raw_params)

        self.assertTrue(valid)
        self.assertEqual(cleaned["text"], "Bonjour monde")

    def test_validation_missing_required_param(self):
        tool = self.am.tools["strict_tool"]
        valid, cleaned, err = self.am.validate_and_sanitize_params(tool, {"count": 3})

        self.assertFalse(valid)
        self.assertIn("obligatoire manquant", err)

    def test_validation_type_coercion_integer(self):
        tool = self.am.tools["strict_tool"]
        # "count" fourni sous forme de string "42"
        valid, cleaned, err = self.am.validate_and_sanitize_params(tool, {
            "required_key": "test",
            "count": "42"
        })

        self.assertTrue(valid)
        self.assertEqual(cleaned["count"], 42)

    def test_parallel_execution_faster_than_sequential(self):
        calls = [
            {"tool": "slow_safe", "params": {"text": "A", "delay": 150}},
            {"tool": "slow_safe", "params": {"text": "B", "delay": 150}},
        ]

        t0 = time.time()
        executed, result = self.am.process_calls(calls)
        elapsed = time.time() - t0

        self.assertTrue(executed)
        self.assertIn("Traité : A", result)
        self.assertIn("Traité : B", result)

        # En séquentiel, cela prendrait >= 0.30s. En parallèle, < 0.25s.
        self.assertLess(elapsed, 0.28, f"L'exécution parallèle a pris {elapsed:.3f}s (devrait être < 0.28s)")


if __name__ == "__main__":
    unittest.main()
