# M1 人工核验指南

## 如何查看

1. 用浏览器打开 `reports/m1_parser_review/index.html`
2. 页面顶部有结论区，底部有 3 篇论文的详细对比

## 检查顺序

### 第一步：看正文提取是否合格

对每篇论文：

1. 看 **PDF Page Screenshots**（page_1.png ~ page_3.png）——这是原始 PDF 长什么样
2. 看 **MarkItDown Output（前 200 行）**——这是 MarkItDown 解析出的正文
3. 对比：正文是否完整？段落是否连贯？是否丢失大段内容？

**判断标准：**
- 如果 MarkItDown 正文覆盖了 PDF 80% 以上的文字内容 → 正文合格
- 如果明显丢失了大段文字或乱码严重 → 正文不合格
- 如果基本可用但有少量问题 → 边界情况

### 第二步：看公式提取是否合格

1. 看 **Formula Page Screenshots**（formula_page_1.png ~ formula_page_3.png）——这是原始 PDF 中公式的截图
2. 看 **Formula Analysis（MarkItDown）** 表——这是 MarkItDown 检测到的公式
3. 看 **pix2tex OCR Test** 表——这是 pix2tex 对公式的 OCR 结果

**判断标准：**
- 如果 MarkItDown 能检测到公式并保留 LaTeX 结构 → 公式合格
- 如果 MarkItDown 检测到公式但只是纯文本 → 公式不合格，需要 OCR
- 如果 pix2tex OCR 输出像 LaTeX 但内容不准确 → 低置信，可作为 on-demand 备选
- 如果 pix2tex 输出完全乱码 → 不可用

### 第三步：看 canonical_paper.md 是否可读

1. 看 **canonical_paper.md（前 200 行）**
2. 检查 front matter 是否完整（paper_id, title, authors, source_type, m2_ready）
3. 检查正文是否可读

**判断标准：**
- 如果 front matter 完整、正文可读 → 合格
- 如果 front matter 缺失字段或正文乱码 → 不合格

## 决策路径

### 如果你觉得正文可以、公式不行

→ M1 可以收口，但需要：
- MarkItDown 作为默认 PDF parser（正文提取）
- pix2tex 作为 on-demand formula OCR（低置信，按需触发）
- 公式质量标记为 degraded，M2 需要处理公式降级

### 如果你觉得公式也可以

→ M1 可以收口，MarkItDown + pix2tex 组合方案

### 如果你觉得正文都不行

→ M1 不能收口，需要：
- 换 parser（Marker 虽然慢但结构更好）
- 或者等 MarkItDown 改进
- 或者接受 PyMuPDF 作为 fallback（内容更少但不会乱码）

### 如果你觉得需要更多样本

→ 在 index.html 中再加几篇论文，重新生成

## 当前结论（待你确认）

- MarkItDown 正文：可用
- MarkItDown 公式：不可用（不保留 LaTeX）
- canonical_paper.md：可读
- pix2tex：低置信 on-demand（结构 OK 但内容不准）
- M1 收口：NEED_USER_REVIEW（等你确认）
