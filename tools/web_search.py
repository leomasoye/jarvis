"""
JARVIS — Outil de recherche Web avancé.

Utilise le package 'ddgs' (DuckDuckGo Search) avec :
- Recherche textuelle classique
- Recherche d'actualités (pour les requêtes récentes/sport/météo)
- Retry automatique avec backoff
- Fallback multi-stratégie (reformulation, changement de région)
- Formatage riche des résultats pour le LLM
"""
import logging
import re
import time
from typing import Any, Dict, List, Optional

from tools.base_tool import BaseTool, RiskLevel

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# Mots-clés déclencheurs pour la recherche d'actualités
# ══════════════════════════════════════════════════════════════════════════════

_NEWS_KEYWORDS = [
    # Sport
    "match", "score", "résultat", "victoire", "défaite", "classement",
    "transfert", "ligue", "champion", "coupe", "goal", "but",
    "football", "basket", "tennis", "f1", "formule 1",
    # Actualité
    "actualité", "news", "aujourd'hui", "hier", "récent", "dernière",
    "élection", "politique", "guerre", "attentat", "catastrophe",
    # Météo / temps réel
    "météo", "température", "temps qu'il fait", "prévisions",
    # Finance
    "bourse", "action", "cours", "bitcoin", "crypto", "prix",
    # Divertissement
    "sortie", "nouveau film", "nouvelle série", "album", "concert",
]

_NEWS_PATTERN = re.compile(
    r'\b(' + '|'.join(re.escape(kw) for kw in _NEWS_KEYWORDS) + r')\b',
    re.IGNORECASE
)


