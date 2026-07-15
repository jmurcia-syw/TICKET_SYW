# Implementation Plan: Contenido enriquecido (formato, imágenes pegadas y adjuntos) en comentarios y descripción de Ticket/Tarea

**Branch**: `develp_Jp` (rama de desarrollo actual; el directorio de la spec es
`017-contenido-enriquecido-ticket`) | **Date**: 2026-07-14 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/017-contenido-enriquecido-ticket/spec.md`

## Summary

Los comentarios del ticket ya soportan adjuntos de archivo (spec 002) pero su cuerpo es texto
plano; la descripción del Ticket/Tarea es texto plano sin ningún adjunto. Este plan agrega un
editor de texto enriquecido (negrilla, cursiva, subrayado, listas, hipervínculos) reutilizado en
**todas** las superficies que hoy escriben `Comment.body`/`Ticket.description` (comentario
principal, cerrar, cancelar, cambiar estado, rechazar resolución, crear Ticket/Tarea/Subtarea).
Sobre esa base, las **dos superficies explícitas del pedido** —el comentario principal y la
descripción al crear un Ticket/Tarea— ganan además la capacidad de pegar imágenes incrustadas
respaldadas por adjuntos reales, reutilizando el mecanismo de almacenamiento de adjuntos ya
existente (sin endpoints nuevos de subida). La tabla `comment_attachments` se extiende para
poder anclarse también a un Ticket directamente (su descripción), no solo a un Comentario. Todo
el HTML se sanea en el servidor (Principio IV) antes de persistirse, sin excepciones.

**Directriz estricta**: no se agrega soporte de imágenes pegadas a los formularios secundarios
(cerrar/cancelar/cambiar estado/rechazar resolución) — solo formato de texto ahí, ver
research.md Decisión 2. No se construye una pantalla de edición de descripción (no existe hoy y
no es parte del pedido).

## Technical Context

**Language/Version**: Python 3.12 (backend) · TypeScript strict / React 19 (frontend)

**Primary Dependencies**: Flask 3.x + Flask-RESTX, SQLAlchemy 2.x + Alembic, Ant Design 5 — **+
dependencias nuevas aprobadas en este plan** (Principio V, ver sección dedicada abajo)

**Storage**: PostgreSQL 16 (Docker `sywork_db`), migración `029` (última actual: `028`) —
extiende `comment_attachments`, sin tablas nuevas. Adjuntos siguen en filesystem local
(`uploads/`, ya existente, spec 002)

**Testing**: pytest contra Postgres real en Docker (`docker exec sywork_backend pytest <tests
dirigidos>`), `npx tsc -b` para typecheck frontend. Solo tests dirigidos (Principio VII); un
archivo de test nuevo (`test_tickets_rich_content.py`), sin fixtures de Resolutor ni disparo de
correo (misma restricción de specs 015/016)

**Target Platform**: Docker Compose on-premise (`sywork_db`/`sywork_backend`/`sywork_frontend`)

**Project Type**: Web application (backend Flask 3 capas + frontend React SPA)

**Performance Goals**: sin cambios relevantes — el saneamiento HTML (`bleach`/`lxml`) opera sobre
strings de tamaño acotado (comentario/descripción individual), no sobre volúmenes grandes

**Constraints**: alcance mínimo (Directriz estricta arriba); compatibilidad total con contenido
existente (texto plano se sigue mostrando sin migración, spec FR-009); saneamiento server-side
obligatorio sin excepciones (spec FR-006); mismos límites de tamaño/tipo de archivo ya vigentes
para adjuntos (spec 002)

**Scale/Scope**: 1 migración (extiende 1 tabla), 2 componentes frontend nuevos (editor/visor)
reutilizados en ~10 puntos de uso, 1 endpoint extendido a multipart (`POST /api/tickets`), 1
endpoint con parámetro nuevo (`?inline=1`), saneamiento centralizado en 1 helper de dominio

## Dependencias nuevas (aprobación Principio V — documentada en este plan de fase)

| Dependencia | Capa | Para qué | Alternativas evaluadas |
|---|---|---|---|
| `@tiptap/react`, `@tiptap/pm`, `@tiptap/starter-kit`, `@tiptap/extension-underline`, `@tiptap/extension-link`, `@tiptap/extension-image` | Frontend | Editor de texto enriquecido (negrilla/cursiva/listas/links/imágenes), manejo de paste configurable | `react-quill` (soporte inestable en React 19 strict mode), `Slate`/`Draft.js` (headless, más esfuerzo de construcción), `Lexical` (menos maduro en extensiones de imagen/paste-cleanup) — ver research.md Decisión 6 |
| `dompurify`, `@types/dompurify` | Frontend | Saneamiento de HTML pegado en el cliente (primera línea, UX) antes de insertarlo en el editor | Ninguna evaluada — es el estándar de facto para sanear HTML en el navegador |
| `bleach` | Backend | Saneamiento de HTML server-side (línea autoritativa, Principio IV) antes de persistir `body`/`description` | Sanear a mano con regex (rechazada: frágil e insegura para HTML) |
| `lxml` | Backend | Parseo/reescritura robusta de HTML real (reemplazar `data-pending-id` por URLs de adjunto reales antes de sanear) | Regex puro (rechazada: el orden de atributos HTML no está garantizado) |

Ninguna reemplaza stack ya aprobado; todas atacan una necesidad que el stack actual no cubre
(no había ningún editor de texto enriquecido ni sanitizador HTML en el proyecto).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Evaluación | Estado |
|-----------|------------|--------|
| I. API-First y Dominio Primero | Saneamiento y "¿está vacío?" viven en un helper de dominio reutilizado por `comment_service` y la validación de creación de Ticket; contrato documentado en `contracts/` antes de tocar rutas | ✅ |
| II. Clean Architecture 3 capas | Sin lógica de negocio en componentes React (el editor es presentación pura); reescritura de `data-pending-id` y saneamiento viven en la ruta orquestando un helper de dominio + `attachment_storage` (infra) ya existente | ✅ |
| III. Tipado estricto | Componentes `RichTextEditor`/`RichTextViewer` tipados sin `any`; `Attachment` con `Optional[uuid.UUID]` explícito en Python | ✅ |
| IV. Seguridad en profundidad | Saneamiento server-side obligatorio (`bleach`) en TODO punto de persistencia de `body`/`description`, sin depender del cliente; mismos permisos ya vigentes (`tickets:transition`, `tickets:view`) sin cambios | ✅ |
| V. Zero dependencias no aprobadas | 4 dependencias nuevas **aprobadas explícitamente en este documento de planificación** (tabla arriba), con alternativas evaluadas — cumple el proceso de gobernanza, no lo evade | ✅ |
| VI. AI-Native | El `comment_type` estructurado no cambia de naturaleza (research.md Decisión 1) — el Gold Standard Dataset sigue basado en datos estructurados, el enriquecimiento es solo del `body` de texto libre que ya era de tipo libre | ✅ |
| VII. Alcance de sesión / testing ultra-limitado | Alcance explícitamente acotado (Directriz estricta); 1 archivo de test nuevo, dirigido, ≤10 registros por caso | ✅ |

Sin violaciones no justificadas — las 4 dependencias nuevas quedan documentadas y justificadas en
la tabla de arriba, cumpliendo el requisito de aprobación de Principio V (no es una excepción,
es el mecanismo de aprobación funcionando).

**Re-check post-diseño (Phase 1)**: sin cambios — el diseño (research.md, data-model.md,
contracts/) no agrega dependencias más allá de las 4 ya aprobadas, ni mueve lógica fuera del
dominio/infra ya establecidos. ✅

## Project Structure

### Documentation (this feature)

```text
specs/017-contenido-enriquecido-ticket/
├── plan.md              # Este archivo
├── research.md          # Phase 0 — decisiones y alternativas
├── data-model.md        # Phase 1 — migración 029, invariantes
├── quickstart.md        # Phase 1 — guía de validación end-to-end
├── contracts/
│   └── tickets-rich-content.md  # Phase 1 — contrato de API (delta)
├── checklists/requirements.md
└── tasks.md              # Phase 2 — /speckit-tasks (no lo crea /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── domain/
│   ├── entities/
│   │   └── comment.py                    # MODIFICADO: Attachment += ticket_id (Optional)
│   └── services/
│       ├── comment_service.py            # MODIFICADO: validate() usa strip_html() para "vacío"
│       └── rich_content_service.py       # NUEVO: strip_html(), sanitize_html(), resolve_pending_images()
├── infra/
│   ├── migrations/versions/
│   │   └── 029_attachments_on_tickets.py # NUEVA
│   ├── models/
│   │   └── comment_model.py              # MODIFICADO: AttachmentModel += ticket_id, CHECK
│   └── repositories/
│       └── comment_repo.py               # MODIFICADO: add_attachment pasa ticket_id;
│                                          #   += list_ticket_attachments(ticket_id)
├── api/routes/
│   └── tickets.py                        # MODIFICADO: POST /tickets acepta multipart +
│                                          #   inline_images; POST /tickets/{id}/comments +=
│                                          #   inline_images; GET .../attachments/{id} += ?inline=1;
│                                          #   _ticket_detail += description_attachments;
│                                          #   sanitize_html() en description/body antes de guardar
└── tests/
    └── api/test_tickets_rich_content.py  # NUEVO (dirigido, ≤10 registros/test)

