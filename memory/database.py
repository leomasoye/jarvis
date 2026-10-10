import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class Database:
    """
    Gestionnaire de la base de données SQLite pour JARVIS.
    Gère l'historique complet, le profil utilisateur et les métadonnées des mémoires.
    """

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Retourne une nouvelle connexion avec le support des row factories."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initialise le schéma de la base de données s'il n'existe pas."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Table: conversations (Historique complet)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    timestamp DATETIME,
                    role TEXT,
                    content TEXT,
                    model_used TEXT,
                    tokens_used INTEGER
                )
            ''')

            # Table: user_profile (Préférences et profil)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_profile (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at DATETIME
                )
            ''')

            # Table: memories (Métadonnées des résumés ChromaDB)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    summary TEXT,
                    chroma_id TEXT,
                    session_date DATE,
                    topics TEXT
                )
            ''')

            conn.commit()
        logger.debug(f"[Database] Schéma initialisé dans {self.db_path}")

    # ── CRUD Conversations ───────────────────────────────────────────────────

    def save_message(self, session_id: str, role: str, content: str, model_used: str = None, tokens: int = None) -> None:
        """Sauvegarde un message dans l'historique."""
        timestamp = datetime.now().isoformat()
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO conversations (session_id, timestamp, role, content, model_used, tokens_used) VALUES (?, ?, ?, ?, ?, ?)",
                (session_id, timestamp, role, content, model_used, tokens)
            )
            conn.commit()

    def get_session_messages(self, session_id: str) -> list[dict]:
        """Récupère tous les messages d'une session."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM conversations WHERE session_id = ? ORDER BY timestamp ASC", (session_id,))
            return [dict(row) for row in cursor.fetchall()]

    # ── CRUD User Profile ────────────────────────────────────────────────────

    def set_profile_value(self, key: str, value: str) -> None:
        """Ajoute ou met à jour une valeur dans le profil utilisateur."""
        timestamp = datetime.now().isoformat()
        with self._get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO user_profile (key, value, updated_at) VALUES (?, ?, ?)",
                (key, value, timestamp)
            )
            conn.commit()
        logger.debug(f"[Database] Profil mis à jour : {key}={value}")

    def get_profile(self) -> dict[str, str]:
        """Retourne l'intégralité du profil utilisateur."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT key, value FROM user_profile")
            return {row["key"]: row["value"] for row in cursor.fetchall()}

    def get_profile_formatted(self) -> str:
        """Retourne le profil formaté pour l'injection dans le prompt."""
        profile = self.get_profile()
        if not profile:
            return ""
        
        formatted = "PROFIL UTILISATEUR :\n"
        for k, v in profile.items():
            formatted += f"- {k} : {v}\n"
        return formatted

    # ── CRUD Memories ────────────────────────────────────────────────────────

    def save_memory(self, summary: str, chroma_id: str, topics: list[str]) -> None:
        """Enregistre une métadonnée de mémoire (lié à ChromaDB)."""
        session_date = datetime.now().date().isoformat()
        topics_json = json.dumps(topics)
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO memories (summary, chroma_id, session_date, topics) VALUES (?, ?, ?, ?)",
                (summary, chroma_id, session_date, topics_json)
            )
            conn.commit()
        logger.info(f"[Database] Mémoire sauvegardée (Chroma ID: {chroma_id})")

    def get_all_memories(self) -> list[dict]:
        """Récupère toutes les métadonnées de mémoires."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM memories ORDER BY session_date DESC")
            rows = []
            for row in cursor.fetchall():
                d = dict(row)
                d["topics"] = json.loads(d["topics"])
                rows.append(d)
            return rows
