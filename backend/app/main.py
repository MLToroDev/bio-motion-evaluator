import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import health, live_pose, pose, video

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Iniciando %s v%s", settings.app_name, settings.app_version)
    yield
    log.info("Apagando API")


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(pose.router)
app.include_router(video.router)
app.include_router(live_pose.router)


@app.get("/")
async def root():
    return {"service": settings.app_name, "docs": "/docs", "health": "/health"}
