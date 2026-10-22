"""
Tests unitaires pour SystemInfoTool.
"""
import unittest
from tools.system_info import SystemInfoTool
from tools.base_tool import RiskLevel


class TestSystemInfo(unittest.TestCase):

    def setUp(self):
        self.tool = SystemInfoTool()

    def test_tool_metadata(self):
        self.assertEqual(self.tool.name, "system_info")
        self.assertEqual(self.tool.risk_level, RiskLevel.SAFE)
        self.assertIn("metric", self.tool.parameters_schema)

    def test_execute_all(self):
        result = self.tool.execute({"metric": "all"})
        self.assertIn("État actuel du système", result)
        self.assertIn("CPU", result)
        self.assertIn("RAM", result)

    def test_execute_cpu(self):
        result = self.tool.execute({"metric": "cpu"})
        self.assertIn("CPU", result)

    def test_execute_memory(self):
        result = self.tool.execute({"metric": "memory"})
        self.assertIn("RAM", result)

    def test_execute_disk(self):
        result = self.tool.execute({"metric": "disk"})
        self.assertIn("Disque", result)

    def test_execute_invalid_metric(self):
        result = self.tool.execute({"metric": "flux_capacitor"})
        self.assertIn("Métrique inconnue", result)


if __name__ == "__main__":
    unittest.main()
