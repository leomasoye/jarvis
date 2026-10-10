import os
import urllib.request
import logging
from pathlib import Path
from piper import PiperVoice
from config.settings import Settings

logger = logging.getLogger(__name__)

class TTS:
    """
    Text-To-Speech utilisant Piper.
    Télécharge automatiquement le modèle FR s'il n'est pas présent.
    """

    MODEL_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/fr/fr_FR/upmc/medium/fr_FR-upmc-medium.onnx"
    CONFIG_URL = MODEL_URL + ".json"

    def __init__(self, settings: Settings) -> None:
        self.model_path = Path(settings.PIPER_MODEL_PATH)
        self.config_path = Path(str(self.model_path) + ".json")
        
        self._ensure_model_exists()
        
        logger.info(f"[TTS] Chargement du modèle Piper : {self.model_path.name}...")
        self.voice = PiperVoice.load(str(self.model_path), str(self.config_path))
        logger.info("[TTS] Modèle Piper prêt.")

    def _ensure_model_exists(self) -> None:
        """Télécharge le modèle et sa configuration s'ils sont introuvables."""
        if self.model_path.exists() and self.config_path.exists():
            return
            
        logger.info(f"[TTS] Le modèle {self.model_path.name} est introuvable. Téléchargement en cours...")
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            if not self.model_path.exists():
                logger.info(f"Téléchargement de {self.MODEL_URL}...")
                urllib.request.urlretrieve(self.MODEL_URL, str(self.model_path))
                
            if not self.config_path.exists():
                logger.info(f"Téléchargement de {self.CONFIG_URL}...")
                urllib.request.urlretrieve(self.CONFIG_URL, str(self.config_path))
                
            logger.info("[TTS] Téléchargement terminé avec succès.")
        except Exception as e:
            logger.error(f"[TTS] Erreur lors du téléchargement du modèle Piper : {e}")
            raise

    def generate_audio(self, text: str) -> bytes:
        """
        Génère les données audio (PCM) à partir du texte.
        
        Args:
            text: Le texte à lire.
            
        Returns:
            Le flux audio PCM en bytes (par défaut mono, 16kHz ou 22kHz selon le modèle).
        """
        if not text.strip():
            return b""
            
        try:
            # synthesize_stream retourne un générateur de bytes
            audio_stream = self.voice.synthesize_stream_raw(text)
            audio_data = b"".join(list(audio_stream))
            return audio_data
        except Exception as e:
            logger.error(f"[TTS] Erreur lors de la synthèse vocale : {e}")
            return b""
