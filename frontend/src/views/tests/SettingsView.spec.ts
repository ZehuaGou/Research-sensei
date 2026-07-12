import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import SettingsView from '../SettingsView.vue'

describe('SettingsView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('loads ccswitch settings and model choices from the versioned settings API', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        active_provider: 'ccswitch',
        provider_display_name: 'ccswitch',
        base_url: 'http://127.0.0.1:15721/v1',
        api_key_env: '',
        model: 'auto',
        model_options: [{ id: 'auto', label: 'auto', source: '当前配置' }],
        enable_env: 'RESEARCHSENSEI_ENABLE_API_LLM',
        llm_enabled: true,
        api_key_configured: true,
        provider_known: true,
      }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mount(SettingsView)
    await flushPromises()

    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/settings')
    const inputs = wrapper.findAll('input')
    expect((inputs[0].element as HTMLInputElement).value).toBe('ccswitch')
    expect((inputs[1].element as HTMLInputElement).value).toBe('http://127.0.0.1:15721/v1')
    expect((inputs[2].element as HTMLInputElement).value).toBe('')
    expect((wrapper.get('[data-testid="model-select"]').element as HTMLSelectElement).value).toBe('auto')
    expect(wrapper.text()).toContain('实时 LLM')
    expect(wrapper.text()).toContain('已启用')
    expect(wrapper.text()).toContain('密钥')
    expect(wrapper.text()).toContain('已配置')
  })

  it('saves selected model through the settings API', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          active_provider: 'ccswitch',
          provider_display_name: 'ccswitch',
          base_url: 'http://127.0.0.1:15721/v1',
          api_key_env: '',
          model: 'claude-sonnet-4-6',
          model_options: [
            { id: 'claude-sonnet-4-6', label: 'claude-sonnet-4-6', source: '当前配置' },
            { id: 'deepseek-v4-flash', label: 'deepseek-v4-flash', source: '最近使用' },
          ],
          model_env: 'RESEARCHSENSEI_LLM_MODEL',
          enable_env: 'RESEARCHSENSEI_ENABLE_API_LLM',
          llm_enabled: true,
          api_key_configured: true,
          provider_known: true,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          active_provider: 'ccswitch',
          provider_display_name: 'ccswitch',
          base_url: 'http://127.0.0.1:15721/v1',
          api_key_env: '',
          model: 'deepseek-v4-flash',
          model_options: [
            { id: 'claude-sonnet-4-6', label: 'claude-sonnet-4-6', source: '当前配置' },
            { id: 'deepseek-v4-flash', label: 'deepseek-v4-flash', source: '最近使用' },
          ],
          model_env: 'RESEARCHSENSEI_LLM_MODEL',
          enable_env: 'RESEARCHSENSEI_ENABLE_API_LLM',
          llm_enabled: true,
          api_key_configured: true,
          provider_known: true,
        }),
      })
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mount(SettingsView)
    await flushPromises()

    await wrapper.get('[data-testid="model-select"]').setValue('deepseek-v4-flash')
    await wrapper.get('[data-testid="save-model"]').trigger('click')
    await flushPromises()

    expect(fetchMock.mock.calls[1][0]).toBe('/api/v1/settings')
    expect(fetchMock.mock.calls[1][1]).toMatchObject({
      method: 'PATCH',
      headers: { 'content-type': 'application/json' },
    })
    expect(JSON.parse(String((fetchMock.mock.calls[1][1] as RequestInit).body))).toEqual({
      model: 'deepseek-v4-flash',
    })
    expect(wrapper.text()).toContain('模型已保存')
  })

  it('tests provider readiness through the backend settings endpoint', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          active_provider: 'ccswitch',
          provider_display_name: 'ccswitch',
          base_url: 'http://127.0.0.1:15721/v1',
          api_key_env: '',
          model: 'auto',
          model_options: [{ id: 'auto', label: 'auto', source: '当前配置' }],
          enable_env: 'RESEARCHSENSEI_ENABLE_API_LLM',
          llm_enabled: true,
          api_key_configured: true,
          provider_known: true,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ ok: true }),
      })
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mount(SettingsView)
    await flushPromises()
    await wrapper.get('[data-testid="test-connection"]').trigger('click')
    await flushPromises()

    expect(fetchMock.mock.calls[1][0]).toBe('/api/v1/settings/test')
    expect(fetchMock.mock.calls[1][1]).toMatchObject({ method: 'POST' })
    expect(wrapper.text()).toContain('连接可用')
  })
})
