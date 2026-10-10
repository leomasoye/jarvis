import logging
import queue
import numpy as np
import sounddevice as sd
from PyQt6.QtCore import QThread, pyqtSignal, QObject
from config.settings import Settings
from audio.vad import VAD
from audio.stt import STT
from audio.tts import TTS

logger = logging.getLogger(__name__)

class AudioThread(QThread):
    """
    Thread dédié à la gestion audio (Microphone -> VAD -> STT) et (Texte -> TTS -> Haut-parleur).
    """

    stt_transcription_ready = pyqtSignal(str)
    audio_level_update = pyqtSignal(float)
    
    def __init__(self, settings: Settings, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.sample_rate = settings.AUDIO_SAMPLE_RATE
        
        self.stt = STT(settings)
        self.tts = TTS(settings)
        self.vad = VAD(threshold=settings.VAD_THRESHOLD, sample_rate=self.sample_rate)
        
        self.audio_queue: queue.Queue = queue.Queue()
        self.is_listening = False
        self.is_running = True
        self.audio_buffer = []
        
        self.stream = None

    def toggle_listening(self) -> None:
        """Active ou désactive l'écoute du microphone."""
        self.is_listening = not self.is_listening
        if self.is_listening:
            logger.info("[Audio] Écoute activée.")
            self._start_stream()
        else:
            logger.info("[Audio] Écoute désactivée.")
            self._stop_stream()

    def speak(self, text: str) -> None:
        """Génère la synthèse vocale et la joue."""
        if not text:
            return
            
        was_listening = self.is_listening
        if was_listening:
            self._stop_stream()
            
        logger.info(f"[Audio] Synthèse vocale de {len(text)} caractères...")
        audio_data = self.tts.generate_audio(text)
        
        if audio_data:
            # Piper utilise par défaut 22050 Hz pour les voix FR UPMC medium
            # À ajuster si la voix utilise 16000 Hz
            piper_sample_rate = 22050
            
            # Convertir les bytes PCM (16-bit) en array numpy pour sounddevice
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            logger.debug("[Audio] Lecture audio en cours...")
            sd.play(audio_array, piper_sample_rate)
            sd.wait() # Bloque le thread jusqu'à la fin de la lecture
            logger.debug("[Audio] Lecture audio terminée.")
            
        if was_listening:
            self._start_stream()

    def cleanup(self) -> None:
        """Arrête le thread proprement."""
        self.is_running = False
        self._stop_stream()
        self.wait()

    def _audio_callback(self, indata, frames, time, status):
        """Callback appelé par sounddevice pour chaque chunk audio."""
        if status:
            logger.warning(f"[Audio] Stream status: {status}")
        if self.is_listening:
            # On copie les données (indata est en lecture seule)
            self.audio_queue.put(indata.copy())

    def _start_stream(self):
        if self.stream is None:
            self.audio_buffer = []
            self.vad.reset()
            # On utilise float32 car c'est ce que VAD et Whisper attendent
            self.stream = sd.InputStream(
                samplerate=self.sample_rate, 
                channels=1, 
                dtype='float32',
                callback=self._audio_callback
            )
            self.stream.start()

    def _stop_stream(self):
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None
            self.audio_queue.queue.clear()

    def run(self) -> None:
        """Boucle principale du thread."""
        logger.info("[Audio] Thread audio démarré.")
        
        while self.is_running:
            try:
                # Timeout de 0.1s pour ne pas bloquer indéfiniment la boucle
                chunk = self.audio_queue.get(timeout=0.1)
                
                # Le chunk est de forme (frames, channels), on l'aplatit
                chunk_flat = chunk.flatten()
                
                # Calcul et émission du niveau audio pour l'UI
                rms = float(np.sqrt(np.mean(np.square(chunk_flat))))
                self.audio_level_update.emit(rms)
                
                # Ajouter au buffer
                if self.vad.is_speaking or rms > self.vad.threshold:
                    self.audio_buffer.append(chunk_flat)
                
                # Vérifier la fin de parole
                if self.vad.process_chunk(chunk_flat):
                    if len(self.audio_buffer) > 0:
                        # Reconstituer l'audio complet
                        full_audio = np.concatenate(self.audio_buffer)
                        self.audio_buffer = []
                        
                        logger.info("[Audio] Fin de phrase détectée, transcription en cours...")
                        # Transcription (bloque le thread audio le temps de traiter)
                        text = self.stt.transcribe(full_audio, self.sample_rate)
                        
                        if text:
                            # Désactiver l'écoute pendant qu'on transmet au LLM
                            self.toggle_listening() 
                            self.stt_transcription_ready.emit(text)
                            
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"[Audio] Erreur dans la boucle principale: {e}")
                
        logger.info("[Audio] Thread audio arrêté.")
