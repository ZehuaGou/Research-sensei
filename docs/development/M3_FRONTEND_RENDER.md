# Frontend Render 模块（M3）

---

## 1. 模块目标

定义前端/API 展示规则，确保用户只看到符合 understanding_status 的内容，并能看见 source / canonicalization / formula / evidence 状态。

## 2. 非目标

- 不实现 audit 内部逻辑（M2.4 负责）
- 不实现 evidence 内部实现（M2.2 负责）
- 不改 backend 核心逻辑
- 不隐藏 canonicalization、formula_origin、formula_ocr_status、evidence_status 降级信息

## 3. 产品流程位置

M3 是用户界面层：M1/M2 生成 source/canonical/evidence/cards 状态 → M3 API gating → 前端展示。

```
M1 canonicalization + M2 pipeline 完成
  → understanding_status.json + cards artifacts 写入
    → M3.1 API endpoints (understanding_status / cards / artifacts)
      → M3.3 LearningWorkspaceView 读取 status + cards
        → M3.4 StatusBanner + cards 渲染
          → 用户看到受控展示
```

### 核心原则

- 前端/API 必须先读取 understanding_status
- 普通用户不能绕过 understanding_status 直接展示 card
- card 是否展示由 status + component_status + allowed_downstream 决定
- source/canonical/formula/evidence 状态必须展示，不得只展示 paper_card
- BLOCKED_UNDERSTANDING 时绝对不能展示解释性 card 内容
- BASELINE_ONLY 普通用户不能当作最终理解展示
- M3 has three frontend areas: DirectionWorkspace, PaperWorkspace, SeedExpansionPanel — parallel capabilities, not replacements

### DirectionWorkspace

Displays:
- direction search input
- survey candidates
- direction framework
- method families
- chronology stages
- landscape anchors
- recommended reading order
- deep-read buttons

Status: NOT_IMPLEMENTED

### PaperWorkspace

Displays:
- upload PDF
- input paper title / DOI / arXiv / URL
- download/verification status
- source_type
- canonicalization_status
- m2_ready
- degradation_reason
- formula_origin
- formula_ocr_status
- evidence_status
- paper_card
- formula_cards
- teaching_cards
- evidence_refs
- quality status
- find-upstream/downstream button

### SeedExpansionPanel

Displays:
- upstream papers
- downstream papers
- related surveys
- follow-up improvements
- same-route papers
- one-click deep-read buttons

Status: NOT_IMPLEMENTED

DirectionWorkspace, PaperWorkspace, and SeedExpansionPanel are parallel frontend capabilities, not replacements.

## 4. Direction / Paper / Seed API Contract

### DirectionWorkspace future APIs

**POST /api/v1/directions/search**

input:
- `direction_query`
- `max_surveys`
- `max_papers`
- `prefer_surveys: true`

output:
- `job_id`
- `status`
- `survey_candidates`
- `direction_landscape_status`

**GET /api/v1/directions/{direction_job_id}/landscape**

output:
- `direction_landscape`
- `survey_candidates`
- `method_families`
- `chronology_stages`
- `landscape_anchors`
- `recommended_reading_order`

Status: DOC_DESIGNED / NOT_IMPLEMENTED

### PaperWorkspace APIs

Existing:
- `POST /api/v1/documents/parse`

Future accepted inputs:
- upload PDF
- title
- DOI
- arXiv ID
- arXiv URL
- PDF URL
- publisher URL

M3 must show:
- `download_status`
- `verification_status`
- `pdf_metadata_check`
- `pdf_title_match`
- `can_enter_m2`
- `source_type`
- `source_confidence`
- `canonicalization_status`
- `m2_ready`
- `degradation_reason`
- `formula_origin`
- `formula_ocr_status`
- `evidence_status`

Status: PARTIAL_CODE / PAGE_REAL_VALIDATION_MISSING

### SeedExpansionPanel future APIs

**POST /api/v1/papers/{paper_id}/expand**

input:
- `paper_id`
- `expansion_types`: cited_by / references / related_surveys / follow_up / same_route

output:
- `seed_expansion_result`
- `paper_relation_graph`

Status: DOC_DESIGNED / NOT_IMPLEMENTED

