# Quickstart: Refactorización visual y de navegación del detalle del Ticket

Validación manual end-to-end. No hay cambios de backend/DB, así que no hace falta correr
migraciones nuevas — solo el frontend (y el backend ya existente, para servir los datos).

## Prerrequisitos

- Stack levantado: `docker compose up -d` (backend + frontend + Postgres), o `pnpm dev` dentro de
  `frontend/` si el backend ya corre en Docker.
- Usuario de prueba con al menos un ticket asignado y permiso `work_sessions:manage`.
- Un ticket con tiempo estimado definido y otro sin estimar, para probar ambos casos del
  indicador de consumo.

## Validación dirigida (por archivo/componente modificado)

Dado que el usuario pidió explícitamente **no correr la suite completa de tests**, validar solo lo
tocado:

```bash
# Typecheck del frontend completo (rápido, no es "la suite de tests", es el build check habitual)
cd frontend && npx tsc -b
```

No hay tests unitarios de frontend en este repo (no hay Vitest/Jest configurado); no aplica un
comando de test dirigido a un archivo. La validación funcional es manual, por escenario, abajo.

## Escenario 1 (US1) — Registrar tiempo desde un modal, revelado fluido

1. Abrir el detalle de un ticket con al menos un registro de tiempo previo.
2. Confirmar que el histórico de tiempo **no** aparece como tabla siempre visible; en su lugar hay
   un resumen compacto (total registrado, estimado) con una acción para "Registrar tiempo".
3. Tocar "Registrar tiempo" → se abre un modal único con el formulario de carga y el histórico de
   ese ticket.
4. Cargar un nuevo registro (con horas de inicio/fin o duración manual) → confirmar que el
   histórico dentro del modal se actualiza sin cerrar el modal.
5. Cerrar el modal → confirmar que se revela, en orden, el resumen de tiempo, los comentarios y la
   actividad (historial de estados), sin recargar la página.
6. Bajar hasta comentarios/actividad y hacer scroll hacia arriba → confirmar que el resumen de
   tiempo vuelve a revelarse de forma fluida.
7. Confirmar que "Volver a {origen}" (Kanban/Tickets/Panel de Asignación) sigue funcionando igual
   que antes de este cambio.

## Escenario 2 (US2) — Fecha de inicio y consumo estimado vs. real

1. Abrir un ticket **sin** registros de tiempo → confirmar que se indica "Aún sin iniciar" (sin
   fecha) y el total real es 0, sin indicador de alerta si tampoco tiene estimado.
2. Cargar un primer registro de tiempo → confirmar que ahora aparece una fecha de inicio igual a
   la fecha de ese primer registro (no la fecha de creación del ticket).
3. Abrir un ticket con tiempo estimado y menos del 80% consumido → confirmar color "éxito".
4. Cargar tiempo hasta quedar entre 80%-100% consumido → confirmar que el indicador cambia a color
   "atención".
5. Superar el 100% → confirmar color "error".
6. Abrir un ticket sin tiempo estimado con horas reales cargadas → confirmar que se muestra el
   total real sin ningún indicador de alerta.

## Escenario 3 (US3) — "Mis Tareas" y filtros guardados

1. Iniciar sesión como un Resolutor con tickets asignados y abrir "Mis Tareas" (nueva entrada de
   menú) → confirmar que arranca mostrando sus tickets asignados, sin configurar nada.
2. En "Tickets", aplicar una combinación de filtros (p. ej. cliente + estado) y guardarla con un
   nombre.
3. Ir a "Mis Tareas" → confirmar que el filtro guardado en el paso anterior aparece disponible y,
   al aplicarlo, muestra los mismos resultados que en "Tickets".
4. Repetir a la inversa: guardar un filtro desde "Mis Tareas" y confirmar que aparece en
   "Tickets".
5. Intentar eliminar el filtro por defecto "Asignado a mí" → confirmar que el sistema no lo
   permite.
6. Eliminar un filtro creado por el usuario → confirmar que desaparece de ambas pantallas.
7. Intentar guardar un filtro con un nombre ya usado → confirmar que el sistema pide un nombre
   distinto.

## Escenario 4 (US4) — Premisa visual de listas/subtareas

1. Abrir el detalle de un ticket → confirmar que existe un indicio visual de "lista" (informativo,
   sin control funcional) y un espacio "Próximamente" para subtareas, con el mismo lenguaje visual
   que "SLA"/"Sesión de trabajo (Focus Room)".
2. Abrir "Mis Tareas" → confirmar que el agrupamiento visual ya sugiere que los tickets podrán
   pertenecer a listas distintas en el futuro, sin implicar funcionalidad real todavía.

## Escenario 5 (regresión)

1. Confirmar que un usuario sin permiso `work_sessions:manage` puede ver el resumen de tiempo y el
   indicador de consumo, pero no ve la acción de abrir el modal de carga (o la ve deshabilitada).
2. Confirmar que `WorkSessionsPage.tsx` (pantalla global de "Registro de Tiempos", fuera de
   alcance de esta funcionalidad) sigue funcionando exactamente igual que antes.
3. Confirmar que el resto de `TicketDetailPage.tsx` (comentarios, asignación, clasificación,
   prioridad/severidad editable) sigue funcionando sin regresiones.
