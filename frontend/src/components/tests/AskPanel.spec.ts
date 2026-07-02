import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import AskPanel from '../layout/AskPanel.vue'
import { useLearningStore } from '../../stores/learning'

function jsonResponse(data: unknown) {
  return {
    ok: true,
    json: async () => data,
  }
}

function mockM4Fetch() {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    const method = init?.method || 'GET'
    if (url.endsWith('/memory') && method === 'DELETE') {
      return jsonResponse({ status: 'CLEARED', records: [] })
    }
    if (url.endsWith('/memory')) {
      return jsonResponse({ records: [{ memory_id: 'm4_memory_1' }] })
    }
    if (url.endsWith('/ask')) {
      return jsonResponse({
        answer: 'M4 的正文回答。',
        evidence_refs: ['paper:b001'],
        memory_refs: ['m4_memory_2'],
      })
    }
    if (url.endsWith('/advisor/question')) {
      return jsonResponse({
        question: '为什么这个方法能回应论文问题？',
        expected_answer_points: ['论文要解决的问题', '方法机制', '对应证据'],
        evidence_refs: ['paper:b002'],
      })
    }
    throw new Error(`Unexpected fetch: ${url}`)
  })
}

function mountPanel() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const store = useLearningStore()
  store.currentJobId = 'job-123'
  return {
    store,
    wrapper: mount(AskPanel, {
      global: {
        plugins: [pinia],
      },
    }),
  }
}

describe('AskPanel', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('loads memory and sends evidence-bound questions with selected text', async () => {
    const fetchMock = mockM4Fetch()
    vi.stubGlobal('fetch', fetchMock)
    const { store, wrapper } = mountPanel()
    store.selectedText = 'attention architecture'
    await flushPromises()

    expect(wrapper.get('[data-testid="selected-context"]').text()).toContain('attention architecture')
    expect(wrapper.text()).toContain('论文问题基于当前证据回答')
    expect(wrapper.text()).not.toContain('已记住')

    await wrapper.get('[data-testid="ask-input"]').setValue('How does it work?')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    const askCall = fetchMock.mock.calls.find(call => String(call[0]).endsWith('/ask'))
    expect(askCall).toBeTruthy()
    expect(String(askCall![0])).toBe('/api/v1/jobs/job-123/ask')
    expect(JSON.parse(String((askCall![1] as RequestInit).body))).toMatchObject({
      question: 'How does it work?',
      selected_text: 'attention architecture',
      context_scope: 'selection',
    })
    expect(wrapper.text()).toContain('M4 的正文回答。')
    expect(wrapper.text()).not.toContain('paper:b001')
    expect(wrapper.text()).not.toContain('m4_memory_2')
  })

  it('requests advisor questions without exposing internal evidence refs', async () => {
    const fetchMock = mockM4Fetch()
    vi.stubGlobal('fetch', fetchMock)
    const { wrapper } = mountPanel()
    await flushPromises()

    await wrapper.get('[data-testid="advisor-button"]').trigger('click')
    await flushPromises()

    const advisorCall = fetchMock.mock.calls.find(call => String(call[0]).endsWith('/advisor/question'))
    expect(advisorCall).toBeTruthy()
    expect(String(advisorCall![0])).toBe('/api/v1/jobs/job-123/advisor/question')
    expect(JSON.parse(String((advisorCall![1] as RequestInit).body))).toEqual({
      advisor_mode: 'group_meeting',
    })
    expect(wrapper.text()).toContain('组会追问：为什么这个方法能回应论文问题？')
    expect(wrapper.text()).toContain('参考回答要点：论文要解决的问题；方法机制；对应证据')
    expect(wrapper.text()).not.toContain('paper:b002')
  })
})
