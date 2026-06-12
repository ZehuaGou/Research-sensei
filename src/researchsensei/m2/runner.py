from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from researchsensei.m2.artifact_reader import M1ArtifactBundle, M1ArtifactReader
from researchsensei.m2.schemas import (
    M2FormulaUnderstanding,
    M2FormulaUnderstandingBundle,
    M2RunResult,
    M2SourceTrace,
    RoleGuess,
)


def run_m2_understanding(
    *,
    input_dir: str | Path,
    output_dir: str | Path,
) -> M2RunResult:
    """Run deterministic M2 paper/formula understanding from M1 artifacts."""
    reader = M1ArtifactReader(input_dir)
    bundle = reader.load()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    formulas = build_formula_understanding(bundle)
    paper_id = str(bundle.front_matter.get("paper_id") or bundle.paper_metadata.get("paper_id") or bundle.input_dir.name)
    title = str(bundle.front_matter.get("title") or bundle.paper_metadata.get("title") or paper_id)
    formula_bundle = M2FormulaUnderstandingBundle(
        paper_id=paper_id,
        title=title,
        formulas=formulas,
        skipped_formula_count=sum(1 for formula in formulas if formula.plain_language_explanation.startswith("Skipped:")),
        used_group_info=any(formula.equation_group_id for formula in formulas),
    )
    method_graph = build_method_graph(bundle, formulas)
    source_trace = {
        "paper_id": paper_id,
        "source_artifacts_read": [
            "canonical_paper.md",
            "document_blocks.json",
            "formula_slots.json",
            "formula_slots.md",
            "paper_metadata.json",
            "quality_report.md",
            "performance_report.json",
            "visual_audit/",
        ],
        "formula_traces": {formula.formula_id: formula.source_trace.model_dump(mode="json") for formula in formulas},
    }
    risk_report = render_risk_report(bundle, formula_bundle)
    paper_markdown = render_paper_understanding(bundle, formula_bundle, method_graph)

    current_hashes = reader.hash_required_inputs()
    output_artifacts = [
        "m2_paper_understanding.md",
        "m2_formula_understanding.json",
        "m2_formula_understanding.md",
        "m2_method_graph.json",
        "m2_source_trace.json",
        "m2_risk_report.md",
        "m2_run_summary.json",
    ]
    run_summary = {
        "paper_id": paper_id,
        "title": title,
        "input_dir": _display_path(bundle.input_dir),
        "output_dir": _display_path(output_dir),
        "input_contract": bundle.contract,
        "formula_count": len(formulas),
        "skipped_formula_count": formula_bundle.skipped_formula_count,
        "used_group_info": formula_bundle.used_group_info,
        "m1_artifacts_modified": current_hashes != bundle.input_hashes,
        "input_artifacts_read": source_trace["source_artifacts_read"],
        "output_artifacts": output_artifacts,
        "m2_ready": bool(bundle.front_matter.get("m2_ready", False)),
        "m2_ready_for_formula_understanding": bool(bundle.front_matter.get("m2_ready_for_formula_understanding", True)),
    }

    (output_dir / "m2_paper_understanding.md").write_text(paper_markdown, encoding="utf-8")
    (output_dir / "m2_formula_understanding.json").write_text(
        json.dumps(formula_bundle.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (output_dir / "m2_formula_understanding.md").write_text(render_formula_markdown(formula_bundle), encoding="utf-8")
    (output_dir / "m2_method_graph.json").write_text(
        json.dumps(method_graph, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (output_dir / "m2_source_trace.json").write_text(
        json.dumps(source_trace, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (output_dir / "m2_risk_report.md").write_text(risk_report, encoding="utf-8")
    (output_dir / "m2_run_summary.json").write_text(
        json.dumps(run_summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return M2RunResult(
        paper_understanding_markdown=paper_markdown,
        formula_understanding=formula_bundle,
        method_graph=method_graph,
        source_trace=source_trace,
        risk_report_markdown=risk_report,
        run_summary=run_summary,
    )


def build_formula_understanding(bundle: M1ArtifactBundle) -> list[M2FormulaUnderstanding]:
    block_by_id = {str(block.get("block_id", "")): block for block in bundle.document_blocks}
    canonical_ids = _formula_ids_in_canonical(bundle.canonical_markdown)
    groups: dict[str, list[dict[str, Any]]] = {}
    for slot in bundle.formula_slots:
        group_id = str(slot.get("equation_group_id") or "")
        if group_id:
            groups.setdefault(group_id, []).append(slot)
    for members in groups.values():
        members.sort(key=lambda slot: int(slot.get("group_order") or 0))

    formulas: list[M2FormulaUnderstanding] = []
    global_formula_ready = bool(bundle.front_matter.get("m2_ready_for_formula_understanding", True))
    for slot in bundle.formula_slots:
        formula = _understand_formula_slot(
            slot=slot,
            block=block_by_id.get(str(slot.get("block_id") or ""), {}),
            group_members=groups.get(str(slot.get("equation_group_id") or ""), []),
            global_formula_ready=global_formula_ready,
            canonical_ids=canonical_ids,
        )
        formulas.append(formula)
    return formulas


def _understand_formula_slot(
    *,
    slot: dict[str, Any],
    block: dict[str, Any],
    group_members: list[dict[str, Any]],
    global_formula_ready: bool,
    canonical_ids: set[str],
) -> M2FormulaUnderstanding:
    formula_id = str(slot.get("formula_id") or "")
    latex = str(slot.get("final_latex") or "")
    risks = [str(item) for item in slot.get("risk_flags", [])]
    slot_ready = slot.get("m2_ready")
    formula_ready = global_formula_ready and (slot_ready is not False) and bool(latex.strip())
    if not formula_ready and "M1_FORMULA_NOT_READY" not in risks:
        risks.append("M1_FORMULA_NOT_READY")

    nearby_text = _nearby_text(slot)
    group_context = _group_context(slot, group_members)
    role = _guess_role(latex, nearby_text) if formula_ready else "unknown"
    explanation = _plain_explanation(role, latex, nearby_text, formula_ready)
    context = _upstream_downstream_context(slot, group_members, formula_ready)
    confidence = _confidence(formula_ready=formula_ready, nearby_text=nearby_text, risks=risks, group_members=group_members)
    source_trace = _source_trace(slot, block, canonical_ids)

    return M2FormulaUnderstanding(
        formula_id=formula_id,
        equation_group_id=str(slot.get("equation_group_id") or ""),
        equation_number=_int_or_none(slot.get("equation_number")),
        page=int(slot.get("page") or 0),
        section=str(slot.get("section") or ""),
        final_latex=latex,
        nearby_text_used=nearby_text,
        group_context_used=group_context,
        role_guess=role,
        plain_language_explanation=explanation,
        upstream_downstream_context=context,
        confidence=confidence,
        risk_flags=risks,
        source_trace=source_trace,
    )


def _nearby_text(slot: dict[str, Any]) -> str:
    before = str(slot.get("nearby_text_before") or "").strip()
    after = str(slot.get("nearby_text_after") or "").strip()
    text = " ".join(part for part in [before, after] if part).strip()
    return text[:1000] if text else "unknown"


def _group_context(slot: dict[str, Any], group_members: list[dict[str, Any]]) -> str:
    group_id = str(slot.get("equation_group_id") or "")
    if not group_id:
        return "standalone"
    member_bits = []
    for member in group_members:
        member_bits.append(f"{member.get('formula_id')}[{member.get('group_order')}]: {member.get('final_latex', '')}")
    group_crop_path = str(slot.get("group_crop_path") or "")
    return f"group_id={group_id}; group_crop_path={group_crop_path}; members=" + " || ".join(member_bits)


def _guess_role(latex: str, nearby_text: str) -> RoleGuess:
    text = f"{latex} {nearby_text}".lower()
    if "attention" in text or "softmax" in text and "q" in text and "k" in text and "v" in text:
        return "attention computation"
    if "anomaly" in text and "score" in text or "assdis" in text:
        return "anomaly score"
    if "contrast" in text or "infonce" in text:
        return "contrastive objective"
    if "reconstruct" in text or r"\hat" in latex or "x-" in text:
        return "reconstruction objective"
    if "loss" in text or r"\mathcal{l}" in text or r"\min" in text:
        return "loss function"
    if "regular" in text or "penalty" in text:
        return "regularization"
    if "bound" in text or "elbo" in text:
        return "bound/derivation"
    if "metric" in text or "accuracy" in text or "auc" in text:
        return "metric"
    return "definition"


def _plain_explanation(role: RoleGuess, latex: str, nearby_text: str, formula_ready: bool) -> str:
    if not formula_ready:
        return "Skipped: M1 marked this formula as not ready for formula understanding or did not provide final_latex."
    evidence = nearby_text if nearby_text != "unknown" else "nearby_text is unknown"
    if role == "attention computation":
        return f"Uses the formula text and nearby evidence to identify an attention computation. Evidence: {evidence}"
    if role == "loss function":
        return f"Uses the formula text and nearby evidence to identify a training loss. Evidence: {evidence}"
    if role == "reconstruction objective":
        return f"Uses the formula text and nearby evidence to identify a reconstruction objective. Evidence: {evidence}"
    if role == "anomaly score":
        return f"Uses the formula text and nearby evidence to identify an anomaly score. Evidence: {evidence}"
    return f"Formula role is inferred as {role} from final_latex and nearby M1 text. Evidence: {evidence}; latex: {latex[:160]}"


def _upstream_downstream_context(
    slot: dict[str, Any],
    group_members: list[dict[str, Any]],
    formula_ready: bool,
) -> str:
    if not formula_ready:
        return "unknown"
    before = str(slot.get("nearby_text_before") or "").strip()
    after = str(slot.get("nearby_text_after") or "").strip()
    group_note = ""
    if group_members:
        ids = ", ".join(str(member.get("formula_id")) for member in group_members)
        group_note = f" Group members considered together: {ids}."
    context = f"Upstream: {before or 'unknown'} Downstream: {after or 'unknown'}{group_note}".strip()
    return context[:1200]


def _confidence(
    *,
    formula_ready: bool,
    nearby_text: str,
    risks: list[str],
    group_members: list[dict[str, Any]],
) -> float:
    if not formula_ready:
        return 0.2
    confidence = 0.74
    if nearby_text == "unknown":
        confidence -= 0.18
    if group_members:
        confidence += 0.04
    if any("crop" in risk.lower() or "group" in risk.lower() for risk in risks):
        confidence -= 0.22
    if any("source" in risk.lower() or "mismatch" in risk.lower() for risk in risks):
        confidence -= 0.25
    return round(max(0.1, min(0.9, confidence)), 2)


def _source_trace(slot: dict[str, Any], block: dict[str, Any], canonical_ids: set[str]) -> M2SourceTrace:
    return M2SourceTrace(
        formula_id=str(slot.get("formula_id") or ""),
        block_id=str(slot.get("block_id") or ""),
        source_artifacts=["formula_slots.json", "document_blocks.json", "canonical_paper.md"],
        immutable_fields={
            "page": int(slot.get("page") or 0),
            "bbox": slot.get("bbox") or block.get("bbox") or [],
            "final_latex": str(slot.get("final_latex") or ""),
            "final_origin": str(slot.get("final_origin") or ""),
            "block_source": str(slot.get("block_source") or block.get("source") or ""),
            "crop_path": str(slot.get("crop_path") or ""),
            "overlay_path": str(slot.get("overlay_path") or ""),
            "group_crop_path": str(slot.get("group_crop_path") or ""),
        },
        nearby_block_ids=[str(item) for item in slot.get("nearby_block_ids", [])],
        canonical_comment_present=str(slot.get("formula_id") or "") in canonical_ids,
    )


def build_method_graph(bundle: M1ArtifactBundle, formulas: list[M2FormulaUnderstanding]) -> dict[str, Any]:
    sections = sorted({str(block.get("section") or "Unknown") for block in bundle.document_blocks})
    nodes = [{"id": f"section:{section}", "type": "section", "label": section} for section in sections]
    edges: list[dict[str, str]] = []
    for formula in formulas:
        nodes.append({"id": f"formula:{formula.formula_id}", "type": "formula", "label": formula.formula_id, "role": formula.role_guess})
        edges.append({"source": f"section:{formula.section or 'Unknown'}", "target": f"formula:{formula.formula_id}", "type": "contains"})
        if formula.equation_group_id:
            group_node = f"group:{formula.equation_group_id}"
            if not any(node["id"] == group_node for node in nodes):
                nodes.append({"id": group_node, "type": "equation_group", "label": formula.equation_group_id})
            edges.append({"source": group_node, "target": f"formula:{formula.formula_id}", "type": "groups"})
    return {"nodes": nodes, "edges": edges}


def render_paper_understanding(
    bundle: M1ArtifactBundle,
    formulas: M2FormulaUnderstandingBundle,
    method_graph: dict[str, Any],
) -> str:
    paper_id = formulas.paper_id
    title = formulas.title
    intro = _section_excerpt(bundle.document_blocks, "Introduction") or _section_excerpt(bundle.document_blocks, "Abstract")
    method = _section_excerpt(bundle.document_blocks, "Method")
    experiments = _section_excerpt(bundle.document_blocks, "Experiments")
    formula_lines = [
        f"- {formula.formula_id}: {formula.role_guess}, section={formula.section}, group={formula.equation_group_id or 'standalone'}, confidence={formula.confidence}"
        for formula in formulas.formulas
    ]
    mapping_lines = [
        f"- {formula.formula_id} -> {formula.section or 'Unknown'} / {formula.role_guess}"
        for formula in formulas.formulas
    ]
    return "\n".join(
        [
            "# M2 Paper Understanding",
            "",
            "## Paper",
            "",
            f"- paper_id: {paper_id}",
            f"- title: {title}",
            f"- primary_parser: {bundle.front_matter.get('primary_parser', 'unknown')}",
            "",
            "## Research Problem",
            "",
            intro or "unknown",
            "",
            "## Method Overview",
            "",
            method or "unknown",
            "",
            "## Module Structure",
            "",
            "\n".join(f"- {node['id']}" for node in method_graph.get("nodes", []) if node.get("type") in {"section", "equation_group"}),
            "",
            "## Key Formulas",
            "",
            "\n".join(formula_lines) if formula_lines else "unknown",
            "",
            "## Formula To Method Mapping",
            "",
            "\n".join(mapping_lines) if mapping_lines else "unknown",
            "",
            "## Experiments Summary",
            "",
            experiments or "unknown",
            "",
            "## Main Uncertainties",
            "",
            "- Rule-based M2 does not infer claims that are absent from M1 nearby_text.",
            "- Crop/group risk flags lower confidence instead of being hidden.",
            "- Performance gate WARNING from M1 remains a known risk, not a PASS.",
            "",
            "## M1 Evidence And M2 Inference Boundary",
            "",
            "M2 reads only M1 artifacts and treats page, bbox, latex, parser source, crop path, overlay path, and source identity as immutable evidence. Explanations are role guesses from final_latex plus nearby_text, not new parser output.",
        ]
    )


def render_formula_markdown(bundle: M2FormulaUnderstandingBundle) -> str:
    lines = ["# M2 Formula Understanding", "", f"paper_id: {bundle.paper_id}", ""]
    for formula in bundle.formulas:
        lines.extend(
            [
                f"## {formula.formula_id}",
                "",
                f"- equation_group_id: {formula.equation_group_id or 'standalone'}",
                f"- equation_number: {formula.equation_number if formula.equation_number is not None else 'unknown'}",
                f"- page: {formula.page}",
                f"- section: {formula.section}",
                f"- role_guess: {formula.role_guess}",
                f"- confidence: {formula.confidence}",
                f"- risk_flags: {', '.join(formula.risk_flags) if formula.risk_flags else 'none'}",
                "",
                "```latex",
                formula.final_latex,
                "```",
                "",
                formula.plain_language_explanation,
                "",
            ]
        )
    return "\n".join(lines)


def render_risk_report(bundle: M1ArtifactBundle, formulas: M2FormulaUnderstandingBundle) -> str:
    perf_warning = bool(bundle.performance_report.get("warnings")) or bundle.performance_report.get("perf_pass") is False
    risky = [formula for formula in formulas.formulas if formula.risk_flags]
    return "\n".join(
        [
            "# M2 Risk Report",
            "",
            f"- M1 contract status: {bundle.contract.get('status')}",
            f"- M1 quality: {bundle.front_matter.get('canonical_quality_status', 'unknown')}",
            f"- M1 m2_ready: {bundle.front_matter.get('m2_ready', False)}",
            f"- M1 formula understanding ready: {bundle.front_matter.get('m2_ready_for_formula_understanding', True)}",
            f"- Performance gate: {'WARNING' if perf_warning else 'PASS'}",
            f"- Formula count: {len(formulas.formulas)}",
            f"- Skipped formulas: {formulas.skipped_formula_count}",
            f"- Formulas with risk flags: {len(risky)}",
            "",
            "## Risk Details",
            "",
            "\n".join(f"- {formula.formula_id}: {', '.join(formula.risk_flags)}" for formula in risky) if risky else "- none",
        ]
    )


def _section_excerpt(blocks: list[dict[str, Any]], section: str) -> str:
    pieces = [
        str(block.get("text") or "").strip()
        for block in blocks
        if str(block.get("section") or "").lower() == section.lower()
        and str(block.get("block_type") or "") in {"text", "caption", "title"}
        and str(block.get("text") or "").strip()
    ]
    return " ".join(pieces).strip()[:1200].rstrip()


def _formula_ids_in_canonical(markdown: str) -> set[str]:
    return set(re.findall(r"formula_id:\s*([A-Za-z0-9_\-]+)", markdown))


def _int_or_none(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)
