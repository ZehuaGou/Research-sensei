from __future__ import annotations

import logging
from typing import Any

from researchsensei.llm.client import LLMClient, parse_llm_json
from researchsensei.llm.types import ChatMessage, LLMConfig
from researchsensei.schemas import CandidatePaper

logger = logging.getLogger(__name__)

_RELEVANCE_JUDGE_SYSTEM = """\
You are a research paper relevance judge. Given a user research query and a list \
of candidate papers (title, abstract, year, venue), judge each paper's relevance.

For each candidate, return:
- relevance_score: 0.0 to 1.0
- relevance_label: "HIGH", "MEDIUM", "LOW", or "IRRELEVANT"
- matched_concepts: list of query concepts that appear in the paper
- missing_concepts: list of important query concepts missing from the paper
- relevance_reason: brief explanation (1 sentence)
- should_download: true if worth downloading the full text
- should_a_read: true if worth deep reading (A_READ priority)

Be strict. A paper must clearly address the query topic to score HIGH. \
Papers that only tangentially mention the topic should score LOW or IRRELEVANT.

Return JSON:
{
  "judgments": [
    {
      "paper_id": "...",
      "relevance_score": 0.0,
      "relevance_label": "HIGH|MEDIUM|LOW|IRRELEVANT",
      "matched_concepts": ["..."],
      "missing_concepts": ["..."],
      "relevance_reason": "...",
      "should_download": true,
      "should_a_read": true
    }
  ]
}"""


class RelevanceJudge:
    """M1.4 LLM-based relevance judge for candidate papers.

    Uses real LLM to assess each candidate's relevance to the user query.
    Produces structured relevance judgments that feed into the A_READ gate.
    """

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        *,
        batch_size: int = 8,
        enabled: bool = True,
    ) -> None:
        self.llm_client = llm_client
        self.batch_size = batch_size
        self.enabled = enabled

    async def judge(
        self,
        query: str,
        candidates: list[CandidatePaper],
        *,
        config: LLMConfig | None = None,
    ) -> list[CandidatePaper]:
        """Judge relevance for a batch of candidates using real LLM."""
        if not self.enabled or not self.llm_client or not candidates:
            return candidates

        scored: list[CandidatePaper] = []
        for start in range(0, len(candidates), self.batch_size):
            batch = candidates[start : start + self.batch_size]
            judged_batch = await self._judge_batch(query, batch, config=config)
            scored.extend(judged_batch)
        return scored

    async def _judge_batch(
        self,
        query: str,
        candidates: list[CandidatePaper],
        *,
        config: LLMConfig | None = None,
    ) -> list[CandidatePaper]:
        """Judge a single batch of candidates."""
        user_message = _build_user_message(query, candidates)
        messages = [
            ChatMessage(role="system", content=_RELEVANCE_JUDGE_SYSTEM),
            ChatMessage(role="user", content=user_message),
        ]

        try:
            cfg = config or LLMConfig(temperature=0.1, max_tokens=2048, json_mode=True)
            response = await self.llm_client.chat(messages, config=cfg)
            data = parse_llm_json(response.content)
            judgments = data.get("judgments", []) if isinstance(data, dict) else []

            judgment_map: dict[str, dict[str, Any]] = {}
            for j in judgments:
                if isinstance(j, dict) and "paper_id" in j:
                    judgment_map[str(j["paper_id"])] = j

            return [_apply_judgment(candidate, judgment_map.get(candidate.paper_id, {})) for candidate in candidates]

        except Exception as exc:
            logger.warning("LLM relevance judge failed: %s: %s", type(exc).__name__, str(exc)[:200])
            return candidates

    async def judge_with_score(
        self,
        query: str,
        candidates: list[CandidatePaper],
        *,
        config: LLMConfig | None = None,
    ) -> tuple[list[CandidatePaper], dict[str, Any]]:
        """Judge relevance and return metadata about the judgment process."""
        metadata: dict[str, Any] = {
            "llm_judged_candidate_count": 0,
            "relevance_filtered_count": 0,
        }
        if not self.enabled or not self.llm_client or not candidates:
            return candidates, metadata

        scored = await self.judge(query, candidates, config=config)
        metadata["llm_judged_candidate_count"] = len(candidates)
        metadata["relevance_filtered_count"] = sum(
            1 for c in scored
            if c.llm_relevance_label in ("IRRELEVANT", "LOW") or c.llm_relevance_score < 0.3
        )
        return scored, metadata


def _build_user_message(query: str, candidates: list[CandidatePaper]) -> str:
    """Build user message with query and candidate summaries."""
    parts = [f"Research query: {query}\n", "Candidates:"]
    for i, c in enumerate(candidates, 1):
        year_str = f" ({c.year})" if c.year else ""
        abstract_preview = (c.abstract[:300] + "...") if len(c.abstract) > 300 else c.abstract
        parts.append(
            f"\n{i}. paper_id={c.paper_id}\n"
            f"   title: {c.title}{year_str}\n"
            f"   venue: {c.venue or 'unknown'}\n"
            f"   abstract: {abstract_preview}"
        )
    return "\n".join(parts)


def _apply_judgment(candidate: CandidatePaper, judgment: dict[str, Any]) -> CandidatePaper:
    """Apply an LLM judgment to a candidate paper."""
    if not judgment:
        return candidate

    score = float(judgment.get("relevance_score", 0.0))
    label = str(judgment.get("relevance_label", "LOW")).upper()
    matched = [str(c) for c in judgment.get("matched_concepts", [])]
    missing = [str(c) for c in judgment.get("missing_concepts", [])]
    reason = str(judgment.get("relevance_reason", ""))
    should_download = bool(judgment.get("should_download", False))
    should_a_read = bool(judgment.get("should_a_read", False))

    return candidate.model_copy(
        update={
            "rule_relevance_score": candidate.rule_relevance_score or score,
            "llm_relevance_score": round(score, 3),
            "llm_relevance_label": label,
            "matched_concepts": matched,
            "missing_concepts": missing,
            "relevance_reason": reason or candidate.relevance_reason,
            "should_download": should_download or candidate.should_download,
            "should_a_read": should_a_read or candidate.should_a_read,
        }
    )


