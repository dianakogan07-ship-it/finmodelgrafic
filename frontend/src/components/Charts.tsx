import { useState } from 'react'
import { qLabel } from '../lib/model'

export interface Bar { name: string; color: string; v: number; ours?: boolean; base?: number | null }
type Key = 'price' | 'pace'

const W = 1360, GW = W / 4

/** Сегментированные столбцы по 4 кварталам окна, единая шкала Y от нуля. */
export function QuarterChart({ kind, height, quarters, bars, fmt }: {
  kind: Key; height: number; quarters: string[]; bars: Bar[][]; fmt: (v: number) => string
}) {
  const [tip, setTip] = useState<{ x: number; y: number; b: Bar } | null>(null)
  let max = 0
  bars.forEach(bs => bs.forEach(b => { max = Math.max(max, b.v, b.base ?? 0) }))
  const top = 60, bottom = height - 34, hMax = bottom - top - 10
  const y = (v: number) => bottom - (max > 0 ? (v / max) * hMax : 0)

  return (
    <>
      <svg viewBox={`0 0 ${W} ${height}`} role="img" aria-label={`${kind === 'price' ? 'Цена 1 м²' : 'Темп продаж'} по кварталам`} data-chart={kind}>
        {quarters.map((ql, g) => {
          const x0 = g * GW, bs = bars[g]
          const head = <text x={x0 + GW / 2} y={24} fill="#dfe3e8" fontSize={15} textAnchor="middle">{qLabel(ql)}</text>
          if (!bs.length) return <g key={g}>{head}<text x={x0 + GW / 2} y={bottom - 20} fill="#6c737d" fontSize={13} textAnchor="middle">нет данных</text></g>
          const slot = Math.min(35, (GW - 60) / bs.length), bw = Math.max(8, slot * 0.62)
          const startX = x0 + (GW - slot * bs.length) / 2
          const labelIdx = new Set([0, bs.length - 1, bs.findIndex(b => b.ours)].filter(k => k >= 0))
          return (
            <g key={g} data-quarter={qLabel(ql)}>
              {head}
              {bs.map((b, k) => {
                const bx = startX + k * slot + (slot - bw) / 2, hgt = bottom - y(b.v), seg = 22, gap = 3
                const segs = []
                for (let h = 0; h < hgt - 0.5; h += seg + gap) {
                  const sh = Math.min(seg, hgt - h)
                  segs.push(<rect key={h} x={bx} y={bottom - h - sh} width={bw} height={sh} fill={b.ours ? 'var(--ours)' : b.color} />)
                }
                const changed = b.ours && b.base != null && Math.abs(b.base - b.v) > 1e-6
                return (
                  <g key={b.name} className="bar" data-name={b.name} data-value={fmt(b.v)}
                    onMouseMove={e => setTip({ x: e.clientX, y: e.clientY, b })} onMouseLeave={() => setTip(null)}>
                    <rect x={bx - 2} y={top - 40} width={bw + 4} height={bottom - top + 40} fill="transparent" />
                    {segs}
                    {changed && <line className="base-mark" x1={bx - 5} x2={bx + bw + 5} y1={y(b.base!)} y2={y(b.base!)} stroke="#ececec" strokeWidth={2} strokeDasharray="4 3" />}
                    {labelIdx.has(k) && (
                      <text x={bx + bw / 2} y={bottom + 20} fill={b.ours ? '#fff' : '#c9ced5'} fontSize={14} fontWeight={b.ours ? 700 : 500} textAnchor="middle"
                        className={b.ours ? 'ours-label' : undefined}>{fmt(b.v)}</text>
                    )}
                  </g>
                )
              })}
            </g>
          )
        })}
      </svg>
      {tip && (
        <div id="tip" style={{ left: Math.min(tip.x + 14, window.innerWidth - 220), top: tip.y + 14 }}>
          <b>{tip.b.name}</b><br />{fmt(tip.b.v)}
          {tip.b.ours && tip.b.base != null && Math.abs(tip.b.base - tip.b.v) > 1e-6 && <span className="muted"> (в модели {fmt(tip.b.base)})</span>}
        </div>
      )}
    </>
  )
}
