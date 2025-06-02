# backend/app/db/session.py
# Database session management for SQLAlchemy.

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from app.config import settings # Import settings to get DATABASE_URL

# Create a SQLAlchemy engine
# The connect_args is specific to SQLite for enabling foreign key constraints.
# For PostgreSQL, it's usually not needed.
# For production with PostgreSQL, you might want to configure pool size, etc.
engine_args = {}
if "sqlite" in settings.DATABASE_URL:
    engine_args["connect_args"] = {"check_same_thread": False} # Required for SQLite

engine = create_engine(
    settings.DATABASE_URL,
    **engine_args
    # For production, you might add:
    # pool_pre_ping=True,
    # pool_recycle=3600, # Recycle connections every hour
)

# Create a SessionLocal class to generate database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for SQLAlchemy models
# All your database models should inherit from this Base.
Base = declarative_base()

# Dependency to get DB session in FastAPI path operations
def get_db():
    """
    FastAPI dependency that provides a SQLAlchemy database session.
    Ensures the session is closed after the request is finished.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
