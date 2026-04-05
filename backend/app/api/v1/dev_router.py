from fastapi import APIRouter, Depends

from app.api.v1.dev import models_admin, samples, training
from app.api.v1.dev.deps import verify_dev_api_key

dev_router = APIRouter(prefix="/dev", dependencies=[Depends(verify_dev_api_key)])
dev_router.include_router(samples.router, tags=["dev-learning"])
dev_router.include_router(training.router, tags=["dev-learning"])
dev_router.include_router(models_admin.router, tags=["dev-learning"])
