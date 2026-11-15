import { usePolling } from '../hooks.js'
import { comp } from '../formato.js'

const ESTADO_TEC = { disponible: 'Disponible', ocupado: 'Ocupado' }

export default function VistaRecursos({ tecnicos, onIncidente }) {
  const rep = usePolling('/repuestos/estado', 20000)
  const lista = tecnicos.datos?.tecnicos || []
  const almacenes = rep.datos?.almacenes || {}
  const maxStock = Math.max(3, ...Object.values(almacenes).flat().map((r) => r.stock || 0))

  return (
    <main className="vista dos-columnas">
      <section className="panel">
        <h2>Técnicos</h2>
        <p className="subtitulo">{tecnicos.datos ? `${tecnicos.datos.disponibles} de ${lista.length} disponibles` : 'Cargando…'}</p>
        <table className="tabla">
          <thead><tr><th>Técnico</th><th>Especialidades</th><th>Estado</th><th className="num">Atendidos</th></tr></thead>
          <tbody>
            {lista.map((t) => (
              <tr key={t.tecnico_id}>
                <td>{t.nombre || t.tecnico_id}<br /><small>{t.tecnico_id}, base {t.zona_base}</small></td>
                <td>{(t.especialidades || []).map(comp).join(', ')}</td>
                <td>
                  <span className={`estado-tec tec-${t.estado}`}>{ESTADO_TEC[t.estado] || t.estado}</span>
                  {t.incidente_actual && <><br /><button className="boton-texto" onClick={() => onIncidente(t.incidente_actual)}>Ver incidente</button></>}
                </td>
                <td className="num">{t.carga || 0}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="panel">
        <h2>Repuestos por almacén</h2>
        {rep.error && <p className="aviso-error">{rep.error}</p>}
        {(rep.datos?.demanda || []).length > 0 && (
          <div className="aviso-grupo">
            <p>Demanda proyectada mayor que el stock:</p>
            <ul>{rep.datos.demanda.map((a) => (
              <li key={a.zona + a.componente}>Zona {a.zona}: faltan {a.faltan} de {comp(a.componente)} ({a.demanda} máquinas en riesgo, stock {a.stock})</li>
            ))}</ul>
          </div>
        )}
        {(rep.datos?.consumo_irregular || []).length > 0 && (
          <p className="aviso-grupo">Consumo irregular: {rep.datos.consumo_irregular.map((x) => `${comp(x.componente)} en ${x.ubicacion}`).join('; ')}.</p>
        )}
        {Object.entries(almacenes).sort().map(([alm, items]) => (
          <div key={alm} className="almacen">
            <h3>{alm}</h3>
            <ul className="stock">
              {items.sort((a, b) => a.componente.localeCompare(b.componente)).map((r) => (
                <li key={r.componente} className={r.bajo_minimo ? 'bajo' : ''}>
                  <span className="stock-nombre">{comp(r.componente)}</span>
                  <span className="stock-barra" aria-hidden="true">
                    <span className="stock-relleno" style={{ width: `${(r.stock / maxStock) * 100}%` }} />
                    <span className="stock-minimo" style={{ left: `${(r.minimo / maxStock) * 100}%` }} />
                  </span>
                  <span className="stock-valor">{r.stock}{r.bajo_minimo ? ', bajo el mínimo' : ''}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
        <p className="nota">La línea vertical marca el stock mínimo de cada repuesto.</p>
      </section>
    </main>
  )
}
