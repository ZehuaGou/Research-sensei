from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter

from researchsensei.core.config import AppConfig
from researchsensei.jobs import JobStore
from researchsensei.llm.client import LLMClient
from researchsensei.m4.service import M4InteractionService
from researchsensei.schemas import InteractiveAnswer, JobRecord
from researchsensei.web.request_models import (
    AdvisorEvaluateRequest,
    AdvisorQuestionRequest,
    FormulaExplainRequest,
    M4AskRequest,
    SelectionExplainRequest,
)


def create_m4_router(
    *,
    jobs: JobStore,
    llm_client: LLMClient | None,
    get_job: Callable[[JobStore, str], JobRecord],
    service_for_job: Callable[..., M4InteractionService],
    sync_memory: Callable[..., JobRecord],
    runtime_answer: Callable[..., InteractiveAnswer | None],
    get_config: Callable[[], AppConfig],
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/jobs/{job_id}", tags=["m4"])

    def service(job: JobRecord, required_gate: str = "reading_display") -> M4InteractionService:
        return service_for_job(job, llm_client=llm_client, required_gate=required_gate)

    @router.post("/selection/explain")
    def explain_selection(job_id: str, payload: SelectionExplainRequest) -> dict[str, object]:
        job = get_job(jobs, job_id)
        interaction = service(job)
        result = interaction.explain_selection(payload.model_dump(mode="json"))
        sync_memory(jobs, job, interaction.memory_path)
        return result.model_dump(mode="json")

    @router.post("/formula/explain")
    def explain_formula(job_id: str, payload: FormulaExplainRequest) -> dict[str, object]:
        job = get_job(jobs, job_id)
        interaction = service(job)
        result = interaction.explain_formula(payload.model_dump(mode="json"))
        sync_memory(jobs, job, interaction.memory_path)
        return result.model_dump(mode="json")

    @router.post("/ask")
    def ask_job(job_id: str, payload: M4AskRequest) -> dict[str, object]:
        job = get_job(jobs, job_id)
        request_payload = payload.model_dump(mode="json")
        answer = runtime_answer(
            request_payload,
            llm_client=llm_client,
            config_service=get_config(),
        )
        if answer is not None:
            return answer.model_dump(mode="json")
        interaction = service(job)
        result = interaction.answer_question(request_payload)
        sync_memory(jobs, job, interaction.memory_path)
        return result.model_dump(mode="json")

    @router.post("/advisor/question")
    def advisor_question(job_id: str, payload: AdvisorQuestionRequest) -> dict[str, object]:
        job = get_job(jobs, job_id)
        interaction = service(job, "advisor_questions")
        result = interaction.advisor_question(payload.model_dump(mode="json"))
        sync_memory(jobs, job, interaction.memory_path)
        return result.model_dump(mode="json")

    @router.post("/advisor/evaluate")
    def advisor_evaluate(job_id: str, payload: AdvisorEvaluateRequest) -> dict[str, object]:
        job = get_job(jobs, job_id)
        interaction = service(job, "advisor_questions")
        result = interaction.advisor_evaluate(payload.model_dump(mode="json"))
        sync_memory(jobs, job, interaction.memory_path)
        return result.model_dump(mode="json")

    @router.get("/memory")
    def get_memory(job_id: str) -> dict[str, object]:
        job = get_job(jobs, job_id)
        return service(job).get_memory().model_dump(mode="json")

    @router.delete("/memory")
    def clear_memory(job_id: str) -> dict[str, object]:
        job = get_job(jobs, job_id)
        interaction = service(job)
        bundle = interaction.clear_memory()
        sync_memory(jobs, job, interaction.memory_path)
        return {"status": "CLEARED", **bundle.model_dump(mode="json")}

    return router
