import os
from unittest.mock import AsyncMock, patch

import pytest

from backend.llm.client import LLMClient
from backend.schemas import (
    DocumentIngestion,
    DocumentBlock,
    EvidenceIndex,
    EvidenceType,
    ModelProviderConfig,
    PaperSkeleton,
)
from backend.understanding import UnderstandingService


@pytest.mark.asyncio
async def test_skeleton_from_llm():
    config = ModelProviderConfig(name="mock", base_url="https://mock.com", api_key_env="MOCK_KEY", model="mock")
    os.environ["MOCK_KEY"] = "test"
    client = LLMClient(config)

    doc = DocumentIngestion(
        paper_id="p1",
        detected_language="en",
        sections={"abstract": "test", "method": "test method"},
        formulas=[], figures=[], tables=[], references=[],
        extraction_warnings=[], blocks=[],
    )
    evidence = EvidenceIndex(paper_id="p1", claims=[])

    mock_response = {
        "problem": {"plain": "问题描述", "technical": "Technical description", "evidence": []},
        "old_methods": [{"name": "Old", "description": "desc", "limitation": "limit"}],
        "bottleneck": [{"description": "bottleneck", "why_critical": "critical"}],
        "assumption": [{"description": "assumption", "justification": "justified"}],
        "representation": [{"description": "rep", "how_different": "diff"}],
        "mechanism": {"plain": "mechanism", "technical": "tech", "evidence": []},
        "objective": [{"formula_ref": "", "purpose": "obj", "why_this_form": "form"}],
        "experiments": [{"description": "exp", "what_proves": "proves", "limitations": "limit"}],
        "limitations": [],
        "transfer": [{"idea": "transfer", "potential_directions": ["d1"]}],
        "pattern_candidates": ["Structure Pattern"],
    }

    with patch.object(client, "chat_json", new_callable=AsyncMock, return_value=mock_response):
        service = UnderstandingService(llm_client=client)
        skeleton = await service.build_skeleton(doc, evidence)
        assert isinstance(skeleton, PaperSkeleton)
        assert skeleton.problem.plain == "问题描述"
        assert skeleton.mechanism.plain == "mechanism"
        assert len(skeleton.old_methods) == 1
        assert skeleton.pattern_candidates == ["Structure Pattern"]


def test_skeleton_fallback():
    doc = DocumentIngestion(
        paper_id="p1",
        detected_language="en",
        sections={"abstract": "test abstract"},
        formulas=[], figures=[], tables=[], references=[],
        extraction_warnings=[], blocks=[],
    )
    evidence = EvidenceIndex(paper_id="p1", claims=[])
    service = UnderstandingService(llm_client=None)
    skeleton = service._fallback_skeleton(doc, evidence)
    assert isinstance(skeleton, PaperSkeleton)
    assert skeleton.paper_id == "p1"
