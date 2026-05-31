"""
Nova AI — FastAPI Application Entry Point
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.api.routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Nova AI starting up...")
    await init_db()
    logger.info("Database initialized.")
    yield
    logger.info("Nova AI shutting down.")


app = FastAPI(
    title="Nova AI — Marketing Audit API",
    description="14-dimension AI-powered website marketing audit engine",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "service": "Nova AI Marketing Audit",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