## External Projects / Adapter Candidates

| 项目 | 对应模块 | 具体能力 | 可复用文件/函数/CLI | 接入方式 | 是否默认依赖 | 风险 | 当前状态 |
|---|---|---|---|---|---|---|---|
| Vue 3 | M3 | 前端工作台框架 | `frontend/src/views/*`, Vue SFC APIs | DIRECT_DEPENDENCY | 是 | 不能重写成 React；需保持现有架构 | IMPLEMENTED |
| Vitest | M3 / M5 | 组件级测试 | `vitest`, `frontend/src/components/tests/*` | DIRECT_DEPENDENCY | 是 | 组件测试不能替代真实页面级验收 | IMPLEMENTED |
| Vue Test Utils | M3 | Vue 组件测试 | `@vue/test-utils`, mount APIs | DIRECT_DEPENDENCY | 是 | 只适合组件级断言 | IMPLEMENTED |
| Playwright | M3 / M5 | 真实页面级 E2E；DirectionWorkspace / PaperWorkspace / SeedExpansionPanel 页面验收 | `playwright test`, page navigation/click/screenshot APIs；必须调研 Vite dev server fixture、后端 API fixture、trace/screenshot artifacts | DIRECT_DEPENDENCY | 否 | 浏览器依赖和运行时间；不得替代后端契约测试 | DOC_DESIGNED |

## 6. 当前代码位置

### 后端 API

- `src/researchsensei/web/app.py` — FastAPI endpoints

### 前端

- `frontend/src/views/UploadView.vue` — 上传页面
- `frontend/src/views/LearningWorkspaceView.vue` — 学习工作区
- `frontend/src/components/StatusBanner.vue` — 状态提示组件

### 测试

- `frontend/src/components/tests/StatusBanner.spec.ts` — StatusBanner 7 tests
- `tests/test_api_status_gating.py` — API status gating 15 tests

## 7. API 端点

### POST /api/v1/documents/parse

| 项 | 值 |
|----|-----|
| 输入 | FormData（file）或 local_path / pdf_url / arxiv_id / arxiv_url |
| 输出 | `{ job_id, status, current_step, artifacts, warnings, degraded }` |
| 前端调用 | UploadView 提交后跳转 `/learn/{job_id}` |

### GET /api/v1/jobs/{job_id}/understanding_status

| 项 | 值 |
|----|-----|
| 输入 | job_id |
| 输出 | understanding_status artifact content |
| 404 | artifact 不存在 |
| 前端调用 | LearningWorkspaceView mount 时首先调用 |

### GET /api/v1/jobs/{job_id}/cards

| 项 | 值 |
|----|-----|
| 输入 | job_id |
| 输出 | paper_card + formula_cards + teaching_cards（按 status gating） |
| 403 | BASELINE_ONLY / BLOCKED_UNDERSTANDING / FAILED |
| 409 | SUCCESS/DEGRADED 但 required cards 缺失 |
| 前端调用 | LearningWorkspaceView 在 status 为 SUCCESS/DEGRADED 时调用 |

### GET /api/v1/jobs/{job_id}/artifacts

| 项 | 值 |
|----|-----|
| 输入 | job_id |
| 输出 | raw artifacts（debug/admin only） |
| 403 | SENSEI_DEBUG 未启用时 |
| 前端调用 | 普通前端不调用此端点 |

### GET /api/v1/jobs

| 项 | 值 |
|----|-----|
| 输入 | limit（可选，默认 20） |
| 输出 | job 列表 |

### GET /api/v1/jobs/{job_id}

| 项 | 值 |
|----|-----|
| 输入 | job_id |
| 输出 | job 详情 |
| 404 | job 不存在 |

### GET /health

| 项 | 值 |
|----|-----|
| 输出 | `{ "status": "ok", "service": "researchsensei" }` |

## 8. 前端组件

### UploadView（M3.2）

| 项 | 值 |
|----|-----|
| 输入 | 用户选择的 PDF 文件 |
| 调用 | POST /api/v1/documents/parse（FormData） |
| 成功 | 跳转 `/learn/{job_id}` |
| 失败 | 显示错误提示 |

### LearningWorkspaceView（M3.3）

