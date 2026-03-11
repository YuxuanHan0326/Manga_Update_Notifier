import { describe, expect, it } from 'vitest'
import {
  buildCheckCronFromHours,
  buildDailyCronFromTime,
  parseCheckCronToHours,
  parseDailyCronToTime,
  statusText
} from './utils'

describe('statusText', () => {
  it('returns new when summary is missing', () => {
    expect(statusText({ summarized_at: null, notified_at: null })).toBe('未汇总')
  })

  it('returns notified when both timestamps exist', () => {
    expect(statusText({ summarized_at: 'x', notified_at: 'y' })).toBe('已通知')
  })
})

describe('schedule cron helpers', () => {
  it('builds simple check cron from hours', () => {
    expect(buildCheckCronFromHours(6)).toBe('0 */6 * * *')
    expect(buildCheckCronFromHours(24)).toBe('0 0 * * *')
  })

  it('parses check cron to hours when pattern is supported', () => {
    expect(parseCheckCronToHours('0 */8 * * *')).toBe(8)
    expect(parseCheckCronToHours('0 0 * * *')).toBe(24)
    expect(parseCheckCronToHours('15 */8 * * *')).toBeNull()
  })

  it('builds and parses daily summary time cron', () => {
    expect(buildDailyCronFromTime('21:30')).toBe('30 21 * * *')
    expect(buildDailyCronFromTime('bad-value')).toBe('0 21 * * *')
    expect(parseDailyCronToTime('30 21 * * *')).toBe('21:30')
    expect(parseDailyCronToTime('30 21 * * 1')).toBeNull()
  })
})
