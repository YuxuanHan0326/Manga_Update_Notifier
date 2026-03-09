from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .adapters import register_builtin_adapters
from .api import router
from .config import settings
from .db import Base, SessionLocal, engine
from .scheduler import scheduler_manager
from .services.bootstrap import bootstrap_sources


def _resolve_static_dir() -> Path | None:
    # Prefer explicit env override, otherwise use image-bundled frontend_dist path.
    if settings.static_dir:
        candidate = Path(settings.static_dir)
    else:
        candidate = Path(__file__).resolve().parents[2] / "frontend_dist"
    return candidate if candidate.exists() else None


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Startup order matters: adapters -> schema -> source bootstrap -> scheduler.
    register_builtin_adapters()
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        bootstrap_sources(db)
    finally:
        db.close()

    if settings.scheduler_enabled:
        scheduler_manager.start()
    try:
        yield
    finally:
        # Shutdown path should stop scheduler first to avoid new DB work during exit.
        if settings.scheduler_enabled:
            scheduler_manager.shutdown()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

static_dir = _resolve_static_dir()
if static_dir:
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="ui")
