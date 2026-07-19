from __future__ import annotations

import pytest

from researchsensei.llm.client import LLMResponseError, parse_llm_json


def test_parse_llm_json_accepts_fenced_object_with_trailing_prose() -> None:
    payload = parse_llm_json(
        'Here is the result:\n```json\n{"claims": [{"text": "ok"}]}\n```\nDone.'
    )

    assert payload == {"claims": [{"text": "ok"}]}


def test_parse_llm_json_handles_braces_in_strings_and_trailing_commas() -> None:
    payload = parse_llm_json('{"text": "set {x}", "items": [1, 2,],} extra')

    assert payload == {"text": "set {x}", "items": [1, 2]}


def test_parse_llm_json_never_exposes_raw_model_output_in_error() -> None:
    with pytest.raises(LLMResponseError) as caught:
        parse_llm_json('{"secret_evidence": "do-not-leak"')

    assert "do-not-leak" not in str(caught.value)
    assert str(caught.value) == "LLM returned invalid JSON output"
