from __future__ import annotations

import hashlib

from researchsensei.schemas import JobRecord


def learning_seeds(
    job: JobRecord,
    artifacts: dict[str, object],
) -> list[dict[str, object]]:
    paper_card = _as_dict(artifacts.get("paper_card"))
    paper_title = _text(paper_card.get("title") or paper_card.get("paper_title"))
    if not paper_title:
        paper_title = job.source_path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1] or job.job_id
    seeds: list[dict[str, object]] = []

    paper_fields = (
        ("problem", "paper", "研究问题"),
        ("core_idea", "concept", "核心思想"),
        ("method_overview", "method", "方法机制"),
        ("experiment_summary", "experiment", "实验结论"),
        ("limitations", "limitation", "局限性"),
    )
    for field, item_type, label in paper_fields:
        claim = _as_dict(paper_card.get(field))
        excerpt = _usable_text(claim.get("text"))
        refs = _refs(claim.get("evidence_ref"))
        if excerpt and refs:
            seeds.append(_seed(job.job_id, paper_title, item_type, label, excerpt, refs))

    teaching_bundle = _as_dict(artifacts.get("teaching_cards"))
    teaching_cards = teaching_bundle.get("teaching_cards", [])
    if isinstance(teaching_cards, list):
        for raw_card in teaching_cards[:16]:
            card = _as_dict(raw_card)
            title = _usable_text(card.get("title"))
            refs = _refs(card.get("evidence_refs") or card.get("evidence_ref"))
            excerpt = _join_usable(
                card.get("human_explanation"),
                card.get("paper_role_explanation"),
                limit=1800,
            )
            if title and excerpt and refs:
                item_type = _normalized_item_type(card.get("target_type"))
                seeds.append(_seed(job.job_id, paper_title, item_type, title, excerpt, refs))

    formula_bundle = _as_dict(artifacts.get("formula_cards"))
    formula_cards = formula_bundle.get("formula_cards", artifacts.get("formula_cards"))
    if isinstance(formula_cards, list):
        for index, raw_card in enumerate(formula_cards[:10], start=1):
            card = _as_dict(raw_card)
            refs = _refs(card.get("evidence_ref"))
            excerpt = _join_usable(
                card.get("original_latex") or card.get("formula_latex") or card.get("formula_raw"),
                card.get("purpose"),
                card.get("plain_summary"),
                limit=1800,
            )
            if not excerpt or not refs:
                continue
            title = _usable_text(card.get("display_title")) or f"公式 {index}"
            seeds.append(_seed(job.job_id, paper_title, "formula", title, excerpt, refs))

    unique: dict[str, dict[str, object]] = {}
    for seed in seeds:
        unique[str(seed["item_id"])] = seed
    return list(unique.values())


def item_type_label(value: str) -> str:
    return {
        "paper": "研究问题",
        "concept": "核心概念",
        "method": "方法机制",
        "formula": "公式含义与作用",
        "experiment": "实验结论",
        "limitation": "论文局限",
    }.get(value, "论文内容")


def _seed(
    job_id: str,
    paper_title: str,
    item_type: str,
    target_concept: str,
    source_excerpt: str,
    evidence_refs: list[str],
) -> dict[str, object]:
    identity = "\x1f".join((job_id, item_type, target_concept, source_excerpt[:500]))
    item_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
    return {
        "item_id": item_id,
        "job_id": job_id,
        "paper_title": paper_title,
        "item_type": item_type,
        "target_concept": target_concept,
        "source_excerpt": source_excerpt,
        "evidence_refs": evidence_refs,
    }


def _normalized_item_type(value: object) -> str:
    text = _text(value).lower()
    return (
        text
        if text in {"paper", "concept", "method", "formula", "experiment", "limitation"}
        else "concept"
    )


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _text(value: object) -> str:
    return str(value or "").strip()


def _usable_text(value: object) -> str:
    text = _text(value)
    if not text or text.upper() == "UNKNOWN":
        return ""
    if "证据不足" in text or "暂不展开" in text:
        return ""
    return text


def _join_usable(*values: object, limit: int) -> str:
    return "\n\n".join(filter(None, (_usable_text(value) for value in values)))[:limit]


def _refs(value: object) -> list[str]:
    values = value if isinstance(value, list) else [value]
    result: list[str] = []
    for item in values:
        text = _text(item)
        if text and text not in result:
            result.append(text)
    return result
