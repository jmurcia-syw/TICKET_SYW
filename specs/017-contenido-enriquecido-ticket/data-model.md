# Data Model: Contenido enriquecido en comentarios y descripción de Ticket/Tarea

**Feature**: `017-contenido-enriquecido-ticket` · **Date**: 2026-07-14
**Migración**: `backend/infra/migrations/versions/029_attachments_on_tickets.py` (down_revision: `028`)

## Entidades modificadas

### Attachment (tabla `comment_attachments`, sin renombrar)

| Columna | Tipo | Constraints (antes) | Constraints (después) |
|---------|------|----------------------|------------------------|
| `comment_id` | UUID | FK `ticket_comments(id)`, **NOT NULL** | FK `ticket_comments(id)`, **NULL** |
| `ticket_id` | UUID | — (no existía) | **NUEVA**: FK `tickets(id)`, NULL |

Se agrega `CHECK` a nivel de tabla: `ck_attachment_exactly_one_parent` —
`(comment_id IS NOT NULL) <> (ticket_id IS NOT NULL)` (XOR: exactamente uno de los dos, nunca
ambos ni ninguno). Resto de columnas (`filename`, `content_type`, `size_bytes`, `storage_path`,
`created_at`) sin cambios.

Dataclass `Attachment` (`backend/domain/entities/comment.py`): `comment_id` pasa a
`Optional[uuid.UUID] = None` y se agrega `ticket_id: Optional[uuid.UUID] = None` (ambos al final
del dataclass, después de los campos obligatorios, para no romper instanciaciones por posición).

### Comment (`ticket_comments`) — sin cambios de esquema

`body` ya es `TEXT`; ahora contiene HTML saneado en vez de texto plano. Sin migración.

### Ticket (`tickets`) — sin cambios de esquema

`description` ya es `TEXT`; mismo cambio de contenido (HTML saneado). Sin migración.

## Migración `029` — orden de operaciones

1. `ALTER TABLE comment_attachments ALTER COLUMN comment_id DROP NOT NULL`.
2. `ALTER TABLE comment_attachments ADD COLUMN ticket_id UUID NULL REFERENCES tickets(id)`.
3. `ALTER TABLE comment_attachments ADD CONSTRAINT ck_attachment_exactly_one_parent CHECK
   ((comment_id IS NOT NULL) <> (ticket_id IS NOT NULL))`.
4. Índice `ix_comment_attachments_ticket_id` sobre la columna nueva (consistente con el índice ya
   existente sobre `comment_id`, si lo hay).

`downgrade`: eliminar el `CHECK`, la columna `ticket_id` y su índice, y devolver `comment_id` a
`NOT NULL` (solo válido si no quedan filas con `ticket_id` no nulo — el downgrade documenta este
requisito, consistente con el criterio de migraciones previas del proyecto).

## Mecanismo de reescritura de imágenes pegadas (lógica de aplicación, no de esquema)

Ver research.md Decisión 3. Contrato de datos en tránsito (no persistido tal cual):

- El HTML que **llega** del cliente puede contener `<img data-pending-id="0" src="blob:...">`.
- El HTML que se **persiste** en `body`/`description` nunca contiene `data-pending-id` ni URLs
  `blob:` — siempre queda reescrito a `<img src="/api/tickets/{ticket_id}/attachments/{id}
  ?inline=1">` antes de guardar (o sin esa referencia si la imagen se descartó por inválida).

## Invariantes

- Un `Attachment` pertenece exactamente a un Comentario **o** a la descripción de un Ticket/
  Tarea — nunca a ambos (constraint `ck_attachment_exactly_one_parent`).
- Todo HTML persistido en `body`/`description` pasó por saneamiento server-side (`bleach`) antes
  de guardarse — sin excepciones, incluso si llega vía API directa sin pasar por el editor.
- El campo `comment_type` (Principio VI) no se ve afectado por este cambio — sigue siendo un
  valor de `COMMENT_TYPES`, ajeno al contenido enriquecido del `body`.

## Diagrama de relaciones (delta)

```
comment_attachments
  ├── comment_id  (FK ticket_comments.id, NULL)  ─┐
  └── ticket_id   (FK tickets.id, NULL)           ┴── CHECK: exactamente uno de los dos

ticket_comments.body        [TEXT, ahora HTML saneado — sin cambio de esquema]
tickets.description         [TEXT, ahora HTML saneado — sin cambio de esquema]
```
