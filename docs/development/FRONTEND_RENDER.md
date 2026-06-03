# Frontend Render 模块

---

## 1. 模块目标

定义前端/API 展示规则，确保用户只看到符合 understanding_status 的内容。

## 2. 非目标

- 不实现 audit 内部逻辑
- 不实现 evidence 内部实现
- 不改 backend 核心逻辑

## 3. 核心原则

- 前端/API 必须先读取 understanding_status。
- 普通用户不能绕过 understanding_status 直接展示 card。
- card 是否展示由 status + component_status + allowed_downstream 决定。
- BLOCKED_UNDERSTANDING 时绝对不能展示解释性 card 内容。
- BASELINE_ONLY 普通用户不能当作最终理解展示。

## 4. status 展示规则

### SUCCESS

- 展示 paper_card / formula_cards / teaching_cards 中成功组件。
- 可称为"导师级解释"，前提是 paper_card、formula_cards、teaching_cards 都成功。
- 若 formula_cards 为 SKIPPED（论文无公式），不展示公式区，不算失败。

### DEGRADED_STRUCTURAL

- 只展示成功组件。
- 失败组件隐藏，并显示明显降级提示。
- teaching_cards FAILED 时，只能称为"论文理解"或"结构化理解"，不能称为"导师级解释"。
- formula_cards optional failed 时，隐藏公式区并显示"公式讲解暂不可用"。
- advisor_questions 是否允许由 `understanding_status.allowed_downstream.advisor_questions` 决定；teaching_cards FAILED 时当前倾向为 False。

### BASELINE_ONLY

- 普通用户不展示 cards。
- 只展示"基线模式：当前结果仅供诊断，不是最终论文理解"。
- debug/admin 模式可查看 baseline cards。

### BLOCKED_UNDERSTANDING

- 不展示 paper_card / formula_cards / teaching_cards。
- 只展示 blocking_reason、warnings、必要 diagnostic metadata。
- 不展示解释性内容。

### FAILED

- 展示系统错误。
- 不展示 cards。

## 5. component_status 展示规则

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

## 6. /cards API 行为

`GET /api/v1/jobs/{job_id}/cards`

| status | 行为 |
|--------|------|
| SUCCESS | 返回成功 cards |
| DEGRADED_STRUCTURAL | 只返回成功组件 cards，返回 degraded_components / warnings |
| BASELINE_ONLY | 普通用户返回 403 或受控提示；debug/admin 可返回 baseline cards |
| BLOCKED_UNDERSTANDING | 返回 403 + blocking_reason + warnings，不返回 card 内容 |
| FAILED | 返回 500/failed status，不返回 card 内容 |

## 7. /artifacts API 权限

- `/artifacts` 定位为 debug/admin raw API。
- 普通前端不应直接用 `/artifacts` 展示 cards。
- `/cards` 是用户端展示 card 的唯一受控 API。
- `/artifacts` 是否脱敏仍未决。
- production 必须有鉴权；本地开发可通过 `SENSEI_DEBUG=1` 暂时允许。

## 8. /quality_report API 权限

- `/quality_report` 定位为 debug/admin API。
- 普通用户不直接访问完整 QualityReport。
- 未来可考虑脱敏版，但当前未决。

## 9. evidence_ref 跳转

- evidence_ref 跳转依赖 `parsed_document.json` + `passage_index.json` + `claim_evidence.json`。
- 前端可通过 evidence_ref / passage_id 定位 passage_text 和 block_ids。
- 初版可以只支持 passage 级定位，精确 bbox/page 跳转留给外部 parser 接入后。
- `passage_index.json` 是 evidence 跳转的关键 artifact。

## 10. debug=true 规则

- `debug=true` 不应默认给普通用户使用。
- debug/admin 鉴权机制未决。
- 原则：`debug=true` admin/dev only。

## 11. 当前未解决问题

- debug/admin 具体鉴权机制。
- `/artifacts` 是否需要脱敏版本。
- DEGRADED_STRUCTURAL 的前端提示文案。
- evidence_ref 跳转的实现优先级（v1 还是 v2）。
- `debug=true` 的认证方式。
