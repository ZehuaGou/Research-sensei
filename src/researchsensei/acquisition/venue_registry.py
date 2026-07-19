"""Venue registry mapping venue strings to OA archive/ranking/source info.

This module is **code-as-data**: VENUE_REGISTRY is a literal dict with no
runtime IO. Tests assert stability; lookups are deterministic.

Used by:
- selection.venue_rankings: replace TOP_VENUE_TERMS keyword matching
- acquisition.landing_extractor: identify OA landing pages and route to
  per-archive_kind HTML extractors
- acquisition.fulltext_resolver: add "OA venue landing" branches to the
  PDF discovery chain
- acquisition.openalex_adapter: venue-targeted search via openalex_source_ids
- query.query_planner: infer venue targets + year range from user query

OpenAlex source IDs are populated from output/openalex_source_ids/openalex_source_ids.json (run 1).
Missing 4 venues (STOC, OSDI, SOSP, EUROCRYPT) have empty tuples; venue-targeted
search falls back to free-text search when no source IDs are present.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from researchsensei.schemas.enums import VenueRank


# ---------------------------------------------------------------------------
# archive_kind vocabulary
# ---------------------------------------------------------------------------
# Each archive_kind maps 1:1 to a handler in landing_extractor.LandingExtractor.
# New archive_kinds must have:
#   - a registered extractor function (see landing_extractor.py)
#   - a landing_url_pattern that uniquely identifies it
#   - a fixture HTML sample (tests/fixtures/oa_landing_pages/{kind}_sample.html)
# ---------------------------------------------------------------------------
ARCHIVE_KINDS = (
    "neurips",
    "pmr",             # proceedings.mlr.press (ICML, PMLR series)
    "openreview",      # ICLR, TMLR
    "cvf",             # openaccess.thecvf.com (CVPR/ICCV/ECCV)
    "acl_anthology",   # aclanthology.org (ACL/EMNLP/NAACL)
    "aaai",            # ojs.aaai.org (OJS)
    "ijcai",           # ijcai.org/proceedings
    "usenix",          # usenix.org/conference (OSDI/NSDI/ATC/Security)
    "jmlr",            # jmlr.org/papers
    "vldb",            # vlldb.org/pvldb (PVLDB is OA)
    "ieee",            # ieeexplore.ieee.org/document (paywalled)
    "acm_dl",          # dl.acm.org/doi (paywalled; some OA)
    "springer",        # link.springer.com/article (paywalled; some OA)
    "other",
)


@dataclass(frozen=True)
class VenueConfig:
    """All info about a venue that downstream code uses.

    Fields intentionally frozen so a registry entry is hashable and immutable.
    """
    canonical_name: str
    # Substring aliases used by lookup_venue() for fuzzy matching. Lowercased.
    aliases: tuple[str, ...]
    rank: VenueRank = VenueRank.UNRANKED
    is_oa: bool = False
    archive_kind: str = "other"
    # OpenAlex source IDs (URL form OR bare form). Empty list = use fallback.
    openalex_source_ids: tuple[str, ...] = ()
    # Regex to recognize this venue's landing URL in `best_oa_location.landing_page_url`.
    landing_url_pattern: re.Pattern[str] | None = None
    # Heuristic estimate: 0.0-1.0 of this venue's papers also have an arXiv preprint.
    # Used by selection service / ranking to estimate OA coverage.
    typical_arxiv_coverage: float = 0.0
    # Optional CSS selector hint for landing_extractor. None = generic extractor.
    pdf_link_selector: str | None = None


# ---------------------------------------------------------------------------
# Helper: build a VenueConfig succinctly
# ---------------------------------------------------------------------------
def _cfg(
    canonical_name: str,
    aliases: Iterable[str],
    *,
    rank: VenueRank = VenueRank.UNRANKED,
    is_oa: bool = False,
    archive_kind: str = "other",
    openalex_source_ids: Iterable[str] = (),
    landing_url_pattern: str = "",
    typical_arxiv_coverage: float = 0.0,
    pdf_link_selector: str | None = None,
) -> VenueConfig:
    return VenueConfig(
        canonical_name=canonical_name,
        aliases=tuple(a.lower() for a in aliases),
        rank=rank,
        is_oa=is_oa,
        archive_kind=archive_kind,
        openalex_source_ids=tuple(openalex_source_ids),
        landing_url_pattern=re.compile(landing_url_pattern, re.I) if landing_url_pattern else None,
        typical_arxiv_coverage=typical_arxiv_coverage,
        pdf_link_selector=pdf_link_selector,
    )


# ---------------------------------------------------------------------------
# VENUE_REGISTRY
# ---------------------------------------------------------------------------
# OpenAlex source IDs are bare strings (without "https://openalex.org/" prefix) for clarity.
# Calling code should re-add the prefix when sending to OpenAlex API.
# Source IDs came from output/openalex_source_ids/openalex_source_ids.json (run 1).
# Missing or uncertain entries: tuple is empty -> venue-targeted search will fall back.
# CCF A-class list is the seed; B-class venues are added where they are widely cited.
# ---------------------------------------------------------------------------

VENUE_REGISTRY: dict[str, VenueConfig] = {
    # ===================== AI / ML conferences (CCF A) =====================
    "neurips": _cfg(
        "NeurIPS",
        ("neurips", "neural information processing systems", "nips"),  # "nips" is legacy
        rank=VenueRank.A_STAR,
        is_oa=True,
        archive_kind="neurips",
        openalex_source_ids=("S4306420609",),
        landing_url_pattern=r"proceedings\.neurips\.cc/paper",
        typical_arxiv_coverage=0.85,
        pdf_link_selector='meta[name="citation_pdf_url"]',
    ),
    "icml": _cfg(
        "ICML",
        ("icml", "international conference on machine learning"),
        rank=VenueRank.A_STAR,
        is_oa=True,
        archive_kind="pmr",
        openalex_source_ids=("S4306419644",),
        landing_url_pattern=r"proceedings\.mlr\.press/v",
        typical_arxiv_coverage=0.85,
        pdf_link_selector='meta[name="citation_pdf_url"]',
    ),
    "iclr": _cfg(
        "ICLR",
        ("iclr", "international conference on learning representations", "learning representations"),
        rank=VenueRank.A_STAR,
        is_oa=True,
        archive_kind="openreview",
        openalex_source_ids=("S4306419637",),
        landing_url_pattern=r"openreview\.net/(?:forum|pdf)",
        typical_arxiv_coverage=0.95,
    ),

    # ===================== Computer vision =====================
    "cvpr": _cfg(
        "CVPR",
        ("cvpr", "computer vision and pattern recognition", "ieee/cvf conference on computer vision and pattern recognition"),
        rank=VenueRank.A_STAR,
        is_oa=True,                   # CVF mirror is OA
        archive_kind="cvf",
        openalex_source_ids=("S4306417987", "S4363607701"),  # 2022 IEEE/CVF + generic CVPR
        landing_url_pattern=r"openaccess\.thecvf\.com/content",
        typical_arxiv_coverage=0.85,
    ),
    "iccv": _cfg(
        "ICCV",
        ("iccv", "international conference on computer vision"),
        rank=VenueRank.A_STAR,
        is_oa=True,
        archive_kind="cvf",
        openalex_source_ids=("S4306419272",),
        landing_url_pattern=r"openaccess\.thecvf\.com/content",
        typical_arxiv_coverage=0.85,
    ),
    "eccv": _cfg(
        "ECCV",
        ("eccv", "european conference on computer vision"),
        rank=VenueRank.A,
        is_oa=True,
        archive_kind="cvf",
        # was not in run 1's CCF list; we add it for completeness
        openalex_source_ids=(),
        landing_url_pattern=r"openaccess\.thecvf\.com/content|(?:link\.springer\.com/chapter/10\.1007/978-3-030-\d+)",
        typical_arxiv_coverage=0.80,
    ),

    # ===================== NLP =====================
    "acl": _cfg(
        "ACL",
        ("acl", "annual meeting of the association for computational linguistics", "acl annual meeting"),
        rank=VenueRank.A_STAR,
        is_oa=True,
        archive_kind="acl_anthology",
        openalex_source_ids=("S4363608652",),  # 60th long papers; ACL splits by year
        landing_url_pattern=r"aclanthology\.org/",
        typical_arxiv_coverage=0.85,
    ),
    "emnlp": _cfg(
        "EMNLP",
        ("emnlp", "empirical methods in natural language processing", "empirical methods on natural language processing"),
        rank=VenueRank.A_STAR,
        is_oa=True,
        archive_kind="acl_anthology",
        openalex_source_ids=(),
        landing_url_pattern=r"aclanthology\.org/",
        typical_arxiv_coverage=0.85,
    ),
    "naacl": _cfg(
        "NAACL",
        ("naacl", "north american chapter of the association for computational linguistics"),
        rank=VenueRank.A,
        is_oa=True,
        archive_kind="acl_anthology",
        openalex_source_ids=(),
        landing_url_pattern=r"aclanthology\.org/",
        typical_arxiv_coverage=0.85,
    ),

    # ===================== AI =====================
    "aaai": _cfg(
        "AAAI",
        ("aaai", "national conference on artificial intelligence", "aaai conference on artificial intelligence"),
        rank=VenueRank.A_STAR,
        is_oa=True,
        archive_kind="aaai",
        openalex_source_ids=("S4210191458",),
        landing_url_pattern=r"ojs\.aaai\.org/",
        typical_arxiv_coverage=0.85,
    ),
    "ijcai": _cfg(
        "IJCAI",
        ("ijcai", "international joint conference on artificial intelligence"),
        rank=VenueRank.A_STAR,
        is_oa=True,
        archive_kind="ijcai",
        openalex_source_ids=("S4306419999",),
        landing_url_pattern=r"ijcai\.org/proceedings",
        typical_arxiv_coverage=0.75,
    ),

    # ===================== Data / DB =====================
    "sigmod": _cfg(
        "SIGMOD",
        ("sigmod", "international conference on management of data", "management of data"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="acm_dl",
        openalex_source_ids=("S4306419648",),
        landing_url_pattern=r"dl\.acm\.org/doi",
        typical_arxiv_coverage=0.40,
    ),
    "vldb": _cfg(
        "VLDB",
        ("vldb", "very large data bases", "pvldb", "proceedings of the vldb endowment"),
        rank=VenueRank.A_STAR,
        # PVLDB is OA; VLDB proceedings themselves are mostly paywalled in ACM DL.
        is_oa=True,
        archive_kind="vldb",
        openalex_source_ids=("S4306421142", "S4210226185"),  # primary + PVLDB journal
        landing_url_pattern=r"vldb\.org/(?:pvldb/volumes/|db/conf/vldb/)|dl\.acm\.org/doi",
        typical_arxiv_coverage=0.50,
    ),
    "kdd": _cfg(
        "KDD",
        ("kdd", "sigkdd", "knowledge discovery and data mining"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="acm_dl",
        openalex_source_ids=("S4393918197",),  # 0 works but canonical entry
        landing_url_pattern=r"dl\.acm\.org/doi",
        typical_arxiv_coverage=0.70,
    ),
    "icde": _cfg(
        "ICDE",
        ("icde", "international conference on data engineering"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="ieee",
        openalex_source_ids=("S4363607857",),
        landing_url_pattern=r"ieeexplore\.ieee\.org/document",
        typical_arxiv_coverage=0.45,
    ),

    # ===================== Networks =====================
    "sigcomm": _cfg(
        "SIGCOMM",
        ("sigcomm", "special interest group on data communication", "data communication"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="acm_dl",
        # Run 1 picked ACM SIGCOMM Computer Communication Review (journal); too broad.
        # Leave empty so venue-targeted search falls back; we don't want to filter on a journal.
        openalex_source_ids=(),
        landing_url_pattern=r"dl\.acm\.org/doi",
        typical_arxiv_coverage=0.50,
    ),

    # ===================== Security =====================
    "ccs": _cfg(
        "ACM CCS",
        ("ccs", "computer and communications security", "acm ccs", "computer and communication security"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="acm_dl",
        openalex_source_ids=("S4306417956",),
        landing_url_pattern=r"dl\.acm\.org/doi",
        typical_arxiv_coverage=0.55,
    ),
    "sp": _cfg(
        "IEEE S&P",
        ("ieee symposium on security and privacy", "s&p", "ieee security and privacy", "ieee s&p"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="ieee",
        openalex_source_ids=("S4306418833",),
        landing_url_pattern=r"ieeexplore\.ieee\.org/document",
        typical_arxiv_coverage=0.50,
    ),
    "crypto": _cfg(
        "CRYPTO",
        ("crypto", "international cryptology conference", "annual international cryptology conference"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="springer",
        openalex_source_ids=("S4306419976",),
        landing_url_pattern=r"link\.springer\.com/(?:chapter|article)",
        typical_arxiv_coverage=0.95,  # crypto is heavily on eprint (IACR)
    ),
    "eurocrypt": _cfg(
        "EUROCRYPT",
        ("eurocrypt", "theory and applications of cryptographic techniques"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="springer",
        openalex_source_ids=(),  # not captured in run 1
        landing_url_pattern=r"link\.springer\.com/(?:chapter|article)",
        typical_arxiv_coverage=0.95,
    ),

    # ===================== Software engineering / systems =====================
    "icse": _cfg(
        "ICSE",
        ("icse", "international conference on software engineering"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="acm_dl",
        openalex_source_ids=("S4306419842",),
        landing_url_pattern=r"dl\.acm\.org/doi",
        typical_arxiv_coverage=0.30,
    ),
    "osdi": _cfg(
        "OSDI",
        ("osdi", "operating systems design and implementation", "usenix symposium on operating systems design"),
        rank=VenueRank.A_STAR,
        is_oa=True,                     # USENIX is OA
        archive_kind="usenix",
        openalex_source_ids=(),         # OpenAlex does not have a clean OSDI source
        landing_url_pattern=r"usenix\.org/(?:conference|system/files)",
        typical_arxiv_coverage=0.30,
    ),
    "sosp": _cfg(
        "SOSP",
        ("sosp", "symposium on operating systems principles", "operating systems principles"),
        rank=VenueRank.A_STAR,
        is_oa=True,                     # ACM Open Access for SOSP since 2017
        archive_kind="acm_dl",
        openalex_source_ids=(),
        landing_url_pattern=r"dl\.acm\.org/doi",
        typical_arxiv_coverage=0.30,
    ),
    "nsdi": _cfg(
        "NSDI",
        ("nsdi", "networked systems design and implementation", "usenix symposium on networked systems"),
        rank=VenueRank.A_STAR,
        is_oa=True,
        archive_kind="usenix",
        openalex_source_ids=(),
        landing_url_pattern=r"usenix\.org/(?:conference|system/files)",
        typical_arxiv_coverage=0.30,
    ),
    "usenix_atc": _cfg(
        "USENIX ATC",
        ("usenix atc", "usenix annual technical", "annual technical conference"),
        rank=VenueRank.A,
        is_oa=True,
        archive_kind="usenix",
        openalex_source_ids=(),
        landing_url_pattern=r"usenix\.org/(?:conference|system/files)",
        typical_arxiv_coverage=0.30,
    ),
    "usenix_sec": _cfg(
        "USENIX Security",
        ("usenix security", "usenix security symposium", "usenix security symposium"),
        rank=VenueRank.A_STAR,
        is_oa=True,
        archive_kind="usenix",
        openalex_source_ids=(),
        landing_url_pattern=r"usenix\.org/(?:conference|system/files)",
        typical_arxiv_coverage=0.45,
    ),

    # ===================== Theory =====================
    "stoc": _cfg(
        "STOC",
        ("stoc", "symposium on theory of computing", "theory of computing"),
        rank=VenueRank.A_STAR,
        is_oa=False,                    # mostly ACM DL paywalled, some OA
        archive_kind="acm_dl",
        openalex_source_ids=(),         # not captured
        landing_url_pattern=r"dl\.acm\.org/doi",
        typical_arxiv_coverage=0.55,
    ),
    "focs": _cfg(
        "FOCS",
        ("focs", "foundations of computer science", "ieee annual symposium on foundations of computer science"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="ieee",
        openalex_source_ids=("S4306418447",),
        landing_url_pattern=r"ieeexplore\.ieee\.org/document",
        typical_arxiv_coverage=0.85,
    ),
    "soda": _cfg(
        "SODA",
        ("soda", "symposium on discrete algorithms", "acm-siam symposium on discrete algorithms"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="acm_dl",
        openalex_source_ids=("S4363608732",),
        landing_url_pattern=r"dl\.acm\.org/doi",
        typical_arxiv_coverage=0.55,
    ),

    # ===================== Graphics / Web =====================
    "siggraph": _cfg(
        "SIGGRAPH",
        ("siggraph", "international conference on computer graphics and interactive techniques"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="acm_dl",
        openalex_source_ids=("S4306419250",),
        landing_url_pattern=r"dl\.acm\.org/doi",
        typical_arxiv_coverage=0.30,
    ),
    "www": _cfg(
        "WWW",
        ("www", "the web conference", "world wide web conference", "international world wide web"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="acm_dl",
        openalex_source_ids=("S4306421067",),
        landing_url_pattern=r"dl\.acm\.org/doi",
        typical_arxiv_coverage=0.50,
    ),

    # ===================== Journals (CCF A) =====================
    "tpami": _cfg(
        "TPAMI",
        ("tpami", "ieee transactions on pattern analysis and machine intelligence"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="ieee",
        openalex_source_ids=("S199944782",),
        landing_url_pattern=r"ieeexplore\.ieee\.org/document",
        typical_arxiv_coverage=0.70,
    ),
    "ijcv": _cfg(
        "IJCV",
        ("ijcv", "international journal of computer vision"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="springer",
        openalex_source_ids=("S25538012",),
        landing_url_pattern=r"link\.springer\.com/article",
        typical_arxiv_coverage=0.65,
    ),
    "jmlr": _cfg(
        "JMLR",
        ("jmlr", "journal of machine learning research"),
        rank=VenueRank.A_STAR,
        is_oa=True,
        archive_kind="jmlr",
        openalex_source_ids=("S118988714",),
        landing_url_pattern=r"jmlr\.org/papers",
        typical_arxiv_coverage=0.85,
    ),
    "tmlr": _cfg(
        "TMLR",
        ("tmlr", "transactions on machine learning research"),
        rank=VenueRank.A,
        is_oa=True,
        archive_kind="openreview",
        openalex_source_ids=(),
        landing_url_pattern=r"openreview\.net/(?:forum|pdf)",
        typical_arxiv_coverage=0.95,
    ),
    "aij": _cfg(
        "Artificial Intelligence",
        ("artificial intelligence", "artificial intelligence journal", "aij"),
        rank=VenueRank.A_STAR,
        is_oa=False,                    # Elsevier paywalled mostly
        archive_kind="other",
        openalex_source_ids=("S196139623",),
        landing_url_pattern=r"sciencedirect\.com/science/article",
        typical_arxiv_coverage=0.40,
    ),
    "tit": _cfg(
        "IEEE TIT",
        ("ieee transactions on information theory", "ieee tit", "information theory"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="ieee",
        openalex_source_ids=("S4502562",),
        landing_url_pattern=r"ieeexplore\.ieee\.org/document",
        typical_arxiv_coverage=0.70,    # arxiv is very common for info theory
    ),
    "tocs": _cfg(
        "ACM TOCS",
        ("acm transactions on computer systems", "tocs"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="acm_dl",
        openalex_source_ids=("S193109227",),
        landing_url_pattern=r"dl\.acm\.org/doi",
        typical_arxiv_coverage=0.40,
    ),
    "dcc": _cfg(
        "DCC",
        ("data compression conference", "dcc"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="ieee",
        openalex_source_ids=("S4306418158",),
        landing_url_pattern=r"ieeexplore\.ieee\.org/document",
        typical_arxiv_coverage=0.30,
    ),
    "tag": _cfg(
        "ACM TAG",
        ("acm transactions on graphics", "transactions on graphics"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="acm_dl",
        openalex_source_ids=("S185367456",),
        landing_url_pattern=r"dl\.acm\.org/doi",
        typical_arxiv_coverage=0.30,
    ),

    # ===================== ML workshops and B-class venues useful to cover =====================
    "aistats": _cfg(
        "AISTATS",
        ("aistats", "artificial intelligence and statistics"),
        rank=VenueRank.A,
        is_oa=True,                     # PMLR is OA
        archive_kind="pmr",
        openalex_source_ids=(),
        landing_url_pattern=r"proceedings\.mlr\.press/v",
        typical_arxiv_coverage=0.85,
    ),
    "colt": _cfg(
        "COLT",
        ("colt", "conference on learning theory", "computational learning theory"),
        rank=VenueRank.A,
        is_oa=True,                     # PMLR is OA
        archive_kind="pmr",
        openalex_source_ids=(),
        landing_url_pattern=r"proceedings\.mlr\.press/v",
        typical_arxiv_coverage=0.85,
    ),
    "uai": _cfg(
        "UAI",
        ("uai", "uncertainty in artificial intelligence"),
        rank=VenueRank.A,
        is_oa=True,                     # PMLR-hosted recent years
        archive_kind="pmr",
        openalex_source_ids=(),
        landing_url_pattern=r"proceedings\.mlr\.press/v|auai\.org/uai",
        typical_arxiv_coverage=0.80,
    ),
    "ecml": _cfg(
        "ECML PKDD",
        ("ecml", "european conference on machine learning", "ecml pkdd"),
        rank=VenueRank.B,
        is_oa=False,                    # Springer LNCS paywalled; some Springer OA chapters
        archive_kind="springer",
        openalex_source_ids=(),
        landing_url_pattern=r"link\.springer\.com/(?:chapter|article)",
        typical_arxiv_coverage=0.50,
    ),
    "mm": _cfg(
        "ACM MM",
        ("acm multimedia", "acm mm", "multimedia conference"),
        rank=VenueRank.A,
        is_oa=False,
        archive_kind="acm_dl",
        openalex_source_ids=(),
        landing_url_pattern=r"dl\.acm\.org/doi",
        typical_arxiv_coverage=0.40,
    ),
    "miccai": _cfg(
        "MICCAI",
        ("miccai", "medical image computing and computer assisted intervention"),
        rank=VenueRank.A,
        is_oa=False,                    # Springer LNCS paywalled
        archive_kind="springer",
        openalex_source_ids=(),
        landing_url_pattern=r"link\.springer\.com/(?:chapter|article)",
        typical_arxiv_coverage=0.50,
    ),

    # ===================== 2026 CCF A coverage extensions =====================
    "ppopp": _cfg(
        "PPoPP",
        ("ppopp", "principles & practice of parallel programming", "principles and practice of parallel programming"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="acm_dl",
        landing_url_pattern=r"dl\.acm\.org/doi",
        typical_arxiv_coverage=0.35,
    ),
    "fast": _cfg(
        "FAST",
        ("fast", "file and storage technologies", "usenix conference on file and storage technologies"),
        rank=VenueRank.A_STAR,
        is_oa=True,
        archive_kind="usenix",
        landing_url_pattern=r"usenix\.org/(?:conference|system/files)",
        typical_arxiv_coverage=0.25,
    ),
    "dac": _cfg(
        "DAC",
        ("dac", "design automation conference"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="acm_dl",
        landing_url_pattern=r"dl\.acm\.org/doi|ieeexplore\.ieee\.org/document",
        typical_arxiv_coverage=0.25,
    ),
    "hpca": _cfg(
        "HPCA",
        ("hpca", "high performance computer architecture"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="ieee",
        landing_url_pattern=r"ieeexplore\.ieee\.org/document|computer\.org/csdl",
        typical_arxiv_coverage=0.35,
    ),
    "micro": _cfg(
        "MICRO",
        ("micro", "international symposium on microarchitecture"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="acm_dl",
        landing_url_pattern=r"dl\.acm\.org/doi|ieeexplore\.ieee\.org/document|computer\.org/csdl",
        typical_arxiv_coverage=0.35,
    ),
    "sc": _cfg(
        "SC",
        ("sc", "supercomputing", "international conference for high performance computing"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="acm_dl",
        landing_url_pattern=r"dl\.acm\.org/doi|ieeexplore\.ieee\.org/document",
        typical_arxiv_coverage=0.30,
    ),
    "asplos": _cfg(
        "ASPLOS",
        ("asplos", "architectural support for programming languages and operating systems"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="acm_dl",
        landing_url_pattern=r"dl\.acm\.org/doi",
        typical_arxiv_coverage=0.40,
    ),
    "isca": _cfg(
        "ISCA",
        ("isca", "international symposium on computer architecture"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="acm_dl",
        landing_url_pattern=r"dl\.acm\.org/doi|ieeexplore\.ieee\.org/document|computer\.org/csdl",
        typical_arxiv_coverage=0.40,
    ),
    "acm_sigops_atc": _cfg(
        "ACM SIGOPS ATC",
        ("acm sigops atc", "acm sigops annual technical conference"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="acm_dl",
        landing_url_pattern=r"dl\.acm\.org/doi",
        typical_arxiv_coverage=0.30,
    ),
    "eurosys": _cfg(
        "EuroSys",
        ("eurosys", "european conference on computer systems"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="acm_dl",
        landing_url_pattern=r"dl\.acm\.org/doi",
        typical_arxiv_coverage=0.35,
    ),
    "hpdc": _cfg(
        "HPDC",
        ("hpdc", "high-performance parallel and distributed computing"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="acm_dl",
        landing_url_pattern=r"dl\.acm\.org/doi",
        typical_arxiv_coverage=0.35,
    ),
    "mobicom": _cfg(
        "MobiCom",
        ("mobicom", "mobile computing and networking"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="acm_dl",
        landing_url_pattern=r"dl\.acm\.org/doi",
        typical_arxiv_coverage=0.40,
    ),
    "infocom": _cfg(
        "INFOCOM",
        ("infocom", "ieee international conference on computer communications"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="ieee",
        landing_url_pattern=r"ieeexplore\.ieee\.org/document|computer\.org/csdl",
        typical_arxiv_coverage=0.35,
    ),
    "ndss": _cfg(
        "NDSS",
        ("ndss", "network and distributed system security symposium"),
        rank=VenueRank.A_STAR,
        is_oa=True,
        archive_kind="other",
        landing_url_pattern=r"ndss-symposium\.org/(?:ndss-paper|wp-content/uploads|ndss\d+)",
        typical_arxiv_coverage=0.55,
    ),
    "pldi": _cfg(
        "PLDI",
        ("pldi", "programming language design and implementation"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="acm_dl",
        landing_url_pattern=r"dl\.acm\.org/doi",
        typical_arxiv_coverage=0.40,
    ),
    "popl": _cfg(
        "POPL",
        ("popl", "principles of programming languages"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="acm_dl",
        landing_url_pattern=r"dl\.acm\.org/doi",
        typical_arxiv_coverage=0.40,
    ),
    "fse": _cfg(
        "FSE",
        ("fse", "foundations of software engineering", "foundation of software engineering"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="acm_dl",
        landing_url_pattern=r"dl\.acm\.org/doi",
        typical_arxiv_coverage=0.30,
    ),
    "oopsla": _cfg(
        "OOPSLA",
        ("oopsla", "object-oriented programming systems", "object oriented programming systems"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="acm_dl",
        landing_url_pattern=r"dl\.acm\.org/doi",
        typical_arxiv_coverage=0.35,
    ),
    "ase": _cfg(
        "ASE",
        ("ase", "automated software engineering"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="acm_dl",
        landing_url_pattern=r"dl\.acm\.org/doi|ieeexplore\.ieee\.org/document",
        typical_arxiv_coverage=0.30,
    ),
    "issta": _cfg(
        "ISSTA",
        ("issta", "software testing and analysis"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="acm_dl",
        landing_url_pattern=r"dl\.acm\.org/doi",
        typical_arxiv_coverage=0.35,
    ),
    "fm": _cfg(
        "FM",
        ("formal methods", "international symposium on formal methods"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="springer",
        landing_url_pattern=r"link\.springer\.com/(?:chapter|article)",
        typical_arxiv_coverage=0.45,
    ),
    "sigir": _cfg(
        "SIGIR",
        ("sigir", "research and development in information retrieval"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="acm_dl",
        landing_url_pattern=r"dl\.acm\.org/doi",
        typical_arxiv_coverage=0.45,
    ),
    "cav": _cfg(
        "CAV",
        ("cav", "computer aided verification"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="springer",
        landing_url_pattern=r"link\.springer\.com/(?:chapter|article)",
        typical_arxiv_coverage=0.70,
    ),
    "lics": _cfg(
        "LICS",
        ("lics", "logic in computer science"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="acm_dl",
        landing_url_pattern=r"dl\.acm\.org/doi|ieeexplore\.ieee\.org/document",
        typical_arxiv_coverage=0.65,
    ),
    "vr": _cfg(
        "IEEE VR",
        ("ieee vr", "virtual reality and 3d user interfaces"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="ieee",
        landing_url_pattern=r"ieeexplore\.ieee\.org/document|computer\.org/csdl",
        typical_arxiv_coverage=0.35,
    ),
    "ieee_vis": _cfg(
        "IEEE VIS",
        ("ieee vis", "ieee visualization conference"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="ieee",
        landing_url_pattern=r"ieeexplore\.ieee\.org/document|computer\.org/csdl",
        typical_arxiv_coverage=0.35,
    ),
    "cscw": _cfg(
        "CSCW",
        ("cscw", "computer supported cooperative work and social computing"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="acm_dl",
        landing_url_pattern=r"dl\.acm\.org/doi",
        typical_arxiv_coverage=0.30,
    ),
    "chi": _cfg(
        "CHI",
        ("chi", "human factors in computing systems"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="acm_dl",
        landing_url_pattern=r"dl\.acm\.org/doi",
        typical_arxiv_coverage=0.30,
    ),
    "ubicomp": _cfg(
        "UbiComp",
        ("ubicomp", "pervasive and ubiquitous computing"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="acm_dl",
        landing_url_pattern=r"dl\.acm\.org/doi",
        typical_arxiv_coverage=0.30,
    ),
    "uist": _cfg(
        "UIST",
        ("uist", "user interface software and technology"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="acm_dl",
        landing_url_pattern=r"dl\.acm\.org/doi",
        typical_arxiv_coverage=0.30,
    ),
    "rtss": _cfg(
        "RTSS",
        ("rtss", "real-time systems symposium", "real time systems symposium"),
        rank=VenueRank.A_STAR,
        is_oa=False,
        archive_kind="ieee",
        landing_url_pattern=r"ieeexplore\.ieee\.org/document|computer\.org/csdl",
        typical_arxiv_coverage=0.25,
    ),

    # ===================== 2026 CCF A journal coverage extensions =====================
    "tos": _cfg("ACM TOS", ("tos", "acm transactions on storage"), rank=VenueRank.A_STAR, is_oa=False, archive_kind="acm_dl", landing_url_pattern=r"dl\.acm\.org/doi", typical_arxiv_coverage=0.35),
    "tcad": _cfg("IEEE TCAD", ("tcad", "computer-aided design of integrated circuits and systems", "computer aided design of integrated circuits and systems"), rank=VenueRank.A_STAR, is_oa=False, archive_kind="ieee", landing_url_pattern=r"ieeexplore\.ieee\.org/document", typical_arxiv_coverage=0.30),
    "tc": _cfg("IEEE TC", ("ieee transactions on computers",), rank=VenueRank.A_STAR, is_oa=False, archive_kind="ieee", landing_url_pattern=r"ieeexplore\.ieee\.org/document", typical_arxiv_coverage=0.35),
    "tpds": _cfg("IEEE TPDS", ("tpds", "transactions on parallel and distributed systems"), rank=VenueRank.A_STAR, is_oa=False, archive_kind="ieee", landing_url_pattern=r"ieeexplore\.ieee\.org/document", typical_arxiv_coverage=0.35),
    "taco": _cfg("ACM TACO", ("taco", "transactions on architecture and code optimization"), rank=VenueRank.A_STAR, is_oa=False, archive_kind="acm_dl", landing_url_pattern=r"dl\.acm\.org/doi", typical_arxiv_coverage=0.35),
    "jsac": _cfg("IEEE JSAC", ("jsac", "journal on selected areas in communications"), rank=VenueRank.A_STAR, is_oa=False, archive_kind="ieee", landing_url_pattern=r"ieeexplore\.ieee\.org/document", typical_arxiv_coverage=0.30),
    "tmc": _cfg("IEEE TMC", ("tmc", "transactions on mobile computing"), rank=VenueRank.A_STAR, is_oa=False, archive_kind="ieee", landing_url_pattern=r"ieeexplore\.ieee\.org/document", typical_arxiv_coverage=0.35),
    "ton": _cfg("IEEE/ACM TON", ("ton", "transactions on networking"), rank=VenueRank.A_STAR, is_oa=False, archive_kind="ieee", landing_url_pattern=r"ieeexplore\.ieee\.org/document|dl\.acm\.org/doi", typical_arxiv_coverage=0.35),
    "tdsc": _cfg("IEEE TDSC", ("tdsc", "transactions on dependable and secure computing"), rank=VenueRank.A_STAR, is_oa=False, archive_kind="ieee", landing_url_pattern=r"ieeexplore\.ieee\.org/document", typical_arxiv_coverage=0.35),
    "tifs": _cfg("IEEE TIFS", ("tifs", "transactions on information forensics and security"), rank=VenueRank.A_STAR, is_oa=False, archive_kind="ieee", landing_url_pattern=r"ieeexplore\.ieee\.org/document", typical_arxiv_coverage=0.35),
    "joc": _cfg("Journal of Cryptology", ("journal of cryptology",), rank=VenueRank.A_STAR, is_oa=False, archive_kind="springer", landing_url_pattern=r"link\.springer\.com/article", typical_arxiv_coverage=0.85),
    "toplas": _cfg("ACM TOPLAS", ("toplas", "transactions on programming languages and systems"), rank=VenueRank.A_STAR, is_oa=False, archive_kind="acm_dl", landing_url_pattern=r"dl\.acm\.org/doi", typical_arxiv_coverage=0.35),
    "tosem": _cfg("ACM TOSEM", ("tosem", "transactions on software engineering and methodology"), rank=VenueRank.A_STAR, is_oa=False, archive_kind="acm_dl", landing_url_pattern=r"dl\.acm\.org/doi", typical_arxiv_coverage=0.30),
    "tse": _cfg("IEEE TSE", ("tse", "transactions on software engineering"), rank=VenueRank.A_STAR, is_oa=False, archive_kind="ieee", landing_url_pattern=r"ieeexplore\.ieee\.org/document", typical_arxiv_coverage=0.35),
    "tsc": _cfg("IEEE TSC", ("tsc", "transactions on services computing"), rank=VenueRank.A_STAR, is_oa=False, archive_kind="ieee", landing_url_pattern=r"ieeexplore\.ieee\.org/document", typical_arxiv_coverage=0.30),
    "tods": _cfg("ACM TODS", ("tods", "transactions on database systems"), rank=VenueRank.A_STAR, is_oa=False, archive_kind="acm_dl", landing_url_pattern=r"dl\.acm\.org/doi", typical_arxiv_coverage=0.35),
    "tois": _cfg("ACM TOIS", ("tois", "transactions on information systems"), rank=VenueRank.A_STAR, is_oa=False, archive_kind="acm_dl", landing_url_pattern=r"dl\.acm\.org/doi", typical_arxiv_coverage=0.40),
    "tkde": _cfg("IEEE TKDE", ("tkde", "transactions on knowledge and data engineering"), rank=VenueRank.A_STAR, is_oa=False, archive_kind="ieee", landing_url_pattern=r"ieeexplore\.ieee\.org/document", typical_arxiv_coverage=0.45),
    "vldbj": _cfg("VLDBJ", ("vldbj", "the vldb journal"), rank=VenueRank.A_STAR, is_oa=False, archive_kind="springer", landing_url_pattern=r"link\.springer\.com/article", typical_arxiv_coverage=0.40),
    "iandc": _cfg("Information and Computation", ("iandc", "information and computation"), rank=VenueRank.A_STAR, is_oa=False, archive_kind="other", landing_url_pattern=r"sciencedirect\.com/science/article", typical_arxiv_coverage=0.45),
    "sicomp": _cfg("SIAM Journal on Computing", ("sicomp", "siam journal on computing"), rank=VenueRank.A_STAR, is_oa=False, archive_kind="other", landing_url_pattern=r"epubs\.siam\.org/doi", typical_arxiv_coverage=0.60),
    "tog": _cfg("ACM TOG", ("tog", "acm transactions on graphics"), rank=VenueRank.A_STAR, is_oa=False, archive_kind="acm_dl", landing_url_pattern=r"dl\.acm\.org/doi", typical_arxiv_coverage=0.30),
    "tip": _cfg("IEEE TIP", ("tip", "transactions on image processing"), rank=VenueRank.A_STAR, is_oa=False, archive_kind="ieee", landing_url_pattern=r"ieeexplore\.ieee\.org/document", typical_arxiv_coverage=0.45),
    "tvcg": _cfg("IEEE TVCG", ("tvcg", "transactions on visualization and computer graphics"), rank=VenueRank.A_STAR, is_oa=False, archive_kind="ieee", landing_url_pattern=r"ieeexplore\.ieee\.org/document", typical_arxiv_coverage=0.35),
    "tmm": _cfg("IEEE TMM", ("tmm", "transactions on multimedia"), rank=VenueRank.A_STAR, is_oa=False, archive_kind="ieee", landing_url_pattern=r"ieeexplore\.ieee\.org/document", typical_arxiv_coverage=0.40),
    "tochi": _cfg("ACM TOCHI", ("tochi", "transactions on computer-human interaction"), rank=VenueRank.A_STAR, is_oa=False, archive_kind="acm_dl", landing_url_pattern=r"dl\.acm\.org/doi", typical_arxiv_coverage=0.25),
    "ijhcs": _cfg("IJHCS", ("ijhcs", "international journal of human-computer studies", "international journal of human computer studies"), rank=VenueRank.A_STAR, is_oa=False, archive_kind="other", landing_url_pattern=r"sciencedirect\.com/science/article", typical_arxiv_coverage=0.25),
    "jacm": _cfg("JACM", ("jacm", "journal of the acm"), rank=VenueRank.A_STAR, is_oa=False, archive_kind="acm_dl", landing_url_pattern=r"dl\.acm\.org/doi", typical_arxiv_coverage=0.45),
    "proc_ieee": _cfg("Proceedings of the IEEE", ("proceedings of the ieee",), rank=VenueRank.A_STAR, is_oa=False, archive_kind="ieee", landing_url_pattern=r"ieeexplore\.ieee\.org/document", typical_arxiv_coverage=0.35),
    "scis": _cfg("SCIS", ("scis", "science china information sciences"), rank=VenueRank.A_STAR, is_oa=False, archive_kind="springer", landing_url_pattern=r"link\.springer\.com/article", typical_arxiv_coverage=0.35),
    "bioinformatics": _cfg("Bioinformatics", ("bioinformatics",), rank=VenueRank.A_STAR, is_oa=False, archive_kind="other", landing_url_pattern=r"academic\.oup\.com/bioinformatics", typical_arxiv_coverage=0.35),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def lookup_venue(venue_str: str) -> VenueConfig | None:
    """Fuzzy-match a venue string against VENUE_REGISTRY. Returns None on miss.

    Matching: case-insensitive substring check on each alias. First match wins.
    Order is deterministic because VENUE_REGISTRY is a dict (insertion-ordered).
    """
    if not venue_str:
        return None
    lower = venue_str.lower()
    for cfg in VENUE_REGISTRY.values():
        if any(_alias_matches(lower, alias) for alias in cfg.aliases):
            return cfg
    return None


def _alias_matches(venue_lower: str, alias: str) -> bool:
    if not alias:
        return False
    if len(alias) <= 4 or re.fullmatch(r"[a-z0-9&.+ -]+", alias):
        return re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", venue_lower) is not None
    return alias in venue_lower


def lookup_venue_by_canonical_name(canonical: str) -> VenueConfig | None:
    """Lookup by canonical_name (case-insensitive)."""
    if not canonical:
        return None
    target = canonical.strip().lower()
    for key, cfg in VENUE_REGISTRY.items():
        if key == target or cfg.canonical_name.lower() == target:
            return cfg
    return None


def is_known_oa_landing(url: str) -> tuple[bool, str, VenueConfig | None]:
    """Return (is_oa, archive_kind, venue_cfg) for a URL by matching it against
    known OA venue landing patterns.

    archive_kind will be "" if the URL doesn't match a known OA venue.
    """
    if not url:
        return False, "", None
    url_lower = url.lower()
    for key, cfg in VENUE_REGISTRY.items():
        if cfg.landing_url_pattern is None:
            continue
        if cfg.landing_url_pattern.search(url_lower):
            if cfg.is_oa:
                return True, cfg.archive_kind, cfg
            # URL matched a paywalled venue (e.g., IEEE/Springer).
            return False, cfg.archive_kind, cfg
    return False, "", None


def all_openalex_source_ids() -> dict[str, tuple[str, ...]]:
    """Return {venue_key: (openalex_source_id, ...)} for venues that have IDs.

    Useful for venue-targeted search: a venue key maps to one or more OpenAlex
    source IDs, and the search adapter OR-filters on them.
    """
    return {key: cfg.openalex_source_ids for key, cfg in VENUE_REGISTRY.items() if cfg.openalex_source_ids}


def venue_rank(venue_str: str) -> VenueRank:
    """Resolve venue rank from a venue string. Returns UNRANKED on miss."""
    cfg = lookup_venue(venue_str)
    return cfg.rank if cfg else VenueRank.UNRANKED


__all__ = [
    "ARCHIVE_KINDS",
    "VenueConfig",
    "VENUE_REGISTRY",
    "lookup_venue",
    "lookup_venue_by_canonical_name",
    "is_known_oa_landing",
    "all_openalex_source_ids",
    "venue_rank",
]
