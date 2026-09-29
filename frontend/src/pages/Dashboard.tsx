import { ChangeEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { QuarterChart, Bar } from '../components/Charts'
import { api, Competitor, Project, ScenarioState } from '../lib/api'
import { useAuth } from '../lib/auth'
import {
  applyArea, applyPrice, baseCur, Cur, curFits, fmtArea, fmtPace, initialStart, ModelData, normQ, ourSeries,
  P_STEP, qLabel, sliderCtx, V_STEP,
} from '../lib/model'
import { useToast } from '../lib/toast'
import { useRecalc } from '../lib/useRecalc'

type Comp = Competitor & { price: (number | null)[]; pace: (number | null)[] }

export default function Dashboard() {
  const id = Number(useParams().id)
  const nav = useNavigate()
  const toast = useToast()
  const { user } = useAuth()
  const [project, setProject] = useState<Project | null>(null)
  const [data, setData] = useState<ModelData | null>(null)
  const [comps, setComps] = useState<Competitor[]>([])
  const [chips, setChips] = useState<Record<string, boolean>>({})
  const [cur, setCur] = useState<Cur | null>(null)
  const [q, setQ] = useState('1')
  const [start, setStart] = useState(0)
  const [tab, setTab] = useState<'market' | 'comp'>('comp')
  const [error, setError] = useState('')
  const [uploading, setUploading] = useState(false)
  const loaded = useRef(false)
  const fileRef = useRef<HTMLInputElement>(null)

  const load = useCallback(async () => {
    loaded.current = false
    try {
      const [p, m, c, s] = await Promise.all([api.project(id), api.model(id), api.competitors(id), api.scenario(id).catch((): ScenarioState => ({}))])
      setProject(p); setData(m); setComps(c)
      setChips(Object.fromEntries(c.map(x => [x.id, s.chips?.[x.id] ?? x.enabled_default])))
      setCur(s.model_version === m.model_version && curFits(m, s.cur) ? s.cur : baseCur(m))
      const qs = Object.keys(m.queues).sort()
      setQ(s.q && (s.q === 'all' || qs.includes(s.q)) ? s.q : qs[0])
      setStart(initialStart(m.labels))
      loaded.current = true
    } catch (e) { setError((e as Error).message) }
  }, [id])
  useEffect(() => { load() }, [load])

  // сценарий пользователя: чипы, очередь, ползунки
  useEffect(() => {
    if (!loaded.current || !data || !cur) return
    const t = window.setTimeout(() => {
      api.saveScenario(id, { chips, q, cur, model_version: data.model_version }).catch(() => {})
    }, 800)
    return () => clearTimeout(t)
  }, [id, chips, q, cur, data])

  const kpi = useRecalc(id, data, cur)

  const compSeries: Comp[] = useMemo(() => {
    if (!data) return []
    const idx = new Map(data.labels.map((l, i) => [normQ(l), i]))
    return comps.map(c => {
      const price = data.labels.map(() => null as number | null), pace = [...price]
      c.series.forEach(s => { const i = idx.get(normQ(s.quarter)); if (i != null) { price[i] = s.price; pace[i] = s.pace } })
      return { ...c, price, pace }
    })
  }, [comps, data])

  if (error) return <div className="empty screen">{error}<br /><button className="btn ghost" onClick={() => nav('/')}>‹ Назад</button></div>
  if (!data || !cur || !project) return <div className="empty screen">Загрузка…</div>

  const n = data.labels.length
  const ctx = sliderCtx(data, cur, q, start)
  const anchor = ctx && !ctx.off ? ctx.i : start
  const lbl = qLabel(data.labels[anchor])
  const disabled = !ctx || ctx.off
  const qd = q !== 'all' ? data.queues[q] : null
  const cell = (row: number | undefined) => (qd && ctx && !ctx.off && row ? ` · ${data.sheet}!${data.cols[anchor]}${row}` : '')

  const setPrice = (v: number) => setCur(c => applyPrice(data, c!, q, start, v))
  const setArea = (v: number) => setCur(c => applyArea(data, c!, q, start, v))
  const reset = () => { setCur(baseCur(data)); toast('Значения модели восстановлены') }

  let pVal = '—', vVal = '—', pSub = '', vSub = ''
  if (!ctx) {
    const s = ourSeries(data, cur, 'all')
    pVal = s.price[start] ? String(Math.round(s.price[start]!)) : '—'
    vVal = s.pace[start] ? fmtArea(s.pace[start]! * 1000) : '—'
    pSub = `${lbl} · средневзв. по очередям`; vSub = 'Меняется в разрезе очереди'
  } else if (ctx.off) {
    pSub = `${lbl} · очередь ${q} не в продаже`
  } else {
    pVal = String(Math.round(ctx.price)); vVal = fmtArea(ctx.area)
    pSub = lbl + cell(qd?.rows.price); vSub = lbl + cell(qd?.rows.area)
  }

  const ours = ourSeries(data, cur, q), oursBase = ourSeries(data, baseCur(data), q)
  const window4 = [0, 1, 2, 3].map(k => start + k).filter(i => i < n)
  const barsFor = (key: 'price' | 'pace') => window4.map(i => {
    const arr: Bar[] = compSeries.filter(c => chips[c.id] && c[key][i] != null).map(c => ({ name: c.name, color: c.color, v: c[key][i]! }))
    const v = ours[key][i]
    if (v != null) arr.push({ name: project.name, color: 'var(--ours)', v, ours: true, base: oursBase[key][i] })
    return arr.sort((a, b) => a.v - b.v)
  })

  const onFile = async (e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    e.target.value = ''
    if (!f) return
    setUploading(true)
    try {
      const r = await api.uploadModel(id, f)
      toast(r.warnings.length ? 'Модель загружена с предупреждениями' : 'Модель загружена')
      await load()
    } catch (err) { toast((err as Error).message) } finally { setUploading(false) }
  }

  const delta = (v: number, base: number, dig: number) => {
    if (!kpi.changed || !isFinite(v)) return <span className="d">значение модели</span>
    const d = v - base
    if (Math.abs(d) < Math.pow(10, -dig - 1) / 2) return <span className="d">как в модели</span>
    // мелкое изменение показываем на знак точнее, чтобы не было «−0.00»
    const shown = Math.abs(d) < Math.pow(10, -dig) / 2 ? dig + 1 : dig
    return <span className={'d' + (d > 0 ? ' up' : ' down')}>{d > 0 ? '+' : '−'}{Math.abs(d).toFixed(shown)} к модели</span>
  }
  const frB = kpi.fr / 1e9, frBase = data.fr / 1e9

  return (
    <section id="dash" className="screen">
      <aside className="side">
        <button className="back" onClick={() => nav('/')}>‹ &nbsp;Назад</button>
        <div className="card">
          <div className="ctrl">
            <div className="ctrl-head"><div><b>Цена 1 м²</b><small>тыс.руб.</small></div>
              <button className="reset" onClick={reset} title="Сбросить к значениям модели" aria-label="Сбросить">↻</button></div>
            <div className="ctrl-val tnum" data-testid="price-val">{pVal}</div>
            <div className="ctrl-row">
              <button className="pm" disabled={disabled} aria-label="Цена −10" onClick={() => ctx && !ctx.off && setPrice(Math.round(ctx.price) - P_STEP)}>−</button>
              <Range disabled={disabled} min={ctx && !ctx.off ? ctx.pMin : 0} max={ctx && !ctx.off ? ctx.pMax : 1} step={P_STEP}
                value={ctx && !ctx.off ? Math.round(ctx.price / 10) * 10 : 0} onChange={setPrice} label="Цена 1 м²" />
              <button className="pm" disabled={disabled} aria-label="Цена +10" onClick={() => ctx && !ctx.off && setPrice(Math.round(ctx.price) + P_STEP)}>+</button>
            </div>
            <div className="ctrl-sub tnum">{pSub}</div>
          </div>
          <div className="ctrl">
            <div className="ctrl-head"><div><b>Темп продаж</b><small>м²/кв.</small></div></div>
            <div className="ctrl-val tnum" data-testid="pace-val">{vVal}</div>
            <div className="ctrl-row">
              <button className="pm" disabled={disabled} aria-label="Темп −100" onClick={() => ctx && !ctx.off && setArea(Math.round(ctx.area / 100) * 100 - V_STEP)}>−</button>
              <Range disabled={disabled} min={ctx && !ctx.off ? ctx.vMin : 0} max={ctx && !ctx.off ? ctx.vMax : 1} step={V_STEP}
                value={ctx && !ctx.off ? Math.round(ctx.area / 100) * 100 : 0} onChange={setArea} label="Темп продаж" />
              <button className="pm" disabled={disabled} aria-label="Темп +100" onClick={() => ctx && !ctx.off && setArea(Math.round(ctx.area / 100) * 100 + V_STEP)}>+</button>
            </div>
            <div className="ctrl-sub tnum">{vSub}</div>
          </div>
        </div>

        <div className="card kpi"><div className="l">Финансовый<br />результат<small>млрд. руб.</small></div>
          <div className="v tnum"><span data-testid="fr">{isFinite(frB) ? frB.toFixed(1) : '—'}</span>{delta(frB, frBase, 1)}</div></div>
        <div className="card kpi"><div className="l">LLCR</div>
          <div className="v tnum"><span data-testid="llcr">{isFinite(kpi.llcr) ? kpi.llcr.toFixed(2) : '—'}</span>{delta(kpi.llcr, data.llcr, 2)}</div></div>
        <div className="calc-state" aria-live="polite" data-testid="calc-state">
          {kpi.pending ? 'пересчёт модели…' : kpi.error ? <span className="warn">{kpi.error}</span> : ''}
        </div>

        <div className="proj-h">Проекты</div>
        <div className="chips">
          <span className="chip ours" style={{ ['--c' as string]: '#f4f5f7' }}>{project.name}</span>
          <div style={{ flexBasis: '100%' }} />
          {comps.map(c => (
            <button key={c.id} className={'chip' + (chips[c.id] ? '' : ' off')} style={{ ['--c' as string]: c.color }}
              aria-pressed={!!chips[c.id]} title={chips[c.id] ? 'Убрать с графиков' : 'Показать на графиках'}
              onClick={() => setChips(s => ({ ...s, [c.id]: !s[c.id] }))}>
              <span aria-hidden="true">{chips[c.id] ? '−' : '+'}</span>{c.name}
            </button>
          ))}
        </div>
        <div className="assist">
          <button className="btn ghost" onClick={() => toast('Вне первой итерации')}>Виртуальный помощник ⚇</button>
          <button onClick={() => toast('Вне первой итерации')} aria-label="Уведомления">🔔</button>
        </div>

        <div className="src">
          <strong>Источник данных</strong>
          <div>{data.filename} · загружена {new Date(data.uploaded_at).toLocaleString('ru-RU', { dateStyle: 'short', timeStyle: 'short' })}</div>
          {data.warnings.map(w => <div key={w} className="warn">{w}</div>)}
          {user?.is_admin && (
            <>
              <input ref={fileRef} type="file" accept=".xlsx,.xlsm" hidden onChange={onFile} />
              <button className="btn ghost" disabled={uploading} onClick={() => fileRef.current?.click()}>
                {uploading ? 'Проверка модели…' : 'Загрузить новую версию модели'}</button>
            </>
          )}
        </div>
      </aside>

      <main className="main">
        <div className="main-title">{project.title}</div>
        <div className="bar">
          <div className="seg">
            <button className={tab === 'market' ? 'on' : ''} onClick={() => setTab('market')}>Рынок</button>
            <button className={tab === 'comp' ? 'on' : ''} onClick={() => setTab('comp')}>Конкуренты</button>
          </div>
          <div className="queues">Очередь:
            {Object.keys(data.queues).sort().map(k => <button key={k} className={q === k ? 'on' : ''} onClick={() => setQ(k)}>{k}</button>)}
            <button className={q === 'all' ? 'on' : ''} onClick={() => setQ('all')}>Весь проект</button>
          </div>
        </div>
        <div className="charts">
          {tab === 'market' ? (
            <div className="empty">Вкладка «Рынок» — во второй итерации.</div>
          ) : (
            <div className="charts-inner">
              <div className="ylab">Цена 1 м², тыс.руб.</div>
              <div><QuarterChart kind="price" height={420} quarters={window4.map(i => data.labels[i])} bars={barsFor('price')} fmt={v => String(Math.round(v))} /></div>
              <div className="ylab">Темп продаж, тыс.м²</div>
              <div><QuarterChart kind="pace" height={360} quarters={window4.map(i => data.labels[i])} bars={barsFor('pace')} fmt={fmtPace} /></div>
            </div>
          )}
        </div>
        <div className="bnav">
          <div>
            <button disabled={start <= 0} onClick={() => setStart(0)} aria-label="В начало">|‹</button>
            <button disabled={start <= 0} onClick={() => setStart(s => Math.max(0, s - 1))}>‹ &nbsp;Предыдущий квартал</button>
          </div>
          <div>
            <button disabled={start >= n - 4} onClick={() => setStart(s => Math.min(n - 4, s + 1))}>Следующий квартал &nbsp;›</button>
            <button disabled={start >= n - 4} onClick={() => setStart(Math.max(0, n - 4))} aria-label="В конец">›|</button>
          </div>
        </div>
        {comps.length > 0 && <div className="proto-note">Данные конкурентов — демонстрационные, до выгрузки из раздела «Проекты конкурентов».</div>}
      </main>
    </section>
  )
}

function Range({ min, max, step, value, onChange, disabled, label }: {
  min: number; max: number; step: number; value: number; onChange: (v: number) => void; disabled: boolean; label: string
}) {
  const p = ((value - min) / (max - min || 1)) * 100
  return <input type="range" aria-label={label} min={min} max={max} step={step} value={value} disabled={disabled}
    style={{ ['--p' as string]: `${p}%` }} onChange={e => onChange(+e.target.value)} />
}
