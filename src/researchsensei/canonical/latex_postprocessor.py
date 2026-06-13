r"""Regex-based LaTeX post-processor for MinerU formula cleanup.

Fixes common formatting issues from MinerU LaTeX output:
- Letter spacing in \mathbf, \text, \mathrm commands
- Extra spaces in subscripts/superscripts
- Trailing/leading spaces in LaTeX commands
"""
from __future__ import annotations

import re


# Patterns that indicate letter-spaced bold/mathbf text
_MATHBF_SPACED = re.compile(r"\\mathbf\s*\{([^}]*\s[^}]*)\}")
_TEXT_SPACED = re.compile(r"\\text\s*\{([^}]*\s[^}]*)\}")
_MATHRM_SPACED = re.compile(r"\\mathrm\s*\{([^}]*\s[^}]*)\}")

# Trailing/leading spaces inside commands: \text { x } -> \text{x}
_CMD_CONTENT_SPACES = re.compile(r"\\(mathbf|text|mathrm|mathcal|mathbb)\s*\{\s*([^{}]+?)\s*\}")

# Subscript/superscript with spaces: _ { x } -> _{x}
_SUB_SUPER_SPACED = re.compile(r"([_^])\s*\{\s*([^{}]+?)\s*\}")

# Space before subscript/superscript operator: \lambda _{1} -> \lambda_{1}
_SPACE_BEFORE_SUB_SUPER = re.compile(r"(?<=[A-Za-z0-9}\)\|])\s+([_^])")

# Space between subscript/superscript and opening brace: ^ {x} -> ^{x}
_SPACE_AFTER_SUB_SUPER = re.compile(r"([_^])\s+\{")

# Subscript/superscript containing one LaTeX command: _ { \mathrm{sta} } -> _{\mathrm{sta}}
_NESTED_CMD_SUB_SUPER_SPACED = re.compile(
    r"([_^])\s*\{\s*(\\(?:mathbf|text|mathrm|mathcal|mathbb)\{[^{}]+?\})\s*\}"
)

# Nested subscript: _ { x _ {0} } -> _{x_0}
_NESTED_SUB = re.compile(r"_\{([^{}]*?)\s*_\{([^{}]*?)\}")

# Command with space before brace: \command { -> \command{
_CMD_SPACE_BRACE = re.compile(r"(\\[a-zA-Z]+)\s+\{")

# Double spaces
_DOUBLE_SPACE = re.compile(r"  +")

_INLINE_MATH_WITH_TAG = re.compile(r"^\$(?P<body>.+?)\$\s*[.,;:]?\s*(?P<tag>\\tag\{[^}]+\})\s*$", re.DOTALL)
_INLINE_MATH_WRAPPER = re.compile(r"^\$(?P<body>.+?)\$\s*$", re.DOTALL)
_DOUBLE_ESCAPED_NORM = re.compile(r"\\\\\|")

# Plain text letter spacing (not in commands): "P r e c i s i o n" at start
_PLAIN_TEXT_SPACED = re.compile(r"^([A-Z]) ((?:[A-Z] )*[A-Z]) = ", re.MULTILINE)

_RELATION_IN_SUBSCRIPT = re.compile(r"\\(?:in|notin|leq|geq|lt|gt|mid|subset|subseteq|supset|supseteq)\b")

_KNOWN_OCR_TOKEN_REPLACEMENTS = (
    (re.compile(r"(?<![A-Za-z])t\s+2\s+v(?![A-Za-z])"), "t2v"),
    (re.compile(r"(?<![A-Za-z])i\s+f(?![A-Za-z])"), "if"),
    (re.compile(r"(?<![A-Za-z])f\s+o\s+r(?![A-Za-z])"), "for"),
    (re.compile(r"(?<![A-Za-z])R\s+e\s+L\s+U(?=\s*(?:\\left|\())"), "ReLU"),
    (re.compile(r"(?<![A-Za-z])T\s+r(?=\s*(?:=|[+\-),.]|\\left|\\right|\())"), "Tr"),
    (re.compile(r"(?<![A-Za-z])E\s+r(?=\s*(?:[_{]|[A-Za-z]*_))"), "Er"),
    (re.compile(r"(?<![A-Za-z])F\s+c(?=\s*_)"), "Fc"),
)

_CIRCLED_COMPONENT_SEQUENCE = re.compile(
    r"(?:①|\\text\{\(1\)\})\s*\+\s*(?:Ⓐ|ⓐ|\\text\{\(A\)\})"
    r"\s*-\s*(?:ⓘ|ⓙ|\\text\{\(i\)\})\s*-\s*(?:ⓘⓘ|ⓘ\s*ⓘ|ⓙ|ⓑ|Ⓤ|\\text\{\(ii\)\})"
)

_CIRCLED_LABELS = {
    "①": r"\text{(1)}",
    "②": r"\text{(2)}",
    "③": r"\text{(3)}",
    "④": r"\text{(4)}",
    "⑤": r"\text{(5)}",
    "⑥": r"\text{(6)}",
    "⑦": r"\text{(7)}",
    "⑧": r"\text{(8)}",
    "⑨": r"\text{(9)}",
    "Ⓐ": r"\text{(A)}",
    "ⓐ": r"\text{(A)}",
    "ⓘ": r"\text{(i)}",
}


