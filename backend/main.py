"""GEOSCAN Mission Planning API — application entry point.

Responsibilities of this module (Single Responsibility: wiring only):
  - Create the FastAPI application instance.
  - Call setup_logging() exactly once.
  - Register CORS middleware.
  - Mount all API routers.
  - Expose a lightweight /health endpoint for load-balancer probes.

No business logic lives here.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.v1.missions import router as missions_router
from core.config import settings
from core.logging_config import setup_logging

setup_logging()

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    description=(
        "UAV mission planning and route optimisation service. "
        "See /docs for the interactive API explorer."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(missions_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["infrastructure"], summary="Health check")
async def health_check() -> dict[str, str]:
    """Returns a simple alive signal for Nginx / load-balancer probes.

    Args:
        None

    Returns:
        dict[str, str]: Always {"status": "ok"} with HTTP 200.
    """
    return {"status": "ok"}


logger.info("GEOSCAN API started | debug=%s | cors_origins=%s", settings.DEBUG, settings.CORS_ORIGINS)
