from __future__ import annotations

from dataclasses import dataclass

from researchsensei.core.config import AppConfig, ConfigService
from researchsensei.direction import DirectionExplorationService, SeedExpansionService
from researchsensei.ingestion import SinglePaperIngestionRunner
from researchsensei.jobs import JobStore
from researchsensei.library import PaperLibraryStore
from researchsensei.llm.client import LLMClient
from researchsensei.source_resolver import SourceResolver
from researchsensei.workspace import WorkspaceStore
from researchsensei.web.services import JobService, PersistentTaskService


@dataclass(frozen=True)
class WebDependencies:
    """Application-scoped runtime dependencies loaded once by the factory."""

    config_service: ConfigService
    config: AppConfig
    workspace: WorkspaceStore
    jobs: JobStore
    job_service: JobService
    paper_library: PaperLibraryStore
    background_tasks: PersistentTaskService
    source_resolver: SourceResolver
    direction_service: DirectionExplorationService
    seed_expansion_service: SeedExpansionService
    runner: SinglePaperIngestionRunner
    llm_client: LLMClient | None
