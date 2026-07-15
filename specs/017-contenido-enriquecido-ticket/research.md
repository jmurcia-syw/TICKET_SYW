# Research: Contenido enriquecido en comentarios y descripción de Ticket/Tarea

**Feature**: `017-contenido-enriquecido-ticket` · **Date**: 2026-07-14

No hay `[NEEDS CLARIFICATION]` pendientes del spec. Este documento registra decisiones técnicas
concretas, verificadas contra el código real de Fase 1 (spec 002) antes de planificar.

## Decisión 1 — Qué ya existe vs. qué es nuevo

**Hallazgo** (verificado en código): `ticket_comments.body` y `tickets.description` ya son
columnas `TEXT` sin restricción de formato — **no requieren migración de tipo**, solo dejan de
guardarse como texto plano para guardarse como HTML saneado. Los adjuntos de comentario
**ya existen** end-to-end (`comment_attachments`, `backend/infra/storage/attachments.py`,
`CommentComposer.tsx` con `Upload`) — lo nuevo es (a) dar formato al texto, (b) permitir pegar
imágenes/contenido con formato incrustado en el cuerpo, y (c) extender el mecanismo de adjuntos
(ya existente) a la descripción del Ticket/Tarea, que hoy no tiene ninguno.

## Decisión 2 — Alcance de superficies (qué inputs se enriquecen)

**Hallazgo**: `Comment.body` se escribe desde múltiples componentes, todos vía el mismo patrón
`ticketService.*(..., body/comment)`: `CommentComposer.tsx` (comentario principal, descripción
de solución al cerrar, motivo de cancelación), `KanbanPage.tsx` (comentario rápido, comentario de
cambio de estado, motivo de rechazo de resolución), `TaskStatusChanger.tsx` (comentario de cambio
de estado de Tarea). `Ticket.description` se escribe solo al crear (`TicketsPage.tsx`,
`SubtaskList.tsx` para Subtareas) — no existe hoy una pantalla de edición posterior.

**Decisión**:
- **Formato de texto** (negrilla/cursiva/subrayado/listas/hipervínculos, FR-001 a FR-003): se
  aplica a **todas** las superficies anteriores — todas escriben al mismo campo `Comment.body` o
  `Ticket.description`, así que un único componente `RichTextEditor` reutilizado en todas ellas
  cubre el pedido sin lógica nueva por endpoint (el body sigue viajando como un string).
- **Pegar imágenes incrustadas con adjunto real** (FR-004, FR-008): se habilita **solo** en las
  dos superficies explícitas del pedido original — el comentario principal
  (`POST /api/tickets/{id}/comments`, ya soporta `multipart/form-data`) y la descripción al crear
  un Ticket/Tarea (`POST /api/tickets`, se extiende para aceptar `multipart/form-data`). Las
  superficies secundarias (cerrar, cancelar, cambiar estado, rechazar resolución) usan el mismo
  editor de texto enriquecido pero con `allowImages={false}`: pueden tener negrilla/listas/
  hipervínculos, pero pegar una imagen ahí no crea un adjunto nuevo (se ignora esa imagen
  puntual, sin bloquear el resto del pegado). Justificación: son formularios de cierre/rechazo de
  bajo volumen de uso, y agregar soporte multipart a 5 endpoints más no está en el pedido
  original ni aporta valor proporcional al esfuerzo (Principio VII, alcance mínimo).

## Decisión 3 — Cómo persisten las imágenes pegadas (mecanismo único, reutiliza adjuntos)

**Alternativas consideradas**:
- Subir la imagen a un endpoint aparte apenas se pega (antes de guardar el comentario/ticket) —
  rechazada para la descripción del Ticket: al crear un Ticket nuevo **todavía no existe
  `ticket_id`**, así que no hay dónde anclar el adjunto hasta que el Ticket exista.
