import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from './api.js'

// Consulta una ruta cada `ms` milisegundos (polling). Sin servidores encendidos: el navegador pregunta.
export function usePolling(ruta, ms = 10000) {
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState(null)
  const vivo = useRef(true)

  const recargar = useCallback(async () => {
    if (!ruta) return
    try {
      const d = await api(ruta)
      if (vivo.current) { setDatos(d); setError(null) }
    } catch (e) {
      if (vivo.current) setError(e.message)
    }
  }, [ruta])

  useEffect(() => {
    vivo.current = true
    setDatos(null)
    recargar()
    const t = ms ? setInterval(recargar, ms) : null
    return () => { vivo.current = false; if (t) clearInterval(t) }
  }, [recargar, ms])

  return { datos, error, recargar }
}
