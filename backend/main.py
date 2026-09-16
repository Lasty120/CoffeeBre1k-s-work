"""GEOSCAN Mission Planning API — application entry point.

Responsibilities of this module (Single Responsibility: wiring only):
  - Create the FastAPI application instance.
  - Call setup_logging() exactly once.
  - Register CORS middleware.
  - Mount all API routers.
  - Expose a lightweight /health endpoint for load-balancer probes.
  - Serve the compiled frontend SPA from dist/ (replaces Nginx static serving).
    Any path that does not match /api*, /health, /docs, /redoc, or /openapi.json
    is resolved against dist/ and falls back to dist/index.html (client-side routing).

No business logic lives here.
"""

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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

# ---------------------------------------------------------------------------
# Static files — frontend SPA built assets
# ---------------------------------------------------------------------------

_DIST_DIR: Path = Path(__file__).parent / "dist"

# Serve hashed asset bundles (JS, CSS, images) directly from dist/assets.
# The path /assets is intentionally not an API prefix, so it must be mounted
# before the catch-all route below.
app.mount("/assets", StaticFiles(directory=_DIST_DIR / "assets"), name="spa-assets")


@app.get("/health", tags=["infrastructure"], summary="Health check")
async def health_check() -> dict[str, str]:
    """Returns a simple alive signal for load-balancer / orchestrator probes.

    Args:
        None

    Returns:
        dict[str, str]: Always {"status": "ok"} with HTTP 200.
    """
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# SPA catch-all — must be registered LAST so API routes take precedence
# ---------------------------------------------------------------------------

# Prefixes that belong exclusively to the backend and must never fall through
# to the frontend index.html.
_BACKEND_PREFIXES: tuple[str, ...] = (
    settings.API_V1_PREFIX,  # e.g. /api/v1
    "/api",                  # any future /api/v2, /api/internal, …
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
)


@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str) -> FileResponse:
    """Serves the compiled frontend SPA for every non-API path.

    Args:
        full_path (str): The requested URL path captured by the wildcard route.

    Returns:
        FileResponse: The exact file from dist/ when it exists, otherwise
            dist/index.html so that the React/Vue router can handle the path
            on the client side.
    """
    requested = _DIST_DIR / full_path

    # Return the file verbatim if it physically exists in dist/
    # (e.g. /vite.svg, /drone.png, /favicon.ico).
    if requested.is_file():
        return FileResponse(requested)

    # Fall back to index.html for all client-side routes (e.g. /dashboard, /missions/42).
    return FileResponse(_DIST_DIR / "index.html")


logger.info("GEOSCAN API started | debug=%s | cors_origins=%s", settings.DEBUG, settings.CORS_ORIGINS)
