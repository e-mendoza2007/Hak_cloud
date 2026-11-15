import { SEVERIDAD } from '../formato.js'

// La severidad nunca va solo por color: siempre con su nombre escrito (como una señal de seguridad).
export default function Insignia({ severidad }) {
  return <span className={`insignia sev-${severidad}`}>{SEVERIDAD[severidad]?.etiqueta || severidad}</span>
}
