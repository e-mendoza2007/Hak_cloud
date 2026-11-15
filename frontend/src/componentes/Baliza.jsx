import { useState } from 'react'
import PanelSimulacion from './PanelSimulacion.jsx'

// Franja de estado de la operación. Las rayas de seguridad cambian de color con el incidente más grave abierto.
export default function Baliza({ maquinas, incidentes, onCambio }) {
  const [simulando, setSimulando] = useState(false)
  const cuenta = { critica: 0, alta: 0, media: 0 }
  incidentes.forEach((i) => { if (cuenta[i.severidad] !== undefined) cuenta[i.severidad] += 1 })
  const nivel = cuenta.critica ? 'critica' : cuenta.alta ? 'alta' : cuenta.media ? 'media' : 'calma'
  const operativas = maquinas.filter((m) => m.estado === 'operativa').length
  const intervencion = maquinas.filter((m) => m.estado === 'requiere_intervencion').length
  const mensaje = {
    critica: `${cuenta.critica} incidente${cuenta.critica > 1 ? 's' : ''} crítico${cuenta.critica > 1 ? 's' : ''} en curso`,
    alta: 'Hay incidentes de severidad alta',
    media: 'Incidentes en observación',
    calma: 'Operación sin incidentes abiertos',
  }[nivel]

  return (
    <header className={`baliza baliza-${nivel}`}>
      <div className="baliza-franja" aria-hidden="true" />
      <div className="baliza-cuerpo">
        <div className="baliza-titulo">
          <span className="marca">ArquiFusion</span>
          <h1 aria-live="polite">{mensaje}</h1>
        </div>
        <dl className="contadores">
          <div className="contador sev-critica"><dt>Crítica</dt><dd>{cuenta.critica}</dd></div>
          <div className="contador sev-alta"><dt>Alta</dt><dd>{cuenta.alta}</dd></div>
          <div className="contador sev-media"><dt>Media</dt><dd>{cuenta.media}</dd></div>
          <div className="contador"><dt>Operativas</dt><dd>{operativas}<small> de {maquinas.length}</small></dd></div>
          <div className="contador"><dt>Requieren intervención</dt><dd>{intervencion}</dd></div>
        </dl>
        <div className="baliza-acciones">
          <button className="boton-secundario" onClick={() => setSimulando((s) => !s)} aria-expanded={simulando}>
            Simular falla
          </button>
          {simulando && <PanelSimulacion maquinas={maquinas} onCerrar={() => setSimulando(false)} onCambio={onCambio} />}
        </div>
      </div>
    </header>
  )
}
