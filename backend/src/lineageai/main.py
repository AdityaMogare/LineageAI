from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lineageai import __version__
from lineageai.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="LineageAI API", version=__version__)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/api/config", tags=["system"])
    def public_config() -> dict[str, str]:
        return {
            "environment": settings.environment,
            "model": settings.moonshot_model,
        }

    return app


app = create_app()
