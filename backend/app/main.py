import asyncio
import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.exception_handlers import register_exception_handlers, unexpected_error_response
from app.api.router import api_router
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.db.verification import verify_database
from app.services.automation_run_service import AutomationRunService
from app.services.automation_scheduler import AutomationScheduler
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


def create_automation_scheduler() -> AutomationScheduler:
    return AutomationScheduler(
        AutomationRunService(SessionLocal)
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Starting %s in %s", settings.app_name, settings.environment)
    verification = verify_database(settings.oai_database_url)
    app.state.database_revision = verification.revision
    scheduler = None
    scheduler_task = None
    if settings.oai_automation_enabled:
        scheduler = create_automation_scheduler()
        scheduler_task = asyncio.create_task(scheduler.run())
        app.state.automation_scheduler_task = scheduler_task
    try:
        yield
    finally:
        if scheduler is not None:
            await scheduler.stop()
        if scheduler_task is not None:
            await scheduler_task
        logger.info("Stopping %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
)
register_exception_handlers(app)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Preserve or assign a correlation ID for every HTTP response."""
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    request.state.request_id = request_id
    try:
        response = await call_next(request)
    except Exception as error:
        response = unexpected_error_response(request, error)
    response.headers["X-Request-ID"] = request_id
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
    allow_headers=["*"],
)
app.include_router(api_router)
