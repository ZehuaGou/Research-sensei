from __future__ import annotations

import subprocess
from pathlib import Path


TEXT_EXTENSIONS = {
    ".css",
    ".html",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".ts",
    ".tsx",
    ".vue",
    ".yml",
    ".yaml",
}


def test_tracked_text_files_do_not_contain_utf8_gbk_mojibake() -> None:
    """Catch real mojibake saved in tracked source/docs, not terminal display issues."""
    result = subprocess.run(
        ["git", "ls-files"],
        check=True,
        capture_output=True,
        text=True,
    )
    offenders: list[str] = []
    for raw_path in result.stdout.splitlines():
        path = Path(raw_path)
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            offenders.append(f"{raw_path}: not valid UTF-8")
            continue
        matches = [marker for marker in _mojibake_markers() if marker and marker in text]
        if matches:
            offenders.append(f"{raw_path}: {matches[:3]}")

    assert offenders == []


def _mojibake_markers() -> list[str]:
    normal_snippets = [
        "\u8fd9\u662f",  # this is
        "\u6ca1\u6709\u6536\u5230",  # did not receive
        "\u89e3\u91ca\u8bc1\u636e",  # explain evidence
        "\u7814\u7a76\u95ee\u9898",  # research problem
        "\u6838\u5fc3\u60f3\u6cd5",  # core idea
        "\u65b9\u6cd5\u673a\u5236",  # method mechanism
        "\u5b9e\u9a8c\u7ed3\u8bba",  # experiment conclusion
        "\u8bba\u6587\u52a9\u6559",  # paper tutor
        "\u516c\u5f0f\u5361\u7247",  # formula card
        "\u5bf9\u5e94\u8bc1\u636e",  # corresponding evidence
    ]
    markers: set[str] = set()
    for snippet in normal_snippets:
        encoded = snippet.encode("utf-8")
        for codec in ("gbk", "cp936"):
            try:
                markers.add(encoded.decode(codec))
            except UnicodeDecodeError:
                markers.add(encoded.decode(codec, errors="ignore"))
                markers.add(encoded.decode(codec, errors="replace"))
    markers.discard("")
    markers.update({
        "\u9205",  # common mojibake for curved quote bytes
        "\u9286",  # common mojibake for Chinese punctuation bytes
        "\u951b",  # common mojibake for full-width colon/comma bytes
        "\ufffd",  # Unicode replacement character
    })
    return sorted(markers, key=len, reverse=True)
