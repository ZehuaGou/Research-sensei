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

  function sourceButton(wrapper: any, label: string) {
    const button = wrapper.findAll('button').find((item: any) => item.text().includes(label))
    expect(button).toBeDefined()
    return button!
  }

  it('submits a PDF URL and navigates to the learning workspace', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ job_id: 'job-url', status: 'succeeded' }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const wrapper = mount(UploadView)

    await sourceButton(wrapper, 'PDF 链接').trigger('click')
    await wrapper.get('[data-testid="pdf-url-input"]').setValue('https://example.org/paper.pdf')
    await wrapper.get('[data-testid="submit-upload"]').trigger('click')
    await flushPromises()

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/documents/jobs/parse')
    const body = fetchMock.mock.calls[0][1].body as FormData
    expect(body.get('pdf_url')).toBe('https://example.org/paper.pdf')
    expect(routerMock.push).toHaveBeenCalledWith('/learn/job-url')
  })

  it('shows DOI OA-resolution source status without navigating when no legal PDF is found', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      json: async () => ({
        detail: {
          status: 'NO_LEGAL_OA_FULLTEXT_FOUND',
          source_status: {
            source_type: 'doi',
            status: 'rejected',
            warnings: ['UNPAYWALL_NOT_FOUND'],
          },
        },
      }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const wrapper = mount(UploadView)

    await sourceButton(wrapper, 'DOI').trigger('click')
    await wrapper.get('[data-testid="doi-input"]').setValue('10.1145/example')
    await wrapper.get('[data-testid="submit-upload"]').trigger('click')
    await flushPromises()

    expect(routerMock.push).not.toHaveBeenCalled()
    expect(wrapper.get('[data-testid="source-status"]').text()).toContain('UNPAYWALL_NOT_FOUND')
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

    await sourceButton(wrapper, 'M2 目录').trigger('click')
    await wrapper.get('[data-testid="m2-artifact-dir-input"]').setValue('D:\\Code\\Python\\Research-sensei\\reports\\m2_live_acceptance_work\\positive_2310_08800v2')
    await wrapper.get('[data-testid="submit-upload"]').trigger('click')
    await flushPromises()

    const body = fetchMock.mock.calls[0][1].body as FormData
    expect(body.get('local_path')).toBe('D:\\Code\\Python\\Research-sensei\\reports\\m2_live_acceptance_work\\positive_2310_08800v2')
    expect(routerMock.push).toHaveBeenCalledWith('/learn/job-m2')
  })
})
