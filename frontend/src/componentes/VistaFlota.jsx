import { usePolling } from '../hooks.js'
import { num, pct } from '../formato.js'

const CLASES = {
  baja_utilizacion: 'Baja utilización',
  uso_excesivo: 'Uso excesivo',
  baja_productividad_alto_costo: 'Baja productividad y costo alto',
}

export default function VistaFlota({ onMaquina }) {
  // Una sola llamada (productividad + combustible) del último día completo ya calculado
  const flota = usePolling('/flota', 60000)
  const p = flota.datos
  const error = flota.error
  const combPorId = Object.fromEntries((p?.maquinas || []).map((m) => [m.maquina_id, m]))

  return (
    <main className="vista">
      <section className="panel ancho">
        <h2>Productividad y combustible{p?.fecha ? ` del ${p.fecha}` : ''}</h2>
        {p?.fecha && <p className="subtitulo">Último día completo procesado por el preventivo diario (24 h de operación).</p>}
        {error && <p className="aviso-error">{error}</p>}
        {p && !p.calculado && (
          <p className="vacio">Todavía no hay métricas calculadas para hoy. Ejecuta la máquina de estados
            PreventivoDiario (consola de Step Functions o README) y vuelve a esta vista.</p>
        )}
        {p?.resumen && Object.keys(p.resumen).length > 0 && (
          <dl className="resumen-clases">
            {Object.entries(p.resumen).map(([k, ids]) => (
              <div key={k}><dt>{CLASES[k] || k}</dt><dd>{ids.length}</dd></div>
            ))}
          </dl>
        )}
        {p?.calculado && (
          <div className="tabla-scroll">
            <table className="tabla">
              <thead>
                <tr><th>Máquina</th><th>Modelo</th><th className="num">Utilización</th><th className="num">Horas</th>
                  <th className="num">Costo por t·h</th><th className="num">Litros por t·h</th>
                  <th className="num">Frente a pares</th><th className="num">Tendencia diaria</th><th>Observación</th></tr>
              </thead>
              <tbody>
                {p.maquinas.map((m) => {
                  const k = combPorId[m.maquina_id] || {}
                  const obs = [...(m.clasificacion || []).map((x) => CLASES[x] || x), k.alerta_combustible ? 'Consumo fuera de lo esperado' : null].filter(Boolean)
                  return (
                    <tr key={m.maquina_id}>
                      <td><button className="boton-texto" onClick={() => onMaquina(m.maquina_id)}>{m.maquina_id}</button></td>
                      <td>{m.modelo}</td>
                      <td className="num"><span className="barra-util" style={{ '--v': Math.min(1, m.utilizacion || 0) }} aria-hidden="true" />{pct(m.utilizacion)}</td>
                      <td className="num">{num(m.horas_op, 1)}</td>
                      <td className="num">{num(m.costo_por_th, 2)}</td>
                      <td className="num">{num(k.litros_por_th, 2)}</td>
                      <td className="num">{k.desv_combustible_pct === undefined || k.desv_combustible_pct === null ? '—' : `${k.desv_combustible_pct > 0 ? '+' : ''}${num(k.desv_combustible_pct, 0)} %`}</td>
                      <td className="num">{k.tend_combustible_pct_dia == null ? '—' : `${num(k.tend_combustible_pct_dia, 1)} %`}</td>
                      <td>{obs.length ? obs.map((o) => <span key={o} className="etiqueta-alerta">{o}</span>) : 'Normal'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
      {p?.plan && (
        <section className="panel ancho">
          <h2>Plan preventivo</h2>
          <p>{p.plan.mantener?.length || 0} máquinas necesitan mantenimiento y se posponen {p.plan.posponer} que todavía no lo requieren.</p>
          <ol className="lista-simple">
            {(p.plan.mantener || []).map((m) => (
              <li key={m.maquina_id}>
                <button className="boton-texto" onClick={() => onMaquina(m.maquina_id)}>{m.maquina_id}</button>
                {' '}{m.estado === 'vencido' ? 'Vencido' : 'Próximo'}, fecha sugerida {m.fecha_sugerida}
              </li>
            ))}
          </ol>
        </section>
      )}
    </main>
  )
}
