"""
JARVIS — Gestionnaire LLM (Ollama).

Architecture : QThread dédié (RÈGLE contexte_projet.md §10.1 n°4).
Le thread principal ne fait jamais d'appel LLM bloquant.

Classes :
    LLMThread   — QThread qui exécute le streaming Ollama avec buffer anti-hallucination
    LLMManager  — QObject orchestrateur (expose les signaux, gère le thread)

Flux de données :
    LLMThread.token_received  → bridge.send_token   → JS: Chat.appendToken()
    LLMThread.response_complete → LLMManager._on_complete → (window.py sauvegarde en mémoire)
    LLMThread.tool_call_detected → LLMManager._on_tool_call → exécution silencieuse + relance
    LLMThread.error_occurred    → LLMManager._on_error   → notification + statut erreur
"""
import re
import time
import logging
import ollama
from PyQt6.QtCore import QThread, QObject, pyqtSignal

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# Patterns d'hallucination à filtrer dans les réponses du LLM
# ══════════════════════════════════════════════════════════════════════════════

# Patterns détectant un appel d'outil textuel (XML ou JSON brut)
_TOOL_CALL_PATTERNS = [
    re.compile(r'<tool_call>', re.IGNORECASE),
    re.compile(r'<function_call>', re.IGNORECASE),
    re.compile(r'\{\s*"tool"\s*:', re.IGNORECASE),
    re.compile(r'\{\s*"name"\s*:\s*".*?"\s*,\s*"arguments"', re.IGNORECASE),
]

# Patterns de "pensée à voix haute" que le LLM génère parfois
_THINKING_PATTERNS = [
    re.compile(r'^(Voyons voir|Voyons|Hmm|Laisse-moi|Laissez-moi|Bien sûr !|Bien sûr,).*$', re.MULTILINE | re.IGNORECASE),
    re.compile(r'^Pour (répondre|faire|résoudre|traiter|chercher|trouver).*je (dois|vais).*$', re.MULTILINE | re.IGNORECASE),
    re.compile(r'^(Je vais maintenant|D\'abord, je|Ensuite, je|Commençons par).*$', re.MULTILINE | re.IGNORECASE),
]

# Pattern pour détecter les résultats d'outils auto-générés (hallucination)
_FAKE_RESULT_PATTERN = re.compile(
    r'\[RÉSULTAT DE L\'OUTIL.*?\].*?$|\[TOOL RESULT\].*?$',
    re.DOTALL | re.IGNORECASE | re.MULTILINE
)


