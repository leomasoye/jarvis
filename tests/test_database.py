"""
Tests unitaires pour la base de données SQLite (Database).
"""
import unittest
import tempfile
import shutil
from pathlib import Path
from memory.database import Database


class TestDatabase(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_jarvis.db"
        self.db = Database(self.db_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_and_get_message(self):
        session_id = "test-session-123"
        self.db.save_message(session_id, "user", "Bonjour Jarvis", "llama3.2", 15)
        self.db.save_message(session_id, "assistant", "Bonjour !", "llama3.2", 20)

        messages = self.db.get_session_messages(session_id)
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[0]["content"], "Bonjour Jarvis")
        self.assertEqual(messages[1]["role"], "assistant")

    def test_user_profile(self):
        self.db.set_profile_value("prenom", "Leo")
        self.db.set_profile_value("langage_prefere", "Python")

        profile = self.db.get_profile()
        self.assertEqual(profile["prenom"], "Leo")
        self.assertEqual(profile["langage_prefere"], "Python")

        formatted = self.db.get_profile_formatted()
        self.assertIn("Leo", formatted)
        self.assertIn("Python", formatted)

    def test_memories_metadata(self):
        self.db.save_memory("Discussion sur Python et IA", "chroma-uuid-1", ["code", "ia"])
        memories = self.db.get_all_memories()
        self.assertEqual(len(memories), 1)
        self.assertEqual(memories[0]["chroma_id"], "chroma-uuid-1")
        self.assertEqual(memories[0]["topics"], ["code", "ia"])


if __name__ == "__main__":
    unittest.main()
