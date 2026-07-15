# Contract: Contenido enriquecido en Tickets/Tareas y Comentarios (spec 017)

Cambios sobre endpoints existentes de `backend/api/routes/tickets.py` (spec 002/008/009). Sin
endpoints nuevos.

**Nota de implementación**: el diseño original consideraba un parámetro `?inline=1` en el
endpoint de descarga para servir imágenes con `Content-Disposition: inline`. Se descartó: el
JWT de este sistema viaja por header (`Authorization: Bearer`, spec 001), no por cookie, así que
un `<img src>` nativo nunca podría autenticar la descarga sin importar la cabecera de
disposición. En su lugar, `RichTextViewer` (frontend) pide cada imagen vía `apiClient`
(header ya inyectado) y la muestra como blob URL — la cabecera de disposición del servidor
queda sin efecto en ese flujo, así que el endpoint de descarga se mantiene sin cambios.

## POST /api/tickets — creación con descripción enriquecida + imágenes pegadas

Sin cambios de permiso. Acepta ahora **también** `multipart/form-data` (antes solo JSON), igual
que ya hace `POST /api/tickets/{id}/comments`.

**Body JSON (sin imágenes pegadas)**: sin cambios de forma — `description` ahora puede contener
HTML saneado en vez de texto plano; el backend lo sanea igual en ambos casos.

**Body multipart (con imágenes pegadas en la descripción)**:
- Todos los campos de siempre como partes de formulario (`title`, `description` con
  `data-pending-id="N"` en los `<img>` pegados, `client_id`, etc.).
- `inline_images`: 0..N archivos, en el mismo orden que sus `data-pending-id` en `description`.
  Mismas reglas de tamaño/tipo que ya aplican a adjuntos de comentario
  (`attachment_storage.validate`, 10 MB, extensiones permitidas).

**201** (forma existente, sin cambios): agrega `"description_attachments": [{id, filename,
content_type, size_bytes}]` con las imágenes ya persistidas de esa creación (mismas que ahora
referencia inline el HTML de `description`).

**Errores nuevos**: 400 `attachment_error` si alguna imagen de `inline_images` no pasa la
validación (mismo código ya usado hoy en comentarios) — el Ticket **no** se crea si alguna imagen
es inválida (todo o nada, igual que hoy con comentarios).

## GET /api/tickets/{id} — descripción ahora trae sus adjuntos

**200** (forma existente): agrega `"description_attachments": [{id, filename, content_type,
size_bytes}]` — adjuntos de la descripción (independientes de `comments[].attachments`, que
siguen siendo solo los de cada comentario).

## POST /api/tickets/{id}/comments — comentario con imágenes pegadas

**Sin cambios de forma del contrato** (ya aceptaba `multipart/form-data` con `files`, spec 002).
Se agrega el campo opcional `inline_images` (mismo formato/orden que en la creación del Ticket,
ver arriba) — distinto de `files` (adjuntos manuales, sin cambios). `body` ahora puede contener
HTML saneado con imágenes ya referenciadas por su URL real (reescritas server-side antes de
guardar).

**201** (forma existente): sin cambios de forma — `comment.attachments[]` incluye tanto los
adjuntos manuales (`files`) como las imágenes pegadas (`inline_images`), indistinguibles en la
respuesta (ambos son `Attachment` con `comment_id` de ese comentario).

## GET /api/tickets/{id}/attachments/{attachment_id} — mostrar imagen incrustada

**Sin cambios de contrato.** Las imágenes incrustadas en `body`/`description` referencian esta
misma URL de descarga ya existente (spec 002). El frontend nunca la carga como `<img src>`
nativo — siempre vía `apiClient` (autenticado) + blob URL (`RichTextViewer`), así que el
`Content-Disposition` de la respuesta no afecta cómo se muestra.

## POST /api/tickets/{id}/close, /cancel, /status, /resolution — solo texto enriquecido

**Sin cambios de contrato.** Los campos `body`/`comment` de estos cuatro endpoints (ya
existentes, JSON) ahora pueden contener HTML saneado (negrilla/cursiva/listas/hipervínculos) —
mismo saneamiento server-side que el resto, pero **sin** soporte de `inline_images`: no aceptan
`multipart/form-data`. Una imagen pegada en estos formularios se descarta silenciosamente en el
cliente antes de enviar (no se implementa soporte de adjunto para estas superficies, ver
research.md Decisión 2).
