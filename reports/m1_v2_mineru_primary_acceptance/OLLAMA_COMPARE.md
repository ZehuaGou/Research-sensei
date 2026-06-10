# Ollama Structured Refiner Compare

Scope: M1 v2 only. This report evaluates optional Ollama section/risk refinement on the two MinerU primary acceptance papers; it does not feed the acceptance artifacts.

- endpoint: /api/chat
- format: JSON Schema
- temperature: 0
- invalid JSON retry: max_retries=1
- forbidden mutations: latex, bbox, page, source
- default route decision: disabled by default; RuleBasedStructureRefiner remains the acceptance path.

| paper | available | model | valid | invalid | retry | timeout | changed_by | risk_changes | forbidden | warnings |
| ----- | --------- | ----- | ----: | ------: | ----: | ------: | ---------: | -----------: | --------: | -------- |
| 2310_08800v2 | True | qwen2.5:0.5b | 0 | 1 | 0 | 1 | 0 | 0 | 0 | ollama_timeout, ollama_noop_invalid_json |
| 2508_11528v1 | True | qwen2.5:0.5b | 0 | 1 | 0 | 1 | 0 | 0 | 0 | ollama_timeout, ollama_noop_invalid_json |

## Sample Section Changes

### 2310_08800v2
- none

### 2508_11528v1
- none
