# BACKLOG — Estado vivo de observaciones

> Única fuente de verdad del estado actual de cada observación. Los archivos `ITER-XXX.md` son históricos e inmutables; este archivo es el que se actualiza. Ver `../CONVENTIONS.md` para el detalle de estados e IDs.

| ID | Módulo/Pantalla | Tipo | Estado | Reportado por | Iteración origen | Iteración cierre | Descripción corta |
|---|---|---|---|---|---|---|---|
| OBS-0001 | Clientes > Nuevo Cliente | Mejora | Abierta | Camilo Reyes | ITER-001 | — | Ampliar "IPs VPN"/"Credenciales VPN" a múltiples accesos (VPN, URL por ambiente, escritorio remoto, adjuntos) |
| OBS-0002 | Pantalla Principal > Menú | Mejora | Abierta | Camilo Reyes | ITER-001 | — | Mover "Catálogos" dentro de "Maestros" en el menú principal |
| OBS-0003 | Inicio de sesión | Mejora | Abierta | Arely Pazmiño | ITER-002 | — | Mensaje de validación de credenciales no específico (usuario vs contraseña) |
| OBS-0004 | Tickets | Mejora | Abierta | Arely Pazmiño | ITER-002 | — | Falta confirmación al eliminar un filtro |
| OBS-0005 | Proyectos > Nuevo Proyecto | Mejora | Abierta | Arely Pazmiño | ITER-002 | — | Falta buscador en el selector de clientes al crear proyecto |
| OBS-0006 | Clientes > Nuevo Cliente | Mejora | Abierta | Arely Pazmiño | ITER-002 | — | Falta mensaje de confirmación al crear un cliente |
| OBS-0007 | Clientes > Nuevo Cliente | Defecto | Abierta | Arely Pazmiño | ITER-002 | — | Campo Teléfono acepta letras y no valida longitud mínima |
| OBS-0008 | Clientes > Editar Cliente | Defecto | Abierta | Arely Pazmiño | ITER-002 | — | Campos VPN muestran información cruzada entre clientes |
| OBS-0009 | Proyectos > Nuevo Proyecto | Mejora | Abierta | Arely Pazmiño | ITER-002 | — | Falta mensaje de confirmación al crear un proyecto |
| OBS-0010 | Proyectos > Nuevo/Editar Proyecto | Defecto | Abierta | Arely Pazmiño | ITER-002 | — | Validaciones insuficientes en nombre de proyecto/listas (longitud, caracteres, duplicados) |
| OBS-0011 | Proyectos > Nuevo/Editar Proyecto | Defecto | Abierta | Arely Pazmiño | ITER-002 | — | Validación inconsistente de fechas de inicio/fin del proyecto |
| OBS-0012 | Proyectos > Nuevo/Editar Proyecto | Defecto | Abierta | Arely Pazmiño | ITER-002 | — | Validación insuficiente en campos monetarios (negativos, formato, separadores) |
| OBS-0013 | Auth · Maestros | Defecto | Abierta | Emilio Vargas | ITER-003 | — | JWT inválido devuelve 500 en vez de 401 en todos los maestros |
| OBS-0014 | Maestros > Clientes | Defecto | Abierta | Emilio Vargas | ITER-003 | — | Campo Nombre del cliente sin validación de caracteres ni longitud |
| OBS-0015 | Maestros > Clientes | Mejora | Abierta | Emilio Vargas | ITER-003 | — | Email de contacto solo valida formato, no existencia real |
| OBS-0016 | Maestros > Clientes (UX) | Mejora | Abierta | Emilio Vargas | ITER-003 | — | Teléfono sin selector de código de país (E.164) |
| OBS-0017 | Maestros > Clientes (seguridad) | Defecto | Abierta | Emilio Vargas | ITER-003 | — | Campos VPN visibles en texto plano al crear/editar (inconsistente con modal de detalle) |
| OBS-0018 | Global (formularios) | Mejora | Abierta | Emilio Vargas | ITER-003 | — | Falta feedback claro (inline) cuando la validación falla |
| OBS-0019 | Maestros > Proyectos | Defecto | Abierta | Emilio Vargas | ITER-003 | — | Editar Proyecto ignora el cambio de Cliente en silencio |
| OBS-0020 | Equipo > Perfil extendido (SDD V3) | Defecto | Abierta | Emilio Vargas | ITER-003 | — | Identificación acepta cualquier carácter y longitud |
| OBS-0021 | Equipo > Perfil extendido (SDD V3) | Mejora | Abierta | Emilio Vargas | ITER-003 | — | Nacionalidad es input libre en vez de lista de países |
| OBS-0022 | Equipo > Perfil extendido (SDD V3) | Defecto | Abierta | Emilio Vargas | ITER-003 | — | Fecha de nacimiento sin validación de edad mínima |
| OBS-0023 | Equipo > Perfil extendido (SDD V3) | Mejora | Abierta | Emilio Vargas | ITER-003 | — | Nivel de estudios es input libre en vez de catálogo |
| OBS-0024 | Equipo > Perfil extendido (SDD V3) | Mejora | Abierta | Emilio Vargas | ITER-003 | — | Equipo es input libre en vez de catálogo administrable |
| OBS-0025 | Roles y Permisos | Defecto | Abierta | Emilio Vargas | ITER-003 | — | Matriz de permisos muestra celdas vacías y omite 9 permisos reales |
| OBS-0026 | Tickets > Cierre · Cronómetro | Defecto | Abierta | Emilio Vargas | ITER-003 | — | Ticket se puede cerrar sin tiempo registrado (cronómetro sin efecto) |
| OBS-0027 | Autenticación > Frontend authStore | Mejora | Abierta | Emilio Vargas | ITER-003 | — | Múltiples usuarios simultáneos en el mismo navegador (postura de seguridad a definir) |
| OBS-0028 | Tickets > Listados | Mejora | Abierta | Emilio Vargas | ITER-003 | — | Listados de tickets sin ordenamiento útil por urgencia real |
