# ResearchSensei Design Overview

This file is a compact design overview. It is not the authoritative status
source; `docs/STATUS.md` is. If this file and `docs/STATUS.md` disagree,
`docs/STATUS.md` wins.

## Product Shape

ResearchSensei is a research-reading system with three implemented readiness
surfaces:

1. M1 discovers papers for a research direction, resolves legal full text, and
   hands source-backed candidates to PaperWorkspace.
2. M2 converts paper material into evidence-backed understanding artifacts and
   card components, with formula provenance and QualityAuditor gates.
3. M3 renders the direction, seed-expansion, and PaperWorkspace states without
   leaking blocked or baseline-only explanatory cards.

M4 interactive tutoring, advisor chat, drills, and long-term memory are out of
scope for current readiness work.

## Runtime Flow

```text
direction query
  -> multi-source acquisition
  -> legal fulltext resolver
  -> DirectionBundle
  -> SeedExpansionBundle
  -> deep_read handoff
  -> arXiv source / PDF / OA PDF
  -> M2 parse and understanding pipeline
  -> understanding_status
  -> gated /cards
  -> PaperWorkspace
```

## M1 Design

M1 is source-aware and legality-aware:

- arXiv search, source/e-print download, and PDF fallback.
- OpenAlex, Semantic Scholar, Crossref, DBLP, and Unpaywall contribute to the
  candidate pool and metadata/full-text fallback.
- FullTextResolver chooses legal source/PDF/HTML readiness and keeps
  metadata-only high-value papers with `needs_user_upload=true`.
- Dedup preserves `discovery_sources`, source IDs, DOI, arXiv ID, and OA PDF
  evidence instead of collapsing everything into arXiv-only candidates.
- Direction Exploration and Seed Expansion are minimal DEGRADED_SMOKE loops,
  not broad M1 completion.

## M2 Design

M2 is fail-closed:

- Parsed documents become passage indexes, claim evidence, evidence packs,
  paper cards, formula cards, teaching cards, quality reports, and
  understanding status artifacts.
- QualityAuditor and FSA-5 must not be relaxed.
- `source_latex` formula provenance permits detailed formula explanation when
  evidence is present.
- `unknown` or weak formula provenance cannot produce detailed derivations.
- DEGRADED_STRUCTURAL may expose only successful components; BLOCKED,
  BASELINE_ONLY, and FAILED must not expose explanatory cards.

## M3 Design

M3 renders status before cards:

- LearningWorkspace first requests `/understanding_status`.
- Only SUCCESS and DEGRADED_STRUCTURAL may request `/cards`.
- DEGRADED_STRUCTURAL shows missing components, degradation reasons, warnings,
  formula provenance, evidence status, and component status.
- BLOCKED_UNDERSTANDING, BASELINE_ONLY, and FAILED show status only and keep
  explanatory cards hidden.
- `/artifacts` is debug/admin oriented and must not become the normal user data
  path.

## Parser And Canonical Rules

- MinerU2.5-Pro via mineru-vl-utils is the primary M1 parser.
- Marker is fallback/audit baseline.
- Ollama is an optional structured refiner.
- Ollama must not modify latex, bbox, page, or source identity.
- M1 gate blocks all-formulas-in-Abstract.
- M1 gate blocks section contradiction.
- M1 gate blocks missing latex/crop/overlay.

## External Tool Position

External projects and services are adapters or strategy references only.
ResearchSensei keeps its own schemas, provenance gates, and UI gating. Do not
replace the project with DeepXiv, PaperQA, ARIS, MinerU, Marker, or any search
tool clone.
