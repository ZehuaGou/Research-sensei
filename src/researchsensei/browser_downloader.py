from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BrowserDownloadResult:
    attempted: bool = False
    success: bool = False
    local_path: str = ""
    final_url: str = ""
    content_type: str = ""
    error_code: str = ""
    error: str = ""


class BrowserSessionDownloader:
    """Optional real-Chrome fallback for a user-authorized publisher session.

    The storage-state file is created explicitly by the user with the bundled
    browser helper. ResearchSensei never reads the user's normal Chrome profile
    or browser cookie database. The helper receives only the landing/PDF URLs
    for the relevance-cleared paper currently being downloaded.
    """

    def __init__(
        self,
        *,
        storage_state_path: str | Path,
        headless: bool = True,
        timeout_seconds: float = 90.0,
        node_command: str = "node",
        helper_script: str | Path | None = None,
    ) -> None:
        self.storage_state_path = Path(storage_state_path).expanduser().resolve()
        self.headless = headless
        self.timeout_seconds = max(float(timeout_seconds), 1.0)
        self.node_command = node_command
        repo_root = Path(__file__).resolve().parents[2]
        self.helper_script = Path(
            helper_script or repo_root / "frontend" / "scripts" / "browser_fulltext.mjs"
        ).resolve()

    @property
    def available(self) -> bool:
        return bool(
            self.storage_state_path.is_file()
            and self.helper_script.is_file()
            and shutil.which(self.node_command)
        )

    def download(
        self,
        *,
        landing_url: str,
        pdf_urls: list[str],
        target_path: str | Path,
        expected_title: str,
    ) -> BrowserDownloadResult:
        if not self.available:
            return BrowserDownloadResult(
                error_code="BROWSER_SESSION_UNAVAILABLE",
                error="Browser session state, helper, or Node.js is unavailable.",
            )

        target = Path(target_path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        request = {
            "storageStatePath": str(self.storage_state_path),
            "landingUrl": landing_url,
            "pdfUrls": pdf_urls,
            "targetPath": str(target),
            "expectedTitle": expected_title,
            "headless": self.headless,
            "timeoutMs": int(self.timeout_seconds * 1000),
        }
        try:
            completed = subprocess.run(
                [self.node_command, str(self.helper_script), "download"],
                input=json.dumps(request, ensure_ascii=False),
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds + 15.0,
                check=False,
                cwd=str(self.helper_script.parent.parent),
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return BrowserDownloadResult(
                attempted=True,
                error_code="BROWSER_SESSION_FAILED",
                error=str(exc)[:300],
            )

        try:
            payload = json.loads(completed.stdout.strip())
        except (json.JSONDecodeError, TypeError):
            payload = {}
        success = bool(payload.get("success")) and target.is_file()
        return BrowserDownloadResult(
            attempted=True,
            success=success,
            local_path=str(target) if success else "",
            final_url=str(payload.get("finalUrl") or ""),
            content_type=str(payload.get("contentType") or ""),
            error_code=str(payload.get("errorCode") or ("" if success else "BROWSER_SESSION_FAILED")),
            error=str(payload.get("error") or completed.stderr or "")[:300],
        )
