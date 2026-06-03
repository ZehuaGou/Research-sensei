# ResearchSensei v0.5 Full Redesign — Design Spec

## Decisions Summary

| Decision | Choice |
|----------|--------|
| Frontend | Vue 3 + Vite + Pinia + TailwindCSS (full separation) |
| LLM | All 8 stub modules connected at once |
| Old package | Delete `research_sensei/`, rewrite to `src/researchsensei/` |
| UI theme | Dark + Light mode, premium glass morphism style |
| Formula rendering | KaTeX, clean academic style, no decoration |
| Interaction | Text selection → floating toolbar, paragraph hover → ask button, formula click → expand |
| Visualization | D3.js concept graphs, Mermaid architecture, Vis.js knowledge maps |

---

## Architecture

```
researchsensei/
  src/
    researchsensei/          # Backend (FastAPI)
      query/
      acquisition/
      selection/
      source_resolver/
      ingestion/
      grounding/
      understanding/
      teaching/
      formula/
      direction/
      patterns/
      drill/
      interactive/
      context/
      llm/
      render/
      web/
      jobs/
      workspace/
  frontend/                   # Vue 3 SPA
    src/
      views/
      components/
      stores/
      composables/
      assets/
```

---

## Phase 1: LLM Client + 8 Module Integration

### 1.1 LLMClient (`llm/client.py`)

```python
class LLMClient:
    """Async OpenAI-compatible LLM client."""
    def __init__(self, config: ModelProviderConfig): ...
    async def chat(self, messages, *, model=None, temperature=0.7,
                   max_tokens=4096, stream=False) -> str: ...
    async def chat_stream(self, messages, **kwargs) -> AsyncIterator[str]: ...
```

- httpx async client
- timeout + retry (3 attempts, exponential backoff)
- token budget estimation
- response cache integration

### 1.2 PromptBuilder (`llm/prompt_builder.py`)

```
System Instruction → User Profile → Current Context → Evidence Chunks
→ Conversation History (compressed) → 【用户输入隔离标记】
```

- Instruction isolation: user input wrapped in delimiters
- Context window management: compress history when approaching limit
- Token budget: must-include vs optional sections

### 1.3 8 Module LLM Integration

| Module | LLM Call | Input | Output |
|--------|----------|-------|--------|
| `query` | Decompose direction, expand terms, detect cross-domain | user_query | QueryPlan |
| `selection` | Relevance judgment, role classification | candidate + query | scoring |
| `understanding` | Extract problem/old_methods/bottleneck/assumption/representation/mechanism/objective/experiments/limitations/transfer | doc + evidence | PaperSkeleton |
| `teaching` | Five-layer explanation (plain/analogy/formula/numeric/paper) | skeleton | TeachingCard |
| `formula` | Term-by-term breakdown, numeric example, remove/weight effects | formula block + nearby text | FormulaCard |
| `drill` | Generate recall/review/transfer/advisor questions + error attribution | skeleton + memory | DrillCard |
| `patterns` | Classify innovation pattern + transfer guidance | skeleton | PatternCard |
| `interactive` | Context-aware follow-up answer | InteractiveContextPackage | InteractiveAnswer |

### 1.4 Caching Strategy

- Content hash based keys
- Version invalidation (prompt_version, card_schema_version, model_name)
- Dependency cascade: paper_sections → skeleton → cards → interactive
- TTL: concepts long-term, SOTA 7 days, search 7-30 days
- Manual invalidation per paper/direction/session/all

---

## Phase 2: Backend API + Async + Persistence

### 2.1 REST API

```
POST /api/directions/search     → direction search
POST /api/papers/upload         → paper upload
POST /api/jobs/{id}/run         → start job
GET  /api/jobs/{id}/status      → job status
GET  /api/learn/{id}/bundle     → learning bundle (JSON)
GET  /api/artifacts/{id}/download → zip download
GET  /api/settings              → model config
POST /api/settings/test         → test connection
GET  /api/interactive/history   → chat history
POST /api/interactive/ask       → follow-up question
```

### 2.2 WebSocket

```
WS /ws/jobs/{id}               → real-time progress
WS /ws/interactive/{session}   → streaming LLM response
```

### 2.3 Async Pipeline

- BackgroundTasks / asyncio for long-running jobs
- pipeline_status tracking per step
- Resume from last successful step on failure
- Progress callback → WebSocket push

### 2.4 Session Persistence

- SQLite storage for SessionMemory
- Fields: understood_items, confusing_items, asked_questions, weak_concepts, review_cards, user_profile
- Cross-restart recovery

### 2.5 Logging

- Structured JSON logs
- Per-step: duration, model, token count, cache hit, errors, degraded reason, output path
- API key masking (never in logs)

---

## Phase 3: PDF Multi-layer Fallback Parsing

### Parser Chain

```
LaTeX Source (arXiv) → Docling → Marker → PyMuPDF (fallback)
```

Each layer tries, falls through on failure with warning.

### Safety

- LaTeX sandbox: disable `\input`, `\write`, `\immediate`, `\openout`
- PDF: disable script execution (PyMuPDF safe mode)
- HTML: XSS sanitization
- Parse failure never假装成功

### Output

`DocumentIngestion` with blocks:
- block_id, type (paragraph/formula/figure/table/algorithm/reference), section, page
- evidence_ref for grounding
- extraction_warnings

