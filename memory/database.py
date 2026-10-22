import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path

from typing import Optional

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

            # Table: audit_log (Journal d'audit des actions exécutées)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    session_id TEXT,
                    tool_name TEXT,
                    params TEXT,
                    result TEXT,
                    risk_level TEXT,
                    user_confirmed BOOLEAN,
                    execution_time_ms INTEGER,
                    success BOOLEAN
                )
            ''')

            conn.commit()
        logger.debug(f"[Database] Schéma initialisé dans {self.db_path}")

    # ── CRUD Conversations ───────────────────────────────────────────────────

    def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        model_used: Optional[str] = None,
        tokens: Optional[int] = None,
    ) -> None:
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

    def update_profile_batch(self, facts: dict[str, str]) -> None:
        """Met à jour plusieurs clés/valeurs du profil utilisateur en une seule transaction."""
        if not facts:
            return
        timestamp = datetime.now().isoformat()
        with self._get_connection() as conn:
            for k, v in facts.items():
                if k and v:
                    conn.execute(
                        "INSERT OR REPLACE INTO user_profile (key, value, updated_at) VALUES (?, ?, ?)",
                        (str(k).strip(), str(v).strip(), timestamp)
                    )
            conn.commit()
        logger.info(f"[Database] Profil utilisateur enrichi avec {len(facts)} fait(s).")

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

    # ── CRUD Audit Trail ─────────────────────────────────────────────────────

    def save_audit_log(
        self,
        session_id: str,
        tool_name: str,
        params: dict,
        result: str,
        risk_level: str,
        user_confirmed: bool = False,
        execution_time_ms: int = 0,
        success: bool = True,
    ) -> None:
        """Enregistre l'exécution d'un outil dans le journal d'audit."""
        timestamp = datetime.now().isoformat()
        params_json = json.dumps(params, ensure_ascii=False)
        # Tronquer le résultat pour ne pas saturer SQLite si fichier ou sortie volumineuse
        truncated_result = (result[:1000] + "...") if len(result) > 1000 else result
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO audit_log (
                    timestamp, session_id, tool_name, params, result, 
                    risk_level, user_confirmed, execution_time_ms, success
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    timestamp, session_id, tool_name, params_json, truncated_result,
                    risk_level, 1 if user_confirmed else 0, execution_time_ms, 1 if success else 0
                )
            )
            conn.commit()
        logger.debug(f"[Database] Action auditée : {tool_name} (succès={success})")

    def get_audit_logs(self, limit: int = 50, session_id: Optional[str] = None) -> list[dict]:
        """Récupère les derniers logs d'audit."""
        with self._get_connection() as conn:
            if session_id:
                cursor = conn.execute(
                    "SELECT * FROM audit_log WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                    (session_id, limit)
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?",
                    (limit,)
                )
            rows = []
            for row in cursor.fetchall():
                d = dict(row)
                try:
                    d["params"] = json.loads(d["params"])
                except Exception:
                    pass
                d["user_confirmed"] = bool(d["user_confirmed"])
                d["success"] = bool(d["success"])
                rows.append(d)
            return rows
