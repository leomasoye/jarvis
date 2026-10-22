import os
import logging
from fnmatch import fnmatch
from typing import Any, Dict
from pathlib import Path

from tools.base_tool import BaseTool, RiskLevel

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# Sandboxing — Chemins autorisés et patterns bloqués
# ══════════════════════════════════════════════════════════════════════════════

# Répertoires dans lesquels JARVIS a le droit de lire/écrire
_ALLOWED_ROOTS = [
    Path.home() / "Documents",
    Path.home() / "Desktop",
    Path.home() / "Downloads",
    Path.home() / "PROJET JARVIS",
    Path.home() / "Projects",
]

# Patterns de fichiers sensibles que JARVIS ne doit jamais lire
_BLOCKED_PATTERNS = [
    "*.env", "*.key", "*.pem", "*.p12", "*.pfx", "*.jks",
    "*password*", "*secret*", "*credential*", "*token*",
    "*.ssh/*", "id_rsa*", "id_ed25519*", "known_hosts",
]


def _is_path_allowed(path: Path) -> tuple[bool, str]:
    """
    Vérifie qu'un chemin est dans la whitelist et n'est pas un fichier sensible.
    Retourne (autorisé, raison).
    """
    resolved = path.resolve()

    # Vérifier la whitelist de répertoires
    in_allowed = any(
        resolved == root or resolved.is_relative_to(root)
        for root in _ALLOWED_ROOTS
    )
    if not in_allowed:
        return False, f"Chemin hors zone autorisée : {resolved}"

    # Vérifier les patterns bloqués
    name_lower = resolved.name.lower()
    full_lower = str(resolved).lower().replace("\\", "/")
    for pattern in _BLOCKED_PATTERNS:
        pat_lower = pattern.lower()
        # Test avec fnmatch sur le nom de fichier et le chemin
        if fnmatch(name_lower, pat_lower) or fnmatch(full_lower, f"*{pat_lower}*"):
            return False, f"Fichier sensible bloqué (pattern: {pattern})"
        # Test sur sous-chaîne sans astérisques
        clean = pat_lower.strip("*")
        if clean and (clean in name_lower or clean in full_lower):
            return False, f"Fichier sensible bloqué (pattern: {pattern})"

    return True, "OK"


class FileReadTool(BaseTool):
    name = "file_read"
    description = "Lit le contenu d'un fichier sur le système local."
    risk_level = RiskLevel.SAFE
    parameters_schema = {
        "file_path": {
            "type": "string",
            "description": "Le chemin absolu vers le fichier à lire."
        }
    }

    def execute(self, params: Dict[str, Any]) -> str:
        file_path = params.get("file_path")
        if not file_path:
            return "Erreur : 'file_path' est requis."

        try:
            path = Path(file_path).resolve()

            # Vérification de sécurité (sandboxing)
            allowed, reason = _is_path_allowed(path)
            if not allowed:
                logger.warning(f"[FileReadTool] Accès refusé : {reason}")
                return f"Accès refusé : {reason}"

            if not path.exists():
                return f"Erreur : Le fichier '{file_path}' n'existe pas."
            if not path.is_file():
                return f"Erreur : '{file_path}' n'est pas un fichier."

            content = path.read_text(encoding="utf-8", errors="replace")
            # Tronquer le contenu si trop long pour éviter de surcharger la mémoire
            max_chars = 20000
            if len(content) > max_chars:
                content = content[:max_chars] + f"\n\n[... CONTENU TRONQUÉ : fichier trop long (> {max_chars} caractères)]"
            
            return f"Contenu de {file_path}:\n{content}"
        except Exception as e:
            logger.error(f"[FileReadTool] Erreur : {e}")
            return f"Erreur lors de la lecture du fichier : {e}"


class FileWriteTool(BaseTool):
    name = "file_write"
    description = "Crée ou écrase un fichier avec du contenu textuel. Utile pour écrire du code, des notes, ou modifier des fichiers existants."
    risk_level = RiskLevel.SENSITIVE
    parameters_schema = {
        "file_path": {
            "type": "string",
            "description": "Le chemin absolu vers le fichier à créer ou modifier."
        },
        "content": {
            "type": "string",
            "description": "Le contenu texte à écrire dans le fichier."
        }
    }

    def execute(self, params: Dict[str, Any]) -> str:
        file_path = params.get("file_path")
        content = params.get("content")
        
        if not file_path:
            return "Erreur : 'file_path' est requis."
        if content is None:
            return "Erreur : 'content' est requis."

        try:
            path = Path(file_path).resolve()

            # Vérification de sécurité (sandboxing)
            allowed, reason = _is_path_allowed(path)
            if not allowed:
                logger.warning(f"[FileWriteTool] Accès refusé : {reason}")
                return f"Accès refusé : {reason}"

            # Créer les répertoires parents si nécessaire
            path.parent.mkdir(parents=True, exist_ok=True)
            
            path.write_text(content, encoding="utf-8")
            return f"Le fichier '{file_path}' a été écrit avec succès ({len(content)} caractères)."
        except Exception as e:
            logger.error(f"[FileWriteTool] Erreur : {e}")
            return f"Erreur lors de l'écriture du fichier : {e}"
