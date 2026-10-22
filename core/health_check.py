"""
JARVIS — Diagnostic et vérification de santé système au démarrage (Health Check).
Vérifie la disponibilité d'Ollama, l'intégrité de la mémoire, l'espace disque et la RAM.
"""
import logging
import psutil
import urllib.request
from typing import Dict, Tuple
from pathlib import Path

from config.settings import Settings

logger = logging.getLogger(__name__)


def run_system_health_check(settings: Settings) -> Dict[str, Tuple[bool, str]]:
    """
    Exécute un ensemble de vérifications de démarrage.
    Retourne un dictionnaire {nom_test: (succès, message)}.
    """
    results: Dict[str, Tuple[bool, str]] = {}

    # 1. Vérification de la RAM disponible
    try:
        mem = psutil.virtual_memory()
        avail_gb = mem.available / (1024 ** 3)
        if avail_gb < 1.0:
            results["ram"] = (False, f"Mémoire RAM faible : seulement {avail_gb:.1f} Go disponibles.")
            logger.warning(f"[HealthCheck] {results['ram'][1]}")
        else:
            results["ram"] = (True, f"RAM disponible : {avail_gb:.1f} Go.")
            logger.debug(f"[HealthCheck] {results['ram'][1]}")
    except Exception as e:
        results["ram"] = (False, f"Impossible de vérifier la RAM : {e}")

    # 2. Vérification de l'espace disque
    try:
        disk_path = settings.DATA_DIR if hasattr(settings, "DATA_DIR") else Path(".")
        disk = psutil.disk_usage(str(disk_path.resolve()))
        free_gb = disk.free / (1024 ** 3)
        if free_gb < 2.0:
            results["disk"] = (False, f"Espace disque critique : seulement {free_gb:.1f} Go libres.")
            logger.warning(f"[HealthCheck] {results['disk'][1]}")
        else:
            results["disk"] = (True, f"Espace disque suffisant : {free_gb:.1f} Go libres.")
            logger.debug(f"[HealthCheck] {results['disk'][1]}")
    except Exception as e:
        results["disk"] = (False, f"Impossible de vérifier le disque : {e}")

    # 3. Vérification des répertoires de données
    try:
        settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
        settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        results["storage_dirs"] = (True, "Répertoires data et logs opérationnels.")
    except Exception as e:
        results["storage_dirs"] = (False, f"Erreur d'accès aux répertoires de stockage : {e}")
        logger.error(f"[HealthCheck] {results['storage_dirs'][1]}")

    # 4. Vérification d'accessibilité Ollama
    try:
        url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags"
        req = urllib.request.Request(url, headers={"User-Agent": "JarvisHealthCheck"})
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            if resp.status == 200:
                results["ollama"] = (True, f"Ollama accessible sur {settings.OLLAMA_BASE_URL}.")
            else:
                results["ollama"] = (False, f"Ollama a retourné le code HTTP {resp.status}.")
    except Exception as e:
        results["ollama"] = (False, f"Ollama non accessible sur {settings.OLLAMA_BASE_URL} ({e}).")
        logger.warning(f"[HealthCheck] {results['ollama'][1]}")

    total_checks = len(results)
    passed_checks = sum(1 for ok, _ in results.values() if ok)
    logger.info(f"[HealthCheck] Diagnostic terminé : {passed_checks}/{total_checks} vérifications validées.")

    return results
