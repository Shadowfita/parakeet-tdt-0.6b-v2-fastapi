import asyncio
import tempfile
from pathlib import Path
from collections import defaultdict
from typing import Optional
from io import StringIO
import soundfile as sf

from fastapi import (
    APIRouter, BackgroundTasks, HTTPException, Request, status,
    File, UploadFile, Form, Query, Response  # <-- Query is the key
)
from fastapi.responses import PlainTextResponse, JSONResponse

from .audio import schedule_cleanup
from .model import _to_builtin
from .schemas import WhisperTranscriptionResponse
from .config import logger, BATCH_SIZE, TARGET_SR
from .chunker import vad_chunk_lowmem
from .formatters import write_txt, write_vtt, write_srt, write_json


whisper_router = APIRouter(tags=["whisper_compatibility"])


@whisper_router.post(
    "/asr",
    response_model=WhisperTranscriptionResponse,
    summary="Transcribe an audio or video file (For use with Bazarr)",
)
@whisper_router.post(
    "/audio/transcriptions",
    response_model=WhisperTranscriptionResponse,
    summary="[OpenAI Compatible] Transcribe audio",
)
@whisper_router.post(
    "/audio/transcriptions/detect-language",
    response_model=WhisperTranscriptionResponse,
    summary="[Legacy Alias] Transcribe audio",
    deprecated=True,
)
async def transcribe_asr_compatible(
    request: Request,
    background_tasks: BackgroundTasks,
    # The 'audio_file' is the only parameter read from the Form Body.
    audio_file: UploadFile = File(..., description="Audio or video file to transcribe."),
    # --- START OF CORRECTED PARAMETERS ---
    # All other parameters are URL Query Parameters, not Form fields.
    task: Optional[str] = Query("transcribe", description="Task to perform (transcribe or translate)."),
    language: Optional[str] = Query("en", description="Language code for the audio."),
    output: str = Query("json", enum=["txt", "vtt", "srt", "json"], description="The desired output format."),
    # --- END OF CORRECTED PARAMETERS ---
) -> Response:
    """
    Trancribes an audio stream and returns the result in the format specified
    by the 'output' query parameter (json, srt, vtt, or txt).
    """
    source_description = f"uploaded file '{audio_file.filename}'"

    content = await audio_file.read()
    total_bytes_read = len(content)
    await audio_file.close()

    if total_bytes_read == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded 'audio_file' is empty.")

    is_valid_wav = (total_bytes_read > 12 and content[:4] == b'RIFF' and content[8:12] == b'WAVE')

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_wav_file:
        tmp_path = Path(tmp_wav_file.name)
        if is_valid_wav:
            tmp_wav_file.write(content)
        else:
            ffmpeg_cmd = [
                "ffmpeg", "-v", "error", "-nostdin", "-y",
                "-f", "s16le", "-ar", str(TARGET_SR), "-ac", "1",
                "-i", "-",
                "-acodec", "pcm_s16le", "-f", "wav", str(tmp_path)
            ]
            process = await asyncio.create_subprocess_exec(
                *ffmpeg_cmd, stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await process.communicate(input=content)

            if process.returncode != 0:
                stderr_str = stderr.decode().strip()
                raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=f"FFmpeg processing failed: {stderr_str[:250]}")

    chunk_paths = vad_chunk_lowmem(tmp_path) or [tmp_path]
    cleanup_files = [tmp_path] + [p for p in chunk_paths if p != tmp_path]
    schedule_cleanup(background_tasks, *cleanup_files)

    chunk_durations = [sf.info(p).duration for p in chunk_paths]

    model = request.app.state.asr_model
    try:
        outs = model.transcribe([str(p) for p in chunk_paths], batch_size=BATCH_SIZE, timestamps=True)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    if isinstance(outs, tuple):
        outs = outs[0]

    segments_data = []
    full_text_parts = []
    time_offset = 0.0

    for i, segment_result in enumerate(outs):
        text = getattr(segment_result, "text", "").strip()
        if not text:
            if i < len(chunk_durations):
                time_offset += chunk_durations[i]
            continue

        full_text_parts.append(text)
        ts_data = _to_builtin(getattr(segment_result, "timestamp", {}))
        segment_ts_list = ts_data.get("segment", [])
        
        if segment_ts_list:
            try:
                first_segment = segment_ts_list[0]
                last_segment = segment_ts_list[-1]
                start_time_rel = first_segment.get('start')
                end_time_rel = last_segment.get('end')

                if start_time_rel is not None and end_time_rel is not None:
                    segments_data.append({
                        "start": start_time_rel + time_offset,
                        "end": end_time_rel + time_offset,
                        "text": text
                    })
            except (IndexError, AttributeError, TypeError):
                pass

        if i < len(chunk_durations):
            time_offset += chunk_durations[i]

    final_result = {
        "text": " ".join(full_text_parts).strip(),
        "segments": segments_data,
        "language": "en"
    }

    with StringIO() as string_io:
        if output == "srt":
            write_srt(final_result, string_io)
            return PlainTextResponse(string_io.getvalue(), media_type="text/plain")
        elif output == "vtt":
            write_vtt(final_result, string_io)
            return PlainTextResponse(string_io.getvalue(), media_type="text/plain")
        elif output == "txt":
            write_txt(final_result, string_io)
            return PlainTextResponse(string_io.getvalue(), media_type="text/plain")
        else: # Default to JSON
            validated_result = WhisperTranscriptionResponse(**final_result)
            return JSONResponse(validated_result.model_dump())
