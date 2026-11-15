import { useState } from 'react'
import { usePolling } from './hooks.js'
import Baliza from './componentes/Baliza.jsx'
import MapaFlota from './componentes/MapaFlota.jsx'
import ColaIncidentes from './componentes/ColaIncidentes.jsx'
import DetalleIncidente from './componentes/DetalleIncidente.jsx'
import PanelMaquina from './componentes/PanelMaquina.jsx'
import VistaFlota from './componentes/VistaFlota.jsx'
import VistaRecursos from './componentes/VistaRecursos.jsx'
import VistaBandeja from './componentes/VistaBandeja.jsx'
import VistaAsistente from './componentes/VistaAsistente.jsx'

const VISTAS = [
  ['operacion', 'Operación'],
  ['flota', 'Productividad y combustible'],
  ['recursos', 'Técnicos y repuestos'],
  ['bandeja', 'Bandeja por rol'],
  ['asistente', 'Asistente'],
]

// Enlaces directos para la demo: ?vista=bandeja, ?incidente=INC-..., ?maquina=M-017
const URL_INICIAL = new URLSearchParams(window.location.search)

export default function App() {
  const [vista, setVista] = useState(URL_INICIAL.get('vista') || 'operacion')
  const [incidenteSel, setIncidenteSel] = useState(URL_INICIAL.get('incidente'))
  const [maquinaSel, setMaquinaSel] = useState(URL_INICIAL.get('maquina'))
  const maquinas = usePolling('/maquinas', 10000)
  const incidentes = usePolling('/incidentes', 8000)
  const tecnicos = usePolling('/tecnicos', 15000)

  const listaMaq = maquinas.datos?.maquinas || []
  const listaInc = incidentes.datos?.incidentes || []
  const error = maquinas.error || incidentes.error

  const verIncidente = (id) => { setMaquinaSel(null); setIncidenteSel(id); setVista('operacion') }
  const verMaquina = (id) => { setIncidenteSel(null); setMaquinaSel(id); setVista('operacion') }

  return (
    <div className="app">
      <Baliza maquinas={listaMaq} incidentes={listaInc} onCambio={() => { maquinas.recargar(); incidentes.recargar() }} />
      <nav className="pestanas" aria-label="Vistas">
        {VISTAS.map(([id, nombre]) => (
          <button key={id} className={vista === id ? 'activa' : ''} aria-current={vista === id ? 'page' : undefined}
                  onClick={() => setVista(id)}>{nombre}</button>
        ))}
      </nav>
      {error && <p className="aviso-error" role="alert">{error}</p>}

      {vista === 'operacion' && (
        <main className="operacion">
          <MapaFlota maquinas={listaMaq} incidentes={listaInc} tecnicos={tecnicos.datos?.tecnicos || []}
                     onMaquina={verMaquina} seleccion={maquinaSel || listaInc.find((i) => i.incidente_id === incidenteSel)?.maquina_id} />
          <aside className="lateral">
            {incidenteSel
              ? <DetalleIncidente id={incidenteSel} onVolver={() => setIncidenteSel(null)} onMaquina={verMaquina}
                                  onCambio={() => { incidentes.recargar(); maquinas.recargar(); tecnicos.recargar() }} />
              : maquinaSel
                ? <PanelMaquina id={maquinaSel} onVolver={() => setMaquinaSel(null)} onIncidente={verIncidente} />
                : <ColaIncidentes incidentes={listaInc} cargando={!incidentes.datos && !incidentes.error} onSeleccionar={verIncidente} />}
          </aside>
        </main>
      )}
      {vista === 'flota' && <VistaFlota onMaquina={verMaquina} />}
      {vista === 'recursos' && <VistaRecursos tecnicos={tecnicos} onIncidente={verIncidente} />}
      {vista === 'bandeja' && <VistaBandeja onIncidente={verIncidente} />}
      {vista === 'asistente' && <VistaAsistente />}
    </div>
  )
}
