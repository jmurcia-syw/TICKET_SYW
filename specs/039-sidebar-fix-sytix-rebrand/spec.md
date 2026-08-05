# Feature Specification: Corrección de Layout del Menú Lateral (Sidebar Estático) y Rebranding a SYTIX

**Feature Branch**: `[039-sidebar-fix-sytix-rebrand]`

**Created**: 2026-08-05

**Status**: Draft

**Input**: User description: "Corrección de Layout del Menú Lateral (Sidebar Estático) y Rebranding a SYTIX — corregir un error de renderizado visual en la barra lateral/header cuando se colapsa la navegación (superposición del logo, auto-despliegue por hover) y actualizar el nombre de la aplicación de 'SyWork Desk'/'SyWork' a 'SYTIX' (eslogan 'Systems | Innovation | Xcellence') en el header, sidebar, títulos de página y componentes, sin agregar imágenes de logo nuevas."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Menú lateral colapsado usable en cualquier resolución (Priority: P1)

Como usuario interno (cualquier rol), cuando colapso el menú lateral a su versión mínima de iconos, necesito que el logo y los iconos se vean correctamente alineados y centrados — sin superponerse entre sí — para poder seguir navegando la aplicación sin que el layout se vea roto, en cualquier tamaño de pantalla.

**Why this priority**: Es un defecto visual activo que degrada la usabilidad de la navegación para todos los roles en todas las pantallas; es el más disruptivo de los tres bugs reportados.

**Independent Test**: Puede probarse por completo colapsando el menú lateral con la app abierta en distintos anchos de ventana (ej. 1920px, 1366px, 1024px) y verificando visualmente que el logo compacto queda centrado dentro del área de iconos, sin recortarse ni superponerse con el menú.

**Acceptance Scenarios**:

1. **Given** el menú lateral está expandido, **When** el usuario lo colapsa, **Then** el logo superior se reduce a su versión compacta y queda centrado dentro del ancho colapsado, sin superponerse ni desbordar sobre la barra de iconos.
2. **Given** el menú lateral está colapsado, **When** el usuario redimensiona la ventana del navegador (o cambia de resolución), **Then** el logo compacto y los iconos del menú permanecen correctamente alineados, sin romperse el layout.
3. **Given** el menú lateral está colapsado, **When** el usuario observa el área superior del sidebar, **Then** no hay elementos de texto ni logo expandido visibles — solo el icono reducido.

---

### User Story 2 - El menú lateral solo cambia de estado por clic explícito (Priority: P1)

Como usuario interno, cuando el menú lateral está colapsado y muevo el cursor sobre él sin intención de expandirlo (por ejemplo, para acceder a un ícono puntual o simplemente porque el cursor pasa por esa zona de la pantalla), necesito que permanezca colapsado, para no perder espacio de trabajo de forma inesperada mientras leo o interactúo con el contenido principal.

**Why this priority**: Junto con US1, corrige el comportamiento errático del sidebar reportado como bug de layout; sin este cambio, la corrección visual de US1 seguiría siendo inconsistente porque el menú se re-expandiría solo con pasar el mouse.

**Independent Test**: Puede probarse por completo colapsando el menú, moviendo el cursor sobre el área del sidebar sin hacer clic en el botón de alternar, y confirmando que el menú permanece colapsado; luego haciendo clic explícito en el botón/flecha de alternar y confirmando que sí cambia de estado.

**Acceptance Scenarios**:

1. **Given** el menú lateral está colapsado, **When** el cursor pasa sobre el área del sidebar sin hacer clic, **Then** el menú permanece colapsado (no se auto-expande).
2. **Given** el menú lateral está colapsado, **When** el usuario hace clic en el botón/flecha de alternar, **Then** el menú se expande a su versión completa.
3. **Given** el menú lateral está expandido, **When** el usuario hace clic en el botón/flecha de alternar, **Then** el menú se colapsa a su versión mínima de iconos.
4. **Given** el menú lateral está colapsado, **When** el usuario hace clic en una opción del menú para navegar a otra pantalla, **Then** el menú permanece colapsado tras la navegación (no se re-expande automáticamente como efecto secundario de haber navegado).

---

### User Story 3 - La aplicación se identifica como SYTIX (Priority: P2)

Como usuario de la aplicación, al iniciar sesión o navegar por cualquier pantalla, necesito ver el nombre "SYTIX" (con su eslogan "Systems | Innovation | Xcellence" donde se muestre la marca completa) en lugar de "SyWork Desk"/"SyWork", para que la interfaz refleje el nombre actual del producto.

**Why this priority**: Es un cambio de branding sin impacto funcional; no bloquea el uso de la aplicación, por lo que se prioriza después de las correcciones de layout (P1), pero es igualmente parte del alcance solicitado.

**Independent Test**: Puede probarse por completo recorriendo las pantallas visibles de la aplicación (login, header, sidebar, título de la pestaña del navegador) y confirmando que ninguna muestra "SyWork Desk" ni "SyWork" como nombre de marca visible al usuario.

**Acceptance Scenarios**:

