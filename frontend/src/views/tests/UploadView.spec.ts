import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import UploadView from '../UploadView.vue'

const routerMock = vi.hoisted(() => ({
  push: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRouter: () => routerMock,
}))

describe('UploadView', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    routerMock.push.mockReset()
  })

  it('submits a PDF URL and navigates to the learning workspace', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ job_id: 'job-url', status: 'succeeded' }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const wrapper = mount(UploadView)

    await wrapper.get('button:nth-of-type(2)').trigger('click')
    await wrapper.get('[data-testid="pdf-url-input"]').setValue('https://example.org/paper.pdf')
    await wrapper.get('[data-testid="submit-upload"]').trigger('click')
    await flushPromises()

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const body = fetchMock.mock.calls[0][1].body as FormData
    expect(body.get('pdf_url')).toBe('https://example.org/paper.pdf')
    expect(routerMock.push).toHaveBeenCalledWith('/learn/job-url')
  })

  it('shows DOI NOT_IMPLEMENTED source status without navigating', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      json: async () => ({
        detail: {
          source_status: {
            source_type: 'doi',
            status: 'rejected',
            warnings: ['DOI_NOT_IMPLEMENTED'],
          },
        },
      }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const wrapper = mount(UploadView)

    await wrapper.get('button:nth-of-type(5)').trigger('click')
    await wrapper.get('[data-testid="doi-input"]').setValue('10.1145/example')
    await wrapper.get('[data-testid="submit-upload"]').trigger('click')
    await flushPromises()

    expect(routerMock.push).not.toHaveBeenCalled()
    expect(wrapper.get('[data-testid="source-status"]').text()).toContain('DOI_NOT_IMPLEMENTED')
    const body = fetchMock.mock.calls[0][1].body as FormData
    expect(body.get('doi')).toBe('10.1145/example')
  })

  it('submits an existing M2 artifact directory through local_path', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ job_id: 'job-m2', status: 'succeeded' }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const wrapper = mount(UploadView)

    await wrapper.get('button:nth-of-type(6)').trigger('click')
    await wrapper.get('[data-testid="m2-artifact-dir-input"]').setValue('D:\\Code\\Python\\Research-sensei\\reports\\m2_live_acceptance_work\\positive_2310_08800v2')
    await wrapper.get('[data-testid="submit-upload"]').trigger('click')
    await flushPromises()

    const body = fetchMock.mock.calls[0][1].body as FormData
    expect(body.get('local_path')).toBe('D:\\Code\\Python\\Research-sensei\\reports\\m2_live_acceptance_work\\positive_2310_08800v2')
    expect(routerMock.push).toHaveBeenCalledWith('/learn/job-m2')
  })
})
