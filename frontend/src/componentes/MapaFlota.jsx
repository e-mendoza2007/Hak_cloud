import { useMemo } from 'react'
import { MapContainer, TileLayer, Marker, Tooltip } from 'react-leaflet'
import L from 'leaflet'
import { ESTADO_MAQUINA, SEVERIDAD, comp } from '../formato.js'

const CENTRO = [-12.06, -77.027]
const ALMACENES = { 'ALM-Z1': [-12.040, -77.030], 'ALM-Z2': [-12.060, -77.050], 'ALM-Z3': [-12.080, -77.020], 'ALM-Z4': [-12.050, -77.000] }

// Íconos como HTML: la forma también comunica (cuadrado = máquina, triángulo = incidente, círculo = técnico)
const iconoMaquina = (m, inc, sel) => L.divIcon({
  className: '',
  html: `<span class="pin pin-${m.estado || 'detenida'}${inc ? ` pin-inc sev-${inc.severidad}` : ''}${sel ? ' pin-sel' : ''}">${m.maquina_id.replace('M-', '')}</span>`,
  iconSize: [30, 30], iconAnchor: [15, 15],
})
const iconoTecnico = (t) => L.divIcon({
  className: '', html: `<span class="pin-tecnico pin-tec-${t.estado}">${t.tecnico_id.replace('T-', 'T')}</span>`,
  iconSize: [24, 24], iconAnchor: [12, 12],
})
const iconoAlmacen = L.divIcon({ className: '', html: '<span class="pin-almacen">A</span>', iconSize: [20, 20], iconAnchor: [10, 10] })

export default function MapaFlota({ maquinas, incidentes, tecnicos, onMaquina, seleccion }) {
  const incPorMaquina = useMemo(() => {
    const r = {}
    incidentes.forEach((i) => {
      const prev = r[i.maquina_id]
      if (!prev || (SEVERIDAD[i.severidad]?.orden || 0) > (SEVERIDAD[prev.severidad]?.orden || 0)) r[i.maquina_id] = i
    })
    return r
  }, [incidentes])

  return (
    <section className="mapa" aria-label="Mapa de la flota">
      <MapContainer center={CENTRO} zoom={14} scrollWheelZoom className="mapa-leaflet">
        <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                   url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        {Object.entries(ALMACENES).map(([id, pos]) => (
          <Marker key={id} position={pos} icon={iconoAlmacen}><Tooltip>Almacén {id}</Tooltip></Marker>
        ))}
        {tecnicos.filter((t) => t.lat).map((t) => (
          <Marker key={t.tecnico_id} position={[t.lat, t.lon]} icon={iconoTecnico(t)}>
            <Tooltip>{t.nombre || t.tecnico_id}: {t.estado}{t.incidente_actual ? ` (${t.incidente_actual})` : ''}</Tooltip>
          </Marker>
        ))}
        {maquinas.filter((m) => m.lat).map((m) => {
          const inc = incPorMaquina[m.maquina_id]
          return (
            <Marker key={m.maquina_id} position={[m.lat, m.lon]} icon={iconoMaquina(m, inc, seleccion === m.maquina_id)}
                    eventHandlers={{ click: () => onMaquina(m.maquina_id) }} zIndexOffset={inc ? 1000 : 0}>
              <Tooltip>
                <strong>{m.maquina_id}</strong> {m.modelo} en zona {m.zona}<br />
                {ESTADO_MAQUINA[m.estado] || m.estado}
                {inc ? <><br />Incidente {SEVERIDAD[inc.severidad]?.etiqueta.toLowerCase()}: {comp(inc.componente_probable)}</> : null}
              </Tooltip>
            </Marker>
          )
        })}
      </MapContainer>
      <ul className="leyenda" aria-label="Leyenda del mapa">
        <li><span className="pin pin-operativa">17</span> Operativa</li>
        <li><span className="pin pin-detenida">17</span> Detenida</li>
        <li><span className="pin pin-requiere_intervencion">17</span> Requiere intervención</li>
        <li><span className="pin pin-inc sev-alta">17</span> Con incidente abierto</li>
        <li><span className="pin-tecnico pin-tec-disponible">T1</span> Técnico</li>
        <li><span className="pin-almacen">A</span> Almacén</li>
      </ul>
    </section>
  )
}
