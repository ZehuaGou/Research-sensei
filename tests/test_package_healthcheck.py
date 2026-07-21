import os
import subprocess
import sys
from pathlib import Path

from starlette.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def _cli_env() -> dict[str, str]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(SRC) if not existing else f"{SRC}{os.pathsep}{existing}"
    return env


def test_researchsensei_package_imports() -> None:
    import researchsensei

    assert researchsensei.__version__


def test_cli_help_succeeds() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "researchsensei", "--help"],
        cwd=ROOT,
        env=_cli_env(),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "healthcheck" in result.stdout


def test_cli_healthcheck_succeeds_without_touching_workspace(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "researchsensei", "healthcheck"],
        cwd=tmp_path,
        env=_cli_env(),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "ResearchSensei healthcheck: ok" in result.stdout
    assert not (tmp_path / "workspace").exists()


def test_basic_fastapi_app_health_endpoint(tmp_path: Path) -> None:
    from researchsensei.web.app import create_app

    with TestClient(create_app(workspace_root=tmp_path / "workspace")) as client:
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "service": "researchsensei"}
