import type { Page, Route } from '@playwright/test'

type FixtureKind = 'success' | 'degraded' | 'blocked' | 'no-llm'

const paperCard = {
  title: 'Fixture: Reliable Multivariate Time-Series Anomaly Detection',
  one_sentence_summary: 'A fixed local paper fixture used to verify the learner workspace without network access.',
  problem: {
    text: 'Detect anomalies in multivariate time series while preserving temporal and cross-channel context.',
    evidence_ref: 'fixture:paper:problem',
  },
  core_idea: {
    text: 'Encode temporal context and compare the reconstruction residual against a paper-defined score.',
    evidence_ref: 'fixture:paper:method',
  },
  method_overview: {
    text: 'The fixture exposes a deterministic reconstruction objective and bound evidence references.',
    evidence_ref: 'fixture:paper:method',
  },
  experiment_summary: {
    text: 'The fixture intentionally contains no live benchmark claim.',
    evidence_ref: 'fixture:paper:experiment',
  },
  evidence_status: 'verified',
}

const formulaCards = [
  {
    formula_id: 'fixture-loss',
    evidence_ref: 'fixture:formula:loss',
    formula_latex: 'L = \\sum_{t=1}^{T} (x_t - \\hat{x}_t)^2',
    display_title: 'Reconstruction objective',
    purpose: 'Measure reconstruction error across observed time steps.',
    intuition: 'Larger residuals contribute more strongly to the objective.',
    numeric_example: 'For residuals 1 and 2, the squared contribution is 1 + 4 = 5.',
    what_if_removed: 'The fixture model would lose its reconstruction training signal.',
    weight_change_effect: 'No extra weight is defined in this fixture.',
    formula_origin: 'source_latex',
    derivation_status: 'supported',
    coverage_status: 'COMPLETE',
    evidence_status: 'verified',
    symbols: [
      { symbol: 'x_t', meaning: 'observed value at time t' },
      { symbol: '\\hat{x}_t', meaning: 'reconstructed value at time t' },
    ],
  },
  {
    formula_id: 'fixture-score',
    evidence_ref: 'fixture:formula:score',
    formula_latex: 's_t = |x_t - \\hat{x}_t|',
    display_title: 'Anomaly score',
    purpose: 'Express the absolute reconstruction residual.',
    intuition: 'A larger residual means the observation is less consistent with its reconstruction.',
    numeric_example: 'If x is 5 and its reconstruction is 3, the score is 2.',
    what_if_removed: 'The fixture would not expose a point-wise score.',
    weight_change_effect: 'No tunable weight is defined.',
    formula_origin: 'source_latex',
    derivation_status: 'supported',
    coverage_status: 'COMPLETE',
    evidence_status: 'verified',
  },
  {
    formula_id: 'fixture-mean',
    evidence_ref: 'fixture:formula:mean',
    formula_latex: '\\bar{s} = \\frac{1}{T} \\sum_{t=1}^{T} s_t',
    display_title: 'Mean score',
    purpose: 'Aggregate fixture scores for display.',
    intuition: 'The mean summarizes the fixed score sequence.',
    numeric_example: 'Scores 1 and 3 have mean 2.',
    what_if_removed: 'Only point-wise fixture scores remain.',
    weight_change_effect: 'No tunable weight is defined.',
    formula_origin: 'source_latex',
    derivation_status: 'supported',
    coverage_status: 'COMPLETE',
    evidence_status: 'verified',
  },
]

const teachingCards = Array.from({ length: 8 }, (_, index) => ({
  card_id: `fixture-teaching-${index + 1}`,
  title: `Fixture teaching card ${index + 1}`,
  card_type: 'concept',
  human_explanation: `Offline explanation ${index + 1}; it does not make a live paper claim.`,
  evidence_refs: [`fixture:teaching:${index + 1}`],
}))

