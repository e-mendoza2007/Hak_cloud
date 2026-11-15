import Insignia from './Insignia.jsx'
import { ESTADO_INCIDENTE, comp, haceCuanto } from '../formato.js'

// Cola priorizada: el orden lo decide la API (severidad, luego score, luego antigüedad)
export default function ColaIncidentes({ incidentes, cargando, onSeleccionar }) {
  return (
    <section className="panel" aria-labelledby="titulo-cola">
      <h2 id="titulo-cola">Qué atender primero</h2>
      {cargando && <p className="vacio">Cargando incidentes…</p>}
      {!cargando && incidentes.length === 0 && (
        <p className="vacio">No hay incidentes abiertos. Usa «Simular falla» para ver el flujo completo.</p>
      )}
      <ol className="cola">
        {incidentes.map((i) => (
          <li key={i.incidente_id}>
            <button className={`tarjeta-incidente borde-${i.severidad}`} onClick={() => onSeleccionar(i.incidente_id)}>
              <span className="fila-sup">
                <span className="id-maquina">{i.maquina_id}</span>
                <Insignia severidad={i.severidad} />
              </span>
              <span className="fila-media">
                {comp(i.componente_probable)} en zona {i.zona}
                {i.grupo_id && <span className="etiqueta-grupo">Causa común</span>}
              </span>
              <span className="fila-inf">
                <span>{ESTADO_INCIDENTE[i.estado] || i.estado}{i.tecnico_id ? `: ${i.tecnico_id}` : ''}</span>
                <span>{haceCuanto(i.creado_ts)}</span>
              </span>
            </button>
          </li>
        ))}
      </ol>
    </section>
  )
}
