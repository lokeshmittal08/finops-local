# app/db/database.py

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

POSTGRES_DSN = os.getenv("POSTGRES_DSN")

if not POSTGRES_DSN:
    raise RuntimeError("POSTGRES_DSN environment variable is required")

engine = create_engine(
    POSTGRES_DSN,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()

def init_db():
    """
    Create all tables if they do not exist.
    Safe to call multiple times.
    """
    import db.models
    Base.metadata.create_all(bind=engine)