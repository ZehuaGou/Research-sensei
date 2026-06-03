from __future__ import annotations

from html import escape

from backend.schemas import DrillCard, FormulaCard, PatternCard, TeachingCard


class RenderService:
    def render_learning_workspace(
        self,
        *,
        title: str,
        paper_card: TeachingCard,
        formula_cards: list[FormulaCard],
        pattern_card: PatternCard,
        drill_card: DrillCard,
        job_id: str,
        warnings: list[str] | None = None,
    ) -> str:
        formula_sections = "\n".join(self._render_formula(card) for card in formula_cards)
        recall = "".join(f"<li>{escape(question)}</li>" for question in drill_card.recall_questions)
        advisor = "".join(f"<li>{escape(question)}</li>" for question in drill_card.advisor_questions)
        unique_warnings = list(dict.fromkeys(warnings or []))
        warning_html = ""
        if unique_warnings:
            warning_items = "".join(f"<li>{escape(warning)}</li>" for warning in unique_warnings)
            warning_html = (
                "<section class='card warning-card'>"
                "<span class='tag'>需要人工核验</span>"
                "<h2>证据降级提示</h2>"
                "<p>当前页面可能不是基于论文全文生成。需要上传全文后再核验公式、实验和关键 claim。</p>"
                f"<ul>{warning_items}</ul>"
                "</section>"
            )
        return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>{escape(title)} - ResearchSensei</title>
  <style>
    body {{ margin:0; font-family: system-ui, sans-serif; color:#18202a; background:#f6f7f9; }}
    .app-shell {{ display:grid; grid-template-columns:260px minmax(0, 1fr) 380px; min-height:100vh; }}
    .workspace {{ display:contents; }}
    aside, main {{ padding:20px; }}
    aside {{ background:#fff; border-right:1px solid #dde2ea; }}
    .learning-sidebar {{ position:sticky; top:0; height:100vh; overflow:auto; }}
    .learning-main {{ max-width:900px; width:100%; margin:0 auto; }}
    .ask-panel {{ position:sticky; top:0; height:100vh; overflow:auto; }}
    .ask {{ border-left:1px solid #dde2ea; border-right:0; }}
    .card {{ background:white; border:1px solid #dde2ea; border-radius:8px; padding:18px; margin-bottom:16px; }}
    .warning-card {{ border-left:4px solid #b54708; background:#fff8ed; }}
    .tag {{ display:inline-block; padding:2px 8px; border-radius:999px; background:#eaf3ff; color:#194a7a; font-size:13px; }}
    textarea {{ width:100%; min-height:120px; }}
    button {{ padding:8px 12px; border-radius:6px; border:1px solid #8391a6; background:#fff; cursor:pointer; }}
    @media (max-width:980px) {{ .app-shell {{ display:block; }} .learning-sidebar, .ask-panel {{ position:static; height:auto; }} }}
  </style>
</head>
<body>
<div class="app-shell workspace">
  <aside class="learning-sidebar">
    <h2>左侧目录</h2>
    <nav>
      <p><a href="#summary">30秒看懂</a></p>
      <p><a href="#five">5分钟讲懂</a></p>
      <p><a href="#deep">深挖推导</a></p>
      <p><a href="#formula">公式卡</a></p>
      <p><a href="#pattern">科研模式</a></p>
      <p><a href="#drill">导师追问</a></p>
    </nav>
  </aside>
  <main class="learning-main">
    {warning_html}
    <section class="card" id="summary">
      <span class="tag">必须掌握</span> <span class="tag">证据状态：{escape(paper_card.evidence_status.value)}</span>
      <h1>{escape(title)}</h1>
      <h2>30秒看懂</h2>
      <p>{escape(paper_card.thirty_second)}</p>
    </section>
    <section class="card" id="five">
      <h2>5分钟讲懂</h2>
      <p>{escape(paper_card.five_minute)}</p>
    </section>
    <details class="card" id="deep" open>
      <summary>深挖推导</summary>
      <p>{escape(paper_card.deep_dive)}</p>
    </details>
    <section id="formula">{formula_sections}</section>
    <section class="card" id="pattern">
      <span class="tag">可以迁移</span>
      <h2>科研模式：{escape(pattern_card.pattern_id)}</h2>
      <p>{escape(pattern_card.definition)}</p>
      <p>{escape(pattern_card.transfer_template)}</p>
    </section>
    <section class="card" id="drill">
      <span class="tag">导师可能追问</span>
      <h2>复述题</h2><ul>{recall}</ul>
      <h2>隔天复习题</h2><ul>{recall}</ul>
      <h2>导师追问</h2><ul>{advisor}</ul>
      <h2>我是否真的懂</h2><ol><li>能否不用原文复述问题、机制、证据和局限？</li><li>能否解释关键公式去掉某项会怎样？</li></ol>
    </section>
  </main>
  <aside class="ask ask-panel">
    <h2>右侧追问区</h2>
    <p class="muted">追问入口：对当前段落、公式或选中文本继续追问。</p>
    <form method="post" action="/interactive/ask" hx-post="/api/interactive/ask" hx-target="#ask-answer" hx-swap="innerHTML">
      <input type="hidden" name="job_id" value="{escape(job_id)}">
      <input type="hidden" name="card_id" value="paper_card">
      <input type="hidden" name="card_type" value="paper_card">
      <p><button type="button">一步步推导</button> <button type="button">导师追问模式</button></p>
      <textarea name="question" placeholder="针对当前卡片继续追问"></textarea>
      <input name="selected_text" placeholder="可粘贴你选中的句子或公式">
      <p><button type="submit">发送追问</button></p>
    </form>
    <div id="ask-answer"></div>
  </aside>
</div>
</body>
</html>"""

    def _render_formula(self, card: FormulaCard) -> str:
        symbols = "".join(
            f"<li><strong>{escape(symbol.symbol)}</strong>：{escape(symbol.meaning)}；{escape(symbol.role)}</li>"
            for symbol in card.symbols
        )
        return f"""<section class="card">
  <span class="tag">公式核心</span> <span class="tag">{escape(card.evidence_status.value)}</span>
  <h2>公式讲解</h2>
  <pre>{escape(card.formula_latex)}</pre>
  <p>{escape(card.problem)}</p>
  <ul>{symbols}</ul>
  <p><strong>小数字例子：</strong>{escape(card.numeric_example)}</p>
  <p><strong>去掉某项会怎样：</strong>{escape(card.remove_effect)}</p>
</section>"""

    def render_direction_page(self, query: str, pool, reading_plan, search_id: str | None = None) -> str:
        a_rows = "\n".join(
            f"<tr><td><strong>{escape(item.title)}</strong><div class='muted'>{escape(item.venue)}</div></td><td>{item.year or ''}</td><td><span class='tag tag-transfer'>{escape(item.role.value)}</span></td><td>{item.quality_score}</td><td><span class='tag tag-required'>{escape(item.reading_priority.value)}</span></td></tr>"
            for item in pool.items[:10]
        )
        ignored = "".join(
            f"<li>{escape(item.title)}：{escape(item.filter_reason)}</li>"
            for item in pool.d_ignore_items[:5]
        )
        generate = ""
        if search_id:
            generate = (
                f"<form method=\"post\" action=\"/searches/{escape(search_id)}/generate\" "
                f"hx-post=\"/api/searches/{escape(search_id)}/generate\" hx-target='#generation-result' hx-swap='innerHTML'>"
                f"<button>生成 A_READ 学习页（{pool.summary.get('A_READ', 0)} 篇）</button></form>"
            )
        return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>方向学习 - ResearchSensei</title>
  <script src="https://unpkg.com/htmx.org@1.9.12" defer></script>
  <style>
    :root {{ color-scheme: light; }}
    body {{ margin:0; font-family:system-ui, sans-serif; color:#1d2733; background:#f5f7fa; }}
    a {{ color:#1b5f91; }}
    .app-shell {{ display:grid; grid-template-columns:260px minmax(0, 1fr) 380px; min-height:100vh; }}
    .learning-sidebar, .ask-panel {{ background:#fff; border-color:#dde3eb; border-style:solid; position:sticky; top:0; height:100vh; overflow:auto; }}
    .learning-sidebar {{ border-width:0 1px 0 0; padding:22px; }}
    .ask-panel {{ border-width:0 0 0 1px; padding:22px; }}
    .learning-main {{ padding:24px; max-width:900px; width:100%; margin:0 auto; }}
    .card {{ background:#fff; border:1px solid #dde3eb; border-radius:8px; padding:18px; margin-bottom:16px; box-shadow:0 1px 2px rgba(16,24,40,.04); }}
    .focus-box {{ border-left:4px solid #2878bd; background:#f0f7ff; padding:12px 14px; border-radius:6px; }}
    .tag {{ display:inline-block; border-radius:999px; padding:3px 9px; font-size:13px; margin:2px 4px 2px 0; }}
    .tag-required {{ background:#e8f3ff; color:#124c7c; }}
    .tag-confusing {{ background:#fff4e5; color:#8a4b00; }}
    .tag-transfer {{ background:#eaf8ef; color:#17653a; }}
    .tag-skip {{ background:#f1f3f5; color:#475467; }}
    .tag-evidence {{ background:#fceeee; color:#a12828; }}
    table {{ width:100%; border-collapse:collapse; font-size:14px; }}
    th, td {{ border-bottom:1px solid #e5e9f0; text-align:left; padding:10px 8px; vertical-align:top; }}
    textarea, input {{ width:100%; box-sizing:border-box; padding:10px; border:1px solid #b8c2d0; border-radius:6px; margin:6px 0; }}
    button {{ padding:9px 13px; border:1px solid #7b8aa0; border-radius:6px; background:white; cursor:pointer; }}
    .muted {{ color:#667085; }}
    @media (max-width: 980px) {{ .app-shell {{ display:block; }} .learning-sidebar, .ask-panel {{ position:static; height:auto; }} }}
  </style>
</head>
<body>
<div class="app-shell">
  <aside class="learning-sidebar">
    <h2>学习目录</h2>
    <nav>
      <p><a href="/">首页</a></p>
      <p><a href="/directions/new">搜索方向</a></p>
      <p><a href="/papers/upload">上传论文</a></p>
      <p><a href="#thirty">30秒看懂</a></p>
      <p><a href="#five">5分钟讲懂</a></p>
      <p><a href="#deep">深挖推导</a></p>
      <p><a href="#pool">候选池摘要</a></p>
      <p><a href="#route">方向脉络图</a></p>
    </nav>
  </aside>
  <main class="learning-main">
    <section class="card" id="thirty">
      <span class="tag tag-required">必须掌握</span>
      <span class="tag tag-evidence">证据状态：metadata-level</span>
      <h1>推荐学习路线 - {escape(query)}</h1>
      <h2>30秒看懂</h2>
      <p class="focus-box">先读少量 A_READ 论文建立主线，再用 B_SKIM 补背景；D_IGNORE 不进入学习时间预算。</p>
    </section>
    <section class="card" id="five">
      <span class="tag tag-transfer">可以迁移</span>
      <h2>5分钟讲懂</h2>
      <p>这个方向的学习重点不是堆论文，而是看清问题假设、方法演化、证据强弱和可迁移科研模式。</p>
    </section>
    <details class="card" id="deep" open>
      <summary>深挖推导</summary>
      <p>深挖阶段只对 A_READ 生成学习页；若只有摘要，会标注需要上传全文后核验公式和实验 claim。</p>
    </details>
    <section class="card" id="pool">
      <h2>候选池摘要</h2>
      <p>共检索 {pool.retrieved_count} 篇；去重后 {pool.deduplicated_count} 篇；强相关 {pool.strong_related_count} 篇；A_READ {pool.summary.get('A_READ', 0)} 篇；B_SKIM {pool.summary.get('B_SKIM', 0)} 篇；D_IGNORE {pool.summary.get('D_IGNORE', 0)} 篇。</p>
      <p><span class="tag tag-required">必须掌握</span><span class="tag tag-confusing">容易混淆</span><span class="tag tag-transfer">可以迁移</span><span class="tag tag-skip">暂时可跳过</span></p>
    </section>
    <section class="card">
      <h2>Top A_READ / 候选池</h2>
      <table><thead><tr><th>论文</th><th>年份</th><th>角色</th><th>质量分</th><th>优先级</th></tr></thead><tbody>{a_rows}</tbody></table>
    </section>
    <section class="card">
      <h2>典型过滤</h2><ul>{ignored}</ul>
    </section>
    <section class="card" id="route">
      <h2>方向脉络图</h2>
      <p>基础假设 -> 传统统计/距离/密度方法 -> 预测/重构误差 -> 图结构/变量依赖 -> Transformer/attention -> 评估批判 -> 新趋势。</p>
    </section>
    <section class="card">
      <h2>复述题</h2>
      <ol><li>这个方向真正要解决的问题是什么？</li><li>A_READ 论文各自代表哪一种方法演化节点？</li></ol>
      <h2>隔天复习题</h2>
      <ol><li>不看页面，复述 A_READ 的阅读顺序。</li><li>指出一个暂时不读的论文及原因。</li></ol>
      <h2>我是否真的懂</h2>
      <ol><li>能否解释为什么 D_IGNORE 不值得读？</li><li>能否说出一个导师可能追问的问题？</li></ol>
    </section>
    <section class="card">
      {generate}
      <div id="generation-result"></div>
    </section>
  </main>
  <aside class="ask-panel">
    <h2>交互追问面板</h2>
    <p class="muted">追问入口：针对当前方向、候选池或选中文字提问。</p>
    <form hx-post="/api/interactive/ask" hx-target="#ask-answer" hx-swap="innerHTML">
      <input type="hidden" name="job_id" value="{escape(search_id or 'direction')}">
      <input type="hidden" name="card_id" value="direction_map">
      <input type="hidden" name="card_type" value="direction_map">
      <button type="button">再讲简单点</button>
      <button type="button">导师追问模式</button>
      <button type="button">出题考我</button>
      <textarea name="question" placeholder="这里直接追问"></textarea>
      <input name="selected_text" placeholder="可粘贴选中的论文标题或句子">
      <button type="submit">发送</button>
    </form>
    <div id="ask-answer"></div>
  </aside>
</div>
</body>
</html>"""

# HTML rendering
from html import escape

from backend.schemas import FormulaCard


class LearningWorkspaceRenderer:
    """Renders a three-pane learning workspace shell."""

    def render_formula_card(self, card: FormulaCard) -> str:
        symbol_rows = "".join(
            f"<li><strong>{escape(symbol.symbol)}</strong>：{escape(symbol.meaning)}；{escape(symbol.role)}</li>"
            for symbol in card.symbols
        )
        return f"""<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>ResearchSensei</title></head>
<body>
<main class="workspace" style="display:grid;grid-template-columns:220px minmax(0,1fr) 300px;gap:16px;font-size:18px;line-height:1.7;">
  <aside aria-label="左侧目录"><h2>左侧目录</h2><a href="#formula">公式卡</a></aside>
  <section id="formula"><h1>公式讲解卡</h1>
    <p><strong>问题：</strong>{escape(card.problem)}</p>
    <pre>{escape(card.formula_latex)}</pre>
    <h2>符号</h2><ul>{symbol_rows}</ul>
    <h2>小数字例子</h2><p>{escape(card.numeric_example)}</p>
    <h2>去掉会怎样</h2><p>{escape(card.remove_effect)}</p>
    <button data-ask="simple">我没看懂</button>
    <button data-ask="derive">一步一步推导</button>
  </section>
  <aside aria-label="右侧追问区"><h2>右侧追问区</h2><textarea placeholder="针对当前卡片追问"></textarea></aside>
</main>
</body>
</html>"""