const statuses: Record<FixtureKind, object> = {
  success: {
    understanding_status: {
      status: 'SUCCESS',
      warnings: [],
      component_status: { paper_card: 'SUCCESS', formula_cards: 'SUCCESS', teaching_cards: 'SUCCESS' },
      allowed_downstream: { cards: true, m4: true },
    },
    paper_workspace_status: {
      source_type: 'local_path',
      verification_status: 'verified',
      can_enter_m2: true,
      m2_ready: true,
      formula_origin: 'source_latex',
      evidence_status: 'verified',
      quality_status: 'pass',
    },
  },
  degraded: {
    understanding_status: {
      status: 'DEGRADED_STRUCTURAL',
      blocking_reason: 'FORMULA_DERIVATION_BLOCKED',
      warnings: [{ code: 'FORMULA_DERIVATION_BLOCKED', message: 'The offline fixture has no supported formula derivation.' }],
      component_status: { paper_card: 'SUCCESS', formula_cards: 'FAILED', teaching_cards: 'SUCCESS' },
      allowed_downstream: { cards: true, m4: true },
    },
    paper_workspace_status: {
      source_type: 'local_path',
      verification_status: 'verified',
      degradation_reason: 'FORMULA_DERIVATION_BLOCKED',
      formula_origin: 'raw_formula_text',
      evidence_status: 'verified',
      quality_status: 'warning',
    },
  },
  blocked: {
    understanding_status: {
      status: 'BLOCKED_UNDERSTANDING',
      blocking_reason: 'MISSING_METHOD_EVIDENCE',
      warnings: [{ code: 'MISSING_METHOD_EVIDENCE', message: 'The fixed fixture is intentionally blocked.' }],
      component_status: { evidence_pack: 'FAILED' },
      allowed_downstream: { cards: false, m4: false },
    },
    paper_workspace_status: {
      source_type: 'local_path',
      verification_status: 'verified',
      evidence_status: 'failed',
      quality_status: 'failed',
    },
  },
  'no-llm': {
    understanding_status: {
      status: 'BASELINE_ONLY',
      blocking_reason: 'NO_LLM_CLIENT',
      warnings: [{ code: 'NO_LLM_CLIENT', message: 'No live model is configured for the offline fixture.' }],
      component_status: { llm: 'SKIPPED' },
      allowed_downstream: { cards: false, m4: false },
    },
    paper_workspace_status: {
      source_type: 'local_path',
      verification_status: 'verified',
      evidence_status: 'not_available',
      quality_status: 'BASELINE',
    },
  },
}

function cardsFor(kind: FixtureKind) {
  return {
    status: kind === 'degraded' ? 'DEGRADED_STRUCTURAL' : 'SUCCESS',
    degraded: kind === 'degraded',
    missing_components: kind === 'degraded' ? ['formula_cards'] : [],
    paper_workspace_status: (statuses[kind] as { paper_workspace_status: object }).paper_workspace_status,
    cards: {
      paper_card: paperCard,
      formula_cards: { formula_cards: kind === 'degraded' ? [] : formulaCards },
      teaching_cards: { teaching_cards: teachingCards },
    },
  }
}

async function json(route: Route, body: object, status = 200) {
  await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) })
}

export async function mockWorkspaceApi(page: Page, kind: FixtureKind) {
  await page.route('**/api/v1/**', async route => {
    const url = new URL(route.request().url())
    const pathname = url.pathname
    if (pathname === '/api/v1/library/search_runs') {
      await json(route, { search_runs: [] })
      return
    }
    if (pathname.endsWith('/understanding_status')) {
      await json(route, statuses[kind])
      return
    }
    if (pathname.endsWith('/cards')) {
      await json(route, cardsFor(kind))
      return
    }
    if (pathname.endsWith('/memory') && route.request().method() === 'GET') {
      await json(route, { records: [], schema_version: 2 })
      return
    }
    if (pathname.endsWith('/memory') && route.request().method() === 'DELETE') {
      await route.fulfill({ status: 204 })
      return
    }
    if (pathname.endsWith('/ask')) {
      await json(route, {
        status: 'SUCCESS',
        answer: 'The fixed offline answer is supported by fixture:paper:method.',
        evidence_refs: ['fixture:paper:method'],
      })
      return
    }
    await json(route, { detail: { code: 'FIXTURE_ROUTE_MISSING', message: `No offline route for ${pathname}` } }, 404)
  })
}

export const fixtureJobPath: Record<FixtureKind, string> = {
  success: '/learn/fixture-success',
  degraded: '/learn/fixture-degraded',
  blocked: '/learn/fixture-blocked',
  'no-llm': '/learn/fixture-no-llm',
}

