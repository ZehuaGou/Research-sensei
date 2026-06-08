"""Probe Marker for formula position (page/bbox/polygon) capability.

Introspects the rendered object from Marker's PdfConverter to determine
whether formula positions are available for crop-based OCR workflow.
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict, is_dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

PROBE_DIR = ROOT / "reports" / "m1_marker_formula_probe"
PAPERS = {
    "paper_1": ROOT / "reports" / "live_eval" / "work" / "m1" / "workspace" / "runs" / "m1-live" / "source_pdfs" / "2112.14436" / "source.pdf",
    "paper_2": ROOT / "reports" / "live_eval" / "work" / "m1" / "workspace" / "runs" / "m1-live" / "source_pdfs" / "W3184127157" / "source.pdf",
    "paper_3": ROOT / "reports" / "live_eval" / "work" / "m1" / "workspace" / "runs" / "m1-live" / "source_pdfs" / "2510.18998" / "source.pdf",
}


def introspect_rendered(rendered, paper_name: str) -> dict:
    """Deeply introspect the Marker rendered object."""
    info = {
        "paper": paper_name,
        "type": type(rendered).__name__,
        "module": type(rendered).__module__,
        "has_markdown": hasattr(rendered, "markdown"),
        "has_json": hasattr(rendered, "json"),
        "has_children": hasattr(rendered, "children"),
        "has_blocks": hasattr(rendered, "blocks"),
        "has_metadata": hasattr(rendered, "metadata"),
        "has_dict": hasattr(rendered, "dict"),
        "has_model_dump": hasattr(rendered, "model_dump"),
        "has___dict__": hasattr(rendered, "__dict__"),
        "is_dataclass": is_dataclass(rendered),
        "dir": sorted(dir(rendered)),
    }

    # Try to get markdown
    if hasattr(rendered, "markdown"):
        info["markdown_length"] = len(rendered.markdown) if rendered.markdown else 0

    # Try model_dump (pydantic)
    if hasattr(rendered, "model_dump"):
        try:
            info["model_dump_keys"] = list(rendered.model_dump().keys())
        except Exception as e:
            info["model_dump_error"] = str(e)

    # Try dict (pydantic v1)
    if hasattr(rendered, "dict"):
        try:
            info["dict_keys"] = list(rendered.dict().keys())
        except Exception as e:
            info["dict_error"] = str(e)

    # Try dataclass asdict
    if is_dataclass(rendered) and not isinstance(rendered, type):
        try:
            info["dataclass_fields"] = list(asdict(rendered).keys())
        except Exception as e:
            info["dataclass_error"] = str(e)

    # Try __dict__
    if hasattr(rendered, "__dict__"):
        info["instance_attrs"] = sorted(rendered.__dict__.keys())

    return info


def try_serialize(rendered) -> dict | None:
    """Try to serialize the rendered object to a dict."""
    # Try model_dump first
    if hasattr(rendered, "model_dump"):
        try:
            return rendered.model_dump()
        except Exception:
            pass

    # Try dict
    if hasattr(rendered, "dict"):
        try:
            return rendered.dict()
        except Exception:
            pass

    # Try dataclass
    if is_dataclass(rendered) and not isinstance(rendered, type):
        try:
            return asdict(rendered)
        except Exception:
            pass

    return None


def find_formula_blocks(rendered, markdown_text: str) -> list[dict]:
    """Find formula-related blocks in the rendered object."""
    formula_keywords = [
        "equation", "math", "formula", "inline", "display",
        "TextInlineMath", "Equation", "Formula",
    ]
    formula_blocks = []

    # Check if rendered has blocks/children
    blocks_to_check = []

    if hasattr(rendered, "blocks") and rendered.blocks:
        blocks_to_check.extend(rendered.blocks)
    if hasattr(rendered, "children") and rendered.children:
        blocks_to_check.extend(rendered.children)

    for block in blocks_to_check:
        block_info = {
            "type": type(block).__name__,
            "attrs": {},
        }

        # Get block attributes
        if hasattr(block, "__dict__"):
            block_info["attrs"] = {k: str(v)[:200] for k, v in block.__dict__.items()}

        # Check if it's a formula block
        block_str = str(block).lower()
        is_formula = any(kw.lower() in block_str for kw in formula_keywords)
        is_formula = is_formula or any(kw.lower() in str(block_info["type"]).lower() for kw in formula_keywords)

        if is_formula:
            formula_blocks.append(block_info)

    # Also search markdown for formula patterns
    import re
    md_formulas = []
    for m in re.finditer(r'\$\$(.*?)\$\$', markdown_text, re.DOTALL):
        md_formulas.append({
            "type": "latex_display",
            "content": m.group(1).strip()[:200],
            "start": m.start(),
            "end": m.end(),
        })

    for m in re.finditer(r'\$([^$]+)\$', markdown_text):
        content = m.group(1).strip()
        if len(content) > 5:  # Skip trivial
            md_formulas.append({
                "type": "latex_inline",
                "content": content[:200],
                "start": m.start(),
                "end": m.end(),
            })

    return {"block_formulas": formula_blocks, "markdown_formulas": md_formulas}


def try_crop_formula(pdf_path: Path, page_num: int, bbox: list[float], output_path: Path) -> bool:
    """Try to crop a formula region from the PDF using PyMuPDF."""
    try:
        import fitz
        with fitz.open(str(pdf_path)) as doc:
            if page_num < 0 or page_num >= len(doc):
                return False
            page = doc[page_num]

            # Determine coordinate system
            # Marker might use: pixels, points, normalized, or page coordinates
            # PyMuPDF uses points (1/72 inch)
            # Try direct points first
            rect = fitz.Rect(bbox)
            clip = page.get_pixmap(clip=rect, dpi=200)
            clip.save(str(output_path))
            return True
    except Exception as e:
        print(f"  Crop failed: {e}")
        return False


def draw_overlay(pdf_path: Path, page_num: int, bbox: list[float], output_path: Path) -> bool:
    """Draw bbox overlay on a page."""
    try:
        import fitz
        with fitz.open(str(pdf_path)) as doc:
            if page_num < 0 or page_num >= len(doc):
                return False
            page = doc[page_num]

            # Render page
            pix = page.get_pixmap(dpi=150)

            # Draw rectangle
            mat = fitz.Matrix(150 / 72, 150 / 72)
            rect = fitz.Rect(bbox)
            page.draw_rect(rect, color=(1, 0, 0), width=2)

            # Re-render
            pix = page.get_pixmap(dpi=150)
            pix.save(str(output_path))
            return True
    except Exception as e:
        print(f"  Overlay failed: {e}")
        return False


def main():
    """Run the Marker formula position probe."""
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict

    print("Loading Marker models...")
    models = create_model_dict()
    converter = PdfConverter(artifact_dict=models)

    all_results = {}

    for paper_name, pdf_path in PAPERS.items():
        if not pdf_path.exists():
            print(f"\n=== {paper_name}: PDF not found ===")
            continue

        print(f"\n=== {paper_name}: {pdf_path.name} ===")
        paper_dir = PROBE_DIR / paper_name
        paper_dir.mkdir(exist_ok=True)

        t0 = time.time()
        rendered = converter(str(pdf_path))
        elapsed = time.time() - t0
        print(f"  Marker conversion: {elapsed:.1f}s")

        # Introspect
        introspection = introspect_rendered(rendered, paper_name)
        introspection["elapsed_seconds"] = round(elapsed, 1)

        # Save introspection
        (paper_dir / "rendered_structure.txt").write_text(
            json.dumps(introspection, indent=2, default=str),
            encoding="utf-8"
        )

        # Try to serialize
        serialized = try_serialize(rendered)
        if serialized:
            try:
                (paper_dir / "rendered_dump.json").write_text(
                    json.dumps(serialized, indent=2, default=str),
                    encoding="utf-8"
                )
                print(f"  Saved rendered_dump.json")
            except Exception as e:
                print(f"  Could not serialize: {e}")

        # Get markdown
        markdown_text = rendered.markdown if hasattr(rendered, "markdown") else str(rendered)

        # Find formula blocks
        formula_info = find_formula_blocks(rendered, markdown_text)
        (paper_dir / "formula_blocks.json").write_text(
            json.dumps(formula_info, indent=2, default=str),
            encoding="utf-8"
        )

        # Generate formula_blocks.md
        md_lines = [f"# Marker Formula Blocks: {paper_name}", ""]
        md_lines.append(f"## Block formulas: {len(formula_info['block_formulas'])}")
        for i, fb in enumerate(formula_info["block_formulas"][:20]):
            md_lines.append(f"\n### Block {i+1}: {fb['type']}")
            for k, v in fb["attrs"].items():
                md_lines.append(f"- {k}: {v}")

        md_lines.append(f"\n## Markdown formulas: {len(formula_info['markdown_formulas'])}")
        for i, mf in enumerate(formula_info["markdown_formulas"][:20]):
            md_lines.append(f"\n### Formula {i+1}: {mf['type']}")
            md_lines.append(f"```latex")
            md_lines.append(mf["content"])
            md_lines.append(f"```")
            md_lines.append(f"- position: chars {mf['start']}-{mf['end']}")

        (paper_dir / "formula_blocks.md").write_text("\n".join(md_lines), encoding="utf-8")

        print(f"  Formula blocks: {len(formula_info['block_formulas'])}")
        print(f"  Markdown formulas: {len(formula_info['markdown_formulas'])}")

        # Store results
        all_results[paper_name] = {
            "introspection": introspection,
            "formula_info": formula_info,
            "markdown_length": len(markdown_text),
        }

    # Save summary
    summary_path = PROBE_DIR / "probe_summary.json"
    summary = {
        "papers": {},
        "conclusion": "",
    }
    for paper_name, result in all_results.items():
        summary["papers"][paper_name] = {
            "type": result["introspection"]["type"],
            "has_blocks": result["introspection"]["has_blocks"],
            "has_children": result["introspection"]["has_children"],
            "has_json": result["introspection"]["has_json"],
            "has_model_dump": result["introspection"]["has_model_dump"],
            "block_formulas": len(result["formula_info"]["block_formulas"]),
            "markdown_formulas": len(result["formula_info"]["markdown_formulas"]),
            "markdown_length": result["markdown_length"],
            "elapsed_seconds": result["introspection"].get("elapsed_seconds", 0),
        }

    # Write conclusion based on findings
    has_blocks = any(r["introspection"]["has_blocks"] for r in all_results.values())
    has_bbox = False
    for r in all_results.values():
        for fb in r["formula_info"]["block_formulas"]:
            attrs = fb.get("attrs", {})
            if any(k in str(attrs).lower() for k in ["bbox", "polygon", "page", "page_id", "page_idx"]):
                has_bbox = True
                break

    if has_blocks and has_bbox:
        summary["conclusion"] = "Marker provides formula blocks with position data (bbox/polygon/page). Crop-based OCR workflow is feasible."
    elif has_blocks:
        summary["conclusion"] = "Marker provides formula blocks but WITHOUT position data (no bbox/polygon). Cannot crop formula regions directly."
    else:
        summary["conclusion"] = "Marker does NOT provide formula blocks. Only markdown output. Need alternative for position-aware formula extraction."

    summary_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(f"\n=== Summary saved to {summary_path} ===")
    print(f"Conclusion: {summary['conclusion']}")


if __name__ == "__main__":
    main()
