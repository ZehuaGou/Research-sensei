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
_SPACE_BEFORE_SUB_SUPER = re.compile(r"(?<=[A-Za-z0-9}\)])\s+([_^])")

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

# Plain text letter spacing (not in commands): "P r e c i s i o n" at start
_PLAIN_TEXT_SPACED = re.compile(r"^([A-Z]) ((?:[A-Z] )*[A-Z]) = ", re.MULTILINE)


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
    # Remove spaces within the content for simple subscripts
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


def postprocess_latex(latex: str) -> str:
    """Apply all regex-based fixes to a LaTeX formula string."""
    if not latex or not latex.strip():
        return latex

    result = latex

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
