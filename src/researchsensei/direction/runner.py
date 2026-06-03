from __future__ import annotations

import logging
from pathlib import Path

from researchsensei.acquisition import ArxivAdapter, OpenAlexAdapter
from researchsensei.query import QueryPlanner
from researchsensei.schemas import CandidatePaper, DirectionBundle, QueryPlan, ReadingPlan
from researchsensei.selection import SelectionService
from researchsensei.workspace import WorkspaceStore

logger = logging.getLogger(__name__)


class DirectionRunner:
    """Orchestrates the direction analysis pipeline: query → acquisition → selection → reading plan."""

    def __init__(
        self,
        workspace: WorkspaceStore,
        query_planner: QueryPlanner | None = None,
        arxiv_adapter: ArxivAdapter | None = None,
        openalex_adapter: OpenAlexAdapter | None = None,
        selection_service: SelectionService | None = None,
        sources: list[str] | None = None,
        max_results_per_source: int = 20,
    ) -> None:
        self.workspace = workspace
        self.query_planner = query_planner or QueryPlanner()
        self.arxiv_adapter = arxiv_adapter or ArxivAdapter()
        self.openalex_adapter = openalex_adapter or OpenAlexAdapter()
        self.selection_service = selection_service or SelectionService()
        self.sources = sources or ["arxiv", "openalex"]
        self.max_results_per_source = max_results_per_source

    async def run(self, user_query: str, direction_id: str | None = None) -> DirectionBundle:
        """Run the full direction analysis pipeline."""
        actual_id = direction_id or _slugify(user_query)
        run_dir = self.workspace.new_run_dir(actual_id)

        # Step 1: Query planning
        query_plan = await self.query_planner.plan(user_query)

        # Step 2: Acquisition
        candidates = self._acquire(query_plan)

        # Step 3: Build candidate pool (raw, before dedup)
        candidate_pool = self.selection_service.build_candidate_pool(
            query=query_plan.direction_en or query_plan.user_query,
            candidates=candidates,
            search_log=[f"{source}: searched" for source in self.sources],
        )

        # Step 4: Deduplicate → filtered candidates
        filtered_items = self.selection_service.deduplicate(candidates)
        filtered_candidates = self.selection_service.build_candidate_pool(
            query=query_plan.direction_en or query_plan.user_query,
            candidates=filtered_items,
            search_log=candidate_pool.search_log + ["dedup: applied"],
        )
        filtered_candidates = filtered_candidates.model_copy(
            update={
                "retrieved_count": len(candidates),
                "deduplicated_count": len(filtered_items),
            }
        )

        # Step 5: Build reading plan from filtered candidates
        reading_plan = self.selection_service.build_reading_plan(query_plan, filtered_items)

        # Step 6: Write artifacts
        self.workspace.write_json(run_dir / "query_plan.json", query_plan)
        self.workspace.write_json(run_dir / "candidate_pool.json", candidate_pool)
        self.workspace.write_json(run_dir / "filtered_candidates.json", filtered_candidates)
        self.workspace.write_json(run_dir / "reading_plan.json", reading_plan)

        return DirectionBundle(
            query_plan=query_plan,
            candidate_pool=candidate_pool,
            filtered_candidates=filtered_candidates,
            reading_plan=reading_plan,
            warnings=query_plan.warnings + reading_plan.warnings,
        )

    def _acquire(self, query_plan: QueryPlan) -> list[CandidatePaper]:
        """Acquire candidate papers from configured sources."""
        query = query_plan.direction_en or query_plan.user_query
        candidates: list[CandidatePaper] = []

        for source in self.sources:
            try:
                if source == "arxiv":
                    results = self.arxiv_adapter.search(query, max_results=self.max_results_per_source)
                elif source == "openalex":
                    results = self.openalex_adapter.search(query, max_results=self.max_results_per_source)
                else:
                    logger.warning("Unknown source: %s", source)
                    continue
                candidates.extend(results)
            except Exception as exc:
                logger.warning("Acquisition failed for source %s: %s", source, exc)

        return candidates


def _slugify(text: str) -> str:
    """Create a URL-friendly slug from text."""
    import re
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[-\s]+", "-", slug).strip("-")
    return slug[:50] or "direction"
