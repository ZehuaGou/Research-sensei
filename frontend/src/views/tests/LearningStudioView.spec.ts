import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import LearningStudioView from '../LearningStudioView.vue'

const overview = {
  total_items: 4,
  due_count: 4,
  mastered_count: 0,
  reviewed_today: 0,
  papers: [{
    job_id: 'job-1',
    paper_title: 'Temporal Root Cause Analysis',
    item_count: 4,
    due_count: 4,
    mastered_count: 0,
    reviewed_count: 0,
    last_review_at: '',
  }],
  due_items: [],
  recent_attempts: [],
}

function jsonResponse(value: unknown) {
  return {
    ok: true,
    status: 200,
    text: async () => JSON.stringify(value),
  }
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('LearningStudioView', () => {
  it('imports a paper and starts a full-width learning session', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/learning/import')) {
        return jsonResponse({ job_id: 'job-1', imported_count: 4, overview })
      }
      if (url.endsWith('/learning/sessions')) {
        return jsonResponse({
          session_id: 'session-1',
          job_id: 'job-1',
          status: 'ACTIVE',
          total: 4,
          completed: 0,
          current: {
            session_id: 'session-1',
            item_id: 'item-1',
            position: 1,
            total: 4,
            question: 'Why is the temporal encoder needed?',
            target_concept: 'Temporal encoder',
            item_type: 'method',
            expected_answer_points: ['temporal dependencies'],
            why_it_matters: 'Connect the mechanism to the research problem.',
            answer_format: ['mechanism', 'evidence'],
            evidence_refs: ['passage:method'],
          },
          created_at: '2026-07-23T00:00:00Z',
          updated_at: '2026-07-23T00:00:00Z',
        })
      }
      if (url.endsWith('/learning/active-session')) {
        return jsonResponse({ job_id: 'job-1', session: null })
      }
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/study/:jobId?', component: LearningStudioView }],
    })
    await router.push('/study/job-1')
    await router.isReady()

    const wrapper = mount(LearningStudioView, {
      global: { plugins: [router] },
    })
    await flushPromises()

    expect(wrapper.get('h1').text()).toContain('Temporal Root Cause Analysis')
    expect(wrapper.text()).toContain('已准备 4 个学习节点')

    await wrapper.get('.paper-focus .primary-btn').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Why is the temporal encoder needed?')
    expect(wrapper.get('textarea').attributes('placeholder')).toContain('不要求背固定句子')
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/jobs/job-1/learning/sessions',
      expect.objectContaining({ method: 'POST' }),
    )
  })
})
