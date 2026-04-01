from fastapi import APIRouter

from app.api.v1 import auth, sessions
from app.routers import gold_standard_videos, health, pose

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(gold_standard_videos.router)
api_router.include_router(pose.router)
api_router.include_router(auth.router)
api_router.include_router(sessions.router)