1. **Given** el usuario abre la pantalla de inicio de sesión, **When** observa el encabezado de marca, **Then** ve "SYTIX" (y el eslogan "Systems | Innovation | Xcellence" donde se muestre la marca completa) en lugar de "SyWork Desk".
2. **Given** el usuario está autenticado, **When** observa el header superior de la aplicación, **Then** ve "SYTIX" en lugar de "SyWork Desk".
3. **Given** el usuario tiene la aplicación abierta, **When** observa el título de la pestaña del navegador, **Then** dice "SYTIX" en lugar de "SyWork Desk".
4. **Given** el logo/icono gráfico existente (imagen), **When** se revisan header y sidebar tras el cambio, **Then** el archivo de imagen del logo no cambia (no se agregan ni reemplazan archivos gráficos) — solo cambia el texto que lo acompaña y, si aplica, las dimensiones del icono compacto de US1.

---

### Edge Cases

- Si el usuario navega directamente a una URL interna (deep link) con el menú lateral ya colapsado de una sesión anterior, el logo compacto y el layout deben verse correctos desde la primera carga, sin depender de una interacción previa.
- En pantallas angostas donde el contenido principal ya fuerza scroll horizontal o vertical, el estado colapsado/expandido del sidebar no debe generar solapamientos adicionales con el header o el contenido.
- Texto de marca dentro de componentes que no son el header/sidebar principal (por ejemplo, un título de página que hoy mencione "SyWork") también debe actualizarse a "SYTIX" si es visible al usuario final.
- Identificadores internos no visibles al usuario (nombres de clases CSS, claves de almacenamiento local, dominios de correo `@sywork.net` usados en validaciones de backend) quedan fuera de alcance de este rebranding visual — ver Assumptions.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE mostrar, cuando el menú lateral está colapsado, únicamente la versión compacta/reducida del logo, correctamente centrada dentro del área de iconos, sin superponerse con ningún otro elemento del menú.
- **FR-002**: El layout del menú lateral colapsado DEBE mantenerse correcto (sin desbordes ni superposiciones) en cualquier resolución o ancho de ventana soportado por la aplicación.
- **FR-003**: El sistema NO DEBE expandir automáticamente el menú lateral colapsado en respuesta a que el cursor pase sobre él (sin clic).
- **FR-004**: El sistema NO DEBE volver a expandir el menú lateral colapsado como efecto secundario de otras acciones del usuario (por ejemplo, al hacer clic en una opción del menú para navegar).
- **FR-005**: El sistema DEBE permitir expandir o colapsar el menú lateral únicamente mediante un clic explícito del usuario en el control de alternar (botón/flecha), preservando esta capacidad para todos los roles que ya la tenían.
- **FR-006**: El sistema DEBE reemplazar toda mención visible al usuario del nombre "SyWork Desk" o "SyWork" por "SYTIX" en el header, el sidebar, los títulos de página (incluido el título de la pestaña del navegador) y demás componentes de interfaz donde el nombre aparezca como texto.
- **FR-007**: Donde hoy se muestre la marca completa acompañada de contexto (por ejemplo, la pantalla de inicio de sesión), el sistema DEBE mostrar junto a "SYTIX" el eslogan "Systems | Innovation | Xcellence".
- **FR-008**: El cambio de nombre de marca NO DEBE requerir ni introducir archivos de imagen de logo nuevos; el archivo gráfico existente se conserva, ajustando únicamente texto y, donde corresponda por US1, las dimensiones del icono compacto.

### Key Entities

*(N/A — esta funcionalidad no introduce ni modifica entidades de datos; es un ajuste de presentación/interfaz.)*

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de las combinaciones probadas de resolución de pantalla (escritorio ancho, laptop estándar, laptop pequeña) muestran el menú lateral colapsado sin superposición visual entre el logo y los iconos.
- **SC-002**: En una sesión de prueba de al menos 20 movimientos de cursor sobre el sidebar colapsado sin clic, el menú permanece colapsado el 100% de las veces (cero auto-expansiones).
- **SC-003**: El texto "SyWork Desk" o "SyWork" no aparece en ninguna pantalla visible al usuario tras recorrer las áreas principales de la aplicación (login, header autenticado, sidebar, título de pestaña del navegador).
- **SC-004**: El control de alternar (clic explícito) sigue permitiendo expandir y colapsar el menú lateral el 100% de las veces, sin regresión respecto al comportamiento previo a este cambio.

## Assumptions

- El defecto de superposición del logo y el auto-despliegue por hover se ubican en el layout principal autenticado de la aplicación (header + menú lateral compartido por todas las pantallas internas); no hay un segundo sidebar independiente a corregir.
- "Componentes" para efectos del rebranding se limita a elementos de interfaz visibles al usuario final (textos de marca, `<title>` de la pestaña, encabezados de pantallas de autenticación). Identificadores internos no visibles — nombres de clases CSS, claves de almacenamiento local/sessionStorage, nombres de paquete (`package.json`), o el dominio de correo `@sywork.net` usado en validaciones de backend — quedan fuera de alcance porque no son parte del "nombre de la aplicación en la interfaz" que el usuario ve.
- El eslogan "Systems | Innovation | Xcellence" se muestra únicamente donde ya se exhibe la marca completa con espacio para texto secundario (p. ej. pantalla de login); en el header compacto de la app autenticada, donde solo cabe el nombre corto, se muestra únicamente "SYTIX".
- Esta funcionalidad es exclusivamente de interfaz/presentación: no introduce, modifica ni elimina reglas de negocio, endpoints, ni lógica de backend — consistente con el alcance indicado por quien solicita la funcionalidad.
- El archivo de imagen del logo existente se reutiliza sin cambios; solo puede ajustarse su tamaño de despliegue (dimensiones en pantalla) para resolver la superposición de US1, no su contenido gráfico.