- Incrustar la imagen como `data:` URI directamente en el HTML guardado — rechazada: no cumple
  FR-008 ("las imágenes pegadas deben quedar disponibles con el mismo mecanismo que los adjuntos
  existentes", es decir, como fila `Attachment` descargable), y además infla indefinidamente la
  columna `TEXT` sin los límites de tamaño/tipo ya validados para adjuntos.

**Decisión**: reutilizar exactamente el patrón que ya usan los adjuntos de comentario hoy
("stage" en el cliente, subida única junto con la creación del padre):
1. El editor, al pegar una imagen, la muestra de inmediato con una URL local temporal
   (`blob:`) y la agrega a un arreglo de archivos pendientes (mismo estado `files` que ya usa
   `CommentComposer.tsx` para adjuntos manuales), marcando su posición en el HTML con
   `data-pending-id="N"` en el `<img>`.
2. Al enviar (crear el comentario o crear el Ticket/Tarea), el frontend manda `multipart/
   form-data` con el cuerpo/descripción (con los `data-pending-id` todavía presentes) y un campo
   `inline_images` con los archivos, en el mismo orden que sus índices `N`.
3. El backend crea primero el Ticket o el Comentario (ya tiene `id`), guarda cada imagen con
   `attachment_storage.save()` (mismas reglas de tamaño/tipo ya vigentes) y crea su fila
   `Attachment` (con `ticket_id` o `comment_id` según corresponda). Con los `id` reales ya
   conocidos, reescribe el HTML reemplazando cada `data-pending-id="N"` por la URL real de
   descarga del adjunto (`/api/tickets/{ticket_id}/attachments/{attachment_id}`) y guarda el
   HTML final saneado. **Actualización durante implementación (T022)**: no hace falta ningún
   parámetro `?inline=1` ni cambio de `Content-Disposition` — el JWT viaja por header
   (`Authorization: Bearer`, no cookie), así que un `<img src>` nativo nunca podría autenticar
   la descarga. `RichTextViewer` (frontend) resuelve esto pidiendo cada imagen vía `apiClient`
   (header ya inyectado por el interceptor de axios) y reemplaza el `src` por un blob URL — con
   ese mecanismo, la cabecera de disposición del servidor es irrelevante en todos los casos.
4. Adjuntos manuales (el botón "Adjuntar" ya existente) siguen exactamente igual — el nuevo campo
   `inline_images` es aparte de `files`, distinguidos solo por si el HTML los referencia o no.

**Rationale**: cero endpoints nuevos de subida "huérfana"; reutiliza 100% el almacenamiento, la
validación de tamaño/tipo y la tabla de adjuntos ya existentes (spec 002) — solo agrega el paso
de reescritura de referencias, que es lógica de aplicación, no de infraestructura nueva.

## Decisión 4 — Adjuntos ahora también en la descripción (no solo en comentarios)

**Hallazgo**: `comment_attachments.comment_id` es `NOT NULL` hoy — un adjunto siempre cuelga de
un comentario.

**Decisión**: la tabla (sin renombrarla, para minimizar el diff) gana una columna `ticket_id`
nullable y `comment_id` pasa a nullable, con una restricción `CHECK` que exige que **exactamente
una** de las dos esté presente — un adjunto es de un comentario **o** de la descripción del
Ticket/Tarea, nunca de ambos ni de ninguno. El endpoint de descarga ya existente
(`GET /api/tickets/{id}/attachments/{attachment_id}`) funciona sin cambios para ambos casos
(`CommentRepository.get_attachment` no distingue el origen).

## Decisión 5 — Mostrar imágenes incrustadas inline (no forzar descarga)

**Hallazgo**: el endpoint de descarga actual sirve todo con `as_attachment=True`
(`Content-Disposition: attachment`), lo cual fuerza la descarga del archivo — un `<img src=...>`
apuntando ahí no se renderiza inline en el navegador.

**Decisión**: agregar un parámetro opcional `?inline=1` al endpoint existente: si viene y el
`content_type` empieza con `image/`, sirve con `as_attachment=False` (se muestra inline); sin el
parámetro, se mantiene el comportamiento actual (fuerza descarga) — sin romper nada existente.

## Decisión 6 — Editor de texto enriquecido (dependencia nueva, aprobación Principio V)

**Decisión**: **TipTap** (`@tiptap/react` + `@tiptap/starter-kit` +
`@tiptap/extension-underline` + `@tiptap/extension-link` + `@tiptap/extension-image`).

**Alternativas consideradas**:
- `react-quill` (Quill) — descartada: soporte de React 18/19 en modo estricto es inestable
  (issues abiertos de larga data en el proyecto), y este stack ya corre en React 19.
- `Slate`/`Draft.js` — descartadas: requieren construir la UI del toolbar y el manejo de paste
  desde cero (son "headless" de más bajo nivel que TipTap), más esfuerzo sin beneficio adicional
  para este alcance.
- `Lexical` (Meta) — viable pero significativamente menos madura su integración con extensiones
  de imagen/paste-cleanup listas para usar, comparada con el ecosistema de extensiones oficiales
  de TipTap.

**Rationale**: TipTap (basado en ProseMirror) es TypeScript-first, tiene manejo de `paste`
configurable (`editorProps.transformPastedHTML`) ideal para normalizar contenido pegado de
Word/Outlook/web, extensión oficial de imágenes, y es la opción con mejor soporte activo para
React 19 al día de hoy.

**Hallazgo durante validación en Docker real (T036)**: `RichTextViewer.tsx` reemplaza el `src`
de cada `<img>` incrustado por un blob URL autenticado (Decisión 5) mediante una mutación
imperativa del DOM dentro de un `useEffect`. El `div` contenedor usa `dangerouslySetInnerHTML=
{{ __html: clean }}` — React diferencia esa prop por **referencia de objeto**, no por el valor
de `__html`; al pasar un objeto literal nuevo en cada render, cualquier re-render de la página
que hospeda el visor (ej. el timer de "Sesión de trabajo" en `TicketDetailPage`, que cambia de
estado cada segundo) hacía que React reescribiera el `innerHTML` con el HTML original (con el
`src` crudo `/api/tickets/.../attachments/...`), destruyendo el blob URL ya asignado — la imagen
quedaba visualmente rota unos instantes después de cargar. Corregido memoizando el objeto con
`useMemo(() => ({ __html: clean }), [clean])` para que React solo lo reaplique cuando el HTML
sanitizado cambia de verdad.

## Decisión 7 — Saneamiento de HTML (defensa en profundidad, dos capas)

**Decisión**:
- **Cliente** (primera línea, UX): `DOMPurify` limpia el HTML pegado *antes* de que TipTap lo
  inserte en el documento (vía `transformPastedHTML`), evitando que se vea basura pegada de
  Word/Outlook (estilos MSO, clases condicionales) incluso antes de guardar.
- **Servidor** (línea autoritativa, seguridad — Principio IV): `bleach` (Python) limpia el HTML
  final antes de persistirlo en `body`/`description`, con una lista blanca fija de tags
  (`p, br, strong, b, em, i, u, a, ul, ol, li, img, blockquote`) y atributos (`href`, `target`,
  `rel`, `src`, `alt`) — nunca se confía en el saneamiento del cliente, un llamado directo a la
  API sin pasar por el editor también queda protegido.
- **Reescritura de `data-pending-id`** (Decisión 3) se hace con `lxml.html` (parseo/serialización
  robusta de HTML real, tolerante a tags no cerrados) **antes** del paso de `bleach`, para que el
  saneamiento final vea ya las URLs reales de los adjuntos.

**Dependencias backend nuevas** (aprobación Principio V, documentada en este plan):
`bleach` (saneamiento HTML, librería madura y de uso estándar en Python) y `lxml` (parseo/
reescritura de HTML, estándar de facto en el ecosistema Python).

## Decisión 8 — Comprobación de "comentario/descripción vacío" con HTML

**Hallazgo**: la validación actual (`comment_service.py`) usa `(body or "").strip()` — un
comentario "vacío" desde un editor de texto enriquecido puede llegar como `<p></p>` o
`<p><br></p>`, que no son strings vacíos y pasarían la validación actual sin contenido real.

**Decisión**: agregar un helper que despoja todas las etiquetas HTML (reutilizando
`bleach.clean(html, tags=[], strip=True)`) antes de comprobar que quede texto no vacío —
aplicado tanto en `comment_service.validate` (comentarios) como en la validación de `description`
requerida al crear un Ticket/Tarea (`TicketList.post`).

## Decisión 9 — Vista previa en texto plano (FR-010)

**Decisión**: el mismo helper de "despojar HTML" (Decisión 8) se reutiliza donde ya existan
vistas previas/resúmenes de comentario o descripción en texto plano (si las hay en listados o
notificaciones) — no se identificó ningún resumen de este tipo en el código actual más allá del
propio detalle del ticket, así que esta decisión queda como una utilidad disponible para
futuro uso, sin un punto de aplicación obligatorio nuevo en este alcance.
