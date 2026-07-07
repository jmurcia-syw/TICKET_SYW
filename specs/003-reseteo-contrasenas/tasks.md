# Tasks: Reseteo de Contraseñas y Credenciales Semilla Estables

**Input**: Design documents from `specs/003-reseteo-contrasenas/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Organization**: Tareas agrupadas por User Story para implementación y validación
independiente. Tests incluidos (mismo patrón que el resto del proyecto en `backend/tests/`).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: paralelizable (archivos distintos, sin dependencias incompletas)
- **[Story]**: [US1] reseteo por Admin, [US2] credenciales semilla estables, [US3] auto-recuperación por email

---

## Phase 1: Setup

- [X] T001 Ejecutar la suite de tests actual como línea base (`docker exec sywork_backend python -m pytest tests/ -q`) y confirmar que está en verde antes de iniciar cambios

---

## Phase 2: Foundational (bloqueante para todas las stories)

**No aplica de forma estricta**: las 3 historias de usuario no comparten migración, endpoint ni
componente — cada una es independiente (ver `plan.md` § Project Structure). Se procede directo a
las fases de User Story, en orden de prioridad.

---

## Phase 3: User Story 1 — Reseteo de contraseña por Admin (P1) 🎯 MVP

**Goal**: un administrador restablece el acceso de un usuario real generando una contraseña
temporal, sin depender de logs. **Independent Test**: Escenario 2 de `quickstart.md`.

- [X] T002 [P] [US1] Agregar `UserRepository.set_password(user_id, password_hash)` en
  `backend/infra/repositories/user_repo.py`
- [X] T003 [US1] Agregar clase `UserResetPassword` (`PATCH /api/users/<id>/reset-password`) en
  `backend/api/routes/users.py`: genera `secrets.token_urlsafe(9)`, hashea con
  `AuthService.hash_password` (ya existente), llama a `UserRepository.set_password` (T002),
  responde `{id, provisional_password}`; `404` si el usuario no existe. Agregar la clase a la
  lista `for _cls in (...)` de `enforce_module("users")` (línea ~297) — depende de T002
- [X] T004 [P] [US1] Test de integración en `backend/tests/api/test_users_api.py`: reseteo `200`
  con contraseña nueva funcional (login exitoso con ella), `404` usuario inexistente, `403` sin
  permiso `users:edit` — depende de T003
- [X] T005 [US1] Agregar `resetPassword(id)` en `frontend/src/services/userService.ts` (PATCH a
  `/api/users/{id}/reset-password`) — depende de T003
- [X] T006 [US1] Botón "Resetear contraseña" (icono llave) en columna Acciones de
  `frontend/src/pages/UsersPage.tsx`, con `ConfirmationModal` previa, reutilizando el modal
  existente "Contraseña provisional generada" (líneas 186-203) para mostrar la respuesta — depende
  de T005

**Checkpoint**: Escenario 2 de `quickstart.md` pasa completo — un usuario real recupera acceso
sin tocar logs.

---

## Phase 4: User Story 2 — Credenciales semilla estables en Desarrollo (P2)

**Goal**: las 4 cuentas de demostración quedan con la misma contraseña en cada instalación de
Desarrollo, documentada. **Independent Test**: Escenario 1 de `quickstart.md`.

- [X] T007 [US2] Modificar `backend/infra/migrations/versions/009_roles_permissions_login.py`:
  agregar `import os`, constante `SEED_PASSWORD_DEV = "SyWork_Dev2026!"`, condicionar
  `provisional_password` a `SEED_PASSWORD_DEV if os.environ.get("FLASK_ENV") != "production" else secrets.token_urlsafe(9)`
- [X] T008 [P] [US2] Crear `docs/credenciales_dev.txt` con la tabla de los 4 usuarios semilla
  (usuario/email, rol, contraseña en base64: `U3lXb3JrX0RldjIwMjYh`)
- [ ] T009 [US2] Verificar en un entorno limpio (`docker compose down -v && docker compose up --build`)
  que los 4 usuarios semilla quedan con la contraseña fija; repetir con `FLASK_ENV=production` y
  confirmar que sigue siendo aleatoria — depende de T007

**Checkpoint**: Escenario 1 de `quickstart.md` pasa completo — cero dependencia de logs para
instalar en un equipo nuevo.

---

## Phase 5: User Story 3 — Auto-recuperación de contraseña por email (P3)

**Goal**: un usuario recupera su propia contraseña sin depender de un administrador.
**Independent Test**: Escenario 3 de `quickstart.md`.

- [X] T010 [US3] Migración `backend/infra/migrations/versions/014_password_reset_tokens.py`:
  agrega `reset_token` (text, nullable, único) y `reset_token_expires_at` (timestamptz, nullable)
  a `users`
- [X] T011 [P] [US3] `AuthService` (`backend/domain/services/auth_service.py`): agregar
  `generate_reset_token()` (`secrets.token_urlsafe(32)` + expiración a 30 min) e
  `is_reset_token_valid(user, token)` (coincide, no expiró, `user.active`) — depende de T010
- [X] T012 [P] [US3] `UserRepository` (`backend/infra/repositories/user_repo.py`): agregar
  `set_reset_token(user_id, token, expires_at)`, `get_by_reset_token(token)`,
  `clear_reset_token(user_id)` — depende de T010
- [X] T013 [US3] Helper de envío de correo en `backend/infra/email/mailer.py` (nuevo): usa
  `smtplib` + `email.mime.text.MIMEText` (stdlib), lee `SMTP_HOST/PORT/USER/PASSWORD/FROM` de
  variables de entorno
- [X] T014 [US3] Endpoint público `POST /api/auth/forgot-password` en
  `backend/api/routes/auth.py`: busca por email, si existe cuenta activa genera+guarda token
  (T011, T012) y envía correo (T013); responde `200` genérico siempre, exista o no la cuenta —
  depende de T011, T012, T013
- [X] T015 [US3] Endpoint público `POST /api/auth/reset-password` en
  `backend/api/routes/auth.py`: valida el token (T011), actualiza `password_hash` vía
  `UserRepository.set_password` (T002) y limpia el token (T012); `400` genérico si inválido/
  expirado/usado/cuenta inactiva — depende de T002, T011, T012
- [X] T016 [P] [US3] (docker-compose.yml hecho; .env.example bloqueado por permisos del entorno — pendiente que el usuario lo agregue manualmente) Agregar `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`
  al `environment` del servicio `backend` en `docker-compose.yml` y a `.env.example`
- [X] T017 [P] [US3] Tests en `backend/tests/domain/test_auth_service.py`: token válido acepta,
  expirado rechaza, usado una vez no es reutilizable, cuenta inactiva rechaza — depende de T011
- [X] T018 [P] [US3] Tests de integración en `backend/tests/api/test_auth_login_api.py`:
  `forgot-password` con email existente/inexistente → mismo `200`; `reset-password` con token
  válido/expirado/inexistente/cuenta inactiva → depende de T014, T015
- [X] T019 [P] [US3] Agregar `forgotPassword(email)` y `resetPassword(token, newPassword)` en
  `frontend/src/services/authService.ts` — depende de T014, T015
- [X] T020 [US3] Link "¿Olvidaste tu contraseña?" + formulario de solicitud en
  `frontend/src/pages/LoginPage.tsx` — depende de T019
- [X] T021 [US3] Nueva pantalla `frontend/src/pages/ResetPasswordPage.tsx` (ruta pública
  `/reset-password`, lee `?token=` de la URL) y su registro en el router — depende de T019

**Checkpoint**: Escenario 3 de `quickstart.md` pasa completo — un usuario recupera su contraseña
sin ningún administrador de por medio.

---

## Final Phase: Polish & Cross-Cutting Concerns

- [X] T022 Ejecutar `quickstart.md` completo (los 3 escenarios) de punta a punta — **validado por
  el usuario en su entorno real** (Docker/Postgres): Escenario 1 (US2, contraseña semilla fija),
  Escenario 2 (US1, reseteo por Admin) y Escenario 3 (US3, recuperación por email, incluida la
  no-reutilización del token) confirmados funcionando
- [X] T023 [P] Revisar que ningún log/documento adicional (fuera de `docs/credenciales_dev.txt`,
  ya acordado) exponga la contraseña semilla o credenciales SMTP
- [X] T024 [P] Actualizar `README.md` / `docs/GUIA_DESPLIEGUE_SYWORK_TICKETS.txt` si mencionan
  el flujo viejo de contraseña semilla aleatoria por logs

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias — puede iniciar de inmediato
- **Foundational (Phase 2)**: no aplica, ver nota arriba
- **User Stories (Phase 3-5)**: independientes entre sí; pueden hacerse en paralelo o en el
  orden de prioridad P1 → P2 → P3
- **Polish (Final Phase)**: depende de que las historias que se vayan a entregar estén completas

### Dentro de cada historia

- US1: T002 → T003 → (T004 en paralelo con T005) → T006
- US2: T007 → T009 (T008 en paralelo, no depende de T007)
- US3: T010 → (T011, T012 en paralelo) → T013 → T014 → T015 → (T016, T017, T018, T019 en
  paralelo) → (T020, T021 en paralelo, ambos dependen de T019)

### Oportunidades de paralelismo

- T002 (US1) y T007-T008 (US2) pueden empezar en paralelo — no comparten archivo
- Dentro de US3: T011 y T012 en paralelo (archivos distintos); T016-T019 en paralelo una vez
  existen T014/T015
- Si hay más de una persona: Developer A toma US1, Developer B toma US2/US3 en paralelo, sin
  bloquearse entre sí

---

## Parallel Example: User Story 3

```bash
# Una vez completados T010 (migración) y T013 (mailer):
Task: "Implementar POST /api/auth/forgot-password en backend/api/routes/auth.py"
Task: "Agregar SMTP_HOST/PORT/USER/PASSWORD/FROM a docker-compose.yml y .env.example"