frontend/
├── package.json                          # MODIFICADO: += dependencias de la tabla de arriba
└── src/
    ├── components/tickets/
    │   ├── RichTextEditor.tsx            # NUEVO: wrapper TipTap, toolbar, paste-clean, allowImages
    │   ├── RichTextViewer.tsx            # NUEVO: render saneado (DOMPurify) de HTML guardado
    │   ├── CommentComposer.tsx           # MODIFICADO: 4 TextArea → RichTextEditor
    │   │                                 #   (2 con allowImages, 2 sin)
    │   ├── CommentThread.tsx             # MODIFICADO: <Text>{body}</Text> → RichTextViewer
    │   ├── SubtaskList.tsx               # MODIFICADO: TextArea descripción → RichTextEditor
    │   └── TaskStatusChanger.tsx         # MODIFICADO: TextArea → RichTextEditor (sin imágenes)
    ├── pages/
    │   ├── TicketsPage.tsx               # MODIFICADO: TextArea descripción → RichTextEditor
    │   │                                 #   (con imágenes); create() envía multipart si hay
    │   │                                 #   imágenes pendientes
    │   ├── TicketDetailPage.tsx          # MODIFICADO: <p>{description}</p> → RichTextViewer
    │   └── KanbanPage.tsx                # MODIFICADO: 3 TextArea → RichTextEditor (sin imágenes)
    ├── services/
    │   └── ticketService.ts              # MODIFICADO: create() acepta imágenes pendientes
    │                                     #   (multipart); addComment() += inline_images
    └── types/
        └── ticket.ts                     # MODIFICADO: TicketDetail += description_attachments
```

**Structure Decision**: web application existente (backend 3 capas + SPA React). El único
componente de UI genuinamente nuevo es el editor/visor de texto enriquecido (2 archivos); el
resto son swaps de `Input.TextArea` por ese componente en los puntos ya identificados en
research.md Decisión 2, sin páginas nuevas.

## Complexity Tracking

> Fill ONLY if Constitution Check has violations that must be justified

Sin violaciones a la Constitución — las dependencias nuevas están aprobadas y justificadas en la
sección dedicada arriba, no en esta tabla (esa sección **es** el mecanismo de aprobación que pide
Principio V, no una excepción a él).
