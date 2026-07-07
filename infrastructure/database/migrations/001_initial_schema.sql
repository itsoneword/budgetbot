-- BudgetBot Initial Schema
-- Migration: 001_initial_schema.sql
-- Created: 2025-01-25

-- ============================================
-- USERS TABLE
-- Source: user_list.csv
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username TEXT,
    telegram_username TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- USER CONFIGURATIONS
-- Source: user_data/<id>/config.ini
-- ============================================
CREATE TABLE IF NOT EXISTS user_configs (
    user_id BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    language VARCHAR(10) DEFAULT 'en',
    currency CHAR(3) DEFAULT 'EUR',
    monthly_limit DECIMAL(15,2) DEFAULT 99999999.00,
    name TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- USER CATEGORIES (Dictionary)
-- Source: user_data/<id>/dictionary_<id>.json
-- ============================================
CREATE TABLE IF NOT EXISTS user_categories (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    language VARCHAR(10) NOT NULL DEFAULT 'en',
    category_name TEXT NOT NULL,
    subcategory_name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, language, category_name, subcategory_name)
);

CREATE INDEX IF NOT EXISTS idx_categories_user_lang 
    ON user_categories(user_id, language);

-- ============================================
-- TRANSACTIONS
-- Source: user_data/<id>/spendings_<id>.csv
-- ============================================
CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ NOT NULL,
    transaction_type VARCHAR(10) NOT NULL DEFAULT 'spending',  -- 'spending' | 'income'
    category_name TEXT NOT NULL,
    subcategory_name TEXT NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    currency CHAR(3) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_transaction_type CHECK (transaction_type IN ('spending', 'income'))
);
CREATE OR REPLACE FUNCTION date_trunc_month(ts TIMESTAMPTZ)  -- or TIMESTAMP
RETURNS TIMESTAMPTZ IMMUTABLE STRICT
LANGUAGE sql AS $$ SELECT date_trunc('month', ts AT TIME ZONE 'UTC'); $$;

-- Performance indexes for common queries
CREATE INDEX IF NOT EXISTS idx_transactions_user_timestamp 
    ON transactions(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_user_month 
ON transactions(user_id, date_trunc_month(timestamp));

CREATE INDEX IF NOT EXISTS idx_transactions_user_category 
    ON transactions(user_id, category_name);
CREATE INDEX IF NOT EXISTS idx_transactions_user_type 
    ON transactions(user_id, transaction_type);

-- ============================================
-- EXCHANGE RATES CACHE
-- Source: configs/exchangerates.json
-- ============================================
CREATE TABLE IF NOT EXISTS exchange_rates (
    base_currency CHAR(3) NOT NULL,
    target_currency CHAR(3) NOT NULL,
    rate DECIMAL(15,6) NOT NULL,
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (base_currency, target_currency)
);

-- ============================================
-- MIGRATION LOG (for tracking migration progress)
-- ============================================
CREATE TABLE IF NOT EXISTS migration_log (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    migration_type VARCHAR(50) NOT NULL,  -- 'user', 'config', 'categories', 'transactions'
    source_file TEXT,
    records_count INTEGER DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- 'pending', 'success', 'failed'
    error_message TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply to users table
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply to user_configs table
DROP TRIGGER IF EXISTS update_user_configs_updated_at ON user_configs;
CREATE TRIGGER update_user_configs_updated_at
    BEFORE UPDATE ON user_configs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
