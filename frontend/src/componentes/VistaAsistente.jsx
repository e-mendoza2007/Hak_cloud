import { useState } from 'react'
import { post } from '../api.js'

const SUGERENCIAS = [
  '¿Qué máquinas atiendo primero y por qué?',
  '¿Hay alguna zona con varias máquinas fallando a la vez?',
  '¿Qué máquinas tienen el mantenimiento vencido?',
]
const FUENTE = { gemini: 'Gemini (Google)', plantilla: 'respuesta de plantilla (IA no disponible)' }
const LIMITE = 10                                   // tope de preguntas por sesión: cuida el crédito de IA

export default function VistaAsistente() {
  const [mensajes, setMensajes] = useState([])
  const [texto, setTexto] = useState('')
  const [esperando, setEsperando] = useState(false)
  const usadas = mensajes.filter((m) => m.quien === 'yo').length

  const preguntar = async (pregunta) => {
    const q = pregunta.trim()
    if (!q || esperando || usadas >= LIMITE) return
    setMensajes((m) => [...m, { quien: 'yo', texto: q }])
    setTexto('')
    setEsperando(true)
    try {
      const r = await post('/asistente', { pregunta: q })
      setMensajes((m) => [...m, { quien: 'ia', texto: r.respuesta, fuente: r.fuente }])
    } catch (e) {
      setMensajes((m) => [...m, { quien: 'error', texto: e.message }])
    } finally {
      setEsperando(false)
    }
  }

  return (
    <main className="vista">
      <section className="panel ancho chat">
        <h2>Asistente de mantenimiento</h2>
        <p className="subtitulo">Responde con los datos actuales de la operación: incidentes abiertos, riesgo por máquina y técnicos disponibles.</p>
        <div className="chat-mensajes" aria-live="polite">
          {mensajes.length === 0 && (
            <div className="sugerencias">
              {SUGERENCIAS.map((s) => <button key={s} className="boton-secundario" onClick={() => preguntar(s)}>{s}</button>)}
            </div>
          )}
          {mensajes.map((m, k) => (
            <div key={k} className={`burbuja burbuja-${m.quien}`}>
              <p>{m.texto}</p>
              {m.fuente && <small>Respondido con {FUENTE[m.fuente] || m.fuente}</small>}
            </div>
          ))}
          {esperando && <div className="burbuja burbuja-ia"><p>Consultando los datos de la operación…</p></div>}
        </div>
        <form className="chat-entrada" onSubmit={(e) => { e.preventDefault(); preguntar(texto) }}>
          <label className="oculto" htmlFor="pregunta">Pregunta</label>
          <input id="pregunta" value={texto} onChange={(e) => setTexto(e.target.value)} maxLength={500}
                 placeholder={usadas >= LIMITE ? 'Llegaste al límite de preguntas de esta sesión' : 'Escribe tu pregunta'}
                 disabled={usadas >= LIMITE} />
          <button className="boton-primario" type="submit" disabled={esperando || !texto.trim() || usadas >= LIMITE}>Preguntar</button>
        </form>
      </section>
    </main>
  )
}
