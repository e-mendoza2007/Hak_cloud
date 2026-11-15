import { useState } from 'react'
import { usePolling } from '../hooks.js'
import { post } from '../api.js'
import Insignia from './Insignia.jsx'
import { ESTADO_INCIDENTE, ROLES, VARIABLES, COMPONENTES, comp, hora, num } from '../formato.js'

const EVENTOS = {
  detectado: 'Anomalía detectada',
  tecnico_asignado: 'Técnico asignado',
  sin_tecnico_disponible: 'Sin técnico disponible',
  repuesto_reservado: 'Repuesto reservado',
  repuesto_sin_stock: 'Repuesto sin stock',
  escalado: 'Escalado',
  en_atencion: 'Técnico en atención',
  resuelto: 'Resuelto',
}
const FUENTE_IA = { gemini: 'Gemini (Google)', plantilla: 'plantilla fija (IA no disponible)' }

export default function DetalleIncidente({ id, onVolver, onMaquina, onCambio }) {
  const { datos: inc, error, recargar } = usePolling(`/incidentes/${id}`, 5000)
  const [cerrando, setCerrando] = useState(false)
  const [componentes, setComponentes] = useState(null)
  const [intervencion, setIntervencion] = useState('Cambio de componente')
  const [accion, setAccion] = useState(null)

  if (error) return <section className="panel"><button className="boton-texto" onClick={onVolver}>Volver a la cola</button><p className="aviso-error">{error}</p></section>
  if (!inc) return <section className="panel"><p className="vacio">Cargando incidente…</p></section>

  const ia = inc.ia || {}
  const asig = inc.asignacion || {}
  const rep = inc.repuesto || {}
  const abierto = inc.estado !== 'resuelto'
  const compsSel = componentes ?? [inc.componente_probable].filter((c) => c && c !== 'ninguno')

  const ejecutar = async (ruta, cuerpo, ok) => {
    setAccion({ tipo: 'enviando' })
    try {
      const r = await post(`/incidentes/${id}/${ruta}`, cuerpo)
      setAccion({ tipo: 'ok', texto: ok(r) })
      setCerrando(false)
      recargar(); onCambio()
    } catch (e) {
      setAccion({ tipo: 'error', texto: e.message })
    }
  }

  return (
    <section className="panel detalle" aria-labelledby="titulo-detalle">
      <button className="boton-texto" onClick={onVolver}>Volver a la cola</button>
      <div className="cabecera-detalle">
        <h2 id="titulo-detalle"><button className="enlace-maquina" onClick={() => onMaquina(inc.maquina_id)}>{inc.maquina_id}</button></h2>
        <Insignia severidad={inc.severidad} />
      </div>
      <p className="subtitulo">
        {inc.maquina?.modelo} en zona {inc.zona}. {ESTADO_INCIDENTE[inc.estado] || inc.estado}
        {inc.nivel_escalamiento ? ` (nivel ${inc.nivel_escalamiento})` : ''}. Score de riesgo {num(inc.score, 2)}.
      </p>
      <p>Variables fuera de lo normal: {(inc.variables_anomalas || []).map((v) => VARIABLES[v]?.nombre || v).join(', ') || '—'}.
        Componente probable: <strong>{comp(inc.componente_probable)}</strong>.</p>
      {inc.grupo_info && (
        <p className="aviso-grupo">Posible causa común: {inc.grupo_info.n_maquinas} máquinas de la zona {inc.grupo_info.zona} con
          incidentes al mismo tiempo ({(inc.grupo_info.maquinas || []).join(', ')}). Variable común: {VARIABLES[inc.grupo_info.variable_comun]?.nombre || inc.grupo_info.variable_comun}.</p>
      )}

      <h3>Diagnóstico</h3>
      {ia.causa_probable ? (
        <>
          <p>{ia.causa_probable}</p>
          {ia.acciones?.length > 0 && <ul className="acciones-ia">{ia.acciones.map((a, k) => <li key={k}>{a}</li>)}</ul>}
          <dl className="por-rol">
            {ROLES.map(([rol, nombre]) => ia.resumen_por_rol?.[rol] && (
              <div key={rol}><dt>{nombre}</dt><dd>{ia.resumen_por_rol[rol]}</dd></div>
            ))}
          </dl>
          <p className="nota">Generado con {FUENTE_IA[ia.fuente] || ia.fuente}.</p>
        </>
      ) : <p className="vacio">La explicación aparece cuando el flujo termina el paso de IA.</p>}

      <h3>Respuesta operativa</h3>
      <dl className="datos">
        <div><dt>Técnico</dt><dd>{inc.tecnico_id ? `${asig.nombre || inc.tecnico_id} a ${num(asig.distancia_km, 1)} km${asig.especialista ? ', especialista' : ''}` : 'Sin asignar'}</dd></div>
        <div><dt>Llegada y reparación</dt><dd>{asig.eta ? `${asig.eta.total_min} min (viaje ${num(asig.eta.viaje_min, 0)} + reparación ${asig.eta.reparacion_min})` : '—'}</dd></div>
        <div><dt>Repuesto</dt><dd>{rep.reservado ? `${comp(rep.componente)} reservado en ${rep.almacen}, quedan ${rep.stock_restante}` : rep.motivo || '—'}
          {rep.bajo_minimo && <span className="etiqueta-alerta">Bajo el mínimo</span>}</dd></div>
        {inc.tiempo_detenida_min !== undefined && <div><dt>Tiempo detenida</dt><dd>{num(inc.tiempo_detenida_min, 0)} min{inc.recurrencia ? ', falla recurrente' : ''}</dd></div>}
      </dl>

      {abierto && (
        <div className="fila-botones">
          {inc.estado !== 'en_atencion' && (
            <button className="boton-primario" disabled={accion?.tipo === 'enviando'}
                    onClick={() => ejecutar('atender', { tecnico_id: inc.tecnico_id }, () => 'El técnico está atendiendo. El flujo deja de escalar.')}>
              Marcar en atención
            </button>
          )}
          <button className="boton-secundario" onClick={() => setCerrando((c) => !c)} aria-expanded={cerrando}>Cerrar incidente</button>
        </div>
      )}
      {cerrando && (
        <form className="form-cierre" onSubmit={(e) => {
          e.preventDefault()
          ejecutar('cerrar', { intervencion, componentes: compsSel },
            (r) => `Cerrado. Tiempo detenida: ${num(r.tiempo_detenida_min, 0)} min.${r.recurrencia ? ` Falla recurrente (antes: ${r.recurrencia_de}).` : ''}`)
        }}>
          <label>Intervención realizada<input value={intervencion} onChange={(e) => setIntervencion(e.target.value)} required /></label>
          <fieldset><legend>Componentes reemplazados</legend>
            {Object.entries(COMPONENTES).filter(([c]) => c !== 'ninguno').map(([c, nombre]) => (
              <label key={c} className="check">
                <input type="checkbox" checked={compsSel.includes(c)}
                       onChange={(e) => setComponentes(e.target.checked ? [...compsSel, c] : compsSel.filter((x) => x !== c))} />
                {nombre}
              </label>
            ))}
          </fieldset>
          <button className="boton-primario" type="submit" disabled={accion?.tipo === 'enviando'}>Confirmar cierre</button>
        </form>
      )}
      {accion?.texto && <p className={accion.tipo === 'error' ? 'aviso-error' : 'aviso-ok'} role="status">{accion.texto}</p>}

      <h3>Línea de tiempo</h3>
      <ol className="linea-tiempo">
        {(inc.timeline || []).map((ev, k) => (
          <li key={k}><time>{hora(ev.ts)}</time> {EVENTOS[ev.evento] || ev.evento}
            {ev.tecnico_id ? `: ${ev.tecnico_id}` : ''}{ev.destino ? ` a ${ev.destino}` : ''}{ev.almacen ? ` en ${ev.almacen}` : ''}</li>
        ))}
      </ol>
    </section>
  )
}
