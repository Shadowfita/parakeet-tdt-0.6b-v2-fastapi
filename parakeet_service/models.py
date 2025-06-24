from datetime import datetime
from uuid import uuid4
from sqlalchemy import JSON, Column, DateTime, Float, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String, default=lambda: str(uuid4()), unique=True)
    status = Column(String)  # processing, completed, failed
    result = Column(JSON)
    file_name = Column(String)
    url = Column(String)
    audio_duration = Column(Float)
    language = Column(String)
    task_type = Column(String)
    task_params = Column(JSON)
    duration = Column(Float)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    error = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)