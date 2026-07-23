from __future__ import annotations

from collections.abc import Callable

from researchsensei.jobs import JobStore
from researchsensei.learning.seeds import item_type_label, learning_seeds
from researchsensei.learning.store import LearningSessionRecord, LearningStore
from researchsensei.schemas import JobRecord
from researchsensei.schemas.learning import (
    LearningAnswerResult,
    LearningItem,
    LearningQuestion,
    LearningSession,
)
from researchsensei.tutor import PaperTutorService


class LearningService:
    """Turns paper-grounded artifacts into persistent, adaptive review sessions."""

    def __init__(
        self,
        *,
        store: LearningStore,
        jobs: JobStore,
        tutor_for_job: Callable[[JobRecord], PaperTutorService],
        artifacts_for_job: Callable[[JobRecord], dict[str, object]],
        sync_tutor_memory: Callable[[JobStore, JobRecord, object], JobRecord],
    ) -> None:
        self.store = store
        self.jobs = jobs
        self.tutor_for_job = tutor_for_job
        self.artifacts_for_job = artifacts_for_job
        self.sync_tutor_memory = sync_tutor_memory

    def import_job(self, job: JobRecord) -> list[LearningItem]:
        seeds = learning_seeds(job, self.artifacts_for_job(job))
        if not seeds:
            return self.store.list_items(job_id=job.job_id)
        return self.store.upsert_items(seeds)

    def start_session(
        self,
        job: JobRecord,
        *,
        count: int,
        include_not_due: bool,
    ) -> LearningSession:
        self.import_job(job)
        items = self.store.list_items(job_id=job.job_id, due_only=True, limit=count)
        if include_not_due and len(items) < count:
            selected = {item.item_id for item in items}
            extra = [
                item
                for item in self.store.list_items(job_id=job.job_id, limit=count * 3)
                if item.item_id not in selected
            ]
            items.extend(extra[: count - len(items)])
        session = self.store.create_session(job.job_id, [item.item_id for item in items])
        return self._session_model(job, session)

    def get_session(self, job: JobRecord, session_id: str) -> LearningSession:
        session = self.store.get_session(session_id)
        if session["job_id"] != job.job_id:
            raise KeyError(f"Learning session does not belong to job: {session_id}")
        return self._session_model(job, session)

    def get_active_session(self, job: JobRecord) -> LearningSession | None:
        session = self.store.latest_active_session(job.job_id)
        return self._session_model(job, session) if session is not None else None

    def answer(
        self,
        job: JobRecord,
        session_id: str,
        user_answer: str,
    ) -> LearningAnswerResult:
        session = self.store.get_session(session_id)
        if session["job_id"] != job.job_id:
            raise KeyError(f"Learning session does not belong to job: {session_id}")
        item_id = self.store.current_item_id(session)
        if not item_id:
            raise ValueError("Learning session is already complete.")
        item = self.store.get_item(item_id)
        prompt = self.store.get_prompt(session_id, item_id)
        if prompt is None:
            self._ensure_question(job, session, item)
            prompt = self.store.get_prompt(session_id, item_id)
        if prompt is None:
            raise RuntimeError("Learning question could not be prepared.")

        tutor = self.tutor_for_job(job)
        evaluation = tutor.advisor_evaluate(
            {
                "question": prompt["question"],
                "user_answer": user_answer,
                "expected_answer_points": prompt["expected_answer_points"],
                "evidence_refs": prompt["evidence_refs"],
            }
        )
        self.sync_tutor_memory(self.jobs, job, tutor.memory_path)
        score = max(0.0, min(float(evaluation.score), 1.0))
        attempt = self.store.review_item(
            session_id=session_id,
            item=item,
            question=str(prompt["question"]),
            user_answer=user_answer,
            score=score,
            rating=_rating_for_score(score),
            feedback=evaluation.feedback,
            covered_points=evaluation.covered_points,
            missing_points=evaluation.missing_points,
            misconceptions=evaluation.misconceptions,
            improvement_steps=evaluation.improvement_steps,
        )
        updated_session = self._session_model(job, self.store.get_session(session_id))
        return LearningAnswerResult(
            attempt=attempt,
            session=updated_session,
            warnings=evaluation.warnings,
        )

    def _session_model(
        self,
        job: JobRecord,
        session: LearningSessionRecord,
    ) -> LearningSession:
        item_ids = [str(value) for value in session["item_ids"]]
        current_index = int(session["current_index"])
        current: LearningQuestion | None = None
        item_id = self.store.current_item_id(session)
        if item_id:
            item = self.store.get_item(item_id)
            current = self._ensure_question(job, session, item)
        return LearningSession(
            session_id=str(session["session_id"]),
            job_id=str(session["job_id"]),
            status=str(session["status"]),
            total=len(item_ids),
            completed=min(current_index, len(item_ids)),
            current=current,
            created_at=str(session["created_at"]),
            updated_at=str(session["updated_at"]),
        )

    def _ensure_question(
        self,
        job: JobRecord,
        session: LearningSessionRecord,
        item: LearningItem,
    ) -> LearningQuestion:
        session_id = str(session["session_id"])
        stored = self.store.get_prompt(session_id, item.item_id)
        if stored is None:
            tutor = self.tutor_for_job(job)
            generated = tutor.advisor_question(
                {
                    "advisor_mode": "group_meeting",
                    "focus_question": (
                        f"围绕“{item.target_concept}”检查用户是否真正理解"
                        f"{item_type_label(item.item_type)}，允许用户用自己的话回答"
                    ),
                    "selected_text": item.source_excerpt,
                }
            )
            evidence_refs = generated.evidence_refs or item.evidence_refs
            expected = generated.expected_answer_points or _fallback_points(item)
            self.store.save_prompt(
                session_id=session_id,
                item_id=item.item_id,
                question=generated.question or _fallback_question(item),
                expected_points=expected,
                why_it_matters=generated.why_it_matters,
                answer_format=generated.answer_format,
                evidence_refs=evidence_refs,
            )
            self.sync_tutor_memory(self.jobs, job, tutor.memory_path)
            stored = self.store.get_prompt(session_id, item.item_id)
        if stored is None:
            raise RuntimeError("Learning prompt persistence failed.")
        item_ids = [str(value) for value in session["item_ids"]]
        return LearningQuestion(
            session_id=session_id,
            item_id=item.item_id,
            position=int(session["current_index"]) + 1,
            total=len(item_ids),
            question=str(stored["question"]),
            target_concept=item.target_concept,
            item_type=item.item_type,
            expected_answer_points=[str(value) for value in stored["expected_answer_points"]],
            why_it_matters=str(stored["why_it_matters"]),
            answer_format=[str(value) for value in stored["answer_format"]],
            evidence_refs=[str(value) for value in stored["evidence_refs"]],
        )


def _fallback_question(item: LearningItem) -> str:
    return f"请用自己的话解释“{item.target_concept}”，并说明它在这篇论文中的作用。"


def _fallback_points(item: LearningItem) -> list[str]:
    return [
        f"准确说明“{item.target_concept}”是什么",
        "说明它与论文研究问题或方法的关系",
        "给出论文中的具体依据或结果",
    ]


def _rating_for_score(score: float) -> int:
    if score < 0.4:
        return 1
    if score < 0.65:
        return 2
    if score < 0.9:
        return 3
    return 4
