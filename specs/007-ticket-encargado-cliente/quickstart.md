# Quickstart: Selección manual del Encargado solicitante en el Ticket

## Prerrequisitos

- Stack levantado: `docker compose up -d` (backend + frontend + Postgres).
- Migración aplicada: `docker exec sywork_backend alembic upgrade head` → `022 (head)`.
- Un Cliente con al menos 2 Encargados registrados (alta vía `/client-contacts`, Fase 2.1) y otro
  Cliente sin ningún Encargado, para probar ambos casos.
- Un usuario Resolutor (sin `client_contacts:manage`) para validar el gap de permiso corregido.

## Validación dirigida

```bash
# Backend: solo los archivos nuevos/tocados por esta funcionalidad
docker exec sywork_backend pytest backend/tests/domain/test_ticket_service_client_contact.py -v
docker exec sywork_backend pytest backend/tests/api/test_tickets_client_contact.py -v

# Frontend: typecheck (no hay suite de tests automatizada en este repo)
cd frontend && npx tsc -b
```

Regresión completa (Fase de Polish, no durante el desarrollo de cada tarea):
```bash
docker exec sywork_backend pytest -q
```

## Escenario 1 (US1) — Asignar Encargado al crear el ticket

1. Como Coordinador (o Resolutor), crear un ticket seleccionando un Cliente con Encargados
   registrados.
2. Confirmar que aparece el campo "Encargado" con la lista de Encargados de ese cliente.
3. Elegir uno, completar el resto del formulario y guardar.
4. Abrir el detalle del ticket → confirmar que muestra a esa persona como "Encargado solicitante"
   (mismo Tag ya usado en Fase 2.1).
5. Repetir el paso 1 con un Cliente sin Encargados registrados → confirmar que el campo aparece
   vacío/deshabilitado con un mensaje claro, y que el ticket se crea igual sin ese dato.

## Escenario 2 (US1, escenario 4) — Encargado autoservicio no cambia

1. Loguearse como un usuario con rol Encargado y crear un ticket (flujo simplificado ya existente).
2. Confirmar que no ve el selector de Encargado (sigue sin cliente ni ese campo en su formulario).
3. Abrir el ticket como Admin → confirmar que "Encargado solicitante" sigue mostrando
   automáticamente a ese mismo usuario, igual que antes de esta funcionalidad.

## Escenario 3 (US2) — Corregir el Encargado después de creado

1. Abrir el detalle de un ticket sin Encargado asignado (creado por personal interno).
2. Editar el campo "Encargado" desde "Clasificación", elegir uno del Cliente del ticket, guardar.
3. Confirmar que el detalle refleja el cambio de inmediato.
4. Cambiarlo por otro Encargado del mismo cliente → confirmar que se actualiza.
5. Intentar lo mismo sobre el ticket del Escenario 2 (creado por un Encargado) → confirmar que el
   campo no es editable (o el intento de PATCH directo devuelve 409 `requester_immutable`).
6. Llevar un ticket a estado Cerrado o Cancelado → confirmar que el campo queda bloqueado
   (`locked_fields` incluye `client_contact_id`).

## Escenario 4 (Edge case) — Cambiar el Cliente limpia el Encargado

1. En un ticket con Encargado asignado, cambiar el Cliente del ticket (si el flujo de edición lo
   permite) a uno distinto.
2. Confirmar que el Encargado previamente asignado deja de mostrarse (queda `null`), no un
   Encargado de otro cliente.

## Escenario 5 (permiso) — Resolutor puede listar Encargados

1. Loguearse como Resolutor (sin `client_contacts:manage`) y crear/editar un ticket.
2. Confirmar que el selector de Encargado carga la lista sin error 403.
3. Confirmar que ese mismo Resolutor sigue sin poder dar de alta un Encargado nuevo desde
   `/client-contacts` (403 en `POST`, sin cambios).

## Escenario 6 (regresión)

1. Confirmar que Cliente y Proyecto del ticket siguen funcionando exactamente igual (creación,
   edición, filtros).
2. Confirmar que la suite completa de backend pasa sin regresión (`pytest -q`).
3. `npx tsc -b` en frontend sin errores.
