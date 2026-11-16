import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from './api.js'

// Consulta una ruta cada `ms` milisegundos (polling), con dos cuidados para no disparar Lambdas de más
// (regla de la hackathon: menos de 10 a la vez):
//  - si la pestaña no está visible, no consulta; al volver a verla, refresca una vez;
//  - si la API responde 429 (tope de concurrencia), conserva los últimos datos sin mostrar error.
export function usePolling(ruta, ms = 15000) {
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState(null)
  const vivo = useRef(true)

  const recargar = useCallback(async () => {
    if (!ruta) return
    try {
      const d = await api(ruta)
      if (vivo.current) { setDatos(d); setError(null) }
    } catch (e) {
      if (vivo.current && e.status !== 429) setError(e.message)
    }
  }, [ruta])

  useEffect(() => {
    vivo.current = true
    setDatos(null)
    recargar()
    const t = ms ? setInterval(() => { if (!document.hidden) recargar() }, ms) : null
    const alVolver = () => { if (!document.hidden) recargar() }
    document.addEventListener('visibilitychange', alVolver)
    return () => {
      vivo.current = false
      if (t) clearInterval(t)
      document.removeEventListener('visibilitychange', alVolver)
    }
  }, [recargar, ms])

  return { datos, error, recargar }
}
