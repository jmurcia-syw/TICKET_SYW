# Quickstart: Validar el Script de Datos Semilla — Clientes Aris y Vaxthera

## Prerrequisitos

- Entorno Docker del proyecto levantado (`sywork_backend`, `sywork_db`) — ver `docker ps` para
  confirmar que `sywork_backend` está corriendo.
- Al menos un usuario Admin/Coordinador ya sembrado (para poder iniciar sesión y navegar a Maestros).

## 1. Ejecutar el script

```bash
docker exec sywork_backend python -m backend.scripts.seed_clients_aris_vaxthera
```

Salida esperada (resumen): confirmación de creación (o "ya existía, omitido") para cada cliente,
proyecto, usuario, regla de SLA y lista de tareas, y las 3 contraseñas iniciales en texto plano
(una única vez, para entregarlas de forma segura fuera del log persistente).

## 2. Verificar re-ejecución segura (idempotencia, FR-012)

```bash
docker exec sywork_backend python -m backend.scripts.seed_clients_aris_vaxthera
```

**Resultado esperado**: la segunda ejecución reporta todos los registros como "ya existía, omitido"
y no crea filas nuevas (SC-002).

## 3. Verificar en la UI

1. **Maestros > Clientes**: confirmar que "Aris" (Colombia, `America/Bogota`) y "Vaxthera" (Ecuador,
   `America/Guayaquil`) aparecen en el listado.
2. **Maestros > Proyectos**: confirmar 3 proyectos bajo Aris (Evolutivo, Preventa, Soporte) y 1 bajo
   Vaxthera (Soporte).
3. **Proyecto Soporte (Aris) > configuración de SLA**: confirmar la matriz de 4 niveles con los
   tiempos de la tabla de `data-model.md` (Crítico 2h/4h, Alto 4h/8h, Medio 8h/24h, Bajo 24h/48h).
4. **Proyectos Evolutivo/Preventa (Aris) y Soporte (Vaxthera)**: confirmar que no muestran matriz de
   SLA activa.
5. **Listas de Tareas del proyecto Soporte (Aris)**: confirmar las 8 listas, en el orden de
   `data-model.md`.
6. **Listas de Tareas del proyecto Soporte (Vaxthera)**: confirmar las 5 listas, en el orden de
   `data-model.md`, incluyendo "Seguimiento (Completadas)" como nombre literal.
7. **Maestros > Usuarios/clientes** (Encargados, `ClientContactsPage.tsx`): confirmar que
   `Eliseon@aris.ming.com` y `paulaBlanco@aris.ming.com` aparecen ahí como Encargados de Aris, y que
   `pablo@vaxthera.com` aparece como Encargado de Vaxthera — **no** deben aparecer únicamente en la
   pestaña de Personal/Equipo de cada proyecto (esa pestaña también los debe listar, con acceso a sus
   proyectos, pero la fuente de verdad de que son Encargados es esta pantalla).

## 3a. Verificar convergencia forzada (edge case)

```bash
# simular un valor divergente y confirmar que el script lo corrige en la siguiente ejecución
docker exec sywork_db psql -U sywork_user -d sywork_tickets \
  -c "UPDATE clients SET timezone='America/Lima', country='Peru' WHERE name='Aris';"
docker exec sywork_backend python -m backend.scripts.seed_clients_aris_vaxthera
docker exec sywork_db psql -U sywork_user -d sywork_tickets \
  -c "SELECT name, country, timezone FROM clients WHERE name='Aris';"
```

**Resultado esperado**: el script reporta `cliente Aris` en "Actualizados" y la consulta final vuelve
a mostrar `Colombia` / `America/Bogota`.

## 4. Verificar el motor de SLA con un Ticket real (User Story 3, opcional)

1. Crear un Ticket de prueba en el proyecto Soporte de Aris → su detalle debe mostrar countdown /
   indicadores de cumplimiento de SLA.
2. Crear un Ticket de prueba en el proyecto Soporte de Vaxthera → su detalle NO debe mostrar ningún
   indicador de SLA.

## Notas de alcance

- El script no crea Tickets, Tareas ni registros de tiempo de ejemplo (FR-013) — los pasos 4 de esta
  guía son solo para validar el comportamiento del motor de SLA con datos reales, no forman parte de
  la siembra en sí; los Tickets de prueba pueden eliminarse después.
- No se debe ejecutar la suite completa de pruebas unitarias como parte de esta validación
  (constitution Principio VII) — la verificación es manual, contra la UI real.
