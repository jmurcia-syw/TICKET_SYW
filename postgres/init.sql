-- Extensiones necesarias (único trabajo de init.sql)
-- Las tablas son creadas y gestionadas por Alembic
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

DO $$ BEGIN
    RAISE NOTICE 'SYWork DB: extensiones instaladas. Alembic creará las tablas.';
END $$;
