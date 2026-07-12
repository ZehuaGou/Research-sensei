import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import HomeView from '../HomeView.vue'

const routerPush = vi.hoisted(() => vi.fn())

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: routerPush }),
}))

describe('HomeView', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    window.localStorage.clear()
    routerPush.mockReset()
  })

  it('loads recent jobs from the versioned jobs API', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        jobs: [
          {
            job_id: 'job-1',
            source_path: 'D:\\Code\\Python\\Research-sensei\\workspace\\runs\\paper.pdf',
            status: 'succeeded',
          },
        ],
      }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mount(HomeView, {
      global: {
        stubs: {
          RouterLink: { props: ['to'], template: '<a :href="to"><slot /></a>' },
        },
      },
    })
    await flushPromises()

    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/jobs')
    expect(wrapper.text()).toContain('paper.pdf')
    expect(wrapper.text()).toContain('已完成')
  })

  it('removes a recent job from the list', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          jobs: [
            {
              job_id: 'job-1',
              source_path: 'paper.pdf',
              status: 'succeeded',
            },
          ],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'DELETED', job_id: 'job-1' }),
      })
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mount(HomeView, {
      global: {
        stubs: {
          RouterLink: { props: ['to'], template: '<a :href="to"><slot /></a>' },
        },
      },
    })
    await flushPromises()

    await wrapper.get('[data-testid="delete-job"]').trigger('click')
    await flushPromises()

    expect(fetchMock.mock.calls[1][0]).toBe('/api/v1/jobs/job-1')
    expect(fetchMock.mock.calls[1][1]).toMatchObject({ method: 'DELETE' })
    expect(wrapper.text()).not.toContain('paper.pdf')
    expect(window.localStorage.getItem('researchsensei.deletedJobIds')).toContain('job-1')
  })
})
