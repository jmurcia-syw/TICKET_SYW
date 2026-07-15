# Feature Specification: Contenido enriquecido (formato, imágenes pegadas y adjuntos) en comentarios y descripción de Ticket/Tarea

**Feature Branch**: `017-contenido-enriquecido-ticket`

**Created**: 2026-07-14

**Status**: Draft

**Input**: User description: "los comentarios del ticket y la descripción de ticket/Tareas
pueden incluir archivos adjuntos, pero también texto enriquecido: copiar y pegar imágenes,
pegar correos completos; deben funcionar los hipervínculos, las negrillas, etc."

**Contexto (estado actual, verificado contra el código de Fase 1 / spec 002)**: los comentarios
del ticket **ya** soportan adjuntos de archivo (selector manual de archivo, hasta 10MB, tipos
permitidos, spec 002 FR-013 a FR-016) y el cuerpo del comentario se guarda y muestra como texto
plano sin formato. La descripción del Ticket/Tarea es hoy un campo de texto plano (`<textarea>`)
sin ningún tipo de adjunto ni formato. Esta feature agrega: (1) formato de texto enriquecido al
cuerpo del comentario y a la descripción, (2) la posibilidad de pegar imágenes o contenido con
formato (por ejemplo, copiado de un correo) directamente en el editor, y (3) adjuntos de archivo
en la descripción, a la par de lo que ya existe en comentarios. El tipo estructurado de
comentario (`comment_type`, Principio VI de la constitución) no cambia — el enriquecimiento
aplica solo al cuerpo del texto.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Dar formato al texto en comentarios y descripción (Priority: P1)

Un Resolutor o Usuario/cliente escribe un comentario o la descripción de un Ticket/Tarea y
necesita resaltar partes del texto (negrillas, cursiva, subrayado), organizar información en
listas, o incluir un hipervínculo a un recurso externo (una URL de documentación, un ticket
relacionado, etc.), en lugar de un bloque de texto plano difícil de leer.

**Why this priority**: es el pedido más directo y de menor riesgo — no depende de pegar
contenido externo, solo de dar formato mientras se escribe.

**Independent Test**: puede probarse completamente escribiendo un comentario o una descripción,
aplicando negrilla/cursiva/lista/hipervínculo desde el editor, guardando, y verificando que el
formato se conserva al volver a cargar la pantalla.

**Acceptance Scenarios**:

1. **Given** el editor de un comentario nuevo, **When** el usuario selecciona texto y aplica
   negrilla, cursiva o subrayado, **Then** el texto se guarda y se muestra con ese formato.
2. **Given** el editor de la descripción de un Ticket/Tarea, **When** el usuario escribe una URL
   y la convierte en hipervínculo (o pega una URL que se detecta automáticamente), **Then** el
   enlace queda guardado y se muestra como clicable, abriendo en una pestaña nueva.
3. **Given** el editor de un comentario, **When** el usuario crea una lista con viñetas o
   numerada, **Then** la lista se guarda y se muestra con su estructura (no como texto plano con
   guiones).

---

### User Story 2 - Pegar contenido con formato (imágenes, texto de un correo, etc.) (Priority: P1)

Un Resolutor necesita copiar el contenido de un correo recibido (con su texto formateado, una
imagen incrustada como una captura de pantalla del error, o un hipervínculo) y pegarlo
directamente en un comentario o en la descripción del Ticket, en lugar de tener que retipear el
texto o adjuntar la imagen por separado.

**Why this priority**: es el caso de uso explícito del pedido — pegar correos completos e
imágenes — y el que más tiempo ahorra al evitar retipear o exportar/adjuntar manualmente cada
imagen.

**Independent Test**: puede probarse completamente copiando texto con formato e imágenes desde
un editor externo (correo, Word, página web) y pegándolo en el editor de un comentario o
descripción; el resultado debe mostrar el texto con su formato compatible y las imágenes
incrustadas en el lugar donde se pegaron.

**Acceptance Scenarios**:

