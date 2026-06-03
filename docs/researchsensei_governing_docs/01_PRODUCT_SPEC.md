# ResearchSensei Product Specification

---

## What ResearchSensei IS NOT

| It is NOT | Why |
|-----------|-----|
| A paper summarizer | Summaries don't teach understanding |
| An auto-paper-writing system | It doesn't write papers |
| An auto-research system | It doesn't do research for you |
| A RAG chatbot | It doesn't just answer questions |
| An ARIS clone | ARIS automates research; ResearchSensei teaches reading |
| A PaperQA clone | PaperQA does QA; ResearchSensei does teaching |

---

## What ResearchSensei IS

ResearchSensei is a **paper reading tutor** — it helps graduate students and junior researchers truly understand papers, not just skim them.

| Capability | Description |
|------------|-------------|
| **Paper Reading Tutor** | Guides users through understanding a paper step by step |
| **Formula Explainer** | Breaks formulas into symbols, terms, roles, numeric examples |
| **Research Thinking Trainer** | Trains users to identify assumptions, innovations, costs, boundaries |
| **Advisor Preparation System** | Prepares users to answer advisor questions |
| **Evidence-Constrained System** | Every explanation must be backed by evidence from the paper |

---

## User Input

| Input Type | Example |
|------------|---------|
| Single paper | Upload PDF/Markdown, or provide arXiv ID/URL |
| Research direction | "time series anomaly detection" (Chinese or English) |

---

## System Output

### Single Paper → 7 Artifacts

1. `source_status.json` — source resolution status
2. `parsed_document.json` — document blocks
3. `evidence_index.json` — evidence binding
4. `paper_skeleton.json` — paper structure
5. `paper_card.json` — paper learning card
6. `formula_cards.json` — formula explanation cards
7. `teaching_cards.json` — five-layer teaching cards

### Research Direction → 4 Artifacts

1. `query_plan.json` — search plan
2. `candidate_pool.json` — raw candidates
3. `filtered_candidates.json` — deduplicated candidates
4. `reading_plan.json` — prioritized reading list

---

## What "Good" Means

A "good" explanation in ResearchSensei must:

1. Be grounded in evidence (evidence_ref exists and is valid)
2. Be faithful to the paper (no fabrication)
3. Be understandable (not just copied from the paper)
4. Include formula breakdown (symbols, terms, role)
5. Include research thinking (assumptions, innovations, costs)
6. Handle uncertainty (degrade when unsure)
7. Be non-generic (contain paper-specific terms)

See `docs/QUALITY_EVALUATION_SPEC.md` for the full scoring rubric.

---

## Current Baseline vs Future v2

| Aspect | Current (Phase 1-11) | Future (Phase 11.6-11.9) |
|--------|---------------------|--------------------------|
| PDF parsing | PyMuPDF fallback | ParserAdapter (Docling/Nougat optional) |
| Evidence level | block-level | passage-level + claim extraction |
| Card builders | rule-based baseline | evidence-constrained LLM |
| Formula symbols | generic dictionary | paper-context grounding |
| Teaching quality | template-based | evidence-constrained five-layer |
| Audit | none | explanation + formula + evidence audit |

**Important**: Current Phase 8-10 rule-based builders are **baseline**, not final product. They produce degraded output (UNKNOWN fields, template text) when input is insufficient. This is by design — the system degrades honestly rather than fabricating.
