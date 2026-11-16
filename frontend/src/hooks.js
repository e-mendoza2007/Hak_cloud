import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from './api.js'

// Consulta una ruta cada `ms` milisegundos (polling), con dos cuidados para no disparar Lambdas de más
// (regla de la hackathon: menos de 10 a la vez):
//  - si la pestaña no está visible, no consulta; al volver a verla, refresca una vez;
//  - si la API falla de forma transitoria (429/5xx por el tope de concurrencia, o la red), reintenta una vez
//    tras una espera aleatoria y conserva los últimos datos; solo muestra el error si vuelve a fallar.
export function usePolling(ruta, ms = 15000) {
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState(null)
  const vivo = useRef(true)

  const recargar = useCallback(async () => {
    if (!ruta) return
    for (let intento = 0; intento < 2; intento++) {
      try {
        const d = await api(ruta)
        if (vivo.current) { setDatos(d); setError(null) }
        return
      } catch (e) {
        const transitorio = !e.status || e.status === 429 || e.status >= 500
        if (transitorio && intento === 0) {
          await new Promise((r) => setTimeout(r, 1000 + Math.random() * 2000))
          continue
        }
        if (vivo.current) setError(e.message)
        return
      }
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
