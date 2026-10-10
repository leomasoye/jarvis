"""
JARVIS — Bridge QWebChannel (Python ↔ JavaScript).

Objet Python exposé à JavaScript via QWebChannel.
Consulter contexte_projet.md §7.1 pour la documentation du protocole.

Signaux (Python → JS) :
    send_token(str)                  Streaming token par token
    send_message_complete(str)       Message IA complet reçu
    send_render_directive(str, str)  Rendu spécial (type, contenu) — Étape 5
    update_status(str)               Statut IA : idle/thinking/speaking/listening/error
    show_notification(str, str)      Toast notification (titre, message)
    update_model_info(str, str)      Info modèle actif (nom, type)
    llm_error(str)                   Erreur LLM (affiché dans le chat)
    action_requires_confirmation(str) Action PC à confirmer — Étape 6

Signaux internes (Python → Python — pour window.py) :
    user_message_received(str)       Message texte de l'utilisateur
    model_change_requested(str)      Changement de modèle demandé
    clear_context_requested()        Effacement du contexte demandé
    cancel_requested()               Annulation de la génération

Slots (JS → Python) :
    on_user_message(str)
    on_toggle_voice()
    on_change_model(str)
    on_clear_context()
    on_cancel_message()
    on_confirm_action(str)
    on_cancel_action(str)
    on_minimize_window()
    on_close_window()
    on_js_log(str)
"""
import logging
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

logger = logging.getLogger(__name__)


class JarvisBridge(QObject):
    """Objet Python exposé à JavaScript via QWebChannel."""

    # ── Signaux Python → JavaScript (visibles depuis le JS) ──────────────────

    # Étape 2 : Streaming LLM
    send_token            = pyqtSignal(str)
    send_message_complete = pyqtSignal(str, str, int)
    llm_error             = pyqtSignal(str)

    # Étape 5 : Rendu dynamique
    send_render_directive = pyqtSignal(str, str)

    # Étape 1+ : Interface
    update_status     = pyqtSignal(str)
    show_notification = pyqtSignal(str, str)
    update_model_info = pyqtSignal(str, str)
    add_user_message_ui = pyqtSignal(str)
    llm_error         = pyqtSignal(str)
    update_system_stats = pyqtSignal(int, int)

    # [NOUVEAU] Niveau audio en temps réel pour l'UI
    audio_level_update = pyqtSignal(float)

    # Étape 6 : Actions PC
    action_requires_confirmation = pyqtSignal(str)
    action_executed_success      = pyqtSignal(str)
    action_executed_error        = pyqtSignal(str)

    # Signal de synchronisation
    js_ready = pyqtSignal()
    
    # Étape LLM Models dynamique
    models_list_ready = pyqtSignal(str)

    # ── Signaux internes Python → Python (pour window.py) ────────────────────
    # (non exposés au JS, mais utilisés via connexions PyQt6)

    user_message_received  = pyqtSignal(str)
    model_toggle_requested = pyqtSignal()
    model_change_requested = pyqtSignal(str)
    clear_context_requested = pyqtSignal()
    cancel_requested       = pyqtSignal()
    voice_toggled          = pyqtSignal()
    action_confirmed       = pyqtSignal(str)
    action_cancelled_sig   = pyqtSignal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        logger.debug("JarvisBridge initialisé.")

    # ── Slots JavaScript → Python ─────────────────────────────────────────────

    @pyqtSlot(str)
    def on_user_message(self, message: str) -> None:
        """Reçoit un message texte de l'utilisateur et le retransmet en interne."""
        if not message.strip():
            return
        logger.info(f"[Bridge] Message : {message[:100]!r}")
        self.user_message_received.emit(message.strip())

    @pyqtSlot()
    def on_toggle_voice(self) -> None:
        """Bascule l'entrée vocale."""
        logger.info("[Bridge] Toggle vocal.")
        self.voice_toggled.emit()

    @pyqtSlot()
    def on_toggle_model(self) -> None:
        """Demande à basculer entre le modèle rapide et avancé."""
        logger.info("[Bridge] Demande de basculement de modèle.")
        self.model_toggle_requested.emit()

    @pyqtSlot(str)
    def on_change_model(self, model_type: str) -> None:
        """Demande à basculer vers un modèle spécifique (auto, fast, advanced)."""
        logger.info(f"[Bridge] Demande de modèle spécifique : {model_type}")
        self.model_change_requested.emit(model_type)

    @pyqtSlot()
    def on_clear_context(self) -> None:
        """Vide le contexte de conversation."""
        logger.info("[Bridge] Effacement du contexte.")
        self.clear_context_requested.emit()

    @pyqtSlot()
    def on_cancel_message(self) -> None:
        """Annule la génération en cours."""
        logger.info("[Bridge] Annulation de la generation.")
        self.cancel_requested.emit()

    @pyqtSlot(str)
    def on_confirm_action(self, action_id: str) -> None:
        """L'utilisateur confirme une action PC."""
        logger.info(f"[Bridge] Action confirmee : {action_id}")
        self.action_confirmed.emit(action_id)

    @pyqtSlot(str)
    def on_cancel_action(self, action_id: str) -> None:
        """L'utilisateur annule une action PC."""
        logger.info(f"[Bridge] Action annulee : {action_id}")
        self.action_cancelled_sig.emit(action_id)

    @pyqtSlot()
    def on_minimize_window(self) -> None:
        """Minimise la fenêtre (mode frameless)."""
        if self.parent() and hasattr(self.parent(), "showMinimized"):
            self.parent().showMinimized()

    @pyqtSlot()
    def on_close_window(self) -> None:
        """Ferme l'application proprement."""
        from PyQt6.QtWidgets import QApplication
        logger.info("[Bridge] Fermeture depuis le JS.")
        QApplication.quit()

    @pyqtSlot()
    def on_fetch_models(self) -> None:
        """Récupère la liste des modèles installés et les envoie au JS."""
        import ollama
        import json
        from config.settings import Settings
        
        try:
            client = ollama.Client(host=Settings.OLLAMA_BASE_URL)
            response = client.list()
            # Selon la version du SDK python, response.models ou response['models']
            models_data = getattr(response, 'models', response.get('models', [])) if isinstance(response, dict) else response.models if hasattr(response, 'models') else response
            
            models = []
            for m in models_data:
                name = m.model if hasattr(m, 'model') else m.get('model', 'unknown')
                details = m.details if hasattr(m, 'details') else m.get('details', {})
                param_size = details.parameter_size if hasattr(details, 'parameter_size') else details.get('parameter_size', '?B')
                
                models.append({
                    "name": name,
                    "param_size": param_size
                })
            
            self.models_list_ready.emit(json.dumps(models))
        except Exception as e:
            logger.error(f"[Bridge] Erreur lors de la récupération des modèles: {e}")
            self.models_list_ready.emit("[]")

    @pyqtSlot(str)
    def on_js_log(self, message: str) -> None:
        """Reçoit les logs du frontend JS."""
        logger.debug(f"[JS] {message}")
        if "HUD opérationnel" in message:
            self.js_ready.emit()
