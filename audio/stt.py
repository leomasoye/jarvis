import logging
import numpy as np
from faster_whisper import WhisperModel
from config.settings import Settings

logger = logging.getLogger(__name__)

class STT:
    """
    Speech-To-Text utilisant Faster-Whisper.
    """

    def __init__(self, settings: Settings) -> None:
        self.model_size = settings.WHISPER_MODEL_SIZE
        self.compute_type = settings.WHISPER_COMPUTE_TYPE
        
        logger.info(f"[STT] Initialisation du modèle Whisper '{self.model_size}' sur CPU ({self.compute_type})...")
        # On force l'utilisation du CPU pour ce projet (comme demandé dans le cahier des charges)
        self.model = WhisperModel(self.model_size, device="cpu", compute_type=self.compute_type)
        logger.info("[STT] Modèle Whisper prêt.")

    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        """
        Transcrit un tableau audio numpy en texte.
        
        Args:
            audio_data: Le flux audio (float32).
            sample_rate: Fréquence d'échantillonnage (doit être 16000 pour Whisper).
            
        Returns:
            Le texte transcrit.
        """
        if len(audio_data) == 0:
            return ""

        try:
            # Whisper attend un tableau float32 1D à 16kHz
            segments, info = self.model.transcribe(audio_data, beam_size=5, language="fr")
            
            text = "".join(segment.text for segment in segments).strip()
            if text:
                logger.debug(f"[STT] Transcrit : {text}")
            return text
        except Exception as e:
            logger.error(f"[STT] Erreur de transcription : {e}")
            return ""
