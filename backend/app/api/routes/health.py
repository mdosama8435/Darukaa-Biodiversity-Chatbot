"""Health check route."""

from typing import Dict
from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=Dict[str, str])
def get_health() -> Dict[str, str]:
    """Returns the operational status of the service."""
    return {
        "status": "ok",
        "service": "darukaa-biodiversity-intelligence",
    }
