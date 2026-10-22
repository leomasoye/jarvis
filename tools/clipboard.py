"""
JARVIS — Outil de gestion du presse-papier (ClipboardTool).
Permet à JARVIS de lire ou d'écrire dans le presse-papier Windows.
"""
import logging
import subprocess
from typing import Any, Dict

from tools.base_tool import BaseTool, RiskLevel

logger = logging.getLogger(__name__)


class ClipboardTool(BaseTool):
    name = "clipboard"
    description = (
        "Lit ou écrit dans le presse-papier de l'ordinateur. "
        "Permet de récupérer du texte copié par l'utilisateur ou de copier un résultat pour qu'il puisse le coller."
    )
    risk_level = RiskLevel.SAFE
    parameters_schema = {
        "action": {
            "type": "string",
            "description": "L'action à réaliser : 'read' (lire le presse-papier) ou 'write' (copier dans le presse-papier)."
        },
        "text": {
            "type": "string",
            "description": "Le texte à écrire dans le presse-papier (requis si action='write').",
            "optional": True
        }
    }

    def execute(self, params: Dict[str, Any]) -> str:
        action = str(params.get("action") or "read").lower().strip()

        try:
            if action in ("read", "get", "paste"):
                proc = subprocess.run(
                    ["powershell.exe", "-NoProfile", "-Command", "Get-Clipboard"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    encoding="utf-8",
                    errors="replace"
                )
                content = proc.stdout.strip()
                if not content:
                    return "Le presse-papier est actuellement vide."
                
                # Tronquer si très long
                max_chars = 5000
                if len(content) > max_chars:
                    content = content[:max_chars] + f"\n[... TRONQUÉ : contenu > {max_chars} caractères]"

                return f"Contenu du presse-papier :\n{content}"

            elif action in ("write", "set", "copy"):
                text = params.get("text")
                if text is None:
                    return "Erreur : 'text' est requis lorsque action='write'."

                # Utiliser stdin pour éviter les problèmes d'échappement de quotes dans PowerShell
                proc = subprocess.run(
                    ["powershell.exe", "-NoProfile", "-Command", "$input | Set-Clipboard"],
                    input=str(text),
                    capture_output=True,
                    text=True,
                    timeout=5,
                    encoding="utf-8",
                    errors="replace"
                )
                if proc.returncode == 0:
                    return f"Le texte a été copié avec succès dans le presse-papier ({len(str(text))} caractères)."
                else:
                    return f"Erreur lors de la copie dans le presse-papier : {proc.stderr}"

            else:
                return f"Action inconnue '{action}'. Actions valides : 'read', 'write'."

        except subprocess.TimeoutExpired:
            return "Erreur : Délai dépassé lors de l'accès au presse-papier."
        except Exception as e:
            logger.error(f"[ClipboardTool] Erreur : {e}")
            return f"Erreur lors de l'opération sur le presse-papier : {e}"
