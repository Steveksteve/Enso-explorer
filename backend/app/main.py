"""Point d'entrée FastAPI. Documentation OpenAPI : /api/docs (Swagger) et /api/openapi.json."""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

from app.api.v1 import router
from app.config import settings

logging.basicConfig(level=settings.log_level)
log = logging.getLogger("api")

app = FastAPI(
    title="ENSO Explorer API",
    version="1.0.0",
    description=(
        "API en lecture seule exposant l'indice NOAA ONI (Oceanic Niño Index, ERSST v6) "
        "pour explorer les épisodes El Niño / La Niña. Source : NOAA CPC."
    ),
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET"],
    allow_headers=["Accept", "Content-Type"],
)


@app.exception_handler(OperationalError)
async def database_unavailable(_: Request, exc: OperationalError) -> JSONResponse:
    # On journalise le détail côté serveur, on ne l'expose pas au client.
    log.error("Erreur base de données : %s", exc.__class__.__name__)
    return JSONResponse(status_code=503, content={"detail": "Base de données indisponible"})


app.include_router(router)
