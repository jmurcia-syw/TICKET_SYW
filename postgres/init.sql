-- Habilitar extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Crear esquema principal
CREATE SCHEMA IF NOT EXISTS sywork;

-- Tabla de usuarios
CREATE TABLE IF NOT EXISTS users (
    id          SERIAL PRIMARY KEY,
    email       VARCHAR(255) UNIQUE NOT NULL,
    name        VARCHAR(255) NOT NULL,
    role        VARCHAR(50) NOT NULL DEFAULT 'resolver',
    skills      JSONB DEFAULT '[]',
    active      BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMP DEFAULT NOW()
);

-- Habilitar RLS en users
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Mensaje de confirmación
DO $$ BEGIN
    RAISE NOTICE 'SYWork DB inicializada correctamente';
END $$;
