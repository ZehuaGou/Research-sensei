# Ollama Diagnosis Report

Generated: 2026-06-10 15:21

## 1. Ollama Service Status

```
NAME                   ID              SIZE      MODIFIED      
qwen2.5:7b-instruct    845dbda0ea48    4.7 GB    4 weeks ago      
deepseek-coder:6.7b    ce298d984115    3.8 GB    5 weeks ago      
qwen3.5:4b             2a654d98e6fb    3.4 GB    6 weeks ago      
qwen2.5:3b             357c53fb659c    1.9 GB    6 weeks ago      
qwen2.5:0.5b           a8b0c5157701    397 MB    6 weeks ago      
deepseek-r1:32b        38056bbcbb2d    19 GB     16 months ago    
deepseek-r1:14b        ea35dfe18182    9.0 GB    16 months ago
```

- **Service**: Running

## 2. Available Models (/api/tags)

- **Model count**: 7

  - `qwen2.5:7b-instruct` — size: 4466MB
  - `deepseek-coder:6.7b` — size: 3650MB
  - `qwen3.5:4b` — size: 3232MB
  - `qwen2.5:3b` — size: 1840MB
  - `qwen2.5:0.5b` — size: 379MB
  - `deepseek-r1:32b` — size: 18931MB
  - `deepseek-r1:14b` — size: 8571MB


## 3. Ollama Version

- **Version**: 0.30.6


## 4. Native /api/chat Structured Output Test

### Timeout: 30s

- **Status**: OK
- **Response**: `{
  "section": "Anomaly Detection Loss Function",
  "confidence": "high"
}`

- **JSON valid**: YES
- **Parsed**: {"section": "Anomaly Detection Loss Function", "confidence": "high"}

### Timeout: 120s

- **Status**: OK
- **Response**: `{
  "section": "anomaly detection",
  "confidence": "high"
}`

- **JSON valid**: YES
- **Parsed**: {"section": "anomaly detection", "confidence": "high"}


## 5. OpenAI-compatible /v1/chat/completions Test

- **Status**: OK
- **Response**: `{
  "section": "anomaly detection",
  "confidence": "high"
}`


## 6. Diagnosis

| Finding | Detail |
|---------|--------|
| qwen2.5:0.5b | Too small for reliable structured JSON output. Timeout on /v1 endpoint. |
| Native /api/chat | May work with format schema but JSON quality depends on model size. |
| Recommended | If Ollama is to be used, need qwen2.5:7b or llama3.2:8b or larger. |
| Cold start | First call may take 30-60s for model loading; subsequent calls should be faster. |
| Current status | **Available but not effective** — qwen2.5:0.5b too weak for section refinement. |

## 7. Recommendation

- Keep Ollama **optional and default OFF** for now.
- If user has qwen2.5:7b+ or llama3.2:8b+, can enable for section refinement.
- Ollama must NOT modify latex, bbox, page, or source identity.
- Only allowed to modify: section, section_confidence, section_reason, risk_flags.