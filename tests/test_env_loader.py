from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from researchsensei.core.env_loader import load_runtime_env, mask_value


# Persisted env keys that may conflict with tests
_REAL_ENV_KEYS = ["UNPAYWALL_EMAIL", "MIMO_API_KEY", "DEEPSEEK_API_KEY",
                   "S2_API_KEY", "SEMANTIC_SCHOLAR_API_KEY"]


@pytest.fixture(autouse=True)
def _isolate_env():
    """Save and restore real env keys that tests may modify."""
    saved = {}
    for k in _REAL_ENV_KEYS:
        saved[k] = os.environ.pop(k, None)
    yield
    for k in _REAL_ENV_KEYS:
        os.environ.pop(k, None)
        if saved.get(k) is not None:
            os.environ[k] = saved[k]


class TestMaskValue:
    def test_mask_api_key(self):
        assert mask_value("MIMO_API_KEY", "tp-abc123def456") == "tp-***"

    def test_mask_email(self):
        result = mask_value("UNPAYWALL_EMAIL", "gouzehua@foxmail.com")
        assert result == "gou***@foxmail.com"

    def test_mask_empty(self):
        assert mask_value("MIMO_API_KEY", "") == "MISSING"

    def test_mask_short_string(self):
        assert mask_value("SOME_KEY", "ab") == "ab***"

    def test_mask_unknown_key(self):
        assert mask_value("UNKNOWN_KEY", "my-secret-value") == "my-***"


class TestLoadRuntimeEnv:
    def test_loads_keys_into_os_environ(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text("MIMO_API_KEY=tp-secret-key\n", encoding="utf-8")
            loaded = load_runtime_env(env_path=str(env_path), suppress_errors=False)
            assert "MIMO_API_KEY" in loaded
            assert os.environ.get("MIMO_API_KEY") == "tp-secret-key"

    def test_returns_masked_values_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text("UNPAYWALL_EMAIL=test@example.com\n", encoding="utf-8")
            loaded = load_runtime_env(env_path=str(env_path), suppress_errors=False)
            assert loaded["UNPAYWALL_EMAIL"] == "tes***@example.com"

    def test_returns_unmasked_when_mask_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text("MIMO_API_KEY=tp-secret\n", encoding="utf-8")
            loaded = load_runtime_env(env_path=str(env_path), mask=False, suppress_errors=False)
            assert loaded["MIMO_API_KEY"] == "tp-secret"

    def test_does_not_overwrite_existing_os_environ(self):
        os.environ["MIMO_API_KEY"] = "existing_value"
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text("MIMO_API_KEY=from_dotenv\nUNPAYWALL_EMAIL=new@dotenv.com\n", encoding="utf-8")
            loaded = load_runtime_env(env_path=str(env_path), suppress_errors=False)
            assert os.environ["MIMO_API_KEY"] == "existing_value"
            assert os.environ["UNPAYWALL_EMAIL"] == "new@dotenv.com"
            assert "UNPAYWALL_EMAIL" in loaded

    def test_handles_missing_file_suppressed(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "nonexistent.env"
            result = load_runtime_env(env_path=str(missing), suppress_errors=True)
            assert result == {}

    def test_handles_missing_file_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "nonexistent.env"
            with pytest.raises(FileNotFoundError):
                load_runtime_env(env_path=str(missing), suppress_errors=False)

    def test_empty_env_file_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text("", encoding="utf-8")
            result = load_runtime_env(env_path=str(env_path), suppress_errors=False)
            assert result == {}

    def test_handles_bom_encoded_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_bytes(b"\xef\xbb\xbfMIMO_API_KEY=tp-bom-secret\n")
            loaded = load_runtime_env(env_path=str(env_path), suppress_errors=False)
            assert loaded.get("MIMO_API_KEY", "MISSING") != "MISSING"
            assert os.environ.get("MIMO_API_KEY") == "tp-bom-secret"


class TestS2Alias:
    def test_s2_api_key_aliased_to_semantic_scholar(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text("S2_API_KEY=s2-secret-key\n", encoding="utf-8")
            loaded = load_runtime_env(env_path=str(env_path), suppress_errors=False)
            assert "SEMANTIC_SCHOLAR_API_KEY" in loaded
            assert os.environ.get("SEMANTIC_SCHOLAR_API_KEY") == "s2-secret-key"

    def test_semantic_scholar_api_key_aliased_to_s2(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text("SEMANTIC_SCHOLAR_API_KEY=ss-secret-key\n", encoding="utf-8")
            loaded = load_runtime_env(env_path=str(env_path), suppress_errors=False)
            assert "S2_API_KEY" in loaded
            assert os.environ.get("S2_API_KEY") == "ss-secret-key"

    def test_both_set_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text(
                "S2_API_KEY=s2-override\nSEMANTIC_SCHOLAR_API_KEY=ss-override\n",
                encoding="utf-8",
            )
            loaded = load_runtime_env(env_path=str(env_path), suppress_errors=False)
            assert loaded.get("S2_API_KEY") is not None
            assert loaded.get("SEMANTIC_SCHOLAR_API_KEY") is not None


class TestConfigServiceIntegration:
    def test_config_service_delegates_to_env_loader(self):
        from researchsensei.core.config import ConfigService

        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text("MIMO_API_KEY=tp-cs-integration\n", encoding="utf-8")
            assert "MIMO_API_KEY" not in os.environ
            ConfigService(config_path="nonexistent", env_path=str(env_path)).load()
            assert os.environ.get("MIMO_API_KEY") == "tp-cs-integration"


class TestNoSecretPrinting:
    def test_mask_in_loaded_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text("MIMO_API_KEY=tp-top-secret-key\nUNPAYWALL_EMAIL=real@mail.com\n", encoding="utf-8")
            loaded = load_runtime_env(env_path=str(env_path), suppress_errors=False)
            output = str(loaded)
            assert "tp-top-secret-key" not in output
            assert "real@mail.com" not in output
            assert "tp-***" in output
            assert "rea***@mail.com" in output
