"""
Audio helpers:
* ensure_mono_16k(path)  -> Path (possibly rewritten .wav)
* schedule_cleanup(background, *paths)
"""
from __future__ import annotations
from pathlib import Path
from typing import Iterable, Tuple, List
import tempfile

import torchaudio
import torchaudio.functional as AF
import soundfile as sf
import numpy as np
from fastapi import BackgroundTasks, HTTPException, status

from .config import TARGET_SR, logger


AUDIO_EXTENSIONS = {'.wav', '.aac', '.mp3', '.awb', '.amr', '.oga', '.ogg', '.wma', '.m4a', '.flac', '.opus'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.mkv', '.avi', '.wmv', '.webm'}
ALLOWED_EXTENSIONS = AUDIO_EXTENSIONS | VIDEO_EXTENSIONS
SUPPORTED_EXTS: List[str] = list(ALLOWED_EXTENSIONS)


def convert_audio_streaming(src: Path) -> Tuple[Path, Path]:
    """
    Stream audio conversion to mono/16kHz with minimal memory usage
    Processes audio in chunks to avoid loading entire file into memory
    """
    try:
        with sf.SoundFile(src, 'r') as snd:
            sr_orig = snd.samplerate
            channels = snd.channels
            # Create temp output file
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            dst = Path(tmp.name)
            
            with sf.SoundFile(tmp.name, 'w', samplerate=16000, 
                             channels=1, subtype='PCM_16') as out:
                # Process in 10-second chunks
                chunk_size = 10 * sr_orig
                while True:
                    chunk = snd.read(int(chunk_size), dtype='float32')
                    if len(chunk) == 0:
                        break
                    
                    # Convert to mono if needed
                    if channels > 1:
                        chunk = np.mean(chunk, axis=1)
                    
                    # Resample if needed
                    if sr_orig != 16000:
                        chunk_tensor = torchaudio.tensor(chunk).unsqueeze(0)
                        chunk = AF.resample(chunk_tensor, sr_orig, 16000)
                        chunk = chunk.squeeze(0).numpy()
                    
                    out.write(chunk)
            
            return src, dst
    
    except Exception as e:
        logger.error(f"Streaming conversion failed: {e}")
        # Fallback to standard conversion
        return ensure_mono_16k_standard(src)


def ensure_mono_16k_standard(src: Path) -> Tuple[Path, Path]:
    """
    Standard full-file audio conversion (fallback)
    """
    wav, sr = torchaudio.load(src)             # (ch, time) float32 −1…1
    if wav.shape[0] > 1:                       # stereo → mono
        wav = wav.mean(dim=0, keepdim=True)

    if sr != TARGET_SR:
        wav = AF.resample(wav, sr, TARGET_SR)

    if src.suffix.lower() == ".wav" and sr == TARGET_SR:
        # rewrite header to 16-bit PCM in-place
        torchaudio.save(src, wav, TARGET_SR,
                        encoding="PCM_S", bits_per_sample=16)
        return src, src

    dst = src.with_suffix(".wav")
    torchaudio.save(dst, wav, TARGET_SR,
                    encoding="PCM_S", bits_per_sample=16)
    return src, dst


def convert_media_to_audio(file_path: Path) -> Path:
    """Convert video/audio file to WAV format using FFmpeg"""
    if file_path.suffix.lower() in VIDEO_EXTENSIONS or needs_conversion(file_path):
        import subprocess
        import tempfile
        
        output = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        try:
            subprocess.run([
                'ffmpeg', '-y', '-v', 'error', '-nostdin',
                '-i', str(file_path),
                '-vn',  # No video
                '-ac', '1',  # Mono
                '-ar', '16000',  # 16kHz
                '-acodec', 'pcm_s16le',
                '-f', 'wav',
                output.name
            ], check=True)
            return Path(output.name)
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg conversion failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Failed to convert media file: {e}"
            )
    return file_path


def needs_conversion(file_path: Path) -> bool:
    """Check if audio file needs conversion"""
    try:
        with sf.SoundFile(file_path) as snd:
            return snd.samplerate != 16000 or snd.channels != 1
    except:
        return True


def ensure_mono_16k(src: Path) -> Tuple[Path, Path]:
    """
    Down-mix and resample to mono/16 kHz using streaming when possible.
    """
    if src.suffix.lower() not in SUPPORTED_EXTS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type {src.suffix}. Supported: {', '.join(SUPPORTED_EXTS)}",
        )
    
    # Handle video files and complex audio conversions with FFmpeg
    if src.suffix.lower() in VIDEO_EXTENSIONS:
        converted_path = convert_media_to_audio(src)
        return src, converted_path
    
    # For WAV files that are already mono and 16kHz, no conversion needed
    if src.suffix.lower() == ".wav":
        try:
            with sf.SoundFile(src) as snd:
                if snd.samplerate == 16000 and snd.channels == 1:
                    return src, src
        except:
            pass
    
    # Use streaming conversion for other cases
    return convert_audio_streaming(src)


def schedule_cleanup(tasks: BackgroundTasks, *paths: Path) -> None:
    for p in paths:
        tasks.add_task(p.unlink, missing_ok=True)