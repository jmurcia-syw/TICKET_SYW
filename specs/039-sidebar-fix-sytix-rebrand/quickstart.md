# Quickstart: Validación del fix de Sidebar y Rebranding a SYTIX

Prerrequisito: stack Docker corriendo, sesión iniciada con cualquier rol interno. Si tras aplicar
los cambios el navegador sigue mostrando la versión anterior del sidebar/branding, reiniciar el
contenedor `sywork_frontend` una vez antes de validar (HMR obsoleto conocido en este entorno).

## Escenario 1 — Logo colapsado sin superposición (Acceptance Scenario 1/2 de US1)

1. Con el menú lateral expandido, hacer clic en el control de alternar para colapsarlo.
2. **Esperado**: el logo superior del sidebar se reduce a su versión compacta, centrada dentro
   del ancho colapsado, sin superponerse ni desbordar sobre los íconos del menú.
3. Repetir con la ventana del navegador en al menos 3 anchos (p. ej. 1920px, 1366px, 1024px).
4. **Esperado**: en los 3 anchos el logo compacto y los íconos permanecen alineados, sin romperse
   el layout.

## Escenario 2 — Colapsado estático (Acceptance Scenarios 1-4 de US2)

1. Con el menú colapsado, mover el cursor sobre el área del sidebar sin hacer clic (al menos 20
   movimientos/pasadas).
2. **Esperado**: el menú permanece colapsado en el 100% de los casos (cero auto-expansiones).
3. Hacer clic en el control de alternar.
4. **Esperado**: el menú se expande a su versión completa.
5. Con el menú expandido, hacer clic de nuevo en el control de alternar.
6. **Esperado**: el menú vuelve a colapsarse.
7. Con el menú colapsado, hacer clic en una opción del menú para navegar a otra pantalla.
8. **Esperado**: tras la navegación, el menú permanece colapsado (no se re-expande solo).

## Escenario 3 — Rebranding a SYTIX (Acceptance Scenarios 1-4 de US3)

1. Abrir la pantalla de login (`/login`).
2. **Esperado**: el panel de marca muestra "SYTIX" junto con el eslogan
   "Systems | Innovation | Xcellence"; el logo gráfico existente no cambió.
3. Iniciar sesión y observar el header superior autenticado.
4. **Esperado**: el header muestra "SYTIX" en vez de "SyWork Desk".
5. Observar el título de la pestaña del navegador.
6. **Esperado**: dice "SYTIX".
7. Recorrer header, sidebar y pantalla de login buscando el texto "SyWork" o "SyWork Desk".
8. **Esperado**: no aparece en ninguna de esas pantallas.

## Validación técnica acotada (Principio VII)

- Frontend: `tsc -b` sin errores.
- Sin cambios de backend — no aplica pytest nuevo ni existente para este alcance.
- **No ejecutar la suite de pruebas** (restricción explícita de esta sesión, ver `research.md`
  Decisión 4) — la validación es exclusivamente manual en navegador contra Docker real, siguiendo
  los 3 escenarios de arriba.
