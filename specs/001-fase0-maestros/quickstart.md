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
5. Intentar acceder a `http://localhost:5173/clients` con un usuario de rol Resolver
6. **Resultado esperado**: Redireccion al dashboard con mensaje "Acceso denegado"

**Validacion API**:
```bash
# Sin token — debe devolver 401
curl http://localhost:5000/api/clients

# Con token de Resolver — debe devolver 403
curl -H "Authorization: Bearer <token-resolver>" http://localhost:5000/api/clients
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

## Escenario 5 — RBAC de Recurso (Resolver ve solo su perfil)

1. Iniciar sesion como usuario Resolver (ej. Carlos)
2. Ir a "Recursos"
3. **Resultado esperado**: Solo ve su propio perfil, no el de otros recursos
4. Intentar acceder via URL directa al perfil de otro recurso:
   `http://localhost:5173/resources/<id-de-otro-recurso>`
5. **Resultado esperado**: Redireccion o mensaje "Acceso denegado"

**Validacion API**:
```bash
# Token de Carlos intentando GET del recurso de Ana — debe devolver 403
curl -H "Authorization: Bearer <token-carlos>" \
  http://localhost:5000/api/resources/<id-ana>
```

---

## Escenario 6 — Regla del ultimo Admin

1. Iniciar sesion como Admin
2. Ir a "Usuarios"
3. Intentar cambiar el rol del unico Admin a "Coordinator"
4. **Resultado esperado**: Error "No se puede cambiar el rol del ultimo Admin activo"
5. Intentar desactivar la cuenta del unico Admin
6. **Resultado esperado**: Error "No se puede desactivar al ultimo Admin activo"

---

## Checklist de validacion final

Antes de marcar Fase 0 como completada:

- [ ] Login Google OAuth2 funciona con @sywork.net
- [ ] Login rechazado para cuentas fuera de @sywork.net
- [ ] CRUD de Clientes funcional para Admin y Coordinator
- [ ] Datos sensibles (VPN) cifrados en DB, visibles solo para Admin/Coordinator
- [ ] CRUD de Proyectos funcional, validaciones de cliente activo y fechas
- [ ] CRUD de Recursos funcional, filtro por skill operativo
- [ ] Resolver solo ve su propio perfil (UI y API)
- [ ] QM puede ver todos los recursos (solo lectura)
- [ ] Skills: creacion y bloqueo de eliminacion cuando en uso
- [ ] Regla del ultimo Admin activa (cambio de rol y desactivacion)
- [ ] Usuarios desactivados no pueden acceder aunque el JWT sea valido
- [ ] Todas las validaciones muestran mensajes en espanol en el formulario
- [ ] Swagger en http://localhost:5000/swagger muestra todos los endpoints documentados
