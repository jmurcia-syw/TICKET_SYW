# Quickstart: Contenido enriquecido en comentarios y descripción de Ticket/Tarea

**Feature**: `017-contenido-enriquecido-ticket`

## Prerrequisitos

- Stack corriendo en Docker (`sywork_db`, `sywork_backend`, `sywork_frontend`).
- Un Ticket existente para probar comentarios; permiso para crear Tickets nuevos.
- Un correo o documento externo con texto en negrilla, un hipervínculo y una imagen incrustada
  (para probar el pegado con formato), o simplemente una captura de pantalla en el portapapeles.

## Escenario 1 — Formato de texto en un comentario

1. Abrir un Ticket, escribir un comentario, seleccionar texto y aplicar negrilla/cursiva, crear
   una lista y un hipervínculo desde la barra de herramientas del editor.
2. Enviar el comentario. Verificar que se muestra con el mismo formato tras recargar la página.

## Escenario 2 — Formato de texto en la descripción de un Ticket/Tarea

1. Crear un Ticket nuevo, aplicar formato (negrilla, lista, hipervínculo) en el campo
   Descripción.
2. Crear el Ticket. Verificar que el detalle del Ticket muestra la descripción con ese formato.

## Escenario 3 — Pegar contenido con formato e imagen en un comentario

1. Copiar desde un correo o documento externo un párrafo con negrilla, una lista, un
   hipervínculo y una imagen incrustada.
2. Pegarlo en el editor de un comentario. Verificar que aparece con el formato compatible
   conservado y la imagen visible incrustada en el punto donde se pegó (no como bloque de texto
   plano ni como adjunto separado).
3. Enviar el comentario. Verificar que la imagen sigue visible tras recargar, y que aparece
   también listada/descargable como cualquier adjunto.

## Escenario 4 — Pegar una imagen (captura de pantalla) en la descripción de un Ticket nuevo

1. Copiar una captura de pantalla al portapapeles (ej. con la herramienta de recortes del SO).
2. Pegarla directamente en el campo Descripción al crear un Ticket nuevo (antes de guardar).
3. Crear el Ticket. Verificar que la imagen aparece incrustada en la descripción del detalle del
   Ticket, y que `GET /api/tickets/{id}` incluye la imagen en `description_attachments`.

## Escenario 5 — Adjuntar un archivo a la descripción

1. Al crear un Ticket, adjuntar un archivo (no imagen, ej. un PDF) además de escribir la
   descripción.
2. Verificar que el archivo queda listado y descargable en el detalle del Ticket, igual que un
   adjunto de comentario.
3. Repetir con un archivo no permitido o que excede 10MB — verificar que se rechaza con el mismo
   mensaje de error que ya usa el adjunto de comentario, y que el Ticket **no** se crea.

## Escenario 6 — Contenido existente (texto plano) sigue funcionando

1. Abrir un Ticket o comentario creado antes de esta feature (texto plano sin formato).
2. Verificar que se sigue mostrando correctamente, sin errores ni pérdida de contenido, dentro
   del nuevo visor.

## Escenario 7 — Saneamiento de contenido inseguro

1. Intentar pegar o escribir contenido con un `<script>` o un atributo `onclick` (por ejemplo,
   copiando HTML crudo desde las herramientas de desarrollador del navegador).
2. Verificar que el comentario/descripción se guarda sin el script ni el atributo — no se
   ejecuta ningún código al ver el ticket.

## Verificación dirigida (Principio VII)

- Backend: `docker exec sywork_backend pytest tests/api/test_tickets_rich_content.py -q`
  (nuevo archivo, tests ultra-limitados: ≤ 5-10 registros por test). Fixtures acotados al flujo
  (Cliente/Proyecto/Ticket ya existentes) — sin usuarios Resolutor adicionales ni disparo de
  correo (misma restricción de specs 015/016).
- Frontend: `npx tsc -b` sobre los archivos modificados.
