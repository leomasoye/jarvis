"""
Tests unitaires pour ClipboardTool.
"""
import unittest
from unittest.mock import patch, MagicMock
from tools.clipboard import ClipboardTool
from tools.base_tool import RiskLevel


class TestClipboardTool(unittest.TestCase):

    def setUp(self):
        self.tool = ClipboardTool()

    def test_metadata(self):
        self.assertEqual(self.tool.name, "clipboard")
        self.assertEqual(self.tool.risk_level, RiskLevel.SAFE)
        self.assertIn("action", self.tool.parameters_schema)

    @patch("tools.clipboard.subprocess.run")
    def test_execute_read(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.stdout = "Texte dans le presse-papier"
        mock_run.return_value = mock_proc

        result = self.tool.execute({"action": "read"})
        self.assertIn("Contenu du presse-papier", result)
        self.assertIn("Texte dans le presse-papier", result)

    @patch("tools.clipboard.subprocess.run")
    def test_execute_write(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_run.return_value = mock_proc

        result = self.tool.execute({"action": "write", "text": "Bonjour Jarvis"})
        self.assertIn("copié avec succès", result)

    def test_execute_write_missing_text(self):
        result = self.tool.execute({"action": "write"})
        self.assertIn("Erreur : 'text' est requis", result)

    def test_execute_unknown_action(self):
        result = self.tool.execute({"action": "delete_all"})
        self.assertIn("Action inconnue", result)


if __name__ == "__main__":
    unittest.main()
