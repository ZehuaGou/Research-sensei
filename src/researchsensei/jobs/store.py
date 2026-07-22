from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from collections.abc import Sequence

from researchsensei.core.sqlite import connect_sqlite
from researchsensei.schemas import JobRecord, JobStatus, WarningItem, WorkspaceArtifact


class JobNotFoundError(KeyError):
    pass


class DuplicateSourceJobError(RuntimeError):
    def __init__(self, job: JobRecord) -> None:
        super().__init__(f"An active job already exists for source identity: {job.source_identity}")
        self.job = job


class DatabaseMigrationError(RuntimeError):
    pass


class JobStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def create(self, job: JobRecord) -> JobRecord:
        with self._connect() as conn:
            conn.execute("begin immediate")
            if job.source_identity:
                row = conn.execute(
                    """
                    select * from jobs
                    where source_identity = ? and status in (?, ?, ?)
                    order by created_at desc limit 1
                    """,
                    (
                        job.source_identity,
                        JobStatus.PENDING.value,
                        JobStatus.RUNNING.value,
                        JobStatus.SUCCEEDED.value,
                    ),
                ).fetchone()
                if row is not None:
                    raise DuplicateSourceJobError(self._from_row(row))
            values = _to_column_values(job)
            columns = [column for column in values if column in _table_columns(conn)]
            placeholders = ",".join("?" for _ in columns)
            conn.execute(
                f"insert into jobs({','.join(columns)}) values({placeholders})",
                tuple(values[column] for column in columns),
            )
        return job

    def get(self, job_id: str) -> JobRecord:
        with self._connect() as conn:
            row = conn.execute("select * from jobs where job_id = ?", (job_id,)).fetchone()
        if row is None:
            raise JobNotFoundError(f"Job not found: {job_id}")
        return self._from_row(row)

    def resolve_latest_job_id(self, job_id: str) -> str:
        """Follow successful reparse links without hiding the original record."""

        current = job_id
        visited: set[str] = set()
        with self._connect() as conn:
            while current not in visited:
                visited.add(current)
                row = conn.execute(
                    "select successor_job_id from job_successors where source_job_id = ?",
                    (current,),
                ).fetchone()
                if row is None:
                    break
                current = str(row["successor_job_id"])
        return current

    def get_latest(self, job_id: str) -> JobRecord:
        return self.get(self.resolve_latest_job_id(job_id))

    def link_successor(self, source_job_id: str, successor_job_id: str) -> None:
        if source_job_id == successor_job_id:
            return
        with self._connect() as conn:
            conn.execute("begin immediate")
            known = {
                str(row["job_id"])
                for row in conn.execute(
                    "select job_id from jobs where job_id in (?, ?)",
                    (source_job_id, successor_job_id),
                ).fetchall()
            }
            if source_job_id not in known:
                raise JobNotFoundError(f"Job not found: {source_job_id}")
            if successor_job_id not in known:
                raise JobNotFoundError(f"Job not found: {successor_job_id}")

            current = successor_job_id
            visited = {source_job_id}
            while current not in visited:
                visited.add(current)
                row = conn.execute(
                    "select successor_job_id from job_successors where source_job_id = ?",
                    (current,),
                ).fetchone()
                if row is None:
                    break
                current = str(row["successor_job_id"])
            if current == source_job_id:
                raise ValueError("Reparse successor link would create a cycle.")

            conn.execute(
                """
                insert into job_successors(source_job_id, successor_job_id, created_at)
                values(?, ?, ?)
                on conflict(source_job_id) do update set
                    successor_job_id=excluded.successor_job_id,
                    created_at=excluded.created_at
                """,
                (source_job_id, successor_job_id, datetime.now(timezone.utc).isoformat()),
            )

    def delete(self, job_id: str) -> None:
        with self._connect() as conn:
            cursor = conn.execute("delete from jobs where job_id = ?", (job_id,))
            deleted = cursor.rowcount
        if deleted == 0:
            raise JobNotFoundError(f"Job not found: {job_id}")

    def find_by_source_identity(self, source_identity: str) -> JobRecord | None:
        """Return the most recent active or successful job for an identity."""
        if not source_identity:
            return None
        with self._connect() as conn:
            row = conn.execute(
                """
                select * from jobs
                where source_identity = ? and status in (?, ?, ?)
                order by created_at desc limit 1
                """,
                (
                    source_identity,
                    JobStatus.PENDING.value,
                    JobStatus.RUNNING.value,
                    JobStatus.SUCCEEDED.value,
                ),
            ).fetchone()
        if row is None:
            return None
        return self._from_row(row)

    def list_recent(self, limit: int = 20) -> list[JobRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "select * from jobs order by created_at desc limit ?",
                (max(1, min(int(limit), 200)),),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def list_ids(self) -> set[str]:
        with self._connect() as conn:
            return {str(row["job_id"]) for row in conn.execute("select job_id from jobs").fetchall()}

    def update(
        self,
        job_id: str,
        *,
        status: JobStatus | None = None,
        current_step: str | None = None,
        error: str | None = None,
        warnings: list[WarningItem] | None = None,
        artifacts: list[WorkspaceArtifact] | None = None,
    ) -> JobRecord:
        with self._connect() as conn:
            conn.execute("begin immediate")
            row = conn.execute("select * from jobs where job_id = ?", (job_id,)).fetchone()
            if row is None:
                raise JobNotFoundError(f"Job not found: {job_id}")
            job = self._from_row(row)
            version = int(row["version"] if "version" in row.keys() else 0)
            updated = job.model_copy(
                update={
                    "status": status or job.status,
                    "current_step": current_step if current_step is not None else job.current_step,
                    "error": error if error is not None else job.error,
                    "warnings": warnings if warnings is not None else job.warnings,
                    "artifacts": artifacts if artifacts is not None else job.artifacts,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            cursor = conn.execute(
                """
                update jobs
                set status=?, source_path=?, run_dir=?, current_step=?, error=?, warnings=?, artifacts=?, created_at=?, updated_at=?, version=version+1
                where job_id=? and version=?
                """,
                (
                    updated.status.value,
                    updated.source_path,
                    updated.run_dir,
                    updated.current_step,
                    updated.error,
                    _dump_models(updated.warnings),
                    _dump_models(updated.artifacts),
                    updated.created_at,
                    updated.updated_at,
                    updated.job_id,
                    version,
                ),
            )
            if cursor.rowcount != 1:
                raise RuntimeError(f"Concurrent update conflict for job: {job_id}")
        return updated

    def _connect(self) -> sqlite3.Connection:
        conn = connect_sqlite(self.db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("pragma busy_timeout=5000")
        conn.execute("pragma foreign_keys=on")
        return conn

    def _init(self) -> None:
        try:
            with self._connect() as conn:
                conn.execute("pragma journal_mode=wal")
                conn.execute(
                    """
                    create table if not exists schema_meta(
                        component text primary key,
                        version integer not null,
                        updated_at text not null
                    )
                    """
                )
                conn.execute(
                """
                create table if not exists jobs(
                    job_id text primary key,
                    status text not null,
                    source_path text not null,
                    run_dir text not null,
                    current_step text not null,
                    error text not null,
                    warnings text not null,
                    artifacts text not null,
                    created_at text not null,
                    updated_at text not null
                )
                """
                )
                conn.execute(
                    """
                    create table if not exists job_successors(
                        source_job_id text primary key references jobs(job_id) on delete cascade,
                        successor_job_id text not null references jobs(job_id) on delete cascade,
                        created_at text not null
                    )
                    """
                )
                self._migrate(conn)
                conn.execute(
                    """
                    insert into schema_meta(component, version, updated_at) values('jobs', 3, ?)
                    on conflict(component) do update set version=excluded.version, updated_at=excluded.updated_at
                    """,
                    (datetime.now(timezone.utc).isoformat(),),
                )
        except sqlite3.Error as error:
            raise DatabaseMigrationError(
                f"Job database migration failed for {self.db_path}. Restore the latest backup before retrying: {error}"
            ) from error

    def _migrate(self, conn: sqlite3.Connection) -> None:
        columns = {row["name"] for row in conn.execute("pragma table_info(jobs)").fetchall()}
        required_columns = {
            "source_path": "text not null default ''",
            "run_dir": "text not null default ''",
            "current_step": "text not null default ''",
            "error": "text not null default ''",
            "warnings": "text not null default '[]'",
            "artifacts": "text not null default '[]'",
            "created_at": "text not null default ''",
            "updated_at": "text not null default ''",
            "source_identity": "text not null default ''",
            "version": "integer not null default 0",
        }
        for column, definition in required_columns.items():
            if column not in columns:
                conn.execute(f"alter table jobs add column {column} {definition}")
        # Ensure index for source_identity lookups
        existing_indexes = {row["name"] for row in conn.execute("pragma index_list(jobs)").fetchall()}
        if "idx_jobs_source_identity" not in existing_indexes:
            conn.execute("create index idx_jobs_source_identity on jobs(source_identity)")

    def backup(self, target: str | Path | None = None) -> Path:
        destination = Path(target) if target is not None else self.db_path.with_suffix(self.db_path.suffix + ".bak")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as source, connect_sqlite(destination) as backup_conn:
            source.backup(backup_conn)
        return destination

    def _to_row(self, job: JobRecord) -> tuple[str, ...]:
        return (
            job.job_id,
            job.status.value,
            job.source_path,
            job.run_dir,
            job.current_step,
            job.error,
            _dump_models(job.warnings),
            _dump_models(job.artifacts),
            job.created_at,
            job.updated_at,
        )

    def _from_row(self, row: sqlite3.Row) -> JobRecord:
        return JobRecord(
            job_id=row["job_id"],
            status=JobStatus(row["status"]),
            source_path=row["source_path"],
            run_dir=row["run_dir"],
            source_identity=row["source_identity"] if "source_identity" in row.keys() else "",
            current_step=row["current_step"],
            error=row["error"],
            warnings=[WarningItem(**item) for item in json.loads(row["warnings"] or "[]")],
            artifacts=[WorkspaceArtifact(**item) for item in json.loads(row["artifacts"] or "[]")],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


def _dump_models(values: Sequence[object]) -> str:
    return json.dumps(
        [
            value.model_dump(mode="json") if hasattr(value, "model_dump") else value
            for value in values
        ],
        ensure_ascii=False,
    )


def _table_columns(conn: sqlite3.Connection) -> set[str]:
    return {row["name"] for row in conn.execute("pragma table_info(jobs)").fetchall()}


def _to_column_values(job: JobRecord) -> dict[str, str]:
    source_name = Path(job.source_path).name if job.source_path else ""
    return {
        "job_id": job.job_id,
        "status": job.status.value,
        "filename": source_name,
        "source_pdf": job.source_path,
        "source_path": job.source_path,
        "run_dir": job.run_dir,
        "current_step": job.current_step,
        "error": job.error,
        "warnings": _dump_models(job.warnings),
        "artifacts": _dump_models(job.artifacts),
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "source_identity": job.source_identity,
    }
