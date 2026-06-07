"""Parser quality scoring and selection for M1 canonical paper generation.

Evaluates multiple parser outputs and selects the best one based on:
- Text quality (spacing, concatenation, garbled characters)
- Section detection
- Formula candidate count
- Content coverage
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class ParserQualityScore:
    """Quality score for a parser output."""
    parser_name: str
    output_length: int = 0
    section_count: int = 0
    long_concat_count: int = 0  # Words with 25+ consecutive letters (concatenation)
    cid_token_count: int = 0    # (cid:xxx) tokens
    spacing_quality: float = 1.0  # 0-1, higher is better
    formula_candidate_count: int = 0
    garbled_line_ratio: float = 0.0  # 0-1, lower is better
    overall_score: float = 0.0
    selection_reason: str = ""


def score_parser_output(text: str, parser_name: str) -> ParserQualityScore:
    """Score a parser output for quality."""
    if not text or not text.strip():
        return ParserQualityScore(parser_name=parser_name, overall_score=0.0, selection_reason="Empty output")

    score = ParserQualityScore(parser_name=parser_name)
    score.output_length = len(text)

    # Count sections
    score.section_count = len(re.findall(r'^#{1,3}\s+', text, re.MULTILINE))

    # Detect long concatenated words (no spaces for 25+ chars)
    long_concat = re.findall(r'[A-Za-z]{25,}', text)
    score.long_concat_count = len(long_concat)

    # Detect CID tokens
    cid_tokens = re.findall(r'\(cid:\d+\)', text)
    score.cid_token_count = len(cid_tokens)

    # Calculate spacing quality
    lines = text.split('\n')
    non_empty_lines = [l for l in lines if l.strip()]
    if non_empty_lines:
        # Check average word length (concatenated text has very long "words")
        words = re.findall(r'[A-Za-z]+', text)
        if words:
            avg_word_len = sum(len(w) for w in words) / len(words)
            # Normal avg word length is ~5-6, concatenated text is ~20+
            score.spacing_quality = max(0.0, min(1.0, 1.0 - (avg_word_len - 8) / 20))
        else:
            score.spacing_quality = 0.5

    # Count formula candidates (not just $$...$$)
    score.formula_candidate_count = count_formula_candidates(text)

    # Calculate garbled line ratio
    if non_empty_lines:
        garbled = sum(1 for l in non_empty_lines if _is_garbled_line(l))
        score.garbled_line_ratio = garbled / len(non_empty_lines)

    # Calculate overall score
    score.overall_score = _calculate_overall_score(score)

    # Generate selection reason
    if score.long_concat_count > 10:
        score.selection_reason = f"Severe concatenation ({score.long_concat_count} long words)"
    elif score.spacing_quality < 0.5:
        score.selection_reason = f"Poor spacing quality ({score.spacing_quality:.2f})"
    elif score.cid_token_count > 5:
        score.selection_reason = f"CID tokens detected ({score.cid_token_count})"
    elif score.output_length < 5000:
        score.selection_reason = "Output too short"
    else:
        score.selection_reason = "Good quality"

    return score


def count_formula_candidates(text: str) -> int:
    """Count formula-like text candidates in parser output.

    Supports multiple formula patterns:
    - $$...$$ (display math)
    - \\[...\\] (display math)
    - begin{equation}...end{equation}
    - Inline math with LaTeX commands
    - Raw formula text patterns (e.g., Attention(Q,K,V), MultiHead, etc.)
    """
    count = 0

    # Display math patterns
    count += len(re.findall(r'\$\$.*?\$\$', text, re.DOTALL))
    count += len(re.findall(r'\\\[.*?\\\]', text, re.DOTALL))
    count += len(re.findall(r'\\begin\{equation\}.*?\\end\{equation\}', text, re.DOTALL))

    # LaTeX-like inline formulas
    count += len(re.findall(r'\$[^$]+[\\{}^_][^$]*\$', text))

    # Raw formula text patterns (common in academic papers)
    raw_patterns = [
        r'Attention\s*\(\s*[QK]\s*,\s*[QK]\s*,\s*[QKV]\s*\)',
        r'MultiHead\s*\(\s*[QK]\s*,\s*[QK]\s*,\s*[QKV]\s*\)',
        r'Softmax\s*\(',
        r'arg\s*max\s',
        r'arg\s*min\s',
        r'KL\s*\(',
        r'Gumbel[\s-]softmax',
        r'AssDis\s*\(',
        r'AnomalyScore\s*\(',
        r'[A-Z][a-z]*\s*=\s*[A-Z][a-z]*\s*\(',  # e.g., f(x) = g(x)
    ]
    for pattern in raw_patterns:
        count += len(re.findall(pattern, text, re.IGNORECASE))

    return count


def _is_garbled_line(line: str) -> bool:
    """Check if a line looks garbled."""
    if not line.strip():
        return False
    # Lines with excessive special characters
    special = len(re.findall(r'[^\w\s.,;:!?()\-\'"=/+<>]', line))
    if len(line) > 0 and special / len(line) > 0.3:
        return True
    # Lines with only numbers and special chars
    if re.match(r'^[\d\s.,;:]+$', line.strip()):
        return True
    return False


def _calculate_overall_score(score: ParserQualityScore) -> float:
    """Calculate overall quality score (0-100)."""
    s = 50.0  # Base score

    # Length bonus (more content is better, up to a point)
    if score.output_length > 50000:
        s += 15
    elif score.output_length > 20000:
        s += 10
    elif score.output_length > 5000:
        s += 5
    else:
        s -= 20

    # Section detection bonus
    s += min(score.section_count * 3, 15)

    # Concatenation penalty
    s -= min(score.long_concat_count * 2, 30)

    # CID token penalty
    s -= min(score.cid_token_count * 3, 15)

    # Spacing quality
    s += score.spacing_quality * 20

    # Formula candidates bonus
    s += min(score.formula_candidate_count * 2, 10)

    # Garbled line penalty
    s -= score.garbled_line_ratio * 20

    return max(0.0, min(100.0, s))


@dataclass
class ParserSelectionResult:
    """Result of parser selection."""
    selected_parser: str
    selected_text: str
    candidates: list[ParserQualityScore] = field(default_factory=list)
    selection_reason: str = ""
    formula_candidates: list[dict] = field(default_factory=list)  # Extracted formula candidates


def select_best_parser(
    markitdown_text: str,
    pymupdf_text: str,
    marker_text: str | None = None,
    threshold: float = 40.0,
) -> ParserSelectionResult:
    """Select the best parser output based on quality scoring.

    Args:
        markitdown_text: MarkItDown output
        pymupdf_text: PyMuPDF output
        marker_text: Marker output (optional, heavy parser)
        threshold: Minimum score to accept a parser output
    """
    md_score = score_parser_output(markitdown_text, "markitdown_pdf")
    pm_score = score_parser_output(pymupdf_text, "pymupdf")

    candidates = [md_score, pm_score]

    if marker_text:
        mk_score = score_parser_output(marker_text, "marker_pdf")
        candidates.append(mk_score)

    # Sort by overall score
    candidates.sort(key=lambda s: s.overall_score, reverse=True)

    best = candidates[0]

    # If best score is below threshold, try to use Marker if available
    if best.overall_score < threshold and marker_text:
        best = next(c for c in candidates if c.parser_name == "marker_pdf")

    # Extract formula candidates from the selected parser
    formula_candidates = extract_formula_candidates(best.parser_name, markitdown_text, pymupdf_text, marker_text)

    return ParserSelectionResult(
        selected_parser=best.parser_name,
        selected_text=_get_text_for_parser(best.parser_name, markitdown_text, pymupdf_text, marker_text),
        candidates=candidates,
        selection_reason=best.selection_reason,
        formula_candidates=formula_candidates,
    )


def _get_text_for_parser(
    parser_name: str,
    markitdown_text: str,
    pymupdf_text: str,
    marker_text: str | None,
) -> str:
    """Get the text for a specific parser."""
    if parser_name == "markitdown_pdf":
        return markitdown_text
    elif parser_name == "pymupdf":
        return pymupdf_text
    elif parser_name == "marker_pdf" and marker_text:
        return marker_text
    return markitdown_text


def extract_formula_candidates(
    selected_parser: str,
    markitdown_text: str,
    pymupdf_text: str,
    marker_text: str | None = None,
) -> list[dict]:
    """Extract formula candidates from parser outputs.

    Returns a list of formula candidates with:
    - latex: the formula text
    - origin: source_latex | parser_latex | raw_formula_text
    - source: which parser found it
    - confidence: 0-1
    """
    candidates = []

    # From MarkItDown
    for m in re.finditer(r'\$\$(.*?)\$\$', markitdown_text, re.DOTALL):
        latex = m.group(1).strip()
        if latex:
            candidates.append({
                "latex": latex,
                "origin": "parser_latex",
                "source": "markitdown",
                "confidence": 0.7,
            })

    # From Marker (if available)
    if marker_text:
        for m in re.finditer(r'\$\$(.*?)\$\$', marker_text, re.DOTALL):
            latex = m.group(1).strip()
            if latex:
                candidates.append({
                    "latex": latex,
                    "origin": "parser_latex",
                    "source": "marker",
                    "confidence": 0.8,
                })

    # Raw formula text from all parsers
    for text, source in [(markitdown_text, "markitdown"), (pymupdf_text, "pymupdf")]:
        raw_formulas = _extract_raw_formula_text(text)
        for rf in raw_formulas:
            candidates.append({
                "latex": rf,
                "origin": "raw_formula_text",
                "source": source,
                "confidence": 0.3,
            })

    return candidates


def _extract_raw_formula_text(text: str) -> list[str]:
    """Extract raw formula text from parser output.

    Looks for patterns like:
    - Attention(Q,K,V) = Softmax(...)
    - MultiHead(Q,K,V) = ...
    - zi,j = arg max ...
    - g = −log(−log u)
    - AssDis(P,S;X)
    """
    formulas = []

    # Pattern: expression = something with math operators
    for m in re.finditer(r'([A-Za-z][A-Za-z0-9,;()\s]{5,50})\s*=\s*([^\n]{5,100})', text):
        expr = m.group(0).strip()
        # Filter out normal sentences
        if any(kw in expr.lower() for kw in ['is', 'are', 'was', 'were', 'the', 'a', 'an']):
            continue
        if len(expr) > 10:
            formulas.append(expr[:200])

    # Pattern: function calls with math content
    for m in re.finditer(r'((?:Attention|MultiHead|Softmax|argmax|argmin|KL|Gumbel|AssDis|AnomalyScore)\s*\([^)]{3,50}\))', text, re.IGNORECASE):
        formulas.append(m.group(1)[:200])

    # Deduplicate
    seen = set()
    unique = []
    for f in formulas:
        if f not in seen:
            seen.add(f)
            unique.append(f)

    return unique[:20]  # Limit to 20 candidates
