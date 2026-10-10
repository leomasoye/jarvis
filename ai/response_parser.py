"""
JARVIS — Parseur de réponses IA.

Détecte et extrait les balises spéciales dans le texte généré par le LLM.
Consulter contexte_projet.md §8 pour la spécification des balises.

Balises reconnues :
    <mermaid>...</mermaid>   → Diagramme Mermaid (Étape 5)
    <map>JSON</map>          → Carte Leaflet (Étape 5)
    ```lang\\n...```          → Bloc de code (Étape 5)
    Reste                    → Texte Markdown brut

Note Étape 2 : Le parseur est fonctionnel mais le rendu visuel des directives
est différé à l'Étape 5. Le texte brut est affiché tel quel.
"""
import re
import logging
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class SegmentType(str, Enum):
    """Types de segments détectés dans une réponse IA."""
    TEXT    = "text"
    MERMAID = "mermaid"
    MAP     = "map"
    CODE    = "code"


@dataclass
class Segment:
    """Un segment de réponse avec son type et son contenu."""
    type: SegmentType
    content: str
    lang: str = field(default="")  # Langage pour les blocs de code (python, js…)


class ResponseParser:
    """
    Analyse le texte complet d'une réponse IA.
    Retourne une liste ordonnée de Segment (text, mermaid, map, code).
    """

    # Patterns de détection (consulter contexte_projet.md §8)
    _MERMAID = re.compile(r'<mermaid>(.*?)</mermaid>', re.DOTALL | re.IGNORECASE)
    _MAP     = re.compile(r'<map>(.*?)</map>',         re.DOTALL | re.IGNORECASE)
    _CODE    = re.compile(r'```(\w*)\n?(.*?)```',      re.DOTALL)

    # Marqueur interne pour séparer le texte des directives
    _MARKER = '\x00JARVIS_DIRECTIVE\x00'

    @classmethod
    def parse(cls, text: str) -> list[Segment]:
        """
        Découpe le texte en segments ordonnés (texte + directives).

        Args:
            text: Réponse brute du LLM

        Returns:
            list[Segment]: Segments dans l'ordre d'apparition dans le texte
        """
        if not text:
            return []

        directives: list[Segment] = []

        def _replace(seg_type: SegmentType, lang: str = ""):
            def _fn(m: re.Match) -> str:
                content = m.group(1).strip() if seg_type != SegmentType.CODE \
                          else m.group(2).strip()
                actual_lang = m.group(1) if seg_type == SegmentType.CODE else lang
                directives.append(Segment(seg_type, content, lang=actual_lang))
                return cls._MARKER
            return _fn

        processed = cls._MERMAID.sub(_replace(SegmentType.MERMAID), text)
        processed = cls._MAP.sub(_replace(SegmentType.MAP), processed)
        processed = cls._CODE.sub(_replace(SegmentType.CODE), processed)

        parts = processed.split(cls._MARKER)
        segments: list[Segment] = []
        dir_idx = 0

        for i, part in enumerate(parts):
            stripped = part.strip()
            if stripped:
                segments.append(Segment(SegmentType.TEXT, stripped))
            if dir_idx < len(directives) and i < len(parts) - 1:
                segments.append(directives[dir_idx])
                dir_idx += 1

        logger.debug(
            f"[Parser] {len(segments)} segment(s) — "
            f"{sum(1 for s in segments if s.type != SegmentType.TEXT)} directive(s)."
        )
        return segments

    @classmethod
    def has_directives(cls, text: str) -> bool:
        """
        Vérifie rapidement si le texte contient au moins une directive spéciale.
        Utilisé par le bridge pour décider si un rendu spécial est nécessaire.
        """
        return bool(
            cls._MERMAID.search(text)
            or cls._MAP.search(text)
            or cls._CODE.search(text)
        )

    @classmethod
    def extract_plain_text(cls, text: str) -> str:
        """
        Retourne le texte en retirant toutes les balises spéciales.
        Utilisé notamment pour le TTS (Étape 4).
        """
        clean = cls._MERMAID.sub('', text)
        clean = cls._MAP.sub('', clean)
        clean = cls._CODE.sub(r'\2', clean)
        return clean.strip()
