from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, File, UploadFile, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import asyncio
import tempfile
from pathlib import Path

from .db import get_db_session, init_db
from .models import Task
from .schemas import TaskStatus, TaskResponse
from .audio import ensure_mono_16k, schedule_cleanup
from .config import logger, DEVICE, HF_TOKEN
from .diarization import DiarizationPipeline, merge_transcription_diarization, DIARIZATION_AVAILABLE

task_router = APIRouter(prefix="/tasks", tags=["tasks"])

async def process_transcription_task(task_uuid: str, file_content: bytes, filename: str, 
                                   include_timestamps: bool = False, include_diarization: bool = False,
                                   min_speakers: Optional[int] = None, max_speakers: Optional[int] = None):
    """Background task to process transcription"""
    from .main import app
    
    # Get database session
    db = next(get_db_session())
    
    try:
        # Update task status
        task = db.query(Task).filter_by(uuid=task_uuid).first()
        if not task:
            logger.error(f"Task {task_uuid} not found")
            return
            
        task.status = "processing"
        task.start_time = datetime.utcnow()
        db.commit()
        
        # Save file temporarily
        suffix = Path(filename).suffix or ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file_content)
            tmp_path = Path(tmp.name)
        
        # Process audio
        original, to_model = ensure_mono_16k(tmp_path)
        
        # Get model from app state (this is a simplified approach)
        # In practice, you'd want to manage model loading more carefully
        model = getattr(app.state, 'asr_model', None)
        if not model:
            raise RuntimeError("ASR model not available")
        
        # Transcribe
        outs = model.transcribe(
            [str(to_model)],
            batch_size=2,
            timestamps=include_timestamps,
        )
        
        # Process results
        if isinstance(outs, tuple):
            outs = outs[0]
        
        texts = []
        timestamps = None
        
        for h in outs:
            texts.append(getattr(h, "text", str(h)))
            if include_timestamps and timestamps is None:
                from .model import _to_builtin
                timestamps = _to_builtin(getattr(h, "timestamp", {}))
        
        result_text = " ".join(texts).strip()
        
        # Add diarization if requested
        speaker_segments = None
        if include_diarization and DIARIZATION_AVAILABLE:
            try:
                diarization_pipeline = DiarizationPipeline(device=DEVICE, hf_token=HF_TOKEN)
                speaker_segments = diarization_pipeline.process(
                    str(to_model),
                    min_speakers=min_speakers,
                    max_speakers=max_speakers
                )
            except Exception as e:
                logger.error(f"Diarization failed: {e}")
                # Continue without diarization
        
        # Build result
        result = {"text": result_text}
        if timestamps:
            result["timestamps"] = timestamps
        if speaker_segments:
            result["speakers"] = speaker_segments
        
        # Update task with results
        task.status = "completed"
        task.end_time = datetime.utcnow()
        task.duration = (task.end_time - task.start_time).total_seconds()
        task.result = result
        db.commit()
        
        # Cleanup files
        for path in [original, to_model, tmp_path]:
            if path and path.exists():
                path.unlink(missing_ok=True)
                
    except Exception as e:
        logger.exception(f"Task {task_uuid} failed")
        
        # Update task with error
        task = db.query(Task).filter_by(uuid=task_uuid).first()
        if task:
            task.status = "failed"
            task.end_time = datetime.utcnow()
            task.error = str(e)
            if task.start_time:
                task.duration = (task.end_time - task.start_time).total_seconds()
            db.commit()
    finally:
        db.close()


@task_router.post("/submit", response_model=TaskResponse)
async def submit_task(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    include_timestamps: bool = Form(False),
    include_diarization: bool = Form(False),
    min_speakers: Optional[int] = Form(None),
    max_speakers: Optional[int] = Form(None),
    session: Session = Depends(get_db_session)
):
    """Submit a transcription task for background processing with optional timestamps and diarization"""
    
    # Read file content
    file_content = await file.read()
    
    # Create task record
    task_params = {
        "include_timestamps": include_timestamps,
        "include_diarization": include_diarization,
        "min_speakers": min_speakers,
        "max_speakers": max_speakers
    }
    
    task = Task(
        status="queued",
        file_name=file.filename,
        task_type="transcription",
        task_params=task_params
    )
    session.add(task)
    session.commit()
    
    # Queue processing
    background_tasks.add_task(
        process_transcription_task, 
        task.uuid, 
        file_content, 
        file.filename or "audio.wav",
        include_timestamps,
        include_diarization,
        min_speakers,
        max_speakers
    )
    
    return TaskResponse(task_id=task.uuid, status="queued")


@task_router.get("/{task_id}", response_model=TaskStatus)
async def get_task_status(
    task_id: str,
    session: Session = Depends(get_db_session)
):
    """Get status of a specific task"""
    task = session.query(Task).filter_by(uuid=task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskStatus(
        task_id=task.uuid,
        status=task.status,
        result=task.result,
        error=task.error,
        created_at=task.created_at,
        completed_at=task.end_time
    )


@task_router.get("/", response_model=List[TaskStatus])
async def list_tasks(
    session: Session = Depends(get_db_session),
    limit: int = 100,
    offset: int = 0,
    status_filter: Optional[str] = None
):
    """List all tasks with optional filtering"""
    query = session.query(Task)
    
    if status_filter:
        query = query.filter(Task.status == status_filter)
    
    tasks = query.order_by(Task.created_at.desc()).limit(limit).offset(offset).all()
    
    return [TaskStatus(
        task_id=task.uuid,
        status=task.status,
        result=task.result,
        error=task.error,
        created_at=task.created_at,
        completed_at=task.end_time
    ) for task in tasks]


@task_router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    session: Session = Depends(get_db_session)
):
    """Delete a task"""
    task = session.query(Task).filter_by(uuid=task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    session.delete(task)
    session.commit()
    
    return {"message": "Task deleted successfully"}