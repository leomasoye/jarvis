"""
JARVIS — Classe principale de l'application PyQt6.
Consulter contexte_projet.md §4 pour l'architecture globale.
"""
import logging
import sys
from typing import Optional

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSharedMemory
from PyQt6.QtGui import QPalette, QColor, QIcon

from config.settings import Settings
from core.window import MainWindow

logger = logging.getLogger(__name__)


class JarvisApp(QApplication):
    """
    Application PyQt6 principale de Jarvis.

    Responsabilités :
    - Configurer le thème sombre global (palette Qt)
    - Initialiser et afficher la MainWindow
    """

    def __init__(self, argv: list[str], settings: Settings) -> None:
        super().__init__(argv)
        self.settings = settings
        self.is_duplicate: bool = False
        self.main_window: Optional[MainWindow] = None

        self._lock = QSharedMemory("Jarvis_Instance_Lock")
        if not self._lock.create(1):
            logger.warning("JARVIS est déjà en cours d'exécution. Arrêt immédiat.")
            self.is_duplicate = True
            return

        self._configure_qt()
        self._apply_dark_palette()
        self._set_app_icon()
        self.main_window = MainWindow(settings)
        self.main_window.showFullScreen()
        logger.info("JarvisApp démarrée.")

    def _set_app_icon(self) -> None:
        """Charge et applique l'icône JARVIS à l'application et à toutes les fenêtres."""
        ext = "ico" if sys.platform == "win32" else "png"
        icon_path = self.settings.ROOT_DIR / "assets" / f"icon.{ext}"
        if not icon_path.exists():
            icon_path = self.settings.ROOT_DIR / "assets" / "icon.png"
            
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
            logger.debug(f"Icône de l'application ({icon_path.name}) chargée avec succès.")
        else:
            logger.warning(f"L'icône {icon_path} est introuvable.")

    def _configure_qt(self) -> None:
        """Configure les attributs globaux de l'application Qt."""
        self.setApplicationName(self.settings.APP_NAME)
        self.setApplicationVersion(self.settings.APP_VERSION)
        self.setOrganizationName("JARVIS")
        logger.debug("Configuration Qt appliquée.")

    def _apply_dark_palette(self) -> None:
        """Applique une palette de couleurs sombre à toute l'application Qt."""
        palette = QPalette()

        # Fond principal — noir quasi-total
        dark_bg = QColor("#060810")
        dark_alt = QColor("#0a0e1a")
        text_color = QColor("#e2e8f0")
        muted_text = QColor("#94a3b8")
        accent = QColor("#00d4ff")
        border = QColor("#1e2a3a")

        palette.setColor(QPalette.ColorRole.Window, dark_bg)
        palette.setColor(QPalette.ColorRole.WindowText, text_color)
        palette.setColor(QPalette.ColorRole.Base, dark_alt)
        palette.setColor(QPalette.ColorRole.AlternateBase, dark_bg)
        palette.setColor(QPalette.ColorRole.ToolTipBase, dark_alt)
        palette.setColor(QPalette.ColorRole.ToolTipText, text_color)
        palette.setColor(QPalette.ColorRole.Text, text_color)
        palette.setColor(QPalette.ColorRole.Button, dark_alt)
        palette.setColor(QPalette.ColorRole.ButtonText, text_color)
        palette.setColor(QPalette.ColorRole.BrightText, accent)
        palette.setColor(QPalette.ColorRole.Link, accent)
        palette.setColor(QPalette.ColorRole.Highlight, accent)
        palette.setColor(QPalette.ColorRole.HighlightedText, dark_bg)
        palette.setColor(QPalette.ColorRole.PlaceholderText, muted_text)
        palette.setColor(QPalette.ColorRole.Mid, border)
        palette.setColor(QPalette.ColorRole.Dark, dark_bg)
        palette.setColor(QPalette.ColorRole.Shadow, QColor("#000000"))

        self.setPalette(palette)
        self.setStyle("Fusion")
        logger.debug("Palette sombre appliquée.")
