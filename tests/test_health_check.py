"""
Tests unitaires pour le module de diagnostic au démarrage (health_check).
"""
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from config.settings import Settings
from core.health_check import run_system_health_check


class TestHealthCheck(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.settings = MagicMock(spec=Settings)
        self.settings.DATA_DIR = Path(self.temp_dir) / "data"
        self.settings.LOGS_DIR = Path(self.temp_dir) / "logs"
        self.settings.OLLAMA_BASE_URL = "http://localhost:11434"

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("core.health_check.urllib.request.urlopen")
    def test_health_check_passes(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        results = run_system_health_check(self.settings)

        self.assertIn("ram", results)
        self.assertIn("disk", results)
        self.assertIn("storage_dirs", results)
        self.assertIn("ollama", results)

        self.assertTrue(results["storage_dirs"][0])
        self.assertTrue(results["ollama"][0])

    @patch("core.health_check.urllib.request.urlopen")
    def test_health_check_ollama_unreachable(self, mock_urlopen):
        mock_urlopen.side_effect = Exception("Connection refused")

        results = run_system_health_check(self.settings)

        self.assertFalse(results["ollama"][0])
        self.assertIn("non accessible", results["ollama"][1])


if __name__ == "__main__":
    unittest.main()
