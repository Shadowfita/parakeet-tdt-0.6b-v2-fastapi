from typing import Any, Dict, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class TranscriptionResponse(BaseModel):
    text: str = Field(..., description="Plain transcription.")
    timestamps: Optional[Dict[str, Any]] = Field(
        None,
        description="Word/segment/char offsets (see NeMo docs).",
    )


class TaskResponse(BaseModel):
    task_id: str = Field(..., description="Unique task identifier")
    status: str = Field(..., description="Current task status")


class TaskStatus(BaseModel):
    task_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DiarizationSegment(BaseModel):
    start: float
    end: float
    speaker: str


class DiarizationResponse(BaseModel):
    text: str
    timestamps: Optional[Dict[str, Any]] = None
    speakers: List[DiarizationSegment]