def _fix_letter_spaced_command(match: re.Match) -> str:
    """Remove spaces between letters in \\mathbf{E L B O} -> \\mathbf{ELBO}."""
    command = match.group(0)
    content = match.group(1)
    # Only remove spaces if all tokens are single letters (not words)
    tokens = content.split()
    if all(len(t) == 1 and t.isalpha() for t in tokens):
        fixed = "".join(tokens)
        return command.replace(content, fixed)
    return command


def _fix_cmd_content_spaces(match: re.Match) -> str:
    """Remove trailing/leading spaces inside commands: \\text { x } -> \\text{x}."""
    cmd_name = match.group(1)
    content = match.group(2)
    return f"\\{cmd_name}{{{content}}}"


def _fix_subscript_spacing(match: re.Match) -> str:
    """Remove extra spaces in subscripts: _ { x } -> _{x}."""
    prefix = match.group(1)
    content = match.group(2)
    if _RELATION_IN_SUBSCRIPT.search(content):
        fixed = re.sub(r"\s+", " ", content.strip())
        fixed = re.sub(r"(?<=[A-Za-z0-9}])\s+\(", "(", fixed)
    else:
        # Remove spaces within simple variable/index subscripts.
        fixed = content.replace(" ", "")
    return f"{prefix}{{{fixed}}}"


def _fix_nested_command_subscript_spacing(match: re.Match) -> str:
    """Remove extra spaces around a command inside subscript/superscript braces."""
    return f"{match.group(1)}{{{match.group(2)}}}"


def _fix_nested_subscript(match: re.Match) -> str:
    """Fix nested subscripts: _{x _{0}} -> _{x_0}."""
    outer = match.group(1).strip()
    inner = match.group(2).strip()
    return f"_{outer}_{{{inner}}}"


def _fix_command_space_brace(match: re.Match) -> str:
    """Remove space between command and brace: \\mathcal { -> \\mathcal{."""
    return match.group(1) + "{"


def _fix_circled_component_sequence(match: re.Match) -> str:
    """Normalize component labels such as ① + A - i - ii."""
    return r"\text{(1)} + \text{(A)} - \text{(i)} - \text{(ii)}"


def _normalize_circled_labels(latex: str) -> str:
    """Convert non-LaTeX circled labels into explicit text labels."""
    latex = _CIRCLED_COMPONENT_SEQUENCE.sub(_fix_circled_component_sequence, latex)
    for raw, replacement in _CIRCLED_LABELS.items():
        latex = latex.replace(raw, replacement)
    return latex


def _fix_known_ocr_token_spacing(latex: str) -> str:
    """Join high-confidence OCR-split math tokens without rewriting semantics."""
    for pattern, replacement in _KNOWN_OCR_TOKEN_REPLACEMENTS:
        latex = pattern.sub(replacement, latex)
    return latex


def _strip_inline_math_wrappers(latex: str) -> str:
    """Remove redundant inline math delimiters around formula-block LaTeX."""
    stripped = latex.strip()
    match = _INLINE_MATH_WITH_TAG.match(stripped)
    if match:
        return f"{match.group('body').strip()} {match.group('tag')}"
    match = _INLINE_MATH_WRAPPER.match(stripped)
    if match:
        return match.group("body").strip()
    return latex


def postprocess_latex(latex: str) -> str:
    """Apply all regex-based fixes to a LaTeX formula string."""
    if not latex or not latex.strip():
        return latex

    result = latex

    # Formula blocks should contain LaTeX content, not nested inline-$ wrappers.
    result = _strip_inline_math_wrappers(result)

    # Normalize OCR'd circled component labels into portable LaTeX text.
    result = _normalize_circled_labels(result)

    # Guarded Ollama output can over-escape norm delimiters as \\|.
    result = _DOUBLE_ESCAPED_NORM.sub(lambda _: r"\|", result)

    # Join a small set of known OCR-split math tokens.
    result = _fix_known_ocr_token_spacing(result)

    # Fix letter-spaced mathbf/text/mathrm
    result = _MATHBF_SPACED.sub(_fix_letter_spaced_command, result)
    result = _TEXT_SPACED.sub(_fix_letter_spaced_command, result)
    result = _MATHRM_SPACED.sub(_fix_letter_spaced_command, result)

    # Fix trailing/leading spaces inside commands
    result = _CMD_CONTENT_SPACES.sub(_fix_cmd_content_spaces, result)

    # Fix command-space-brace: \mathcal { -> \mathcal{
    result = _CMD_SPACE_BRACE.sub(_fix_command_space_brace, result)

    # Remove spaces before _/^ operators.
    result = _SPACE_BEFORE_SUB_SUPER.sub(r"\1", result)
    result = _SPACE_AFTER_SUB_SUPER.sub(r"\1{", result)

    # Fix subscript/superscript that wraps one command.
    result = _NESTED_CMD_SUB_SUPER_SPACED.sub(_fix_nested_command_subscript_spacing, result)

    # Fix subscript/superscript spacing (repeated to handle nested)
    for _ in range(3):
        prev = result
        result = _SUB_SUPER_SPACED.sub(_fix_subscript_spacing, result)
        result = _NESTED_CMD_SUB_SUPER_SPACED.sub(_fix_nested_command_subscript_spacing, result)
        if result == prev:
            break

    # Collapse double spaces
    result = _DOUBLE_SPACE.sub(" ", result)

    return result.strip()
