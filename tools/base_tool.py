from enum import Enum
from typing import Any, Dict

class RiskLevel(str, Enum):
    SAFE = "SAFE"           # Exécution directe
    MODERATE = "MODERATE"   # Demande confirmation via Action Card
    SENSITIVE = "SENSITIVE" # Demande confirmation stricte

class BaseTool:
    """Classe de base pour tous les outils agentiques."""
    
    name: str = "base_tool"
    description: str = "Description de l'outil"
    risk_level: RiskLevel = RiskLevel.SAFE
    parameters_schema: Dict[str, Any] = {}

    def execute(self, params: Dict[str, Any]) -> str:
        """
        Exécute l'outil avec les paramètres fournis.
        Doit retourner une chaîne de caractères (résultat ou erreur détaillée).
        """
        raise NotImplementedError("La méthode execute() doit être implémentée par la sous-classe.")
