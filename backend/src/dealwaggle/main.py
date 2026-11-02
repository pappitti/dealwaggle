import stripe
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from dealwaggle.api import router as api_router
from dealwaggle.config import get_settings
from dealwaggle.db import get_engine
from dealwaggle.webhooks import router as webhook_router


def create_app():
    settings = get_settings()
    app = FastAPI(
        title="DealWaggle", version="0.1.0", description="Sourced dealflow, shared with intent."
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Demo-User"],
    )
    app.include_router(api_router)
    app.include_router(webhook_router)

    @app.middleware("http")
    async def private_responses(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.exception_handler(IntegrityError)
    async def conflict(request, exception):
        return JSONResponse(
            status_code=409, content={"detail": "This change conflicts with an existing record"}
        )

    @app.exception_handler(stripe.StripeError)
    async def stripe_error(request, exception):
        return JSONResponse(
            status_code=502, content={"detail": "Billing provider unavailable; please try again"}
        )

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "dealwaggle"}

    @app.get("/ready")
    def ready():
        try:
            with get_engine().connect() as connection:
                connection.execute(text("SELECT version_num FROM alembic_version"))
            return {"status": "ready"}
        except SQLAlchemyError:
            return JSONResponse(
                status_code=503, content={"status": "database_unavailable_or_unmigrated"}
            )

    return app


app = create_app()
