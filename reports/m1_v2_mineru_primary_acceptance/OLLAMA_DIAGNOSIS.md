# Ollama Diagnosis Report

Generated: 2026-06-10 15:40

## Models Tested

| Model | Prompt | Timeout | JSON Valid | Latency (s) | Response |
|-------|--------|---------|:---:|---:|---|
| qwen2.5:7b-instruct | simple | 120s | YES | 11.0 | {"section": "Method", "confidence": "high"} |
| qwen2.5:7b-instruct | medium | 120s | YES | 3.0 | {"section": "Method", "confidence": "high"} |
| qwen2.5:7b-instruct | real_slot | 120s | YES | 3.6 | {"section": "Method", "confidence": "high", "reason": "The text describes a loss |
| qwen3.5:4b | simple | 120s | YES | 47.4 | {"section": "Method", "confidence": "high"} |
| qwen3.5:4b | medium | 120s | YES | 49.3 | {"section": "Method", "confidence": "high"} |
| qwen3.5:4b | real_slot | 120s | YES | 32.5 | {"section": "Method", "confidence": "high", "reason": "The text explicitly defin |

## Diagnosis

| Finding | Detail |
|---------|--------|
| qwen2.5:7b-instruct | 4.7GB model, should handle real FormulaSlot prompts. |
| qwen3.5:4b | 3.4GB model, may struggle with complex prompts. |
| Native /api/chat | Works with JSON Schema format. Temperature=0 for deterministic output. |
| Cold start | First call may take 30-60s for model loading. |

## Recommendation

- **qwen2.5:7b-instruct works for real FormulaSlot prompts.** JSON valid=YES for all 3 prompt sizes. Latency 3-11s warm, acceptable.
- **Ollama can be effective with 7b+ models.** qwen2.5:7b-instruct is the recommended model.
- Keep Ollama optional and default OFF for now. Can be enabled for section refinement.
- Ollama must NOT modify latex, bbox, page, or source identity. Only allowed: section, section_confidence, section_reason, risk_flags.