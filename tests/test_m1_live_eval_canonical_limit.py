from __future__ import annotations

from pathlib import Path

from researchsensei.direction.runner import DirectionRunner
from researchsensei.schemas.canonical import CanonicalizationResult
from researchsensei.schemas.direction import CandidatePaper, ResolvedPaperSource, SourceResolutionResult
from researchsensei.schemas.enums import CanonicalQualityStatus, CanonicalizationStatus, PaperSourceStatus, PaperSourceType, SourcePriority
from researchsensei.workspace import WorkspaceStore


class CountingNormalizer:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def normalize(self, candidate, source_item, output_dir):
        self.calls.append(candidate.paper_id)
        return CanonicalizationResult(
            paper_id=candidate.paper_id,
            title=candidate.title,
            source_type="pdf",
            source_priority=SourcePriority.PDF,
            preferred_m2_input="pdf",
            has_valid_deep_reading_source=True,
            canonical_paper_path=str(Path(output_dir) / "canonical_paper.md"),
            canonicalization_status=CanonicalizationStatus.SUCCESS,
            canonical_quality_status=CanonicalQualityStatus.PASS,
            m2_ready=True,
        )


def test_direction_runner_default_source_is_paper_search_mcp(tmp_path) -> None:
    runner = DirectionRunner(workspace=WorkspaceStore(tmp_path / "workspace"))

    assert runner.sources == ["paper_search"]


def test_direction_runner_limits_live_canonicalization_to_source_candidates(tmp_path) -> None:
    normalizer = CountingNormalizer()
    runner = DirectionRunner(
        workspace=WorkspaceStore(tmp_path / "workspace"),
        material_normalizer=normalizer,
        max_canonicalize_candidates=1,
    )
    candidates = [
        CandidatePaper(paper_id="p1", title="Paper 1"),
        CandidatePaper(paper_id="p2", title="Paper 2"),
        CandidatePaper(paper_id="p3", title="Paper 3"),
    ]
    source_resolution = SourceResolutionResult(
        query="q",
        items=[
            ResolvedPaperSource(
                paper_id="p1",
                title="Paper 1",
                source_type=PaperSourceType.PDF,
                status=PaperSourceStatus.RESOLVED_PDF_DOWNLOADED,
                local_path="p1.pdf",
                source_priority=SourcePriority.PDF,
                has_valid_deep_reading_source=True,
            ),
            ResolvedPaperSource(
                paper_id="p2",
                title="Paper 2",
                source_type=PaperSourceType.PDF,
                status=PaperSourceStatus.RESOLVED_PDF_DOWNLOADED,
                local_path="p2.pdf",
                source_priority=SourcePriority.PDF,
                has_valid_deep_reading_source=True,
            ),
        ],
    )

    results = runner._canonicalize_resolved_candidates(candidates, source_resolution, tmp_path / "canonical")

    assert normalizer.calls == ["p1"]
    assert [result.paper_id for result in results] == ["p1"]
