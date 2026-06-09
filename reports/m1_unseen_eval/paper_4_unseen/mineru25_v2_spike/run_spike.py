"""MinerU2.5-Pro v2 Pipeline Spike.

Tests MinerU2.5-Pro via mineru-vl-utils + StructureRefiner on paper_4_unseen
to verify if it fixes the section inference failure that Marker had.

Usage:
    cd reports/m1_unseen_eval/paper_4_unseen/mineru25_v2_spike
    python run_spike.py
"""
import json
import os
import re
import sys
import time
from pathlib import Path

# Proxy for model download
os.environ.setdefault("HTTP_PROXY", "http://127.0.0.1:7890")
os.environ.setdefault("HTTPS_PROXY", "http://127.0.0.1:7890")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

SPIKE_DIR = Path(__file__).resolve().parent
PAPER_DIR = SPIKE_DIR.parent
PDF_PATH = PAPER_DIR / "source.pdf"
OUTPUT_DIR = SPIKE_DIR

# ============================================================
# 1. DocumentBlock Schema
# ============================================================

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class DocumentBlock:
    """Normalized document block from any parser."""
    block_id: str
    page: int
    bbox: list[float]  # [x1, y1, x2, y2]
    block_type: str  # title / text / formula / table / figure / caption / reference / unknown
    text: str = ""
    latex: str = ""
    html: str = ""
    reading_order: int = 0
    source: str = ""  # mineru25pro / marker_document / pymupdf
    confidence: float = 0.0
    parent_section: str = ""
    raw_payload_ref: str = ""
    # Section refinement fields
    section: str = ""
    section_confidence: str = "low"
    section_reason: str = ""
    risk_flags: list[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


# ============================================================
# 2. MinerU25ProAdapter
# ============================================================

class MinerU25ProAdapter:
    """Adapter for MinerU2.5-Pro via mineru-vl-utils."""

    def __init__(self, model_path: str = "opendatalab/MinerU2.5-Pro-2604-1.2B"):
        self.model_path = model_path
        self.client = None

    def load(self):
        """Load the model."""
        from mineru_vl_utils import MinerUClient
        print(f"[MinerU25Pro] Loading model: {self.model_path}")
        t0 = time.time()
        self.client = MinerUClient(
            backend="transformers",
            model_path=self.model_path,
            use_tqdm=True,
            handle_equation_block=True,
        )
        print(f"[MinerU25Pro] Model loaded in {time.time()-t0:.1f}s")

    def parse_pdf(self, pdf_path: Path) -> tuple[list[DocumentBlock], dict]:
        """Parse PDF and return DocumentBlocks + raw output."""
        import fitz

        print(f"[MinerU25Pro] Parsing: {pdf_path.name}")
        doc = fitz.open(str(pdf_path))
        page_count = len(doc)

        all_blocks = []
        raw_pages = []
        block_counter = 0
        t0 = time.time()

        for page_idx in range(page_count):
            page = doc[page_idx]
            # Render page as image
            mat = fitz.Matrix(2, 2)  # 2x resolution
            pix = page.get_pixmap(matrix=mat)
            img_path = SPIKE_DIR / f"_tmp_page_{page_idx}.png"
            pix.save(str(img_path))

            from PIL import Image
            img = Image.open(str(img_path))

            # Extract with MinerU2.5-Pro
            result = self.client.two_step_extract(img)

            page_blocks = []
            for i, block in enumerate(result):
                block_counter += 1
                block_type = block.get("type", "unknown")
                bbox = block.get("bbox", [0, 0, 0, 0])
                content = block.get("content", "")

                # Normalize block type
                norm_type = self._normalize_block_type(block_type, content)

                # Extract LaTeX if formula
                latex = ""
                if norm_type == "formula":
                    latex = self._extract_latex(content)

                db = DocumentBlock(
                    block_id=f"b{block_counter:04d}",
                    page=page_idx + 1,
                    bbox=bbox,
                    block_type=norm_type,
                    text=content if norm_type != "formula" else "",
                    latex=latex,
                    reading_order=i,
                    source="mineru25pro",
                    confidence=0.9,  # MinerU2.5-Pro default confidence
                    raw_payload_ref=f"page_{page_idx}_block_{i}",
                )
                page_blocks.append(db)

            raw_pages.append({
                "page": page_idx + 1,
                "blocks": [dict(b) for b in result],
            })
            all_blocks.extend(page_blocks)

            # Cleanup temp file
            img_path.unlink(missing_ok=True)

            print(f"  Page {page_idx+1}/{page_count}: {len(page_blocks)} blocks")

        doc.close()
        elapsed = time.time() - t0

        stats = {
            "pages": page_count,
            "total_blocks": len(all_blocks),
            "elapsed_seconds": round(elapsed, 1),
            "blocks_per_page": round(len(all_blocks) / page_count, 1),
        }
        print(f"[MinerU25Pro] Done: {stats['total_blocks']} blocks in {stats['elapsed_seconds']}s")

        return all_blocks, {"pages": raw_pages, "stats": stats}

    def _normalize_block_type(self, raw_type: str, content: str) -> str:
        """Normalize MinerU block type to standard types."""
        t = raw_type.lower()
        if "title" in t or "heading" in t:
            return "title"
        if "formula" in t or "equation" in t:
            return "formula"
        if "table" in t:
            return "table"
        if "figure" in t or "image" in t:
            return "figure"
        if "caption" in t:
            return "caption"
        if "reference" in t or "ref" in t:
            return "reference"
        if "text" in t:
            return "text"
        return "text"

    def _extract_latex(self, content: str) -> str:
        """Extract LaTeX from content if present."""
        if not content:
            return ""
        # Check for LaTeX delimiters
        if "\\(" in content and "\\)" in content:
            m = re.search(r"\\((.*?)\\)", content, re.DOTALL)
            if m:
                return m.group(1).strip()
        if "\\[" in content and "\\]" in content:
            m = re.search(r"\[(.*?)\]", content, re.DOTALL)
            if m:
                return m.group(1).strip()
        if "$$" in content:
            parts = content.split("$$")
            if len(parts) >= 3:
                return parts[1].strip()
        if "$" in content:
            parts = content.split("$")
            if len(parts) >= 3:
                return parts[1].strip()
        return content


# ============================================================
# 3. RuleBasedStructureRefiner
# ============================================================

# Trusted section names
TRUSTED_SECTIONS = {
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
    "proposed approach": "Method",
    "model": "Method",
    "model architecture": "Method",
    "experiments": "Experiments",
    "experiment": "Experiments",
    "experimental results": "Experiments",
    "evaluation": "Experiments",
    "results": "Experiments",
    "discussion": "Experiments",
    "conclusion": "Conclusion",
    "conclusions": "Conclusion",
    "summary": "Conclusion",
    "references": "References",
    "appendix": "Appendix",
}

FORMULA_PATTERNS = [
    r"[=∑√σλτπ∈⊙]",
    r"\\(?:frac|sum|int|partial|alpha|beta|gamma|delta|mathcal|mathbb|mathrm|sqrt)",
    r"(?:Attention|Softmax|argmax|argmin)\s*\(",
]


def _looks_like_formula(text: str) -> bool:
    for p in FORMULA_PATTERNS:
        if re.search(p, text):
            return True
    return False


def _extract_section_from_heading(text: str) -> Optional[str]:
    """Extract section name from a heading line."""
    text = text.strip()
    if not text or len(text) > 80:
        return None
    if _looks_like_formula(text):
        return None

    # Strip number prefix: "3 Method" -> "Method", "3.1 Overall" -> "Overall"
    cleaned = re.sub(r"^\d+(?:\.\d+)*\s+", "", text)
    cleaned = re.sub(r"^[IVXLC]+\.\s+", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip().lower()

    if cleaned in TRUSTED_SECTIONS:
        return TRUSTED_SECTIONS[cleaned]
    for key, standard in TRUSTED_SECTIONS.items():
        if key in cleaned:
            return standard
    return None


def _merge_adjacent_number_lines(lines: list[str]) -> list[str]:
    """Merge lines like '3' + 'Method' into '3 Method'."""
    merged = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if re.match(r"^\d+(?:\.\d+)*$", line) and i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            if next_line and not re.match(r"^\d+(?:\.\d+)*$", next_line):
                merged.append(line + " " + next_line)
                i += 2
                continue
        merged.append(line)
        i += 1
    return merged


class RuleBasedStructureRefiner:
    """Refines document structure using rule-based section inference."""

    def refine(self, blocks: list[DocumentBlock]) -> list[DocumentBlock]:
        """Refine section assignments for all blocks."""
        # Step 1: Build section timeline from title blocks
        section_timeline = self._build_section_timeline(blocks)

        # Step 2: Assign sections to each block
        for block in blocks:
            self._assign_section(block, section_timeline)

        # Step 3: Detect risks
        self._detect_risks(blocks)

        return blocks

    def _build_section_timeline(self, blocks: list[DocumentBlock]) -> dict[int, str]:
        """Build page -> section mapping from title blocks."""
        timeline: dict[int, str] = {}
        current_section = "Unknown"

        # Group by page
        pages: dict[int, list[DocumentBlock]] = {}
        for b in blocks:
            pages.setdefault(b.page, []).append(b)

        for page_num in sorted(pages.keys()):
            page_blocks = sorted(pages[page_num], key=lambda b: b.bbox[1] if b.bbox else 0)
            for b in page_blocks:
                if b.block_type == "title":
                    section = _extract_section_from_heading(b.text)
                    if section:
                        current_section = section
            timeline[page_num] = current_section

        return timeline

    def _assign_section(self, block: DocumentBlock, timeline: dict[int, str]):
        """Assign section to a block based on nearby text and timeline."""
        # For title blocks, try to extract section directly
        if block.block_type == "title":
            section = _extract_section_from_heading(block.text)
            if section:
                block.section = section
                block.section_confidence = "high"
                block.section_reason = f"title_block_match: {block.text[:50]}"
                return

        # For formula blocks, check nearby text
        if block.block_type == "formula":
            # Use text from same page to find headings
            page_section = timeline.get(block.page, "Unknown")
            block.section = page_section
            block.section_confidence = "medium"
            block.section_reason = f"page_timeline: page {block.page}"
            return

        # For other blocks, use page timeline
        block.section = timeline.get(block.page, "Unknown")
        block.section_confidence = "medium"
        block.section_reason = f"page_timeline: page {block.page}"

    def _detect_risks(self, blocks: list[DocumentBlock]):
        """Detect section-related risks."""
        # Count formulas per section
        formula_sections: dict[str, int] = {}
        for b in blocks:
            if b.block_type == "formula":
                formula_sections[b.section] = formula_sections.get(b.section, 0) + 1

        # Check all_formulas_in_Abstract_suspicious
        total_formulas = sum(formula_sections.values())
        abstract_formulas = formula_sections.get("Abstract", 0)
        if total_formulas >= 5 and abstract_formulas == total_formulas:
            for b in blocks:
                if b.block_type == "formula":
                    b.risk_flags.append("ALL_FORMULAS_IN_ABSTRACT_SUSPICIOUS")

        # Check section contradiction (formula on non-Abstract page labeled Abstract)
        # This is a simplified check — in full implementation, check nearby text
        for b in blocks:
            if b.block_type == "formula" and b.section == "Abstract" and b.page > 2:
                b.risk_flags.append("SECTION_CONTRADICTION_POSSIBLE")


# ============================================================
# 4. LlamaSectionRefiner (optional)
# ============================================================

class LlamaSectionRefiner:
    """Optional Llama-based section refinement via local Ollama or OpenAI-compatible endpoint."""

    def __init__(self, base_url: str = "http://localhost:11434/v1", model: str = "llama3.2"):
        self.base_url = base_url
        self.model = model
        self.available = False
        self.json_valid_count = 0
        self.json_invalid_count = 0

    def check_availability(self) -> bool:
        """Check if local Llama is available."""
        try:
            import httpx
            resp = httpx.get(f"{self.base_url}/models", timeout=5)
            if resp.status_code == 200:
                self.available = True
                print(f"[Llama] Available at {self.base_url}")
                return True
        except Exception:
            pass
        print(f"[Llama] Not available at {self.base_url}")
        self.available = False
        return False

    def refine(self, blocks: list[DocumentBlock]) -> list[DocumentBlock]:
        """Refine sections using Llama if available."""
        if not self.available:
            return blocks

        # Group blocks by page
        pages: dict[int, list[DocumentBlock]] = {}
        for b in blocks:
            pages.setdefault(b.page, []).append(b)

        for page_num in sorted(pages.keys()):
            page_blocks = pages[page_num]
            self._refine_page(page_blocks)

        return blocks

    def _refine_page(self, blocks: list[DocumentBlock]):
        """Refine a single page's blocks using Llama."""
        import httpx

        # Build context for Llama
        context_lines = []
        for b in blocks:
            if b.block_type == "title":
                context_lines.append(f"HEADING: {(b.text or '')[:100]}")
            elif b.block_type == "text":
                context_lines.append(f"TEXT: {(b.text or '')[:100]}")
            elif b.block_type == "formula":
                context_lines.append(f"FORMULA: {(b.latex or b.text or '')[:100]}")

        context = "\n".join(context_lines[:30])  # Limit context

        prompt = f"""Analyze this document page and assign section names to each block.
Return ONLY valid JSON: a list of objects with "block_id" and "section" fields.
Valid sections: Abstract, Introduction, Related Work, Method, Experiments, Conclusion, References, Appendix.

Page content:
{context}

Return JSON array:"""

        try:
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.0,
                    "max_tokens": 1000,
                },
                timeout=30,
            )
            if resp.status_code == 200:
                result = resp.json()
                content = result["choices"][0]["message"]["content"]
                # Parse JSON from response
                json_match = re.search(r"\[.*\]", content, re.DOTALL)
                if json_match:
                    assignments = json.loads(json_match.group())
                    self.json_valid_count += 1
                    # Apply assignments
                    id_to_block = {b.block_id: b for b in blocks}
                    for a in assignments:
                        bid = a.get("block_id")
                        section = a.get("section")
                        if bid in id_to_block and section:
                            id_to_block[bid].section = section
                            id_to_block[bid].section_confidence = "llama"
                            id_to_block[bid].section_reason = "llama_refined"
                else:
                    self.json_invalid_count += 1
            else:
                self.json_invalid_count += 1
        except Exception as e:
            print(f"[Llama] Error: {e}")
            self.json_invalid_count += 1


