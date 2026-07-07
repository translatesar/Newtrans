import asyncio
import tempfile
from pathlib import Path
from faster_whisper import WhisperModel
from utils.logger import setup_logger

logger = setup_logger(__name__)


class SpeechService:
    def __init__(self, model_size: str = "base"):
        self.model = None
        self.model_size = model_size
    
    def _load_model(self):
        if self.model is None:
            logger.info(f"Loading faster-whisper model: {self.model_size}")
            self.model = WhisperModel(
                self.model_size,
                device="cpu",
                compute_type="int8",
            )
    
    async def transcribe(self, audio_path: str) -> str:
        try:
            wav_path = await self._convert_to_wav(audio_path)
            self._load_model()
            
            loop = asyncio.get_event_loop()
            segments, info = await loop.run_in_executor(
                None,
                lambda: self.model.transcribe(wav_path, beam_size=5)
            )
            
            transcription = []
            for segment in segments:
                transcription.append(segment.text.strip())
            
            if wav_path != audio_path:
                Path(wav_path).unlink(missing_ok=True)
            
            text = " ".join(transcription)
            text = self._clean_transcription(text)
            
            logger.info(f"Transcription complete: {len(text)} characters")
            return text
            
        except Exception as e:
            logger.error(f"Transcription error: {e}", exc_info=True)
            raise
    
    async def _convert_to_wav(self, audio_path: str) -> str:
        if audio_path.endswith(".wav"):
            return audio_path
        
        output_path = audio_path + ".wav"
        
        try:
            import ffmpeg
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: (
                    ffmpeg
                    .input(audio_path)
                    .output(output_path, acodec='pcm_s16le', ac=1, ar='16k')
                    .overwrite_output()
                    .run(quiet=True)
                )
            )
            return output_path
        except Exception as e:
            logger.error(f"Audio conversion error: {e}")
            return audio_path
    
    def _clean_transcription(self, text: str) -> str:
        text = " ".join(text.split())
        if text and not text[-1] in ".!?۔":
            text += "."
        return text
