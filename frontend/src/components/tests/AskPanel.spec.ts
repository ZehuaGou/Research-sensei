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
          context_mode: 'full_paper',
          continued_from_history: false,
          focus_question: 'How does it work?',
          evidence_count: 1,
          selected_text_used: bodyHasSelection(init),
          full_text_chars: 47572,
          full_text_complete: true,
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
    localStorage.clear()
  })

  it('uses a readable default font and can request moving M4 to the other side', async () => {
    vi.stubGlobal('fetch', mockM4Fetch())
    const { wrapper } = mountPanel()
    await flushPromises()

    expect(wrapper.get('[data-testid="ask-panel"]').attributes('style')).toContain('--m4-font-size: 15px')
    expect(wrapper.get('[data-testid="m4-side-toggle"]').text()).toBe('左置')
    await wrapper.get('[data-testid="m4-side-toggle"]').trigger('click')
    expect(wrapper.emitted('toggleSide')).toHaveLength(1)
  })

  it('loads memory and sends full-paper questions with selected text', async () => {
    const fetchMock = mockM4Fetch()
    vi.stubGlobal('fetch', fetchMock)
    const { store, wrapper } = mountPanel()
    store.selectedText = 'attention architecture'
    await flushPromises()

    expect(wrapper.get('[data-testid="selected-context"]').text()).toContain('attention architecture')
    expect(wrapper.text()).toContain('整篇论文 + 选中文本')
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
      answer_mode: 'full_paper',
    })
    expect(wrapper.text()).toContain('模型不是平均看所有证据')
    expect(wrapper.find('.answer-bubble').exists()).toBe(true)
    expect(wrapper.get('.markdown-answer').findAll('p')).toHaveLength(3)
    expect(wrapper.get('[data-testid="context-trace"]').text()).toContain('4.8 万字全文')
    expect(wrapper.text()).toContain('为什么这种机制能连接稀疏证据？')
    expect(wrapper.text()).not.toContain('paper:b001')
    expect(wrapper.text()).not.toContain('m4_memory_2')
  })

  it('restores real recent answers so a refreshed page can continue the conversation', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/memory')) {
        return jsonResponse({
          records: [{
            memory_type: 'interactive_answer',
            question: '它为什么扩大搜索圆弧？',
            answer: '为了覆盖急剧弯曲的根，同时用直径相似性降低追错风险。',
            evidence_refs: ['paper:b004'],
            created_at: '2026-07-22T12:00:00Z',
            metadata: {
              status: 'SUCCESS',
              context_mode: 'full_paper',
              full_text_chars: 47572,
              full_text_complete: true,
            },
          }],
        })
      }
      throw new Error(`Unexpected fetch: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const { wrapper } = mountPanel()
    await flushPromises()

    expect(wrapper.text()).toContain('它为什么扩大搜索圆弧？')
    expect(wrapper.text()).toContain('为了覆盖急剧弯曲的根')
    expect(wrapper.get('[data-testid="context-trace"]').text()).toContain('4.8 万字全文')
    expect(wrapper.text()).not.toContain('已恢复这篇论文的上一轮问题')
  })

  it('reveals the latest message after reopening a long conversation', async () => {
    let resolveMemory: ((value: ReturnType<typeof jsonResponse>) => void) | undefined
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/memory')) {
        return await new Promise<ReturnType<typeof jsonResponse>>((resolve) => {
          resolveMemory = resolve
        })
      }
      throw new Error(`Unexpected fetch: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const { store, wrapper } = mountPanel()
    store.replaceChat([
      { role: 'user', content: '第一轮问题', timestamp: 1 },
      { role: 'assistant', content: '最新一轮回答', timestamp: 2 },
    ])
    await wrapper.vm.$nextTick()

    const messages = wrapper.get('.messages').element as HTMLElement
    const scrollTo = vi.fn()
    Object.defineProperty(messages, 'scrollHeight', { configurable: true, value: 2400 })
    messages.scrollTo = scrollTo

    expect(resolveMemory).toBeTypeOf('function')
    resolveMemory?.(jsonResponse({ records: [] }))
    await flushPromises()

    expect(scrollTo).toHaveBeenCalledWith({ top: 2400, behavior: 'auto' })
    expect(wrapper.text()).toContain('最新一轮回答')
  })

  it('uses a floating question navigator to return to earlier conversation nodes', async () => {
    vi.stubGlobal('fetch', mockM4Fetch())
    const { store, wrapper } = mountPanel()
    store.replaceChat([
      { role: 'user', content: '第一个问题：这篇论文解决了什么？', timestamp: 1 },
      { role: 'assistant', content: '第一个回答', timestamp: 2 },
      { role: 'user', content: '第二个问题：核心方法如何实现？', timestamp: 3 },
      { role: 'assistant', content: '第二个回答', timestamp: 4 },
      { role: 'user', content: '第三个问题：实验有哪些限制？', timestamp: 5 },
      { role: 'assistant', content: '第三个回答', timestamp: 6 },
    ])
    await flushPromises()

    expect(wrapper.get('[data-testid="question-navigator-toggle"]').text()).toContain('3/3')
    await wrapper.get('[data-testid="question-navigator-toggle"]').trigger('click')

    const nodeButtons = wrapper.findAll('.question-node')
    expect(nodeButtons).toHaveLength(3)
    expect(nodeButtons[0].text()).toContain('第一个问题')
    expect(nodeButtons[1].text()).toContain('第二个问题')

    const messages = wrapper.get('.messages').element as HTMLElement
    const secondQuestion = wrapper.get('[data-question-message-index="2"]').element as HTMLElement
    const scrollTo = vi.fn()
    Object.defineProperty(messages, 'scrollTop', { configurable: true, value: 500 })
    messages.scrollTo = scrollTo
    vi.spyOn(messages, 'getBoundingClientRect').mockReturnValue({ top: 100 } as DOMRect)
    vi.spyOn(secondQuestion, 'getBoundingClientRect').mockReturnValue({ top: 340 } as DOMRect)

    await nodeButtons[1].trigger('click')

    expect(scrollTo).toHaveBeenCalledWith({ top: 728, behavior: 'auto' })
    expect(wrapper.find('.question-node-popover').exists()).toBe(false)

    await wrapper.get('[data-testid="question-navigator-toggle"]').trigger('click')
    expect(wrapper.findAll('.question-node')[1].attributes('aria-current')).toBe('step')
  })

  it('uses one full-paper request without the old evidence-preview round trip', async () => {
    let resolveFullPaper: ((value: ReturnType<typeof jsonResponse>) => void) | undefined
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.endsWith('/memory')) return jsonResponse({ records: [] })
      const body = init?.body ? JSON.parse(String(init.body)) : {}
      if (url.endsWith('/ask') && body.answer_mode === 'full_paper') {
        return await new Promise<ReturnType<typeof jsonResponse>>(resolve => {
          resolveFullPaper = resolve
        })
      }
      throw new Error(`Unexpected fetch: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const { wrapper } = mountPanel()
    await flushPromises()

    await wrapper.get('[data-testid="ask-input"]').setValue('说得再详细一些，这到底是什么、怎么实现的？')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toContain('正在阅读整篇论文并组织回答')
    expect(fetchMock.mock.calls.filter(call => String(call[0]).endsWith('/ask'))).toHaveLength(1)
    expect(resolveFullPaper).toBeTypeOf('function')

    resolveFullPaper?.(jsonResponse({
      status: 'SUCCESS',
      answer: '完整回答：先解释它是什么，再按实际执行顺序讲清楚实现机制和实验结果。',
      evidence_refs: ['paper:b001'],
      context_trace: {
        scope: 'paper',
        context_mode: 'full_paper',
        continued_from_history: false,
        focus_question: '怎么实现的？',
        evidence_count: 1,
        selected_text_used: false,
        full_text_chars: 47572,
        full_text_complete: true,
      },
    }))
    await flushPromises()

    expect(wrapper.text()).toContain('完整回答')
    expect(wrapper.text()).not.toContain('正在阅读整篇论文并组织回答')
  })

  it('renders model markdown as clean reader text', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/memory')) return jsonResponse({ records: [] })
      if (url.endsWith('/ask')) {
        return jsonResponse({
          status: 'SUCCESS',
          answer: '### 核心方法\n\n**第一步**：读取图像。\n\n---\n\n- 继续追踪根节点。',
          evidence_refs: [],
          context_trace: {
            scope: 'paper',
            context_mode: 'full_paper',
            full_text_chars: 47572,
            full_text_complete: true,
            evidence_count: 0,
          },
        })
      }
      throw new Error(`Unexpected fetch: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const { wrapper } = mountPanel()
    await flushPromises()

    await wrapper.get('[data-testid="ask-input"]').setValue('请解释方法')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toContain('核心方法')
    expect(wrapper.get('.markdown-answer h3').text()).toBe('核心方法')
    expect(wrapper.text()).toContain('第一步：读取图像。')
    expect(wrapper.text()).toContain('继续追踪根节点。')
    expect(wrapper.get('.markdown-answer ul').text()).toContain('继续追踪根节点。')
    expect(wrapper.get('.markdown-answer strong').text()).toBe('第一步')
    expect(wrapper.text()).not.toContain('###')
    expect(wrapper.text()).not.toContain('**')
    expect(wrapper.text()).not.toContain('---')
  })

  it('turns model markdown tables into readable rows', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/memory')) return jsonResponse({ records: [] })
      if (url.endsWith('/ask')) return jsonResponse({
        status: 'SUCCESS',
        answer: '## 条件对比\n\n| 条件 | 处理 |\n|---|---|\n| 弯曲根 | 缩短节点间距 |\n| 交叉根 | 约束直径 |',
        evidence_refs: [],
        context_trace: { scope: 'paper', context_mode: 'full_paper', evidence_count: 0 },
      })
      throw new Error(`Unexpected fetch: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const { wrapper } = mountPanel()
    await flushPromises()

    await wrapper.get('[data-testid="ask-input"]').setValue('对比两种情况')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    const rows = wrapper.get('.markdown-answer table').findAll('tr')
    expect(rows).toHaveLength(3)
    expect(rows[1].text()).toContain('弯曲根')
    expect(rows[1].text()).toContain('缩短节点间距')
    expect(rows[2].text()).toContain('交叉根')
    expect(rows[2].text()).toContain('约束直径')
    expect(wrapper.text()).not.toContain('|---|')
  })

  it('escapes model HTML and renders fenced latex with KaTeX', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/memory')) return jsonResponse({ records: [] })
      if (url.endsWith('/ask')) return jsonResponse({
        status: 'SUCCESS',
        answer: '### 公式\n\n<script>window.bad = true</script>\n\n```latex\ny = Wx + b\n```',
        evidence_refs: [],
        context_trace: { scope: 'paper', context_mode: 'full_paper', evidence_count: 0 },
      })
      throw new Error(`Unexpected fetch: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const { wrapper } = mountPanel()
    await flushPromises()

    await wrapper.get('[data-testid="ask-input"]').setValue('解释公式')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.find('.markdown-answer script').exists()).toBe(false)
    expect(wrapper.text()).toContain('<script>window.bad = true</script>')
    expect(wrapper.html()).toContain('markdown-math')
    expect(wrapper.html()).toContain('katex')
  })

  it('keeps strict lookup only when the user explicitly chooses 找证据', async () => {
    const fetchMock = mockM4Fetch()
    vi.stubGlobal('fetch', fetchMock)
    const { wrapper } = mountPanel()
    await flushPromises()

    await wrapper.get('#m4-mode-evidence').trigger('click')
    await wrapper.get('[data-testid="ask-input"]').setValue('这条结论对应哪段正文？')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    const askCall = fetchMock.mock.calls.find(call => String(call[0]).endsWith('/ask'))
    expect(JSON.parse(String((askCall![1] as RequestInit).body))).toMatchObject({
      answer_mode: 'evidence_only',
    })
  })

  it('routes explanation questions back to full-paper mode instead of returning raw evidence', async () => {
    const fetchMock = mockM4Fetch()
    vi.stubGlobal('fetch', fetchMock)
    const { wrapper } = mountPanel()
    await flushPromises()

    await wrapper.get('#m4-mode-evidence').trigger('click')
    await wrapper.get('[data-testid="ask-input"]').setValue('请按实际执行顺序展开论文的核心方法。')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    const askCall = fetchMock.mock.calls.find(call => String(call[0]).endsWith('/ask'))
    expect(JSON.parse(String((askCall![1] as RequestInit).body))).toMatchObject({
      question: '请按实际执行顺序展开论文的核心方法。',
      answer_mode: 'full_paper',
    })
    expect(wrapper.get('#m4-mode-paper').attributes('aria-selected')).toBe('true')
  })

  it('shows mode-specific starter prompts and sends evidence starters as strict lookup', async () => {
    const fetchMock = mockM4Fetch()
    vi.stubGlobal('fetch', fetchMock)
    const { wrapper } = mountPanel()
    await flushPromises()

    await wrapper.get('#m4-mode-evidence').trigger('click')
    const starter = wrapper.findAll('.starter-prompts button').find(button => button.text().includes('核心方法对应哪些原文'))
    expect(starter).toBeDefined()
    await starter!.trigger('click')
    expect(wrapper.get('[data-testid="ask-input"]').element).toHaveProperty(
      'value',
      '这篇论文的核心方法对应哪些原文段落或页码？',
    )

    await wrapper.get('form').trigger('submit')
    await flushPromises()
    const askCall = fetchMock.mock.calls.find(call => String(call[0]).endsWith('/ask'))
    expect(JSON.parse(String((askCall![1] as RequestInit).body))).toMatchObject({
      answer_mode: 'evidence_only',
    })
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
    expect(wrapper.get('.markdown-answer').findAll('p')).toHaveLength(3)
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
