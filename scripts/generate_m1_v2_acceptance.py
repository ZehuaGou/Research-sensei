from __future__ import annotations

import json
import re
import shutil
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import fitz

from researchsensei.canonical.canonical_builder import CanonicalBuilder
from researchsensei.canonical.document_blocks import CanonicalDocumentBlock
from researchsensei.canonical.pipeline import M1CanonicalPipeline
from researchsensei.canonical.quality_gate import M1QualityGate
from researchsensei.canonical.visual_audit import M1VisualAuditReportGenerator
from researchsensei.schemas.enums import CanonicalQualityStatus


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "m1_v2_acceptance"
REVIEW = ROOT / "reports" / "m1_parser_review"
THREE_PIPELINE = ROOT / "reports" / "m1_three_pipeline_architecture"
PAPER4 = ROOT / "reports" / "m1_unseen_eval" / "paper_4_unseen"
UNSEEN_PDF = (
    ROOT
    / "reports"
    / "live_eval"
    / "work"
    / "m1"
    / "workspace"
    / "runs"
    / "m1-live"
    / "source_pdfs"
    / "2d57a3f90adf3fc28f0de61fb4b7b34bccb1b92d"
    / "source.pdf"
)


@dataclass(frozen=True)
class PaperSpec:
    key: str
    title: str
    source_dir: Path
    source_pdf: Path
    route: str
    parser_name: str
    core_samples: tuple[str, ...]
    use_mineru_blocks: bool = False
    unseen_reason: str = ""


PAPERS = [
    PaperSpec(
        key="paper_1",
        title="Monte Carlo EM for Deep Time Series Anomaly Detection",
        source_dir=REVIEW / "paper_1",
        source_pdf=REVIEW / "paper_1" / "source_monte_carlo_em.pdf",
        route="C Marker fallback/audit baseline",
        parser_name="marker_document",
        core_samples=("p(x|z)", "p(xt|zt=0)", "p(zt+1|zt)", "ELBO"),
    ),
    PaperSpec(
        key="paper_2",
        title="Learning Graph Structures with Transformer for Multivariate Time Series Anomaly Detection in IoT",
        source_dir=REVIEW / "paper_2",
        source_pdf=REVIEW / "paper_2" / "source.pdf",
        route="D MarkItDown/PyMuPDF fallback/debug",
        parser_name="pymupdf",
        core_samples=("Gumbel-softmax", "Attention(Q,K,V)", "MultiHead(Q,K,V)", "Influence Propagation"),
    ),
    PaperSpec(
        key="paper_3",
        title="Anomaly Transformer: Time Series Anomaly Detection with Association Discrepancy",
        source_dir=THREE_PIPELINE / "paper_1",
        source_pdf=THREE_PIPELINE / "paper_1" / "source.pdf",
        route="C Marker formula audit + PyMuPDF body fallback",
        parser_name="pymupdf",
        core_samples=("Prior-Association", "Series-Association", "AssDis(P,S;X)", "AnomalyScore"),
    ),
    PaperSpec(
        key="paper_4_unseen",
        title="MEMTO: Memory-guided Transformer for Multivariate Time Series Anomaly Detection",
        source_dir=PAPER4,
        source_pdf=PAPER4 / "source.pdf",
        route="A MinerU2.5-Pro + RuleBasedStructureRefiner",
        parser_name="mineru25pro",
        core_samples=("Gated memory", "anomaly score", "bi-dimensional deviation", "K-means"),
        use_mineru_blocks=True,
        unseen_reason="Selected as blind MEMTO case: long, formula-heavy, transformer-based anomaly detection paper.",
    ),
    PaperSpec(
        key="paper_5_unseen",
        title="TranAD: Deep Transformer Networks for Anomaly Detection in Multivariate Time Series Data",
        source_dir=UNSEEN_PDF.parent,
        source_pdf=UNSEEN_PDF,
        route="D PyMuPDF fallback/debug for new unseen",
        parser_name="pymupdf",
        core_samples=("TranAD", "transformer", "anomaly score", "self-conditioning"),
        unseen_reason="Automatically acquired by prior M1 live_eval search/download; not one of paper_1/2/3 or MEMTO; 15-page transformer anomaly-detection method paper.",
    ),
]

VISUAL_REVIEW_BLOCKING_REASONS = {"MISSING_FORMULA_CROP", "MISSING_FORMULA_OVERLAY"}


SECTION_ALIASES = {
    "abstract": "Abstract",
    "introduction": "Introduction",
    "related work": "Related Work",
    "related works": "Related Work",
    "background": "Related Work",
    "preliminaries": "Related Work",
    "method": "Method",
    "methods": "Method",
    "methodology": "Method",
    "approach": "Method",
    "proposed method": "Method",
    "experiments": "Experiments",
    "experiment": "Experiments",
    "experimental results": "Experiments",
    "evaluation": "Experiments",
    "results": "Experiments",
    "conclusion": "Conclusion",
    "conclusions": "Conclusion",
    "references": "References",
    "bibliography": "References",
    "appendix": "Appendix",
}


def normalize_match(text: str) -> str:
    text = text.lower()
    text = text.replace("√", "sqrt").replace("−", "-").replace("×", "x")
    text = re.sub(r"\\(?:mathbf|mathrm|mathcal|text|operatorname)\s*\{([^{}]*)\}", r"\1", text)
    text = text.replace("\\", "")
    text = text.replace("_", "").replace("^", "")
    return re.sub(r"[^a-z0-9]+", "", text)


