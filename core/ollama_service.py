"""
JARVIS — Service de gestion et démarrage automatique d'Ollama.

Assure que le démon Ollama tourne en tâche de fond (sans fenêtre console parasite)
et précharge les modèles en mémoire GPU au lancement de l'application.
"""
import logging
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import Optional

from config.settings import Settings

logger = logging.getLogger(__name__)

# Process global si démarré par Jarvis
_ollama_process: Optional[subprocess.Popen] = None


def is_ollama_running(base_url: str = "http://127.0.0.1:11434") -> bool:
    """Vérifie si l'API Ollama répond."""
    try:
        url = f"{base_url.rstrip('/')}/api/tags"
        req = urllib.request.Request(url, headers={"User-Agent": "JARVIS-Healthcheck"})
        with urllib.request.urlopen(req, timeout=1.5) as response:
            return response.status == 200
    except Exception:
        return False


def find_ollama_executable() -> Optional[str]:
    """Trouve l'exécutable ollama sur le système."""
    # 1. Vérifier dans le PATH
    path_in_env = shutil.which("ollama")
    if path_in_env:
        return path_in_env

    # 2. Emplacement standard Windows
    if sys.platform == "win32":
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        if local_appdata:
            standard_path = os.path.join(local_appdata, "Programs", "Ollama", "ollama.exe")
            if os.path.exists(standard_path):
                return standard_path

    return None


def ensure_ollama_running(settings: Settings, max_wait_seconds: int = 10) -> bool:
    """
    Vérifie qu'Ollama est actif. S'il n'est pas actif, le démarre en arrière-plan.
    Retourne True si Ollama est opérationnel.
    """
    global _ollama_process

    if is_ollama_running(settings.OLLAMA_BASE_URL):
        logger.info("[OllamaService] Ollama est déjà actif et répond.")
        return True

    exe_path = find_ollama_executable()
    if not exe_path:
        logger.error("[OllamaService] Exécutable 'ollama' introuvable sur le système.")
        return False

    logger.info(f"[OllamaService] Démarrage silencieux d'Ollama via {exe_path} serve...")

    creation_flags = 0
    if sys.platform == "win32":
        # Empêche l'ouverture d'une fenêtre cmd noire sous Windows
        CREATE_NO_WINDOW = 0x08000000
        DETACHED_PROCESS = 0x00000008
        creation_flags = CREATE_NO_WINDOW | DETACHED_PROCESS

    try:
        _ollama_process = subprocess.Popen(
            [exe_path, "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags,
            close_fds=(sys.platform != "win32"),
        )
    except Exception as e:
        logger.error(f"[OllamaService] Échec du lancement d'Ollama : {e}")
        return False

    # Attente active de la disponibilité de l'API
    start_time = time.time()
    while time.time() - start_time < max_wait_seconds:
        if is_ollama_running(settings.OLLAMA_BASE_URL):
            elapsed = time.time() - start_time
            logger.info(f"[OllamaService] Ollama est prêt et opérationnel en {elapsed:.1f}s.")
            return True
        time.sleep(0.5)

    logger.warning(
        f"[OllamaService] Ollama n'a pas répondu dans le délai imparti ({max_wait_seconds}s)."
    )
    return False


def preload_model(model_name: str) -> None:
    """
    Précharge le modèle spécifié en VRAM GPU sans générer de texte,
    pour éliminer la latence du premier message de l'utilisateur.
    """
    if not model_name:
        return

    try:
        import ollama
        logger.info(f"[OllamaService] Préchargement du modèle '{model_name}' en VRAM...")
        # Un appel generate avec prompt vide et keep_alive charge les poids en VRAM
        ollama.generate(model=model_name, prompt="", keep_alive="30m")
        logger.info(f"[OllamaService] Modèle '{model_name}' préchargé avec succès en VRAM.")
    except Exception as e:
        logger.warning(f"[OllamaService] Impossible de précharger '{model_name}' : {e}")


def shutdown_ollama_if_managed() -> None:
    """Arrête le processus Ollama s'il a été lancé par Jarvis."""
    global _ollama_process
    if _ollama_process and _ollama_process.poll() is None:
        logger.info("[OllamaService] Arrêt du processus Ollama lancé par Jarvis...")
        try:
            _ollama_process.terminate()
            _ollama_process.wait(timeout=3)
        except Exception as e:
            logger.warning(f"[OllamaService] Erreur lors de l'arrêt d'Ollama : {e}")
            try:
                _ollama_process.kill()
            except Exception:
                pass
        _ollama_process = None