| 项 | 值 |
|----|-----|
| 输入 | job_id（从路由参数） |
| 调用1 | GET /understanding_status |
| 调用2 | GET /cards（仅当 status 为 SUCCESS/DEGRADED） |
| 渲染 | StatusBanner + 成功组件 cards |
| 必须显示 | source_type, canonicalization_status, m2_ready, degradation_reason, formula_origin, formula_ocr_status, evidence_status |

### StatusBanner（M3.4）

| 状态 | 样式 | 内容 |
|------|------|------|
| BASELINE_ONLY | amber warning | 无 LLM 配置提示 |
| BLOCKED_UNDERSTANDING | red error | blocking_reason + warnings |
| DEGRADED_STRUCTURAL | indigo warning | missing components 列表 |
| FAILED | red error | 重新上传提示 |

StatusBanner must also show:
- `canonicalization_status`
- `m2_ready`
- `degradation_reason`
- formula extraction / OCR degradation when formula cards are unavailable

## 9. status 展示规则

### SUCCESS

- 展示 paper_card / formula_cards / teaching_cards 中成功组件
- 可称为"导师级解释"（前提是 paper_card、formula_cards、teaching_cards 都成功）
- formula_cards 为 SKIPPED（论文无公式）时，不展示公式区，不算失败
- 展示 source/canonical 状态
- formula card 上显示 formula_origin / formula_ocr_status

### DEGRADED_STRUCTURAL

- 只展示成功组件
- 失败组件隐藏，并显示明显降级提示
- teaching_cards FAILED 时，只能称为"论文理解"或"结构化理解"，不能称为"导师级解释"
- formula_cards optional failed 时，隐藏公式区并显示"公式讲解不可用 / DEGRADED"
- advisor_questions 由 `allowed_downstream.advisor_questions` 决定；teaching_cards FAILED 时倾向 False
- 展示 `canonicalization_status=degraded`、`degradation_reason`
- 展示 parser/OCR/reconstructed/unknown 公式来源提示

### BASELINE_ONLY

- 普通用户不展示 cards
- 只展示"基线模式：当前结果仅供诊断，不是最终论文理解"
- debug/admin 模式可查看 baseline cards
- 如果 canonical/evidence 状态可用，普通用户可看到状态摘要，但不能把 baseline card 当最终学习内容

### BLOCKED_UNDERSTANDING

- 不展示 paper_card / formula_cards / teaching_cards
- 只展示 blocking_reason、warnings、必要 diagnostic metadata
- 不展示解释性内容
- 展示 canonicalization_status、m2_ready、evidence_status、formula_origin failure when relevant

### FAILED

- 展示系统错误
- 不展示 cards

## 10. component_status 展示规则

```
component_status:
  paper_card: SUCCESS / FAILED / BASELINE
  formula_cards: SUCCESS / SKIPPED / FAILED / BASELINE
  teaching_cards: SUCCESS / FAILED / BASELINE
  audit: SUCCESS / FAILED
```

| 组件状态 | 展示行为 |
|---------|---------|
| SUCCESS | 可展示 |
| SKIPPED | 隐藏，不算失败 |
| FAILED | 隐藏，显示对应降级提示 |
| BASELINE | 普通用户隐藏，debug/admin 可看 |

Formula provenance display:

| formula_origin | 展示行为 |
|---|---|
| source_latex | source badge |
| parser_latex | parser badge + warning |
| ocr_latex | OCR badge + confidence warning |
| reconstructed | speculative badge |
| unknown | hide detailed derivation, show unavailable status |

## 11. /cards API 行为

| status | 行为 |
|--------|------|
| SUCCESS | 返回成功 cards |
| DEGRADED_STRUCTURAL | 只返回成功组件 cards，返回 `degraded: true` + `missing_components` |
| BASELINE_ONLY | 普通用户返回 403；debug/admin 可返回 baseline cards |
| BLOCKED_UNDERSTANDING | 返回 403 + blocking_reason + warnings |
| FAILED | 返回 403，不返回 card 内容 |

## 12. /artifacts 权限与 /quality_report 状态

