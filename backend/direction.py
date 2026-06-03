from __future__ import annotations

from backend.schemas import ReadingPlan


class DirectionService:
    def evolution_chain(self, plan: ReadingPlan) -> list[str]:
        return [f"{item.role.value}: {item.paper.title}" for item in plan.a_read]
