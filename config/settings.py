"""
JARVIS — Configuration centralisée de l'application.
Toutes les constantes et paramètres sont définis ici.
Référence : contexte_projet.md §10.1 Règle n°6 — Jamais de magic strings.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Charger .env depuis la racine du projet
_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".env", override=False)


class Settings:
    """
    Classe de configuration centralisée.
    Toutes les valeurs proviennent du fichier .env ou ont une valeur par défaut saine.
    """

    # --- Chemins de l'application ---
    ROOT_DIR: Path = _ROOT
    UI_DIR: Path = _ROOT / "ui" / "web"
    DATA_DIR: Path = _ROOT / "data"
    CONFIG_DIR: Path = _ROOT / "config"
    LOGS_DIR: Path = _ROOT / "logs"

    # --- Métadonnées de l'application ---
    APP_NAME: str = "JARVIS"
    APP_VERSION: str = "1.0.0"
    APP_LOG_LEVEL: str = os.getenv("APP_LOG_LEVEL", "DEBUG")
    APP_THEME: str = os.getenv("APP_THEME", "dark")

    # --- Ollama ---
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL_FAST: str = os.getenv("OLLAMA_MODEL_FAST", "llama3.2:latest")
    OLLAMA_MODEL_ADVANCED: str = os.getenv("OLLAMA_MODEL_ADVANCED", "qwen2.5:latest")

    # --- Audio ---
    WHISPER_MODEL_SIZE: str = os.getenv("WHISPER_MODEL_SIZE", "small")
    WHISPER_COMPUTE_TYPE: str = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
    PIPER_MODEL_PATH: str = os.getenv(
        "PIPER_MODEL_PATH", "data/piper_models/fr_FR-upmc-medium.onnx"
    )
    AUDIO_SAMPLE_RATE: int = int(os.getenv("AUDIO_SAMPLE_RATE", "16000"))
    VAD_THRESHOLD: float = float(os.getenv("VAD_THRESHOLD", "0.05"))

    # --- Mémoire ---
    CHROMA_DB_PATH: str = os.getenv("CHROMA_DB_PATH", "data/chromadb")
    SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", "data/jarvis.db")
    SHORT_TERM_MAX_TURNS: int = int(os.getenv("SHORT_TERM_MAX_TURNS", "5"))
    RAG_SIMILARITY_THRESHOLD: float = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "1.2"))

    # --- Actions PC (Étape 6) ---
    FS_MAX_FILE_SIZE_MB: int = int(os.getenv("FS_MAX_FILE_SIZE_MB", "50"))
    SHELL_TIMEOUT_SECONDS: int = int(os.getenv("SHELL_TIMEOUT_SECONDS", "30"))
    SHELL_ENABLED: bool = os.getenv("SHELL_ENABLED", "false").lower() == "true"
    PERMISSIONS_CONFIG: str = os.getenv("PERMISSIONS_CONFIG", "config/permissions.json")

    def __init__(self) -> None:
        """Crée les répertoires nécessaires s'ils n'existent pas."""
        self.DATA_DIR.mkdir(exist_ok=True)
        self.LOGS_DIR.mkdir(exist_ok=True)
        (self.DATA_DIR / "piper_models").mkdir(exist_ok=True)