1. **Given** un correo copiado con texto en negrilla, una lista y un hipervínculo, **When** el
   usuario lo pega en el editor de un comentario, **Then** el comentario guardado conserva la
   negrilla, la lista y el hipervínculo.
2. **Given** un correo o documento copiado que incluye una imagen incrustada (ej. una captura de
   pantalla), **When** el usuario lo pega en el editor, **Then** la imagen aparece incrustada en
   el punto donde se pegó y queda disponible para verse/descargarse igual que un adjunto.
3. **Given** un usuario copia y pega una imagen directamente desde el portapapeles (captura de
   pantalla, "pegar imagen"), **When** la pega en el editor de un comentario o descripción,
   **Then** la imagen se incrusta en el texto sin necesidad de adjuntarla manualmente como
   archivo aparte.
4. **Given** contenido pegado con formato o estilos no soportados por el editor (fuentes
   personalizadas, colores de fondo, tablas complejas, scripts), **When** se pega, **Then** el
   sistema conserva el formato compatible (negrillas, cursiva, listas, hipervínculos, imágenes) y
   descarta silenciosamente lo no soportado o inseguro, sin romper el diseño de la pantalla ni
   ejecutar código.

---

### User Story 3 - Adjuntar archivos a la descripción del Ticket/Tarea (Priority: P2)

Un Coordinador que crea o edita un Ticket/Tarea necesita adjuntar un archivo de referencia (por
ejemplo, un documento o una planilla) directamente en la descripción, igual que ya puede hacerlo
hoy en un comentario.

**Why this priority**: extiende una capacidad que ya existe y funciona en comentarios a un lugar
donde hoy no existe; de menor urgencia que dar formato al texto (US1) y pegar contenido (US2),
que fueron el pedido explícito.

**Independent Test**: puede probarse completamente adjuntando un archivo al crear o editar la
descripción de un Ticket/Tarea, y verificando que queda listado y descargable igual que un
adjunto de comentario.

**Acceptance Scenarios**:

1. **Given** el formulario de creación o edición de un Ticket/Tarea, **When** el usuario adjunta
   un archivo permitido (mismo tipo/tamaño que ya se acepta en comentarios) a la descripción,
   **Then** el archivo queda asociado a la descripción y disponible para descargar.
2. **Given** un archivo no permitido (tipo no soportado o que excede el tamaño máximo), **When**
   el usuario intenta adjuntarlo a la descripción, **Then** el sistema lo rechaza con el mismo
   mensaje de error que ya usa para adjuntos de comentarios.

---

### Edge Cases

- ¿Qué pasa con los comentarios y descripciones ya existentes (texto plano, sin formato)? Se
  siguen mostrando tal cual dentro del nuevo editor/visor, sin necesidad de migración ni pérdida
  de contenido.
- ¿Qué pasa si se pega contenido que incluye un objeto no soportado (ej. una hoja de cálculo
  incrustada, un video)? Se descarta silenciosamente esa parte, conservando el texto e imágenes
  compatibles alrededor.
- ¿Qué pasa con los resúmenes de comentario en notificaciones o listados (ej. vista previa en un
  listado de tickets)? Se muestran como texto plano legible, sin las marcas de formato ni
  imágenes incrustadas.
- ¿Qué pasa si el contenido pegado o escrito intenta incluir un script o código ejecutable? Se
  descarta por completo — nunca se ejecuta ni se guarda como HTML sin filtrar.
- ¿Qué pasa si se pegan muchas imágenes grandes en un solo comentario o descripción? Cada imagen
  respeta el mismo límite de tamaño ya vigente para adjuntos (spec 002); una imagen que lo exceda
  se rechaza con el mismo mensaje de error que un adjunto demasiado grande.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir aplicar negrilla, cursiva y subrayado al texto de
  comentarios y de la descripción de Ticket/Tarea.
- **FR-002**: El sistema DEBE permitir crear hipervínculos dentro del texto de comentarios y de
  la descripción, que se muestren como enlaces clicables.