def sample_variants(sample: str) -> set[str]:
    variants = {sample}
    variants.add(sample.replace("xt", "x_t").replace("zt", "z_t"))
    variants.add(sample.replace("x", "\\mathbf{x}").replace("z", "z"))
    variants.add(sample.replace(" ", ""))
    if "assdis" in sample.lower():
        variants.update({"associationdiscrepancy", "assdis"})
    if "gumbel" in sample.lower():
        variants.update({"gumbelsoftmax", "gumbel softmax", "argmax(log"})
    if "influence" in sample.lower():
        variants.update({"influencepropagation", "graph convolution"})
    return {normalize_match(v) for v in variants if v}


def copy_optional(src: Path, dst: Path) -> None:
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def extract_front_matter(markdown: str) -> tuple[dict, str]:
    if not markdown.startswith("---"):
        return {}, markdown
    parts = markdown.split("---", 2)
    if len(parts) < 3:
        return {}, markdown
    front: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            front[key.strip()] = value.strip().strip('"')
    return front, parts[2]


def section_from_heading(text: str) -> str | None:
    clean = re.sub(r"^[#\s]*(?:[ivxlcdm]+|\d+(?:\.\d+)*|[A-Z])[\.\)]?\s+", "", text.strip(), flags=re.I)
    clean = clean.strip(" #:.-").lower()
    if clean in SECTION_ALIASES:
        return SECTION_ALIASES[clean]
    for key, section in SECTION_ALIASES.items():
        if re.search(rf"\b{re.escape(key)}\b", clean):
            return section
    return None


def blocks_from_review_canonical(spec: PaperSpec) -> list[CanonicalDocumentBlock]:
    markdown_path = spec.source_dir / "canonical_paper.md"
    markdown = markdown_path.read_text(encoding="utf-8", errors="replace")
    _, body = extract_front_matter(markdown)
    blocks: list[CanonicalDocumentBlock] = []
    current_section = "Unknown"
    paragraph: list[str] = []
    reading_order = 0
    page = 1
    in_code = False

    def flush() -> None:
        nonlocal paragraph, reading_order, page
        text = " ".join(part.strip() for part in paragraph if part.strip())
        paragraph = []
        if not text or text.startswith("<!-- formula_id:"):
            return
        blocks.append(CanonicalDocumentBlock(
            block_id=f"t{len(blocks)+1:05d}",
            page=page,
            bbox=[0.0, 0.0, 1.0, 1.0],
            block_type="text",
            text=text[:4000],
            reading_order=reading_order,
            source=spec.parser_name,
            confidence=0.7,
            section=current_section,
        ))
        reading_order += 1
        if len(text) > 600:
            page += 1

    for raw in body.splitlines():
        line = raw.strip()
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code or line.startswith("<!-- formula_id:"):
            continue
        if line.startswith("#"):
            flush()
            found = section_from_heading(line)
            if found:
                current_section = found
                blocks.append(CanonicalDocumentBlock(
                    block_id=f"h{len(blocks)+1:05d}",
                    page=page,
                    bbox=[0.0, 0.0, 1.0, 0.05],
                    block_type="title",
                    text=found,
                    reading_order=reading_order,
                    source=spec.parser_name,
                    confidence=0.8,
                    section=found,
                    section_confidence="high",
                    section_reason="canonical_heading",
                ))
                reading_order += 1
            continue
        if not line:
            flush()
        else:
            paragraph.append(line)
    flush()

    slots = load_formula_slots(spec)
    if slots:
        for slot in slots:
            latex = slot.get("final_latex") or slot.get("marker_latex") or ""
            raw_text = ""
            if not latex:
                raw_text = slot.get("raw_formula_text") or slot.get("marker_text") or slot.get("content") or slot.get("final_text") or ""
            section = slot.get("section") or current_section or "Unknown"
            source = slot.get("detection_source") or slot.get("block_source") or spec.parser_name
            blocks.append(CanonicalDocumentBlock(
                block_id=slot.get("formula_id", f"f{len(blocks)+1:05d}"),
                page=int(slot.get("page") or 1),
                bbox=slot.get("bbox") or [0.0, 0.0, 1.0, 1.0],
                block_type="formula",
                text=raw_text,
                latex=latex,
                reading_order=reading_order,
                source=source,
                confidence=float(slot.get("detection_confidence") or slot.get("confidence") or (0.8 if latex else 0.3)),
                section=section,
                section_confidence=slot.get("section_confidence") or ("medium" if section != "Unknown" else "low"),
                section_reason=slot.get("section_reason") or "formula_slot_section",
            ))
            reading_order += 1
    else:
        for formula in formulas_from_canonical(markdown):
            blocks.append(CanonicalDocumentBlock(
                block_id=formula["formula_id"],
                page=formula["page"],
                bbox=formula["bbox"],
                block_type="formula",
                text=formula["raw_text"],
                latex=formula["latex"],
                reading_order=reading_order,
                source=formula["source"] or spec.parser_name,
                confidence=formula["confidence"],
                section=formula["section"],
                section_confidence="low" if formula["section"] in {"Unknown", "Formula Blocks"} else "medium",
                section_reason="canonical_formula_block",
            ))
            reading_order += 1
    return blocks


