"""
JARVIS — Fenêtre principale de l'application.

Contient :
- QWebEngineView (moteur Chromium, affiche le HUD HTML/CSS/JS)
- QWebChannel (bridge bidirectionnel JS <-> Python)
- JarvisBridge (objet Python exposé au JS)
- LLMManager + ShortTermMemory (Étape 2)

Consulter contexte_projet.md §4 pour l'architecture globale.
"""
import logging
from pathlib import Path

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PyQt6.QtWebChannel import QWebChannel

from config.settings import Settings
from core.bridge import JarvisBridge
from ai.llm_manager import LLMManager
from memory.memory_manager import MemoryManager
from audio.audio_thread import AudioThread
from core.system_monitor import SystemMonitor
from ai.action_manager import ActionManager

logger = logging.getLogger(__name__)


class JarvisPage(QWebEnginePage):
    """
    Page WebEngine personnalisée.
    Redirige les messages console JavaScript vers le logger Python.
    """

    def javaScriptConsoleMessage(
        self,
        level: QWebEnginePage.JavaScriptConsoleMessageLevel,
        message: str | None,
        lineNumber: int,
        sourceID: str | None,
    ) -> None:
        level_names = {
            QWebEnginePage.JavaScriptConsoleMessageLevel.InfoMessageLevel:    "INFO",
            QWebEnginePage.JavaScriptConsoleMessageLevel.WarningMessageLevel: "WARN",
            QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel:   "ERROR",
        }
        lvl = level_names.get(level, "DBG")
        src = (sourceID or "").split("/")[-1] if sourceID else "?"
        msg = message or ""
        logger.debug(f"[JS:{lvl}] {src}:{lineNumber} > {msg}")


