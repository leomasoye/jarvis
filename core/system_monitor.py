import psutil
import logging
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

logger = logging.getLogger(__name__)

class SystemMonitor(QObject):
    """
    Moniteur système qui lit l'état du CPU et de la RAM
    en temps réel et émet un signal avec les pourcentages.
    """
    
    # Émet (cpu_percent, ram_percent)
    stats_updated = pyqtSignal(int, int)

    def __init__(self, update_interval_ms: int = 2000, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setInterval(update_interval_ms)
        self._timer.timeout.connect(self._fetch_stats)
        
        # Initialiser psutil cpu_percent (le premier appel retourne 0.0)
        psutil.cpu_percent()
        logger.info(f"[SystemMonitor] Démarré (intervalle: {update_interval_ms}ms)")

    def start(self) -> None:
        self._timer.start()
        
    def stop(self) -> None:
        self._timer.stop()

    def _fetch_stats(self) -> None:
        cpu = int(psutil.cpu_percent())
        ram = int(psutil.virtual_memory().percent)
        self.stats_updated.emit(cpu, ram)
