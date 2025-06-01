# backend/app/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from ..config import settings # Assuming your config.py is one level up

# Construct the database URL.
# Ensure your settings.DATABASE_URL is correctly formatted,
# e.g., "postgresql://user:password@host:port/dbname"
engine = create_engine(settings.DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()