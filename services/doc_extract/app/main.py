from fastapi import FastAPI
from api.routes.extract import router as extract_router
from db.database import init_db


# from app.db.database import engine, Base
# from app.db import models

# Base.metadata.create_all(bind=engine)

app = FastAPI(title="doc-extract-service", version="0.5")

@app.on_event("startup")
def on_startup():
    init_db()


app.include_router(extract_router)