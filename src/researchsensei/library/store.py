from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from researchsensei.schemas import CandidatePaper, ResolvedPaperSource
from researchsensei.schemas.enums import VenueRank


@dataclass(frozen=True)
class PaperLibraryRecord:
    paper_id: str
    title: str
    normalized_title: str
    authors: list[str]
    year: int | None
    venue: str
    venue_canonical_name: str
    venue_rank: str
    doi: str
    arxiv_id: str
    pdf_url: str
    landing_url: str
    local_path: str
    sha256: str
    file_size: int
    downloaded_at: str
    first_seen_at: str
    last_seen_at: str
    deleted_at: str

    def to_dict(self) -> dict[str, object]:
        return {
            "paper_id": self.paper_id,
            "title": self.title,
            "normalized_title": self.normalized_title,
            "authors": self.authors,
            "year": self.year,
            "venue": self.venue,
            "venue_canonical_name": self.venue_canonical_name,
            "venue_rank": self.venue_rank,
            "doi": self.doi,
            "arxiv_id": self.arxiv_id,
            "pdf_url": self.pdf_url,
            "landing_url": self.landing_url,
            "local_path": self.local_path,
            "sha256": self.sha256,
            "file_size": self.file_size,
            "downloaded_at": self.downloaded_at,
            "first_seen_at": self.first_seen_at,
            "last_seen_at": self.last_seen_at,
            "deleted_at": self.deleted_at,
        }


