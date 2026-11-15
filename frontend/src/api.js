// Cliente de la API REST de plataforma/ (API Gateway). La URL llega por VITE_API_URL en .env.local
const BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')

export async function api(ruta, opciones = {}) {
  if (!BASE) throw new Error('Falta VITE_API_URL en frontend/.env.local')
  const r = await fetch(BASE + ruta, { ...opciones, headers: { 'Content-Type': 'application/json' } })
  const datos = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(datos.error || `La API respondió ${r.status} en ${ruta}`)
  return datos
}

export const post = (ruta, cuerpo) => api(ruta, { method: 'POST', body: JSON.stringify(cuerpo || {}) })
