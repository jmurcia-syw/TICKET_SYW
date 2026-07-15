import { useEffect, useMemo, useRef } from 'react'
import DOMPurify from 'dompurify'
import apiClient from '../../services/apiClient'

interface RichTextViewerProps {
  html: string
}

/** Muestra HTML enriquecido ya saneado por el servidor (spec 017) — vuelve a sanear en el
 * cliente antes de inyectarlo (defensa en profundidad, nunca confiar ciegamente en lo ya
 * persistido). Contenido plano preexistente (sin tags) se muestra igual, sin cambios.
 *
 * Las imágenes incrustadas apuntan a `/api/tickets/.../attachments/...` (descarga autenticada
 * por JWT vía header, spec 002) — un `<img src>` nativo no puede mandar ese header, así que acá
 * se buscan esas imágenes y se reemplaza su `src` por un blob URL obtenido con `apiClient`. */
export default function RichTextViewer({ html }: RichTextViewerProps) {
  const clean = DOMPurify.sanitize(html || '')
  const containerRef = useRef<HTMLDivElement>(null)
  // `dangerouslySetInnerHTML` se diffea por referencia del objeto, no por el valor de `__html`:
  // sin memoizar, cada re-render de la página (ej. el timer de la sesión de foco, que cambia de
  // estado cada segundo) crea un objeto nuevo y React vuelve a pisar el innerHTML, destruyendo el
  // swap a blob URL hecho abajo aunque el HTML en sí no haya cambiado.
  const htmlProp = useMemo(() => ({ __html: clean }), [clean])

  useEffect(() => {
    const container = containerRef.current
    if (!container) return
    const blobUrls: string[] = []
    const images = Array.from(container.querySelectorAll('img[src^="/api/"]'))
    images.forEach((img) => {
      const src = img.getAttribute('src')
      if (!src) return
      apiClient.get(src, { responseType: 'blob' })
        .then(res => {
          const blobUrl = URL.createObjectURL(res.data as Blob)
          blobUrls.push(blobUrl)
          img.setAttribute('src', blobUrl)
        })
        .catch(() => { img.setAttribute('alt', 'Imagen no disponible') })
    })
    return () => { blobUrls.forEach(u => URL.revokeObjectURL(u)) }
  }, [clean])

  return (
    <div
      ref={containerRef}
      className="sywork-rich-viewer"
      style={{ whiteSpace: 'pre-wrap' }}
      // eslint-disable-next-line react/no-danger
      dangerouslySetInnerHTML={htmlProp}
    />
  )
}
