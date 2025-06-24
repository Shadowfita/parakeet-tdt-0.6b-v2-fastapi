# Parakeet Enhanced Features Migration Guide

This guide outlines the implementation of key features from WhisperX to enhance the Parakeet service.

## Implemented Features

### 1. Database Persistence Layer ✅
- **Location**: `parakeet_service/models.py`, `parakeet_service/db.py`
- **Description**: SQLAlchemy-based persistence for transcription tasks and results
- **Usage**: Automatic initialization on app startup, stores task history and results

### 2. Enhanced Audio Processing ✅
- **Location**: `parakeet_service/audio.py`
- **Description**: Support for multiple audio/video formats including MP4, AVI, MOV, etc.
- **Supported Formats**: WAV, MP3, MP4, MOV, AVI, FLAC, OGG, AAC, M4A, WMA, WEBM, MKV, WMV

### 3. Speaker Diarization ✅
- **Location**: `parakeet_service/diarization.py`
- **Description**: pyannote.audio-based speaker identification
- **Endpoint**: `POST /transcribe-with-diarization`
- **Requirements**: HuggingFace token for pyannote models

### 4. Task Management API ✅
- **Location**: `parakeet_service/task_routes.py`
- **Description**: Background task processing with status tracking
- **Endpoints**:
  - `POST /tasks/submit` - Submit transcription task
  - `GET /tasks/{task_id}` - Get task status
  - `GET /tasks/` - List all tasks
  - `DELETE /tasks/{task_id}` - Delete task

### 5. URL-based Audio Processing ✅
- **Location**: Added to `parakeet_service/routes.py`
- **Description**: Direct transcription from URLs
- **Endpoint**: `POST /transcribe-url`

## Installation

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your settings, especially HF_TOKEN for diarization
   ```

3. **Database Setup**:
   The database is automatically initialized on first run using SQLite by default.

## New API Endpoints

### Diarization
```bash
curl -X POST "http://localhost:8000/transcribe-with-diarization" \
  -F "file=@audio.wav" \
  -F "include_timestamps=true" \
  -F "min_speakers=2" \
  -F "max_speakers=4"
```

### URL Transcription
```bash
curl -X POST "http://localhost:8000/transcribe-url" \
  -F "url=https://example.com/audio.mp3" \
  -F "include_timestamps=false"
```

### Task Management
```bash
# Submit task
curl -X POST "http://localhost:8000/tasks/submit" \
  -F "file=@audio.wav" \
  -F "include_timestamps=true"

# Check status
curl "http://localhost:8000/tasks/{task_id}"

# List tasks
curl "http://localhost:8000/tasks/?limit=10"
```

## Configuration Options

### Environment Variables
- `DB_URL`: Database connection string (default: SQLite)
- `HF_TOKEN`: HuggingFace token for diarization models
- `MAX_AUDIO_SIZE_MB`: Maximum audio file size (default: 500MB)
- `TASK_CLEANUP_HOURS`: Hours to keep completed tasks (default: 24)
- `MAX_CONCURRENT_TASKS`: Maximum simultaneous tasks (default: 10)

### Audio Processing
- Enhanced FFmpeg support for video files
- Automatic format detection and conversion
- Streaming audio processing for large files

## Performance Considerations

1. **Diarization**: Requires significant GPU memory, disable if not needed
2. **Database**: Use PostgreSQL for production environments
3. **Task Management**: Monitor task queue size and cleanup old tasks
4. **Video Processing**: Large video files may require additional disk space

## Error Handling

- Graceful degradation when diarization unavailable
- Comprehensive error logging for debugging
- Proper cleanup of temporary files
- Task failure recovery with error storage

## Migration Notes

- Existing `/transcribe` endpoint remains unchanged
- New features are additive and don't break existing functionality
- Database tables are created automatically
- Optional features can be disabled by not installing dependencies

## Testing

Run the service and test new endpoints:
```bash
uvicorn parakeet_service.main:app --host 0.0.0.0 --port 8000
```

Access the interactive API documentation at `http://localhost:8000/docs`