from fastapi import FastAPI

from .model import lifespan
from .routes import router
from .config import logger, is_v3_model

from parakeet_service.stream_routes import router as stream_router

def create_app() -> FastAPI:
    app = FastAPI(
        title="Parakeet ASR Service",
        version="0.0.2",
        description=(
            "High-accuracy English speech-to-text (FastConformer-TDT) "
            "with optional word/char/segment timestamps. Supports v2 and v3 models."
        ),
        lifespan=lifespan,
    )
    app.include_router(router)
    app.include_router(stream_router)

    # Conditionally include the whisper-compatible routes if v3 model is selected
    if is_v3_model():
        from .whisper_routes import whisper_router
        logger.info("Parakeet v3 model detected. Enabling Whisper ASR compatibility endpoint.")
        app.include_router(whisper_router)
    
    logger.info("FastAPI app initialised")
    return app


app = create_app()
