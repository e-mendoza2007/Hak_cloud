import { useState } from 'react'
import { post } from '../api.js'

const TIPOS = [
  ['rodamiento', 'Rodamiento (vibración y temperatura)'],
  ['refrigeracion', 'Refrigeración (temperatura)'],
  ['inyectores', 'Inyectores (combustible)'],
  ['hidraulica', 'Hidráulica (presión)'],
]

// Panel de demo: inyecta una degradación gradual con POST /demo/falla (requiere el simulador encendido).
export default function PanelSimulacion({ maquinas, onCerrar, onCambio }) {
  const [alcance, setAlcance] = useState('maquina')
  const [maquina, setMaquina] = useState('M-017')
  const [zona, setZona] = useState('Z2')
  const [tipo, setTipo] = useState('rodamiento')
  const [rampa, setRampa] = useState(3)
  const [cantidad, setCantidad] = useState(3)
  const [estado, setEstado] = useState(null)

  const deLaZona = maquinas.filter((m) => m.zona === zona).map((m) => m.maquina_id).sort()
  const objetivo = alcance === 'maquina' ? { maquina_id: maquina }
    : alcance === 'grupo' ? { maquinas: deLaZona.slice(0, Number(cantidad)) } : { zona }
  const enviar = async (limpiar) => {
    setEstado({ tipo: 'enviando' })
    try {
      const r = await post('/demo/falla', limpiar ? { ...objetivo, limpiar: true } : { ...objetivo, tipo, rampa_min: Number(rampa) })
      const ids = r.degradando || r.limpiadas || []
      setEstado({ tipo: 'ok', texto: limpiar ? `Falla quitada en ${ids.join(', ')}.` : `Degradando ${ids.join(', ')} durante ${rampa} min.` })
      onCambio()
    } catch (e) {
      setEstado({ tipo: 'error', texto: e.message })
    }
  }

  return (
    <div className="panel-simulacion" role="dialog" aria-label="Simular falla">
      <p className="nota">Inyecta una degradación gradual en la telemetría simulada. El simulador tiene que estar encendido.</p>
      <fieldset className="segmentado">
        <legend>Alcance</legend>
        <label><input type="radio" checked={alcance === 'maquina'} onChange={() => setAlcance('maquina')} /> Una máquina</label>
        <label><input type="radio" checked={alcance === 'grupo'} onChange={() => setAlcance('grupo')} /> Varias de una zona</label>
        <label><input type="radio" checked={alcance === 'zona'} onChange={() => setAlcance('zona')} /> Toda una zona</label>
      </fieldset>
      {alcance === 'maquina' ? (
        <label>Máquina
          <select value={maquina} onChange={(e) => setMaquina(e.target.value)}>
            {(maquinas.length ? maquinas.map((m) => m.maquina_id) : ['M-017']).map((id) => <option key={id}>{id}</option>)}
          </select>
        </label>
      ) : (
        <label>Zona
          <select value={zona} onChange={(e) => setZona(e.target.value)}>
            {['Z1', 'Z2', 'Z3', 'Z4'].map((z) => <option key={z}>{z}</option>)}
          </select>
        </label>
      )}
      {alcance === 'grupo' && (
        <label>Cuántas máquinas de {zona} (desde 3 se detecta causa común)
          <select value={cantidad} onChange={(e) => setCantidad(e.target.value)}>
            {[3, 4].map((n) => <option key={n} value={n}>{n}: {deLaZona.slice(0, n).join(', ')}</option>)}
          </select>
        </label>
      )}
      <label>Tipo de falla
        <select value={tipo} onChange={(e) => setTipo(e.target.value)}>
          {TIPOS.map(([id, nombre]) => <option key={id} value={id}>{nombre}</option>)}
        </select>
      </label>
      <label>Minutos hasta la falla completa
        <input type="number" min="1" max="30" value={rampa} onChange={(e) => setRampa(e.target.value)} />
      </label>
      <div className="fila-botones">
        <button className="boton-primario" onClick={() => enviar(false)} disabled={estado?.tipo === 'enviando'}>Inyectar falla</button>
        <button className="boton-secundario" onClick={() => enviar(true)} disabled={estado?.tipo === 'enviando'}>Quitar falla</button>
        <button className="boton-texto" onClick={onCerrar}>Cerrar</button>
      </div>
      {estado?.texto && <p className={estado.tipo === 'error' ? 'aviso-error' : 'aviso-ok'} role="status">{estado.texto}</p>}
    </div>
  )
}