---

## Phase 4: Vue 3 Frontend

### 4.1 Tech Stack

- Vue 3 Composition API + `<script setup>`
- Vite build
- Pinia state management
- Vue Router
- TailwindCSS
- KaTeX (formula rendering)
- D3.js / Vis.js (concept graphs, knowledge maps)
- Mermaid (architecture diagrams)

### 4.2 Pages

| Route | Component | Description |
|-------|-----------|-------------|
| `/` | HomeView | Job list + quick actions |
| `/directions/new` | DirectionSearchView | Search direction |
| `/learn/:jobId` | LearningWorkspaceView | Main 3-pane workspace |
| `/papers/upload` | UploadView | PDF upload |
| `/settings` | SettingsView | Model config |

### 4.3 Three-Pane Layout

```
┌─────────────────────────────────────────────┐
│  Top Bar: breadcrumb | theme toggle | search │
├──────────┬──────────────────────┬───────────┤
│ Sidebar  │    Main Content      │ Ask Panel │
│ (240px)  │    (max 720px)       │ (360px)   │
│          │                      │           │
│ Nav tree │  Cards (vertical)    │ Chat hist │
│ Progress │  30s / 5min / deep   │ Quick ask │
│ Bookmarks│  Formula cards       │ Input     │
└──────────┴──────────────────────┴───────────┘
```

Mobile (<768px): stacked, bottom ask bar.

### 4.4 Key Components

**TextSelectionToolbar.vue**
- Listen mouseup → getSelection() → compute position → show floating toolbar
- Actions: ask about this / explain simpler / numeric example / free ask
- Auto-fill selection into AskPanel

**FormulaCard.vue**
- KaTeX clean rendering, no decoration
- Click to expand: symbol table + numeric example + remove/weight effects
-追问 buttons: ask / more examples / derive / remove term

**ParagraphWithAsk.vue**
- Each paragraph wrapped, hover shows ask button
- Click sends paragraph as context to AskPanel

**AskPanel.vue**
- Receives selected text automatically
- WebSocket streaming response
- Quick action buttons (没看懂/举例子/推导/导师追问)
- Chat history scroll

### 4.5 Premium UI Design

**Dark Mode**
- Background: #0a0a0f → #12121a → #1a1a28
- Cards: rgba(255,255,255,0.03) + backdrop-filter: blur(20px)
- Borders: rgba(255,255,255,0.06) thin lines
- Text: #e8e8ed / #a0a0b0 / #6b6b80

**Light Mode**
- Background: #fafafa → #f5f5f7 → #ffffff
- Cards: #ffffff + box-shadow: 0 1px 3px rgba(0,0,0,0.04)
- Borders: rgba(0,0,0,0.06)
- Text: #1d1d1f / #6e6e73 / #86868b

**Color Palette**
- Primary: #6366f1 → #8b5cf6 (indigo-purple gradient)
- Blue: #3b82f6 → #06b6d4
- Green: #10b981 → #34d399
- Yellow: #f59e0b → #fbbf24
- Red: #ef4444 → #f87171

**Typography**
- Body: Inter + Noto Sans SC, 17px, line-height 1.75
- Headings: Noto Serif SC
- Code/formulas: JetBrains Mono / KaTeX
- Max content width: 720px

**Micro-interactions**
- Card hover: translateY(-2px) + subtle glow
- Ask response: typing animation
- Page transitions: fade + slide
- Expand/collapse: smooth height
- Button press: scale(0.97)

### 4.6 Additional UX Features

**Reading Comfort**
- Font size adjust (14-22px)
- Focus mode (F key): hide sidebars
- Keyboard shortcuts (J/K navigate, Q ask, B bookmark, D theme)

**Learning Progress**
- Stats: papers read, formulas learned, streak days, mastery rate
- Achievement badges
- Daily learning goals with progress bars

**Spaced Repetition**
- FSRS algorithm integration
- Review queue (overdue/today/upcoming)

**Visualization**
- D3.js concept relationship graphs (auto-generated from skeleton)
- Mermaid architecture/flow diagrams
- Vis.js knowledge maps with cross-paper links
- Method evolution timeline

**Content Management**
- 4-color highlighting (important/concept/innovation/question)
- Bookmarks with categories
- Annotation notes
- Export: Markdown / PDF / Anki

---

## Phase 5: Security + Testing

### Security

- LaTeX sandbox (dangerous commands)
- PDF script禁用
- HTML XSS sanitization
- Prompt instruction isolation
- API key masking
- User upload controlled directory

### Testing

- Unit tests per service
- Integration tests: pipeline end-to-end
- Golden standard set: 3-15 papers with expert annotations
- Security tests: injection attacks
- Cost tests: token/latency budgets
- UI tests: layout/render/interaction

---

## Phase 6: Cleanup

- Delete `research_sensei/` old package
- Unify to `src/researchsensei/` (backend) + `frontend/` (Vue)
- Complete test coverage
- Update documentation

---

## Budgets

- Single paper deep read: < 3-5 min, < 50 API calls, < 200K-300K tokens
- Follow-up response: < 5-15 seconds
- Every artifact: generated_at, generator_version, content_hash
- Pipeline: resume from successful steps on failure