- `/artifacts` 定位为 debug/admin raw API
- `/quality_report` endpoint 当前未实现
- `quality_report.json` 当前只能通过 debug/admin raw artifacts（`/artifacts`）查看
- 普通用户不能访问完整 QualityReport
- 若新增 `/quality_report` endpoint，必须走正式 debug/admin 鉴权
- 普通前端不应直接用 `/artifacts` 展示 cards
- `/cards` 是用户端展示 card 的唯一受控 API
- production 必须有鉴权；本地开发可通过 `SENSEI_DEBUG=1`

## 13. evidence_ref 跳转（设计中）

- evidence_ref 跳转依赖 `parsed_document.json` + `passage_index.json` + `claim_evidence.json`
- 前端可通过 evidence_ref / passage_id 定位 passage_text 和 block_ids
- 初版可以只支持 passage 级定位，精确 bbox/page 跳转留给外部 parser 接入后
- `passage_index.json` 是 evidence 跳转的关键 artifact
- 当前未实现

## 14. 错误策略

| 场景 | API 行为 | 前端行为 |
|------|----------|----------|
| job 不存在 | 404 | 显示"任务不存在" |
| understanding_status 缺失 | 404 | 显示"理解状态未生成" |
| BASELINE_ONLY + 普通用户访问 /cards | 403 | StatusBanner 显示基线提示 |
| BLOCKED + 普通用户访问 /cards | 403 | StatusBanner 显示阻塞原因 |
| SUCCESS 但 cards 缺失 | 409 | 显示"卡片生成不完整" |
| DEGRADED 但 required cards 缺失 | 409 | 显示降级 + 缺失组件 |
| SENSEI_DEBUG 未启用访问 /artifacts | 403 | 不展示 |
| 前端 fetch 失败 | — | 显示错误提示 |

## 15. 测试要求

### M3.1 后端 API 测试

| 测试 | 断言 |
|------|------|
| test_parse_endpoint_returns_job_id | POST /parse → 200 + job_id |
| test_understanding_status_endpoint | GET /understanding_status → status content |
| test_cards_success_returns_all | SUCCESS → paper_card + formula_cards + teaching_cards |
| test_cards_degraded_returns_success_only | DEGRADED → only successful components |
| test_cards_baseline_returns_403 | BASELINE_ONLY → 403 |
| test_cards_blocked_returns_403 | BLOCKED → 403 + blocking_reason |
| test_cards_failed_returns_error | FAILED → error response |
| test_cards_success_missing_returns_409 | SUCCESS but card missing → 409 |
| test_artifacts_no_debug_returns_403 | SENSEI_DEBUG off → 403 |
| test_artifacts_debug_enabled | SENSEI_DEBUG on → raw artifacts |
| test_jobs_list_endpoint | GET /jobs → job list |
| test_job_detail_endpoint | GET /jobs/{id} → job detail |
| test_health_endpoint | GET /health → ok |

### M3.2 UploadView 测试

| 测试 | 断言 |
|------|------|
| test_upload_sends_formdata | POST called with FormData |
| test_upload_success_redirects | 200 → redirect to /learn/{job_id} |
| test_upload_failure_shows_error | error → error message displayed |

### M3.3 LearningWorkspaceView 测试

| 测试 | 断言 |
|------|------|
| test_workspace_fetches_status | understanding_status fetched on mount |
| test_workspace_fetches_cards_when_success | SUCCESS → cards fetched |
| test_workspace_fetches_cards_when_degraded | DEGRADED → cards fetched |
| test_workspace_no_cards_when_baseline | BASELINE → cards not fetched |
| test_workspace_no_cards_when_blocked | BLOCKED → cards not fetched |
| test_workspace_shows_status_banner | StatusBanner rendered for non-SUCCESS |
| test_workspace_shows_canonical_status | source_type/canonicalization_status/m2_ready visible |
| test_workspace_shows_degradation_reason | degradation_reason visible |
| test_workspace_shows_formula_origin | formula_origin visible on formula cards |
| test_workspace_shows_formula_ocr_status | formula_ocr_status visible when present |
| test_workspace_hides_unknown_formula_derivation | unknown formula origin hides derivation |

### M3.4 StatusBanner 测试

