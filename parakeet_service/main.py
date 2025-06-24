from fastapi import FastAPI

from .model import lifespan
from .routes import router
from .config import logger
from .db import init_db
from .task_routes import task_router

from parakeet_service.stream_routes import router as stream_router

def create_app() -> FastAPI:
    app = FastAPI(
        title="Parakeet-TDT 0.6B v2 STT service",
        version="0.0.1",
        description=(
            "High-accuracy English speech-to-text (FastConformer-TDT) "
            "with optional word/char/segment timestamps."
        ),
        lifespan=lifespan,
    )
    app.include_router(router)
    app.include_router(task_router)

    # TODO: improve streaming and add support for other audio formats (maybe)
    app.include_router(stream_router)
    
    # Initialize database
    init_db()
    
    logger.info("FastAPI app initialised")
    return app


app = create_app()
