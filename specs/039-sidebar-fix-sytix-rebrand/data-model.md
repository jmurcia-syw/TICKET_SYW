# Data Model: Corrección de Layout del Menú Lateral y Rebranding a SYTIX

Sin cambios de esquema de base de datos, sin cambios de contrato de API, sin nuevas entidades ni
campos. Esta feature es exclusivamente de presentación (Capa 3): ajustes de estilos/estado local
en un componente React ya existente (`DashboardPage.tsx`) y reemplazo de literales de texto de
marca en 3 archivos frontend (`DashboardPage.tsx`, `AuthLayout.tsx`, `index.html`).

## Frontend — estado local, sin tipos nuevos

- `DashboardPage.tsx` ya mantiene `const [collapsed, setCollapsed] = useState(false)` (declarado
  en spec 038 US1) — no se agrega estado nuevo; se eliminan dos disparadores que lo mutaban
  (`onMouseEnter` del `Sider`, `onClick` del `Menu`) según `research.md` Decisión 2.
- No se modifica `frontend/src/types/ticket.ts`, `user.ts` ni ningún otro tipo compartido.
- El texto "SYTIX" y el eslogan "Systems | Innovation | Xcellence" son literales de string
  incrustados directamente en el JSX de los 3 archivos afectados (no se introduce una constante
  de configuración de marca nueva — no la pidió el alcance, y evita tocar archivos adicionales
  fuera de layout/branding).
