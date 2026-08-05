# Research: Corrección de Layout del Menú Lateral (Sidebar Estático) y Rebranding a SYTIX

## Decisión 1 — Causa raíz y fix de la superposición del logo colapsado

**Decisión**: Hacer que el bloque del logo dentro del `Sider` (`frontend/src/pages/DashboardPage.tsx:112-114`)
lea el mismo estado `collapsed` que el componente ya mantiene, y renderice una variante con
padding horizontal reducido y contenido centrado (`justifyContent: 'center'`) cuando está
colapsado, en vez de mantener el mismo `padding: '20px 24px 16px'` fijo en ambos estados.

**Rationale**: El `<Sider collapsible collapsed={collapsed} ...>` de Ant Design colapsa el ancho
del riel a `collapsedWidth` (80px por defecto) y el `Menu` interno adapta sus íconos
automáticamente, pero el `<div>` del logo está codificado a mano con padding/ancho fijos —
no reacciona al colapso, por lo que la imagen (`height: 30`) queda descentrada y su contenedor
se desborda/superpone visualmente sobre la franja de íconos angosta. El header superior
(`<Header>`, fuera del `Sider`) no colapsa junto con el sidebar — no requiere el mismo fix, solo
el cambio de texto de marca (Decisión 3).

**Alternatives considered**:
- Adoptar el patrón de slot de logo de `@ant-design/pro-layout` — rechazado: dependencia nueva,
  prohibida por el Principio V (Gobernanza de Librerías) sin aprobación previa documentada, que
  no aplica a un fix de bug.
- Fix vía hoja de estilos global apuntando a la clase interna `.ant-layout-sider-collapsed` —
  rechazado: más frágil que leer el booleano `collapsed` que el propio componente ya controla,
  y más difícil de verificar sin depender de nombres de clase internos de Ant Design que pueden
  cambiar entre versiones.

## Decisión 2 — Eliminar auto-expansión por hover y por click de navegación

**Decisión**: Eliminar dos disparadores independientes que hoy fuerzan la expansión del menú:
el `onMouseEnter={() => { if (collapsed) setCollapsed(false) }}` del `<Sider>`
(`DashboardPage.tsx:109`) y el `setCollapsed(false)` incondicional dentro del `onClick` del
`<Menu>` (`DashboardPage.tsx:121`). El único disparador de cambio de estado que queda es el
callback nativo `onCollapse` del `Sider`, que Ant Design ya invoca exclusivamente desde su
botón/flecha de alternar (`collapsible` renderiza ese control por defecto) — no hace falta
construir un botón de toggle nuevo.

**Rationale**: Ambos triggers son responsables del comportamiento errático reportado (el menú se
"auto-despliega" tanto al pasar el mouse como al navegar a otra pantalla). Quitarlos deja el
`Sider` en modo puramente controlado por clic explícito, que es exactamente FR-003/FR-004 de
`spec.md`.

**Alternatives considered**:
- Mantener el hover-expand pero con debounce/delay — rechazado: la spec exige que el menú
  colapsado permanezca fijo hasta un clic explícito (FR-003); un delay solo pospone la
  auto-expansión, no la elimina.

## Decisión 3 — Alcance del rebranding y ubicación del eslogan

**Decisión**: Reemplazo de texto únicamente, en los 3 puntos donde "SyWork"/"SyWork Desk" es
visible al usuario final:
- `frontend/index.html:7` — `<title>SyWork Desk</title>` → `<title>SYTIX</title>`.
- `frontend/src/pages/DashboardPage.tsx:75` — texto de marca del header autenticado
  ("SyWork Desk" → "SYTIX", sin eslogan — el header compacto no tiene espacio vertical para una
  segunda línea sin agrandar su altura, fuera de alcance).
- `frontend/src/components/common/AuthLayout.tsx:34` — título de marca del panel compartido por
  Login/Reset-password ("SyWork Desk" → "SYTIX"), agregando el eslogan
  "Systems | Innovation | Xcellence" en la línea de `<Text>` secundaria que ese panel ya tiene
  para copy de marca (hoy "Tickets, tiempos y equipo de soporte en un solo lugar.").
- Atributos `alt="SyWork"` de las 4 instancias del mismo `<img>` (`DashboardPage.tsx:72,113` y
  `AuthLayout.tsx:32,48`) → `alt="SYTIX"`, sin tocar el archivo de imagen (`logo-sywork.jpg`)
  en sí (FR-008).

**Rationale**: Son los únicos lugares donde el nombre de marca aparece como texto/atributo
accesible visible al usuario final; el panel de `AuthLayout` ya tiene una segunda línea de texto
diseñada para copy de marca, por lo que agregar el eslogan ahí no requiere cambios de layout.

**Alternatives considered**:
- Renombrar también identificadores internos no visibles: la clave del `BroadcastChannel`
  `'sywork-auth'` y el nombre de storage `'sywork-auth'` (`authStore.ts:30,56`, usados para
  coordinar el cierre de sesión entre pestañas), las clases CSS `sywork-env-banner`,
  `sywork-rich-editor-content`/`sywork-rich-viewer` (`index.css`), la clave de Zustand
  `'sywork-saved-filters'`, y el nombre de paquete `sywork-frontend` (`package.json`) —
  rechazado: ninguno es visible al usuario final, y renombrar las claves de
  `BroadcastChannel`/`sessionStorage`/`localStorage` invalidaría sin necesidad las sesiones ya
  abiertas en pestañas existentes (comportamiento no solicitado, fuera del alcance estrictamente
  visual pedido). Documentado también en `spec.md` § Assumptions.
- Renombrar el dominio de correo `@sywork.net` usado en validaciones de backend/formularios
  (`TeamPage.tsx`, `LoginPage.tsx`, `backend/api/routes/auth.py`) — rechazado explícitamente:
  es lógica de backend/validación de dominio real de correo, no el "nombre de la aplicación en
  la interfaz"; tocarlo violaría además la restricción explícita del usuario de no alterar
  backend en esta sesión.

## Decisión 4 — Estrategia de validación (sin suite de pruebas)

**Decisión**: No se agrega ni ejecuta ninguna prueba automatizada nueva. La validación es manual,
en navegador, contra el frontend real (`sywork_frontend` en Docker), cubriendo los escenarios de
aceptación de `spec.md` en al menos 3 anchos de ventana más una verificación de "hover no
expande". Ver `quickstart.md`.

**Rationale**: El Principio VII prohíbe correr la suite de pruebas de forma masiva en esta
sesión, y el usuario lo reiteró explícitamente para esta feature ("estrictamente PROHIBIDO
ejecutar la suite de pruebas"). Es además un cambio puramente de CSS/layout + reemplazo de
texto, sin lógica de dominio ni de backend que amerite un test unitario nuevo — solo
`tsc -b` (verificación de tipos, no es "correr pruebas") aplica como chequeo técnico.

**Alternatives considered**:
- Agregar un test de interacción (Testing Library) que aserte que `onMouseEnter` ya no cambia
  `collapsed` — rechazado: no existe hoy ningún archivo de test para `DashboardPage.tsx`, y
  crear uno nuevo iría contra la instrucción explícita del usuario para esta sesión.
