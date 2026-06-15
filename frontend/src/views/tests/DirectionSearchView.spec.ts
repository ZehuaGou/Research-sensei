import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import DirectionSearchView from '../DirectionSearchView.vue'

describe('DirectionSearchView', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('shows NOT_IMPLEMENTED backend status without fake papers', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        status: 'NOT_IMPLEMENTED',
        direction_workspace_status: 'NOT_IMPLEMENTED',
        message: 'DirectionWorkspace backend is not implemented yet.',
        seed_expansion_status: 'NOT_IMPLEMENTED',
        papers: [],
        warnings: [{ code: 'DIRECTION_WORKSPACE_NOT_IMPLEMENTED', message: 'No fake output.' }],
      }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mount(DirectionSearchView)
    await wrapper.get('[data-testid="direction-query"]').setValue('anomaly detection')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(wrapper.get('[data-testid="direction-status"]').text()).toContain('NOT_IMPLEMENTED')
    expect(wrapper.get('[data-testid="seed-expansion-panel"]').text()).toContain('NOT_IMPLEMENTED')
    expect(wrapper.text()).toContain('DIRECTION_WORKSPACE_NOT_IMPLEMENTED')
  })
})
