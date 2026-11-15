import { useState } from 'react'
import { usePolling } from '../hooks.js'
import Insignia from './Insignia.jsx'
import { ROLES, hora } from '../formato.js'

const QUE_RECIBE = {
  operador: 'Qué hacer ahora con la máquina. Solo bandeja: no recibe correos.',
  tecnico: 'Diagnóstico, repuesto reservado y tiempo estimado. Recibe correo siempre.',
  supervisor: 'Prioridad, asignación, stock y causas comunes. Recibe correo siempre y los escalamientos de nivel 1.',
  gerente: 'Impacto en la operación. Correo solo en incidentes críticos y en escalamientos de nivel 2.',
}

export default function VistaBandeja({ onIncidente }) {
  const [rol, setRol] = useState('supervisor')
  const { datos, error } = usePolling(`/notificaciones?rol=${rol}`, 8000)

  return (
    <main className="vista">
      <section className="panel ancho">
        <h2>Bandeja por rol</h2>
        <div className="segmentado-botones" role="tablist" aria-label="Rol">
          {ROLES.map(([id, nombre]) => (
            <button key={id} role="tab" aria-selected={rol === id} className={rol === id ? 'activa' : ''} onClick={() => setRol(id)}>{nombre}</button>
          ))}
        </div>
        <p className="subtitulo">{QUE_RECIBE[rol]}</p>
        {error && <p className="aviso-error">{error}</p>}
        {datos && datos.notificaciones.length === 0 && <p className="vacio">Este rol no tiene mensajes todavía.</p>}
        <ul className="bandeja">
          {(datos?.notificaciones || []).map((n) => (
            <li key={n.ts}>
              <div className="bandeja-meta">
                <time>{hora(n.ts)}</time>
                {n.severidad && <Insignia severidad={n.severidad} />}
                <span className="canal">{n.canal === 'email' ? 'Correo y bandeja' : 'Solo bandeja'}</span>
                {n.tipo === 'escalamiento' && <span className="etiqueta-alerta">Escalamiento</span>}
                {n.tipo === 'preventivo' && <span className="etiqueta-info">Plan preventivo</span>}
              </div>
              <p className="bandeja-texto">{n.mensaje}</p>
              {n.incidente_id?.startsWith('INC-') && <button className="boton-texto" onClick={() => onIncidente(n.incidente_id)}>Abrir incidente</button>}
            </li>
          ))}
        </ul>
      </section>
    </main>
  )
}
