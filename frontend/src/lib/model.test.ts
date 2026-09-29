import { describe, expect, it } from 'vitest'
import { applyArea, applyPrice, baseCur, initialStart, ModelData, ourSeries, qLabel, sliderCtx } from './model'

// ряды очереди 1 модели 09_09_26 (Продажи!U12/U15 →), как отдаёт API
const labels = ['1кв. 26', '2кв. 26', '3кв. 26', '4кв. 26', '1кв. 27', '2кв. 27', '3кв. 27', '4кв. 27']
const price = [497.703, 547.787, 572.692, 586.055, 606.79, 621.96, 637.51, 653.45]
const area = [9314.2, 2888.2, 1900, 2400, 1970.7, 2589.7, 2589.7, 2589.7]
const d: ModelData = {
  model_version: 'v', filename: 'm.xlsx', uploaded_at: '', warnings: [], labels, cols: ['U', 'V', 'W', 'X', 'Y', 'Z', 'AA', 'AB'], sheet: 'Продажи',
  queues: { 1: { price, area, total: area.reduce((a, b) => a + b, 0), rows: { price: 12, area: 15 } } }, fr: 18575830371.56, llcr: 1.1991,
}
const start = initialStart(labels, new Date(2026, 8, 29))

describe('окно и якорь', () => {
  it('III кв. 26 при дате 29.09.2026', () => {
    expect(qLabel(labels[start])).toBe('III кв. 26')
    const c = sliderCtx(d, baseCur(d), '1', start)
    expect(c && !c.off && Math.round(c.price)).toBe(573)
    expect(c && !c.off && c.area).toBe(1900)
  })
  it('ряды графика: 573 / 586 / 607 / 622; 1.9 / 2.4 / 2.0 / 2.6', () => {
    const s = ourSeries(d, baseCur(d), '1')
    expect(s.price.slice(start, start + 4).map(v => Math.round(v!))).toEqual([573, 586, 607, 622])
    expect(s.pace.slice(start, start + 4).map(v => v!.toFixed(1))).toEqual(['1.9', '2.4', '2.0', '2.6'])
  })
})

describe('ползунки', () => {
  it('цена +3 шага → 603, кривая с III кв. 26 выросла на 5,3%', () => {
    let cur = baseCur(d)
    for (let k = 0; k < 3; k++) cur = applyPrice(d, cur, '1', start, Math.round(cur['1'].price[start]) + 10)
    expect(Math.round(cur['1'].price[start])).toBe(603)
    for (let t = start; t < labels.length; t++) expect(cur['1'].price[t] / price[t]).toBeCloseTo(603 / 572.692, 6)
    for (let t = 0; t < start; t++) expect(cur['1'].price[t]).toBe(price[t])
  })
  it('темп +5 шагов → 2 400 м², итог очереди не меняется', () => {
    let cur = baseCur(d)
    for (let k = 0; k < 5; k++) cur = applyArea(d, cur, '1', start, Math.round(cur['1'].area[start] / 100) * 100 + 100)
    expect(cur['1'].area[start]).toBe(2400)
    expect(cur['1'].area.reduce((a, b) => a + b, 0)).toBeCloseTo(d.queues[1].total, 6)
    expect(cur['1'].area.slice(0, start)).toEqual(area.slice(0, start))
  })
  it('цена ограничена ±30%', () => {
    const cur = applyPrice(d, baseCur(d), '1', start, 10_000)
    expect(cur['1'].price[start]).toBeCloseTo(750, 9)
  })
})
