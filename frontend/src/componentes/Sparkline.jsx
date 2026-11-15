import { useState } from 'react'
import { hora } from '../formato.js'

const W = 320, H = 72, PAD = 4

// Mini gráfica de una sola variable: línea de 2px, mínimo y máximo visibles, cruz y valor al pasar el cursor.
export default function Sparkline({ titulo, unidad, puntos }) {
  const [hover, setHover] = useState(null)
  if (!puntos.length) return <figure className="spark"><figcaption>{titulo}</figcaption><p className="vacio">Sin lecturas recientes</p></figure>
  const xs = puntos.map((p) => p.ts), ys = puntos.map((p) => p.v)
  const x0 = Math.min(...xs), x1 = Math.max(...xs)
  let y0 = Math.min(...ys), y1 = Math.max(...ys)
  if (y1 - y0 < 1e-9) { y0 -= 1; y1 += 1 }
  const px = (t) => PAD + ((t - x0) / Math.max(1, x1 - x0)) * (W - 2 * PAD)
  const py = (v) => H - PAD - ((v - y0) / (y1 - y0)) * (H - 2 * PAD)
  const d = puntos.map((p, k) => `${k ? 'L' : 'M'}${px(p.ts).toFixed(1)},${py(p.v).toFixed(1)}`).join(' ')
  const ultimo = puntos[puntos.length - 1]
  const activo = hover ?? ultimo

  const mover = (e) => {
    const r = e.currentTarget.getBoundingClientRect()
    const t = x0 + ((e.clientX - r.left) / r.width) * (x1 - x0)
    setHover(puntos.reduce((a, b) => (Math.abs(b.ts - t) < Math.abs(a.ts - t) ? b : a)))
  }

  return (
    <figure className="spark">
      <figcaption>
        <span>{titulo}</span>
        <span className="valor">{activo.v.toFixed(1)} {unidad}</span>
        <small className="spark-hora">{hora(activo.ts)}</small>
      </figcaption>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" role="img"
           aria-label={`${titulo}: de ${y0.toFixed(1)} a ${y1.toFixed(1)} ${unidad}, último ${ultimo.v.toFixed(1)}`}
           onMouseMove={mover} onMouseLeave={() => setHover(null)}>
        <line x1={PAD} x2={W - PAD} y1={py(y0)} y2={py(y0)} className="spark-base" />
        <path d={d} className="spark-linea" vectorEffect="non-scaling-stroke" />
        {hover && <line x1={px(hover.ts)} x2={px(hover.ts)} y1={0} y2={H} className="spark-cruz" vectorEffect="non-scaling-stroke" />}
        <circle cx={px(activo.ts)} cy={py(activo.v)} r="4" className="spark-punto" />
      </svg>
      <div className="spark-rango"><span>mín {y0.toFixed(1)}</span><span>máx {y1.toFixed(1)}</span></div>
    </figure>
  )
}
