# Quickstart: Fase 1 — Tickets

**Prerequisitos**: `docker compose up -d` (Postgres + backend + frontend), migración
`011_create_tickets.py` aplicada (el backend la ejecuta al arrancar), usuarios semilla de
Fase 0 con contraseña provisional conocida. Referencias: [contracts/tickets.md](contracts/tickets.md),
[data-model.md](data-model.md).

Verificación rápida del arranque:

```bash
docker exec sywork_backend alembic current          # → 011 (head)
curl -s http://localhost:5000/health/ | head -1     # → status ok
docker exec sywork_backend python -m pytest tests/ -q
```

---

## Escenario 1 — Enforcement de seguridad (FR-022) ⚠️ validar primero

1. `GET /api/clients` **sin token** → 401 (en Fase 0 era 200; este es el cambio).
2. `GET /api/tickets` sin token → 401; con token de Resolutor → 200.
3. `POST /api/tickets/{id}/cancel` con token de QM → 403 (QM no tiene `tickets:cancel`).
4. Login en el frontend → todas las pantallas siguen funcionando (el interceptor Axios ya
   envía el JWT desde Fase 0).

## Escenario 2 — Registro y consulta (US1)

1. Como Coordinador, crear un ticket: cliente activo, proyecto del cliente, tipo Incidente,
   prioridad Alta, severidad S2, herramienta JDE, proceso Finanzas.
2. Verificar: nace en NUEVO con número `TK-nnnnnn`; aparece en el listado; el detalle
   muestra todos los campos y el historial vacío.
3. Filtrar por estado NUEVO + cliente → solo los esperados.
4. Intentar crear con proyecto de otro cliente → error en español.

## Escenario 3 — Triage Push (US2)

1. Asignar el ticket a un Resolutor → pasa a CONTACTO, comentario automático "Asignado",
   y el Resolutor ve la notificación en la campana.
2. Crear otro ticket y asignarlo al QM con modo Pre-Análisis → PRE-ANÁLISIS.
3. Como QM, reasignar al Resolutor → CONTACTO.
4. Verificar en DB el Gold Standard Dataset:
   ```bash
   docker exec sywork_db psql -U sywork_user -d sywork_tickets \
     -c "SELECT resulting_status, context FROM ticket_assignments ORDER BY created_at;"
   ```
   → cada fila con `context` JSONB completo (skills, carga, prioridad, severidad).
5. Repetir la asignación vía `curl` directo a `POST /api/tickets/{id}/assign` → mismo
   comportamiento que desde la UI (FR-018).

## Escenario 4 — Ciclo de vida completo por comentarios (US3, camino feliz)

Como el Resolutor asignado, recorrer SOLO con comentarios tipificados:

1. CONTACTO: enviar "Confirmación de atención" → EN ANÁLISIS; verificar que severidad/
   prioridad/tiempo estimado quedan editables (`locked_fields` cambia).
2. EN ANÁLISIS: registrar tiempo estimado; enviar "Termina análisis" → EN EJECUCIÓN;
   tiempo de resolución bloqueado.
3. EN EJECUCIÓN: enviar "Solicitud de información" con un adjunto (PNG < 10 MB) →
   PENDIENTE DE USUARIO; adjunto descargable desde el detalle.
4. Registrar "Respuesta de usuario" (en nombre del cliente, Q2) → EN EJECUCIÓN.
5. Pasar a EN PRUEBAS y volver (toggle, Q1) → estados correctos.
6. Enviar "Solicitud de cierre" → RESUELTO (`resolved_at` seteado).
7. Registrar aceptación (`/resolution accepted: true`) y cerrar con tipo de resolución +
   "Descripción solución" → CERRADO; Coordinador y QM reciben notificación.
8. Verificar el historial: cada transición con autor, fecha y comentario asociado.

**Negativos**:
- En NUEVO, intentar "Confirmación de atención" → 409 con acciones válidas en español.
- Cerrar sin tipo de resolución → bloqueado.
- Como otro Resolutor (no asignado), intentar cualquier transición → 403 (FR-028).
- Rechazo de resolución (`accepted: false`) → vuelve a EN EJECUCIÓN + notificación.
- Editar `severity` por PATCH estando en CONTACTO → 409 `field_locked`.
- Adjunto > 10 MB → 400 con mensaje claro.

## Escenario 5 — Panel de Asignación (US4)

1. Con ≥3 resolutores y tickets repartidos en varios estados, abrir el panel → matriz
   resolutor × estado con conteos correctos y total por resolutor.
2. Asignar un ticket NUEVO desde el panel → mismo efecto que Escenario 3.
3. Filtrar por estados CONTACTO + EN ANÁLISIS → conteos solo de esos estados.
4. (SC-005) Sembrar ~500 tickets de prueba y verificar carga < 2 s.

## Escenario 6 — Catálogos

1. Como Coordinador, agregar herramienta "OTM" → aparece en el selector de tickets nuevos.
2. Desactivar un proceso en uso por un ticket abierto → 409 con conteo.
3. Desactivar uno sin uso → desaparece de selectores; tickets viejos conservan el valor.

## Checklist de validación

- [ ] Enforcement JWT+permisos activo en TODAS las rutas (maestros incluidos) — 401/403 correctos
- [ ] Ticket nace en NUEVO con consecutivo único legible
- [ ] Matriz de transiciones exacta: camino feliz completo y negativos rechazados en español
- [ ] Comentario tipificado + transición + notificación = operación atómica
- [ ] Gold Standard Dataset: toda asignación con contexto JSONB completo, append-only
- [ ] Bloqueo/desbloqueo de campos por estado (UI y API)
- [ ] Adjuntos: subida, límite de tamaño, descarga autenticada
- [ ] Resolutor no puede transicionar tickets ajenos (API directa incluida)
- [ ] Panel de Asignación: conteos correctos, asignación inline, < 2 s con 500 tickets
- [ ] Notificaciones: campana con no-leídas, marcar leídas, eventos FR-023/024
- [ ] Catálogos administrables con bloqueo por uso
- [ ] Tests: dominio (FSM completa) + API contra Postgres en verde
