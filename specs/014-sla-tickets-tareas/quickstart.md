# Quickstart: Validación — SLAs por Proyecto y Prioridad

**Feature**: 014-sla-tickets-tareas

## Prerrequisitos

- Stack levantado con Docker (`docker ps`), incluyendo el nuevo worker Celery + Redis
  (`docker compose up -d` debe traer también `sywork_worker` y `sywork_redis` una vez agregados
  al `docker-compose.yml`).
- Credenciales semilla: `docs/credenciales_dev.txt`.
- Contrato de referencia: [contracts/sla-contract.md](./contracts/sla-contract.md).
- Modelo de datos: [data-model.md](./data-model.md).

## Validación 1 — Configurar una regla de SLA por Proyecto (Historia 1)

1. Login como Admin. `POST /api/sla-rules` con `project_id`, `priority=high`, `contact_minutes=15`,
   `execution_minutes=480`.
2. `GET /api/sla-rules?project_id=...` → la regla aparece en el listado.
3. Crear otra regla para el mismo `project_id` con `priority=critical` (valores distintos) → ambas
   coexisten, cada Proyecto+Prioridad es independiente.
4. Intentar crear una regla duplicada para la misma combinación `(project_id, priority)` → 409
   `DUPLICATE_RULE`.
5. Consultar un ticket de un Proyecto sin regla para su Prioridad → el bloque `sla` muestra
   `status=sin_sla` (no hay fallback automático).

Test unitario específico (Principio VII):
```bash
docker exec sywork_backend pytest backend/tests/domain/test_sla_service.py backend/tests/api/test_sla_rules.py -v
```

## Validación 2 — Contador en el detalle del ticket, 2 fases (Historia 2)

1. Crear un ticket en el Proyecto/Prioridad de la regla del paso anterior (estado inicial `nuevo`).
2. Abrir el detalle → el bloque SLA (antes `—:—:—`) muestra `phase=contacto`, `status=corriendo` y
   el tiempo límite de contacto (15 min).
3. Ejecutar `assign_resolver` (pasa a estado `contacto`) → el bloque SLA muestra `phase=ejecucion`,
   `contact_result` congelado (`cumplido` o `vencido` según el tiempo transcurrido) y el contador
   de la segunda fase arranca en `consumed_seconds=0` con el tiempo límite de ejecución de la
   Prioridad del ticket.
4. Mover el ticket a `pendiente_usuario` (comentario "Solicitud de información") → el bloque SLA
   pasa a `status=pausado`, deja de avanzar (misma fase `ejecucion`).
5. Responder como usuario (`respuesta_usuario`) → el bloque SLA vuelve a `corriendo`, reanudando
   desde el tiempo ya acumulado en la fase `ejecucion` (no se reinicia).
6. Ajustar manualmente en DB (dev only) `sla_consumed_seconds` por encima de
   `sla_phase_limit_minutes*60` y refrescar → el bloque SLA muestra `vencido` con estilo de alerta.

## Validación 3 — Indicadores agregados (Historia 3)

1. Con varios tickets en distintos estados de SLA, abrir el listado de Tickets → cada fila
   muestra el indicador de SLA correspondiente.
2. El stat "Vencen hoy" del dashboard (antes fijo en `—`) refleja el conteo real de
   `sla_expiring_within_hours=24`.
3. Esperar (o disparar manualmente en dev) la tarea Celery de detección de vencimientos:
   ```bash
   docker exec sywork_worker celery -A backend.workers.sla_tasks call backend.workers.sla_tasks.check_sla_breaches
   ```
   → se crea una notificación interna para el Resolutor asignado y el Coordinador del ticket
   vencido, visible en la campana de notificaciones ya existente.

## Resultado esperado global

- SC-001: tickets vencidos/próximos a vencer identificables sin abrir el detalle.
- SC-002: el contador de cada ticket con regla aplicable es coherente con su historial de estados.
- SC-003: el tiempo en `pendiente_usuario` nunca se suma al consumo.
- SC-004: notificación de vencimiento generada en minutos (ciclo de la tarea Celery, no al abrir
  la pantalla).
- SC-005: alta de una regla completa en menos de 2 minutos desde la pantalla de configuración.
