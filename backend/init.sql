-- Mamaope Legal AI - Database Initialization Script
-- This script creates the initial database structure and sets up security

-- Create database if it doesn't exist (this will be handled by POSTGRES_DB)
-- CREATE DATABASE IF NOT EXISTS mamaope_legal_ai;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create the application user if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'mamaope_legal') THEN
        CREATE USER mamaope_legal WITH PASSWORD 'SecurePass123!';
    END IF;
END
$$;

-- Grant privileges to the application user
GRANT ALL PRIVILEGES ON DATABASE mamaope_legal_ai TO mamaope_legal;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO mamaope_legal;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO mamaope_legal;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO mamaope_legal;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO mamaope_legal;

-- Set up security
ALTER DATABASE mamaope_legal_ai SET log_statement = 'all';
ALTER DATABASE mamaope_legal_ai SET log_min_duration_statement = 1000;

-- Create a read-only user for monitoring
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'mamaope_monitor') THEN
        CREATE ROLE mamaope_monitor WITH LOGIN PASSWORD 'monitor_password_change_me';
        GRANT CONNECT ON DATABASE mamaope_legal_ai TO mamaope_monitor;
        GRANT USAGE ON SCHEMA public TO mamaope_monitor;
        GRANT SELECT ON ALL TABLES IN SCHEMA public TO mamaope_monitor;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO mamaope_monitor;
    END IF;
END
$$;

-- Create indexes for performance (will be created by Alembic migrations)
-- These are just examples of what will be created

-- Security audit log indexes
-- CREATE INDEX IF NOT EXISTS idx_audit_log_user_action ON audit_logs(user_id, action);
-- CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_logs(created_at);
-- CREATE INDEX IF NOT EXISTS idx_audit_log_success ON audit_logs(success);

-- User table indexes
-- CREATE INDEX IF NOT EXISTS idx_user_email_active ON users(email, is_active);
-- CREATE INDEX IF NOT EXISTS idx_user_username_active ON users(username, is_active);

-- Legal consultation session indexes
-- CREATE INDEX IF NOT EXISTS idx_consultation_user_session ON legal_consultations(user_id, session_id);
-- CREATE INDEX IF NOT EXISTS idx_consultation_created_at ON legal_consultations(created_at);

-- Security event indexes
-- CREATE INDEX IF NOT EXISTS idx_security_event_type ON security_events(event_type);
-- CREATE INDEX IF NOT EXISTS idx_security_severity ON security_events(severity);
-- CREATE INDEX IF NOT EXISTS idx_security_resolved ON security_events(resolved);
-- CREATE INDEX IF NOT EXISTS idx_security_created_at ON security_events(created_at);

-- Log successful initialization
INSERT INTO pg_stat_statements_info (dealloc) VALUES (0) ON CONFLICT DO NOTHING;
