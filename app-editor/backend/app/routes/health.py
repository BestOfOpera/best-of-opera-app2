"""Health check."""
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    return {"status": "ok", "app": "Best of Opera — Editor", "version": "1.0.0"}
