"""
JARVIS — Mémoire Court-terme (Session).

Buffer circulaire des N derniers tours de conversation.
Consulter contexte_projet.md §6.1 pour la spécification.

Structure d'un message Ollama :
    {"role": "user" | "assistant" | "system", "content": str}
"""
import logging
from collections import deque

logger = logging.getLogger(__name__)


class ShortTermMemory:
    """
    Mémoire de session — stocke les N derniers tours (user + assistant).

    - Implémentée avec un deque à maxlen pour une complexité O(1).
    - Le system prompt est séparé et toujours injecté en premier.
    - maxlen = max_turns * 2  (un tour = 1 message user + 1 message assistant)
    """

    def __init__(self, max_turns: int = 5) -> None:
        self._max_turns = max_turns
        self._messages: deque[dict] = deque(maxlen=max_turns * 2)
        self._system_prompt: str = ""
        logger.debug(f"[Memory] ShortTermMemory initialisée — max {max_turns} tours.")

    # ── Configuration ─────────────────────────────────────────────────────────

    def set_system_prompt(self, prompt: str) -> None:
        """Définit le system prompt injecté en tête de chaque requête."""
        self._system_prompt = prompt.strip()
        logger.debug(f"[Memory] System prompt défini ({len(self._system_prompt)} caractères).")

    # ── Écriture ──────────────────────────────────────────────────────────────

    def add(self, role: str, content: str) -> None:
        """
        Ajoute un message au buffer.
        Le deque supprime automatiquement le plus ancien si maxlen est atteint.

        Args:
            role: "user" | "assistant" | "system"
            content: Contenu textuel du message
        """
        if role not in ("user", "assistant", "system"):
            logger.warning(f"[Memory] Rôle inconnu : {role!r}")
        self._messages.append({"role": role, "content": content})
        logger.debug(f"[Memory] +{role} ({len(self._messages)} messages au total).")

    # ── Lecture ───────────────────────────────────────────────────────────────

    def get_messages_for_llm(self) -> list[dict]:
        """
        Retourne la liste de messages formatée pour l'API Ollama.
        
        Filtre le contexte pour ne garder que les échanges user/assistant pertinents,
        en excluant les messages système intermédiaires (résultats d'outils, etc.)
        qui pourraient polluer le contexte.
        
        Le system prompt est toujours injecté en premier (rôle "system").

        Returns:
            list[dict]: [{"role": ..., "content": ...}, ...]
        """
        result: list[dict] = []
        if self._system_prompt:
            result.append({"role": "system", "content": self._system_prompt})

        # Extraire les messages du deque
        all_messages = list(self._messages)
        
        # Stratégie de filtrage : on garde les échanges user/assistant récents
        # et les messages système importants (résultats d'outils)
        filtered = []
        for msg in all_messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            if role in ("user", "assistant"):
                filtered.append(msg)
            elif role == "system":
                # Garder les résultats d'outils récents (dans les 2 derniers tours)
                # mais pas les vieux messages système
                filtered.append(msg)

        # Limiter strictement aux N derniers échanges
        max_messages = self._max_turns * 2
        if len(filtered) > max_messages:
            filtered = filtered[-max_messages:]
        
        result.extend(filtered)
        return result

    def clear(self) -> None:
        """Vide le buffer (conserve le system prompt)."""
        self._messages.clear()
        logger.info("[Memory] Contexte de session effacé.")

    def compress(self, summary: str) -> None:
        """
        Remplace la première moitié des messages par un message de résumé condensé,
        préservant le contexte tout en libérant de la place dans la fenêtre d'attention.
        """
        if not summary or len(self._messages) < 4:
            return

        all_msgs = list(self._messages)
        half = len(all_msgs) // 2
        recent_half = all_msgs[half:]

        # Reconstruction du deque avec le résumé en tête suivi des messages récents
        self._messages.clear()
        self._messages.append({
            "role": "system",
            "content": f"[RÉSUMÉ DU CONTEXTE ANTÉRIEUR] : {summary.strip()}"
        })
        for msg in recent_half:
            self._messages.append(msg)

        logger.info(f"[Memory] Contexte court-terme compressé : {len(all_msgs)} -> {len(self._messages)} messages.")

    # ── Propriétés ────────────────────────────────────────────────────────────

    @property
    def messages(self) -> list[dict]:
        """Copie des messages enregistrés dans le buffer."""
        return list(self._messages)

    @property
    def message_count(self) -> int:
        """Nombre de messages dans le buffer (hors system prompt)."""
        return len(self._messages)

    @property
    def turn_count(self) -> int:
        """Nombre de tours de conversation (arrondi)."""
        return len(self._messages) // 2

    def __repr__(self) -> str:
        return f"ShortTermMemory(turns={self.turn_count}, messages={self.message_count})"
