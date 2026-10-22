"""
Tests unitaires pour l'audit trail (table audit_log et ActionManager).
"""
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock

from memory.database import Database
from ai.action_manager import ActionManager
from tools.base_tool import BaseTool, RiskLevel


class DummySafeTool(BaseTool):
    name = "dummy_safe"
    description = "Outil de test SAFE"
    risk_level = RiskLevel.SAFE
    parameters_schema = {"query": {"type": "string"}}

    def execute(self, params):
        return f"Résultat pour {params.get('query')}"


class DummySensitiveTool(BaseTool):
    name = "dummy_sensitive"
    description = "Outil de test SENSITIVE"
    risk_level = RiskLevel.SENSITIVE
    parameters_schema = {"command": {"type": "string"}}

    def execute(self, params):
        return f"Exécuté : {params.get('command')}"


class TestAuditLog(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_audit.db"
        self.db = Database(self.db_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_and_retrieve_audit_log(self):
        self.db.save_audit_log(
            session_id="sess-1",
            tool_name="web_search",
            params={"query": "météo paris"},
            result="Il fait 18°C",
            risk_level="SAFE",
            user_confirmed=False,
            execution_time_ms=120,
            success=True
        )

        logs = self.db.get_audit_logs(session_id="sess-1")
        self.assertEqual(len(logs), 1)
        log = logs[0]
        self.assertEqual(log["tool_name"], "web_search")
        self.assertEqual(log["params"], {"query": "météo paris"})
        self.assertEqual(log["risk_level"], "SAFE")
        self.assertFalse(log["user_confirmed"])
        self.assertTrue(log["success"])
        self.assertEqual(log["execution_time_ms"], 120)

    def test_action_manager_logs_safe_tool(self):
        bridge = MagicMock()
        am = ActionManager(bridge=bridge)
        am.set_db(self.db, session_id="sess-safe")
        am.register_tool(DummySafeTool())

        calls = [{"tool": "dummy_safe", "params": {"query": "test"}}]
        executed, result = am.process_calls(calls)

        self.assertTrue(executed)
        self.assertIn("Résultat pour test", result)

        logs = self.db.get_audit_logs(session_id="sess-safe")
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["tool_name"], "dummy_safe")
        self.assertEqual(logs[0]["params"], {"query": "test"})
        self.assertFalse(logs[0]["user_confirmed"])
        self.assertTrue(logs[0]["success"])

    def test_action_manager_logs_pending_confirmation(self):
        bridge = MagicMock()
        am = ActionManager(bridge=bridge)
        am.set_db(self.db, session_id="sess-sensitive")
        am.register_tool(DummySensitiveTool())

        calls = [{"tool": "dummy_sensitive", "params": {"command": "reboot"}}]
        executed, action_id = am.process_calls(calls)

        self.assertFalse(executed)
        self.assertIsNotNone(action_id)

        # L'action n'est pas encore exécutée donc aucun log
        self.assertEqual(len(self.db.get_audit_logs(session_id="sess-sensitive")), 0)

        # L'utilisateur confirme l'action
        res = am.execute_pending(action_id)
        self.assertEqual(res, "Exécuté : reboot")

        logs = self.db.get_audit_logs(session_id="sess-sensitive")
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["tool_name"], "dummy_sensitive")
        self.assertTrue(logs[0]["user_confirmed"])
        self.assertTrue(logs[0]["success"])


if __name__ == "__main__":
    unittest.main()
