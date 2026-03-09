import { describe, expect, it } from 'vitest'
import { statusText } from './utils'

describe('statusText', () => {
  it('returns new when summary is missing', () => {
    expect(statusText({ summarized_at: null, notified_at: null })).toBe('new')
  })

  it('returns notified when both timestamps exist', () => {
    expect(statusText({ summarized_at: 'x', notified_at: 'y' })).toBe('notified')
  })
})
