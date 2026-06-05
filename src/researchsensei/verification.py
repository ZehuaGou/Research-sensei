from __future__ import annotations

import logging
import re
import time

import httpx

from researchsensei.schemas import CandidatePaper, VerificationStatus

logger = logging.getLogger(__name__)

_USER_AGENT = "ResearchSensei/0.5 (+https://github.com/ZehuaGou/Research-sensei)"


class CandidateVerifier:
    """M1.4 three-layer candidate verification.

    Layer 1: arXiv ID lookup
    Layer 2: CrossRef DOI lookup
    Layer 3: Semantic Scholar fuzzy title search

    Unverified candidates cannot enter A_READ.
    Transient API failure = verify_pending, not hallucination.
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
        """Run 3-layer verification on a candidate paper."""
        if not self.enabled:
            return paper

        # Layer 1: arXiv ID
        if paper.arxiv_id:
            result = self._verify_arxiv(paper)
            if result is not None:
                return result

        # Layer 2: CrossRef DOI
        if paper.doi:
            result = self._verify_crossref(paper)
            if result is not None:
                return result

        # Layer 3: Semantic Scholar fuzzy title
        result = self._verify_s2_title(paper)
        if result is not None:
            return result

        # All layers exhausted without finding
        return paper.model_copy(
            update={
                "verification_status": VerificationStatus.UNVERIFIED,
                "verification_method": "no_identifier_available",
                "verification_reason": "No arXiv ID, DOI, or verifiable title found.",
                "verification_confidence": "low",
            }
        )

    def verify_batch(self, candidates: list[CandidatePaper]) -> list[CandidatePaper]:
        """Verify a batch of candidates."""
        if not self.enabled:
            return candidates
        return [self.verify(paper) for paper in candidates]

    def _verify_arxiv(self, paper: CandidatePaper) -> CandidatePaper | None:
        """Layer 1: Verify via arXiv id_list lookup."""
        arxiv_id = paper.arxiv_id.strip()
        if not arxiv_id:
            return None

        clean_id = re.sub(r"v\d+$", "", arxiv_id.removeprefix("arXiv:").removeprefix("arxiv:"))
        url = f"https://export.arxiv.org/api/query?id_list={clean_id}"

        try:
            response = self._client.get(url)
            if response.status_code == 200 and "<entry>" in response.text:
                # Parse title from XML response
                xml_title = _extract_arxiv_title(response.text)
                title_match = _titles_match(paper.title, xml_title)
                confidence = "high" if title_match else "medium"
                return paper.model_copy(
                    update={
                        "verification_status": VerificationStatus.VERIFIED,
                        "verification_method": "arxiv_id_lookup",
                        "verification_reason": f"arXiv ID {clean_id} confirmed. Title match: {title_match}.",
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
            # arXiv returned 200 but no entry — ID not found
            return paper.model_copy(
                update={
                    "verification_status": VerificationStatus.UNVERIFIED,
                    "verification_method": "arxiv_id_lookup",
                    "verification_reason": f"arXiv ID {clean_id} returned no entry.",
                    "verification_confidence": "low",
                }
            )
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
            return paper.model_copy(
                update={
                    "verification_status": VerificationStatus.UNVERIFIED,
                    "verification_method": "crossref_doi_lookup",
                    "verification_reason": f"DOI {clean_doi} not found in CrossRef (HTTP {response.status_code}).",
                    "verification_confidence": "low",
                }
            )
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
                            "verification_reason": f"Title fuzzy-matched in Semantic Scholar results.",
                            "verification_confidence": "medium",
                        }
                    )
                # No exact match found in results
                return paper.model_copy(
                    update={
                        "verification_status": VerificationStatus.UNVERIFIED,
                        "verification_method": "s2_title_search",
                        "verification_reason": f"Title not found among Semantic Scholar results.",
                        "verification_confidence": "low",
                    }
                )
            if response.status_code in {429, 503}:
                return paper.model_copy(
                    update={
                        "verification_status": VerificationStatus.VERIFY_PENDING,
                        "verification_method": "s2_title_search",
                        "verification_reason": f"Semantic Scholar returned {response.status_code} during verification.",
                        "verification_confidence": "low",
                    }
                )
            return paper.model_copy(
                update={
                    "verification_status": VerificationStatus.ERROR,
                    "verification_method": "s2_title_search",
                    "verification_reason": f"Semantic Scholar verification error (HTTP {response.status_code}).",
                    "verification_confidence": "low",
                }
            )
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
        # Skip the feed-level title
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
    # Exact match after normalization
    if norm_a == norm_b:
        return True
    # One contains the other (for slight variations)
    if len(norm_a) > 10 and len(norm_b) > 10:
        shorter = norm_a if len(norm_a) <= len(norm_b) else norm_b
        longer = norm_b if len(norm_a) <= len(norm_b) else norm_a
        if shorter in longer:
            return True
    return False
