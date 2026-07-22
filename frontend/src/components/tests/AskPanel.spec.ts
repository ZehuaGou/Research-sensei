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
        status: 'SUCCESS',
        answer: [
          '可以先把它理解成：模型不是平均看所有证据，而是先找和问题最相关的片段。',
          '关键机制是 attention 会给不同片段分配权重，权重高的部分更影响最终表示，所以稀疏证据也能被拉出来。',
          '能追到的证据是论文正文里的方法描述和实验对比，它们说明这种权重分配支撑了结论。',
        ].join('\n\n'),
        evidence_refs: ['paper:b001'],
        memory_refs: ['m4_memory_2'],
        uncertainty: '回答基于当前论文证据。',
        follow_up_suggestions: ['为什么这种机制能连接稀疏证据？'],
        context_trace: {
          scope: bodyHasSelection(init) ? 'selection' : 'paper',
          continued_from_history: false,
          focus_question: 'How does it work?',
          evidence_count: 1,
          selected_text_used: bodyHasSelection(init),
        },
      })
    }
    if (url.endsWith('/advisor/question')) {
      const body = init?.body ? JSON.parse(String(init.body)) : {}
      const focus = typeof body.user_question === 'string' ? body.user_question : ''
      return jsonResponse({
        question: focus
          ? `围绕你的问题“${focus}”，请按你的问题、论文回答、证据依据回答。`
          : '为什么这个方法能回应论文问题？请按问题、机制、证据回答。',
        user_question: focus,
        expected_answer_points: ['问题：论文要解决的问题', '机制：方法机制', '证据：对应证据'],
        answer_format: focus
          ? ['先用一句自然话回答你真正想问的点', '再把论文里的机制或发现解释成能听懂的因果链', '最后补一句：这个判断主要靠哪类正文证据支撑']
          : ['先说明论文真正卡住的地方', '再讲方法怎么接上这个困难', '最后补一句它依靠哪类正文证据'],
        evidence_refs: ['paper:b002'],
      })
    }
    if (url.endsWith('/advisor/evaluate')) {
      return jsonResponse({
        score: 0.67,
        covered_points: ['机制：方法机制'],
        missing_points: ['证据：对应证据'],
        feedback: '方向是对的，但还需要把证据补实。',
        next_question: '请补一句：论文中哪类证据支持这个机制？',
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
    expect(wrapper.text()).toContain('选中文本已加入上下文')
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
    expect(wrapper.text()).toContain('模型不是平均看所有证据')
    expect(wrapper.find('.answer-bubble').exists()).toBe(true)
    expect(wrapper.find('.answer-block.tone-lead').text()).toContain('重点')
    expect(wrapper.find('.answer-block.tone-concept').text()).toContain('关键机制')
    expect(wrapper.find('.answer-block.tone-evidence').text()).toContain('证据')
    expect(wrapper.findAll('.answer-keyword').map(node => node.text())).toContain('证据')
    expect(wrapper.get('[data-testid="context-trace"]').text()).toContain('1 条已验证证据')
    expect(wrapper.text()).toContain('为什么这种机制能连接稀疏证据？')
    expect(wrapper.text()).not.toContain('paper:b001')
    expect(wrapper.text()).not.toContain('m4_memory_2')
  })

  it('shows verified evidence before the model enhancement finishes', async () => {
    let resolveEnhanced: ((value: ReturnType<typeof jsonResponse>) => void) | undefined
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      const body = init?.body ? JSON.parse(String(init.body)) : {}
      if (body.answer_mode === 'evidence_only') {
        return jsonResponse({
          status: 'SUCCESS',
          answer: '先显示的论文证据答案：这个方法通过证据片段完成核心机制。',
          evidence_refs: ['paper:b001'],
          context_trace: {
            scope: 'paper',
            continued_from_history: false,
            focus_question: '怎么实现的？',
            evidence_count: 1,
            selected_text_used: false,
          },
        })
      }
      if (body.answer_mode === 'enhanced') {
        return await new Promise<ReturnType<typeof jsonResponse>>(resolve => {
          resolveEnhanced = resolve
        })
      }
      return jsonResponse({ records: [] })
    })
    vi.stubGlobal('fetch', fetchMock)
    const { wrapper } = mountPanel()
    await flushPromises()

    await wrapper.get('[data-testid="ask-input"]').setValue('说得再详细一些，这到底是什么、怎么实现的？')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toContain('先显示的论文证据答案')
    expect(wrapper.text()).toContain('正在读证据并组织回答')
    expect(resolveEnhanced).toBeTypeOf('function')

    resolveEnhanced?.(jsonResponse({
      status: 'SUCCESS',
      answer: '模型增强后的证据答案：先解释是什么，再解释实现机制。',
      evidence_refs: ['paper:b001'],
      context_trace: {
        scope: 'paper',
        continued_from_history: false,
        focus_question: '怎么实现的？',
        evidence_count: 1,
        selected_text_used: false,
      },
    }))
    await flushPromises()

    expect(wrapper.text()).toContain('模型增强后的证据答案')
    expect(wrapper.text()).not.toContain('先显示的论文证据答案')
  })

  it('does not replace verified evidence with an unsupported model failure', async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      const body = init?.body ? JSON.parse(String(init.body)) : {}
      if (body.answer_mode === 'evidence_only') {
        return jsonResponse({
          status: 'SUCCESS',
          answer: '已经通过论文证据验证的本地答案。',
          evidence_refs: ['paper:b001'],
        })
      }
      if (body.answer_mode === 'enhanced') {
        return jsonResponse({
          status: 'DEGRADED',
          answer: 'M4 这次没有拿到可用的大模型解释。',
          evidence_refs: [],
          warnings: [{ code: 'M4_CLAIM_UNSUPPORTED', message: '模型结论未通过证据审计。' }],
        })
      }
      return jsonResponse({ records: [] })
    })
    vi.stubGlobal('fetch', fetchMock)
    const { wrapper } = mountPanel()
    await flushPromises()

    await wrapper.get('[data-testid="ask-input"]').setValue('这个方法怎么实现？')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toContain('已经通过论文证据验证的本地答案')
    expect(wrapper.text()).toContain('模型增强暂时没有完成')
    expect(wrapper.text()).not.toContain('没有拿到可用的大模型解释')
  })

  it('does not flash an ungrounded degraded preview while enhancement is running', async () => {
    let resolveEnhanced: ((value: ReturnType<typeof jsonResponse>) => void) | undefined
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      const body = init?.body ? JSON.parse(String(init.body)) : {}
      if (body.answer_mode === 'evidence_only') {
        return jsonResponse({
          status: 'DEGRADED',
          answer: '证据不足，暂不展开。',
          evidence_refs: [],
        })
      }
      if (body.answer_mode === 'enhanced') {
        return await new Promise<ReturnType<typeof jsonResponse>>(resolve => {
          resolveEnhanced = resolve
        })
      }
      return jsonResponse({ records: [] })
    })
    vi.stubGlobal('fetch', fetchMock)
    const { wrapper } = mountPanel()
    await flushPromises()

    await wrapper.get('[data-testid="ask-input"]').setValue('这篇论文真正解决了什么问题？')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.text()).not.toContain('证据不足，暂不展开')
    expect(wrapper.text()).toContain('正在读证据并组织回答')

    resolveEnhanced?.(jsonResponse({
      status: 'SUCCESS',
      answer: '论文解决了人工追踪根系既耗时又容易出错的问题。',
      evidence_refs: ['paper:b001'],
    }))
    await flushPromises()

    expect(wrapper.text()).toContain('人工追踪根系既耗时又容易出错')
  })

  it('answers a custom user question before creating a focused advisor question', async () => {
    const fetchMock = mockM4Fetch()
    vi.stubGlobal('fetch', fetchMock)
    const { store, wrapper } = mountPanel()
    store.selectedText = 'Attention helps connect scattered evidence.'
    await flushPromises()

    await wrapper.get('[data-testid="ask-input"]').setValue('为什么这个方法能处理稀疏证据？')
    await wrapper.get('[data-testid="advisor-button"]').trigger('click')
    await flushPromises()
    await flushPromises()

    const askCall = fetchMock.mock.calls.find(call => String(call[0]).endsWith('/ask'))
    expect(askCall).toBeTruthy()
    expect(JSON.parse(String((askCall![1] as RequestInit).body))).toMatchObject({
      question: '为什么这个方法能处理稀疏证据？',
      selected_text: 'Attention helps connect scattered evidence.',
      context_scope: 'selection',
    })

    const advisorCall = fetchMock.mock.calls.find(call => String(call[0]).endsWith('/advisor/question'))
    expect(advisorCall).toBeTruthy()
    expect(JSON.parse(String((advisorCall![1] as RequestInit).body))).toEqual({
      advisor_mode: 'group_meeting',
      user_question: '为什么这个方法能处理稀疏证据？',
      selected_text: 'Attention helps connect scattered evidence.',
    })
    expect(wrapper.text()).toContain('模型不是平均看所有证据')
    expect(wrapper.findAll('.answer-block').length).toBeGreaterThanOrEqual(3)
    expect(wrapper.text()).toContain('围绕你的问题：为什么这个方法能处理稀疏证据？')
    expect(wrapper.get('[data-testid="advisor-card"]').text()).toContain('先用一句自然话回答你真正想问的点')
    expect(wrapper.text()).not.toContain('paper:b001')
    expect(wrapper.text()).not.toContain('paper:b002')
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
    expect(wrapper.get('[data-testid="advisor-card"]').text()).toContain('先说明论文真正卡住的地方')
    expect(wrapper.text()).not.toContain('paper:b002')

    await wrapper.get('[data-testid="advisor-answer"]').setValue('这个方法用 attention 连接证据。')
    await wrapper.get('form.advisor-composer').trigger('submit')
    await flushPromises()

    const evaluateCall = fetchMock.mock.calls.find(call => String(call[0]).endsWith('/advisor/evaluate'))
    expect(evaluateCall).toBeTruthy()
    expect(JSON.parse(String((evaluateCall![1] as RequestInit).body))).toMatchObject({
      question: '为什么这个方法能回应论文问题？请按问题、机制、证据回答。',
      user_answer: '这个方法用 attention 连接证据。',
      evidence_refs: ['paper:b002'],
    })
    expect(wrapper.get('[data-testid="advisor-feedback"]').text()).toContain('方向是对的')
    expect(wrapper.text()).toContain('请补一句：论文中哪类证据支持这个机制？')
    expect(wrapper.text()).not.toContain('paper:b002')
  })
})

function bodyHasSelection(init?: RequestInit) {
  if (!init?.body) return false
  const body = JSON.parse(String(init.body)) as { selected_text?: string }
  return Boolean(body.selected_text)
}
