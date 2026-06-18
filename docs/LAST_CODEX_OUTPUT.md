# Last Codex Output

## 1. Commit

- commit hash: `8e0bb65`
- branch: main
- git status --short: clean

## 2. Task Summary

**目标**: 修复 smoke/matrix 脚本运行时没有自动加载 .env 的问题，确保 UNPAYWALL_EMAIL、RESEARCHSENSEI_CONTACT_EMAIL、MIMO_API_KEY、SEMANTIC_SCHOLAR_API_KEY、S2_API_KEY 能从 .env 被加载到 Python 进程，不打印完整 key/email。

**实际完成**:
- 调研发现 `ConfigService._load_env()` 已使用 `dotenv_values` 从 .env 加载到 `os.environ`，但存在三个问题：
  1. 仅在 `ConfigService.load()` 中被动调用，缺乏统一入口
  2. 被 `try/except` 包裹，异常被静默吞掉
  3. 不处理 UTF-8 BOM 前缀（.env 文件以 `\xef\xbb\xbf` 开头）
- 新增 `src/researchsensei/core/env_loader.py` 提供统一 `load_runtime_env()` 函数
- 更新三个脚本和 `ConfigService._load_env()` 使用统一入口
- 修复 BOM 问题（`key.lstrip("\ufeff")`）
- 添加 S2_API_KEY ↔ SEMANTIC_SCHOLAR_API_KEY 别名自动补齐
- 所有 key/email 仅在 masked 日志中显示（e.g. `gou***@foxmail.com`, `tp-***`）
- 18 个测试覆盖：mask 行为、env 加载、BOM 处理、S2 alias、ConfigService 集成、禁止明文输出

## 3. Code Changes

| 文件 | 改动 |
|------|------|
| `src/researchsensei/core/env_loader.py` | **新增**。统一 `.env` 加载入口 `load_runtime_env()`。支持 mask 输出、S2 别名自动补齐、BOM 处理、不覆盖已有 `os.environ`。 |
| `src/researchsensei/core/config.py` | **修改**。`_load_env()` 改为委托 `load_runtime_env()`，删除旧的 `dotenv_values` 直接调用逻辑。添加 `from researchsensei.core.env_loader import load_runtime_env`。 |
| `scripts/run_main_chain_smoke.py` | **修改**。添加模块级 `load_runtime_env(suppress_errors=True)` 调用，在 `main()` 中输出 masked 加载信息。 |
| `scripts/run_main_chain_matrix.py` | **修改**。`ConfigService` 导入替换为 `load_runtime_env`，在 `main()` 中输出 masked 加载信息。 |
| `scripts/run_literature_acquisition_smoke.py` | **修改**。模块级 `try/except ConfigService().load()` 替换为 `load_runtime_env(suppress_errors=True)`。在 `main()` 中输出 masked 加载信息。 |
| `tests/test_env_loader.py` | **新增**。18 个测试：mask_value 单元测试（API key / email / empty / short），load_runtime_env 加载、mask/unmask、不覆盖已有 key、文件不存在、空文件、BOM 编码、S2 别名（双向）、ConfigService 集成、禁止明文输出。 |

## 4. Environment Loading Verification

通过 `_test_env_load.py` 验证（于 2026-06-18 14:47 UTC）：

| Key | dotenv 可读 | os.environ（before load） | os.environ（after load） |
|-----|:----------:|:------------------------:|:-----------------------:|
| UNPAYWALL_EMAIL | gou***@foxmail.com | NOT SET | SET (len=20) |
| RESEARCHSENSEI_CONTACT_EMAIL | gou***@foxmail.com | NOT SET | SET (len=20) |
| MIMO_API_KEY | tp-*** | NOT SET | SET (len=51) |
| SEMANTIC_SCHOLAR_API_KEY | MISSING | - | - |
| S2_API_KEY | MISSING | - | - |

S2_API_KEY 和 SEMANTIC_SCHOLAR_API_KEY 缺失是 API 速率限制的根本原因，env_loader 已提供别名自动补齐机制，一旦任一 key 被添加即可生效。

## 5. Tests

- backend: 565 passed, 15 skipped（含 18 个新的 env_loader 测试）
- frontend: 42 passed
- build: 成功

## 6. Key Design Decisions

- **不覆盖已有 `os.environ`**：`if key in os.environ: continue`，显式 `$env:KEY=val` 优先于 .env
- **S2 别名自动补齐**：若 .env 中设置了 `S2_API_KEY` 但未设置 `SEMANTIC_SCHOLAR_API_KEY`，自动补齐后者（反之亦然）
- **Masked 日志**：`logger.info("Loaded from .env: %s", masked_items)` 只在 DEBUG 级别可见，stdout 输出 `[env] loaded from .env: {<masked>}`
- **BOM 处理**：`.env` 文件以 UTF-8 BOM（`\xef\xbb\xbf`）开头，`dotenv_values` 不处理此情况，`load_runtime_env` 通过 `key.lstrip("\ufeff")` 修复

## 7. Current Strict Status

- **Broad REAL_E2E**: 否
- **Product-ready**: 否。S2_API_KEY 缺失导致持续 429。
- **M4 started**: 否
- **Current max shortfall**: (1) S2_API_KEY 缺失导致 Semantic Scholar 持续 429；(2) 矩阵运行时需 ~60+ 外部 API 调用。

## 8. Next Suggested Step

1. 添加 `SEMANTIC_SCHOLAR_API_KEY` 和 `S2_API_KEY` 到 `.env`
2. 运行完整 live matrix: `--provider mimo --refresh-cache`
3. 验证 cached matrix: `--provider mimo --use-cache`
