# M4 Interactive Learning Contract

M4 v1 is implemented for PaperWorkspace. It is not a raw-PDF chatbot; it is an
evidence-bound tutor over M2 artifacts.

## Implemented

- Backend service: `src/researchsensei/m4/service.py`
- Schemas: `src/researchsensei/schemas/m4.py`
- API routes:
  - `POST /api/v1/jobs/{job_id}/selection/explain`
  - `POST /api/v1/jobs/{job_id}/formula/explain`
  - `POST /api/v1/jobs/{job_id}/ask`
  - `POST /api/v1/jobs/{job_id}/advisor/question`
  - `POST /api/v1/jobs/{job_id}/advisor/evaluate`
  - `GET /api/v1/jobs/{job_id}/memory`
  - `DELETE /api/v1/jobs/{job_id}/memory`
- Frontend:
  - `AskPanel.vue`
  - `TextSelectionToolbar.vue`
  - Paper/formula card M4 actions
- Memory artifact: `m4_memory.json`

## Runtime Rules

- M4 reads user-facing M2 artifacts only: paper card, formula cards, teaching
  cards, passage index, claim evidence, evidence index, and previous M4 memory.
- M4 controls mount only when `/cards` is allowed.
- Answers must cite allowed evidence refs when evidence is available.
- Non-paper/off-task prompts such as weather, jokes, code writing, travel
  booking, or creative writing are rejected as `DEGRADED` without calling the
  LLM or writing M4 memory.
- If the configured LLM answer is missing, invalid, empty, or cites unknown
  evidence refs, M4 falls back to deterministic artifact answers and emits a
  warning.
- The configured live LLM path uses ccswitch by default. M4 tutor calls pass a
  route-specific override of `disable_thinking=True`, `max_tokens=2400`, and
  `timeout=90` so interactive answers fail over quickly to deterministic
  evidence-card responses when the live model is unavailable or invalid.
- User-facing M4 text is Chinese by default.

## Frontend Interaction

- Selected text opens a toolbar with `追问`, `讲简单点`, and `举例`.
- The toolbar is positioned from the selected text rectangle and clamped to the
  viewport so it is less likely to overlap Edge's native selection menu.
- The right M4 panel behaves like a tutor chat, not a debug console.
- Memory count and evidence refs are visible in Chinese.

## Not Yet Implemented

- Direction-level interactive chat.
- Seed-expansion interactive chat.
- PaperQA/vector-memory adapter.
- Full drill/pattern generation beyond advisor v1.
- Broad live M4 acceptance matrix.

## Validation

- `tests/test_m4_api.py` covers backend gating, fallback, evidence validation,
  advisor, and memory behavior.
- `frontend/src/components/tests/AskPanel.spec.ts` covers frontend M4 chat,
  memory, selected text, and advisor request flow.
