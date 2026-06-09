# Ollama Structured Refiner Eval

- Endpoint: native `/api/chat` through `OllamaStructuredClient`
- Format: JSON Schema, temperature=0
- Cached paper_4_unseen eval: JSON valid=0, invalid=17
- Current local smoke: model=qwen2.5:0.5b, sample=12 paper_4 blocks, timeout_seconds=20, available=True, JSON valid=0, invalid=1, timeout=1, changed_by_count=0
- Decision: Ollama is implemented as optional structured refiner only; it is not enabled by default and cannot modify latex, bbox, page, or source identity.