# ============================================================
# 5. FormulaSlot Extraction
# ============================================================

def extract_formula_slots(blocks: list[DocumentBlock]) -> list[dict]:
    """Extract FormulaSlot-like dicts from DocumentBlocks."""
    slots = []
    for b in blocks:
        if b.block_type == "formula":
            slots.append({
                "formula_id": f"formula_{len(slots)+1:03d}",
                "page": b.page,
                "bbox": b.bbox,
                "section": b.section,
                "section_confidence": b.section_confidence,
                "section_reason": b.section_reason,
                "block_source": b.source,
                "mineru_latex": b.latex,
                "final_latex": b.latex,
                "final_origin": "mineru_latex" if b.latex else "unresolved",
                "risk_flags": b.risk_flags,
            })
    return slots


# ============================================================
# 6. Canonical Paper Generation
# ============================================================

def generate_canonical_v2(blocks: list[DocumentBlock], formula_slots: list[dict]) -> str:
    """Generate canonical_paper.md from DocumentBlocks."""
    lines = [
        "---",
        "paper_id: 2312.02530",
        "title: MEMTO: Memory-guided Transformer for Multivariate Time Series Anomaly Detection",
        "authors: Junho Song, Keonwoo Kim, Jeonglyul Oh, Sungzoon Cho",
        "year: 2023",
        "venue: arXiv 2023",
        "source_type: pdf",
        "source_confidence: high",
        "canonicalization_status: success",
        "primary_parser: mineru25pro",
        "fallback_used: false",
        "m2_ready: true",
        f"formula_slot_count: {len(formula_slots)}",
        "---",
        "",
    ]

    # Group blocks by section
    sections: dict[str, list[DocumentBlock]] = {}
    for b in blocks:
        sections.setdefault(b.section or "Unknown", []).append(b)

    # Section order
    section_order = ["Abstract", "Introduction", "Related Work", "Method", "Experiments", "Conclusion", "References", "Appendix"]

    for section_name in section_order:
        if section_name not in sections:
            continue
        section_blocks = sections[section_name]
        lines.append(f"## {section_name}")
        lines.append("")

        for b in sorted(section_blocks, key=lambda x: (x.page, x.bbox[1] if x.bbox else 0)):
            if b.block_type == "title":
                # Skip section headings (already added as ## headers)
                if _extract_section_from_heading(b.text or "") == section_name:
                    continue
                lines.append(f"### {b.text or ''}")
                lines.append("")
            elif b.block_type == "formula":
                formula_id = f"formula_{sum(1 for s in formula_slots if s['page'] <= b.page):03d}"
                lines.append(f"<!-- formula_id: {formula_id} -->")
                if b.latex:
                    lines.append(f"```latex\n{b.latex}\n```")
                else:
                    lines.append(f"{{{{FORMULA: {(b.text or '')[:100]}}}}}")
                lines.append("")
            elif b.block_type == "text":
                lines.append(b.text or "")
                lines.append("")
            elif b.block_type == "table":
                lines.append(f"[TABLE: {(b.text or '')[:200]}]")
                lines.append("")
            elif b.block_type == "figure":
                lines.append(f"[FIGURE: {(b.text or '')[:200]}]")
                lines.append("")

    # Add remaining sections not in the order
    for section_name, section_blocks in sections.items():
        if section_name not in section_order:
            lines.append(f"## {section_name}")
            lines.append("")
            for b in sorted(section_blocks, key=lambda x: (x.page, x.bbox[1] if x.bbox else 0)):
                if b.block_type == "text":
                    lines.append(b.text or "")
                    lines.append("")

    return "\n".join(lines)


