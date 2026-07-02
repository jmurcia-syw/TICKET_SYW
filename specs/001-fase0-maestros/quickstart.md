# Quickstart — Validacion Fase 0: Maestros

**Feature**: specs/001-fase0-maestros
**Date**: 2026-06-29

Esta guia valida que la implementacion funciona de extremo a extremo antes de pasar a Fase 1.

---

## Prerequisitos

1. Docker Desktop corriendo
2. `.env` configurado con variables requeridas (ver README.md)
3. Proyecto levantado: `docker compose up --build`
4. Servicios saludables:
   - Backend: `http://localhost:5000/swagger` debe responder
   - Frontend: `http://localhost:5173` debe cargar
   - DB: `docker compose ps` muestra `sywork_db` healthy

---

## Escenario 1 — Login y RBAC basico

1. Abrir `http://localhost:5173`
2. Hacer click en "Iniciar sesion con Google"
3. Autenticarse con cuenta `@sywork.net`
4. **Resultado esperado**: Redireccion al dashboard. JWT visible en DevTools > Application > LocalStorage
5. Intentar acceder a `http://localhost:5173/clients` con un usuario de rol Resolutor
6. **Resultado esperado**: Ve el listado de clientes (permiso `clients: view`) sin botones de
   crear/editar/desactivar, y sin los campos VPN sensibles (reservados a Admin/Coordinador)
7. Intentar acceder a `http://localhost:5173/roles` (Roles y Permisos) con un usuario de rol
   Coordinador o QM
8. **Resultado esperado**: El menu "Roles y Permisos" no aparece (ningun permiso sobre `roles`)

**Validacion API** (enforcement de backend diferido a fase futura, ver FR-017 — hoy no hay 401/403
reales en las rutas de maestros):
```bash
curl http://localhost:5000/api/clients
# Login provisional y verificacion de permisos devueltos:
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username_or_email": "resolutor@sywork.net", "password": "<password-de-la-migracion>"}'
# El campo "permissions" debe incluir {"module": "clients", "action": "view"} pero NO
# {"module": "clients", "action": "create"}
```

---

## Escenario 2 — CRUD de Clientes (Admin)

1. Iniciar sesion con usuario Admin
2. Ir a "Clientes" en el menu lateral
3. Crear cliente:
   - Nombre: "Empresa Test SA"
   - Email contacto: "contacto@test.com"
   - VPN IPs: "192.168.1.1"
   - VPN Credentials: "user: admin / pass: test123"
4. **Resultado esperado**: Cliente aparece en la lista con badge "Activo"
5. Abrir el detalle del cliente
6. **Resultado esperado**: VPN IPs y credenciales son visibles en el detalle
7. Intentar crear otro cliente con el mismo nombre "Empresa Test SA"
8. **Resultado esperado**: Error visible junto al campo "Ya existe un cliente con ese nombre"

**Validacion de cifrado**:
```bash
# Verificar en DB que la columna esta cifrada (no texto plano)
docker exec -it sywork_db psql -U <user> -d sywork \
  -c "SELECT vpn_ips FROM clients WHERE name = 'Empresa Test SA';"
# Debe mostrar datos binarios (bytea), no texto legible
```

---

## Escenario 3 — Cascade de desactivacion de cliente

1. Crear un cliente con 2 proyectos activos
2. Intentar desactivar el cliente
3. **Resultado esperado**: Dialogo de confirmacion mostrando:
   - "Este cliente tiene 2 proyectos activos"
   - "Confirmar desactivacion"
4. Confirmar la desactivacion
5. **Resultado esperado**: Cliente aparece como "Inactivo" en la lista
6. Intentar crear un proyecto nuevo para ese cliente
7. **Resultado esperado**: Error "No se puede crear un proyecto para un cliente inactivo"

---

## Escenario 4 — Gestion de Recursos y Skills

1. Como Admin, ir a "Configuracion > Skills"
2. Crear skill: Code: "JDE_AP", Label: "JDE Accounts Payable"
3. Ir a "Recursos" y crear un recurso nuevo:
   - Nombre: "Ana Perez"
   - Email: "ana.perez@sywork.net"
   - Asignar skill: JDE_AP
4. **Resultado esperado**: Recurso aparece en la lista con skill visible
5. Filtrar la lista de recursos por skill "JDE_AP"
6. **Resultado esperado**: Solo muestra "Ana Perez"
7. Intentar eliminar el skill "JDE_AP" desde Configuracion
8. **Resultado esperado**: Error "El skill esta asignado a 1 recurso activo"

---

## Escenario 5 — RBAC de Recurso (Resolutor ve solo su perfil; QM tiene CRUD completo)

1. Iniciar sesion como usuario Resolutor (ej. Carlos)
2. Ir a "Recursos"
3. **Resultado esperado**: Solo ve su propio perfil, no el de otros recursos
4. Intentar acceder via URL directa al perfil de otro recurso:
   `http://localhost:5173/resources/<id-de-otro-recurso>`
5. **Resultado esperado**: Redireccion o mensaje "Acceso denegado"
6. Cerrar sesion e iniciar sesion como usuario QM
7. Ir a "Recursos"
8. **Resultado esperado**: Ve todos los recursos y puede crear/editar/desactivar (FR-013 —
   mismo nivel de acceso que Admin/Coordinador)

