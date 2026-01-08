from typing import List, Optional, Union, Dict
from pydantic import BaseModel, Field


class Timestamps(BaseModel):
    """
    word and char-level timestamps are not guaranteed to be monotonic
    """

    char: Optional[List[List[float]]] = None
    word: Optional[List[List[float]]] = None
    segment: Optional[List[List[float]]] = None


class TranscriptionResponse(BaseModel):
    text: str = Field(..., description="Transcribed text")
    timestamps: Optional[Timestamps] = Field(
        None, description="Timestamps for characters, words, or segments"
    )


class WhisperTranscriptionResponse(BaseModel):
    text: str = Field(..., description="The transcribed text.")
    language: str = Field(
        "en",
        description="The detected language of the audio. Always 'en' for Parakeet.",
    )
    segments: List[Dict[str, Union[float, str]]] = Field(
        [],
        description="List of transcribed segments with start and end times.",
        example=[{"start": 0.0, "end": 5.0, "text": "This is a segment."}],
    )