export interface DirectionMockState {
  searchCreates: number
  searchPolls: number
  deepReadCreates: number
  deepReadPolls: number
  synchronousCalls: number
}

export async function mockDirectionTaskApi(page: Page): Promise<DirectionMockState> {
  const state: DirectionMockState = {
    searchCreates: 0,
    searchPolls: 0,
    deepReadCreates: 0,
    deepReadPolls: 0,
    synchronousCalls: 0,
  }
  const task = (taskId: string, kind: string, status: string, stage: string, progress: number, result: object | null = null) => ({
    task_id: taskId,
    kind,
    status,
    stage,
    progress,
    result,
    error: null,
    error_type: null,
  })
  const searchResult = {
    status: 'SUCCESS',
    direction_workspace_status: 'SUCCESS',
    message: 'Offline fixture search completed through the persistent task API.',
    query_plan: {
      user_query: 'offline reliability fixture',
      english_query: 'offline reliability fixture',
      core_terms: ['reliability', 'fixture'],
      query_variants: ['offline reliability fixture'],
    },
    papers: [
      {
        paper_id: 'fixture-direction-candidate',
        title: 'Synthetic Offline Reliability Paper',
        authors: ['Fixture Author'],
        year: 2026,
        venue: 'local fixture',
        source: 'offline_fixture',
        discovery_sources: ['offline_fixture'],
        pdf_url: '/e2e-fixtures/fixed-paper.pdf',
        pdf_available: true,
        fulltext_status: 'pdf_ready',
        selected_fulltext_source: 'local_fixture',
        can_enter_m2: true,
        m2_ready: true,
        relevance_score: 0.98,
        source_confidence: 'high',
        verification_status: 'verified',
        relevance_gate_evaluated: true,
        relevance_gate_passed: true,
        deep_read_relevance_passed: true,
        rule_relevance_score: 0.98,
        relevance_reason: 'Fixed deterministic E2E fixture.',
      },
    ],
  }

  await page.route('**/api/v1/**', async route => {
    const url = new URL(route.request().url())
    const pathname = url.pathname
    const method = route.request().method()
    if (pathname === '/api/v1/library/search_runs') {
      await json(route, { search_runs: [] })
      return
    }
    if (pathname === '/api/v1/directions/jobs/search' && method === 'POST') {
      state.searchCreates += 1
      await json(route, task('fixture-search-task', 'direction_search', 'PENDING', 'queued', 0))
      return
    }
    if (pathname === '/api/v1/directions/jobs/fixture-search-task' && method === 'GET') {
      state.searchPolls += 1
      await json(route, state.searchPolls === 1
        ? task('fixture-search-task', 'direction_search', 'RUNNING', 'ranking_candidates', 65)
        : task('fixture-search-task', 'direction_search', 'SUCCEEDED', 'completed', 100, searchResult))
      return
    }
    if (pathname === '/api/v1/directions/jobs/deep_read' && method === 'POST') {
      state.deepReadCreates += 1
      await json(route, task('fixture-deep-read-task', 'direction_deep_read', 'PENDING', 'queued', 0))
      return
    }
    if (pathname === '/api/v1/directions/jobs/fixture-deep-read-task' && method === 'GET') {
      state.deepReadPolls += 1
      await json(route, state.deepReadPolls === 1
        ? task('fixture-deep-read-task', 'direction_deep_read', 'RUNNING', 'canonicalizing', 70)
        : task('fixture-deep-read-task', 'direction_deep_read', 'SUCCEEDED', 'completed', 100, { job_id: 'fixture-deep-read' }))
      return
    }
    if (pathname === '/api/v1/directions/search' || pathname === '/api/v1/directions/deep_read') {
      state.synchronousCalls += 1
      await json(route, { detail: { code: 'SYNC_ENDPOINT_USED', message: 'The E2E client must prefer asynchronous jobs.' } }, 500)
      return
    }
    if (pathname.endsWith('/understanding_status')) {
      await json(route, statuses['no-llm'])
      return
    }
    await json(route, { detail: { code: 'FIXTURE_ROUTE_MISSING', message: `No offline route for ${pathname}` } }, 404)
  })
  return state
}
