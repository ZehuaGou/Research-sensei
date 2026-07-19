from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable, Sequence

from researchsensei.schemas import CandidatePaper, QueryPlan


MIN_RELEVANCE_SCORE = 0.68
MIN_DEEP_READ_RELEVANCE_SCORE = 0.72


def passes_strict_relevance_gate(candidate: CandidatePaper) -> bool:
    """Return whether a paper is strong enough for full-text acquisition."""

    return bool(
        candidate.relevance_gate_evaluated
        and candidate.relevance_gate_passed
        and candidate.rule_relevance_score >= MIN_DEEP_READ_RELEVANCE_SCORE
    )


@dataclass(frozen=True)
class ConceptRule:
    name: str
    aliases: tuple[str, ...]
    category: str


@dataclass(frozen=True)
class QueryRelevanceRequirements:
    required_concepts: tuple[str, ...]
    optional_concepts: tuple[str, ...]
    forbidden_intent_mismatches: tuple[str, ...]
    allow_survey: bool
    fallback_terms: tuple[str, ...]


@dataclass(frozen=True)
class CandidateRelevanceAssessment:
    score: float
    concept_coverage: float
    matched_concepts: tuple[str, ...]
    missing_concepts: tuple[str, ...]
    forbidden_intent_matches: tuple[str, ...]
    passed: bool
    reason: str


_CONCEPT_RULES: tuple[ConceptRule, ...] = (
    ConceptRule(
        "time_series",
        (
            "time series",
            "temporal series",
            "temporal sequence",
            "sequential sensor data",
            "时间序列",
            "时序数据",
            "时序",
        ),
        "data",
    ),
    ConceptRule(
        "multivariate",
        (
            "multivariate",
            "multi variate",
            "multiple variables",
            "multiple sensor variables",
            "multivariable",
            "多变量",
            "多元",
        ),
        "data",
    ),
    ConceptRule(
        "anomaly_detection",
        (
            "anomaly detection",
            "anomaly detector",
            "detect anomalies",
            "detecting anomalies",
            "anomalous event detection",
            "outlier detection",
            "novelty detection",
            "abnormality detection",
            "异常检测",
            "异常识别",
        ),
        "task",
    ),
    ConceptRule(
        "forecasting",
        (
            "forecast",
            "forecasting",
            "time series prediction",
            "temporal prediction",
            "predict future",
            "预测",
            "预报",
        ),
        "task",
    ),
    ConceptRule(
        "imputation",
        (
            "imputation",
            "impute missing",
            "missing value completion",
            "missing values completion",
            "missing data completion",
            "missing value recovery",
            "插补",
            "缺失值填补",
            "缺失值补全",
            "数据补全",
        ),
        "task",
    ),
    ConceptRule(
        "clustering",
        ("clustering", "cluster analysis", "聚类"),
        "task",
    ),
    ConceptRule(
        "classification",
        ("classification", "classifier", "分类"),
        "task",
    ),
    ConceptRule(
        "root_cause_analysis",
        (
            "root cause analysis",
            "root cause localization",
            "root cause diagnosis",
            "root cause identification",
            "fault localization",
            "failure localization",
            "incident diagnosis",
            "rca",
            "根因分析",
            "根因定位",
            "故障定位",
            "故障诊断",
        ),
        "task",
    ),
    ConceptRule(
        "graph",
        (
            "graph",
            "graph structured",
            "graph based",
            "network topology",
            "图结构",
            "图数据",
            "图异常",
            "时空图",
            "图神经",
        ),
        "method",
    ),
    ConceptRule(
        "gnn",
        (
            "graph neural network",
            "graph neural networks",
            "graph convolutional network",
            "graph attention network",
            "gnn",
            "gcn",
            "gat",
            "图神经网络",
            "图网络",
        ),
        "method",
    ),
    ConceptRule(
        "diffusion",
        (
            "diffusion model",
            "diffusion models",
            "diffusion based",
            "denoising diffusion",
            "score based generative",
            "扩散模型",
            "扩散方法",
        ),
        "method",
    ),
    ConceptRule(
        "llm",
        (
            "large language model",
            "large language models",
            "foundation language model",
            "llm",
            "大语言模型",
            "语言大模型",
        ),
        "method",
    ),
    ConceptRule(
        "aiops",
        (
            "aiops",
            "ai for it operations",
            "it operations",
            "service operations",
            "intelligent operations",
            "智能运维",
            "运维场景",
        ),
        "domain",
    ),
    ConceptRule(
        "survey",
        (
            "survey",
            "systematic review",
            "literature review",
            "review article",
            "taxonomy",
            "tutorial",
            "综述",
            "文献调研",
            "研究综述",
        ),
        "intent",
    ),
)

_RULE_BY_NAME = {rule.name: rule for rule in _CONCEPT_RULES}
_TASK_CONCEPTS = {
    rule.name for rule in _CONCEPT_RULES if rule.category == "task"
}
_STOPWORDS = {
    "about",
    "and",
    "based",
    "for",
    "from",
    "method",
    "methods",
    "model",
    "models",
    "of",
    "on",
    "paper",
    "research",
    "the",
    "using",
    "with",
}


