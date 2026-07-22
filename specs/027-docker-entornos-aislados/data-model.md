# Data Model: Configuración de Entornos Aislados (Test y Producción) en Docker Compose

Esta feature no introduce ni modifica entidades de negocio ni tablas de base de datos. Es un
cambio de configuración de infraestructura (Docker Compose + variables de entorno + documentación
técnica); el esquema de PostgreSQL (`backend/infra/migrations/`, revisión `040`) no se toca.

No aplica una sección de "Key Entities" — se omite del `spec.md` por la misma razón (ver plantilla
del spec: "include if feature involves data").

## Configuración por ambiente (no es una entidad de datos, es config operativa)

A efectos de trazabilidad de la Fase 1, se documenta aquí la forma de la configuración que cada
ambiente necesita (detalle completo de variables en `research.md`, Decisión 4):

| Concepto | Dónde vive | Persistencia |
|---|---|---|
| Nombre de proyecto Compose (`sywork_test` / `sywork_prod`) | Flag `-p` o `COMPOSE_PROJECT_NAME` en el archivo de ambiente | No persiste en BD — solo en el archivo `.env.test`/`.env.prod` del servidor |
| Puertos publicados (`FRONTEND_PORT`, `BACKEND_PORT`, `POSTGRES_PORT`, `REDIS_PORT`) | Variables interpoladas en `docker-compose.yml` | Igual que arriba |
| Secretos/credenciales (`JWT_SECRET`, `POSTGRES_PASSWORD`, `SMTP_*`, `GOOGLE_CLIENT_*`) | Variables en `.env.test`/`.env.prod` | Nunca en git (`.gitignore`); nunca en base de datos |
| Datos de aplicación (tickets, clientes, usuarios, etc.) | Volumen `postgres_data` namespaced por ambiente | Completamente separado entre Test y Producción — cada ambiente tiene su propio volumen físico |
