# Quickstart: Corregir el Cliente de un Usuario/cliente y desambiguar Proyectos homónimos

**Feature**: `016-corregir-cliente-encargado`

## Prerrequisitos

- Stack corriendo en Docker (`sywork_db`, `sywork_backend`, `sywork_frontend`).
- Dos Clientes distintos, cada uno con un Proyecto activo (idealmente con **el mismo nombre**,
  ej. "SOPORTE", para probar la desambiguación).
- Un usuario Admin o Coordinador con permiso `client_contacts:manage`.

## Escenario 1 — Corregir un Cliente mal asignado

1. Crear un Usuario/cliente con un Proyecto del Cliente A (el "equivocado" a propósito).
2. Abrir "Gestionar proyectos" y quitar ese Proyecto (queda en 0).
3. Abrir el selector "Agregar proyecto": debe mostrar Proyectos de **cualquier** Cliente
   (incluido el Cliente B), cada uno etiquetado como "Cliente — Proyecto".
4. Agregar un Proyecto del Cliente B. Verificar:
   - La operación responde 201.
   - La columna "Cliente" del Usuario/cliente en la tabla pasa a mostrar el Cliente B.
   - `GET /api/client-contacts?client_id=<Cliente B>` incluye ahora al contacto;
     `?client_id=<Cliente A>` ya no.

## Escenario 2 — La regla de "mismo Cliente" se mantiene con 1+ Proyectos

1. Sobre el Usuario/cliente del Escenario 1 (ahora con 1 Proyecto del Cliente B), intentar
   agregarle un Proyecto del Cliente A.
2. Verificar que se rechaza (400) — la corrección de Cliente solo aplica partiendo de cero.

## Escenario 3 — Desambiguación de Proyectos homónimos

1. Con dos Clientes que tienen cada uno un Proyecto llamado igual (ej. "SOPORTE"), abrir
   "Gestionar proyectos" de un Usuario/cliente sin Proyectos asignados.
2. Verificar que el selector muestra ambos "SOPORTE" diferenciados por Cliente (ej. "Cliente A —
   SOPORTE" y "Cliente B — SOPORTE"), no dos entradas idénticas.

## Escenario 4 — Tickets históricos no se ven afectados

1. Antes de corregir el Cliente (Escenario 1), crear un ticket del Proyecto del Cliente A con
   este Usuario/cliente como solicitante.
2. Corregir el Cliente al Cliente B (Escenario 1).
3. Verificar que el ticket creado en el paso 1 conserva su solicitante y su Proyecto sin cambios.

## Verificación dirigida (Principio VII)

- Backend: `docker exec sywork_backend pytest backend/tests/api/test_client_contacts_projects.py -q`
  (casos nuevos agregados al archivo existente de spec 015). Fixtures limitados a Clientes y
  Proyectos — sin usuarios Resolutor ni disparo de correo (misma restricción que spec 015).
- Frontend: `npx tsc -b` sobre los archivos modificados.
