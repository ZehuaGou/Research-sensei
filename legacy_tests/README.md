# Legacy Tests

This directory contains tests from the old `backend/` package that has been frozen as a migration source.

These tests import from `backend.*` and test code that has NOT been migrated to `src/researchsensei/`.

## Status

These tests are NOT run by default `pytest`. They are preserved as:

- Migration reference (what the old code did)
- Feature reference (what capabilities existed in v0.5)
- Behavioral reference (expected inputs/outputs for future migration)

## Running

```bash
# These require the old backend/ package to be on PYTHONPATH
python -m pytest legacy_tests/ -v
```

## Migration Status

| Test file | Old module | Migrated to researchsensei? |
|-----------|-----------|---------------------------|
| test_drill_llm.py | backend.drill | No (Phase 8+) |
| test_formula_llm.py | backend.formula | No (Phase 8+) |
| test_interactive_llm.py | backend.interactive | No (Phase 8+) |
| test_patterns_llm.py | backend.patterns | No (Phase 8+) |
| test_query_llm.py | backend.query | No (Phase 8+) |
| test_teaching_llm.py | backend.teaching | No (Phase 8+) |
| test_understanding_llm.py | backend.understanding | No (Phase 8+) |
| test_v05_*.py | Various backend modules | Partially (Phase 1-7 infra) |