**Validacion API**:
```bash
# Token de Carlos (Resolutor) intentando GET del recurso de Ana — debe devolver 403
curl -H "Authorization: Bearer <token-carlos>" \
  http://localhost:5000/api/resources/<id-ana>
```

---

## Escenario 6 — Regla del ultimo Admin

1. Iniciar sesion como Admin
2. Ir a "Usuarios"
3. Intentar cambiar el rol del unico Admin a "Coordinador"
4. **Resultado esperado**: Error "No se puede cambiar el rol del ultimo Admin activo"
5. Intentar desactivar la cuenta del unico Admin
6. **Resultado esperado**: Error "No se puede desactivar al ultimo Admin activo"

---

## Escenario 7 — Login provisional usuario/contraseña (FR-022b)

1. Abrir `http://localhost:5173/login`
2. Usar el formulario "Iniciar sesion con usuario y contraseña" (alternativa a Google)
3. Ingresar `username_or_email` + `password` de una cuenta con `password_hash` asignado
4. **Resultado esperado**: Acceso equivalente al login por Google (mismo token, mismo rol y
   permisos visibles en el menu)

**Validacion API**:
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username_or_email": "carlos.rodriguez", "password": "secreto123"}'
# Debe devolver { access_token, user: { role: { name, ... }, permissions: [...] } }
```

---

## Escenario 8 — Roles dinamicos y permisos granulares (FR-015, FR-015b)

1. Iniciar sesion como Admin, ir a "Roles y Permisos"
2. Crear un rol nuevo: nombre "Auditor", sin permisos
3. Asignarle permisos via la matriz modulo x accion: `clients.view`, `resources.view`
4. **Resultado esperado**: El rol "Auditor" queda disponible en el selector de "Usuarios"
5. Asignar el rol "Auditor" a un usuario existente y volver a iniciar sesion con esa cuenta
6. **Resultado esperado**: El menu solo muestra "Clientes" y "Recursos" (segun sus permisos `view`)
7. Intentar eliminar un permiso que esta asignado al rol "Auditor"
8. **Resultado esperado**: Error 409 "El permiso esta asignado a al menos un rol"

---

## Escenario 9 — Reactivacion de registros inactivos

1. Como Admin, desactivar un cliente, un proyecto y un recurso (uno por uno)
2. **Resultado esperado**: Cada uno aparece como "Inactivo" en su lista
3. Desde la pantalla de detalle de cada uno, usar la accion "Reactivar"
4. **Resultado esperado**: Cada registro vuelve a aparecer como "Activo" y disponible en
   selectores (ej. el cliente reactivado vuelve a aparecer en el selector de nuevo proyecto)

---

## Escenario 10 — Alta de usuario nuevo (FR-018b)

1. Iniciar sesion como Admin, ir a "Usuarios"
2. Click en "Nuevo usuario"; completar email `nuevo.consultor@sywork.net`, username
   `nuevo.consultor`, rol "Resolutor"
3. **Resultado esperado**: El sistema muestra una contraseña provisional una unica vez, en un
   modal con aviso de que no se volvera a mostrar
4. Cerrar sesion e iniciar sesion con `nuevo.consultor` + la contraseña mostrada
5. **Resultado esperado**: Acceso exitoso, con el rol y permisos de Resolutor
6. Intentar crear un usuario con email `otro@gmail.com` (dominio distinto)
7. **Resultado esperado**: Error de validacion, dominio invalido
8. Intentar crear un usuario con el mismo email `nuevo.consultor@sywork.net` de nuevo
9. **Resultado esperado**: Error 409, email duplicado

**Validacion API**:
```bash
curl -X POST http://localhost:5000/api/users \
  -H "Content-Type: application/json" \
  -d '{"email": "nuevo.consultor@sywork.net", "username": "nuevo.consultor", "role_id": "<uuid-resolutor>"}'
# Debe devolver 201 con { user: {...}, provisional_password: "..." }
```

---

## Checklist de validacion final

Antes de marcar Fase 0 como completada:

- [ ] Login Google OAuth2 funciona con @sywork.net
- [ ] Login rechazado para cuentas fuera de @sywork.net
- [ ] CRUD de Clientes funcional para Admin y Coordinador
- [ ] Datos sensibles (VPN) cifrados en DB, visibles solo para Admin/Coordinador
- [ ] CRUD de Proyectos funcional, validaciones de cliente activo y fechas
- [ ] CRUD de Recursos funcional, filtro por skill operativo
- [ ] Resolutor solo ve su propio perfil (UI y API)
- [ ] QM tiene el mismo acceso completo que Admin/Coordinador sobre Recursos y Skills (FR-013)
- [ ] Admin puede dar de alta un usuario nuevo con contraseña provisional mostrada una unica vez
- [ ] Skills: creacion y bloqueo de eliminacion cuando en uso
- [ ] Regla del ultimo Admin activa (cambio de rol y desactivacion)
- [ ] Usuarios desactivados no pueden acceder aunque el JWT sea valido
- [ ] Login provisional usuario/contraseña funciona con el mismo resultado que Google OAuth2
- [ ] Roles dinamicos: Admin puede crear un rol, asignarle permisos y verlo reflejado en el menu
- [ ] Clientes, Proyectos y Recursos pueden reactivarse despues de desactivarse
- [ ] Todas las validaciones muestran mensajes en espanol en el formulario
- [ ] Swagger en http://localhost:5000/swagger muestra todos los endpoints documentados
