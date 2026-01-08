import json
from typing import Dict, List, TextIO

# Helper to format timestamps, ensuring compatibility.
def format_timestamp(seconds: float, always_include_hours: bool = False, decimal_marker: str = '.') -> str:
    assert seconds >= 0, "non-negative timestamp expected"
    milliseconds = round(seconds * 1000.0)

    hours = milliseconds // 3_600_000
    milliseconds %= 3_600_000
    minutes = milliseconds // 60_000
    milliseconds %= 60_000
    seconds = milliseconds // 1000
    milliseconds %= 1000

    if always_include_hours or hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}{decimal_marker}{milliseconds:03d}"
    else:
        return f"{minutes:02d}:{seconds:02d}{decimal_marker}{milliseconds:03d}"

def write_txt(result: Dict, file: TextIO):
    """Writes the transcription in plain text format."""
    for segment in result.get("segments", []):
        print(segment.get("text", "").strip(), file=file, flush=True)

def write_vtt(result: Dict, file: TextIO):
    """Writes the transcription in VTT format."""
    print("WEBVTT\n", file=file)
    for segment in result.get("segments", []):
        start = segment.get("start", 0.0)
        end = segment.get("end", 0.0)
        text = segment.get("text", "").strip().replace("-->", "->")
        print(
            f"{format_timestamp(start)} --> {format_timestamp(end)}\n"
            f"{text}\n",
            file=file,
            flush=True,
        )

def write_srt(result: Dict, file: TextIO):
    """Writes the transcription in SRT format."""
    for i, segment in enumerate(result.get("segments", []), start=1):
        start = segment.get("start", 0.0)
        end = segment.get("end", 0.0)
        text = segment.get("text", "").strip().replace("-->", "->")
        print(
            f"{i}\n"
            f"{format_timestamp(start, always_include_hours=True, decimal_marker=',')} --> "
            f"{format_timestamp(end, always_include_hours=True, decimal_marker=',')}\n"
            f"{text}\n",
            file=file,
            flush=True,
        )

def write_json(result: Dict, file: TextIO):
    """Writes the transcription in JSON format."""
    json.dump(result, file, indent=2)
