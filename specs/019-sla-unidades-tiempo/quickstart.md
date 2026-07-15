# Quickstart: Unidades de tiempo (minutos/horas/días) al configurar SLA

Validación manual end-to-end. No hay cambios de backend/DB, así que no hace falta correr
migraciones nuevas — solo el frontend (y el backend ya existente, para servir/guardar las reglas).

## Prerrequisitos

- Stack levantado: `docker compose up -d` (backend + frontend + Postgres), o `pnpm dev` dentro de
  `frontend/` si el backend ya corre en Docker.
- Usuario con permiso `sla_rules:manage` (Admin/Coordinador) y al menos un Proyecto activo.
- Pantalla: Configuración de SLA (`SlaRulesPage`, donde vive el listado y el botón "Nueva regla de
  SLA").

## Validación dirigida (por archivo modificado)

Dado que el proyecto no tiene suite de tests de frontend configurada (Principio VII, mismo
hallazgo que specs anteriores), validar solo lo tocado:

```bash
# Typecheck del frontend completo (build check habitual, no es "la suite de tests")
cd frontend && npx tsc -b
```

La validación funcional es manual, por escenario, abajo.

## Escenario 1 (US1) — Crear una regla ingresando horas

1. Abrir "Nueva regla de SLA", elegir Proyecto y Prioridad.
2. En "Tiempo límite de contacto" ingresar `15` (sin cambios respecto a hoy: sin selector de
   unidad).
3. En "Tiempo límite de diagnóstico, análisis y ejecución" seleccionar unidad "horas" e ingresar
   `8`.
4. Guardar → confirmar en el listado que la regla quedó con el tiempo equivalente a 480 minutos
   (columna "Diagnóstico/Análisis/Ejecución (min)" debe mostrar 480, o el valor que use esa
   columna para representarlo).

## Escenario 2 (US1) — Crear una regla ingresando días

1. Abrir "Nueva regla de SLA" para una Prioridad distinta (p. ej. "Baja").
2. En el campo de diagnóstico/análisis/ejecución, seleccionar unidad "días" e ingresar `5`.
3. Guardar → confirmar que el tiempo límite persistido equivale a 7200 minutos (5 × 24h × 60min).

## Escenario 3 (regresión) — Minutos sigue funcionando igual que hoy

1. Abrir "Nueva regla de SLA".
2. Dejar la unidad en "minutos" (default) e ingresar `480` directamente en el campo de
   diagnóstico/análisis/ejecución.
3. Guardar → confirmar que el resultado es idéntico al de ingresar "8" con unidad "horas"
   (Escenario 1): 480 minutos. Confirmar también que el campo de contacto no tiene ningún selector
   de unidad nuevo.

## Escenario 4 (US1) — Cambiar de unidad sin perder el valor

1. En el formulario de alta, ingresar `2` en el campo de diagnóstico/análisis/ejecución con unidad
   "días".
2. Cambiar la unidad a "horas" sin tocar el monto → confirmar que el monto mostrado se recalcula a
   `48` (2 días = 48 horas), no que quede en "2 horas".
3. Cambiar la unidad a "minutos" → confirmar que el monto mostrado pasa a `2880`.
4. Guardar → confirmar que el tiempo límite persistido sigue siendo 2880 minutos en cualquiera de
   los 3 pasos anteriores (el cambio de unidad no debe alterar el valor real).

## Escenario 5 (US2) — Editar una regla existente y ver la unidad legible

1. Sobre una regla ya guardada con 480 minutos (creada en el Escenario 1), abrir "Editar".
2. Confirmar que el campo de diagnóstico/análisis/ejecución muestra `8` con unidad "horas" (no
   `480` con unidad "minutos").
3. Sobre una regla guardada con 7200 minutos (Escenario 2), abrir "Editar" → confirmar que muestra
   `5` con unidad "días".
4. Crear (o editar) una regla con un valor que no es múltiplo exacto de 60 (p. ej. `135` minutos
   directo) → al reabrir para editar, confirmar que se muestra `135` con unidad "minutos" (no una
   fracción de horas).

## Escenario 6 (validación) — Rechazo de valores inválidos

1. En el campo de diagnóstico/análisis/ejecución, seleccionar unidad "días" e ingresar `0` →
   confirmar que el formulario rechaza el guardado igual que hoy rechaza "0 minutos".
2. Ingresar un valor fraccionario, p. ej. `1.5` horas → confirmar que se guarda como 90 minutos sin
   error.

## Escenario 7 (regresión) — Reapertura del modal entre distintas reglas

1. Abrir "Editar" sobre la regla de 480 minutos → confirmar unidad "horas"/`8`.
2. Cerrar sin guardar y abrir "Editar" sobre la regla de 7200 minutos → confirmar que ahora muestra
   unidad "días"/`5` (no arrastra el "horas"/`8` de la apertura anterior).
3. Cerrar y abrir "Nueva regla de SLA" → confirmar que el campo aparece vacío con unidad "minutos"
   por defecto (no arrastra valores de la edición anterior).
