// Логика ползунков и рядов графика. Чистые функции — покрыты тестами (model.test.ts).

export interface QueueData { price: number[]; area: number[]; total: number; rows: { price: number; area: number } }
export interface ModelData {
  model_version: string
  filename: string
  uploaded_at: string
  warnings: string[]
  labels: string[]
  cols: string[]
  sheet: string
  queues: Record<string, QueueData>
  fr: number
  llcr: number
}
export type Cur = Record<string, { price: number[]; area: number[] }>
export type Series = { price: (number | null)[]; pace: (number | null)[] }

export const P_STEP = 10
export const V_STEP = 100
const ROMAN: Record<string, string> = { 1: 'I', 2: 'II', 3: 'III', 4: 'IV' }

export const qLabel = (s: string) => {
  const m = String(s).match(/(\d)\s*кв\.?\s*(\d{2,4})/i)
  return m ? `${ROMAN[m[1]]} кв. ${m[2].slice(-2)}` : String(s)
}
export const normQ = (s: string) => String(s).replace(/\s+/g, '').toLowerCase()
export const fmtArea = (v: number) => Math.round(v).toLocaleString('ru-RU').replace(/\s/g, ' ')
export const fmtPace = (v: number) => (v < 0.1 ? v.toFixed(2) : v.toFixed(1))

export const baseCur = (d: ModelData): Cur =>
  Object.fromEntries(Object.entries(d.queues).map(([q, v]) => [q, { price: [...v.price], area: [...v.area] }]))

/** Окно начинается с текущего календарного квартала (если он есть в модели). */
export function initialStart(labels: string[], now = new Date()): number {
  const cq = Math.floor(now.getMonth() / 3) + 1
  const cy = String(now.getFullYear()).slice(-2)
  const idx = labels.findIndex(l => new RegExp(`^\\s*${cq}\\s*кв\\.?\\s*${cy}`).test(l))
  return Math.max(0, Math.min(idx < 0 ? 0 : idx, labels.length - 4))
}

/** Ряды нашего проекта: цена тыс.руб./м², темп тыс.м² (для графика). */
export function ourSeries(d: ModelData, cur: Cur, q: string): Series {
  if (q !== 'all') {
    const s = cur[q]
    return { price: s.price.map(v => (v > 0 ? v : null)), pace: s.area.map(v => (v > 0 ? v / 1000 : null)) }
  }
  const price: (number | null)[] = [], pace: (number | null)[] = []
  for (let i = 0; i < d.labels.length; i++) {
    let a = 0, pa = 0
    const ps: number[] = []
    for (const k of Object.keys(cur)) {
      const s = cur[k]
      if (s.area[i] > 0) { a += s.area[i]; pa += s.area[i] * s.price[i] }
      if (s.price[i] > 0) ps.push(s.price[i])
    }
    price.push(a > 0 ? pa / a : ps.length ? ps.reduce((x, y) => x + y, 0) / ps.length : null)
    pace.push(a > 0 ? a / 1000 : null)
  }
  return { price, pace }
}

export type SliderCtx =
  | { off: true; i: number }
  | { off: false; i: number; pMin: number; pMax: number; vMin: number; vMax: number; price: number; area: number }

/** Якорный квартал — первый видимый квартал окна, где очередь в продаже. */
export function sliderCtx(d: ModelData, cur: Cur, q: string, start: number): SliderCtx | null {
  if (q === 'all') return null
  const base = d.queues[q], c = cur[q]
  let i = start
  for (let k = 0; k < 4; k++) {
    const j = start + k
    if (base.price[j] > 0 && base.area[j] > 0) { i = j; break }
  }
  if (!(base.price[i] > 0)) return { off: true, i }
  const sold = c.area.slice(0, i).reduce((x, y) => x + y, 0)
  const pMin = Math.floor((base.price[i] * 0.7) / 10) * 10
  const pMax = Math.ceil((base.price[i] * 1.3) / 10) * 10
  const vMax = Math.max(0, Math.floor((base.total - sold) / 100) * 100)
  return { off: false, i, pMin, pMax, vMin: 0, vMax: Math.min(vMax, Math.max(5000, Math.ceil((base.area[i] * 2.5) / 100) * 100)), price: c.price[i], area: c.area[i] }
}

const clone = (cur: Cur): Cur => Object.fromEntries(Object.entries(cur).map(([q, v]) => [q, { price: [...v.price], area: [...v.area] }]))

/** Цена в якорном квартале = v; последующие кварталы очереди умножаются на тот же коэффициент. */
export function applyPrice(d: ModelData, cur: Cur, q: string, start: number, v: number): Cur {
  const c = sliderCtx(d, cur, q, start)
  if (!c || c.off) return cur
  v = Math.max(c.pMin, Math.min(c.pMax, v))
  const next = clone(cur), s = next[q], ratio = v / s.price[c.i]
  for (let t = c.i; t < s.price.length; t++) if (s.price[t] > 0) s.price[t] *= ratio
  return next
}

/** Продажи в якорном квартале = v; хвост масштабируется, итог площади очереди не меняется. */
export function applyArea(d: ModelData, cur: Cur, q: string, start: number, v: number): Cur {
  const c = sliderCtx(d, cur, q, start)
  if (!c || c.off) return cur
  const base = d.queues[q], next = clone(cur), s = next[q], n = s.area.length
  const before = s.area.slice(0, c.i).reduce((x, y) => x + y, 0)
  const rest = base.total - before
  v = Math.max(0, Math.min(v, rest))
  if (c.i + 1 >= n) v = rest // последний квартал — остаток некуда перенести
  const tailSum = s.area.slice(c.i + 1).reduce((x, y) => x + y, 0)
  const need = rest - v
  s.area[c.i] = v
  if (tailSum > 0) {
    const k = need / tailSum
    for (let t = c.i + 1; t < n; t++) s.area[t] *= k
  } else if (need > 0) {
    s.area[c.i + 1] = need
    if (!(s.price[c.i + 1] > 0)) s.price[c.i + 1] = s.price[c.i] * 1.02
  }
  return next
}

export function isChanged(d: ModelData, cur: Cur): boolean {
  return Object.entries(d.queues).some(([q, b]) =>
    b.price.some((v, i) => Math.abs(v - cur[q].price[i]) > 1e-9) || b.area.some((v, i) => Math.abs(v - cur[q].area[i]) > 1e-9))
}

/** Сохранённый сценарий подходит, только если совпадает форма рядов модели. */
export function curFits(d: ModelData, cur: unknown): cur is Cur {
  if (!cur || typeof cur !== 'object') return false
  const c = cur as Cur
  return Object.entries(d.queues).every(([q, b]) =>
    c[q] && Array.isArray(c[q].price) && Array.isArray(c[q].area) && c[q].price.length === b.price.length && c[q].area.length === b.area.length)
}
