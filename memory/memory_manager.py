import logging
import uuid
from typing import Optional
from datetime import datetime
import ollama
from config.settings import Settings
from memory.short_term import ShortTermMemory
from memory.long_term import LongTermMemory
from memory.database import Database

logger = logging.getLogger(__name__)

class MemoryManager:
    """
    Orchestrateur de mémoire pour JARVIS.
    Gère la mémoire court-terme (session), long-terme (vectorielle ChromaDB) 
    et l'historique complet (SQLite).
    """

    def __init__(self, settings: Settings, action_manager=None) -> None:
        self.settings = settings
        self.session_id = str(uuid.uuid4())
        self.action_manager = action_manager
        
        # Initialisation des sous-systèmes
        self.short_term = ShortTermMemory(settings.SHORT_TERM_MAX_TURNS)
        self.long_term = LongTermMemory(settings.CHROMA_DB_PATH)
        self.db = Database(settings.SQLITE_DB_PATH)
        
        self.base_system_prompt = ""
        self.persona = ""
        logger.info(f"[MemoryManager] Initialisé avec session_id={self.session_id}")

    def set_system_prompt(self, prompt: str, persona: str = "") -> None:
        """Définit le system prompt de base et le persona de l'IA."""
        self.base_system_prompt = prompt.strip()
        self.persona = persona.strip()
        # Le prompt final sera reconstruit dynamiquement
        self.short_term.set_system_prompt(self._build_initial_prompt())

    def _build_initial_prompt(self) -> str:
        """Combine le system prompt de base avec le persona et les outils."""
        prompt = self.base_system_prompt
        if self.persona:
            prompt += f"\n\n--- IDENTITÉ DE L'IA (PERSONA) ---\n{self.persona}\n"
        if self.action_manager:
            prompt += f"\n\n--- OUTILS DISPONIBLES (ACTIONS PC) ---\n{self.action_manager.get_tool_documentation()}\n"
        return prompt

    def add(
        self,
        role: str,
        content: str,
        model_used: Optional[str] = None,
        tokens: Optional[int] = None,
    ) -> None:
        """
        Ajoute un message à la fois dans le buffer court-terme et dans la DB SQLite.
        """
        # Sauvegarde en RAM
        self.short_term.add(role, content)
        # Sauvegarde sur disque
        self.db.save_message(self.session_id, role, content, model_used, tokens)

    def get_messages_for_llm(self, user_input: str) -> list[dict]:
        """
        Construit le contexte complet pour le LLM :
        1. Récupère le profil utilisateur.
        2. Recherche les mémoires pertinentes dans ChromaDB (avec seuil de similarité).
        3. Construit un system prompt enrichi.
        4. Ajoute l'historique court-terme (limité aux N derniers échanges).
        """
        # 1. Profil Utilisateur
        profile_text = self.db.get_profile_formatted()

        # 2. Mémoires pertinentes (avec seuil de similarité pour éviter les documents non pertinents)
        rag_threshold = getattr(self.settings, 'RAG_SIMILARITY_THRESHOLD', 1.2)
        memories = self.long_term.query_relevant_memories(
            user_input, 
            top_k=3,
            distance_threshold=rag_threshold
        )
        memories_text = ""
        if memories:
            memories_text = "MÉMOIRES PERTINENTES (Conversations passées) :\n"
            for m in memories:
                date = m["metadata"].get("date", "Inconnue")
                distance = m.get("distance", 0.0)
                memories_text += f"[{date}] (pertinence: {1.0 - distance/2:.0%}) {m['summary']}\n"

        # 3. Construction du prompt système final
        final_system_prompt = self._build_initial_prompt()
        if profile_text or memories_text:
            final_system_prompt += "\n\n--- CONTEXTE DYNAMIQUE ---\n"
            if profile_text:
                final_system_prompt += f"{profile_text}\n"
            if memories_text:
                final_system_prompt += f"{memories_text}\n"

        # Mise à jour du prompt système dans la mémoire court-terme avant de récupérer les messages
        self.short_term.set_system_prompt(final_system_prompt)

        return self.short_term.get_messages_for_llm()

    def clear_context(self) -> None:
        """Vide le contexte de la session courante."""
        self.short_term.clear()
        self.session_id = str(uuid.uuid4())
        logger.info(f"[MemoryManager] Contexte effacé, nouvelle session : {self.session_id}")

    def summarize_and_save_session(self, model: str) -> None:
        """
        Génère un résumé de la session courante via Ollama et le sauvegarde 
        dans ChromaDB et SQLite.
        """
        if self.short_term.message_count < 2:
            logger.info("[MemoryManager] Pas assez de messages pour générer un résumé.")
            return

        logger.info("[MemoryManager] Début de la génération du résumé de session...")
        
        # Extraire les messages pour le résumé (hors system prompt)
        messages_text = ""
        for msg in self.short_term.messages:
            messages_text += f"{msg['role'].capitalize()}: {msg['content']}\n"

        prompt = f"""Voici la transcription d'une conversation récente entre l'utilisateur et toi (JARVIS).
Fais-en un résumé concis d'un seul paragraphe en soulignant les faits importants, les décisions ou les préférences de l'utilisateur. 
Ne retiens que ce qui est utile pour l'avenir.

Conversation:
{messages_text}

Résumé:"""

        try:
            client = ollama.Client(host=self.settings.OLLAMA_BASE_URL)
            response = client.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                stream=False
            )
            
            summary = ""
            if hasattr(response, "message") and getattr(response, "message", None) is not None:
                raw_content = getattr(response.message, "content", "")
                summary = (raw_content or "").strip()
            elif isinstance(response, dict) and "message" in response:
                summary = str(response["message"].get("content", "") or "").strip()
            else:
                summary = str(response or "").strip()
            
            # Génération des tags/topics (simplifié pour l'instant)
            topics = ["général"]
            
            memory_id = str(uuid.uuid4())
            metadata = {"date": datetime.now().date().isoformat()}
            
            # Sauvegarde dans ChromaDB
            self.long_term.add_memory(memory_id, summary, metadata)
            
            # Sauvegarde dans SQLite
            self.db.save_memory(summary, memory_id, topics)
            
            logger.info("[MemoryManager] Résumé de session sauvegardé avec succès.")
        except Exception as e:
            logger.error(f"[MemoryManager] Erreur lors de la génération du résumé: {e}")