class DeterministicRelevanceEvaluator:
    """Offline M1 gate for task, data-shape, method, and intent coverage.

    An LLM score may annotate a candidate, but it never rescues a candidate
    that fails this deterministic gate.
    """

    def requirements(self, query_plan: QueryPlan) -> QueryRelevanceRequirements:
        query_text = _query_text(query_plan)
        detected = detect_concepts(query_text)
        required = [rule.name for rule in _CONCEPT_RULES if rule.name in detected]

        # GNN is a graph method. Requiring both makes a plain graph method an
        # explicit near miss rather than an acceptable GNN result.
        if "gnn" in detected and "graph" not in required:
            required.append("graph")

        allow_survey = "survey" in detected
        requested_tasks = set(required) & _TASK_CONCEPTS
        forbidden: list[str] = []
        if not allow_survey:
            forbidden.append("survey")
        for task in sorted(_TASK_CONCEPTS - requested_tasks):
            forbidden.append(task)

        optional: list[str] = []
        if "time_series" in required and "multivariate" not in required:
            optional.append("multivariate")
        if "anomaly_detection" in required and "root_cause_analysis" not in required:
            optional.append("root_cause_analysis")
        if "aiops" in required and "time_series" not in required:
            optional.append("time_series")

        return QueryRelevanceRequirements(
            required_concepts=tuple(_unique(required)),
            optional_concepts=tuple(_unique(optional)),
            forbidden_intent_mismatches=tuple(_unique(forbidden)),
            allow_survey=allow_survey,
            fallback_terms=tuple(_fallback_terms(query_plan)),
        )

    def assess(
        self,
        query_plan: QueryPlan,
        candidate: CandidatePaper,
        *,
        requirements: QueryRelevanceRequirements | None = None,
    ) -> CandidateRelevanceAssessment:
        req = requirements or self.requirements(query_plan)
        text = _candidate_text(candidate)
        title = _normalize_text(candidate.title)
        detected = detect_concepts(text)

        matched = [name for name in req.required_concepts if name in detected]
        missing = [name for name in req.required_concepts if name not in detected]
        coverage = len(matched) / len(req.required_concepts) if req.required_concepts else 0.0
        optional_coverage = (
            sum(1 for name in req.optional_concepts if name in detected) / len(req.optional_concepts)
            if req.optional_concepts
            else 0.0
        )
        lexical_coverage = _lexical_coverage(text, req.fallback_terms)
        title_coverage = _concept_coverage(title, req.required_concepts)

        forbidden_matches: list[str] = []
        requested_tasks = set(req.required_concepts) & _TASK_CONCEPTS
        candidate_tasks = detected & _TASK_CONCEPTS
        if missing and candidate_tasks and not requested_tasks.issubset(candidate_tasks):
            for task in sorted(candidate_tasks - requested_tasks):
                forbidden_matches.append(f"task_mismatch:{task}")
        if not req.allow_survey and "survey" in detected:
            forbidden_matches.append("survey_not_requested")

        penalty = min(0.54, 0.24 * len(forbidden_matches))
        if req.required_concepts:
            raw_score = (
                0.78 * coverage
                + 0.08 * optional_coverage
                + 0.09 * lexical_coverage
                + 0.05 * title_coverage
                - penalty
            )
            threshold = MIN_RELEVANCE_SCORE
            deterministic_pass = not missing and not forbidden_matches
        else:
            # Unknown research areas still use a deterministic lexical gate;
            # they are not silently accepted merely because a source returned.
            raw_score = lexical_coverage
            coverage = lexical_coverage
            threshold = 0.45
            deterministic_pass = lexical_coverage >= threshold

        llm_veto = candidate.llm_relevance_label.upper() == "IRRELEVANT"
        if llm_veto:
            forbidden_matches.append("llm_irrelevant_veto")
        score = round(max(0.0, min(1.0, raw_score)), 3)
        passed = bool(deterministic_pass and score >= threshold and not llm_veto)
        reason = _assessment_reason(
            score=score,
            threshold=threshold,
            coverage=coverage,
            matched=matched,
            missing=missing,
            forbidden=forbidden_matches,
            passed=passed,
        )
        return CandidateRelevanceAssessment(
            score=score,
            concept_coverage=round(coverage, 3),
            matched_concepts=tuple(matched),
            missing_concepts=tuple(missing),
            forbidden_intent_matches=tuple(forbidden_matches),
            passed=passed,
            reason=reason,
        )

    def evaluate_candidate(
        self,
        query_plan: QueryPlan,
        candidate: CandidatePaper,
        *,
        requirements: QueryRelevanceRequirements | None = None,
    ) -> CandidatePaper:
        req = requirements or self.requirements(query_plan)
        assessment = self.assess(query_plan, candidate, requirements=req)
        gate_metadata = {
            "evaluated": True,
            "passed": assessment.passed,
            "score": assessment.score,
            "minimum_score": MIN_RELEVANCE_SCORE if req.required_concepts else 0.45,
            "deep_read_minimum_score": MIN_DEEP_READ_RELEVANCE_SCORE,
            "concept_coverage": assessment.concept_coverage,
            "required_concepts": list(req.required_concepts),
            "optional_concepts": list(req.optional_concepts),
            "matched_concepts": list(assessment.matched_concepts),
            "missing_concepts": list(assessment.missing_concepts),
            "forbidden_intent_matches": list(assessment.forbidden_intent_matches),
            "allow_survey": req.allow_survey,
            "reason": assessment.reason,
        }
        return candidate.model_copy(
            update={
                "relevance_score": assessment.score,
                "rule_relevance_score": assessment.score,
                "matched_concepts": list(assessment.matched_concepts),
                "missing_concepts": list(assessment.missing_concepts),
                "relevance_reason": assessment.reason,
                "relevance_gate_evaluated": True,
                "relevance_gate_passed": assessment.passed,
                "concept_coverage": assessment.concept_coverage,
                "forbidden_intent_matches": list(assessment.forbidden_intent_matches),
                "raw_source_metadata": {
                    **candidate.raw_source_metadata,
                    "relevance_gate": gate_metadata,
                },
            }
        )

    def evaluate_and_rank(
        self,
        query_plan: QueryPlan,
        candidates: Sequence[CandidatePaper],
    ) -> list[CandidatePaper]:
        req = self.requirements(query_plan)
        assessed = [
            self.evaluate_candidate(query_plan, candidate, requirements=req)
            for candidate in candidates
        ]
        indexed = list(enumerate(assessed))
        indexed.sort(
            key=lambda pair: (
                0 if pair[1].relevance_gate_passed else 1,
                -pair[1].rule_relevance_score,
                pair[1].rerank_rank or pair[1].search_rank or pair[0] + 1,
            )
        )
        return [candidate for _index, candidate in indexed]


