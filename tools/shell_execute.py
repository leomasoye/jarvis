import os
import logging
import subprocess
from typing import Any, Dict
from pathlib import Path

from tools.base_tool import BaseTool, RiskLevel

logger = logging.getLogger(__name__)

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
