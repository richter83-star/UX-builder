from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from app.utils.config import settings

# Create engine
engine = create_engine(settings.DATABASE_URL)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Metadata for migrations
metadata = MetaData()

def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Import all models to ensure they are registered with Base
from . import schemas  # noqa: F401