export const SEVERIDAD = {
  critica: { etiqueta: 'Crítica', orden: 4 },
  alta: { etiqueta: 'Alta', orden: 3 },
  media: { etiqueta: 'Media', orden: 2 },
  baja: { etiqueta: 'Baja', orden: 1 },
  normal: { etiqueta: 'Normal', orden: 0 },
}

export const ESTADO_MAQUINA = {
  operativa: 'Operativa',
  detenida: 'Detenida',
  requiere_intervencion: 'Requiere intervención',
  mantenimiento: 'En mantenimiento',
}

export const ESTADO_INCIDENTE = {
  abierto: 'Abierto',
  asignado: 'Técnico asignado',
  en_atencion: 'En atención',
  escalado: 'Escalado',
  resuelto: 'Resuelto',
}

export const ROLES = [
  ['operador', 'Operador'],
  ['tecnico', 'Técnico'],
  ['supervisor', 'Supervisor'],
  ['gerente', 'Gerente'],
]

export const COMPONENTES = {
  rodamientos: 'Rodamientos',
  refrigeracion: 'Refrigeración',
  bomba_hidraulica: 'Bomba hidráulica',
  inyectores: 'Inyectores',
  motor_transmision: 'Motor y transmisión',
  ninguno: 'Sin identificar',
}

export const VARIABLES = {
  temperatura: { nombre: 'Temperatura', unidad: '°C' },
  vibracion: { nombre: 'Vibración', unidad: 'mm/s' },
  presion: { nombre: 'Presión hidráulica', unidad: 'bar' },
  combustible_lh: { nombre: 'Combustible', unidad: 'L/h' },
  rpm: { nombre: 'Revoluciones', unidad: 'rpm' },
}

export const comp = (c) => COMPONENTES[c] || c || 'Sin identificar'

export function hora(ts) {
  if (!ts) return '—'
  return new Date(Number(ts)).toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
}

export function haceCuanto(ts) {
  if (!ts) return '—'
  const s = Math.max(0, Math.round((Date.now() - Number(ts)) / 1000))
  if (s < 60) return `hace ${s} s`
  if (s < 3600) return `hace ${Math.round(s / 60)} min`
  return `hace ${Math.round(s / 3600)} h`
}

export function fecha(ts) {
  if (!ts) return '—'
  return new Date(Number(ts)).toLocaleDateString('es-PE', { day: '2-digit', month: '2-digit' })
}

export const num = (x, d = 1) => (x === null || x === undefined ? '—' : Number(x).toFixed(d))
export const pct = (x) => (x === null || x === undefined ? '—' : `${Math.round(Number(x) * 100)} %`)
