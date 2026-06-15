"""Run reproducible M2 live acceptance on a real M1 canonical bundle."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from researchsensei.core.config import ConfigService, ModelProviderConfig  # noqa: E402
from researchsensei.llm.client import LLMClient, parse_llm_json  # noqa: E402
from researchsensei.llm.types import ChatMessage, ChatResponse, LLMConfig  # noqa: E402
from researchsensei.m2.full_pipeline import run_m2_full_pipeline  # noqa: E402


POSITIVE_REQUIRED_ARTIFACTS = [
    "source_status.json",
    "canonical_status.json",
    "parsed_document.json",
    "passage_index.json",
    "claim_evidence.json",
    "evidence_index.json",
    "paper_skeleton.json",
    "evidence_pack.json",
    "formula_evidence_pack.json",
    "survey_status.json",
    "survey_landscape.json",
    "method_taxonomy.json",
    "extracted_key_papers.json",
    "survey_claims.json",
    "paper_card.json",
    "formula_cards.json",
    "teaching_cards.json",
    "quality_report.json",
    "understanding_status.json",
    "m2_run_summary.json",
    "m2_full_report.md",
]

CARD_ARTIFACTS = ["paper_card.json", "formula_cards.json", "teaching_cards.json"]
ACCEPTED_POSITIVE_STATUSES = {"SUCCESS", "DEGRADED_STRUCTURAL"}


class M2LLMUsage:
    def __init__(self, model: str = "") -> None:
        self.model = model
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0
        self.call_count = 0
        self.latencies_ms: list[int] = []

    def as_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "call_count": self.call_count,
            "latencies_ms": self.latencies_ms,
        }


class MeteredM2LLMClient:
    """LLMClient wrapper that records real-call metadata."""

    def __init__(self, provider: ModelProviderConfig, config: LLMConfig) -> None:
        self.provider = provider
        self.client = LLMClient(provider, config=config)
        self.config = config
        self.usage = M2LLMUsage(model=provider.model)

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        config: LLMConfig | None = None,
    ) -> ChatResponse:
        cfg = config or self.config
        started = time.perf_counter()
        response = await self.client.chat(messages, config=cfg)
        latency_ms = int((time.perf_counter() - started) * 1000)
        self._record(response, messages, latency_ms)
        return response

    async def chat_json(
        self,
        messages: list[ChatMessage],
        *,
        config: LLMConfig | None = None,
    ) -> dict[str, Any]:
        cfg = config or self.config.model_copy(update={"json_mode": True, "temperature": 0.2})
        response = await self.chat(messages, config=cfg)
        return parse_llm_json(response.content)

    def _record(
        self,
        response: ChatResponse,
        messages: list[ChatMessage],
        latency_ms: int,
    ) -> None:
        prompt_tokens = response.usage_prompt_tokens or _estimate_tokens(
            "\n".join(message.content for message in messages)
        )
        completion_tokens = response.usage_completion_tokens or _estimate_tokens(response.content)
        total_tokens = response.usage_total_tokens or prompt_tokens + completion_tokens
        self.usage.model = response.model or self.usage.model
        self.usage.prompt_tokens += prompt_tokens
        self.usage.completion_tokens += completion_tokens
        self.usage.total_tokens += total_tokens
        self.usage.call_count += 1
        self.usage.latencies_ms.append(latency_ms)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run M2 live acceptance with real M1 input, real LLM, and negative gates."
    )
    parser.add_argument(
        "--input-dir",
        default=str(ROOT / "reports" / "m1_canonical_acceptance" / "2310_08800v2"),
        help="Real M1 artifact directory. Defaults to reports/m1_canonical_acceptance/2310_08800v2.",
    )
    parser.add_argument("--provider", default="", help="Provider from config/local.toml. Defaults to active_provider.")
    parser.add_argument("--llm-max-tokens", type=int, default=2400)
    parser.add_argument("--llm-timeout", type=float, default=0.0)
    parser.add_argument(
        "--work-root",
        default=str(ROOT / "reports" / "m2_live_acceptance_work"),
        help="Ignored report work directory for positive and negative runs.",
    )
    parser.add_argument(
        "--report-path",
        default=str(ROOT / "reports" / "m2_live_acceptance.md"),
        help="Markdown acceptance report path.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    input_dir = Path(args.input_dir).resolve()
    work_root = Path(args.work_root).resolve()
    report_path = Path(args.report_path).resolve()

    provider, llm_config = _load_provider(args.provider, args.llm_max_tokens, args.llm_timeout)
    llm_client = MeteredM2LLMClient(provider, llm_config)
    command = _command_line()

    _reset_dir(work_root)
    positive_dir = work_root / "positive_2310_08800v2"
    positive = _run_positive(input_dir, positive_dir, llm_client)
    positive_usage = dict(llm_client.usage.as_dict())

    negative_inputs_root = work_root / "negative_inputs"
    negative_inputs_root.mkdir(parents=True, exist_ok=True)
    negatives = [
        _run_negative(
            name="missing_canonical",
            input_dir=_make_missing_canonical_input(negative_inputs_root),
            output_dir=work_root / "negative_missing_canonical",
            llm_client=llm_client,
            expected_reason="MISSING_CANONICAL_INPUT",
        ),
        _run_negative(
            name="m2_ready_false",
            input_dir=_make_m2_not_ready_input(input_dir, negative_inputs_root / "m2_ready_false"),
            output_dir=work_root / "negative_m2_ready_false",
            llm_client=llm_client,
            expected_reason="M1_M2_NOT_READY",
        ),
        _run_negative(
            name="missing_method_evidence",
            input_dir=_make_missing_method_input(input_dir, negative_inputs_root / "missing_method_evidence"),
            output_dir=work_root / "negative_missing_method_evidence",
            llm_client=llm_client,
            expected_reason="MISSING_METHOD_EVIDENCE",
        ),
    ]

    acceptance = _evaluate_acceptance(positive, negatives)
    report = _render_report(
        command=command,
        input_dir=input_dir,
        report_path=report_path,
        provider=provider,
        positive=positive,
        positive_usage=positive_usage,
        total_usage=llm_client.usage.as_dict(),
        negatives=negatives,
        acceptance=acceptance,
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")

    artifact_list = ", ".join(positive["artifact_names"])
    usage = llm_client.usage.as_dict()
    print(f"paper_id: {positive['paper_id']}")
    print(f"input_path: {input_dir}")
    print(f"run_dir: {positive_dir}")
    print(f"status: {positive['status']}")
    print(f"LLM calls: {usage['call_count']}")
    print(f"tokens: {usage['total_tokens']}")
    print(f"artifacts: {artifact_list}")
    print(f"report_path: {report_path}")

    return 0 if acceptance["passed"] else 2


def _run_positive(
    input_dir: Path,
    output_dir: Path,
    llm_client: MeteredM2LLMClient,
) -> dict[str, Any]:
    result = run_m2_full_pipeline(
        input_dir=input_dir,
        output_dir=output_dir,
        llm_client=llm_client,
        llm_metadata={"provider": llm_client.provider.name, "model": llm_client.provider.model},
    )
    loaded = _load_run(output_dir)
    checks = _positive_checks(output_dir, loaded)
    return {
        **loaded,
        "paper_id": result.paper_id,
        "output_dir": str(output_dir),
        "status": result.status.status,
        "blocking_reason": result.status.blocking_reason,
        "checks": checks,
    }


def _run_negative(
    *,
    name: str,
    input_dir: Path,
    output_dir: Path,
    llm_client: MeteredM2LLMClient,
    expected_reason: str,
) -> dict[str, Any]:
    before_calls = llm_client.usage.call_count
    result = run_m2_full_pipeline(
        input_dir=input_dir,
        output_dir=output_dir,
        llm_client=llm_client,
        llm_metadata={"provider": llm_client.provider.name, "model": llm_client.provider.model},
    )
    status_data = _read_json(output_dir / "understanding_status.json")
    artifacts = sorted(path.name for path in output_dir.iterdir() if path.is_file())
    card_files = [name for name in CARD_ARTIFACTS if (output_dir / name).exists()]
    return {
        "name": name,
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "status": result.status.status,
        "blocking_reason": result.status.blocking_reason,
        "expected_reason": expected_reason,
        "card_files": card_files,
        "artifact_names": artifacts,
        "status_data": status_data,
        "llm_calls_delta": llm_client.usage.call_count - before_calls,
        "passed": (
            result.status.status == "BLOCKED_UNDERSTANDING"
            and result.status.blocking_reason == expected_reason
            and not card_files
        ),
    }


def _positive_checks(output_dir: Path, loaded: dict[str, Any]) -> dict[str, Any]:
    missing_artifacts = [
        name for name in POSITIVE_REQUIRED_ARTIFACTS
        if not (output_dir / name).exists()
    ]
    invalid_refs = _invalid_card_refs(loaded)
    formula_coverage = _formula_coverage(loaded)
    quality_findings = loaded["quality_report"].get("findings", [])
    block_findings = [finding for finding in quality_findings if finding.get("effect") == "BLOCK"]
    quality_judgment = _quality_judgment(loaded, formula_coverage, invalid_refs, block_findings)
    component_status = loaded["understanding_status"].get("component_status", {})
    allowed_downstream = loaded["understanding_status"].get("allowed_downstream", {})
    return {
        "missing_artifacts": missing_artifacts,
        "invalid_refs": invalid_refs,
        "formula_coverage": formula_coverage,
        "block_findings": block_findings,
        "warning_findings": [finding for finding in quality_findings if finding.get("effect") == "WARNING"],
        "quality_judgment": quality_judgment,
        "component_status": component_status,
        "allowed_downstream": allowed_downstream,
        "m2_ready": loaded["canonical_status"].get("m2_ready"),
        "canonicalization_status": loaded["canonical_status"].get("canonicalization_status"),
        "checked_artifacts": loaded["understanding_status"].get("checked_artifacts", []),
    }


def _evaluate_acceptance(positive: dict[str, Any], negatives: list[dict[str, Any]]) -> dict[str, Any]:
    checks = positive["checks"]
    positive_ok = (
        positive["status"] in ACCEPTED_POSITIVE_STATUSES
        and not checks["missing_artifacts"]
        and not checks["invalid_refs"]
        and checks["formula_coverage"]["status"] == "PASS"
        and not checks["block_findings"]
        and checks["quality_judgment"]["passed"]
    )
    negative_ok = all(item["passed"] for item in negatives)
    reasons: list[str] = []
    if positive["status"] not in ACCEPTED_POSITIVE_STATUSES:
        reasons.append(f"positive status is {positive['status']}")
    if checks["missing_artifacts"]:
        reasons.append(f"missing artifacts: {checks['missing_artifacts']}")
    if checks["invalid_refs"]:
        reasons.append(f"invalid evidence refs: {checks['invalid_refs'][:5]}")
    if checks["formula_coverage"]["status"] != "PASS":
        reasons.append(f"formula coverage: {checks['formula_coverage']}")
    if checks["block_findings"]:
        reasons.append(f"quality BLOCK findings: {checks['block_findings']}")
    if not checks["quality_judgment"]["passed"]:
        reasons.append(f"quality judgment failed: {checks['quality_judgment']['issues']}")
    failed_negatives = [item["name"] for item in negatives if not item["passed"]]
    if failed_negatives:
        reasons.append(f"negative gates failed: {failed_negatives}")
    return {
        "passed": positive_ok and negative_ok,
        "positive_ok": positive_ok,
        "negative_ok": negative_ok,
        "reasons": reasons,
        "m2_real_e2e_verdict": (
            "NO_BROAD_REAL_E2E_VERIFIED_SELECTED_PAPER_ONLY"
            if positive_ok and negative_ok
            else "NO"
        ),
        "status_wording_allowed": (
            "M2 selected-paper live acceptance passed"
            if positive_ok and negative_ok
            else "M2 NOT_REAL_E2E_VERIFIED"
        ),
    }


def _quality_judgment(
    loaded: dict[str, Any],
    formula_coverage: dict[str, Any],
    invalid_refs: list[dict[str, str]],
    block_findings: list[dict[str, Any]],
) -> dict[str, Any]:
    paper_card = loaded.get("paper_card", {})
    formula_cards = loaded.get("formula_cards", {}).get("formula_cards", [])
    teaching_cards = loaded.get("teaching_cards", {}).get("teaching_cards", [])
    issues: list[str] = []

    core_fields = ["problem", "core_idea", "method_overview", "experiment_summary"]
    core_texts = {
        field: str((paper_card.get(field) or {}).get("text") or "")
        for field in core_fields
    }
    for field, text in core_texts.items():
        if not text or text in {"UNKNOWN", "INSUFFICIENT_EVIDENCE"}:
            issues.append(f"paper_card.{field} is not explanatory")

    combined_paper_text = " ".join([paper_card.get("title", ""), paper_card.get("one_sentence_summary", ""), *core_texts.values()]).lower()
    specific_terms = ["ddmt", "diffusion", "mask", "transformer", "anomaly", "time series"]
    if sum(1 for term in specific_terms if term in combined_paper_text) < 3:
        issues.append("paper_card lacks DDMT-specific terminology")

    if not formula_cards:
        issues.append("formula_cards is empty")
    if formula_coverage["status"] != "PASS":
        issues.append("formula coverage is not PASS")
    for index, card in enumerate(formula_cards):
        if not str(card.get("purpose") or "").strip() or card.get("purpose") == "UNKNOWN":
            issues.append(f"formula_cards[{index}].purpose is empty")
        if not str(card.get("formula_origin") or "").strip():
            issues.append(f"formula_cards[{index}].formula_origin is empty")
        if not str(card.get("formula_ocr_status") or "").strip():
            issues.append(f"formula_cards[{index}].formula_ocr_status is empty")

    if not teaching_cards:
        issues.append("teaching_cards is empty")
    for index, card in enumerate(teaching_cards):
        if not str(card.get("human_explanation") or "").strip() or card.get("human_explanation") == "UNKNOWN":
            issues.append(f"teaching_cards[{index}].human_explanation is empty")
        if not card.get("evidence_refs"):
            issues.append(f"teaching_cards[{index}] has no evidence_refs")

    if invalid_refs:
        issues.append("one or more card evidence_refs are invalid")
    if block_findings:
        issues.append("QualityAuditor produced BLOCK findings")

    origins = Counter(str(card.get("formula_origin") or "unknown") for card in formula_cards)
    coverage_statuses = Counter(str(card.get("coverage_status") or "") for card in formula_cards)
    derivation_statuses = Counter(str(card.get("derivation_status") or "") for card in formula_cards)

    return {
        "passed": not issues,
        "issues": issues,
        "paper_card_summary": {
            "title": paper_card.get("title", ""),
            "one_sentence_summary": paper_card.get("one_sentence_summary", ""),
            "problem": core_texts["problem"],
            "method_overview": core_texts["method_overview"],
            "experiment_summary": core_texts["experiment_summary"],
        },
        "formula_card_summary": {
            "count": len(formula_cards),
            "origins": dict(origins),
            "coverage_statuses": dict(coverage_statuses),
            "derivation_statuses": dict(derivation_statuses),
        },
        "teaching_card_summary": {
            "count": len(teaching_cards),
            "titles": [str(card.get("title") or "") for card in teaching_cards],
        },
    }


def _invalid_card_refs(loaded: dict[str, Any]) -> list[dict[str, str]]:
    valid_refs = _valid_refs(loaded)
    invalid: list[dict[str, str]] = []
    for artifact_name in ["paper_card", "formula_cards", "teaching_cards"]:
        for path, ref in _collect_evidence_refs(loaded.get(artifact_name), artifact_name):
            if ref and ref not in valid_refs:
                invalid.append({"path": path, "evidence_ref": ref})
    return invalid


def _valid_refs(loaded: dict[str, Any]) -> set[str]:
    refs: set[str] = set()
    for claim in loaded["claim_evidence"].get("claims", []):
        ref = str(claim.get("evidence_ref") or "")
        if ref:
            refs.add(ref)
    for claim in loaded["evidence_index"].get("claims", []):
        ref = str(claim.get("evidence_ref") or "")
        if ref:
            refs.add(ref)
    for passage in loaded["passage_index"].get("passages", []):
        for ref in passage.get("evidence_refs", []):
            if ref:
                refs.add(str(ref))
    return refs


def _collect_evidence_refs(obj: Any, path: str) -> list[tuple[str, str]]:
    refs: list[tuple[str, str]] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            child_path = f"{path}.{key}" if path else key
            if key == "evidence_ref" and isinstance(value, str) and value:
                refs.append((child_path, value))
            elif key == "evidence_refs" and isinstance(value, list):
                for index, ref in enumerate(value):
                    if isinstance(ref, str) and ref:
                        refs.append((f"{child_path}[{index}]", ref))
            else:
                refs.extend(_collect_evidence_refs(value, child_path))
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            refs.extend(_collect_evidence_refs(value, f"{path}[{index}]"))
    return refs


def _formula_coverage(loaded: dict[str, Any]) -> dict[str, Any]:
    formula_items = [
        item for item in loaded.get("formula_evidence_pack", {}).get("items", [])
        if item.get("claim_type") == "FORMULA_CONTEXT" and item.get("evidence_ref")
    ]
    expected_refs = {str(item["evidence_ref"]) for item in formula_items}
    actual_refs = {
        str(card.get("evidence_ref"))
        for card in loaded.get("formula_cards", {}).get("formula_cards", [])
        if card.get("evidence_ref")
    }
    missing_refs = sorted(expected_refs - actual_refs)
    extra_refs = sorted(actual_refs - expected_refs)
    return {
        "expected_count": len(expected_refs),
        "covered_count": len(expected_refs) - len(missing_refs),
        "actual_count": len(actual_refs),
        "missing_refs": missing_refs,
        "extra_refs": extra_refs,
        "status": "PASS" if not missing_refs and not extra_refs else "FAIL",
    }


def _load_run(output_dir: Path) -> dict[str, Any]:
    data: dict[str, Any] = {
        "artifact_names": sorted(path.name for path in output_dir.iterdir() if path.is_file()),
    }
    for name in POSITIVE_REQUIRED_ARTIFACTS:
        path = output_dir / name
        key = name.replace(".json", "").replace(".md", "")
        if path.exists() and name.endswith(".json"):
            data[key] = _read_json(path)
    data.setdefault("source_status", {})
    data.setdefault("canonical_status", {})
    data.setdefault("parsed_document", {})
    data.setdefault("passage_index", {"passages": []})
    data.setdefault("claim_evidence", {"claims": []})
    data.setdefault("evidence_index", {"claims": []})
    data.setdefault("paper_skeleton", {})
    data.setdefault("evidence_pack", {"items": []})
    data.setdefault("formula_evidence_pack", {"items": []})
    data.setdefault("paper_card", {})
    data.setdefault("formula_cards", {"formula_cards": []})
    data.setdefault("teaching_cards", {"teaching_cards": []})
    data.setdefault("quality_report", {"findings": []})
    data.setdefault("understanding_status", {"status": "UNKNOWN"})
    data.setdefault("m2_run_summary", {})
    return data


def _make_missing_canonical_input(root: Path) -> Path:
    path = root / "missing_canonical"
    _reset_dir(path)
    return path


def _make_m2_not_ready_input(source: Path, target: Path) -> Path:
    _copy_bundle(source, target)
    canonical = target / "canonical_paper.md"
    text = canonical.read_text(encoding="utf-8")
    if "m2_ready: true" not in text:
        raise RuntimeError("Expected m2_ready: true in canonical_paper.md")
    canonical.write_text(text.replace("m2_ready: true", "m2_ready: false", 1), encoding="utf-8")
    return target


def _make_missing_method_input(source: Path, target: Path) -> Path:
    _copy_bundle(source, target)
    blocks_path = target / "document_blocks.json"
    blocks = _read_json(blocks_path)
    retained = [
        block for block in blocks
        if _is_intro_or_abstract_claim_block(block)
    ]
    if not retained:
        retained = [
            block for block in blocks
            if str(block.get("section") or "").strip().lower() in {"abstract", "introduction", "intro"}
            and str(block.get("block_type") or "").strip().lower() == "text"
        ][:8]
    if not retained:
        raise RuntimeError("Could not derive a non-method failure input from real document_blocks.json")
    blocks_path.write_text(json.dumps(retained, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def _is_intro_or_abstract_claim_block(block: dict[str, Any]) -> bool:
    section = str(block.get("section") or "").strip().lower()
    block_type = str(block.get("block_type") or "").strip().lower()
    text = str(block.get("text") or "").strip().lower()
    if section not in {"abstract", "introduction", "intro"} or block_type != "text":
        return False
    if len(text) < 80:
        return False
    terms = ["propose", "present", "introduce", "develop", "contribut", "problem", "challenge", "difficult", "limitation"]
    return any(term in text for term in terms)


def _copy_bundle(source: Path, target: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)


def _load_provider(
    provider_name: str,
    max_tokens: int,
    timeout: float,
) -> tuple[ModelProviderConfig, LLMConfig]:
    config = ConfigService().load()
    resolved_name = provider_name or config.active_provider
    if resolved_name not in config.providers:
        raise SystemExit(f"ERROR: unknown provider '{resolved_name}'")
    provider = config.providers[resolved_name]
    if not os.getenv(provider.api_key_env, ""):
        raise SystemExit(f"ERROR: {provider.missing_api_key_message()}")
    llm_config = LLMConfig(
        temperature=0.2,
        max_tokens=max_tokens,
        json_mode=True,
        timeout=timeout or float(provider.timeout_seconds or 60),
        max_retries=0,
    )
    return provider, llm_config


def _render_report(
    *,
    command: str,
    input_dir: Path,
    report_path: Path,
    provider: ModelProviderConfig,
    positive: dict[str, Any],
    positive_usage: dict[str, Any],
    total_usage: dict[str, Any],
    negatives: list[dict[str, Any]],
    acceptance: dict[str, Any],
) -> str:
    checks = positive["checks"]
    quality = checks["quality_judgment"]
    findings = positive["quality_report"].get("findings", [])
    finding_lines = [
        f"- {f.get('code')}: {f.get('effect')} {f.get('message')}"
        for f in findings
    ] or ["- none"]
    negative_lines = [
        (
            f"- {item['name']}: status={item['status']}, "
            f"blocking_reason={item['blocking_reason']}, "
            f"expected={item['expected_reason']}, card_files={item['card_files'] or 'none'}, "
            f"llm_calls_delta={item['llm_calls_delta']}, passed={item['passed']}"
        )
        for item in negatives
    ]
    artifact_lines = [f"- {name}" for name in positive["artifact_names"]]
    evidence_line = (
        "PASS"
        if not checks["invalid_refs"]
        else f"FAIL: {checks['invalid_refs'][:10]}"
    )
    formula = checks["formula_coverage"]
    status_data = positive["understanding_status"]
    summary = positive["m2_run_summary"]
    report_lines = [
        "# M2 Live Acceptance",
        "",
        f"- test_time_utc: {datetime.now(timezone.utc).isoformat()}",
        f"- commit_sha: {_git_commit_sha()}",
        f"- project_venv: {_is_project_venv()}",
        f"- python: {sys.executable}",
        f"- model_provider: {provider.name}",
        f"- model: {provider.model}",
        f"- paper_id: {positive['paper_id']}",
        f"- input_dir: {input_dir}",
        f"- report_path: {report_path}",
        f"- command: `{command}`",
        "",
        "## LLM Usage",
        "",
        f"- positive_calls: {positive_usage.get('call_count', 0)}",
        f"- positive_tokens: {positive_usage.get('total_tokens', 0)}",
        f"- total_calls_including_negative_preflights: {total_usage.get('call_count', 0)}",
        f"- total_tokens: {total_usage.get('total_tokens', 0)}",
        f"- latencies_ms: {total_usage.get('latencies_ms', [])}",
        "",
        "## Positive Sample",
        "",
        f"- status: {positive['status']}",
        f"- blocking_reason: {positive['blocking_reason'] or 'none'}",
        f"- source_type: {positive['source_status'].get('source_type')}",
        f"- canonicalization_status: {checks['canonicalization_status']}",
        f"- m2_ready: {checks['m2_ready']}",
        f"- component_status: {checks['component_status']}",
        f"- allowed_downstream: {checks['allowed_downstream']}",
        f"- checked_artifacts: {checks['checked_artifacts']}",
        f"- output_artifact_count: {len(positive['artifact_names'])}",
        f"- summary_formula_card_coverage: {summary.get('formula_card_coverage')}",
        "",
        "## Failure Samples",
        "",
        *negative_lines,
        "",
        "## Artifact List",
        "",
        *artifact_lines,
        "",
        "## Evidence Refs",
        "",
        f"- status: {evidence_line}",
        f"- valid_ref_count: {len(_valid_refs(positive))}",
        "",
        "## Formula Coverage",
        "",
        f"- status: {formula['status']}",
        f"- expected_count: {formula['expected_count']}",
        f"- covered_count: {formula['covered_count']}",
        f"- actual_count: {formula['actual_count']}",
        f"- missing_refs: {formula['missing_refs']}",
        f"- extra_refs: {formula['extra_refs']}",
        "",
        "## QualityAuditor Findings",
        "",
        *finding_lines,
        "",
        "## Card Quality Judgment",
        "",
        f"- paper_card_passed: {not any(issue.startswith('paper_card') for issue in quality['issues'])}",
        f"- paper_card_summary: {quality['paper_card_summary']}",
        f"- formula_cards_passed: {not any(issue.startswith('formula') for issue in quality['issues'])}",
        f"- formula_card_summary: {quality['formula_card_summary']}",
        f"- teaching_cards_passed: {not any(issue.startswith('teaching') for issue in quality['issues'])}",
        f"- teaching_card_summary: {quality['teaching_card_summary']}",
        f"- quality_issues: {quality['issues'] or 'none'}",
        "",
        "## M2 Status Decision",
        "",
        f"- acceptance_passed: {acceptance['passed']}",
        f"- positive_ok: {acceptance['positive_ok']}",
        f"- negative_ok: {acceptance['negative_ok']}",
        f"- reasons: {acceptance['reasons'] or 'none'}",
        f"- allow_broad_REAL_E2E_VERIFIED: {acceptance['m2_real_e2e_verdict']}",
        f"- status_wording_allowed: {acceptance['status_wording_allowed']}",
        "",
        "## Remaining Issues",
        "",
        "- This is selected-paper live acceptance, not broad M2 completion.",
        "- Multi-paper acceptance remains pending.",
        "- Survey PDF live acceptance remains pending.",
        "- Formula derivation quality remains bounded by M1 LaTeX fidelity and nearby evidence.",
        "- QualityAuditor is deterministic and evidence-gate oriented; it does not prove full semantic correctness.",
    ]
    if status_data.get("status") in {"BASELINE_ONLY", "BLOCKED_UNDERSTANDING"}:
        report_lines.append("- Positive sample is not user-facing; M2 must remain NOT_REAL_E2E_VERIFIED.")
    return "\n".join(report_lines) + "\n"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _reset_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _command_line() -> str:
    return " ".join([str(Path(sys.executable).resolve()), *sys.argv])


def _git_commit_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return result.stdout.strip()
    except Exception as exc:  # pragma: no cover - diagnostic only
        return f"UNKNOWN ({exc})"


def _is_project_venv() -> bool:
    executable = Path(sys.executable).resolve()
    venv_root = (ROOT / ".venv").resolve()
    return venv_root in executable.parents


if __name__ == "__main__":
    raise SystemExit(main())
