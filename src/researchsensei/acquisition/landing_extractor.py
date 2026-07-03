"""OA venue landing page HTML -> PDF URL extractor.

Purpose:
- OpenAlex/S2 frequently return landing URLs (e.g. AAAI OJS, ACL Anthology,
  NeurIPS proceedings, CVF) rather than direct PDF URLs. This module fetches
  the landing HTML, parses it, and returns the actual PDF URL.

- Per-archive_kind strategies are registered as decorator functions because
  each venue's HTML differs. A generic fallback handles unknown venues.

- This module is **stateless**: it doesn't own routing logic. The caller
  (FullTextResolver) decides whether to call the extractor based on the
  ``landing_url_pattern`` registry match.

Care:
- HTML parsing uses BeautifulSoup4 (bs4). bs4 is a hard dependency
  (pyproject.toml lists it).
- All network fetching uses the httpx.Client passed in. Tests should inject
  a fake client.
- The extractor never raises; on parse/fetch error, it returns ``("", warnings)``.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Callable
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from researchsensei.acquisition.venue_registry import is_known_oa_landing

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# User Agent
# ---------------------------------------------------------------------------
def _build_user_agent() -> str:
    contact = os.getenv("RESEARCHSENSEI_CONTACT_EMAIL", "").strip()
    base = "ResearchSensei/0.5 (+https://github.com/ZehuaGou/Research-sensei)"
    return f"{base} mailto:{contact}" if contact else base


_PROJECT_UA = _build_user_agent()


@dataclass(frozen=True)
class LandingResult:
    """Result of a single extract() call.

    Attributes:
        pdf_url: the extracted PDF URL (absolute). "" when not found.
        warnings: list of issue strings, suitable for logging or surfacing.
        archive_kind: archive_kind matched by is_known_oa_landing.
        extracted_via: which strategy picked the winning URL ("meta"|"iframe"|"anchor"|...).
    """
    pdf_url: str = ""
    warnings: tuple[str, ...] = ()
    archive_kind: str = ""
    extracted_via: str = ""


# ---------------------------------------------------------------------------
# Extractor registry
# ---------------------------------------------------------------------------
ExtractorFn = Callable[..., str | None]
_EXTRACTOR_REGISTRY: dict[str, ExtractorFn] = {}
PROBE_ONLY_ARCHIVE_KINDS = {"acm_dl", "ieee", "springer", "other"}


def register(archive_kind: str) -> Callable[[ExtractorFn], ExtractorFn]:
    """Decorator: register a per-archive_kind HTML extractor."""

    def decorator(fn: ExtractorFn) -> ExtractorFn:
        _EXTRACTOR_REGISTRY[archive_kind] = fn
        return fn

    return decorator


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------
class LandingPdfExtractor:
    """Fetch an OA venue landing URL and extract the PDF URL from its HTML."""

    def __init__(
        self,
        *,
        http_client: httpx.Client | None = None,
        timeout_seconds: float = 20.0,
        user_agent: str = _PROJECT_UA,
    ) -> None:
        env_timeout = os.getenv("RESEARCHSENSEI_LANDING_FETCH_TIMEOUT", "")
        try:
            if env_timeout.strip():
                self.timeout_seconds = float(env_timeout)
            else:
                self.timeout_seconds = timeout_seconds
        except ValueError:
            self.timeout_seconds = timeout_seconds
        if http_client is not None:
            self.http_client = http_client
        else:
            self.http_client = httpx.Client(
                follow_redirects=True,
                trust_env=True,
                timeout=self.timeout_seconds,
                headers={"User-Agent": user_agent},
            )
        self.user_agent = user_agent

    def extract(self, landing_url: str) -> LandingResult:
        """Return a LandingResult for `landing_url`.

        Behavior:
        - Skip if URL doesn't match a known OA venue archive.
        - Fetch via passed http_client.
        - Try the archive's specific extractor first; on miss, run the generic fallback.
        - Network/parse errors become (warnings, pdf_url="").
        """
        is_oa, archive_kind, _ = is_known_oa_landing(landing_url)
        if not is_oa and archive_kind not in PROBE_ONLY_ARCHIVE_KINDS:
            return LandingResult(pdf_url="", warnings=("NOT_KNOWN_OA_VENUE",), archive_kind=archive_kind)
        warnings: list[str] = []
        try:
            resp = self.http_client.get(
                landing_url,
                timeout=self.timeout_seconds,
                follow_redirects=True,
            )
        except (httpx.TimeoutException, httpx.ConnectError, OSError) as exc:
            warnings.append(f"NETWORK_ERROR:{type(exc).__name__}")
            return LandingResult(pdf_url="", warnings=tuple(warnings), archive_kind=archive_kind)
        except Exception as exc:
            warnings.append(f"FETCH_ERROR:{type(exc).__name__}")
            return LandingResult(pdf_url="", warnings=tuple(warnings), archive_kind=archive_kind)
        if resp.status_code != 200:
            warnings.append(f"HTTP_{resp.status_code}")
            return LandingResult(pdf_url="", warnings=tuple(warnings), archive_kind=archive_kind)
        html = resp.text
        base_url = str(resp.url)
        extractor = _EXTRACTOR_REGISTRY.get(archive_kind, _generic_extract)
        extracted_via = ""
        try:
            url = extractor(html=html, base_url=base_url, archive_kind=archive_kind)
        except Exception as exc:
            warnings.append(f"EXTRACTOR_ERROR_{archive_kind}:{type(exc).__name__}")
            url = None
        if url:
            return LandingResult(
                pdf_url=url,
                warnings=tuple(warnings),
                archive_kind=archive_kind,
                extracted_via=archive_kind,
            )
        # Fallback to generic
        generic_url = _generic_extract(html=html, base_url=base_url, archive_kind=archive_kind)
        if generic_url:
            return LandingResult(
                pdf_url=generic_url,
                warnings=tuple(warnings) or (),
                archive_kind=archive_kind,
                extracted_via="generic",
            )
        warnings.append("NO_PDF_LINK_FOUND")
        return LandingResult(pdf_url="", warnings=tuple(warnings), archive_kind=archive_kind)


# ---------------------------------------------------------------------------
# Generic fallback extractor
# ---------------------------------------------------------------------------
def _generic_extract(*, html: str, base_url: str, archive_kind: str = "") -> str | None:
    """Find a PDF URL via generic HTML parsing strategies.

    Order:
    1. <meta name="citation_pdf_url"> (most reliable across venues)
    2. <iframe src="*.pdf">
    3. <a href="*.pdf"> where the link text mentions "pdf"
    """
    soup = BeautifulSoup(html, "html.parser")
    # meta citation_pdf_url
    meta = soup.find("meta", attrs={"name": "citation_pdf_url"})
    if meta and meta.get("content"):
        return urljoin(base_url, str(meta["content"]).strip())
    # iframe
    for iframe in soup.find_all("iframe", src=True):
        src = str(iframe["src"] or "")
        absolute = urljoin(base_url, src)
        if _looks_like_pdf_url(absolute):
            return absolute
    # anchor with .pdf href
    for a in soup.find_all("a", href=True):
        href = str(a["href"] or "")
        if not href:
            continue
        absolute = urljoin(base_url, href)
        if _looks_like_pdf_url(absolute):
            return absolute
    return None


def _looks_like_pdf_url(url: str) -> bool:
    lower = str(url or "").lower()
    return (
        lower.endswith(".pdf")
        or "/pdf" in lower
        or "pdf" in lower
        or "ieeexplore.ieee.org/stamp/stamp.jsp" in lower
    )


# ---------------------------------------------------------------------------
# Per-archive extractors
# ---------------------------------------------------------------------------
@register("neurips")
def _extract_neurips(*, html: str, base_url: str, archive_kind: str = "") -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    meta = soup.find("meta", attrs={"name": "citation_pdf_url"})
    if meta and meta.get("content"):
        return urljoin(base_url, str(meta["content"]).strip())
    # NeurIPS page has buttons; try a.btn-primary with .pdf href, then a.nav-link.
    for a in soup.select("a.btn-primary, a.btn, a.nav-link"):
        href = a.get("href")
        if href and ".pdf" in href.lower():
            return urljoin(base_url, href)
    return None


@register("pmr")
def _extract_pmr(*, html: str, base_url: str, archive_kind: str = "") -> str | None:
    """proceedings.mlr.press pages are simple; the citation meta is reliable."""
    soup = BeautifulSoup(html, "html.parser")
    meta = soup.find("meta", attrs={"name": "citation_pdf_url"})
    if meta and meta.get("content"):
        return urljoin(base_url, str(meta["content"]).strip())
    # PMLR pages often expose a Download PDF h2 right after the title
    for a in soup.select("a[href]"):
        text = (a.get_text() or "").strip().lower()
        href = str(a.get("href") or "")
        if "pdf" in text and href.lower().endswith(".pdf"):
            return urljoin(base_url, href)
    return None


@register("cvf")
def _extract_cvf(*, html: str, base_url: str, archive_kind: str = "") -> str | None:
    """CVF pages: <a href="/papers/CVPR2024_paper_xxx.pdf">PDF</a>.

    The link text typically contains "pdf" (case-insensitive). Skip supplemental links.
    """
    soup = BeautifulSoup(html, "html.parser")
    # First try meta (sometimes available)
    meta = soup.find("meta", attrs={"name": "citation_pdf_url"})
    if meta and meta.get("content"):
        url = urljoin(base_url, str(meta["content"]).strip())
        if "/papers/" in url and "supplemental" not in url.lower():
            return url
    # Anchor strategy: prefer text "PDF" + /papers/ + .pdf suffix.
    candidates: list[tuple[int, str]] = []
    for a in soup.find_all("a", href=True):
        href = str(a["href"] or "")
        if not href:
            continue
        text = (a.get_text() or "").strip().lower()
        full = urljoin(base_url, href)
        if not full.lower().endswith(".pdf"):
            continue
        # Score: matching link text "pdf download" > "pdf" > nothing
        score = 0
        if "pdf" in text:
            score += 2
        if "download" in text:
            score += 1
        if "/papers/" in full:
            score += 2
        if "supplemental" in full.lower() or "supp" in full.lower():
            score -= 5
        candidates.append((max(score, 0), full))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


@register("acl_anthology")
def _extract_acl(*, html: str, base_url: str, archive_kind: str = "") -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    meta = soup.find("meta", attrs={"name": "citation_pdf_url"})
    if meta and meta.get("content"):
        return urljoin(base_url, str(meta["content"]).strip())
    # Anthology pages have an <a class="btn" href="...{file}.pdf">
    for a in soup.select("a.btn, a.accordion-button, a.action-button"):
        href = a.get("href")
        if not href:
            continue
        full = urljoin(base_url, href)
        if full.lower().endswith(".pdf"):
            return full
    # Plain href: bias toward the PDF button text.
    for a in soup.find_all("a", href=True):
        href = str(a["href"] or "")
        if not href:
            continue
        absolute = urljoin(base_url, href)
        if absolute.lower().endswith(".pdf"):
            return absolute
    return None


@register("openreview")
def _extract_openreview(*, html: str, base_url: str, archive_kind: str = "") -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    meta = soup.find("meta", attrs={"name": "citation_pdf_url"})
    if meta and meta.get("content"):
        return urljoin(base_url, str(meta["content"]).strip())
    # OpenReview exposes <a href="/pdf?id=...">PDF</a>
    for a in soup.find_all("a", href=True):
        href = str(a["href"] or "")
        if "/pdf?" in href or href.lower().endswith(".pdf"):
            return urljoin(base_url, href)
    return None


@register("aaai")
def _extract_aaai(*, html: str, base_url: str, archive_kind: str = "") -> str | None:
    """OJS-hosted venues (AAAI, JAIR, AI Magazine).

    OJS papers typically expose <meta name="citation_pdf_url">, plus an
    <a href="...download/..."> link with text "PDF".
    """
    soup = BeautifulSoup(html, "html.parser")
    meta = soup.find("meta", attrs={"name": "citation_pdf_url"})
    if meta and meta.get("content"):
        return urljoin(base_url, str(meta["content"]).strip())
    for a in soup.find_all("a", href=True):
        href = str(a["href"] or "")
        text = (a.get_text() or "").strip().lower()
        absolute = urljoin(base_url, href)
        # OJS download path looks like /article/view/<id>/<idser> then .pdf
        if absolute.lower().endswith(".pdf") or ("download" in href.lower() and "pdf" in text):
            return absolute
    return None


@register("ijcai")
def _extract_ijcai(*, html: str, base_url: str, archive_kind: str = "") -> str | None:
    """IJCAI proceedings page: simple HTML with a single PDF link per paper."""
    soup = BeautifulSoup(html, "html.parser")
    # The PDF link is typically <a href="proceedings/2024/xxxx.pdf">pdf</a>
    for a in soup.find_all("a", href=True):
        href = str(a["href"] or "")
        if "proceedings" in href.lower() and href.lower().endswith(".pdf"):
            return urljoin(base_url, href)
    # Fallback to any .pdf anchor.
    for a in soup.find_all("a", href=True):
        href = str(a["href"] or "")
        absolute = urljoin(base_url, href)
        if absolute.lower().endswith(".pdf"):
            return absolute
    return None


@register("usenix")
def _extract_usenix(*, html: str, base_url: str, archive_kind: str = "") -> str | None:
    """USENIX paper pages: prominent "PDF" CTA button or direct file link."""
    soup = BeautifulSoup(html, "html.parser")
    meta = soup.find("meta", attrs={"name": "citation_pdf_url"})
    if meta and meta.get("content"):
        return urljoin(base_url, str(meta["content"]).strip())
    for a in soup.find_all("a", href=True):
        href = str(a["href"] or "")
        text = (a.get_text() or "").strip().lower()
        absolute = urljoin(base_url, href)
        # USENIX download links are usually /system/files/atc24-foo-bar.pdf
        if absolute.lower().endswith(".pdf") and ("pdf" in text or "downloads" in text or "download" in text):
            return absolute
    # Fallback: any .pdf link.
    for a in soup.find_all("a", href=True):
        href = str(a["href"] or "")
        absolute = urljoin(base_url, href)
        if absolute.lower().endswith(".pdf"):
            return absolute
    return None


@register("jmlr")
def _extract_jmlr(*, html: str, base_url: str, archive_kind: str = "") -> str | None:
    """JMLR article pages: the citation_pdf_url meta is reliable, but JMLR's
    paper pages expose plain <a href="papers/v28/abc.pdf"> links too."""
    soup = BeautifulSoup(html, "html.parser")
    meta = soup.find("meta", attrs={"name": "citation_pdf_url"})
    if meta and meta.get("content"):
        return urljoin(base_url, str(meta["content"]).strip())
    # JMLR article pages have a "PDF" link by title.
    for a in soup.find_all("a", href=True):
        href = str(a["href"] or "")
        text = (a.get_text() or "").strip().lower()
        if "pdf" in text and href.lower().endswith(".pdf"):
            return urljoin(base_url, href)
    return None


@register("vldb")
def _extract_vldb(*, html: str, base_url: str, archive_kind: str = "") -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    meta = soup.find("meta", attrs={"name": "citation_pdf_url"})
    if meta and meta.get("content"):
        return urljoin(base_url, str(meta["content"]).strip())
    # PVLDB volumes: any .pdf link.
    for a in soup.find_all("a", href=True):
        href = str(a["href"] or "")
        absolute = urljoin(base_url, href)
        if absolute.lower().endswith(".pdf"):
            return absolute
    return None


@register("acm_dl")
def _extract_acm_dl(*, html: str, base_url: str, archive_kind: str = "") -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    meta = soup.find("meta", attrs={"name": "citation_pdf_url"})
    if meta and meta.get("content"):
        return urljoin(base_url, str(meta["content"]).strip())
    for a in soup.find_all("a", href=True):
        href = str(a["href"] or "")
        full = urljoin(base_url, href)
        if "/doi/pdf/" in full.lower() or "/doi/epdf/" in full.lower() or _looks_like_pdf_url(full):
            return full
    return None


@register("ieee")
def _extract_ieee(*, html: str, base_url: str, archive_kind: str = "") -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    meta = soup.find("meta", attrs={"name": "citation_pdf_url"})
    if meta and meta.get("content"):
        return urljoin(base_url, str(meta["content"]).strip())
    for a in soup.find_all("a", href=True):
        href = str(a["href"] or "")
        full = urljoin(base_url, href)
        if "stamp/stamp.jsp" in full.lower() or _looks_like_pdf_url(full):
            return full
    return None


@register("springer")
def _extract_springer(*, html: str, base_url: str, archive_kind: str = "") -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    meta = soup.find("meta", attrs={"name": "citation_pdf_url"})
    if meta and meta.get("content"):
        return urljoin(base_url, str(meta["content"]).strip())
    for a in soup.find_all("a", href=True):
        href = str(a["href"] or "")
        full = urljoin(base_url, href)
        if "/content/pdf/" in full.lower() or _looks_like_pdf_url(full):
            return full
    return None
