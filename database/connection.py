"""Database connection management for DPRK image capture system"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:jonathanholmes@localhost:5432/dprk")

engine = create_engine(DATABASE_URL, pool_size=20, max_overflow=30)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Session:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_session() -> Session:
    """Get a new database session"""
    return SessionLocal()