# Una vez completados T014 y T015:
Task: "Tests de dominio de reset_token en backend/tests/domain/test_auth_service.py"
Task: "Tests de integración forgot/reset-password en backend/tests/api/test_auth_login_api.py"
Task: "forgotPassword/resetPassword en frontend/src/services/authService.ts"
```

---

## Implementation Strategy

### MVP First (User Story 1 solamente)

1. Completar Phase 1: Setup
2. Completar Phase 3: User Story 1 (reseteo por Admin)
3. **Detener y validar**: Escenario 2 de `quickstart.md` de punta a punta
4. Esto ya resuelve el problema más urgente (usuarios reales bloqueados) sin esperar a US2/US3

### Entrega incremental

1. Setup → User Story 1 (MVP, resuelve el bloqueo real) → validar → desplegar
2. + User Story 2 (credenciales semilla estables) → validar → desplegar
3. + User Story 3 (auto-recuperación por email) → validar → desplegar
4. Cada historia suma valor sin romper las anteriores

---

## Notes

- Sin dependencias nuevas de terceros — `smtplib`/`email.mime` son stdlib de Python (Principio V
  ya evaluado en `plan.md`)
- T002 (`UserRepository.set_password`) es compartido por US1 y US3 — al ser la primera tarea de
  US1, US3 puede reusarla directamente en T015 sin duplicar código
- Verificar que los tests fallen antes de implementar donde aplique (T004, T017, T018)
- Commitear después de cada tarea o grupo lógico, igual que el resto del proyecto
