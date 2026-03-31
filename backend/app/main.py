import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config import settings
from app.db.session import init_engine
from app.routers import health, live_pose, pose, video

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Iniciando %s v%s", settings.app_name, settings.app_version)
    init_engine()
    yield
    log.info("Apagando API")


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

# CORS: con allow_credentials=True no puede usarse allow_origins=["*"] (el navegador bloquea).
# Flutter web usa puertos aleatorios en localhost; el regex cubre cualquier puerto en dev.
_cors_kw = {"allow_methods": ["*"], "allow_headers": ["*"]}
_origins = settings.cors_origins_list
if _origins == ["*"]:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        **_cors_kw,
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origins,
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_credentials=True,
        **_cors_kw,
    )

app.include_router(health.router)
app.include_router(pose.router)
app.include_router(video.router)
app.include_router(live_pose.router)
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"service": settings.app_name, "docs": "/docs", "health": "/health"}
