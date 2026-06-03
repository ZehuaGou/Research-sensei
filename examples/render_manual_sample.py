from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from research_sensei.core.direction import DirectionCurator
from research_sensei.core.patterns import default_pattern_cards
from research_sensei.core.quality import PaperQualityEvaluator
from research_sensei.renderer import HtmlCardRenderer
from research_sensei.schemas import (
    ConceptCardData,
    DrillCardData,
    DrillItem,
    EvidenceLink,
    FormulaCardData,
    FormulaTerm,
    LearningMode,
    PaperCandidate,
    PaperCardData,
    PhdThinkingScaffold,
    ResearchFramework,
    to_plain_data,
)


def dump_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(to_plain_data(data), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def build_candidates() -> list[PaperCandidate]:
    return [
        PaperCandidate(
            title="Attention Is All You Need",
            authors=["Ashish Vaswani", "Noam Shazeer", "Niki Parmar"],
            year=2017,
            venue="NeurIPS",
            source_tool="manual-seed",
            source_platform="manual",
            url="https://arxiv.org/abs/1706.03762",
            pdf_url="https://arxiv.org/pdf/1706.03762",
            abstract="Introduces the Transformer architecture based entirely on attention mechanisms.",
            citation_count=100000,
            open_access=True,
            quality_signals=["ablation:strong", "baseline:strong"],
        ),
        PaperCandidate(
            title="BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
            authors=["Jacob Devlin", "Ming-Wei Chang", "Kenton Lee", "Kristina Toutanova"],
            year=2019,
            venue="NAACL",
            source_tool="manual-seed",
            source_platform="manual",
            url="https://arxiv.org/abs/1810.04805",
            pdf_url="https://arxiv.org/pdf/1810.04805",
            abstract="Introduces masked language model pre-training for bidirectional representations.",
            citation_count=80000,
            open_access=True,
            quality_signals=["ablation:strong", "baseline:strong"],
        ),
        PaperCandidate(
            title="Language Models are Few-Shot Learners",
            authors=["Tom B. Brown"],
            year=2020,
            venue="NeurIPS",
            source_tool="manual-seed",
            source_platform="manual",
            url="https://arxiv.org/abs/2005.14165",
            pdf_url="https://arxiv.org/pdf/2005.14165",
            abstract="Studies scaling language models and in-context few-shot behavior.",
            citation_count=30000,
            open_access=True,
            quality_signals=["baseline:strong"],
        ),
        PaperCandidate(
            title="Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks",
            authors=["Patrick Lewis"],
            year=2020,
            venue="NeurIPS",
            source_tool="manual-seed",
            source_platform="manual",
            url="https://arxiv.org/abs/2005.11401",
            pdf_url="https://arxiv.org/pdf/2005.11401",
            abstract="Combines parametric generation with non-parametric retrieval memory.",
            citation_count=12000,
            open_access=True,
            quality_signals=["ablation:strong", "baseline:strong"],
        ),
    ]


def build_paper_card(candidate: PaperCandidate, evaluator: PaperQualityEvaluator) -> PaperCardData:
    return PaperCardData(
        paper=candidate,
        quality=evaluator.assess(candidate),
        framework=ResearchFramework(
            problem="序列建模依赖循环或卷积结构，长距离依赖学习慢且难并行。",
            old_methods="RNN/CNN encoder-decoder 通过顺序递推或局部卷积处理 token。",
            bottleneck="计算路径长、并行度低，远距离 token 交互成本高。",
            assumption="如果 token 间关系可以由 attention 直接建模，就不必依赖递归结构。",
            representation="把 token 表示为 query/key/value，并加入 positional encoding 表示顺序。",
            mechanism="Self-attention 让每个 token 按相关性聚合全局上下文。",
            objective="用最大似然训练翻译模型，使目标序列概率最大。",
            evidence="机器翻译实验、速度对比和 ablation 支持 attention-only 结构有效。",
            limitation="需要较大数据和算力；长上下文 attention 成本随长度平方增长。",
            transfer="可迁移到文本、视觉、语音、图结构、检索增强和多模态建模。",
        ),
        phd=PhdThinkingScaffold(
            claims=["仅用 attention 也能获得强序列建模能力。"],
            evidence=[
                EvidenceLink(
                    claim="attention-only 有效",
                    source="实验章节与 ablation 表",
                    quote="需要人工核验具体表格数值。",
                    confidence="medium",
                )
            ],
            assumptions=["位置编码足以补回序列顺序信息。", "训练数据规模足够支撑模型学习关系。"],
            weak_points=["长序列二次复杂度会成为瓶颈。", "翻译任务上的证据不能自动推出所有任务都有效。"],
            research_questions=["如何降低 attention 在长序列上的复杂度？", "attention 是否真的学到了可解释结构？"],
            mini_projects=["复现一个小型 self-attention 分类器，并去掉 positional encoding 做 ablation。"],
        ),
        patterns=["Representation", "Structure", "System Pipeline"],
        tags=["必须掌握", "容易混淆", "可以迁移"],
        thirty_second="Transformer 把序列建模从递归更新改成 token 间直接交互。",
        five_minute="核心不是一句“用了 attention”，而是把表示、交互路径和并行训练方式一起换了。",
        deep_dive="需要人工核验: 具体 BLEU、训练成本和 ablation 表格应回到原文。",
        recall_questions=["不用公式，讲清 self-attention 解决了 RNN 的哪个瓶颈。"],
        review_questions=["明天比较 Transformer 与 RNN 的信息路径长度。"],
        understanding_checks=["能说出去掉 positional encoding 会损失什么吗？"],
    )


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    json_dir = root / "cards" / "json"
    html_dir = root / "cards" / "html"

    evaluator = PaperQualityEvaluator()
    renderer = HtmlCardRenderer()
    candidates = build_candidates()
    direction = DirectionCurator(evaluator).curate(
        "Transformer 到检索增强语言模型",
        candidates,
        mode=LearningMode.REPRODUCIBLE,
    )
    anchor = direction.core_papers[0].paper
    paper_card = build_paper_card(anchor, evaluator)
    formula_card = FormulaCardData(
        title="Scaled Dot-Product Attention",
        formula_latex=r"\mathrm{Attention}(Q,K,V)=\mathrm{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V",
        problem="让每个 token 根据相关性从其他 token 聚合信息。",
        inputs=["Q: 当前 token 想查询什么", "K: 每个 token 提供什么匹配线索", "V: 每个 token 提供什么内容"],
        outputs=["按相关性加权后的上下文表示"],
        symbols=[
            FormulaTerm(symbol="QK^T", meaning="query 与 key 的匹配分数", role="鼓励相关 token 互相连接", remove_effect="无法判断该看谁"),
            FormulaTerm(symbol=r"\sqrt{d_k}", meaning="维度缩放", role="避免点积过大导致 softmax 过尖", weight_change_effect="缩放变小会让分布更尖"),
            FormulaTerm(symbol="V", meaning="被聚合的内容", role="把注意力权重转成实际上下文表示"),
        ],
        mechanism_link="这个公式把“找相关 token”和“聚合信息”合成一个可微模块。",
        numeric_example="若两个 key 得分分别为 2 和 0，softmax 后第一个 token 权重更高。",
        plain_summary="Attention 是一个按相关性加权取信息的机制。",
        manual_check=["真实论文中的矩阵维度和多头细节需要回原文核验。"],
        recall_questions=["解释为什么要除以 sqrt(d_k)。"],
        review_questions=["明天用两个 token 的数字例子复述 softmax 加权。"],
        understanding_checks=["能说明去掉 V 后公式还剩什么吗？"],
    )
    concept_card = ConceptCardData(
        concept="Self-Attention",
        definition="同一序列内部的 token 互相查询、匹配并聚合信息。",
        prerequisites=["向量点积", "softmax", "序列表示"],
        examples=["句子中 pronoun 关注它指代的名词。"],
        misconceptions=["attention 权重高不一定等于人类解释。"],
        paper_usage="Transformer 用 self-attention 替代循环结构，缩短信号传递路径。",
        transfer_cases=["图节点消息传递", "图像 patch 交互", "检索增强上下文选择"],
        recall_questions=["用人话解释 self-attention 和 cross-attention 的差别。"],
        review_questions=["明天举一个非 NLP 的迁移例子。"],
        understanding_checks=["能说出 attention 的局限吗？"],
    )
    pattern_card = default_pattern_cards()[0]
    drill_card = DrillCardData(
        target=anchor.title,
        recall_questions=[DrillItem(question="这篇论文解决什么瓶颈？", expected_move="先说旧方法，再说瓶颈。")],
        review_questions=[DrillItem(question="明天复述公式每一项。", expected_move="符号 -> 作用 -> 去掉影响。")],
        advisor_questions=[DrillItem(question="为什么这篇值得读？", expected_move="回答方向转折，而不是只说引用高。")],
        reviewer_questions=[DrillItem(question="实验是否足以支持 claim？", expected_move="回到 evidence 和 weak point。")],
        rubric=["能复述机制", "能指出假设", "能提出 follow-up"],
        weak_points=["容易把 attention 权重直接当解释。"],
        next_review_at="由 py-fsrs 在后续接入后计算",
    )

    cards = {
        "paper_card": paper_card,
        "formula_card": formula_card,
        "concept_card": concept_card,
        "direction_map": direction,
        "pattern_card": pattern_card,
        "drill_card": drill_card,
    }
    for name, card in cards.items():
        dump_json(json_dir / f"{name}.json", card)
        renderer.render(f"{name}.html", card, html_dir / f"{name}.html")


if __name__ == "__main__":
    main()