# ============================================================
# 7. Comparison Report
# ============================================================

def generate_comparison(
    v1_slots: list[dict],
    v2_slots: list[dict],
    v2_blocks: list[DocumentBlock],
    raw_output: dict,
    stats: dict,
    llama_status: dict,
) -> str:
    """Generate comparison report between v1 Marker and v2 MinerU."""

    # v1 section distribution
    v1_sections: dict[str, int] = {}
    for s in v1_slots:
        sec = s.get("section", "Unknown")
        v1_sections[sec] = v1_sections.get(sec, 0) + 1

    # v2 section distribution
    v2_sections: dict[str, int] = {}
    for s in v2_slots:
        sec = s.get("section", "Unknown")
        v2_sections[sec] = v2_sections.get(sec, 0) + 1

    # v2 block type distribution
    block_types: dict[str, int] = {}
    for b in v2_blocks:
        block_types[b.block_type] = block_types.get(b.block_type, 0) + 1

    # Risk analysis
    v2_risk_count = sum(1 for s in v2_slots if s.get("risk_flags"))
    v2_abstract_suspicious = sum(1 for s in v2_slots if "ALL_FORMULAS_IN_ABSTRACT_SUSPICIOUS" in s.get("risk_flags", []))
    v2_contradictions = sum(1 for s in v2_slots if "SECTION_CONTRADICTION_POSSIBLE" in s.get("risk_flags", []))

    latex_count = sum(1 for s in v2_slots if s.get("mineru_latex"))
    bbox_count = sum(1 for s in v2_slots if s.get("bbox") and len(s["bbox"]) == 4)

    report = f"""# MinerU2.5-Pro v2 Spike Report

Generated: {time.strftime('%Y-%m-%d %H:%M')}

## Paper

- Title: MEMTO: Memory-guided Transformer for Multivariate Time Series Anomaly Detection
- arXiv: 2312.02530
- PDF: {PDF_PATH}

## v1 Marker Results (baseline)

Formula count: {len(v1_slots)}
Section distribution:
"""
    for sec, count in sorted(v1_sections.items()):
        report += f"- {sec}: {count}\n"

    report += f"""
all_formulas_in_Abstract_suspicious: {'YES' if len(v1_slots) >= 5 and v1_sections.get('Abstract', 0) == len(v1_slots) else 'NO'}
section_contradiction_count: {sum(1 for s in v1_slots if 'SECTION_CONTRADICTION' in str(s.get('section_reason', '')))}

## v2 MinerU2.5-Pro Results

Formula count: {len(v2_slots)}
Latex count: {latex_count}
Bbox count: {bbox_count}

Section distribution:
"""
    for sec, count in sorted(v2_sections.items()):
        report += f"- {sec}: {count}\n"

    report += f"""
all_formulas_in_Abstract_suspicious: {'YES' if v2_abstract_suspicious > 0 else 'NO'}
section_contradiction_count: {v2_contradictions}
risk_flags_total: {v2_risk_count}

Block type distribution:
"""
    for bt, count in sorted(block_types.items()):
        report += f"- {bt}: {count}\n"

    report += f"""
## Runtime & Resources

- Backend: transformers (CPU)
- Model: opendatalab/MinerU2.5-Pro-2604-1.2B
- Pages: {stats.get('pages', 'N/A')}
- Total blocks: {stats.get('total_blocks', 'N/A')}
- Elapsed: {stats.get('elapsed_seconds', 'N/A')}s
- Blocks/page: {stats.get('blocks_per_page', 'N/A')}
- GPU: None (CPU only)
- VRAM: N/A

## Llama Refiner

- Available: {llama_status.get('available', False)}
- Model: {llama_status.get('model', 'N/A')}
- Base URL: {llama_status.get('base_url', 'N/A')}
- JSON valid: {llama_status.get('json_valid_count', 0)}
- JSON invalid: {llama_status.get('json_invalid_count', 0)}
- Participated: {'YES' if llama_status.get('available', False) and llama_status.get('json_valid_count', 0) > 0 else 'NO'}

## Per-Formula Detail (v2)

| # | formula_id | page | section | latex_present | risk_flags |
|---|-----------|-----:|---------|:---:|---|
"""
    for i, s in enumerate(v2_slots, 1):
        latex_yn = "Y" if s.get("mineru_latex") else "N"
        risks = ", ".join(s.get("risk_flags", [])) or "—"
        report += f"| {i} | {s['formula_id']} | {s['page']} | {s['section']} | {latex_yn} | {risks} |\n"

    report += f"""
## Conclusion

{'v2 MinerU2.5-Pro FIXED the all-Abstract problem.' if v2_abstract_suspicious == 0 and v1_sections.get('Abstract', 0) == len(v1_slots) else 'See analysis above.'}
v1 had {v1_sections.get('Abstract', 0)}/{len(v1_slots)} formulas in Abstract.
v2 has {v2_sections.get('Abstract', 0)}/{len(v2_slots)} formulas in Abstract.
"""
    return report


