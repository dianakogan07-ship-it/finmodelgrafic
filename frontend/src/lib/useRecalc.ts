import { useEffect, useRef, useState } from 'react'
import { api } from './api'
import { Cur, isChanged, ModelData } from './model'

export interface KPI { fr: number; llcr: number; pending: boolean; error: string | null; changed: boolean }

/** ФР и LLCR: база — из файла; после изменения ползунков — пересчёт моделью (debounce 400 мс, устаревшие запросы отменяются). */
export function useRecalc(projectId: number, data: ModelData | null, cur: Cur | null): KPI {
  const [kpi, setKpi] = useState<KPI>({ fr: NaN, llcr: NaN, pending: false, error: null, changed: false })
  const ctrl = useRef<AbortController>()

  useEffect(() => {
    if (!data || !cur) return
    ctrl.current?.abort()
    if (!isChanged(data, cur)) {
      setKpi({ fr: data.fr, llcr: data.llcr, pending: false, error: null, changed: false })
      return
    }
    setKpi(k => ({ ...k, pending: true, error: null, changed: true }))
    const c = new AbortController()
    ctrl.current = c
    const t = window.setTimeout(() => {
      api.recalc(projectId, data.model_version, cur, c.signal)
        .then(r => { if (!c.signal.aborted) setKpi({ fr: r.fr, llcr: r.llcr, pending: false, error: null, changed: true }) })
        .catch(e => { if (!c.signal.aborted) setKpi(k => ({ ...k, pending: false, error: e.message })) })
    }, 400)
    return () => { clearTimeout(t); c.abort() }
  }, [projectId, data, cur])

  return kpi
}
