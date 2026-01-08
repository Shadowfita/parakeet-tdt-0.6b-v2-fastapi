from __future__ import annotations
import asyncio
import shutil
import tempfile
from pathlib import Path
from collections import defaultdict

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Query, UploadFile, status, Request, Form

from .audio import ensure_mono_16k, schedule_cleanup
from .model import _to_builtin
from .schemas import TranscriptionResponse
from .config import logger

from parakeet_service.model import reset_fast_path
from parakeet_service.chunker import vad_chunk_lowmem, vad_chunk_streaming


router = APIRouter(tags=["speech"])


@router.get("/healthz", summary="Liveness/readiness probe")
def health():
    return {"status": "ok"}


@router.post(
    "/transcribe",
    response_model=TranscriptionResponse,
    summary="Transcribe an audio file",
)
@router.post(
    "/audio/transcriptions",
    response_model=TranscriptionResponse,
    summary="Transcribe an audio file",
)
async def transcribe_audio(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., media_type="audio/*"),
    include_timestamps: bool = Form(
        False, description="Return char/word/segment offsets",
    ),
    should_chunk: bool = Form(True,
        description="If true (default), split long audio into "
                    "~60s VAD-aligned chunks for batching"),
):
    # Create temp file with appropriate extension
    suffix = Path(file.filename or "").suffix or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = Path(tmp.name)
    
    # Stream upload directly to processing with cancellation handling
    try:
        # Use FFmpeg for MP3 files to fix header issues
        # Create temp MP3 file if needed
        mp3_tmp_path = None
        if suffix.lower() == ".mp3":
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as mp3_tmp:
                mp3_tmp_path = Path(mp3_tmp.name)
            # Write entire MP3 to temporary file
            with open(mp3_tmp_path, "wb") as f:
                while True:
                    try:
                        chunk = await file.read(8192)
                    except asyncio.CancelledError:
                        logger.warning("File upload cancelled during MP3 saving")
                        raise
                    if not chunk:
                        break
                    f.write(chunk)
            
            # Update FFmpeg command to read from file
            ffmpeg_cmd = [
                "ffmpeg", "-v", "error", "-nostdin", "-y",
                "-i", str(mp3_tmp_path),
                "-acodec", "pcm_s16le", "-ac", "1", "-ar", "16000",
                "-f", "wav", str(tmp_path)
            ]
        else:
            ffmpeg_cmd = None
            # For non-MP3, stream directly to file
            with open(tmp_path, "wb") as f:
                while True:
                    try:
                        chunk = await file.read(8192)
                    except asyncio.CancelledError:
                        logger.warning("File upload cancelled during processing")
                        raise
                    if not chunk:
                        break
                    f.write(chunk)
        
        # Run FFmpeg if processing MP3
        if ffmpeg_cmd:
            process = await asyncio.create_subprocess_exec(
                *ffmpeg_cmd,
                stdout=asyncio.subprocess.DEVNULL,  # We don't need stdout
                stderr=asyncio.subprocess.PIPE
            )
            
            # Read stderr in real-time
            stderr_lines = []
            while True:
                line = await process.stderr.readline()
                if not line:
                    break
                line_str = line.decode().strip()
                stderr_lines.append(line_str)
                logger.debug(f"FFmpeg: {line_str}")
            
            # Wait for process to finish
            return_code = await process.wait()
            stderr_str = "\n".join(stderr_lines)
            
            if return_code != 0:
                logger.error(f"FFmpeg failed with return code {return_code}")
                logger.error(f"FFmpeg error output: {stderr_str}")
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail=f"Invalid audio format: {stderr_str[:200]}"
                )
            else:
                logger.debug(f"FFmpeg completed successfully")
    except asyncio.CancelledError:
        # Clean up temporary files if processing was cancelled
        if tmp_path.exists():
            tmp_path.unlink()
        if mp3_tmp_path and mp3_tmp_path.exists():
            mp3_tmp_path.unlink()
        raise
    except BrokenPipeError:
        logger.error("FFmpeg process terminated unexpectedly")
        if tmp_path.exists():
            tmp_path.unlink()
        if mp3_tmp_path and mp3_tmp_path.exists():
            mp3_tmp_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Audio processing failed due to FFmpeg crash"
        )
    finally:
        await file.close()

    # Process audio to ensure mono 16kHz
    original, to_model = ensure_mono_16k(tmp_path)

    if should_chunk:
        # Use low-memory chunker for non-streaming requests
        chunk_data = vad_chunk_lowmem(to_model) or [(to_model, 0.0)]
    else:
        chunk_data = [(to_model, 0.0)]

    chunk_paths = [path for path, _ in chunk_data]
    chunk_offsets = [offset for _, offset in chunk_data]

    logger.info("transcribe(): sending %d chunks to ASR", len(chunk_paths))

    # Clean up all temporary files
    cleanup_files = [original, to_model] + chunk_paths
    if mp3_tmp_path:
        cleanup_files.append(mp3_tmp_path)
    schedule_cleanup(background_tasks, *cleanup_files)

    # 2 – run ASR
    model = request.app.state.asr_model

    try:
        outs = model.transcribe(
            [str(p) for p in chunk_paths],
            batch_size=2,
            timestamps=include_timestamps,
        )
        if (
          not include_timestamps                     # switch back to model fast-path if timestamps turned off
          and getattr(model.cfg.decoding, "compute_timestamps", False)
        ):
          reset_fast_path(model)                    
    except RuntimeError as exc:
        logger.exception("ASR failed")
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=str(exc)) from exc

    if isinstance(outs, tuple):
      outs = outs[0]
    texts = []
    ts_agg = [] if include_timestamps else None
    merged = defaultdict(list)

    for idx, h in enumerate(outs):
        texts.append(getattr(h, "text", str(h)))
        if include_timestamps:
            offset = chunk_offsets[idx]
            for k, v in _to_builtin(getattr(h, "timestamp", {})).items():
                # Adjust timestamps by adding the chunk offset
                if isinstance(v, list) and len(v) > 0:
                    adjusted = []
                    for item in v:
                        if isinstance(item, (list, tuple)) and len(item) >= 2:
                            # Assume format is [start, end, ...] or (start, end, ...)
                            adjusted_item = list(item)
                            adjusted_item[0] = item[0] + offset
                            adjusted_item[1] = item[1] + offset
                            adjusted.append(adjusted_item)
                        elif isinstance(item, dict):
                            # Handle dict format with 'start' and 'end' keys
                            adjusted_item = item.copy()
                            if 'start' in adjusted_item:
                                adjusted_item['start'] += offset
                            if 'end' in adjusted_item:
                                adjusted_item['end'] += offset
                            adjusted.append(adjusted_item)
                        else:
                            adjusted.append(item)
                    merged[k].extend(adjusted)
                else:
                    merged[k].extend(v)

    merged_text = " ".join(texts).strip()
    timestamps  = dict(merged) if include_timestamps else None

    return TranscriptionResponse(text=merged_text, timestamps=timestamps)

@router.get("/debug/cfg")
def show_cfg(request: Request):
    from omegaconf import OmegaConf
    model = request.app.state.asr_model         
    yaml_str = OmegaConf.to_yaml(model.cfg, resolve=True) 
    return yaml_str