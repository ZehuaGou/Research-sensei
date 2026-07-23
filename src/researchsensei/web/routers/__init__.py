"""FastAPI routers for the ResearchSensei web surface."""

from researchsensei.web.routers.directions import DirectionRouteOps, create_directions_router
from researchsensei.web.routers.library import create_library_router
from researchsensei.web.routers.jobs import create_jobs_router
from researchsensei.web.routers.tutor import create_tutor_router
from researchsensei.web.routers.settings import create_settings_router

__all__ = [
    "DirectionRouteOps",
    "create_directions_router",
    "create_jobs_router",
    "create_library_router",
    "create_tutor_router",
    "create_settings_router",
]
