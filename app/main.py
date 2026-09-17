from fastapi import FastAPI

from app.api.checks import router as checks_router


def create_app() -> FastAPI:
    app = FastAPI(title="Med checks API")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(checks_router)

    return app


app = create_app()
