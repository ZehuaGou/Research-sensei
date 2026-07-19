from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from researchsensei.library import PaperLibraryStore


def create_library_router(paper_library: PaperLibraryStore) -> APIRouter:
    router = APIRouter(prefix="/api/v1/library", tags=["library"])

    @router.get("/papers")
    def list_library_papers(
        query: str = Query(default="", max_length=500),
        limit: int = Query(default=100, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
        include_deleted: bool = False,
    ) -> dict[str, object]:
        return {
            "papers": paper_library.list_papers(
                query=query,
                limit=limit,
                offset=offset,
                include_deleted=include_deleted,
            ),
            "total": paper_library.count_papers(
                query=query,
                include_deleted=include_deleted,
            ),
            "limit": limit,
            "offset": offset,
        }

    @router.get("/search_runs")
    def list_library_search_runs(limit: int = Query(default=50, ge=1, le=200)) -> dict[str, object]:
        return {"search_runs": paper_library.list_search_runs(limit=limit)}

    @router.delete("/papers/{paper_id}")
    def delete_library_paper(paper_id: str, remove_file: bool = True) -> dict[str, object]:
        try:
            deleted = paper_library.delete_paper(paper_id, remove_file=remove_file)
        except ValueError as error:
            raise HTTPException(
                status_code=409,
                detail={"code": "UNSAFE_LIBRARY_PATH", "message": str(error)},
            ) from error
        if not deleted:
            raise HTTPException(status_code=404, detail="Paper not found.")
        return {"status": "DELETED", "paper_id": paper_id, "remove_file": remove_file}

    return router