class PaperLibraryStore:
    """SQLite-backed local paper library for M1 search/download reuse."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def find_match(self, candidate: CandidatePaper) -> PaperLibraryRecord | None:
        doi = _normalize_doi(candidate.doi)
        arxiv_id = _normalize_arxiv(candidate.arxiv_id)
        title = _normalize_title(candidate.normalized_title or candidate.title)
        urls = [url for url in (candidate.pdf_url, candidate.landing_url, candidate.url, candidate.source_url) if url]
        with self._connect() as conn:
            row = None
            if doi:
                row = conn.execute(
                    "select * from papers where doi = ? and deleted_at = '' order by last_seen_at desc limit 1",
                    (doi,),
                ).fetchone()
            if row is None and arxiv_id:
                row = conn.execute(
                    "select * from papers where arxiv_id = ? and deleted_at = '' order by last_seen_at desc limit 1",
                    (arxiv_id,),
                ).fetchone()
            if row is None and title:
                row = conn.execute(
                    "select * from papers where normalized_title = ? and deleted_at = '' order by last_seen_at desc limit 1",
                    (title,),
                ).fetchone()
            if row is None and urls:
                row = conn.execute(
                    """
                    select p.*
                    from papers p
                    join paper_sources s on s.paper_id = p.paper_id
                    where s.url in ({}) and p.deleted_at = ''
                    order by p.last_seen_at desc
                    limit 1
                    """.format(",".join("?" for _ in urls)),
                    tuple(urls),
                ).fetchone()
        if row is None:
            return None
        record = _record_from_row(row)
        if not record.local_path or not Path(record.local_path).exists():
            return None
        return record

    def upsert_download(
        self,
        candidate: CandidatePaper,
        item: ResolvedPaperSource,
        *,
        seen_at: str | None = None,
    ) -> PaperLibraryRecord | None:
        local_path = str(item.local_path or "").strip()
        if not local_path or not item.has_valid_deep_reading_source:
            return None
        path = Path(local_path)
        if not path.exists() or not path.is_file():
            return None

        now = seen_at or _now()
        content = path.read_bytes()
        sha256 = item.sha256 or hashlib.sha256(content).hexdigest()
        file_size = item.file_size or path.stat().st_size
        doi = _normalize_doi(candidate.doi or item.doi)
        arxiv_id = _normalize_arxiv(candidate.arxiv_id or item.arxiv_id)
        normalized_title = _normalize_title(candidate.normalized_title or candidate.title or item.title)
        paper_id = self._existing_paper_id(doi=doi, arxiv_id=arxiv_id, normalized_title=normalized_title, sha256=sha256)
        if not paper_id:
            paper_id = _library_id(doi=doi, arxiv_id=arxiv_id, normalized_title=normalized_title, fallback=item.paper_id or candidate.paper_id)

        title = candidate.title or item.title
        authors = candidate.authors
        year = candidate.year
        venue_rank = _venue_rank_value(candidate.venue_rank)
        pdf_url = item.pdf_url or candidate.pdf_url
        landing_url = item.landing_url or candidate.landing_url or candidate.url
        source_url = item.source_url or candidate.source_url or pdf_url or landing_url

        with self._connect() as conn:
            existing = conn.execute("select first_seen_at from papers where paper_id = ?", (paper_id,)).fetchone()
            first_seen_at = existing["first_seen_at"] if existing is not None else now
            conn.execute(
                """
                insert into papers(
                    paper_id, title, normalized_title, authors, year, venue, venue_canonical_name, venue_rank,
                    doi, arxiv_id, pdf_url, landing_url, local_path, sha256, file_size,
                    downloaded_at, first_seen_at, last_seen_at, deleted_at
                )
                values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'')
                on conflict(paper_id) do update set
                    title=excluded.title,
                    normalized_title=excluded.normalized_title,
                    authors=excluded.authors,
                    year=excluded.year,
                    venue=excluded.venue,
                    venue_canonical_name=excluded.venue_canonical_name,
                    venue_rank=excluded.venue_rank,
                    doi=excluded.doi,
                    arxiv_id=excluded.arxiv_id,
                    pdf_url=excluded.pdf_url,
                    landing_url=excluded.landing_url,
                    local_path=excluded.local_path,
                    sha256=excluded.sha256,
                    file_size=excluded.file_size,
                    downloaded_at=excluded.downloaded_at,
                    last_seen_at=excluded.last_seen_at,
                    deleted_at=''
                """,
                (
                    paper_id,
                    title,
                    normalized_title,
                    json.dumps(authors, ensure_ascii=False),
                    year,
                    candidate.venue,
                    candidate.venue_canonical_name,
                    venue_rank,
                    doi,
                    arxiv_id,
                    pdf_url,
                    landing_url,
                    str(path.resolve()),
                    sha256,
                    file_size,
                    now,
                    first_seen_at,
                    now,
                ),
            )
            self._upsert_source_rows(conn, paper_id, candidate, item, source_url=source_url, seen_at=now)
            row = conn.execute("select * from papers where paper_id = ?", (paper_id,)).fetchone()
        return _record_from_row(row)

    def record_search(
        self,
        *,
        query: str,
        candidates: list[CandidatePaper],
        items: list[ResolvedPaperSource],
        topic_folder: str = "",
    ) -> dict[str, object]:
        now = _now()
        run_id = uuid.uuid4().hex
        by_paper_id = {item.paper_id: item for item in items}
        downloaded_count = 0
        reused_count = 0
        rows: list[tuple[str, str, str, int, str, str, int, str, str, str]] = []

        for fallback_rank, candidate in enumerate(candidates, start=1):
            rank = _search_rank(candidate, fallback=fallback_rank)
            item = by_paper_id.get(candidate.paper_id)
            action = "not_attempted"
            reason = candidate.download_reason
            record: PaperLibraryRecord | None = None
            if item is not None:
                strategy = item.metadata.get("resolution_strategy", "")
                if item.download_status == "downloaded" and item.has_valid_deep_reading_source:
                    record = self.upsert_download(candidate, item, seen_at=now)
                    action = "reused" if strategy in {"library_reuse", "existing_named_pdf", "reused_named_pdf"} else "downloaded"
                    if action == "reused":
                        reused_count += 1
                    else:
                        downloaded_count += 1
                elif item.download_status == "failed":
                    action = "failed"
                    reason = item.error or item.error_code or reason
                else:
                    action = item.download_status or "skipped"
                    reason = item.error or reason
            paper_id = record.paper_id if record else _library_id(
                doi=_normalize_doi(candidate.doi),
                arxiv_id=_normalize_arxiv(candidate.arxiv_id),
                normalized_title=_normalize_title(candidate.normalized_title or candidate.title),
                fallback=candidate.paper_id,
            )
            rows.append(
                (
                    run_id,
                    paper_id,
                    candidate.title,
                    rank,
                    action,
                    reason,
                    1 if candidate.download_selected else 0,
                    candidate.venue_canonical_name or candidate.venue,
                    _venue_rank_value(candidate.venue_rank),
                    record.local_path if record else (item.local_path if item is not None else ""),
                )
            )

        with self._connect() as conn:
            conn.execute(
                """
                insert into search_runs(run_id, query, topic_folder, created_at, candidate_count, downloaded_count, reused_count)
                values(?,?,?,?,?,?,?)
                """,
                (run_id, query, topic_folder, now, len(candidates), downloaded_count, reused_count),
            )
            conn.executemany(
                """
                insert or replace into search_run_papers(
                    run_id, paper_id, title, search_rank, action, reason, download_selected, venue, venue_rank, local_path
                )
                values(?,?,?,?,?,?,?,?,?,?)
                """,
                rows,
            )
        return {
            "run_id": run_id,
            "query": query,
            "candidate_count": len(candidates),
            "downloaded_count": downloaded_count,
            "reused_count": reused_count,
        }

    def list_papers(
        self,
        *,
        query: str = "",
        limit: int = 100,
        include_deleted: bool = False,
    ) -> list[dict[str, object]]:
        where = []
        args: list[object] = []
        if not include_deleted:
            where.append("deleted_at = ''")
        if query.strip():
            needle = f"%{query.strip().lower()}%"
            where.append("(lower(title) like ? or lower(venue) like ? or lower(venue_canonical_name) like ?)")
            args.extend([needle, needle, needle])
        sql = "select * from papers"
        if where:
            sql += " where " + " and ".join(where)
        sql += " order by last_seen_at desc limit ?"
        args.append(max(1, min(limit, 500)))
        with self._connect() as conn:
            rows = conn.execute(sql, tuple(args)).fetchall()
        return [_record_from_row(row).to_dict() for row in rows]

    def list_search_runs(self, *, limit: int = 50) -> list[dict[str, object]]:
        with self._connect() as conn:
            runs = conn.execute(
                """
                select * from search_runs
                order by created_at desc
                limit ?
                """,
                (max(1, min(limit, 200)),),
            ).fetchall()
            run_ids = [row["run_id"] for row in runs]
            paper_rows: list[sqlite3.Row] = []
            if run_ids:
                paper_rows = conn.execute(
                    """
                    select * from search_run_papers
                    where run_id in ({})
                    order by run_id, search_rank
                    """.format(",".join("?" for _ in run_ids)),
                    tuple(run_ids),
                ).fetchall()
        by_run: dict[str, list[dict[str, object]]] = {run_id: [] for run_id in run_ids}
        for row in paper_rows:
            by_run[row["run_id"]].append({
                "paper_id": row["paper_id"],
                "title": row["title"],
                "search_rank": row["search_rank"],
                "action": row["action"],
                "reason": row["reason"],
                "download_selected": bool(row["download_selected"]),
                "venue": row["venue"],
                "venue_rank": row["venue_rank"],
                "local_path": row["local_path"],
            })
        return [
            {
                "run_id": row["run_id"],
                "query": row["query"],
                "topic_folder": row["topic_folder"],
                "created_at": row["created_at"],
                "candidate_count": row["candidate_count"],
                "downloaded_count": row["downloaded_count"],
                "reused_count": row["reused_count"],
                "papers": by_run.get(row["run_id"], []),
            }
            for row in runs
        ]

    def delete_paper(self, paper_id: str, *, remove_file: bool = True) -> bool:
        now = _now()
        with self._connect() as conn:
            row = conn.execute("select local_path from papers where paper_id = ? and deleted_at = ''", (paper_id,)).fetchone()
            if row is None:
                return False
            conn.execute("update papers set deleted_at = ?, last_seen_at = ? where paper_id = ?", (now, now, paper_id))
        if remove_file:
            path = Path(row["local_path"] or "")
            if path.exists() and path.is_file():
                try:
                    path.unlink()
                except OSError:
                    pass
        return True

    def import_manifests(self, search_root: str | Path) -> int:
        root = Path(search_root)
        if not root.exists():
            return 0
        imported = 0
        for manifest_path in root.glob("*/manifest.json"):
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            papers = manifest.get("papers")
            if not isinstance(papers, list):
                continue
            for entry in papers:
                if not isinstance(entry, dict):
                    continue
                local_path = str(entry.get("local_path") or "")
                if not local_path or not Path(local_path).exists():
                    continue
                candidate = CandidatePaper(
                    paper_id=str(entry.get("paper_id") or _normalize_title(str(entry.get("title") or "")) or uuid.uuid4().hex),
                    title=str(entry.get("title") or Path(local_path).stem),
                    authors=_as_string_list(entry.get("authors")),
                    year=_as_int(entry.get("year")),
                    venue=str(entry.get("venue") or ""),
                    venue_canonical_name=str(entry.get("venue_canonical_name") or ""),
                    venue_rank=_as_venue_rank(str(entry.get("venue_rank") or "")),
                    doi=str(entry.get("doi") or ""),
                    arxiv_id=str(entry.get("arxiv_id") or ""),
                    pdf_url=str(entry.get("pdf_url") or ""),
                    landing_url=str(entry.get("landing_url") or ""),
                    url=str(entry.get("landing_url") or entry.get("pdf_url") or ""),
                )
                item = ResolvedPaperSource(
                    paper_id=candidate.paper_id,
                    title=candidate.title,
                    doi=candidate.doi,
                    arxiv_id=candidate.arxiv_id,
                    pdf_url=candidate.pdf_url,
                    landing_url=candidate.landing_url,
                    download_status="downloaded",
                    local_path=local_path,
                    sha256=str(entry.get("sha256") or ""),
                    file_size=Path(local_path).stat().st_size,
                    has_valid_deep_reading_source=True,
                    metadata={"resolution_strategy": "manifest_import"},
                )
                if self.upsert_download(candidate, item) is not None:
                    imported += 1
        return imported

    def _existing_paper_id(self, *, doi: str, arxiv_id: str, normalized_title: str, sha256: str = "") -> str:
        with self._connect() as conn:
            if doi:
                row = conn.execute("select paper_id from papers where doi = ? order by last_seen_at desc limit 1", (doi,)).fetchone()
                if row is not None:
                    return str(row["paper_id"])
            if arxiv_id:
                row = conn.execute("select paper_id from papers where arxiv_id = ? order by last_seen_at desc limit 1", (arxiv_id,)).fetchone()
                if row is not None:
                    return str(row["paper_id"])
            if normalized_title:
                row = conn.execute(
                    "select paper_id from papers where normalized_title = ? order by last_seen_at desc limit 1",
                    (normalized_title,),
                ).fetchone()
                if row is not None:
                    return str(row["paper_id"])
            if sha256:
                row = conn.execute("select paper_id from papers where sha256 = ? order by last_seen_at desc limit 1", (sha256,)).fetchone()
                if row is not None:
                    return str(row["paper_id"])
        return ""

    def _upsert_source_rows(
        self,
        conn: sqlite3.Connection,
        paper_id: str,
        candidate: CandidatePaper,
        item: ResolvedPaperSource,
        *,
        source_url: str,
        seen_at: str,
    ) -> None:
        source_ids = dict(candidate.source_ids)
        if candidate.source and candidate.paper_id:
            source_ids.setdefault(candidate.source, candidate.paper_id)
        rows: list[tuple[str, str, str, str, str, str]] = []
        for source, source_id in source_ids.items():
            rows.append((paper_id, source, str(source_id), source_url, seen_at, seen_at))
        for source, url in (
            ("pdf", item.pdf_url or candidate.pdf_url),
            ("landing", item.landing_url or candidate.landing_url or candidate.url),
            ("source", item.source_url or candidate.source_url),
        ):
            if url:
                rows.append((paper_id, source, "", url, seen_at, seen_at))
        if not rows:
            return
        conn.executemany(
            """
            insert into paper_sources(paper_id, source, source_id, url, first_seen_at, last_seen_at)
            values(?,?,?,?,?,?)
            on conflict(paper_id, source, source_id, url) do update set last_seen_at=excluded.last_seen_at
            """,
            rows,
        )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                create table if not exists papers(
                    paper_id text primary key,
                    title text not null,
                    normalized_title text not null,
                    authors text not null default '[]',
                    year integer,
                    venue text not null default '',
                    venue_canonical_name text not null default '',
                    venue_rank text not null default 'unranked',
                    doi text not null default '',
                    arxiv_id text not null default '',
                    pdf_url text not null default '',
                    landing_url text not null default '',
                    local_path text not null default '',
                    sha256 text not null default '',
                    file_size integer not null default 0,
                    downloaded_at text not null default '',
                    first_seen_at text not null,
                    last_seen_at text not null,
                    deleted_at text not null default ''
                )
                """
            )
            conn.execute("create index if not exists idx_papers_doi on papers(doi)")
            conn.execute("create index if not exists idx_papers_arxiv on papers(arxiv_id)")
            conn.execute("create index if not exists idx_papers_title on papers(normalized_title)")
            conn.execute("create index if not exists idx_papers_sha256 on papers(sha256)")
            conn.execute(
                """
                create table if not exists paper_sources(
                    id integer primary key autoincrement,
                    paper_id text not null,
                    source text not null default '',
                    source_id text not null default '',
                    url text not null default '',
                    first_seen_at text not null,
                    last_seen_at text not null,
                    unique(paper_id, source, source_id, url)
                )
                """
            )
            conn.execute("create index if not exists idx_paper_sources_url on paper_sources(url)")
            conn.execute(
                """
                create table if not exists search_runs(
                    run_id text primary key,
                    query text not null,
                    topic_folder text not null default '',
                    created_at text not null,
                    candidate_count integer not null default 0,
                    downloaded_count integer not null default 0,
                    reused_count integer not null default 0
                )
                """
            )
            conn.execute(
                """
                create table if not exists search_run_papers(
                    run_id text not null,
                    paper_id text not null,
                    title text not null,
                    search_rank integer not null default 0,
                    action text not null default '',
                    reason text not null default '',
                    download_selected integer not null default 0,
                    venue text not null default '',
                    venue_rank text not null default '',
                    local_path text not null default '',
                    primary key(run_id, paper_id, title)
                )
                """
            )
            self._migrate_search_run_papers(conn)

    @staticmethod
    def _migrate_search_run_papers(conn: sqlite3.Connection) -> None:
        columns = {row["name"] for row in conn.execute("pragma table_info(search_run_papers)").fetchall()}
        if "search_rank" not in columns:
            conn.execute("alter table search_run_papers add column search_rank integer not null default 0")
        if "download_selected" not in columns:
            conn.execute("alter table search_run_papers add column download_selected integer not null default 0")


