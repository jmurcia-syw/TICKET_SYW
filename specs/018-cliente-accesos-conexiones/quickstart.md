# Quickstart — Validación de Accesos y conexiones múltiples del Cliente

Valida las tres observaciones UAT resueltas por este spec: `OBS-0001`, `OBS-0008`, `OBS-0017`.
Ver contratos en [contracts/client-access.md](contracts/client-access.md) y modelo en
[data-model.md](data-model.md).

## Prerrequisitos

- Entorno Docker Compose levantado (`sywork_db`, `sywork_backend`, `sywork_frontend`).
- Migraciones aplicadas hasta `031_client_access_rls` (`alembic upgrade head`).
- Un usuario con rol Admin o Coordinador (permiso `include_sensitive` sobre Clientes).
- Al menos un cliente existente que ya tuviera datos en "IPs VPN"/"Credenciales VPN" antes de
  esta migración (para validar US1, escenario 4 — la migración sin pérdida).

## Escenario 1 — Migración sin pérdida (FR-007/FR-008, SC-004)

1. Antes de migrar, anotar el valor de `vpn_ips`/`vpn_credentials` de un cliente existente
   (`GET /api/clients/{id}` con `include_sensitive`).
2. Aplicar la migración (`alembic upgrade head`).
3. `GET /api/clients/{id}/access` → debe existir exactamente un registro con
   `access_type='vpn'`, `host` = el valor anotado de `vpn_ips`, `password` = el valor anotado de
   `vpn_credentials`.
4. **Resultado esperado**: ningún dato se perdió; el cliente sigue mostrando su información VPN,
   ahora como un registro de acceso.

## Escenario 2 — Registrar múltiples accesos de distintos tipos (US1)

1. En Maestros > Clientes, abrir el detalle/edición de un cliente → pestaña "Accesos y
   conexiones".
2. Agregar un registro tipo "VPN" (usuario, contraseña, host, notas) → guardar.
3. Agregar un segundo registro tipo "URL de sistema", ambiente "TEST" → guardar.
4. Agregar un tercer registro tipo "Escritorio remoto" → guardar.
5. Adjuntar un archivo (ej. `instructivo.pdf`) en la sección de adjuntos.
6. Cerrar y reabrir el detalle del cliente.
7. **Resultado esperado**: los tres registros persisten por separado, con sus propios valores;
   el adjunto sigue disponible para descarga; ninguna de las tres altas requirió tocar el botón
   "Guardar" del formulario principal del cliente (FR-012).

## Escenario 3 — Aislamiento entre clientes (US2 — regresión de `OBS-0008`)

1. Abrir el detalle/edición del Cliente A (con accesos ya cargados del Escenario 2).
2. Cerrar sin guardar cambios en los datos generales.
3. Abrir inmediatamente el detalle/edición del Cliente B (sin accesos, o con accesos distintos).
4. **Resultado esperado**: la pestaña "Accesos y conexiones" del Cliente B muestra únicamente
   sus propios registros (o ninguno) — cero rastros de los accesos del Cliente A.
5. Repetir la secuencia A→B→C (tres clientes) para confirmar que no es una coincidencia del
   primer ciclo.

## Escenario 4 — Enmascarado por defecto (US3 — regresión de `OBS-0017`)

1. Abrir el formulario de edición del cliente del Escenario 2.
2. En la pestaña "Accesos y conexiones", verificar que el campo contraseña de cada fila se
   muestra enmascarado (`Input.Password` o `••••••••`), no en texto plano.
3. Accionar el control de revelado de una fila → confirmar que muestra el valor real.
4. Iniciar sesión con un usuario sin permiso de datos sensibles (rol sin `include_sensitive`) →
   abrir el mismo cliente → confirmar que ve tipo/ambiente de cada acceso pero no puede revelar
   usuario/contraseña (FR-010).

## Verificación de contrato (opcional, vía curl/Swagger UI)

```bash
# Listar accesos (con JWT de un usuario con include_sensitive)
curl -H "Authorization: Bearer $TOKEN" http://localhost:5000/api/clients/$CLIENT_ID/access

# Crear un acceso
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"access_type":"vpn","username":"admin","password":"secret","host":"10.0.0.5"}' \
  http://localhost:5000/api/clients/$CLIENT_ID/access
```

**Resultado esperado**: `201` con el registro creado; `GET` posterior lo incluye en `items[]`.
