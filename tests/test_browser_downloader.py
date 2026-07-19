from __future__ import annotations

import json
import subprocess
from pathlib import Path

from researchsensei.browser_downloader import BrowserSessionDownloader


def test_browser_session_downloader_uses_only_explicit_state_and_candidate_urls(
    tmp_path: Path,
    monkeypatch,
) -> None:
    state = tmp_path / "browser-session.json"
    state.write_text('{"cookies": [], "origins": []}', encoding="utf-8")
    helper = tmp_path / "browser_fulltext.mjs"
    helper.write_text("// injected test helper", encoding="utf-8")
    target = tmp_path / "paper.pdf"
    captured: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured["command"] = command
        captured["request"] = json.loads(str(kwargs["input"]))
        target.write_bytes(b"%PDF-1.4\nhelper\n%%EOF")
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps({
                "success": True,
                "finalUrl": "https://dl.acm.org/doi/pdf/10.1145/example",
                "contentType": "application/pdf",
            }),
            stderr="",
        )

    monkeypatch.setattr("researchsensei.browser_downloader.shutil.which", lambda _name: "node")
    monkeypatch.setattr("researchsensei.browser_downloader.subprocess.run", fake_run)
    downloader = BrowserSessionDownloader(
        storage_state_path=state,
        helper_script=helper,
        timeout_seconds=5,
    )

    result = downloader.download(
        landing_url="https://dl.acm.org/doi/10.1145/example",
        pdf_urls=["https://dl.acm.org/doi/pdf/10.1145/example"],
        target_path=target,
        expected_title="Relevant ACM Paper",
    )

    assert result.success is True
    assert result.local_path == str(target.resolve())
    assert captured["command"] == ["node", str(helper.resolve()), "download"]
    request = captured["request"]
    assert isinstance(request, dict)
    assert request["storageStatePath"] == str(state.resolve())
    assert request["landingUrl"] == "https://dl.acm.org/doi/10.1145/example"
    assert "cookies" not in request


def test_browser_session_downloader_fails_closed_without_saved_state(tmp_path: Path) -> None:
    downloader = BrowserSessionDownloader(
        storage_state_path=tmp_path / "missing.json",
        helper_script=tmp_path / "missing.mjs",
    )

    result = downloader.download(
        landing_url="https://dl.acm.org/doi/10.1145/example",
        pdf_urls=[],
        target_path=tmp_path / "paper.pdf",
        expected_title="Relevant ACM Paper",
    )

    assert result.attempted is False
    assert result.success is False
    assert result.error_code == "BROWSER_SESSION_UNAVAILABLE"
    assert not (tmp_path / "paper.pdf").exists()
