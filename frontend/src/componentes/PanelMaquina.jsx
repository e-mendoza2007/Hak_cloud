import { usePolling } from '../hooks.js'
import Sparkline from './Sparkline.jsx'
import Insignia from './Insignia.jsx'
import { ESTADO_MAQUINA, ESTADO_INCIDENTE, VARIABLES, comp, hora, fecha, num } from '../formato.js'

const GRAFICAS = ['temperatura', 'vibracion', 'combustible_lh', 'presion']
const PREVENTIVO = { vencido: 'Vencido', proximo: 'Próximo', ok: 'Al día' }

export default function PanelMaquina({ id, onVolver, onIncidente }) {
  const { datos, error } = usePolling(`/maquinas/${id}`, 20000)
  const tele = usePolling(`/maquinas/${id}/telemetria`, 20000)
  if (error) return <section className="panel"><button className="boton-texto" onClick={onVolver}>Volver</button><p className="aviso-error">{error}</p></section>
  if (!datos) return <section className="panel"><p className="vacio">Cargando máquina…</p></section>

  const m = datos.maquina
  const p = m.preventivo || {}
  const lecturas = (tele.datos?.lecturas || []).filter((l) => l.estado === 'operativa')

  return (
    <section className="panel detalle" aria-labelledby="titulo-maquina">
      <button className="boton-texto" onClick={onVolver}>Volver a la cola</button>
      <div className="cabecera-detalle">
        <h2 id="titulo-maquina"><span className="id-maquina">{m.maquina_id}</span></h2>
        <span className={`estado-maquina est-${m.estado}`}>{ESTADO_MAQUINA[m.estado] || m.estado}</span>
      </div>
      <p className="subtitulo">{m.modelo} en zona {m.zona}. {num(m.horas_totales, 0)} h de uso, {num(m.horas_desde_mant, 0)} h desde el último mantenimiento.</p>
      {m.degradacion && <p className="aviso-grupo">Simulación activa: falla de {m.degradacion.tipo}.</p>}

      <h3>Últimos 30 minutos en operación</h3>
      <div className="sparks">
        {GRAFICAS.map((v) => (
          <Sparkline key={v} titulo={VARIABLES[v].nombre} unidad={VARIABLES[v].unidad}
                     puntos={lecturas.filter((l) => l[v] !== undefined).map((l) => ({ ts: l.ts, v: Number(l[v]) }))} />
        ))}
      </div>

      <h3>Mantenimiento preventivo</h3>
      {p.estado ? (
        <p>{PREVENTIVO[p.estado] || p.estado}: fecha sugerida {p.fecha_sugerida} ({num(p.horas_restantes, 0)} h restantes).
          {p.factor_uso_severo > 0 && ` El uso severo acorta el intervalo un ${Math.round(p.factor_uso_severo * 30)} %.`}</p>
      ) : <p className="vacio">Se calcula en el preventivo diario.</p>}

      <h3>Incidentes</h3>
      {datos.incidentes.length === 0 ? <p className="vacio">Sin incidentes registrados.</p> : (
        <ul className="lista-simple">
          {datos.incidentes.map((i) => (
            <li key={i.incidente_id}>
              <button className="boton-texto" onClick={() => onIncidente(i.incidente_id)}>{hora(i.creado_ts)}</button>
              <Insignia severidad={i.severidad} /> {comp(i.componente_probable)}, {ESTADO_INCIDENTE[i.estado] || i.estado}
            </li>
          ))}
        </ul>
      )}

      <h3>Historial de intervenciones</h3>
      {datos.historial.length === 0 ? <p className="vacio">Sin intervenciones.</p> : (
        <div className="tabla-scroll"><table className="tabla">
          <thead><tr><th>Fecha</th><th>Intervención</th><th className="num">Detenida</th><th>Recurrente</th></tr></thead>
          <tbody>
            {datos.historial.map((h) => (
              <tr key={h.ts}>
                <td>{fecha(h.ts)}</td>
                <td>{h.tipo}<br /><small>{(h.componentes || []).map(comp).join(', ')}</small></td>
                <td className="num">{num(h.tiempo_detenida_min, 0)} min</td>
                <td>{h.recurrencia ? <span className="etiqueta-alerta">Sí</span> : 'No'}</td>
              </tr>
            ))}
          </tbody>
        </table></div>
      )}
    </section>
  )
}
