"""
Tests unitaires pour ShortTermMemory.
"""
import unittest
from memory.short_term import ShortTermMemory


class TestShortTermMemory(unittest.TestCase):

    def setUp(self):
        self.mem = ShortTermMemory(max_turns=3)

    def test_initial_state(self):
        self.assertEqual(self.mem.message_count, 0)
        self.assertEqual(self.mem.turn_count, 0)
        self.assertEqual(len(self.mem.messages), 0)

    def test_system_prompt(self):
        self.mem.set_system_prompt("Tu es Jarvis.")
        messages = self.mem.get_messages_for_llm()
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0], {"role": "system", "content": "Tu es Jarvis."})

    def test_add_messages(self):
        self.mem.add("user", "Bonjour")
        self.mem.add("assistant", "Bonjour ! Que puis-je faire pour vous ?")
        self.assertEqual(self.mem.message_count, 2)
        self.assertEqual(self.mem.turn_count, 1)

    def test_sliding_window_overflow(self):
        # max_turns=3 => max 6 messages
        for i in range(10):
            self.mem.add("user", f"Question {i}")
            self.mem.add("assistant", f"Réponse {i}")

        # Seuls les 6 derniers messages sont conservés
        self.assertEqual(self.mem.message_count, 6)
        messages = self.mem.get_messages_for_llm()
        # Ne doit contenir que Question 7..9 et Réponse 7..9
        self.assertEqual(messages[0]["content"], "Question 7")
        self.assertEqual(messages[-1]["content"], "Réponse 9")

    def test_clear(self):
        self.mem.set_system_prompt("Tu es Jarvis.")
        self.mem.add("user", "Hello")
        self.mem.add("assistant", "Hi")
        self.mem.clear()

        self.assertEqual(self.mem.message_count, 0)
    def test_compress(self):
        # 6 messages
        for i in range(6):
            self.mem.add("user" if i % 2 == 0 else "assistant", f"Message {i}")
        
        self.assertEqual(self.mem.message_count, 6)
        self.mem.compress("L'utilisateur s'appelle Léo et travaille sur Python.")

        # Doit contenir le résumé en tête + les messages récents (la 2e moitié = 3 messages)
        # Total = 1 + 3 = 4 messages
        self.assertEqual(self.mem.message_count, 4)
        messages = self.mem.messages
        self.assertIn("[RÉSUMÉ DU CONTEXTE ANTÉRIEUR]", messages[0]["content"])
        self.assertIn("Léo", messages[0]["content"])
        self.assertEqual(messages[-1]["content"], "Message 5")


if __name__ == "__main__":
    unittest.main()
