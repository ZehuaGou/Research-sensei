const TASK_STAGE_LABELS: Record<string, string> = {
  queued: '等待开始',
  starting: '正在启动',
  planning_query: '正在规划检索词',
  searching_sources: '正在检索论文来源',
  deduplicating: '正在去重候选',
  verifying_candidates: '正在验证论文信息',
  discovering_fulltext: '正在解析全文来源',
  ranking_candidates: '正在评估相关性',
  downloading_fulltext: '正在下载并验证全文',
  assembling_results: '正在整理结果',
  resolving_source: '正在解析论文来源',
  source_resolved: '全文来源已确认',
  validating_source: '正在验证原始文件',
  preparing_source: '正在准备论文文件',
  parsing_document: '正在解析论文结构',
  indexing_evidence: '正在建立证据索引',
  building_evidence_pack: '正在整理可引用证据',
  building_paper_card: '正在生成论文概览',
  paper_card_ready: '论文概览已生成',
  building_formula_cards: '正在生成公式卡片',
  formula_cards_ready: '公式卡片已生成',
  building_teaching_cards: '正在生成教学卡片',
  teaching_cards_ready: '教学卡片已生成',
  auditing_understanding: '正在核验卡片与证据',
  writing_artifacts: '正在保存深读结果',
  completed: '已完成',
  failed: '任务失败',
  cancelling: '正在取消',
  cancelled: '已取消',
  service_restarted: '服务重启，任务已中断',
}

export function formatTaskStage(stage: string) {
  const formulaMatch = stage.match(/^building_formula_cards:(\d+)\/(\d+)$/)
  if (formulaMatch) {
    const [, completed, total] = formulaMatch
    return total === '0'
      ? '论文中没有可推导公式'
      : `正在生成公式卡片（${completed}/${total} 批）`
  }
  return TASK_STAGE_LABELS[stage] || stage || '等待开始'
}
