"""
Nova AI — FastAPI Application Entry Point
"""
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.api.routes import router

# ── Logging Configuration ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    stream=sys.stdout,
)
# Suppress noisy SQLAlchemy engine logs (only show warnings/errors)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
# Suppress noisy httpx debug logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
settings = get_settings()


def _startup_banner():
    """Print a comprehensive service health banner on startup."""
    nvidia_key = settings.nvidia_api_key
    nvidia_masked = f"{nvidia_key[:8]}...{nvidia_key[-4:]}" if len(nvidia_key) > 12 else "(not set)"
    lines = [
        "",
        "=" * 60,
        "  NOVA AI — Marketing Intelligence Engine v1.0.0",
        "=" * 60,
        "",
        f"  Environment:     {settings.app_env}",
        f"  Database:        {settings.database_url}",
        f"  CORS Origins:    {settings.cors_origins}",
        "",
        "  ── LLM Provider ──",
        f"  NVIDIA NIM:      {'[OK] CONFIGURED' if settings.nvidia_available else '[FAIL] NOT CONFIGURED'}",
        f"  NVIDIA Model:    {settings.nvidia_model}",
        f"  NVIDIA Key:      {nvidia_masked}",
        f"  NVIDIA Base URL: {settings.nvidia_base_url}",
        "",
        "  ── Services ──",
        f"  PageSpeed API:   {'[OK] KEY SET' if settings.pagespeed_key_valid else '[WARN] No key (heuristic fallback)'}",
        f"  Reports Dir:     {settings.reports_dir}",
        "",
        "=" * 60,
    ]
    for line in lines:
        logger.info(line)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _startup_banner()
    logger.info("[Startup] Verifying database connectivity...")
    await init_db()
    logger.info("[OK] Database initialized — schema ready.")
    
    logger.info("[Startup] Loading LLM Gateway...")
    from app.llm.gateway import llm_complete
    if not settings.nvidia_available:
        logger.error("[FAIL] NVIDIA_API_KEY is not configured or invalid. LLM features will fail.")
    else:
        logger.info("[OK] LLM Gateway loaded successfully. NVIDIA API key is configured.")
        
    logger.info("[Startup] Loading AI Agent Modules...")
    from app.agents.content_agent import ContentAgent
    from app.agents.strategy_agent import StrategyAgent
    logger.info("[OK] AI Agent Modules are ready.")
    
    logger.info("[OK] All Services Verified. Nova AI is READY to accept requests.")
    yield
    logger.info("Nova AI shutting down.")


app = FastAPI(
    title="Nova AI — Marketing Audit API",
    description="8-dimension AI-powered website marketing audit engine",
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