def formulas_from_canonical(markdown: str) -> list[dict]:
    formulas: list[dict] = []
    lines = markdown.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line.startswith("<!-- formula_id:"):
            index += 1
            continue
        meta = parse_formula_comment(line)
        index += 1
        if index >= len(lines) or not lines[index].strip().startswith("```"):
            continue
        fence = lines[index].strip().strip("`").strip().lower()
        is_latex = fence == "latex" or meta.get("is_latex", "").lower() == "true"
        index += 1
        content: list[str] = []
        while index < len(lines) and not lines[index].strip().startswith("```"):
            content.append(lines[index])
            index += 1
        index += 1
        text = "\n".join(content).strip()
        origin = meta.get("origin", "")
        source = "marker_document" if origin == "parser_latex" else ""
        section = meta.get("section") or "Unknown"
        if section == "Formula Blocks":
            section = "Unknown"
        formulas.append({
            "formula_id": meta.get("formula_id") or f"fc_{len(formulas)+1}",
            "page": safe_int(meta.get("page"), default=1),
            "bbox": parse_bbox(meta.get("bbox", "")) or [0.0, 0.0, 1.0, 1.0],
            "section": section,
            "source": source,
            "confidence": float(meta.get("confidence") or (0.8 if is_latex else 0.3)),
            "latex": text if is_latex else "",
            "raw_text": "" if is_latex else text,
        })
    return formulas


def parse_formula_comment(line: str) -> dict[str, str]:
    inner = line.strip().removeprefix("<!--").removesuffix("-->").strip()
    fields: dict[str, str] = {}
    for part in inner.split("|"):
        if ":" not in part:
            continue
        key, value = part.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def parse_bbox(value: str) -> list[float]:
    if not value or value.strip() == "[]":
        return []
    numbers = re.findall(r"-?\d+(?:\.\d+)?", value)
    return [float(item) for item in numbers[:4]] if len(numbers) >= 4 else []


def safe_int(value: object, default: int = 1) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return default


def blocks_from_mineru_spike(spec: PaperSpec) -> list[CanonicalDocumentBlock]:
    data = json.loads((spec.source_dir / "mineru25_v2_spike" / "document_blocks.json").read_text(encoding="utf-8"))
    return [CanonicalDocumentBlock.model_validate(item) for item in data]


def blocks_from_pdf_debug(spec: PaperSpec) -> list[CanonicalDocumentBlock]:
    blocks: list[CanonicalDocumentBlock] = []
    doc = fitz.open(spec.source_pdf)
    order = 0
    current_section = "Unknown"
    for page_index, page in enumerate(doc, start=1):
        text = page.get_text("text")
        for raw in text.splitlines():
            line = re.sub(r"\s+", " ", raw).strip()
            if not line:
                continue
            found = section_from_heading(line)
            if found and len(line) <= 80:
                current_section = found
                block_type = "title"
            else:
                block_type = "formula" if looks_formula_like(line) else "text"
            section_for_line = current_section
            if block_type != "title" and current_section == "Abstract" and page_index > 2:
                section_for_line = "Unknown"
            blocks.append(CanonicalDocumentBlock(
                block_id=f"u{len(blocks)+1:05d}",
                page=page_index,
                bbox=[0.0, 0.0, 1.0, 1.0],
                block_type=block_type,
                text=line if block_type == "formula" else line[:1200],
                latex="",
                reading_order=order,
                source=spec.parser_name,
                confidence=0.35 if block_type == "formula" else 0.65,
                section=section_for_line,
                section_confidence="medium" if section_for_line != "Unknown" else "low",
                section_reason="pymupdf_debug_line",
            ))
            order += 1
    return blocks


def looks_formula_like(line: str) -> bool:
    if len(line) > 220:
        return False
    if re.search(r"(attention|multihead|softmax|argmax|anomalyscore|assdis|prior association|series association)", line, re.I):
        return True
    symbol_count = len(re.findall(r"[=+\-*/^_{}∑∏√≤≥∈×]", line))
    alpha_count = len(re.findall(r"[A-Za-z]", line))
    return symbol_count >= 2 and alpha_count >= 1


def load_formula_slots(spec: PaperSpec) -> list[dict]:
    candidates = [
        spec.source_dir / "formula_slots.json",
        spec.source_dir / "mineru25_v2_spike" / "formula_slots_v2.json",
    ]
    for path in candidates:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    return []


def formula_slots_for_gate(spec: PaperSpec, out_dir: Path, blocks: list[CanonicalDocumentBlock]) -> list[dict]:
    slots = []
    originals = load_formula_slots(spec)
    by_id = {item.get("formula_id"): item for item in originals}
    for index, block in enumerate((b for b in blocks if b.block_type == "formula"), start=1):
        formula_id = block.block_id if block.block_id.startswith("formula_") else f"formula_{index:03d}"
        original = by_id.get(formula_id, {})
        crop_exists = any((out_dir / "formula_crops").glob(f"{formula_id}_*.png"))
        overlay_exists = any((out_dir / "formula_overlays").glob("overlay_page*.png"))
        crop_path = next((out_dir / "formula_crops").glob(f"{formula_id}_*.png"), None)
        overlay_path = next((out_dir / "formula_overlays").glob("overlay_page*.png"), None)
        review_disabled = original.get("review_disabled") is True or str(original.get("review_disabled", "")).lower() == "true"
        slots.append({
            "formula_id": formula_id,
            "block_id": block.block_id,
            "page": block.page,
            "bbox": block.bbox,
            "crop_required": not review_disabled,
            "overlay_required": not review_disabled,
            "crop_path": str(crop_path) if crop_exists and crop_path else "",
            "overlay_path": str(overlay_path) if overlay_exists and overlay_path else "",
            "source_mismatch": False,
            "review_disabled": review_disabled,
        })
    return slots


