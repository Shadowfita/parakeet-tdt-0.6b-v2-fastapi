from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .config import Config
from .models import Base

def get_db_url():
    """Get database URL from environment or use default SQLite"""
    import os
    return os.getenv("DB_URL", "sqlite:///transcriptions.db")

DB_URL = get_db_url()
engine = create_engine(DB_URL, connect_args={"check_same_thread": False} if "sqlite" in DB_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)