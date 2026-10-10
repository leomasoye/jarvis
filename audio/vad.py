import numpy as np
import logging

logger = logging.getLogger(__name__)

class VAD:
    """
    Voice Activity Detection basé sur l'énergie RMS du signal audio.
    Détecte les silences prolongés pour signaler la fin d'une phrase.
    """

    def __init__(self, threshold: float = 0.02, silence_duration: float = 1.5, sample_rate: int = 16000) -> None:
        """
        Args:
            threshold: Le seuil d'énergie au-dessus duquel on considère qu'il y a de la voix.
            silence_duration: Temps de silence en secondes avant de considérer la parole comme terminée.
            sample_rate: La fréquence d'échantillonnage de l'audio.
        """
        self.threshold = threshold
        self.silence_frames_threshold = int(silence_duration * sample_rate)
        self.silence_counter = 0
        self.is_speaking = False

    def process_chunk(self, audio_chunk: np.ndarray) -> bool:
        """
        Analyse un chunk audio et retourne True si l'utilisateur vient de terminer de parler.
        
        Args:
            audio_chunk: Tableau numpy contenant l'audio float32 (-1.0 à 1.0).
            
        Returns:
            bool: True si une fin de phrase (silence prolongé après parole) est détectée, sinon False.
        """
        if len(audio_chunk) == 0:
            return False

        # Calcul de l'énergie RMS
        rms = np.sqrt(np.mean(np.square(audio_chunk)))

        if rms > self.threshold:
            self.is_speaking = True
            self.silence_counter = 0
        else:
            if self.is_speaking:
                self.silence_counter += len(audio_chunk)

        # Si le silence dépasse la durée définie et qu'on était en train de parler
        if self.is_speaking and self.silence_counter >= self.silence_frames_threshold:
            logger.debug("[VAD] Fin de parole détectée.")
            self.reset()
            return True

        return False

    def reset(self) -> None:
        """Réinitialise l'état du VAD."""
        self.is_speaking = False
        self.silence_counter = 0
