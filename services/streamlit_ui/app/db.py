import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

POSTGRES_DSN = os.getenv("POSTGRES_DSN")

engine = create_engine(POSTGRES_DSN, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)