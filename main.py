"""
JARVIS — Point d'entrée principal de l'application.

Usage :
    python main.py

Référence : contexte_projet.md — à consulter avant tout développement.
"""
import sys
import logging
from pathlib import Path

# Forcer UTF-8 sur stdout/stderr — Windows (cp1252) ne supporte pas les accents/emojis
if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    getattr(sys.stderr, "reconfigure")(encoding="utf-8", errors="replace")

# Garantir que la racine du projet est dans le path Python
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import Settings
from core.app import JarvisApp


def setup_logging(settings: Settings) -> None:
    """Configure le système de logging (console + fichier rotatif)."""
    settings.LOGS_DIR.mkdir(exist_ok=True)

    level = getattr(logging, settings.APP_LOG_LEVEL.upper(), logging.DEBUG)

    fmt = "%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s"
    datefmt = "%H:%M:%S"

    handlers: list[logging.Handler] = [
        logging.StreamHandler(
            stream=open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1, closefd=False)
            if hasattr(sys.stdout, 'fileno') else sys.stdout
        ),
        logging.FileHandler(settings.LOGS_DIR / "jarvis.log", encoding="utf-8"),
    ]

    logging.basicConfig(level=level, format=fmt, datefmt=datefmt, handlers=handlers)

    # Réduire le bruit des bibliothèques tierces
    for noisy_lib in ("urllib3", "httpx", "httpcore", "asyncio"):
        logging.getLogger(noisy_lib).setLevel(logging.WARNING)


def main() -> int:
    """Point d'entrée principal."""
    settings = Settings()
    setup_logging(settings)

    log = logging.getLogger(__name__)
    log.info("=" * 60)
    log.info(f"  {settings.APP_NAME} — Démarrage  (v{settings.APP_VERSION})")
    log.info("=" * 60)
    log.info(f"  Modèle rapide   : {settings.OLLAMA_MODEL_FAST}")
    log.info(f"  Modèle avancé   : {settings.OLLAMA_MODEL_ADVANCED}")
    log.info(f"  Backend Ollama  : {settings.OLLAMA_BASE_URL}")
    log.info("=" * 60)

    # Force l'icône dans la barre des tâches Windows
    if sys.platform == 'win32':
        try:
            import ctypes
            myappid = "jarvis.app"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception as e:
            log.warning(f"Impossible de forcer l'icône dans la barre des tâches : {e}")

    # Vérifier et lancer Ollama automatiquement si besoin
    from core.ollama_service import ensure_ollama_running, preload_model
    ensure_ollama_running(settings)

    # Précharger le modèle en VRAM dans un thread dédié pour ne pas ralentir l'UI
    import threading
    threading.Thread(
        target=preload_model,
        args=(settings.OLLAMA_MODEL_FAST,),
        name="OllamaPreloadThread",
        daemon=True,
    ).start()

    app = JarvisApp(sys.argv, settings)
    if getattr(app, "is_duplicate", False):
        return 0

    exit_code = app.exec()

    from core.ollama_service import shutdown_ollama_if_managed
    shutdown_ollama_if_managed()

    log.info(f"Application terminée (code {exit_code}).")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
