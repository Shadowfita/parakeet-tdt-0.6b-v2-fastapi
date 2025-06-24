import torch
from typing import List, Dict, Optional
import numpy as np
from .config import logger, DEVICE, HF_TOKEN

try:
    from pyannote.audio import Pipeline
    DIARIZATION_AVAILABLE = True
except ImportError:
    logger.warning("pyannote.audio not available. Diarization features disabled.")
    DIARIZATION_AVAILABLE = False


class DiarizationPipeline:
    def __init__(self, device: str = DEVICE, hf_token: Optional[str] = HF_TOKEN):
        if not DIARIZATION_AVAILABLE:
            raise ImportError("pyannote.audio is required for diarization")
        
        self.device = device
        try:
            self.pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=hf_token
            )
            if torch.cuda.is_available() and device == "cuda":
                self.pipeline.to(torch.device(device))
        except Exception as e:
            logger.error(f"Failed to load diarization pipeline: {e}")
            raise
    
    def process(self, audio_path: str, min_speakers: Optional[int] = None, 
                max_speakers: Optional[int] = None) -> List[Dict]:
        """Process audio for speaker diarization"""
        try:
            diarization = self.pipeline(
                audio_path,
                min_speakers=min_speakers,
                max_speakers=max_speakers
            )
            
            segments = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                segments.append({
                    "start": turn.start,
                    "end": turn.end,
                    "speaker": speaker
                })
            return segments
        except Exception as e:
            logger.error(f"Diarization failed: {e}")
            raise


def merge_transcription_diarization(transcription_result, speaker_segments):
    """Merge transcription timestamps with speaker diarization"""
    # This is a simplified implementation
    # In practice, you'd need more sophisticated alignment
    result = transcription_result.copy() if hasattr(transcription_result, 'copy') else transcription_result
    
    # Add speaker information to result
    if hasattr(result, '__dict__'):
        result.speakers = speaker_segments
    elif isinstance(result, dict):
        result['speakers'] = speaker_segments
    
    return result