def _record_from_row(row: sqlite3.Row) -> PaperLibraryRecord:
    return PaperLibraryRecord(
        paper_id=row["paper_id"],
        title=row["title"],
        normalized_title=row["normalized_title"],
        authors=_as_string_list(json.loads(row["authors"] or "[]")),
        year=row["year"],
        venue=row["venue"],
        venue_canonical_name=row["venue_canonical_name"],
        venue_rank=row["venue_rank"],
        doi=row["doi"],
        arxiv_id=row["arxiv_id"],
        pdf_url=row["pdf_url"],
        landing_url=row["landing_url"],
        local_path=row["local_path"],
        sha256=row["sha256"],
        file_size=row["file_size"],
        downloaded_at=row["downloaded_at"],
        first_seen_at=row["first_seen_at"],
        last_seen_at=row["last_seen_at"],
        deleted_at=row["deleted_at"],
    )


def _normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", title.lower())).strip()


def _normalize_doi(doi: str) -> str:
    value = doi.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if value.startswith(prefix):
            value = value[len(prefix):]
    return value


def _normalize_arxiv(arxiv_id: str) -> str:
    value = arxiv_id.strip().lower()
    value = value.removeprefix("arxiv:")
    value = value.removeprefix("https://arxiv.org/abs/")
    value = value.removeprefix("http://arxiv.org/abs/")
    value = value.removesuffix(".pdf")
    return value


def _library_id(*, doi: str, arxiv_id: str, normalized_title: str, fallback: str) -> str:
    if doi:
        key = f"doi:{doi}"
    elif arxiv_id:
        key = f"arxiv:{arxiv_id}"
    elif normalized_title:
        key = f"title:{normalized_title}"
    else:
        key = f"id:{fallback}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:24]


def _venue_rank_value(rank: VenueRank | str) -> str:
    return rank.value if isinstance(rank, VenueRank) else str(rank or VenueRank.UNRANKED.value)


def _search_rank(candidate: CandidatePaper, *, fallback: int) -> int:
    metadata = candidate.raw_source_metadata or {}
    for key in ("search_rank", "rank", "download_queue_rank"):
        value = metadata.get(key)
        try:
            rank = int(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            continue
        if rank > 0:
            return rank
    return fallback


def _as_venue_rank(value: str) -> VenueRank:
    for rank in VenueRank:
        if value == rank.value:
            return rank
    return VenueRank.UNRANKED


def _as_string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _as_int(value: object) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