class WebSearchTool(BaseTool):
    """
    Outil de recherche Web multi-stratégie pour JARVIS.
    
    Stratégies :
    1. Si la requête semble être de l'actualité/sport/météo → recherche NEWS d'abord
    2. Recherche textuelle classique en parallèle
    3. Retry avec reformulation si aucun résultat
    4. Formatage riche avec titres, sources et snippets
    """
    
    name = "web_search"
    description = (
        "Recherche une information sur Internet via DuckDuckGo. "
        "OBLIGATOIRE pour vérifier tout fait, actualité, résultat sportif, météo, "
        "prix, date, ou toute information potentiellement récente. "
        "Retourne les résultats les plus pertinents avec sources."
    )
    risk_level = RiskLevel.SAFE
    parameters_schema = {
        "query": {
            "type": "string",
            "description": "La requête de recherche. Sois précis et concis (ex: 'météo Paris aujourd'hui', 'résultat PSG match hier', 'prix iPhone 16')."
        }
    }

    # Configuration
    MAX_RESULTS = 6
    MAX_NEWS_RESULTS = 4
    MAX_RETRIES = 2
    RETRY_DELAY = 1.0  # secondes

    def execute(self, params: Dict[str, Any]) -> str:
        query = params.get("query", "").strip()
        if not query:
            return "Erreur : le paramètre 'query' est requis."

        logger.info(f"[WebSearch] Recherche : '{query}'")

        # Déterminer si c'est une requête d'actualité
        is_news_query = bool(_NEWS_PATTERN.search(query))

        # Stratégie 1 : Recherche d'actualités (si pertinent)
        news_results = []
        if is_news_query:
            news_results = self._search_news(query)

        # Stratégie 2 : Recherche textuelle classique
        text_results = self._search_text(query)

        # Stratégie 3 : Si tout est vide, reformuler et réessayer
        if not text_results and not news_results:
            logger.info(f"[WebSearch] Aucun résultat — tentative de reformulation.")
            reformulated = self._reformulate_query(query)
            if reformulated != query:
                text_results = self._search_text(reformulated)
                if not text_results:
                    news_results = self._search_news(reformulated)

        # Stratégie 4 : Recherche en anglais si le français échoue
        if not text_results and not news_results:
            logger.info(f"[WebSearch] Tentative de recherche sans restriction de région.")
            text_results = self._search_text(query, region="wt-wt")

        # Formatage final
        return self._format_results(query, text_results, news_results)

    # ── Moteurs de recherche ─────────────────────────────────────────────────

    def _search_text(self, query: str, region: str = "fr-fr") -> List[dict]:
        """Recherche textuelle DuckDuckGo avec retry."""
        for attempt in range(self.MAX_RETRIES):
            try:
                from ddgs import DDGS
                results = DDGS().text(
                    query, 
                    max_results=self.MAX_RESULTS,
                    region=region
                )
                if results:
                    logger.info(f"[WebSearch] Texte : {len(results)} résultat(s) (tentative {attempt + 1})")
                    return results
            except Exception as e:
                logger.warning(f"[WebSearch] Erreur texte (tentative {attempt + 1}) : {e}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY * (attempt + 1))
        return []

    def _search_news(self, query: str) -> List[dict]:
        """Recherche d'actualités DuckDuckGo."""
        for attempt in range(self.MAX_RETRIES):
            try:
                from ddgs import DDGS
                results = DDGS().news(
                    query, 
                    max_results=self.MAX_NEWS_RESULTS,
                    region="fr-fr"
                )
                if results:
                    logger.info(f"[WebSearch] News : {len(results)} résultat(s)")
                    return results
            except Exception as e:
                logger.warning(f"[WebSearch] Erreur news (tentative {attempt + 1}) : {e}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY * (attempt + 1))
        return []

    # ── Reformulation ────────────────────────────────────────────────────────

    def _reformulate_query(self, query: str) -> str:
        """
        Tente de reformuler la requête pour obtenir plus de résultats.
        Supprime les mots vides, les accents problématiques, etc.
        """
        # Supprimer les guillemets qui pourraient trop restreindre
        reformulated = query.replace('"', '').replace("'", ' ')
        
        # Supprimer les mots interrogatifs courants en français
        noise_words = [
            "quel est", "quelle est", "quels sont", "quelles sont",
            "comment", "pourquoi", "est-ce que", "qu'est-ce que",
            "dis-moi", "montre-moi", "explique-moi", "parle-moi de",
            "je voudrais savoir", "peux-tu me dire",
        ]
        lower = reformulated.lower()
        for noise in noise_words:
            if lower.startswith(noise):
                reformulated = reformulated[len(noise):].strip()
                lower = reformulated.lower()
                break

        # Ajouter l'année courante pour les requêtes qui semblent d'actualité
        if _NEWS_PATTERN.search(query) and "2026" not in query and "2025" not in query:
            reformulated += " 2026"

        return reformulated.strip()

    # ── Formatage ────────────────────────────────────────────────────────────

    def _format_results(
        self, 
        query: str, 
        text_results: List[dict], 
        news_results: List[dict]
    ) -> str:
        """Formate les résultats en texte structuré pour le LLM."""
        if not text_results and not news_results:
            return (
                f"Aucun résultat trouvé pour '{query}'. "
                "Informe l'utilisateur que la recherche n'a rien donné et "
                "propose de reformuler sa question."
            )

        output_parts = []
        output_parts.append(f"Résultats de recherche pour : \"{query}\"\n")

        # Actualités en premier (plus pertinentes pour les requêtes récentes)
        if news_results:
            output_parts.append("══ ACTUALITÉS ══")
            for i, r in enumerate(news_results, 1):
                title = r.get("title", "Sans titre")
                body = r.get("body", "")
                source = r.get("source", "")
                date = r.get("date", "")
                url = r.get("url", r.get("href", ""))
                
                parts = [f"{i}. **{title}**"]
                if source:
                    parts.append(f"   Source : {source}")
                if date:
                    # Formater la date si possible
                    date_str = str(date)[:16] if len(str(date)) > 16 else str(date)
                    parts.append(f"   Date : {date_str}")
                if body:
                    # Tronquer le body si trop long
                    body_clean = body[:300].strip()
                    parts.append(f"   {body_clean}")
                
                output_parts.append("\n".join(parts))

        # Résultats texte
        if text_results:
            if news_results:
                output_parts.append("\n══ RÉSULTATS WEB ══")
            else:
                output_parts.append("══ RÉSULTATS WEB ══")
                
            for i, r in enumerate(text_results, 1):
                title = r.get("title", "Sans titre")
                body = r.get("body", "")
                url = r.get("href", "")
                
                entry = f"{i}. **{title}**"
                if body:
                    body_clean = body[:300].strip()
                    entry += f"\n   {body_clean}"
                if url:
                    entry += f"\n   Source : {url}"
                
                output_parts.append(entry)

        output_parts.append(
            "\n---\n"
            "Utilise ces informations pour formuler une réponse concise et factuelle. "
            "Cite les sources si pertinent."
        )

        return "\n\n".join(output_parts)