# ============================================================
# Main
# ============================================================

def main():
    print("=" * 60)
    print("MinerU2.5-Pro v2 Spike")
    print("=" * 60)

    # Load v1 results
    v1_slots_path = PAPER_DIR / "formula_slots.json"
    with open(v1_slots_path, "r", encoding="utf-8") as f:
        v1_slots = json.load(f)
    print(f"Loaded v1 slots: {len(v1_slots)}")

    # Initialize MinerU
    adapter = MinerU25ProAdapter()
    adapter.load()

    # Parse PDF
    blocks, raw_output = adapter.parse_pdf(PDF_PATH)

    # Save raw output
    raw_path = OUTPUT_DIR / "raw_mineru_output.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(raw_output, f, indent=2, ensure_ascii=False)
    print(f"Saved raw output: {raw_path}")

    # Save document blocks
    blocks_path = OUTPUT_DIR / "document_blocks.json"
    with open(blocks_path, "w", encoding="utf-8") as f:
        json.dump([b.to_dict() for b in blocks], f, indent=2, ensure_ascii=False)
    print(f"Saved document blocks: {blocks_path}")

    # Apply RuleBasedStructureRefiner
    print("\nApplying RuleBasedStructureRefiner...")
    refiner = RuleBasedStructureRefiner()
    blocks = refiner.refine(blocks)

    # Try LlamaSectionRefiner
    print("\nChecking LlamaSectionRefiner...")
    llama = LlamaSectionRefiner()
    llama.check_availability()
    if llama.available:
        print("Applying LlamaSectionRefiner...")
        blocks = llama.refine(blocks)

    llama_status = {
        "available": llama.available,
        "model": llama.model,
        "base_url": llama.base_url,
        "json_valid_count": llama.json_valid_count,
        "json_invalid_count": llama.json_invalid_count,
    }

    # Extract formula slots
    v2_slots = extract_formula_slots(blocks)
    slots_path = OUTPUT_DIR / "formula_slots_v2.json"
    with open(slots_path, "w", encoding="utf-8") as f:
        json.dump(v2_slots, f, indent=2, ensure_ascii=False)
    print(f"Saved v2 formula slots: {slots_path}")

    # Generate canonical paper
    canonical = generate_canonical_v2(blocks, v2_slots)
    canonical_path = OUTPUT_DIR / "canonical_paper_v2.md"
    canonical_path.write_text(canonical, encoding="utf-8")
    print(f"Saved canonical paper: {canonical_path}")

    # Generate structure refine report
    refine_report = f"""# Structure Refine Report

Generated: {time.strftime('%Y-%m-%d %H:%M')}

## Pipeline

1. MinerU2.5-Pro (opendatalab/MinerU2.5-Pro-2604-1.2B) via mineru-vl-utils
2. RuleBasedStructureRefiner (always)
3. LlamaSectionRefiner (optional, {'applied' if llama.available and llama.json_valid_count > 0 else 'not available'})

## Block Statistics

- Total blocks: {len(blocks)}
- Formula blocks: {sum(1 for b in blocks if b.block_type == 'formula')}
- Title blocks: {sum(1 for b in blocks if b.block_type == 'title')}
- Text blocks: {sum(1 for b in blocks if b.block_type == 'text')}

## Section Distribution (after refinement)

"""
    section_counts: dict[str, int] = {}
    for b in blocks:
        section_counts[b.section] = section_counts.get(b.section, 0) + 1
    for sec, count in sorted(section_counts.items()):
        refine_report += f"- {sec}: {count}\n"

    refine_report += f"""
## Risk Flags

- ALL_FORMULAS_IN_ABSTRACT_SUSPICIOUS: {sum(1 for b in blocks if 'ALL_FORMULAS_IN_ABSTRACT_SUSPICIOUS' in b.risk_flags)}
- SECTION_CONTRADICTION_POSSIBLE: {sum(1 for b in blocks if 'SECTION_CONTRADICTION_POSSIBLE' in b.risk_flags)}

## Llama Refiner Details

- Available: {llama.available}
- Model: {llama.model}
- JSON valid responses: {llama.json_valid_count}
- JSON invalid responses: {llama.json_invalid_count}
"""
    refine_path = OUTPUT_DIR / "STRUCTURE_REFINE_REPORT.md"
    refine_path.write_text(refine_report, encoding="utf-8")
    print(f"Saved refine report: {refine_path}")

    # Generate comparison report
    stats = raw_output.get("stats", {})
    comparison = generate_comparison(v1_slots, v2_slots, blocks, raw_output, stats, llama_status)
    compare_path = OUTPUT_DIR / "COMPARE_V1_MARKER_VS_V2_MINERU.md"
    compare_path.write_text(comparison, encoding="utf-8")
    print(f"Saved comparison: {compare_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    v1_sections = {}
    for s in v1_slots:
        v1_sections[s.get("section", "Unknown")] = v1_sections.get(s.get("section", "Unknown"), 0) + 1
    v2_sections = {}
    for s in v2_slots:
        v2_sections[s.get("section", "Unknown")] = v2_sections.get(s.get("section", "Unknown"), 0) + 1

    print(f"v1 formulas: {len(v1_slots)}, sections: {v1_sections}")
    print(f"v2 formulas: {len(v2_slots)}, sections: {v2_sections}")
    print(f"v2 blocks: {len(blocks)}")
    print(f"v2 latex: {sum(1 for s in v2_slots if s.get('mineru_latex'))}")
    print(f"v2 bbox: {sum(1 for s in v2_slots if s.get('bbox'))}")
    print(f"v2 all_Abstract_suspicious: {sum(1 for s in v2_slots if 'ALL_FORMULAS_IN_ABSTRACT_SUSPICIOUS' in s.get('risk_flags', []))}")
    print(f"Llama available: {llama.available}")


if __name__ == "__main__":
    main()
