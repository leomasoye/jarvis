import os
import re
import logging
import subprocess
from typing import Any, Dict
from pathlib import Path

from tools.base_tool import BaseTool, RiskLevel

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# Blacklist de commandes shell dangereuses
# ══════════════════════════════════════════════════════════════════════════════

_BLOCKED_COMMANDS = [
    "rm -rf", "rmdir /s", "del /s /q", "del /f /s /q",
    "format", "diskpart",
    "reg delete", "reg add",
    "shutdown", "restart",
    "taskkill /f /im",
    "net user", "net localgroup",
    "netsh advfirewall",
    "schtasks /create",
    "bcdedit",
    "cipher /w",
]

_BLOCKED_PATTERNS_REGEX = [
    re.compile(r"powershell\s+-enc", re.IGNORECASE),          # Commandes encodées (obfuscation)
    re.compile(r"Invoke-WebRequest.*-OutFile", re.IGNORECASE), # Téléchargement suspect
    re.compile(r"Start-Process.*-Verb\s+RunAs", re.IGNORECASE), # Élévation de privilèges
    re.compile(r"\|\s*Out-File.*\\system32", re.IGNORECASE),   # Écriture dans system32
    re.compile(r"Set-ExecutionPolicy\s+Unrestricted", re.IGNORECASE),  # Bypass de sécurité
    re.compile(r"Invoke-Expression.*\(.*DownloadString", re.IGNORECASE),  # Download & execute
]


def _is_command_safe(command: str) -> tuple[bool, str]:
    """
    Vérifie qu'une commande shell n'est pas dans la blacklist.
    Retourne (autorisé, raison).
    """
    cmd_lower = command.lower().strip()

    # Vérifier les commandes bloquées (substring)
    for blocked in _BLOCKED_COMMANDS:
        if blocked.lower() in cmd_lower:
            return False, f"Commande bloquée : contient '{blocked}'"

    # Vérifier les patterns regex dangereux
    for pattern in _BLOCKED_PATTERNS_REGEX:
        if pattern.search(command):
            return False, f"Commande bloquée : correspond au pattern '{pattern.pattern}'"

    return True, "OK"


class ShellCommandTool(BaseTool):
    name = "shell_execute"
    description = "Exécute une commande shell ou PowerShell sur le PC. Permet à JARVIS de créer des dossiers, de lancer des scripts ou de gérer le système."
    risk_level = RiskLevel.SENSITIVE
    parameters_schema = {
        "command": {
            "type": "string",
            "description": "La commande PowerShell ou CMD à exécuter."
        },
        "cwd": {
            "type": "string",
            "description": "Le répertoire de travail (optionnel). Par défaut, c'est le répertoire courant."
        }
    }

    def execute(self, params: Dict[str, Any]) -> str:
        command = params.get("command")
        cwd = params.get("cwd")
        
        if not command:
            return "Erreur : 'command' est requis."

        # Vérification de sécurité (blacklist)
        safe, reason = _is_command_safe(command)
        if not safe:
            logger.warning(f"[ShellCommandTool] Commande refusée : {reason} — Commande : {command}")
            return f"Commande refusée pour raisons de sécurité : {reason}"

        logger.info(f"[ShellCommandTool] Exécution: {command} (cwd={cwd})")
        
        try:
            # Exécution dans PowerShell pour un meilleur support sous Windows
            result = subprocess.run(
                ["powershell.exe", "-Command", command],
                capture_output=True,
                text=True,
                cwd=cwd if cwd else None,
                timeout=30 # Sécurité pour éviter un blocage
            )
            
            output = ""
            if result.stdout:
                output += f"--- STDOUT ---\n{result.stdout}\n"
            if result.stderr:
                output += f"--- STDERR ---\n{result.stderr}\n"
                
            if not output:
                output = "(Commande exécutée avec succès, pas de sortie texte)"
                
            return f"Résultat (code retour: {result.returncode}):\n{output}"
            
        except subprocess.TimeoutExpired:
            logger.error("[ShellCommandTool] Timeout expiré.")
            return "Erreur : La commande a pris trop de temps à s'exécuter (> 30s) et a été interrompue."
        except Exception as e:
            logger.error(f"[ShellCommandTool] Erreur : {e}")
            return f"Erreur lors de l'exécution de la commande : {e}"
