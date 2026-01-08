import logging, os, sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Model Selection
MODEL_NAME = os.getenv("MODEL_NAME", "nvidia/parakeet-tdt-0.6b-v2")

# Configuration from environment variables
TARGET_SR = int(os.getenv("TARGET_SR", "16000"))          # model’s native sample-rate
MODEL_PRECISION = os.getenv("MODEL_PRECISION", "fp16")
DEVICE = os.getenv("DEVICE", "cuda")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "4"))
MAX_AUDIO_DURATION = int(os.getenv("MAX_AUDIO_DURATION", "30"))   # seconds
VAD_THRESHOLD = float(os.getenv("VAD_THRESHOLD", "0.5"))
PROCESSING_TIMEOUT = int(os.getenv("PROCESSING_TIMEOUT", "60"))    # seconds

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s  %(levelname)-7s  %(name)s: %(message)s",
    stream=sys.stdout,
    force=True
)

logger = logging.getLogger("parakeet_service")

# Helper to check which model is active
def is_v3_model():
    """Checks if the configured model is the v3 version."""
    return "v3" in MODEL_NAME
