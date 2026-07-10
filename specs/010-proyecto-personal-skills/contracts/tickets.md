# Contract: Tickets — validación del solicitante por Proyecto

Endpoints existentes (`POST /api/tickets`, `PATCH /api/tickets/{id}`). **Sin cambios de
esquema ni de shape** — `client_contact_id` se conserva (clarificación 2026-07-09). Cambian
validaciones y textos.

## POST /api/tickets — validaciones nuevas

1. **Solicitante por proyecto**: si el body trae `client_contact_id` **y** `project_id`, el
   Usuario/cliente debe estar vinculado a ese proyecto (`project_members`) →
   **409 `contact_not_in_project`** ("El Usuario/cliente indicado no está asignado al proyecto
   del ticket"). El chequeo existente por Cliente (409 `client_contact_mismatch`) se mantiene.
   Sin `project_id`, comportamiento actual (solo chequeo por Cliente).
2. **Autoservicio acotado a proyectos vinculados** (FR-007): si el creador es un
   Usuario/cliente y el body trae `project_id`, ese proyecto debe estar entre sus membresías →
   **409 `project_not_assigned`** ("No estás asignado a este proyecto").

## PATCH /api/tickets/{id}

Misma validación (1) al modificar `client_contact_id` o `project_id`. Reglas de la spec `007`
intactas (limpieza al cambiar Cliente, bloqueo en autoservicio y estados finales).

## Textos

Mensajes de error y descripciones Swagger que dicen "Encargado" pasan a "Usuario/cliente"
(p. ej. `client_contact_mismatch`: "El Usuario/cliente indicado no pertenece al cliente del
ticket"; `no_client_contact`: mensaje equivalente). Los **códigos** de error existentes NO
cambian (compatibilidad de contrato).
