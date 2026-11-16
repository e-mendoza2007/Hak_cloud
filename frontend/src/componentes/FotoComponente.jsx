import { useState } from 'react'
import { post } from '../api.js'

// Reduce la foto a 1024 px (JPEG) en el navegador: así cabe holgada en API Gateway y Lambda
function reducir(archivo, max = 1024) {
  return new Promise((resolver, rechazar) => {
    const img = new Image()
    img.onload = () => {
      const k = Math.min(1, max / Math.max(img.width, img.height))
      const lienzo = document.createElement('canvas')
      lienzo.width = Math.round(img.width * k)
      lienzo.height = Math.round(img.height * k)
      lienzo.getContext('2d').drawImage(img, 0, 0, lienzo.width, lienzo.height)
      resolver(lienzo.toDataURL('image/jpeg', 0.85).split(',')[1])
      URL.revokeObjectURL(img.src)
    }
    img.onerror = () => rechazar(new Error('No se pudo leer la imagen'))
    img.src = URL.createObjectURL(archivo)
  })
}

// Foto del componente: se guarda en S3 (con versionado) y Amazon Rekognition dice qué ve
export default function FotoComponente({ incidenteId, foto, onCambio }) {
  const [estado, setEstado] = useState(null)

  const subir = async (e) => {
    const archivo = e.target.files?.[0]
    if (!archivo) return
    setEstado({ tipo: 'enviando', texto: 'Analizando la foto…' })
    try {
      const imagen_base64 = await reducir(archivo)
      await post(`/incidentes/${incidenteId}/foto`, { imagen_base64, tipo: 'image/jpeg' })
      setEstado(null)
      onCambio()
    } catch (err) {
      setEstado({ tipo: 'error', texto: err.message })
    } finally {
      e.target.value = ''
    }
  }

  return (
    <div className="foto-componente">
      <h3>Foto del componente</h3>
      {foto ? (
        <>
          <p>Rekognition ve: {foto.etiquetas.map((t) => `${t.nombre} (${Math.round(t.confianza)} %)`).join(', ') || 'nada reconocible'}.</p>
          {foto.posible_dano?.length > 0 && <p className="aviso-grupo">Posible daño visible: {foto.posible_dano.join(', ')}.</p>}
          <p className="nota">Guardada en {foto.s3}</p>
        </>
      ) : <p className="vacio">Sube una foto de la pieza para que el técnico llegue con más contexto.</p>}
      <label className="boton-secundario boton-archivo">
        {foto ? 'Subir otra foto' : 'Subir foto'}
        <input type="file" accept="image/*" capture="environment" onChange={subir} disabled={estado?.tipo === 'enviando'} />
      </label>
      {estado?.texto && <p className={estado.tipo === 'error' ? 'aviso-error' : 'nota'} role="status">{estado.texto}</p>}
    </div>
  )
}
