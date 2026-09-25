"""Vizzy Chat — FastAPI application entrypoint.

Startup order:
  1. Configure logging
  2. Create FastAPI application
  3. Configure CORS
  4. Register exception handlers
  5. Include routers (health, users)

No business logic lives here — all logic is in routes / services / core.
"""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import assets, conversations, health, messages, users
from app.core.config import get_settings
from app.core.constants import API_V1_PREFIX
from app.core.exceptions import (
    VizzyException,
    unhandled_exception_handler,
    validation_exception_handler,
    vizzy_exception_handler,
)
from app.core.logging import configure_logging

# ── 1. Configure logging ──────────────────────────────────────────────────────
settings = get_settings()
configure_logging(debug=settings.debug)

# ── 2. Create FastAPI application ─────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Vizzy Chat — conversational image-generation API",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ── 3. Configure CORS ─────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 4. Register exception handlers ────────────────────────────────────────────
app.add_exception_handler(VizzyException, vizzy_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(Exception, unhandled_exception_handler)  # type: ignore[arg-type]

# ── 5. Include routers ────────────────────────────────────────────────────────
app.include_router(health.router, prefix=API_V1_PREFIX)
app.include_router(users.router, prefix=API_V1_PREFIX)
app.include_router(conversations.router, prefix=API_V1_PREFIX)
app.include_router(messages.router, prefix=API_V1_PREFIX)
app.include_router(assets.router, prefix=API_V1_PREFIX)
