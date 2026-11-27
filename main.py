from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.db.database import engine
from app.db.models.auth_challenge import AuthChallenge
from app.core.security import _require_secret


app = FastAPI(
    title="TEE Backend",
    version="1.0.0"
)


@app.on_event('startup')
def ensure_auth_challenge_table():
    _require_secret()
    AuthChallenge.__table__.create(bind=engine, checkfirst=True)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(
    api_router,
    prefix="/api"
)


@app.get("/")
def root():
    return {
        "message": "TEE Backend is running"
    }