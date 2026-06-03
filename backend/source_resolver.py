from __future__ import annotations

from pathlib import Path

import httpx

from backend.schemas import CandidatePaper, SourceStatus, SourceTrustFlags


class SourceResolverService:
    """Resolves source availability without owning crawler/parser logic."""

    def resolve(self, paper: CandidatePaper) -> SourceStatus:
        if paper.latex_source_url:
            source_kind = "latex_source"
            source_path = paper.latex_source_url
        elif paper.pdf_url:
            source_kind = "pdf"
            source_path = paper.pdf_url
        elif paper.url and "http" in paper.url:
            source_kind = "html_or_landing_page"
            source_path = paper.url
        else:
            source_kind = "abstract_only"
            source_path = ""
        venue_known = bool(paper.venue and paper.venue.lower() != "unknown")
        flags = SourceTrustFlags(
            is_peer_reviewed=False if "arxiv" in (paper.source or "").lower() else None,
            venue_known=venue_known,
            source_reliability="high" if venue_known else "unknown",
            warning=[] if source_kind != "abstract_only" else ["FULL_TEXT_MISSING", "ABSTRACT_ONLY"],
        )
        return SourceStatus(
            paper_id=paper.paper_id,
            source_kind=source_kind,
            source_path=source_path,
            warnings=list(flags.warning),
            source_trust_flags=flags,
        )

    def resolve_to_workspace(self, paper: CandidatePaper, run_dir: str | Path) -> SourceStatus:
        """Resolve and download direct PDF links into a run directory.

        This is intentionally not a crawler: it only uses explicit metadata
        links such as pdf_url or an arXiv id that deterministically maps to the
        public arXiv PDF endpoint.
        """

        run_path = Path(run_dir)
        run_path.mkdir(parents=True, exist_ok=True)
        remote_pdf = self._pdf_url(paper)
        if remote_pdf:
            try:
                response = httpx.get(remote_pdf, timeout=45, follow_redirects=True)
                response.raise_for_status()
                pdf_path = run_path / "source.pdf"
                pdf_path.write_bytes(response.content)
                return self._status(
                    paper,
                    source_kind="downloaded_pdf",
                    source_path=str(pdf_path),
                    warnings=[],
                )
            except Exception as error:
                return self._status(
                    paper,
                    source_kind="pdf_download_failed",
                    source_path=remote_pdf,
                    warnings=[f"PDF_DOWNLOAD_FAILED: {error}"],
                )

        status = self.resolve(paper)
        if status.source_kind == "abstract_only":
            status = status.model_copy(update={
                "warnings": [*status.warnings, "NEEDS_USER_UPLOAD_FULL_TEXT"],
            })
        return status

    def _status(
        self,
        paper: CandidatePaper,
        *,
        source_kind: str,
        source_path: str,
        warnings: list[str],
    ) -> SourceStatus:
        venue_known = bool(paper.venue and paper.venue.lower() != "unknown")
        flags = SourceTrustFlags(
            is_peer_reviewed=False if "arxiv" in (paper.source or "").lower() else None,
            venue_known=venue_known,
            source_reliability="high" if venue_known else "unknown",
            warning=warnings,
        )
        return SourceStatus(
            paper_id=paper.paper_id,
            source_kind=source_kind,
            source_path=source_path,
            warnings=warnings,
            source_trust_flags=flags,
        )

    def _pdf_url(self, paper: CandidatePaper) -> str:
        if paper.pdf_url:
            return paper.pdf_url
        arxiv_id = paper.arxiv_id.strip().removeprefix("arXiv:")
        if arxiv_id:
            return f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        if "arxiv.org/abs/" in paper.url:
            arxiv_id = paper.url.rstrip("/").rsplit("/", 1)[-1]
            return f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        return ""
