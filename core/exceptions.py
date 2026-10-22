"""
JARVIS — Hiérarchie d'exceptions typées.
Permet une gestion d'erreurs granulaire et évite les 'except Exception' trop larges.
"""

class JarvisError(Exception):
    """Exception de base pour toutes les erreurs spécifiques à JARVIS."""
    pass


class SecurityViolationError(JarvisError):
    """Levée lorsqu'une action enfreint les règles de sécurité (sandboxing, blacklist)."""
    pass


class ToolError(JarvisError):
    """Exception de base pour les outils agentiques."""
    pass


class ToolValidationError(ToolError):
    """Levée quand les paramètres d'un outil ne respectent pas le schéma requis."""
    pass


class ToolExecutionError(ToolError):
    """Levée lors d'un échec d'exécution d'un outil."""
    pass


class MemoryError(JarvisError):
    """Levée lors d'un problème avec ChromaDB, SQLite ou la gestion de contexte."""
    pass


class LLMConnectionError(JarvisError):
    """Levée en cas d'impossibilité de joindre le serveur Ollama ou d'inférence en échec."""
    pass
