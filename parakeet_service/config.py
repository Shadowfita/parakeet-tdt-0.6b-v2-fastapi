import logging, os, sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

MODEL_NAME = "nvidia/parakeet-tdt-0.6b-v2"  # Keep hardcoded as requested

# Configuration from environment variables
TARGET_SR = int(os.getenv("TARGET_SR", "16000"))          # model’s native sample-rate
MODEL_PRECISION = os.getenv("MODEL_PRECISION", "fp16")
DEVICE = os.getenv("DEVICE", "cuda")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "4"))
MAX_AUDIO_DURATION = int(os.getenv("MAX_AUDIO_DURATION", "30"))   # seconds
VAD_THRESHOLD = float(os.getenv("VAD_THRESHOLD", "0.5"))
PROCESSING_TIMEOUT = int(os.getenv("PROCESSING_TIMEOUT", "60"))    # seconds

# Database
DB_URL = os.getenv("DB_URL", "sqlite:///transcriptions.db")

# Diarization
HF_TOKEN = os.getenv("HF_TOKEN")

# Task Management
TASK_CLEANUP_HOURS = int(os.getenv("TASK_CLEANUP_HOURS", "24"))
MAX_CONCURRENT_TASKS = int(os.getenv("MAX_CONCURRENT_TASKS", "10"))

# Audio Processing
MAX_AUDIO_SIZE_MB = int(os.getenv("MAX_AUDIO_SIZE_MB", "500"))

class Config:
    DB_URL = DB_URL
    HF_TOKEN = HF_TOKEN
    TASK_CLEANUP_HOURS = TASK_CLEANUP_HOURS
    MAX_CONCURRENT_TASKS = MAX_CONCURRENT_TASKS
    MAX_AUDIO_SIZE_MB = MAX_AUDIO_SIZE_MB

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s  %(levelname)-7s  %(name)s: %(message)s",
    stream=sys.stdout,
    force=True
)

logger = logging.getLogger("parakeet_service")
