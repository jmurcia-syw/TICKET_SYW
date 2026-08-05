# Quickstart: Ajustes Globales — Seguridad/Permisos, Notificaciones, Motor de SLA, Bugs de UI y Rendimiento

Validación manual contra Docker real (`docker compose up --build -d`), por user story. Cada
escenario es independiente — no requiere completar los anteriores.

## Prerrequisitos

- Stack levantado: `docker compose ps` muestra los 5 servicios `Up`.
- Al menos 2 usuarios de prueba: uno con rol Resolutor (con 2-3 tickets asignados y algunos NO
  asignados a él en el sistema) y uno con rol Coordinador o Administrador.
- Un Cliente de prueba con 2+ tipos de acceso configurados (Maestros → Clientes → Accesos).
- Ver credenciales semilla en `docs/credenciales_dev.txt`.

## US1 — Vistas acotadas por rol

1. Login como Resolutor de prueba → abrir Kanban: verificar que solo aparecen sus tickets/tareas
   asignados (comparar contra el total real vía login como Coordinador).
2. Mismo usuario → abrir Mis Tareas/Listas: mismo criterio aplicado.
3. Mismo usuario → intentar navegar a `/tickets` (vista global): verificar que la opción no está
   en el menú y que la URL directa no muestra el listado completo.
4. Login como Coordinador/Admin → verificar que `/tickets` sigue mostrando todo sin filtro.
5. Login como Resolutor → abrir Calendario: verificar que solo se ve su propio calendario/franja.
6. Con las DevTools de red abiertas, login como Resolutor y navegar la app: confirmar que no se
   disparan peticiones a los catálogos administrativos completos (Clientes/Herramientas/Procesos/
   Tipos de resolución/Equipos/Tipos de acceso).
7. Cualquier usuario → hacer clic en el control de colapsar del menú lateral: verificar que se
   reduce a solo iconos y se expande al interactuar/seleccionar una opción.

## US2 — Motor de SLA y auditoría inicial

1. Crear un Ticket de prueba → abrir su detalle → Historial de Estados: verificar que existe una
   primera entrada "Ticket creado en estado Nuevo" (o equivalente) con fecha/hora y creador.
2. Crear una Tarea de prueba → mismo chequeo en su Historial de Estados.
3. Asignar el Ticket (pasa a "Contacto") y esperar unos minutos sin transicionarlo a "En Análisis":
   verificar que el contador de SLA de Contacto sigue corriendo (no "detenido").
4. Transicionar a "En Análisis" (comentario "Confirmación de atención"): verificar que el SLA de
   Contacto se congela en ese instante (resultado cumplido/vencido fijo desde ahí).
5. Llevar el Ticket a "Resuelto": verificar que el SLA de Resolución sigue "corriendo" (no
   "detenido") mientras permanece en ese estado.
6. Cerrar el Ticket ("Cerrado"): verificar que el SLA de Resolución se congela recién ahí.
7. (Opcional) Rechazar la resolución de un Ticket "Resuelto" (vuelve a "En Ejecución"): verificar
   que el SLA de Resolución retoma sin reiniciar el tiempo ya consumido.

## US3 — Bugs críticos de UI

1. Abrir el detalle de un Ticket/Tarea y reproducir el flujo de scroll/interacción que antes
   generaba parpadeo (spec `036`): verificar que el menú lateral y los componentes principales
   permanecen estables (usar el mismo método de verificación con `ResizeObserver` de spec `036`
   si aplica, extendido al contenedor del menú).
2. Abrir el detalle de un Cliente con 2+ tipos de acceso → editar credenciales del primer tipo →
   cambiar al segundo tipo y editar sus credenciales → guardar ambos.
3. Releer ambos tipos de acceso: verificar que cada uno conserva únicamente sus propios datos, sin
   mezcla.

## US4 — Formularios y validaciones

1. En el formulario de Ticket/Tarea (u otro formulario con Cliente+Proyecto, ej. SLA Configurable/
   Reportes), seleccionar un Cliente: verificar que el selector de Proyecto solo ofrece proyectos
   de ese Cliente.
2. Cambiar de Cliente habiendo ya elegido un Proyecto: verificar que la selección de Proyecto se
   limpia.
3. Intentar guardar un Ticket sin Usuario/cliente solicitante: verificar que se bloquea.
4. Intentar guardar una Tarea sin Usuario/cliente solicitante: verificar que se guarda sin error.
5. Intentar guardar un Registro de Tiempo sin Descripción/Nota: verificar que se bloquea.

## US5 — Gestión de usuarios y notificaciones

1. Crear/resetear un usuario de prueba → hacer clic en "Copiar Contraseña" → pegar en otro campo
   (ej. la barra de direcciones) y confirmar que coincide con el valor mostrado en pantalla.
2. Crear un usuario nuevo marcando "Notificar al Usuario": confirmar en el buzón de prueba (o
   `docker compose logs backend | grep -i correo` si SMTP no está configurado en el entorno de
   prueba) que se generó/envió el correo con logo, mensaje de bienvenida, URL de login,
   contraseña temporal y enlace de cambio.
3. Abrir el enlace de cambio de contraseña dentro de los 30 minutos: confirmar que funciona.
4. (Con un segundo usuario de prueba, o esperando) abrir el enlace después de 30 minutos:
   confirmar que se rechaza con mensaje claro.
5. Crear un usuario nuevo SIN marcar "Notificar al Usuario": confirmar que no se envía correo y el
   alta se completa igual.

## US6 — Rendimiento del Detalle del Cliente

1. Con DevTools → Network abierto, abrir el detalle de un Cliente con historial extenso (varios
   accesos/proyectos/contactos): registrar tiempo hasta interactivo y número de peticiones.
2. Cambiar entre sus pestañas internas: confirmar que los datos de una pestaña no se cargan hasta
   visitarla.
3. Repetir la apertura y comparar contra la medición previa al cambio (antes/después) para
   confirmar la mejora perceptible pedida en SC-010.

## Pruebas dirigidas (backend)

Por Principio VII: correr solo los archivos de test tocados por esta feature, con datasets de
máximo 5-10 registros mock por test nuevo. Ejemplos esperados (nombres exactos se definen en
`tasks.md`):

```bash
docker exec sywork_backend python -m pytest tests/domain/test_sla_service.py -q
docker exec sywork_backend python -m pytest tests/api/test_tickets_view_assigned.py -q
docker exec sywork_backend python -m pytest tests/domain/test_work_session_service.py -q
docker exec sywork_backend python -m pytest tests/api/test_users_notify.py -q
```

No ejecutar `pytest tests/ -q` (suite completa) durante esta feature.

```bash
cd frontend && npx tsc -b
```