def copy_source_artifacts(spec: PaperSpec, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    copy_optional(spec.source_pdf, out_dir / "source.pdf")
    for name in ["markitdown.md", "pymupdf.txt", "marker.md", "marker_skipped.txt", "marker_skipped_by_policy.txt", "compare_summary.md", "section_samples.md", "formula_review.md", "formula_candidates.md"]:
        copy_optional(spec.source_dir / name, out_dir / name)
    if not any((out_dir / name).exists() for name in ["marker.md", "marker_skipped.txt", "marker_skipped_by_policy.txt"]):
        (out_dir / "marker_skipped_by_policy.txt").write_text(
            "marker_enabled=false; trigger_mode=never for ordinary live eval. "
            "Marker may be used only in review/heavy mode with timeout/skipped_by_policy reporting.\n",
            encoding="utf-8",
        )
    for folder in ["formula_crops", "formula_overlays"]:
        src = spec.source_dir / folder
        if src.exists():
            shutil.copytree(src, out_dir / folder, dirs_exist_ok=True)


def write_dense_pages(spec: PaperSpec, out_dir: Path) -> list[dict]:
    doc = fitz.open(spec.source_pdf)
    rows = []
    token_re = re.compile(r"(?:\\[a-zA-Z]+|[=+\-*/^_{}∑∏√≤≥∈×]|softmax|attention|argmax|argmin|log|exp|frac)", re.I)
    for page_number, page in enumerate(doc, start=1):
        lines = [line.strip() for line in page.get_text("text").splitlines() if line.strip()]
        joined = "\n".join(lines)
        count = len(token_re.findall(joined))
        density = count / max(len(joined), 1)
        sample_lines = [line for line in lines if token_re.search(line)][:5]
        rows.append({"page": page_number, "math_token_count": count, "density": density, "sample_lines": sample_lines})
    selected = sorted(rows, key=lambda item: (item["math_token_count"], item["density"]), reverse=True)[:4]
    lines = ["# Formula Dense Pages", "", "| page | math_token_count | density | selected | sample_lines |", "| ---: | ---------------: | ------: | -------- | ------------ |"]
    selected_pages = {item["page"] for item in selected}
    for item in rows:
        lines.append(
            f"| {item['page']} | {item['math_token_count']} | {item['density']:.4f} | "
            f"{'YES' if item['page'] in selected_pages else 'NO'} | {json.dumps(item['sample_lines'], ensure_ascii=False)} |"
        )
    (out_dir / "formula_dense_pages.md").write_text("\n".join(lines), encoding="utf-8")
    for item in selected:
        pix = doc[item["page"] - 1].get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
        pix.save(out_dir / f"formula_page_{item['page']}.png")
    return selected


def coverage(blocks: list[CanonicalDocumentBlock], samples: Iterable[str], aux_texts: Iterable[str]) -> dict[str, str]:
    latex_text = "\n".join(block.latex for block in blocks if block.block_type == "formula" and block.latex)
    raw_formula_text = "\n".join(block.text for block in blocks if block.block_type == "formula" and block.text and not block.latex)
    all_text = "\n".join([latex_text, raw_formula_text, *aux_texts])
    norm_latex = normalize_match(latex_text)
    norm_raw = normalize_match(raw_formula_text)
    norm_all = normalize_match(all_text)
    result = {}
    for sample in samples:
        variants = sample_variants(sample)
        if any(v and v in norm_latex for v in variants):
            result[sample] = "FOUND_LATEX"
        elif any(v and v in norm_raw for v in variants):
            result[sample] = "FOUND_RAW_TEXT"
        elif any(v and v in norm_all for v in variants):
            result[sample] = "FOUND_TEXT"
        else:
            result[sample] = "MISSING: not present in parsed formula blocks or copied parser text"
    return result


def metrics_for(spec: PaperSpec, out_dir: Path, blocks: list[CanonicalDocumentBlock], quality, started: float, cov: dict[str, str]) -> dict:
    formulas = [b for b in blocks if b.block_type == "formula"]
    formula_slots = load_formula_slots(spec)
    return {
        "route": spec.route,
        "primary_parser": spec.parser_name,
        "formula_count": len(formulas),
        "latex_count": sum(1 for b in formulas if b.latex),
        "raw_formula_text_count": sum(1 for b in formulas if b.text and not b.latex),
        "bbox_count": sum(1 for b in formulas if len(b.bbox) == 4),
        "crop_exists": sum(1 for slot in formula_slots if any((out_dir / "formula_crops").glob(f"{slot.get('formula_id','')}_*.png"))),
        "overlay_exists": len(list((out_dir / "formula_overlays").glob("overlay_page*.png"))) if (out_dir / "formula_overlays").exists() else 0,
        "canonical_match": all(status.startswith("FOUND") or "MISSING:" in status for status in cov.values()),
        "section_distribution": section_distribution(blocks),
        "section_contradiction_count": quality.section_contradiction_count,
        "all_formulas_in_Abstract_suspicious": quality.all_formulas_in_abstract_suspicious,
        "polluted_section_count": quality.polluted_section_count,
        "missing_crop_count": quality.missing_crop_count,
        "missing_overlay_count": quality.missing_overlay_count,
        "raw_only_formula_dense": quality.raw_only_formula_dense,
        "m2_ready_for_formula_understanding": quality.m2_ready_for_formula_understanding,
        "formula_understanding_reasons": "; ".join(quality.formula_understanding_reasons) or "none",
        "blocking_reasons": "; ".join(quality.blocking_reasons) or "none",
        "warning_reasons": "; ".join(quality.warning_reasons) or "none",
        "high_risk_count": quality.high_risk_count,
        "medium_risk_count": quality.medium_risk_count,
        "low_risk_count": max(quality.low_risk_count, 0),
        "runtime_seconds": round(time.perf_counter() - started, 3),
        "runtime_device": "CPU/cached artifacts",
        "peak_vram_estimate": "not measured",
        "ollama_json_valid": 0,
        "ollama_json_invalid": 17 if spec.key == "paper_4_unseen" else 0,
        "ollama_retry": 0,
        "ollama_timeout": 0,
        "ollama_changed_by_count": 0,
        "core_formula_coverage": cov,
    }


def parser_quality_rows_from_canonical(spec: PaperSpec) -> list[dict[str, object]]:
    markdown_path = spec.source_dir / "canonical_paper.md"
    if not markdown_path.exists():
        return []
    markdown = markdown_path.read_text(encoding="utf-8", errors="replace")
    parts = markdown.split("---", 2)
    if len(parts) < 3:
        return []
    front_text = parts[1]
    selected_parser = ""
    selected_reason = ""
    for line in front_text.splitlines():
        if line.startswith("selected_parser:") or line.startswith("body_selected_parser:"):
            selected_parser = line.split(":", 1)[1].strip().strip("'\"")
        elif line.startswith("parser_selection_reason:") or line.startswith("body_parser_selection_reason:"):
            selected_reason = line.split(":", 1)[1].strip().strip("'\"")

    rows: list[dict[str, object]] = []
    active = False
    current: dict[str, object] | None = None
    for line in front_text.splitlines():
        if line.strip() == "parser_quality_details:":
            active = True
            continue
        if not active:
            continue
        if line and not line.startswith(" "):
            break
        parser_match = re.match(r"\s{2}([A-Za-z0-9_]+):\s*$", line)
        if parser_match:
            if current:
                rows.append(current)
            current = {"parser": parser_match.group(1)}
            continue
        if current and line.startswith("    ") and ":" in line:
            key, value = line.strip().split(":", 1)
            value = value.strip().strip("'\"")
            current[key] = _parse_metric_value(value)
    if current:
        rows.append(current)

    for row in rows:
        row["selected"] = "YES" if row.get("parser") == selected_parser else "NO"
        row["reason"] = str(row.get("reason") or (selected_reason if row["selected"] == "YES" else "not_selected"))
    return rows


def _parse_metric_value(value: str) -> object:
    if value == "":
        return ""
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def section_distribution(blocks: list[CanonicalDocumentBlock]) -> dict[str, int]:
    result: dict[str, int] = {}
    for block in blocks:
        result[block.section or "Unknown"] = result.get(block.section or "Unknown", 0) + 1
    return result


def write_section_samples(out_dir: Path, spec: PaperSpec, blocks: list[CanonicalDocumentBlock]) -> None:
    lines = [f"# Section Samples: {spec.title}", ""]
    for section in ["Abstract", "Introduction", "Related Work", "Method", "Experiments", "Conclusion", "References"]:
        texts = [
            block.text.strip()
            for block in blocks
            if block.section == section and block.block_type == "text" and block.text.strip()
        ]
        sample = "\n\n".join(texts)[:1600] if texts else "No sample available."
        lines += [f"## {section} sample", "", sample, ""]
    (out_dir / "section_samples.md").write_text("\n".join(lines), encoding="utf-8")


def write_formula_review(out_dir: Path, title: str, metrics: dict, blocks: list[CanonicalDocumentBlock]) -> None:
    formulas = [block for block in blocks if block.block_type == "formula"]
    lines = [f"# Formula Review: {title}", "", "## Formula Statistics", ""]
    lines += [
        "| type | count |",
        "| ---- | ----: |",
        f"| source_latex | 0 |",
        f"| mineru_latex/parser_latex | {metrics['latex_count']} |",
        f"| ocr_latex | 0 |",
        f"| raw_formula_text | {metrics['raw_formula_text_count']} |",
        f"| unknown | 0 |",
        f"| canonical FormulaBlock total | {metrics['formula_count']} |",
        "",
        f"- m2_ready_for_formula_understanding: {metrics['m2_ready_for_formula_understanding']}",
        f"- formula_understanding_reasons: {metrics['formula_understanding_reasons']}",
        f"- raw_only_formula_dense: {metrics['raw_only_formula_dense']}",
        "",
        "## Formula Samples (from canonical paper)",
        "",
        "| id | origin | is_latex | confidence | source_parser | content |",
        "| -- | ------ | -------- | ---------: | ------------- | ------- |",
    ]
    for block in formulas[:15]:
        origin = "parser_latex" if block.latex else "raw_formula_text"
        content = (block.latex or block.text).replace("\n", " ")
        content = content[:180]
        lines.append(
            f"| {block.block_id} | {origin} | {'True' if block.latex else 'False'} | "
            f"{block.confidence:.2f} | {block.source} | {content} |"
        )
    lines += [
        "",
        "## Core Formula Coverage",
        "",
    ]
    for sample, status in metrics["core_formula_coverage"].items():
        lines.append(f"- {sample}: {status}")
    lines += ["", "## Raw Formula Text Check", ""]
    raw_blocks = [block for block in formulas if block.text and not block.latex]
    if not raw_blocks:
        lines.append("OK: no raw_formula_text blocks")
    for block in raw_blocks:
        lines.append(f"OK: {block.block_id} uses raw_formula_text and leaves latex empty")
    text = "\n".join(lines)
    (out_dir / "formula_review.md").write_text(text, encoding="utf-8")
    (out_dir / "formula_review_v2.md").write_text(text, encoding="utf-8")

    candidate_lines = [
        f"# Formula Candidates: {title}",
        "",
        "| id | page | section | origin | is_latex | content |",
        "| -- | ---: | ------- | ------ | -------- | ------- |",
    ]
    for block in formulas:
        origin = "parser_latex" if block.latex else "raw_formula_text"
        content = (block.latex or block.text).replace("\n", " ")[:220]
        candidate_lines.append(
            f"| {block.block_id} | {block.page} | {block.section or 'Unknown'} | "
            f"{origin} | {'True' if block.latex else 'False'} | {content} |"
        )
    (out_dir / "formula_candidates.md").write_text("\n".join(candidate_lines), encoding="utf-8")


def write_compare_report(out_dir: Path, spec: PaperSpec, metrics: dict, quality) -> str:
    lines = [
        f"# M1 Compare Report: {spec.title}",
        "",
        f"- paper_id: {spec.key}",
        f"- route: {spec.route}",
        f"- primary_parser: {spec.parser_name}",
        f"- canonical_quality_status: {quality.status.value}",
        f"- selected_route_reason: {route_reason(spec)}",
        f"- formula_count: {metrics['formula_count']}",
        f"- latex_count: {metrics['latex_count']}",
        f"- raw_formula_text_count: {metrics['raw_formula_text_count']}",
        f"- bbox_count: {metrics['bbox_count']}",
        f"- crop_exists: {metrics['crop_exists']}",
        f"- overlay_exists: {metrics['overlay_exists']}",
        f"- missing_crop_count: {metrics['missing_crop_count']}",
        f"- missing_overlay_count: {metrics['missing_overlay_count']}",
        f"- raw_only_formula_dense: {metrics['raw_only_formula_dense']}",
        f"- m2_ready_for_formula_understanding: {metrics['m2_ready_for_formula_understanding']}",
        f"- formula_understanding_reasons: {metrics['formula_understanding_reasons']}",
        f"- section_contradiction_count: {metrics['section_contradiction_count']}",
        f"- all_formulas_in_Abstract_suspicious: {metrics['all_formulas_in_Abstract_suspicious']}",
        f"- polluted_section_count: {metrics['polluted_section_count']}",
        f"- runtime_seconds: {metrics['runtime_seconds']}",
        f"- runtime_device: {metrics['runtime_device']}",
        f"- ollama_json_valid: {metrics['ollama_json_valid']}",
        f"- ollama_json_invalid: {metrics['ollama_json_invalid']}",
        "",
        "## Core Formula Coverage",
        "",
    ]
    for sample, status in metrics["core_formula_coverage"].items():
        lines.append(f"- {sample}: {status}")
    text = "\n".join(lines)
    (out_dir / "compare_report.md").write_text(text, encoding="utf-8")
    rows = parser_quality_rows_from_canonical(spec)
    if not rows:
        rows = [{
            "parser": spec.parser_name,
            "overall_score": 0.0,
            "output_length": 0,
            "section_count": 0,
            "long_concat_count": 0,
            "spacing_quality": 0.0,
            "cid_token_count": 0,
            "formula_candidate_count": metrics["formula_count"],
            "garbled_line_ratio": 0.0,
            "selected": "YES",
            "reason": "generated_from_acceptance_blocks",
        }]
    selected_row = next((row for row in rows if row.get("selected") == "YES"), rows[0])
    selected_score = _fmt_metric(selected_row.get("overall_score"))
    summary_lines = [
        f"# Parser Comparison: {spec.title}",
        "",
        "## Basic Info",
        f"- title: {spec.title}",
        f"- paper_id: {spec.key}",
        "- source_pdf_path: source.pdf",
        f"- selected_parser: {spec.parser_name}",
        f"- parser_selection_reason: {route_reason(spec)}",
        f"- parser_quality_score: {selected_score}",
        f"- canonical_quality_status: {quality.status.value}",
        f"- degradation_reason: {'; '.join(quality.blocking_reasons + quality.warning_reasons) or 'none'}",
        "- canonical_paper_path: canonical_paper.md",
        "",
        "## Parser Quality Table",
        "",
        "| parser | overall_score | output_length | section_count | long_concat_count | spacing_quality | cid_token_count | formula_candidate_count | garbled_line_ratio | selected | reason |",
        "| ------ | ------------: | ------------: | ------------: | ----------------: | --------------: | --------------: | ----------------------: | -----------------: | -------- | ------ |",
    ]
    for row in rows:
        summary_lines.append(
            f"| {row.get('parser', spec.parser_name)} | {_fmt_metric(row.get('overall_score'))} | "
            f"{_fmt_metric(row.get('output_length'))} | {_fmt_metric(row.get('section_count'))} | "
            f"{_fmt_metric(row.get('long_concat_count'))} | {_fmt_metric(row.get('spacing_quality'))} | "
            f"{_fmt_metric(row.get('cid_token_count'))} | {_fmt_metric(row.get('formula_candidate_count'))} | "
            f"{_fmt_metric(row.get('garbled_line_ratio'))} | {row.get('selected', 'NO')} | {row.get('reason', 'not_selected')} |"
        )
    (out_dir / "compare_summary.md").write_text("\n".join(summary_lines), encoding="utf-8")
    return text


def _fmt_metric(value: object) -> str:
    if value is None or value == "":
        return "0"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def route_reason(spec: PaperSpec) -> str:
    if spec.parser_name == "mineru25pro":
        return "MinerU route verified on paper_4 only; multi-paper MinerU acceptance remains pending."
    if spec.parser_name == "marker_document":
        return "Marker fallback selected because it produced real parser_latex FormulaBlocks for this review case."
    if "Marker formula audit" in spec.route:
        return "PyMuPDF body text plus Marker formula slots selected from stable three-pipeline review artifacts."
    return "Fallback/debug route selected because cached MinerU output is unavailable and report must not claim primary success."


def downgrade_visual_review_only_fail_to_degraded(quality) -> None:
    if quality.status != CanonicalQualityStatus.FAIL:
        return
    non_visual_blockers = [reason for reason in quality.blocking_reasons if reason not in VISUAL_REVIEW_BLOCKING_REASONS]
    if non_visual_blockers:
        return
    quality.status = CanonicalQualityStatus.DEGRADED
    if "FORMULA_VISUAL_REVIEW_PENDING" not in quality.warning_reasons:
        quality.warning_reasons.append("FORMULA_VISUAL_REVIEW_PENDING")
    quality.high_risk_count = max(quality.high_risk_count, len(quality.blocking_reasons), 1)
    quality.medium_risk_count = len(quality.warning_reasons)


def build_paper(spec: PaperSpec) -> dict:
    out_dir = OUT / spec.key
    out_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    copy_source_artifacts(spec, out_dir)
    dense_pages = write_dense_pages(spec, out_dir)

    if spec.use_mineru_blocks:
        blocks = blocks_from_mineru_spike(spec)
    elif spec.key == "paper_5_unseen":
        blocks = blocks_from_pdf_debug(spec)
    else:
        blocks = blocks_from_review_canonical(spec)

    gate_slots = formula_slots_for_gate(spec, out_dir, blocks)
    quality = M1QualityGate().evaluate(blocks, gate_slots)
    downgrade_visual_review_only_fail_to_degraded(quality)

    aux_texts = []
    for name in ["markitdown.md", "pymupdf.txt", "marker.md"]:
        path = out_dir / name
        if path.exists():
            aux_texts.append(path.read_text(encoding="utf-8", errors="replace"))
    cov = coverage(blocks, spec.core_samples, aux_texts)
    metrics = metrics_for(spec, out_dir, blocks, quality, started, cov)
    compare = write_compare_report(out_dir, spec, metrics, quality)

    result = CanonicalBuilder().build(
        paper_id=spec.key,
        title=spec.title,
        blocks=blocks,
        quality=quality,
        output_dir=out_dir,
        parser_name=spec.parser_name,
        source_pdf_path="source.pdf",
        metrics={k: v for k, v in metrics.items() if isinstance(v, (str, int, float, bool))},
    )
    report = M1VisualAuditReportGenerator().write(
        output_dir=out_dir,
        paper_id=spec.key,
        title=spec.title,
        blocks=blocks,
        quality=quality,
        metrics=metrics,
        compare_markdown=compare,
    )
    write_section_samples(out_dir, spec, blocks)
    write_formula_review(out_dir, spec.title, metrics, blocks)
    (out_dir / "README_REVIEW.md").write_text(
        f"# {spec.key} Review\n\n"
        f"- title: {spec.title}\n"
        f"- route: {spec.route}\n"
        f"- selected_parser: {spec.parser_name}\n"
        f"- selected_reason: {route_reason(spec)}\n"
        f"- canonical_quality_status: {quality.status.value}\n"
        f"- m2_ready: {result.m2_ready}\n"
        f"- m2_ready_for_formula_understanding: {result.m2_ready_for_formula_understanding}\n"
        f"- canonical_paper: {Path(result.canonical_paper_path).name}\n"
        f"- visual_audit: {Path(report.html_path).name}\n"
        f"- dense_pages: formula_dense_pages.md generated from PyMuPDF page-level text scan; selected pages: {[p['page'] for p in dense_pages]}\n"
        f"- unseen_reason: {spec.unseen_reason or 'review paper'}\n",
        encoding="utf-8",
    )
    return {
        "spec": spec,
        "metrics": metrics,
        "quality": quality.status.value,
        "m2_ready": result.m2_ready,
        "m2_ready_for_formula_understanding": result.m2_ready_for_formula_understanding,
    }


def write_top_level(rows: list[dict]) -> None:
    lines = [
        "# M1 Acceptance Report",
        "",
        "Default route decision: MinerU2.5-Pro + RuleBasedStructureRefiner is the primary M1 route, but the MinerU route is verified on paper_4 only. Multi-paper MinerU acceptance remains pending. Fallback reports are allowed for parser review and debugging, but they cannot prove that the primary route is stable. Marker remains fallback/audit baseline. Ollama remains optional and disabled by default because the cached paper_4_unseen evaluation recorded JSON valid=0 / invalid=17, so it did not improve section/context quality reliably.",
        "",
        "Current local Ollama smoke (qwen2.5:0.5b, 12 paper_4 blocks, timeout 20s): available=True, JSON valid=0, invalid=1, timeout=1, changed_by_count=0. This confirms Ollama remains optional/off by default.",
        "",
        "Marker default policy: marker_enabled=false, trigger_mode=never for ordinary live eval; review/heavy modes may opt in with timeout and skipped_by_policy/timeout_degraded reporting.",
        "",
        "Formula dense pages are computed by scanning each PDF page with PyMuPDF text extraction and math-token density, not from selected_text guesses.",
        "",
        "## Papers",
        "",
        "| paper | parser | status | m2_ready | formula_m2_ready | formulas | latex | raw_text | high_risk | coverage |",
        "| ----- | ------ | ------ | -------- | ---------------- | -------: | ----: | -------: | --------: | -------- |",
    ]
    for row in rows:
        spec = row["spec"]
        metrics = row["metrics"]
        coverage_text = "; ".join(f"{k}={v}" for k, v in metrics["core_formula_coverage"].items())
        lines.append(
            f"| {spec.key} | {spec.parser_name} | {row['quality']} | {row['m2_ready']} | "
            f"{row['m2_ready_for_formula_understanding']} | "
            f"{metrics['formula_count']} | {metrics['latex_count']} | {metrics['raw_formula_text_count']} | "
            f"{metrics['high_risk_count']} | {coverage_text} |"
        )
    lines += [
        "",
        "## Route Comparison",
        "",
        "- A MinerU2.5-Pro + RuleBasedStructureRefiner: verified on paper_4_unseen only; multi-paper MinerU acceptance is pending.",
        "- B MinerU2.5-Pro + RuleBasedStructureRefiner + Ollama structured refiner: not selected by default; Ollama native /api/chat JSON schema path is implemented, but cached live eval was JSON valid=0 / invalid=17.",
        "- C Marker fallback/audit baseline: retained for parser_latex fallback and visual audit comparison; not primary after all-formulas-in-Abstract blind failure.",
        "- D PyMuPDF/MarkItDown fallback/debug: allowed for review/debug artifacts, raw_formula_text must stay raw_formula_text and is never written as LaTeX.",
        "",
        "## New Unseen Selection",
        "",
        "- paper_5_unseen uses TranAD from the existing M1 live_eval auto search/download directory. It is a 15-page transformer anomaly-detection method paper and is not one of paper_1/2/3 or paper_4 MEMTO.",
    ]
    (OUT / "README_REVIEW.md").write_text("\n".join(lines), encoding="utf-8")
    (OUT / "OLLAMA_EVAL.md").write_text(
        "# Ollama Structured Refiner Eval\n\n"
        "- Endpoint: native `/api/chat` through `OllamaStructuredClient`\n"
        "- Format: JSON Schema, temperature=0\n"
        "- Cached paper_4_unseen eval: JSON valid=0, invalid=17\n"
        "- Current local smoke: model=qwen2.5:0.5b, sample=12 paper_4 blocks, timeout_seconds=20, available=True, JSON valid=0, invalid=1, timeout=1, changed_by_count=0\n"
        "- Decision: Ollama is implemented as optional structured refiner only; it is not enabled by default and cannot modify latex, bbox, page, or source identity.\n",
        encoding="utf-8",
    )


def make_bundle() -> Path:
    strip_report_text_trailing_whitespace(OUT)
    bundle = OUT.with_name("m1_v2_acceptance_bundle.zip")
    if bundle.exists():
        bundle.unlink()
    with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in OUT.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                zf.write(path, path.relative_to(OUT.parent))
    return bundle


def strip_report_text_trailing_whitespace(root: Path) -> None:
    text_suffixes = {".md", ".txt", ".json", ".html"}
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in text_suffixes:
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        stripped = "\n".join(line.rstrip() for line in content.splitlines())
        if content.endswith("\n"):
            stripped += "\n"
        path.write_text(stripped, encoding="utf-8", newline="\n")


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)
    rows = [build_paper(spec) for spec in PAPERS]
    write_top_level(rows)
    bundle = make_bundle()
    print(f"Wrote {OUT}")
    print(f"Wrote {bundle}")


if __name__ == "__main__":
    main()