class MainWindow(QMainWindow):
    """
    Fenêtre principale de Jarvis.

    Initialise (dans l'ordre) :
    1. La fenêtre native PyQt6
    2. QWebEngineView + page HUD
    3. QWebChannel + JarvisBridge
    4. LLMManager + ShortTermMemory  (Étape 2)
    5. Raccourcis clavier
    6. Chargement du HUD HTML
    """

    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self.settings = settings
        self._setup_window()
        self._setup_webengine()
        self._setup_bridge()
        self._setup_llm()
        self._setup_audio()
        self._setup_monitor()
        self._setup_shortcuts()
        self._load_hud()

        logger.info("MainWindow prete.")

    # ══════════════════════════════════════════════════════════════════════════
    # Initialisation
    # ══════════════════════════════════════════════════════════════════════════

    def _setup_window(self) -> None:
        self.setWindowTitle(f"{self.settings.APP_NAME}  v{self.settings.APP_VERSION}")
        self.setMinimumSize(1280, 720)
        self.setStyleSheet("QMainWindow { background-color: #060810; }")
        from PyQt6.QtGui import QIcon
        icon_path = self.settings.ROOT_DIR / "assets" / "icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.showMaximized()

    def _setup_webengine(self) -> None:
        """Crée le QWebEngineView et configure les paramètres de sécurité."""
        self.web_view = QWebEngineView(self)
        self.web_page = JarvisPage(self.web_view)
        self.web_view.setPage(self.web_page)
        self.web_view.setStyleSheet("background-color: #060810;")

        ws = self.web_page.settings()
        if ws is not None:
            ws.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
            ws.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
            ws.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.web_view)
        self.setCentralWidget(container)
        logger.debug("QWebEngineView configure.")

    def _setup_bridge(self) -> None:
        """Configure QWebChannel et expose le bridge au JavaScript."""
        self.bridge = JarvisBridge(self)
        self.channel = QWebChannel(self.web_page)
        self.channel.registerObject("jarvis", self.bridge)
        self.web_page.setWebChannel(self.channel)
        
        # Connecte le signal js_ready pour finaliser le démarrage
        self.bridge.js_ready.connect(self._on_system_ready)
        
        logger.debug("QWebChannel pret — objet 'jarvis' enregistre.")

    def _setup_llm(self) -> None:
        """
        Initialise la couche LLM :
        - Charge le system prompt depuis config/system_prompt.txt
        - Crée la mémoire court-terme
        - Crée le LLMManager et connecte tous les signaux
        """
        # 1. Action Manager (Étape 6)
        self.action_manager = ActionManager(self.bridge)

        # 2. System prompt & Persona
        system_prompt = self._load_system_prompt()
        persona = self._load_persona()

        # 3. Gestionnaire de mémoire (court et long terme)
        self.memory_manager = MemoryManager(self.settings, self.action_manager)
        self.memory_manager.set_system_prompt(system_prompt, persona=persona)
        self.action_manager.set_db(self.memory_manager.db, self.memory_manager.session_id)

        # 4. LLM Manager (connecte token_received -> bridge.send_token en interne)
        self.llm_manager = LLMManager(self.settings, self.bridge)

        # 5. Injection des managers pour l'exécution silencieuse d'outils
        self.llm_manager.set_managers(self.memory_manager, self.action_manager)

        # 6. Connexions bridge <-> window
        # Message utilisateur -> process LLM
        self.bridge.user_message_received.connect(self._handle_user_message)

        # Changement de modèle
        self.bridge.model_toggle_requested.connect(self.llm_manager.toggle_model)
        self.bridge.model_change_requested.connect(self.llm_manager.set_route_mode)

        # Effacement du contexte
        self.bridge.clear_context_requested.connect(self._handle_clear_context)

        # Annulation de la génération
        self.bridge.cancel_requested.connect(self._handle_cancel)

        # Réponse complète -> sauvegarde en mémoire + reset statut
        self.llm_manager.response_complete.connect(self._handle_response_complete)

        # Outil en cours d'exécution -> notification UI
        self.llm_manager.tool_executing.connect(self._handle_tool_executing)

        # Actions (Étape 6 — confirmation utilisateur)
        self.bridge.action_confirmed.connect(self._handle_action_confirmed)
        self.bridge.action_cancelled_sig.connect(self._handle_action_cancelled)

        logger.info("[LLM] Setup complet.")

    def _setup_audio(self) -> None:
        """Initialise le thread audio pour STT et TTS."""
        self.audio_thread = AudioThread(self.settings, self)
        
        # Connexions Bridge -> AudioThread
        self.bridge.voice_toggled.connect(self.audio_thread.toggle_listening)
        
        # Connexions AudioThread -> UI + LLM
        self.audio_thread.stt_transcription_ready.connect(self._handle_stt_transcription)
        self.audio_thread.audio_level_update.connect(self.bridge.audio_level_update.emit)
        
        # Connexions LLM -> AudioThread (TTS)
        self.llm_manager.response_complete.connect(self.audio_thread.speak)
        
        self.audio_thread.start()
        logger.info("[Audio] Setup complet.")

    def _setup_monitor(self) -> None:
        """Initialise le moniteur système (CPU/RAM)."""
        self.system_monitor = SystemMonitor(update_interval_ms=2000, parent=self)
        self.system_monitor.stats_updated.connect(self.bridge.update_system_stats.emit)
        self.system_monitor.start()
        logger.info("[SystemMonitor] Setup complet.")

    def _setup_shortcuts(self) -> None:
        """Raccourcis clavier de débogage."""
        reload_sc = QShortcut(QKeySequence("F5"), self)
        reload_sc.activated.connect(self.web_view.reload)

        devtools_sc = QShortcut(QKeySequence("F12"), self)
        devtools_sc.activated.connect(self._open_devtools)

    def _load_hud(self) -> None:
        """Charge la page HTML du HUD depuis ui/web/index.html."""
        index_path: Path = self.settings.UI_DIR / "index.html"
        if not index_path.exists():
            logger.error(f"HUD introuvable : {index_path}")
            return
        self.web_view.load(QUrl.fromLocalFile(str(index_path.resolve())))
        logger.info(f"HUD charge -> {index_path}")

    # ══════════════════════════════════════════════════════════════════════════
    # Handlers de messages
    # ══════════════════════════════════════════════════════════════════════════

    def _handle_stt_transcription(self, text: str) -> None:
        """Appelé par AudioThread quand une transcription est prête."""
        # 1. L'afficher dans l'UI
        self.bridge.add_user_message_ui.emit(text)
        # 2. Le traiter comme un message normal
        self._handle_user_message(text)

    def _handle_user_message(self, message: str) -> None:
        """
        Reçoit un message utilisateur depuis le bridge :
        1. Le stocke en mémoire
        2. Met le statut en 'thinking'
        3. Lance l'inférence LLM avec le contexte complet
        """
        self.memory_manager.add("user", message, model_used=self.llm_manager.active_model)
        self.bridge.update_status.emit("thinking")
        messages = self.memory_manager.get_messages_for_llm(message)
        logger.info(f"[Window] Traitement : {message[:80]!r} ({len(messages)} msg contexte)")
        self.llm_manager.process(messages)

    def _handle_response_complete(self, full_text: str) -> None:
        """
        Reçoit la réponse complète du LLM (déjà nettoyée par le buffer LLMThread).
        Le parsing des tool calls est maintenant géré en amont par LLMManager.
        
        Responsabilités restantes :
        1. Stocker le texte en mémoire
        2. Envoyer le signal de fin au JS
        3. Remettre le statut en idle
        """
        # Nettoyage résiduel (balises qui auraient échappé au buffer)
        _, clean_text = self.action_manager.parse_and_clean(full_text)
        clean_text = clean_text or full_text
        
        if clean_text.strip():
            self.memory_manager.add("assistant", clean_text, model_used=self.llm_manager.active_model)
        
        token_count = len(full_text) // 4
        self.bridge.send_message_complete.emit(clean_text, self.llm_manager.active_model, token_count)

        self.bridge.update_status.emit("idle")
        logger.info(
            f"[Window] Reponse stockee ({len(clean_text)} chars) — "
            f"contexte: {self.memory_manager.short_term.message_count} messages."
        )

    def _handle_tool_executing(self, tool_name: str) -> None:
        """Informer l'UI qu'un outil est en cours d'exécution silencieuse."""
        self.bridge.show_notification.emit("Outil en cours", f"Exécution de '{tool_name}'...")
        logger.info(f"[Window] Exécution silencieuse de l'outil : {tool_name}")

    def _handle_action_confirmed(self, action_id: str) -> None:
        """Exécute l'action confirmée, puis relance le LLM avec le résultat."""
        result = self.action_manager.execute_pending(action_id)
        self.memory_manager.add("user", f"[RÉSULTAT ACTION]\n{result}", model_used="SYSTEM")
        self.bridge.update_status.emit("thinking")
        messages = self.memory_manager.get_messages_for_llm("Action exécutée.")
        self.llm_manager.process(messages)

    def _handle_action_cancelled(self, action_id: str) -> None:
        """Annule l'action et prévient le LLM."""
        if action_id in self.action_manager.pending_actions:
            del self.action_manager.pending_actions[action_id]
        self.memory_manager.add("user", "[L'utilisateur a annulé l'action]", model_used="SYSTEM")
        self.bridge.update_status.emit("thinking")
        messages = self.memory_manager.get_messages_for_llm("Action annulée.")
        self.llm_manager.process(messages)

    def _handle_clear_context(self) -> None:
        """Vide la mémoire de session et notifie l'UI."""
        self.memory_manager.clear_context()
        self.bridge.show_notification.emit("Contexte effacé", "La conversation a été réinitialisée.")

    def _handle_cancel(self) -> None:
        """Annule la génération et remet le statut en idle."""
        self.llm_manager.cancel()
        self.bridge.update_status.emit("idle")
        logger.info("[Window] Generation annulee.")

    # ══════════════════════════════════════════════════════════════════════════
    # Démarrage / Nettoyage
    # ══════════════════════════════════════════════════════════════════════════

    def _on_system_ready(self) -> None:
        """Émis 2.5s après le boot — notifie l'UI que tout est prêt."""
        model = self.llm_manager.active_model
        self.bridge.update_status.emit("idle")
        self.bridge.update_model_info.emit(model, "AUTO - RAPIDE")
        self.bridge.show_notification.emit(
            "Systeme pret",
            f"JARVIS est operationnel. Modele : {model}"
        )

    def _load_system_prompt(self) -> str:
        """Charge le system prompt depuis config/system_prompt.txt."""
        prompt_path = self.settings.CONFIG_DIR / "system_prompt.txt"
        if prompt_path.exists():
            content = prompt_path.read_text(encoding="utf-8").strip()
            logger.info(f"[Window] System prompt charge ({len(content)} chars).")
            return content
        logger.warning("[Window] system_prompt.txt introuvable — prompt vide.")
        return ""

    def _load_persona(self) -> str:
        """Charge le persona de l'IA depuis config/persona.md."""
        persona_path = self.settings.CONFIG_DIR / "persona.md"
        if persona_path.exists():
            content = persona_path.read_text(encoding="utf-8").strip()
            logger.info(f"[Window] Persona charge ({len(content)} chars).")
            return content
        return ""

    def _open_devtools(self) -> None:
        """Ouvre les DevTools Chromium dans une fenêtre séparée."""
        self._devtools_view = QWebEngineView()
        self._devtools_view.setWindowTitle("JARVIS — DevTools")
        self._devtools_view.resize(1200, 800)
        self.web_page.setDevToolsPage(self._devtools_view.page())
        self._devtools_view.show()
        logger.debug("DevTools ouverts.")

    def closeEvent(self, a0) -> None:
        """Nettoyage à la fermeture : sauvegarde mémoire et arrêt propre du LLM."""
        logger.info("Fermeture de MainWindow — sauvegarde mémoire et nettoyage LLM...")
        if hasattr(self, 'audio_thread'):
            self.audio_thread.cleanup()
        self.memory_manager.summarize_and_save_session(self.llm_manager.active_model)
        self.llm_manager.cleanup()
        super().closeEvent(a0)
