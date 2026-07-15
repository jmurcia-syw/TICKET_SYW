# Quickstart: Encargado (Usuario/cliente) en múltiples Proyectos

**Feature**: `015-encargado-multiples-proyectos`

## Prerrequisitos

- Stack corriendo en Docker (`sywork_db`, `sywork_backend`, `sywork_frontend`).
- Un Cliente con **2+ Proyectos activos** (usar datos semilla o crear en Maestros).
- Un usuario Admin o Coordinador con permiso `client_contacts:manage`.

## Escenario 1 — Alta con varios Proyectos (US1)

1. Ir a **Usuarios/cliente** → "Nuevo Usuario/cliente".
2. Completar email y username; en el campo Proyecto, seleccionar **2 Proyectos** del mismo
   Cliente (multi-select).
3. Crear. Verificar:
   - La cuenta aparece en la tabla con ambos Proyectos en la columna "Proyectos".
   - `GET /api/client-contacts?project_id=<proyecto-a>` incluye a la cuenta creada.
   - `GET /api/client-contacts?project_id=<proyecto-b>` también la incluye.
4. Al crear un ticket para cualquiera de los dos Proyectos, la cuenta aparece en el selector de
   "Encargado solicitante".

## Escenario 2 — Rechazo por Clientes distintos

1. Repetir el alta seleccionando 2 Proyectos que pertenezcan a **Clientes distintos**.
2. Verificar que el sistema rechaza la operación (400 `validation_error`) y no crea ninguna
   cuenta ni membresía parcial.

## Escenario 3 — Gestión posterior de Proyectos (US2)

1. Sobre un Usuario/cliente ya existente con 1 Proyecto asignado, usar la acción "Gestionar
   proyectos" de su fila.
2. Agregar un segundo Proyecto (del mismo Cliente). Verificar que aparece de inmediato en la
   columna "Proyectos" y que el contacto queda seleccionable en tickets de ese Proyecto.
3. Quitar uno de los dos Proyectos. Verificar:
   - Desaparece de la columna "Proyectos".
   - Ya no aparece como solicitante seleccionable en tickets **nuevos** de ese Proyecto.
   - Un ticket ya existente que lo tenía como solicitante en ese Proyecto **no cambia**
     (`client_contact_id` se conserva).

## Escenario 4 — Compatibilidad con la forma legada

1. Crear un Usuario/cliente usando `client_id` directo (sin `project_ids`), como hoy.
2. Verificar que sigue funcionando sin cambios (0 Proyectos asignados, editable después vía
   "Gestionar proyectos" para agregarle uno).

## Verificación dirigida (Principio VII)

- Backend: `docker exec sywork_backend pytest backend/tests/api/test_client_contacts_projects.py -q`
  (nuevo archivo, tests ultra-limitados: ≤ 5-10 registros por test). Fixtures limitados a
  Clientes y Proyectos ya existentes — **no crear usuarios Resolutor adicionales ni disparar el
  correo de reseteo/reenvío de contraseña**; la contraseña provisional se valida en la respuesta
  JSON del alta, no por email.
- Frontend: `npx tsc -b` (typecheck) sobre los archivos modificados; sin suite E2E nueva.