- **FR-003**: El sistema DEBE permitir crear listas con viñetas o numeradas dentro del texto de
  comentarios y de la descripción.
- **FR-004**: El sistema DEBE permitir pegar una imagen desde el portapapeles directamente en el
  editor de un comentario o de la descripción, incrustándola en el texto en el punto donde se
  pegó.
- **FR-005**: El sistema DEBE permitir pegar contenido con formato copiado de un origen externo
  (correo, procesador de texto, página web), conservando el formato compatible (negrilla,
  cursiva, subrayado, listas, hipervínculos, imágenes) y descartando el formato no soportado o
  inseguro.
- **FR-006**: El sistema DEBE sanear todo contenido pegado o escrito para impedir la ejecución de
  scripts o HTML no seguro, sin excepciones.
- **FR-007**: El sistema DEBE permitir adjuntar archivos a la descripción de un Ticket/Tarea, con
  las mismas reglas de tamaño y tipo de archivo ya vigentes para adjuntos de comentarios.
- **FR-008**: Las imágenes pegadas DEBEN quedar disponibles para verse/descargarse con el mismo
  mecanismo que ya usan los adjuntos existentes.
- **FR-009**: El sistema DEBE seguir mostrando correctamente los comentarios y descripciones ya
  existentes (texto plano), sin requerir migración de datos.
- **FR-010**: Cualquier vista previa o resumen de un comentario o descripción en texto plano
  (notificaciones, listados) DEBE mostrar el contenido legible sin marcas de formato ni imágenes
  incrustadas.
- **FR-011**: El tipo estructurado de comentario (`comment_type`) DEBE seguir siendo un campo
  separado y estructurado, sin verse afectado por el enriquecimiento del cuerpo del comentario.

### Key Entities

- **Comentario**: su cuerpo pasa de texto plano a contenido con formato (negrillas, listas,
  hipervínculos, imágenes incrustadas); su tipo estructurado no cambia.
- **Descripción de Ticket/Tarea**: gana formato de texto enriquecido y adjuntos de archivo,
  igual que ya tiene el comentario.
- **Adjunto**: entidad ya existente (spec 002); se extiende para poder asociarse también a la
  descripción de un Ticket/Tarea, no solo a un comentario.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un usuario puede crear un comentario con negrilla, un hipervínculo y una imagen
  pegada, y verlo mostrado con ese mismo formato al recargar la pantalla.
- **SC-002**: Un usuario puede pegar el contenido de un correo (texto con formato + imagen) en un
  comentario o en la descripción y conservar al menos negrillas, listas, hipervínculos e
  imágenes.
- **SC-003**: Un usuario puede adjuntar un archivo a la descripción de un Ticket/Tarea, igual que
  ya puede hacerlo en un comentario.
- **SC-004**: 0 casos de contenido pegado que ejecute código o rompa visualmente la pantalla.
- **SC-005**: El 100% de los comentarios y descripciones existentes (texto plano) se siguen
  mostrando correctamente, sin pérdida de contenido.

## Assumptions

- El subconjunto de formato soportado es el estándar de un editor de texto enriquecido básico:
  negrilla, cursiva, subrayado, listas, hipervínculos e imágenes incrustadas — sin fuentes o
  colores personalizados, ni tablas complejas.
- El contenido pegado con formato (Word, correos, páginas web) se normaliza al subconjunto
  soportado por el editor; no se garantiza una réplica visual exacta del origen (comportamiento
  estándar de la mayoría de editores de texto enriquecido al pegar contenido externo).
- Las imágenes pegadas se almacenan y sirven con el mismo mecanismo de adjuntos ya existente para
  comentarios (spec 002), reutilizado también para la descripción.
- Los límites de tamaño y tipos de archivo permitidos son los mismos ya vigentes para adjuntos de
  comentarios (10MB, extensiones permitidas).
- No se requiere migrar comentarios ni descripciones existentes: el contenido plano ya guardado
  se sigue mostrando tal cual dentro del nuevo editor/visor.