def detect_concepts(text: str) -> set[str]:
    normalized = _normalize_text(text)
    return {
        rule.name
        for rule in _CONCEPT_RULES
        if any(_contains_alias(normalized, alias) for alias in rule.aliases)
    }


def _query_text(query_plan: QueryPlan) -> str:
    # Deliberately exclude query_variants: heuristic variants contain survey
    # and review terms that the user did not necessarily request.
    return " ".join(
        value
        for value in (
            query_plan.user_query,
            query_plan.english_query,
            query_plan.direction_en,
            " ".join(query_plan.core_terms),
        )
        if value
    )


def _candidate_text(candidate: CandidatePaper) -> str:
    categories = candidate.raw_source_metadata.get("categories", [])
    if not isinstance(categories, list):
        categories = [categories]
    return _normalize_text(
        " ".join(
            [
                candidate.title,
                candidate.abstract,
                candidate.tldr,
                " ".join(str(item) for item in categories[:8]),
            ]
        )
    )


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text or "").lower()
    normalized = re.sub(r"[-_/]+", " ", normalized)
    normalized = re.sub(r"[^\w\u4e00-\u9fff]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _contains_alias(text: str, alias: str) -> bool:
    normalized_alias = _normalize_text(alias)
    if not normalized_alias:
        return False
    if any("\u4e00" <= char <= "\u9fff" for char in normalized_alias):
        return normalized_alias in text
    return re.search(rf"(?<![a-z0-9]){re.escape(normalized_alias)}(?![a-z0-9])", text) is not None


def _fallback_terms(query_plan: QueryPlan) -> list[str]:
    source = " ".join(
        value
        for value in (query_plan.english_query, query_plan.direction_en, query_plan.user_query)
        if value
    )
    tokens = re.findall(r"[a-z0-9]+", _normalize_text(source))
    return _unique(token for token in tokens if len(token) >= 3 and token not in _STOPWORDS)


def _lexical_coverage(text: str, terms: Iterable[str]) -> float:
    term_list = list(terms)
    if not term_list:
        return 0.0
    return sum(1 for term in term_list if _contains_alias(text, term)) / len(term_list)


def _concept_coverage(text: str, concepts: Iterable[str]) -> float:
    concept_list = list(concepts)
    if not concept_list:
        return 0.0
    detected = detect_concepts(text)
    return sum(1 for concept in concept_list if concept in detected) / len(concept_list)


def _assessment_reason(
    *,
    score: float,
    threshold: float,
    coverage: float,
    matched: list[str],
    missing: list[str],
    forbidden: list[str],
    passed: bool,
) -> str:
    verdict = "PASS" if passed else "FAIL"
    parts = [
        f"deterministic_relevance={verdict}",
        f"score={score:.3f}",
        f"threshold={threshold:.3f}",
        f"coverage={coverage:.3f}",
        f"matched={','.join(matched) or 'none'}",
    ]
    if missing:
        parts.append(f"missing={','.join(missing)}")
    if forbidden:
        parts.append(f"intent_mismatch={','.join(forbidden)}")
    return "; ".join(parts)


def _unique(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value and value not in seen:
            result.append(value)
            seen.add(value)
    return result