def sanitize_response(text: str) -> str:
    """
    Nettoie la réponse du LLM en supprimant les patterns d'hallucination.
    Appliqué après la génération complète, avant l'envoi au frontend.
    """
    if not text:
        return text

    # 1. Couper tout ce qui suit un faux résultat d'outil
    split = re.split(r'\[RÉSULTAT DE L\'OUTIL', text, flags=re.IGNORECASE)
    if len(split) > 1:
        text = split[0]

    # 2. Supprimer les balises tool_call résiduelles en texte
    text = re.sub(r'</?tool_call>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'</?function_call>', '', text, flags=re.IGNORECASE)

    # 3. Supprimer les lignes de "pensée à voix haute"
    for pattern in _THINKING_PATTERNS:
        text = pattern.sub('', text)

    # 4. Nettoyer les lignes vides multiples
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


# ══════════════════════════════════════════════════════════════════════════════
# LLMThread — Thread dédié au streaming Ollama avec buffer intelligent
# ══════════════════════════════════════════════════════════════════════════════

class LLMThread(QThread):
    """
    Thread dédié aux appels Ollama en streaming.
    
    Nouveauté : Buffer intelligent qui intercepte les tool calls et les
    patterns d'hallucination AVANT de les envoyer au frontend.
    """

    token_received    = pyqtSignal(str)   # Un token streamé (filtré)
    response_complete = pyqtSignal(str)   # Réponse complète (texte propre)
    tool_call_detected = pyqtSignal(str, str)  # (tool_call_json, texte_avant_tool)
    error_occurred    = pyqtSignal(str)   # Message d'erreur (échec)

    # Taille du buffer de lookahead (en caractères) pour détecter les patterns
    _BUFFER_LOOKAHEAD = 20

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._messages:  list[dict] = []
        self._model:     str = ""
        self._base_url:  str = "http://localhost:11434"
        self._cancel:    bool = False
        self._options:   dict = {}   # Paramètres Ollama (temperature, etc.)

    def configure(self, base_url: str) -> None:
        """Configure l'URL du serveur Ollama."""
        self._base_url = base_url

    def set_options(self, options: dict) -> None:
        """Configure les paramètres de génération Ollama (temperature, top_p, etc.)."""
        self._options = options

    def start_inference(self, messages: list[dict], model: str) -> None:
        """
        Lance l'inférence en arrière-plan (non-bloquant).
        Si un appel est déjà en cours, il est annulé proprement avant de relancer.
        """
        if self.isRunning():
            logger.warning("[LLM] Thread actif — annulation de l'appel précédent.")
            self._cancel = True
            self.wait(3000)

        self._messages = messages
        self._model = model
        self._cancel = False
        logger.info(f"[LLM] Inférence démarrée — modèle: {model} | {len(messages)} messages")
        self.start()

    def cancel(self) -> None:
        """Demande l'arrêt du streaming en cours."""
        logger.info("[LLM] Annulation demandée par l'utilisateur.")
        self._cancel = True

    # ── run() — Corps du thread avec buffer intelligent ──────────────────────

    def run(self) -> None:
        """
        Exécuté dans le thread dédié par Qt.
        
        Le buffer fonctionne en 2 modes :
        - MODE NORMAL : les tokens sont émis vers le frontend après un court délai
          de lookahead pour détecter le début d'un tool_call.
        - MODE SILENCIEUX : activé dès qu'un pattern d'outil est détecté. Les tokens
          s'accumulent en silence jusqu'à la fin du stream, puis le signal
          tool_call_detected est émis.
        """
        full_response = ""
        buffer = ""              # Buffer de lookahead
        silent_mode = False      # True = on a détecté un tool call, on arrête d'émettre
        text_before_tool = ""    # Texte propre émis avant le tool call

        try:
            client = ollama.Client(host=self._base_url)

            # Construire les kwargs pour chat()
            chat_kwargs = {
                "model": self._model,
                "messages": self._messages,
                "stream": True,
            }
            if self._options:
                chat_kwargs["options"] = self._options

            stream = client.chat(**chat_kwargs)

            for chunk in stream:
                if self._cancel:
                    logger.info("[LLM] Stream interrompu.")
                    return

                token: str = chunk.message.content or ""
                if not token:
                    continue

                full_response += token

                if silent_mode:
                    # En mode silencieux, on accumule sans émettre
                    continue

                buffer += token

                # Vérifier si le buffer contient un début de tool call
                if self._check_tool_call_start(buffer):
                    # Passage en mode silencieux
                    silent_mode = True
                    text_before_tool = full_response[:len(full_response) - len(buffer)]
                    logger.info("[LLM] Tool call détecté — passage en mode silencieux.")
                    continue

                # Émettre les tokens confirmés (garder un lookahead)
                if len(buffer) > self._BUFFER_LOOKAHEAD:
                    emit_count = len(buffer) - self._BUFFER_LOOKAHEAD
                    to_emit = buffer[:emit_count]
                    buffer = buffer[emit_count:]
                    self.token_received.emit(to_emit)

            # ── Fin du stream ──

            if self._cancel:
                return

            if silent_mode:
                # Un tool call a été capturé — extraire et signaler
                logger.info(f"[LLM] Réponse complète en mode silencieux ({len(full_response)} chars).")
                self.tool_call_detected.emit(full_response, text_before_tool)
            else:
                # Émettre le reste du buffer
                if buffer:
                    self.token_received.emit(buffer)

                # Nettoyer la réponse avant de la finaliser
                cleaned = sanitize_response(full_response)
                logger.info(f"[LLM] Réponse complète ({len(cleaned)} chars).")
                self.response_complete.emit(cleaned)

        except ollama.ResponseError as e:
            msg = f"Erreur Ollama : {e.error}"
            if "not found" in str(e.error).lower():
                msg = f"Modele '{self._model}' introuvable. Executez : ollama pull {self._model}"
            logger.error(f"[LLM] {msg}")
            self.error_occurred.emit(msg)

        except Exception as e:
            err = str(e)
            if "connection" in err.lower() or "refused" in err.lower():
                msg = "Impossible de joindre Ollama. Assurez-vous qu'Ollama est demarre (ollama serve)."
            else:
                msg = f"Erreur inattendue : {err[:200]}"
            logger.exception(f"[LLM] {msg}")
            self.error_occurred.emit(msg)

    def _check_tool_call_start(self, text: str) -> bool:
        """Vérifie si le texte contient le début d'un appel d'outil."""
        for pattern in _TOOL_CALL_PATTERNS:
            if pattern.search(text):
                return True
        return False


# ══════════════════════════════════════════════════════════════════════════════
# LLMManager — Orchestrateur avec exécution silencieuse d'outils
# ══════════════════════════════════════════════════════════════════════════════

class LLMManager(QObject):
    """
    Gestionnaire de haut niveau pour les appels LLM.

    Responsabilités :
    - Créer et gérer le LLMThread
    - Connecter les signaux du thread vers le bridge (JS)
    - Intercepter les tool calls et les exécuter en silence
    - Relancer le LLM avec le résultat de l'outil (max 3 itérations)
    - Exposer response_complete pour que window.py sauvegarde en mémoire
    - Gérer les erreurs avec notifications UI
    """

    # Signal retransmis vers window.py pour sauvegarde en mémoire court-terme
    response_complete = pyqtSignal(str)

    # Signal pour informer l'UI qu'un outil est en cours d'exécution
    tool_executing = pyqtSignal(str)

    # Nombre maximum de boucles outil → LLM → outil (garde-fou anti-boucle)
    MAX_TOOL_LOOPS = 3

    # Profils de génération adaptatifs selon la nature de la tâche
    GENERATION_PROFILES = {
        "factual": {       # Recherche, faits, météo, actions système
            "temperature": 0.1,
            "top_p": 0.8,
            "top_k": 30,
            "repeat_penalty": 1.2,
            "num_predict": 1024,
        },
        "conversational": { # Discussion, opinion, général
            "temperature": 0.6,
            "top_p": 0.9,
            "top_k": 50,
            "repeat_penalty": 1.1,
            "num_predict": 1024,
        },
        "code": {          # Programmation, scripts, debug, terminal
            "temperature": 0.2,
            "top_p": 0.85,
            "top_k": 40,
            "repeat_penalty": 1.15,
            "num_predict": 2048,
        },
        "creative": {      # Histoires, poèmes, brainstorming
            "temperature": 0.8,
            "top_p": 0.95,
            "top_k": 60,
            "repeat_penalty": 1.05,
            "num_predict": 1536,
        },
    }

    # Paramètres par défaut
    GENERATION_OPTIONS = GENERATION_PROFILES["conversational"]

    # TTL du cache de la liste des modèles (2 minutes)
    CACHE_TTL_MODELS = 120.0

    def __init__(self, settings, bridge) -> None:
        super().__init__()
        self._settings = settings
        self._bridge = bridge
        self._active_model: str = settings.OLLAMA_MODEL_FAST
        self._route_mode: str = "AUTO"  # Modes: AUTO, FIXED_FAST, FIXED_ADVANCED
        self._tool_loop_count: int = 0  # Compteur de boucles outil

        # Cache de la liste des modèles installés
        self._models_cache: list[str] = []
        self._models_cache_time: float = 0.0

        # Référence vers le gestionnaire de mémoire (injectée par window.py)
        self._memory_manager = None
        self._action_manager = None

        # Créer et démarrer le thread
        self._thread = LLMThread(self)
        self._thread.configure(settings.OLLAMA_BASE_URL)
        self._thread.set_options(self.GENERATION_OPTIONS)

        # Tokens → bridge → JS (direct, sans passer par window.py)
        self._thread.token_received.connect(bridge.send_token)

        # Réponse complète → ici d'abord, puis retransmis
        self._thread.response_complete.connect(self._on_complete)

        # Tool call détecté → exécution silencieuse
        self._thread.tool_call_detected.connect(self._on_tool_call_detected)

        # Erreurs → notification + statut UI
        self._thread.error_occurred.connect(self._on_error)

        logger.info(f"[LLMManager] Initialise — modele actif: {self._active_model}")

    # ── Injection de dépendances (appelé par window.py) ──────────────────────

    def set_managers(self, memory_manager, action_manager) -> None:
        """Injecte les managers nécessaires pour l'exécution silencieuse d'outils."""
        self._memory_manager = memory_manager
        self._action_manager = action_manager

    # ── API publique ─────────────────────────────────────────────────────────

    def get_available_models(self, force_refresh: bool = False) -> list[str]:
        """Récupère la liste des modèles installés via l'API Ollama avec mise en cache TTL."""
        if not force_refresh and self._models_cache and (time.time() - self._models_cache_time < self.CACHE_TTL_MODELS):
            return self._models_cache

        try:
            client = ollama.Client(host=self._settings.OLLAMA_BASE_URL)
            response = client.list()
            models_data = getattr(response, 'models', response.get('models', [])) if isinstance(response, dict) else response.models if hasattr(response, 'models') else response
            self._models_cache = [m.model if hasattr(m, 'model') else m.get('model', '') for m in models_data]
            self._models_cache_time = time.time()
            return self._models_cache
        except Exception as e:
            logger.error(f"Erreur get_available_models: {e}")
            return self._models_cache or []

    def _detect_generation_profile(self, content: str, is_action_result: bool) -> str:
        """Détermine le profil de génération le plus adapté selon le contexte."""
        if is_action_result:
            return "factual"

        content_lower = content.lower()
        if any(kw in content_lower for kw in ["code", "script", "programme", "erreur", "bug", "terminal", "python", "javascript", "fonction", "classe", "sql"]):
            return "code"
        if any(kw in content_lower for kw in ["cherche", "internet", "web", "météo", "actualité", "trouve sur", "recherche", "heure", "date"]):
            return "factual"
        if any(kw in content_lower for kw in ["invente", "poème", "histoire", "blague", "raconte", "imagine"]):
            return "creative"

        return "conversational"

    def process(self, messages: list[dict]) -> None:
        """Lance l'inférence avec la liste de messages fournie, en choisissant le modèle et le profil adaptés."""
        if not messages:
            return

        last_msg = messages[-1]
        content = ""
        is_action_result = False
        if last_msg.get("role") == "user":
            content = last_msg.get("content", "")
            is_action_result = content.lower().startswith("[résultat action]")

        # 1. Sélection et application du profil de génération adaptatif
        profile_name = self._detect_generation_profile(content, is_action_result)
        options = dict(self.GENERATION_PROFILES.get(profile_name, self.GENERATION_OPTIONS))
        self._thread.set_options(options)
        logger.debug(f"[LLMManager] Profil de génération appliqué: {profile_name} (temp={options.get('temperature')})")

        # 2. Application du routage de modèle
        if self._route_mode == "FIXED_FAST":
            if self._active_model != self._settings.OLLAMA_MODEL_FAST:
                self.set_model(self._settings.OLLAMA_MODEL_FAST, update_ui_type="FIXE - RAPIDE")
        elif self._route_mode == "FIXED_ADVANCED":
            if self._active_model != self._settings.OLLAMA_MODEL_ADVANCED:
                self.set_model(self._settings.OLLAMA_MODEL_ADVANCED, update_ui_type="FIXE - AVANCÉ")
        elif self._route_mode == "AUTO":
            if last_msg.get("role") == "user" and not is_action_result:
                # Détection de l'intention
                is_code = profile_name == "code"
                is_search = profile_name == "factual"
                
                # Récupération dynamique des modèles (avec cache TTL)
                available_models = self.get_available_models()
                
                best_model = self._settings.OLLAMA_MODEL_FAST
                ui_type = "AUTO - RAPIDE"
                
                if is_code:
                    code_models = ["qwen", "codellama", "deepseek", "phind"]
                    found = next((m for m in available_models if any(cm in m.lower() for cm in code_models)), None)
                    if found:
                        best_model = found
                        ui_type = "AUTO - CODE"
                    else:
                        best_model = self._settings.OLLAMA_MODEL_ADVANCED
                        ui_type = "AUTO - AVANCÉ"
                        
                elif is_search:
                    tool_models = ["llama3.1", "llama3.2", "qwen2.5", "mistral-nemo"]
                    found = next((m for m in available_models if any(tm in m.lower() for tm in tool_models)), None)
                    if found:
                        best_model = found
                        ui_type = "AUTO - OUTILS/WEB"
                    else:
                        best_model = self._settings.OLLAMA_MODEL_ADVANCED
                        ui_type = "AUTO - AVANCÉ"
                        
                else:
                    fr_models = ["mistral", "mixtral", "gemma"]
                    found = next((m for m in available_models if any(fm in m.lower() for fm in fr_models)), None)
                    if found:
                        best_model = found
                        ui_type = "AUTO - FRANÇAIS"
                    else:
                        best_model = self._settings.OLLAMA_MODEL_FAST
                        ui_type = "AUTO - RAPIDE"
                        
                if self._active_model != best_model:
                    logger.info(f"[LLMManager] Routage intelligent -> {best_model} (Raison: {ui_type})")
                    self.set_model(best_model, update_ui_type=ui_type)

        self._thread.start_inference(messages, self._active_model)

    def set_model(self, model_id: str, update_ui_type: str = None) -> None:
        """Change le modèle actif et met à jour le badge dans le HUD."""
        self._active_model = model_id
        if update_ui_type is None:
            if self._route_mode == "AUTO":
                update_ui_type = "AUTO - AVANCÉ" if model_id == self._settings.OLLAMA_MODEL_ADVANCED else "AUTO - RAPIDE"
            elif self._route_mode == "FIXED_FAST":
                update_ui_type = "FIXE - RAPIDE"
            elif self._route_mode == "FIXED_ADVANCED":
                update_ui_type = "FIXE - AVANCÉ"
            else:
                update_ui_type = "CUSTOM"
                
        self._bridge.update_model_info.emit(model_id, update_ui_type)
        logger.info(f"[LLMManager] Modele change -> {model_id} ({update_ui_type})")

    def toggle_model(self) -> None:
        """Bascule (cycle) entre les 3 modes de routage : AUTO -> FIXED_FAST -> FIXED_ADVANCED -> AUTO"""
        if self._route_mode == "AUTO":
            self._route_mode = "FIXED_FAST"
            self.set_model(self._settings.OLLAMA_MODEL_FAST, "FIXE - RAPIDE")
        elif self._route_mode == "FIXED_FAST":
            self._route_mode = "FIXED_ADVANCED"
            self.set_model(self._settings.OLLAMA_MODEL_ADVANCED, "FIXE - AVANCÉ")
        else:
            self._route_mode = "AUTO"
            self.set_model(self._settings.OLLAMA_MODEL_FAST, "AUTO - RAPIDE")

    def set_route_mode(self, mode: str) -> None:
        """Définit explicitement le mode de routage ou force un modèle spécifique."""
        mode_lower = mode.lower()
        if mode_lower == "auto":
            self._route_mode = "AUTO"
            self.set_model(self._settings.OLLAMA_MODEL_FAST, "AUTO - RAPIDE")
        elif mode_lower == "fast":
            self._route_mode = "FIXED_FAST"
            self.set_model(self._settings.OLLAMA_MODEL_FAST, "FIXE - RAPIDE")
        elif mode_lower == "advanced":
            self._route_mode = "FIXED_ADVANCED"
            self.set_model(self._settings.OLLAMA_MODEL_ADVANCED, "FIXE - AVANCÉ")
        else:
            # C'est le nom exact d'un modèle choisi depuis le menu dynamique
            self._route_mode = "FIXED_CUSTOM"
            self.set_model(mode, f"CUSTOM")

    def cancel(self) -> None:
        """Annule l'inférence en cours."""
        self._thread.cancel()
        self._tool_loop_count = 0  # Reset du compteur

    @property
    def active_model(self) -> str:
        return self._active_model

    # ── Handlers privés ──────────────────────────────────────────────────────

    def _on_complete(self, full_text: str) -> None:
        """Retransmet la réponse complète vers window.py (pour la mémoire)."""
        self._tool_loop_count = 0  # Reset du compteur après une réponse propre
        self.response_complete.emit(full_text)

    def _on_tool_call_detected(self, full_response: str, text_before_tool: str) -> None:
        """
        Appelé quand le LLMThread détecte un tool call dans le stream.
        Exécute l'outil en silence et relance le LLM avec le résultat.
        """
        if not self._action_manager or not self._memory_manager:
            logger.warning("[LLMManager] Managers non injectés — impossible d'exécuter le tool call.")
            # Fallback : émettre le texte avant le tool call comme réponse
            cleaned = sanitize_response(text_before_tool) if text_before_tool else "Je n'ai pas pu traiter cette demande."
            self.response_complete.emit(cleaned)
            return

        # Garde-fou anti-boucle
        self._tool_loop_count += 1
        if self._tool_loop_count > self.MAX_TOOL_LOOPS:
            logger.warning(f"[LLMManager] Limite de boucles outils atteinte ({self.MAX_TOOL_LOOPS}). Arrêt.")
            self._tool_loop_count = 0
            cleaned = sanitize_response(text_before_tool) if text_before_tool else "Je n'ai pas pu compléter cette action."
            self.response_complete.emit(cleaned)
            return

        # Parser les tool calls
        calls, clean_text = self._action_manager.parse_and_clean(full_response)

        if not calls:
            logger.warning("[LLM] Faux positif de tool call détecté — aucun appel valide extrait.")
            self._tool_loop_count = 0
            cleaned = sanitize_response(full_response)
            self.response_complete.emit(cleaned)
            return

        logger.info(f"[LLMManager] Exécution silencieuse de {len(calls)} outil(s) (boucle {self._tool_loop_count}/{self.MAX_TOOL_LOOPS})")

        # Émettre le texte propre avant le tool call (s'il y en a)
        if text_before_tool and text_before_tool.strip():
            cleaned_before = sanitize_response(text_before_tool)
            if cleaned_before:
                self._bridge.send_token.emit(cleaned_before)

        # Informer l'UI qu'un outil s'exécute
        tool_name = calls[0].get("tool", "inconnu")
        self.tool_executing.emit(tool_name)

        # Exécuter les outils
        is_safe, result = self._action_manager.process_calls(calls)

        if is_safe and result:
            # Outil SAFE exécuté → injecter le résultat et relancer le LLM
            if clean_text:
                self._memory_manager.add("assistant", clean_text, model_used=self._active_model)
            self._memory_manager.add("user", result, model_used="SYSTEM")

            # Relancer le LLM avec le contexte enrichi
            self._bridge.update_status.emit("thinking")
            messages = self._memory_manager.get_messages_for_llm(result)
            self._thread.start_inference(messages, self._active_model)
        elif not is_safe and result:
            # Action MODERATE en attente de confirmation utilisateur
            self._tool_loop_count = 0
            if clean_text:
                self._memory_manager.add("assistant", clean_text, model_used=self._active_model)
            token_count = len(full_response) // 4
            self._bridge.send_message_complete.emit(
                sanitize_response(clean_text) if clean_text else "",
                self._active_model,
                token_count
            )
            self._bridge.update_status.emit("idle")
        else:
            # Rien à faire — émettre la réponse nettoyée
            self._tool_loop_count = 0
            cleaned = sanitize_response(full_response)
            self.response_complete.emit(cleaned)

    def _on_error(self, error_msg: str) -> None:
        """Gère les erreurs : met à jour le statut et affiche une notification."""
        self._tool_loop_count = 0
        self._bridge.update_status.emit("error")
        self._bridge.llm_error.emit(error_msg)
        self._bridge.show_notification.emit("Erreur IA", error_msg[:120])

    # ── Nettoyage ─────────────────────────────────────────────────────────────

    def cleanup(self) -> None:
        """Arrête proprement le thread LLM à la fermeture de l'application."""
        if self._thread.isRunning():
            self._thread.cancel()
            self._thread.wait(3000)
        logger.info("[LLMManager] Nettoye.")
