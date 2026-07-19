import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useLearningStore } from './learning'

describe('learning store paper-scoped conversations', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('keeps each paper conversation isolated and restores it when switching back', () => {
    const store = useLearningStore()
    store.setCurrentJob('paper-a')
    store.addMessage({ role: 'user', content: 'A 的问题', timestamp: 1 })

    store.setCurrentJob('paper-b')
    expect(store.chatHistory).toEqual([])
    store.addMessage({ role: 'user', content: 'B 的问题', timestamp: 2 })

    store.setCurrentJob('paper-a')
    expect(store.chatHistory.map(message => message.content)).toEqual(['A 的问题'])
  })
})
