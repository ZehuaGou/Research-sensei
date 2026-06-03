# End-to-End Tests

This directory contains end-to-end and smoke tests that require a running server or real external services.

These tests are NOT run by default `pytest`. They must be run manually when a server is available.

## Running

```bash
# Start the server first
uvicorn researchsensei.web.app:app --port 18765

# Then run e2e tests
python -m pytest tests_e2e/ -v
```

## Tests

| Test file | Requirement |
|-----------|------------|
| smoke_test.py | Running server on http://127.0.0.1:18765 |
