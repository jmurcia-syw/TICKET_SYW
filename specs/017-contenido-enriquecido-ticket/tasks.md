# Tasks: Contenido enriquecido (formato, imágenes pegadas y adjuntos) en comentarios y descripción de Ticket/Tarea

**Input**: Design documents from `specs/017-contenido-enriquecido-ticket/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: incluidos y **dirigidos** (Principio VII): un solo archivo de test nuevo
(`backend/tests/api/test_tickets_rich_content.py`), ≤10 registros por caso.

**Restricción de alcance en pruebas/fixtures** (misma directriz de specs 015/016): fixtures
limitados a los maestros que participan del flujo (Cliente/Proyecto/Ticket ya existentes o
creados mínimamente). Prohibido crear usuarios Resolutor adicionales como fixture o disparar el
flujo de correo de contraseña.

**Organización**: tareas agrupadas por User Story. Orden de ejecución: US1 (P1, formato de
texto) → US2 (P1, pegar contenido con formato + imágenes) → US3 (P2, adjuntar archivos a la
descripción). US2 y US3 comparten la migración y el mecanismo de adjuntos-en-ticket de la fase
Foundational.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: paralelizable (archivos distintos, sin dependencias incompletas)
- **[Story]**: [US1] formato de texto, [US2] pegar contenido/imágenes, [US3] adjuntar archivos a
  la descripción

---

## Phase 1: Setup

- [X] T001 Agregar `bleach` y `lxml` a `backend/requirements.txt` (saneamiento HTML server-side
  y reescritura de `data-pending-id` — research.md Decisión 6/7) y reconstruir la imagen
  `sywork_backend`
- [X] T002 [P] Agregar `@tiptap/react`, `@tiptap/pm`, `@tiptap/starter-kit`,
  `@tiptap/extension-underline`, `@tiptap/extension-link`, `@tiptap/extension-image`,
  `dompurify` a `frontend/package.json` (research.md Decisión 6/7) — instalado vía `pnpm add`
  en `sywork_frontend`, versión resuelta TipTap v3.27.4 (`@types/dompurify` omitido: dompurify
  v3 ya trae sus propios tipos TS, el paquete `@types/*` está deprecado)

**Checkpoint**: dependencias nuevas instaladas y aprobadas (plan.md, tabla de Principio V).

---

## Phase 2: Foundational (bloqueante para US1, US2 y US3)

**Nota**: el saneamiento HTML y el editor/visor son compartidos por las 3 historias — nada es
usable sin esta fase.

- [X] T003 Migración `backend/infra/migrations/versions/029_attachments_on_tickets.py`
  (down_revision `028`): `ALTER TABLE comment_attachments ALTER COLUMN comment_id DROP NOT
  NULL`; `ADD COLUMN ticket_id UUID NULL REFERENCES tickets(id)`; `ADD CONSTRAINT
  ck_attachment_exactly_one_parent CHECK ((comment_id IS NOT NULL) <> (ticket_id IS NOT
  NULL))`; índice `ix_comment_attachments_ticket_id`. `downgrade` completo (depende de T001)
- [X] T004 [P] `backend/domain/entities/comment.py`: `Attachment` — `comment_id` pasa a
  `Optional[uuid.UUID] = None`, se agrega `ticket_id: Optional[uuid.UUID] = None` (ambos al
  final del dataclass, después de los campos obligatorios) (depende de T003)
- [X] T005 `backend/infra/models/comment_model.py`: `AttachmentModel` += columna `ticket_id`
  (FK `tickets.id`, nullable) + `CheckConstraint` `ck_attachment_exactly_one_parent`;
  `to_entity()`/`from_entity()` incluyen `ticket_id` (depende de T004)
- [X] T006 `backend/infra/repositories/comment_repo.py`: `add_attachment()` pasa también
  `ticket_id=attachment.ticket_id` al `AttachmentModel`; += método
  `list_ticket_attachments(ticket_id: uuid.UUID) -> list[Attachment]` (filtra
  `AttachmentModel.ticket_id == ticket_id`) (depende de T005)
- [X] T007 [P] `backend/domain/services/rich_content_service.py` nuevo:
  `strip_html(html: str) -> str` (despoja tags vía `bleach.clean(html, tags=[], strip=True)`,
  para el chequeo de "vacío"); `sanitize_html(html: str) -> str` (lista blanca `p, br, strong,
  b, em, i, u, a, ul, ol, li, img, blockquote` / atributos `href, target, rel, src, alt`);
  `resolve_pending_images(html: str, id_by_index: dict[int, str], base_url: str) -> str`
  (parsea con `lxml.html`, por cada `<img data-pending-id="N">` fija `src` a
  `f"{base_url}/{id_by_index[N]}?inline=1"` y elimina el atributo `data-pending-id`, serializa
  de vuelta a string) (depende de T001)
- [X] T008 `backend/domain/services/comment_service.py`: `validate()` cambia
  `if not (body or "").strip()` por `if not strip_html(body or "").strip()` (importa de
  `rich_content_service`) (depende de T007)
- [X] T009 [P] `frontend/src/components/tickets/RichTextEditor.tsx` nuevo: wrapper de TipTap
  (incluye ya el manejo de paste/drop de imágenes de T024 — mismo componente, se activa con
  `allowImages`)
  (`useEditor` con `StarterKit`, `Underline`, `Link`, `Image`), toolbar básica (negrilla,
  cursiva, subrayado, lista, hipervínculo), `transformPastedHTML` que pasa el HTML pegado por
  `DOMPurify.sanitize()` antes de insertarlo; props `value: string`, `onChange: (html: string)
  => void`, `allowImages?: boolean` (default `false`), `onPendingImage?: (file: File) => number`
  (si `allowImages`, en paste/drop de una imagen genera una URL `blob:` local, inserta `<img
  data-pending-id="{index}">` y llama `onPendingImage` para que el padre acumule el archivo)
  (depende de T002)
- [X] T010 [P] `frontend/src/components/tickets/RichTextViewer.tsx` nuevo: componente que
  renderiza `DOMPurify.sanitize(html)` vía `dangerouslySetInnerHTML`, con estilos básicos para
  `p, ul, ol, a, img, strong, em, u` (depende de T002)

**Checkpoint**: migración aplicada, saneamiento de dominio y componentes de editor/visor listos
— las 3 historias pueden arrancar.

---

## Phase 3: User Story 1 — Dar formato al texto en comentarios y descripción (Priority: P1) 🎯 MVP

**Goal**: negrilla, cursiva, subrayado, listas e hipervínculos disponibles (y saneados) en todas
las superficies que hoy escriben `Comment.body`/`Ticket.description`.

**Independent Test**: Escenarios 1, 2, 6 y 7 del quickstart.

### Implementation for User Story 1

- [X] T011 [US1] `backend/api/routes/tickets.py`: `sanitize_html()` (de
  `rich_content_service`) aplicado antes de persistir en `TicketComments.post` (`body`),
  `TicketClose.post`, `TicketCancel.post`, `TicketStatusChange.patch`, `TicketResolution.post`
  (todos `body`), `TicketList.post` (`description`) y `TicketDetail.patch` (si `"description"`
  viene en `clean`) (depende de T007)
- [X] T012 [P] [US1] `frontend/src/components/tickets/CommentComposer.tsx`: los 4
  `Input.TextArea` (comentario principal ×2 variantes, `closeBody`, `cancelBody`) →
  `RichTextEditor` con `allowImages={false}` (se habilita para el principal en US2/T025)
  (depende de T009)
- [X] T013 [P] [US1] `frontend/src/components/tickets/CommentThread.tsx`:
  `<Text>{c.body}</Text>` → `<RichTextViewer html={c.body} />` (depende de T010)
- [X] T014 [P] [US1] `frontend/src/components/tickets/SubtaskList.tsx`: `Input.TextArea` de
  descripción → `RichTextEditor` (`allowImages={false}`) (depende de T009)
- [X] T015 [P] [US1] `frontend/src/components/tickets/TaskStatusChanger.tsx`: `Input.TextArea`
  → `RichTextEditor` (`allowImages={false}`) (depende de T009)
- [X] T016 [P] [US1] `frontend/src/pages/TicketsPage.tsx`: `Input.TextArea` de descripción →
  `RichTextEditor` (`allowImages={false}` por ahora; se habilita en US2/T027) (depende de T009)
- [X] T017 [P] [US1] `frontend/src/pages/TicketDetailPage.tsx`: `<p style="white-space:
  pre-wrap">{ticket.description}</p>` → `<RichTextViewer html={ticket.description} />` (depende
  de T010)
- [X] T018 [P] [US1] `frontend/src/pages/KanbanPage.tsx`: los 3 `Input.TextArea`
  (`commentBody`, `taskStatusBody`, `resolutionBody`) → `RichTextEditor` (`allowImages={false}`)
  (depende de T009)
- [X] T019 [US1] `backend/tests/api/test_tickets_rich_content.py` nuevo (dirigido, ≤10
  registros, sin Resolutor ni correo): comentario con `<p><strong>negrilla</strong> <a
  href="https://example.com">link</a></p>` → 201, `body` sanitizado conserva `strong`/`a`;
  comentario "vacío" `<p><br></p>` → 400 `validation_error`; body con `<script>` u
  `onclick="..."` → se guarda sin el script/atributo; Ticket con `description` con formato →
  201, `description` sanitizada conservando el formato permitido. Correr solo este archivo:
  `docker exec sywork_backend pytest tests/api/test_tickets_rich_content.py -v` (depende de
  T011)

**Checkpoint US1**: Escenarios 1, 2, 6 y 7 del quickstart ejecutables end-to-end.

---

## Phase 4: User Story 2 — Pegar contenido con formato e imágenes (Priority: P1)

**Goal**: pegar texto con formato (de un correo, Word, una web) e imágenes incrustadas en el
comentario principal o en la descripción al crear un Ticket/Tarea, respaldadas por adjuntos
reales.

**Independent Test**: Escenarios 3 y 4 del quickstart.

### Implementation for User Story 2

- [X] T020 [US2] `backend/api/routes/tickets.py`, `TicketComments.post`: además de `files`, lee
  `request.files.getlist("inline_images")`; para cada una, valida
  (`attachment_storage.validate`), la guarda (`attachment_storage.save`) y genera su
  `attachment_id = uuid.uuid4()` **antes** de crear el `Comment` (sin este orden no hay ID para
  reescribir); construye `id_by_index` y llama `resolve_pending_images(body, id_by_index,
  f"/api/tickets/{ticket.id}/attachments")` para obtener el `body` final; crea el `Comment` con
  ese `body` ya reescrito, y luego una fila `Attachment` por imagen (con el `id` pre-generado y
  `comment_id` del comentario recién creado) (depende de T006, T007, T011)
- [X] T021 [US2] `backend/api/routes/tickets.py`, `TicketList.post`: acepta también
  (también deja listo el campo `attachments` de T031/US3 en el mismo pase, backend completo)
  `multipart/form-data` (mismo patrón de detección que `TicketComments.post`: campos de
  formulario en vez de JSON) además de `application/json`; si vienen `inline_images`, mismo
  flujo que T020 pero generando primero `ticket.id = uuid.uuid4()` (ya se genera antes de
  construir el `Ticket`, reordenar si hace falta) para poder resolver las URLs antes del
  `TicketRepository(db).create(ticket)`, y crear las filas `Attachment` con `ticket_id` (no
  `comment_id`) tras crear el Ticket (depende de T020, mismo archivo)
- [X] T022 [US2] ~~`backend/api/routes/tickets.py`, `TicketAttachment.get` += `?inline=1`~~ —
  **superado durante la implementación**: el JWT viaja por header (`Authorization: Bearer`), no
  por cookie, así que un `<img src>` nativo nunca autenticaría la descarga sin importar
  `Content-Disposition`. `RichTextViewer` (T010) ya resuelve esto pidiendo la imagen vía
  `apiClient` y mostrándola como blob URL — sin cambios de backend necesarios. Ver
  contracts/tickets-rich-content.md y research.md Decisión 5 (actualizados)
- [X] T023 [US2] `backend/api/routes/tickets.py`, `_ticket_detail()`: += `"description_attachments":
  [{"id": str(a.id), "filename": a.filename, "content_type": a.content_type, "size_bytes":
  a.size_bytes} for a in CommentRepository(db).list_ticket_attachments(ticket.id)]` (depende de
  T006; mismo archivo que T020-T022, aplicar tras esas ediciones)
- [X] T024 [US2] (ya implementado en T009 — mismo componente)
  `frontend/src/components/tickets/RichTextEditor.tsx`: implementar el
  handler de paste/drop de imagen cuando `allowImages` es `true` (crear `blob:` URL local,
  insertar `<img data-pending-id="{index}" src="{blobUrl}">`, invocar `onPendingImage(file)`)
  (depende de T009)
- [X] T025 [US2] `frontend/src/components/tickets/CommentComposer.tsx`: el comentario principal
  (ambas variantes) pasa a `allowImages={true}`; `send()` arma `FormData` con `inline_images`
  cuando hay imágenes pendientes acumuladas (mismo patrón que ya usa `files`) (depende de T012,
  T024)
- [X] T026 [US2] `frontend/src/services/ticketService.ts`: `addComment()` acepta un parámetro
  opcional de imágenes pendientes y las agrega al `FormData` bajo `inline_images` (depende de
  T025, mismo archivo)
- [X] T027 [US2] `frontend/src/pages/TicketsPage.tsx`: la descripción pasa a
  `allowImages={true}`; `handleCreate()` arma `multipart/form-data` (en vez de JSON) cuando hay
  imágenes pendientes, incluyendo `inline_images` (depende de T016, T024)
- [X] T028 [US2] `frontend/src/services/ticketService.ts`: `create()` soporta el modo multipart
  con `inline_images` cuando corresponde (depende de T026, mismo archivo)
- [X] T029 [P] [US2] `frontend/src/types/ticket.ts`: `TicketDetail` += `description_attachments:
  ContactProjectRef[]`-like `{id, filename, content_type, size_bytes}[]` (depende de T023) —
  implementado reusando la interfaz `TicketAttachment` ya existente; además se cableó la
  visualización en `TicketDetailPage.tsx` (lista de adjuntos descargables bajo la descripción,
  mismo patrón que `CommentThread.tsx`)
- [X] T030 [US2] `backend/tests/api/test_tickets_rich_content.py` += (mismos fixtures, sin
  Resolutor ni correo): comentario multipart con `inline_images=[imagen]` y `body` con
  `<img data-pending-id="0">` → 201, `body` devuelto ya con la URL real, adjunto creado con
  `comment_id`; Ticket multipart con `inline_images` en la descripción → 201,
  `description_attachments` con 1 item y `description` reescrita; imagen inválida en
  `inline_images` → 400 `attachment_error`, nada se crea. ~~`GET .../attachments/{id}?inline=1`~~
  — chequeo eliminado: el parámetro `?inline=1` fue superado en T022 (el visor usa blob-fetch
  autenticado, no `Content-Disposition`), no queda comportamiento nuevo que probar ahí. Correr
  solo este archivo (depende de T021, T022, T023)
  **Bug real detectado y corregido al escribir el test**: en `TicketComments.post` y
  `TicketList.post`, `sanitize_html()` se aplicaba ANTES de `resolve_pending_images()` — como
  `data-pending-id` no está en la lista blanca de atributos de `sanitize_html`, quedaba
  despojado antes de poder resolverse a la URL real, dejando un `<img>` sin `src`. Se invirtió
  el orden en ambos endpoints (`resolve_pending_images` primero sobre el HTML crudo, luego
  `sanitize_html` sobre el resultado ya reescrito) — sin este fix, pegar una imagen en un
  comentario o descripción nunca habría persistido correctamente en producción. Verificado con
  `pytest tests/api/test_lifecycle.py` (7 passed) sin regresiones tras el cambio.

**Checkpoint US2**: Escenarios 3 y 4 del quickstart ejecutables end-to-end.

---

## Phase 5: User Story 3 — Adjuntar archivos a la descripción del Ticket/Tarea (Priority: P2)

**Goal**: adjuntar un archivo (no necesariamente imagen) a la descripción al crear un Ticket/
Tarea, con las mismas reglas ya vigentes para adjuntos de comentario.

**Independent Test**: Escenario 5 del quickstart.

### Implementation for User Story 3

- [X] T031 [US3] `backend/api/routes/tickets.py`, `TicketList.post`: además de `inline_images`,
  lee `request.files.getlist("attachments")` (archivos manuales, sin referencia en el HTML);
  mismo flujo de validar/guardar/crear `Attachment` con `ticket_id`, sin pasar por
  `resolve_pending_images` (depende de T021) — ya implementado como parte del pase combinado de
  T021; confirmado con T034
- [X] T032 [P] [US3] `frontend/src/pages/TicketsPage.tsx`: botón "Adjuntar" (`Upload`, mismo
  patrón que `CommentComposer.tsx`) junto al editor de descripción; `handleCreate()` agrega esos
  archivos al `FormData` bajo `attachments` (fuerza modo multipart aunque no haya imágenes
  pegadas) (depende de T027) — ya implementado como parte del pase combinado de T027
  (`descriptionAttachments: UploadFile[]` + `<Upload>` bajo "Adjuntos de la descripción")
- [X] T033 [US3] `frontend/src/services/ticketService.ts`: `create()` soporta el campo
  `attachments` adicional en el modo multipart (depende de T028, mismo archivo) — ya
  implementado como parte del pase combinado de T028
- [X] T034 [US3] `backend/tests/api/test_tickets_rich_content.py` += : Ticket con `attachments`
  (un archivo no-imagen, ej. `.pdf`) → 201, listado en `description_attachments`, descargable
  vía `GET .../attachments/{id}`; archivo no permitido o > 10MB en `attachments` → 400
  `attachment_error`, el Ticket no se crea. Correr solo este archivo (depende de T031) —
  `test_ticket_multipart_with_manual_attachment` y
  `test_ticket_multipart_manual_attachment_type_not_allowed`, ambos en verde

**Checkpoint US3**: Escenario 5 del quickstart ejecutable end-to-end.

---

## Phase 6: Polish y validación transversal

- [X] T035 [P] Swagger revisado contra `contracts/tickets-rich-content.md`: `POST /api/tickets`
  documenta el modo multipart y `inline_images`/`attachments`; `GET .../attachments/{id}`
  documenta `?inline=1`; `_ticket_detail` documenta `description_attachments` — verificado vía
  `docker exec sywork_backend python3 -c "..."` contra `/swagger.json`: descripciones de
  `POST /api/tickets` y `POST /api/tickets/{ticket_id}/comments` mencionan `multipart/form-data`,
  `inline_images` y `attachments`; `TicketDetail.description_attachments` presente en
  `definitions` apuntando a `CommentAttachment`. `?inline=1` ya no aplica (superado en T022, ver
  nota en T030) — no se documenta porque no existe ese comportamiento
- [X] T036 Ejecutar `quickstart.md` (Escenarios 1-7) contra Docker real — verificado vía Browser
  pane contra `sywork_backend`/`sywork_frontend` reales (login admin@sywork.net):
  - Escenario 1/2/6: formato (negrilla + lista) aplicado y persistido correctamente en la
    descripción de un Ticket nuevo (verificado en vivo en el modal "Nuevo ticket") y en
    TK-000194/TK-000186 (creados por los tests dirigidos, formato `<em>`/`<ul><li>` visible en
    el detalle)
  - Escenario 3/4: TK-000196 (imagen pegada en la descripción) — adjunto real listado y
    **bug real encontrado y corregido**: `RichTextViewer.tsx` pasaba `dangerouslySetInnerHTML=
    {{ __html: clean }}` como objeto literal nuevo en cada render; React diferencia esa prop por
    referencia de objeto (no por el valor de `__html`), así que cualquier re-render de la página
    (el timer de "Sesión de trabajo" cambia de estado cada segundo) pisaba el `innerHTML` y
    destruía el swap a blob URL hecho por el efecto — la imagen quedaba con el `src` crudo
    `/api/tickets/.../attachments/...` (que un `<img>` nativo no puede autenticar, 401) unos
    instantes después de cargar. Corregido memoizando `htmlProp` con `useMemo(() => ({ __html:
    clean }), [clean])`. Verificado tras el fix: el `src` permanece en `blob:...` incluso después
    de 4+ segundos (varios ciclos del timer)
  - Escenario 5: TK-000198 (adjunto manual) — "manual.pdf (0 KB)" listado y descargable bajo la
    descripción
  - Escenario 7: cubierto por `test_comment_strips_script_and_event_handler` (backend) — sin
    verificación adicional de navegador necesaria (no hay superficie donde ejecutar script
    inyectado si el saneamiento server-side ya lo elimina)
  - Escenario 1 (comentario): comentario de texto plano enviado y mostrado vía `RichTextViewer`
    en `CommentThread` (round-trip POST 201 → GET → render confirmado en vivo en TK-000198); el
    formato negrilla/lista del mismo `RichTextEditor`/toolbar ya se había confirmado funcionando
    en el modal "Nuevo ticket" en este mismo pase
- [X] T037 Validación dirigida de cierre (NUNCA la suite completa — Principio VII): `docker exec
  sywork_backend pytest tests/api/test_tickets_rich_content.py tests/api/test_lifecycle.py -q` →
  17 passed; `docker exec sywork_frontend npx tsc -b` → sin errores (ambos corridos después del
  fix de `RichTextViewer.tsx` de T036)

**Checkpoint Final**: quickstart completo en verde y tests dirigidos en verde.

---

## Dependencies & Execution Order

```
Phase 1 (T001 → T002[P])
→ Phase 2 (T003 → T004[P] → T005 → T006; T007[P] → T008; T009[P], T010[P])
→ Phase 3/US1 (T011 → T019; T012..T018[P] en paralelo entre sí)
→ Phase 4/US2 (T020 → T021 → T022 → T023 → T030; T024 → T025 → T026; T027 → T028; T029[P])
→ Phase 5/US3 (T031 → T034; T032 → T033)
→ Phase 6 (T035[P], T036, T037)
```

- US2 y US3 comparten `backend/api/routes/tickets.py` (T020-T023 antes que T031) y
  `frontend/src/pages/TicketsPage.tsx`/`ticketService.ts` (T027-T028 antes que T032-T033) —
  dependencia de archivo, no de dominio: US3 reutiliza el modo multipart que US2 ya deja
  construido en `TicketList.post`.
- US1 es funcionalmente completa sin US2/US3 (formato de texto en todas las superficies, sin
  imágenes ni adjuntos nuevos) — es el MVP.
- Dentro de US1, T012 a T018 tocan archivos distintos entre sí y pueden hacerse en paralelo tras
  T009/T010.

## Parallel Example: Foundational

```bash
# En paralelo tras T001/T002:
Task: "rich_content_service.py (strip_html/sanitize_html/resolve_pending_images)"  # T007
Task: "RichTextEditor.tsx"                                                          # T009
Task: "RichTextViewer.tsx"                                                          # T010
```

## Parallel Example: User Story 1

```bash
# En paralelo tras T009/T010 (archivos todos distintos):
Task: "CommentComposer.tsx → RichTextEditor"      # T012
Task: "CommentThread.tsx → RichTextViewer"        # T013
Task: "SubtaskList.tsx → RichTextEditor"          # T014
Task: "TaskStatusChanger.tsx → RichTextEditor"    # T015
Task: "TicketsPage.tsx descripción → RichTextEditor"  # T016
Task: "TicketDetailPage.tsx → RichTextViewer"     # T017
Task: "KanbanPage.tsx → RichTextEditor (x3)"      # T018
```

---

## Implementation Strategy

1. **MVP = Phase 1 + Phase 2 + US1** (formato de texto en todas las superficies, saneado
   server-side) — resuelve la mitad del pedido (negrillas/hipervínculos/listas) sin la
   complejidad de imágenes/adjuntos.
2. Incremento 1: US2 (pegar contenido con formato + imágenes incrustadas en comentario y
   descripción) — el pedido más explícito del usuario ("copiar y pegar imágenes... correos
   completos").
3. Incremento 2: US3 (adjuntar archivos a la descripción) — paridad con lo que ya existía en
   comentarios desde spec 002, menor urgencia.
4. Riesgo concentrado en T020/T021 (orquestación de multipart + reescritura de HTML antes de
   persistir) — validar con Escenario 3/4 del quickstart sobre datos reales antes de avanzar a
   US3.

## Notes

- [P] = archivos distintos, sin dependencias incompletas
- Commitear después de cada tarea o grupo lógico
- Detenerse en cada checkpoint para validar la story de forma independiente
- **Directriz estricta**: no agregar soporte de `inline_images` a los formularios secundarios
  (cerrar/cancelar/cambiar estado/rechazar resolución) — solo formato de texto ahí (research.md
  Decisión 2); no construir una pantalla de edición de descripción (no existe hoy)
