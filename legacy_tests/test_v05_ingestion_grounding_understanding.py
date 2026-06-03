import asyncio

from backend.grounding import GroundingService
from backend.ingestion import IngestionService
from backend.schemas import BlockType, EvidenceType
from backend.understanding import UnderstandingService


SAMPLE_TEXT = """
Title: Tiny Paper
Abstract
We study anomaly detection in multivariate time series.
Introduction
Old forecasting-error methods miss dependency changes.
Method
We minimize L = L_rec + lambda L_graph to model sensor dependencies.
Experiments
Table 1 shows better F1 on SWaT.
Conclusion
The graph assumption can fail when sensors are independent.
"""


def test_ingestion_outputs_blocks_with_evidence_refs_and_formula_block():
    doc = IngestionService().ingest_text("paper_x", SAMPLE_TEXT)

    assert doc.detected_language == "en"
    assert any(block.type == BlockType.PARAGRAPH for block in doc.blocks)
    formula_blocks = [block for block in doc.blocks if block.type == BlockType.FORMULA]
    assert formula_blocks
    assert formula_blocks[0].evidence_ref == "paper_x:eq001"


def test_grounding_and_understanding_keep_evidence_state():
    doc = IngestionService().ingest_text("paper_x", SAMPLE_TEXT)
    evidence = GroundingService().build_index(doc)
    skeleton = asyncio.run(UnderstandingService().build_skeleton(doc, evidence))

    assert evidence.claims
    assert any(claim.evidence_type == EvidenceType.SUPPORTED_BY_EXPERIMENT for claim in evidence.claims)
    assert skeleton.problem.plain
    assert skeleton.mechanism.evidence
    assert skeleton.objective[0].formula_ref == "eq001"
