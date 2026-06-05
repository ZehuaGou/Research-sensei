from __future__ import annotations

import logging
import re
import time

import httpx

from researchsensei.schemas import CandidatePaper, VerificationStatus

logger = logging.getLogger(__name__)

_USER_AGENT = "ResearchSensei/0.5 (+https://github.com/ZehuaGou/Research-sensei)"

_ARXIV_URL_RE = re.compile(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})(?:v\d+)?(?:\.pdf)?")


class CandidateVerifier:
    """M1.4 three-layer candidate verification.

    Layer 1: arXiv ID lookup (from arxiv_id field or extracted from pdf_url/landing_url)
    Layer 2: CrossRef DOI lookup
    Layer 3: Semantic Scholar fuzzy title search

    Key rules:
    - DOI 404 does NOT terminate verification; layers continue.
    - Transient API failure = verify_pending, not unverified.
    - Only if ALL available layers fail to confirm is the paper UNVERIFIED.
    """

    def __init__(
        self,
        *,
        timeout_seconds: float = 15.0,
        s2_api_key: str = "",
        enabled: bool = True,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.s2_api_key = s2_api_key
        self.enabled = enabled
        self._client = httpx.Client(
            headers={"User-Agent": _USER_AGENT},
            trust_env=True,
            timeout=timeout_seconds,
        )

    def verify(self, paper: CandidatePaper) -> CandidatePaper:
        """Run multi-layer verification on a candidate paper.

        Layers are tried in order. A confirmed result (VERIFIED) stops.
        A failed-but-not-terminal result (e.g. DOI 404) continues to next layer.
        Transient errors set VERIFY_PENDING and stop (don't mask with next layer).
        """
        if not self.enabled:
            return paper

        # Collect best non-terminal results across layers
        pending_results: list[CandidatePaper] = []
        arxiv_id = self._resolve_arxiv_id(paper)

        # Layer 1: arXiv ID
        if arxiv_id:
            result = self._verify_arxiv(paper, arxiv_id)
            if result is not None:
                if result.verification_status == VerificationStatus.VERIFIED:
                    return result
                if result.verification_status == VerificationStatus.VERIFY_PENDING:
                    pending_results.append(result)
                # UNVERIFIED/ERROR from arXiv → continue to next layer

        # Layer 2: CrossRef DOI
        if paper.doi:
            result = self._verify_crossref(paper)
            if result is not None:
                if result.verification_status == VerificationStatus.VERIFIED:
                    return result
                if result.verification_status == VerificationStatus.VERIFY_PENDING:
                    pending_results.append(result)
                # UNVERIFIED/ERROR from CrossRef → continue to next layer

        # Layer 3: Semantic Scholar fuzzy title
        result = self._verify_s2_title(paper)
        if result is not None:
            if result.verification_status == VerificationStatus.VERIFIED:
                return result
            if result.verification_status == VerificationStatus.VERIFY_PENDING:
                pending_results.append(result)

        # If we have any pending (transient error), return that
        if pending_results:
            return pending_results[0]

        # All layers exhausted — check if we even had anything to verify
        has_arxiv = bool(arxiv_id)
        has_doi = bool(paper.doi.strip()) if paper.doi else False
        has_title = bool(paper.title.strip()) if paper.title else False

        if not has_arxiv and not has_doi and not has_title:
            return paper.model_copy(
                update={
                    "verification_status": VerificationStatus.UNVERIFIED,
                    "verification_method": "no_identifier_available",
                    "verification_reason": "No arXiv ID, DOI, or verifiable title found.",
                    "verification_confidence": "low",
                }
            )

        # All layers ran but none confirmed
        methods_tried = []
        if has_arxiv:
            methods_tried.append("arxiv_id_lookup")
        if has_doi:
            methods_tried.append("crossref_doi_lookup")
        if has_title:
            methods_tried.append("s2_title_search")

        return paper.model_copy(
            update={
                "verification_status": VerificationStatus.UNVERIFIED,
                "verification_method": "+".join(methods_tried),
                "verification_reason": f"All verification layers failed to confirm: {', '.join(methods_tried)}.",
                "verification_confidence": "low",
            }
        )

    def verify_batch(self, candidates: list[CandidatePaper]) -> list[CandidatePaper]:
        """Verify a batch of candidates."""
        if not self.enabled:
            return candidates
        return [self.verify(paper) for paper in candidates]

    @staticmethod
    def _resolve_arxiv_id(paper: CandidatePaper) -> str:
        """Extract arxiv_id from field, pdf_url, or landing_url."""
        if paper.arxiv_id:
            clean = re.sub(r"v\d+$", "", paper.arxiv_id.strip().removeprefix("arXiv:").removeprefix("arxiv:"))
            if re.fullmatch(r"\d{4}\.\d{4,5}", clean):
                return clean

        for url_field in (paper.pdf_url, paper.landing_url, paper.url, paper.source_url):
            if not url_field:
                continue
            m = _ARXIV_URL_RE.search(url_field)
            if m:
                return m.group(1)
        return ""

    def _verify_arxiv(self, paper: CandidatePaper, arxiv_id: str) -> CandidatePaper | None:
        """Layer 1: Verify via arXiv id_list lookup."""
        url = f"https://export.arxiv.org/api/query?id_list={arxiv_id}"

        try:
            response = self._client.get(url)
            if response.status_code == 200 and "<entry>" in response.text:
                xml_title = _extract_arxiv_title(response.text)
                title_match = _titles_match(paper.title, xml_title)
                confidence = "high" if title_match else "medium"
                return paper.model_copy(
                    update={
                        "verification_status": VerificationStatus.VERIFIED,
                        "verification_method": "arxiv_id_lookup",
                        "verification_reason": f"arXiv ID {arxiv_id} confirmed. Title match: {title_match}.",
                        "verification_confidence": confidence,
                    }
                )
            if response.status_code in {429, 503}:
                return paper.model_copy(
                    update={
                        "verification_status": VerificationStatus.VERIFY_PENDING,
                        "verification_method": "arxiv_id_lookup",
                        "verification_reason": f"arXiv returned {response.status_code} during verification.",
                        "verification_confidence": "low",
                    }
                )
            # arXiv returned 200 but no entry — ID not found, continue
            return None
        except (httpx.TimeoutException, httpx.ConnectError, OSError) as exc:
            return paper.model_copy(
                update={
                    "verification_status": VerificationStatus.VERIFY_PENDING,
                    "verification_method": "arxiv_id_lookup",
                    "verification_reason": f"arXiv verification network error: {type(exc).__name__}.",
                    "verification_confidence": "low",
                }
            )
        except Exception as exc:
            return paper.model_copy(
                update={
                    "verification_status": VerificationStatus.ERROR,
                    "verification_method": "arxiv_id_lookup",
                    "verification_reason": f"arXiv verification error: {type(exc).__name__}: {str(exc)[:120]}.",
                    "verification_confidence": "low",
                }
            )

    def _verify_crossref(self, paper: CandidatePaper) -> CandidatePaper | None:
        """Layer 2: Verify via CrossRef DOI lookup."""
        doi = paper.doi.strip()
        if not doi:
            return None

        clean_doi = doi.removeprefix("doi:").removeprefix("DOI:")
        clean_doi = re.sub(r"^https?://doi\.org/", "", clean_doi, flags=re.IGNORECASE)
        url = f"https://api.crossref.org/works/{clean_doi}"

        try:
            response = self._client.get(url)
            if response.status_code == 200:
                data = response.json()
                cr_title = ""
                if "message" in data and "title" in data["message"]:
                    titles = data["message"]["title"]
                    if titles:
                        cr_title = titles[0]
                title_match = _titles_match(paper.title, cr_title)
                confidence = "high" if title_match else "medium"
                return paper.model_copy(
                    update={
                        "verification_status": VerificationStatus.VERIFIED,
                        "verification_method": "crossref_doi_lookup",
                        "verification_reason": f"DOI {clean_doi} confirmed via CrossRef. Title match: {title_match}.",
                        "verification_confidence": confidence,
                    }
                )
            if response.status_code in {429, 503}:
                return paper.model_copy(
                    update={
                        "verification_status": VerificationStatus.VERIFY_PENDING,
                        "verification_method": "crossref_doi_lookup",
                        "verification_reason": f"CrossRef returned {response.status_code} during verification.",
                        "verification_confidence": "low",
                    }
                )
            # DOI not found in CrossRef — continue to next layer
            return None
        except (httpx.TimeoutException, httpx.ConnectError, OSError) as exc:
            return paper.model_copy(
                update={
                    "verification_status": VerificationStatus.VERIFY_PENDING,
                    "verification_method": "crossref_doi_lookup",
                    "verification_reason": f"CrossRef verification network error: {type(exc).__name__}.",
                    "verification_confidence": "low",
                }
            )
        except Exception as exc:
            return paper.model_copy(
                update={
                    "verification_status": VerificationStatus.ERROR,
                    "verification_method": "crossref_doi_lookup",
                    "verification_reason": f"CrossRef verification error: {type(exc).__name__}: {str(exc)[:120]}.",
                    "verification_confidence": "low",
                }
            )

    def _verify_s2_title(self, paper: CandidatePaper) -> CandidatePaper | None:
        """Layer 3: Verify via Semantic Scholar fuzzy title search."""
        title = paper.title.strip()
        if not title:
            return None

        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {"query": title[:200], "limit": 3, "fields": "title,year,authors"}
        headers = {"User-Agent": _USER_AGENT}
        if self.s2_api_key:
            headers["x-api-key"] = self.s2_api_key

        try:
            response = self._client.get(url, params=params, headers=headers)
            if response.status_code == 200:
                data = response.json()
                papers = data.get("data", [])
                best_match = False
                for p in papers:
                    if _titles_match(title, p.get("title", "")):
                        best_match = True
                        break
                if best_match:
                    return paper.model_copy(
                        update={
                            "verification_status": VerificationStatus.VERIFIED,
                            "verification_method": "s2_title_search",
                            "verification_reason": "Title fuzzy-matched in Semantic Scholar results.",
                            "verification_confidence": "medium",
                        }
                    )
                return None
            if response.status_code in {429, 503}:
                return paper.model_copy(
                    update={
                        "verification_status": VerificationStatus.VERIFY_PENDING,
                        "verification_method": "s2_title_search",
                        "verification_reason": f"Semantic Scholar returned {response.status_code} during verification.",
                        "verification_confidence": "low",
                    }
                )
            return None
        except (httpx.TimeoutException, httpx.ConnectError, OSError) as exc:
            return paper.model_copy(
                update={
                    "verification_status": VerificationStatus.VERIFY_PENDING,
                    "verification_method": "s2_title_search",
                    "verification_reason": f"Semantic Scholar verification network error: {type(exc).__name__}.",
                    "verification_confidence": "low",
                }
            )
        except Exception as exc:
            return paper.model_copy(
                update={
                    "verification_status": VerificationStatus.ERROR,
                    "verification_method": "s2_title_search",
                    "verification_reason": f"Semantic Scholar verification error: {type(exc).__name__}: {str(exc)[:120]}.",
                    "verification_confidence": "low",
                }
            )

    def close(self) -> None:
        self._client.close()


def _extract_arxiv_title(xml_text: str) -> str:
    """Extract title from arXiv Atom XML response."""
    match = re.search(r"<title>(.*?)</title>", xml_text, re.DOTALL)
    if match:
        title = match.group(1).strip()
        if title.lower().startswith("arxiv:"):
            return ""
        return title
    return ""


def _titles_match(title_a: str, title_b: str) -> bool:
    """Fuzzy title comparison: normalize and check containment."""
    if not title_a or not title_b:
        return False
    norm_a = re.sub(r"[^a-z0-9]+", " ", title_a.lower()).strip()
    norm_b = re.sub(r"[^a-z0-9]+", " ", title_b.lower()).strip()
    if not norm_a or not norm_b:
        return False
    if norm_a == norm_b:
        return True
    if len(norm_a) > 10 and len(norm_b) > 10:
        shorter = norm_a if len(norm_a) <= len(norm_b) else norm_b
        longer = norm_b if len(norm_a) <= len(norm_b) else norm_a
        if shorter in longer:
            return True
    return False
