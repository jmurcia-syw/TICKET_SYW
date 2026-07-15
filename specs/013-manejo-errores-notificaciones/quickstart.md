# Quickstart: Validación — Manejo Global de Errores y Notificaciones

**Feature**: 013-manejo-errores-notificaciones

## Prerrequisitos

- Stack levantado con Docker: `docker compose up -d` (verificar antes con `docker ps`).
- Frontend dev server: `pnpm dev` en `frontend/` (o el contenedor correspondiente).
- Credenciales semilla: ver `docs/credenciales_dev.txt`.
- Contrato de referencia: [contracts/error-contract.md](./contracts/error-contract.md).

## Validación 1 — Contrato backend (sin UI)

Con un token válido (login vía `POST /api/auth/login`):

```bash
# 404: proyecto inexistente → estructura estándar
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:5000/api/projects/00000000-0000-0000-0000-000000000000
# Esperado: status 404, cuerpo con "success": false, "message", "code": "NOT_FOUND" (o específico)

# 403: usuario sin permiso (usar token de un rol sin el permiso del endpoint)
curl -s -H "Authorization: Bearer $TOKEN_SIN_PERMISO" -X DELETE \
  http://localhost:5000/api/clients/<id-existente>
# Esperado: status 403, "code": "FORBIDDEN" (o específico), mensaje entendible

# 400: validación de negocio (p. ej. payload inválido en creación de ticket)
# Esperado: status 400, estructura estándar

# 500 controlado: forzar una excepción (solo en dev) y verificar que el cuerpo
# NO contiene stack trace ni texto de la excepción, solo mensaje genérico.
```

Test unitario específico (único comando de pruebas permitido — Principio VII):

```bash
docker exec sywork_backend pytest tests/api/test_error_contract.py -v
```

Esperado: todos los casos pasan; el archivo usa ≤ 5-10 mocks/casos simulados.

## Validación 2 — Notificación visual (UI, casos críticos)

Escenarios en el navegador (usuario autenticado):

1. **Ticket no asignado al proyecto**: provocar la operación que relaciona un ticket con un
   proyecto al que no pertenece → toast de error inmediato con el mensaje específico del
   servidor (p. ej. "El ticket no está asignado a este proyecto").
2. **Usuario sin permisos**: con un rol limitado (p. ej. Resolutor), intentar una acción
   restringida (p. ej. editar skills del ticket, restringido a Coordinador/QM/Admin) →
   toast con el mensaje de permiso denegado. La pantalla no queda congelada.
3. **Proyecto no encontrado**: navegar/operar sobre un proyecto eliminado o con ID inválido →
   toast "proyecto no encontrado" (mensaje del servidor).

## Validación 3 — Fallback genérico y casos borde

1. **Error de red**: detener el backend (`docker stop <contenedor-api>`) y ejecutar cualquier
   acción → toast "Ha ocurrido un error inesperado. Por favor, inténtalo de nuevo"; la UI no
   queda en loading infinito. Reiniciar el backend después.
2. **401**: dejar expirar el token (o borrarlo del storage) y ejecutar una acción → redirección
   a /login SIN toast de error adicional.
3. **Dedupe**: abrir una pantalla que dispare varias llamadas (dashboard/tickets) con el
   backend devolviendo el mismo error → una sola notificación visible, no una por llamada.

## Resultado esperado global

- SC-001: todo fallo de API produce notificación visual inmediata.
- SC-002: los 3 casos críticos muestran su mensaje específico (no el genérico).
- SC-003: ninguna pantalla queda congelada/loading indefinido tras un fallo.
- SC-004: ninguna respuesta de error expone detalles internos del servidor.