| 测试 | 断言 |
|------|------|
| test_banner_baseline_only | amber warning displayed |
| test_banner_blocked_understanding | red error + blocking_reason |
| test_banner_degraded_structural | indigo warning + missing components |
| test_banner_failed | red error + re-upload prompt |
| test_banner_shows_canonical_status | canonicalization_status visible |
| test_banner_shows_m2_ready | m2_ready visible |
| test_banner_shows_formula_degradation | formula degradation reason visible |

### M3.5 Debug/Artifacts 测试

| 测试 | 断言 |
|------|------|
| test_debug_flag_gates_artifacts | SENSEI_DEBUG controls /artifacts access |
| test_normal_user_cannot_access_artifacts | 403 without debug flag |

### 全局规则

- 前端测试用 Vitest + Vue Test Utils + jsdom
- 组件级测试可使用 mock fetch（快速回归）
- 页面级验收必须真实后端联调
- 组件测试不代替页面级验收
- M3 验收必须显示 `canonical_paper.md` 状态、formula_origin、formula_ocr_status、evidence_status

## 16. 验收标准

- 普通用户不能绕过 understanding_status 获取 cards
- BASELINE_ONLY / BLOCKED 不展示 cards
- DEGRADED 显示降级提示
- /artifacts 默认 403
- 前端不直接调用 /artifacts
- StatusBanner 有测试
- canonicalization_status / m2_ready / degradation_reason 可见
- formula_origin / formula_ocr_status 可见
- evidence_status 可见
- 每个 M3.x 子模块都有测试覆盖
- 真实验收必须有至少一个真实后端 API smoke：上传真实小 PDF，后端返回 job / status / cards，前端能展示状态
- mock fetch 只能用于组件单测，不代表页面验收通过

## 17. 当前实现状态

### 已实现

- `/api/v1/documents/parse` endpoint
- `/api/v1/jobs/{job_id}/understanding_status` endpoint
- `/api/v1/jobs/{job_id}/cards` endpoint（status gating）
- `/api/v1/jobs/{job_id}/artifacts` endpoint（debug-only）
- `/api/v1/jobs` list endpoint
- `/api/v1/jobs/{job_id}` detail endpoint
- `/health` endpoint
- StatusBanner 组件（4 种状态）
- UploadView 对齐 /api/v1/documents/parse
- LearningWorkspaceView 对齐 /understanding_status + /cards
- StatusBanner 测试（7 tests）
- API status gating 测试（15 tests）
- canonical source panel、formula provenance badges、evidence_status display 为 DOC_DESIGNED / NOT_IMPLEMENTED

### 未实现

- M3.2 UploadView 页面级测试
- M3.3 LearningWorkspaceView 页面级测试
- M4 互动式学习 tabs（显示"未开放"，归 M4）
- /quality_report debug endpoint（当前未实现，quality_report.json 只能通过 /artifacts 查看）
- debug/admin 鉴权机制
- evidence_ref 跳转
- canonical source panel
- formula provenance badges
- evidence_status panel

## 18. External Reference Implementation Notes

- **Reference source**: ARIS `skills/research-lit/SKILL.md` (output table), ARIS verification/relevance/source fields
- **Reference use**: STRATEGY_BORROW
- **Borrowed behavior**: Users should see why a paper was selected, why it is trusted, why it is degraded or blocked. Display source contribution, verification_status, relevance_reason, limitations, open_questions.
- **ResearchSensei-owned target**: `/cards` response, `/understanding_status` response, `LearningWorkspaceView`, `StatusBanner`
- **Schema / artifact impact**: Card response should include `verification_status` / `relevance_reason` / `source_confidence` / `evidence_ref` summary. DEGRADED / BLOCKED should show reasons.
- **Boundary**: ARIS has no reusable frontend UI. M3 remains Vue + FastAPI. Only display field structure is borrowed. Not just title and abstract; must show trust/selection/degradation reasons.
- **Validation implication**: BLOCKED does not return card content. Raw artifacts require debug/admin permission.

## 19. 当前未解决问题

- debug/admin 具体鉴权机制
- `/artifacts` 是否需要脱敏版本
- evidence_ref 跳转的实现优先级
- `debug=true` 的认证方式
- LearningWorkspaceView status gating 页面级测试
- UploadView upload flow 页面级测试
