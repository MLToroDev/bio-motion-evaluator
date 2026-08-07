from fastapi import APIRouter

from app.api.v1 import auth, download, exercises, gold_standard_videos, health, pose, sessions
from app.api.v1.dev_router import dev_router

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(gold_standard_videos.router)
api_router.include_router(pose.router)
api_router.include_router(exercises.router)
api_router.include_router(auth.router)
api_router.include_router(sessions.router)
api_router.include_router(download.router)
api_router.include_router(dev_router)

