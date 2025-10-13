-- BTC Watcher Database Initialization Script
-- This script creates all necessary database tables and indexes

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pg_trgm for full-text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create enum types
CREATE TYPE user_role AS ENUM ('user', 'admin', 'superuser');
CREATE TYPE strategy_status AS ENUM ('stopped', 'starting', 'running', 'stopping', 'error');
CREATE TYPE signal_action AS ENUM ('buy', 'sell', 'hold');
CREATE TYPE strength_level AS ENUM ('strong', 'medium', 'weak', 'ignore');
CREATE TYPE notification_status AS ENUM ('pending', 'sending', 'sent', 'failed', 'cancelled');
CREATE TYPE notification_priority AS ENUM ('P0', 'P1', 'P2');
CREATE TYPE proxy_type AS ENUM ('http', 'https', 'socks5');

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    last_login TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(is_active);

-- Proxies table
CREATE TABLE IF NOT EXISTS proxies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    proxy_type VARCHAR(20) NOT NULL,
    host VARCHAR(100) NOT NULL,
    port INTEGER NOT NULL,
    username VARCHAR(100),
    password VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_healthy BOOLEAN DEFAULT TRUE,
    health_check_url VARCHAR(255) DEFAULT 'https://api.binance.com/api/v3/ping',
    success_rate FLOAT DEFAULT 100.0,
    avg_latency_ms FLOAT,
    last_check_at TIMESTAMP WITH TIME ZONE,
    last_success_at TIMESTAMP WITH TIME ZONE,
    last_failure_at TIMESTAMP WITH TIME ZONE,
    total_requests INTEGER DEFAULT 0,
    successful_requests INTEGER DEFAULT 0,
    failed_requests INTEGER DEFAULT 0,
    consecutive_failures INTEGER DEFAULT 0,
    max_consecutive_failures INTEGER DEFAULT 3,
    health_check_interval INTEGER DEFAULT 3600,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_proxies_active ON proxies(is_active);
CREATE INDEX idx_proxies_healthy ON proxies(is_healthy);

-- Strategies table
CREATE TABLE IF NOT EXISTS strategies (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    strategy_class VARCHAR(100) NOT NULL,
    version VARCHAR(20) DEFAULT 'v1.0',
    exchange VARCHAR(50) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    pair_whitelist JSONB NOT NULL,
    pair_blacklist JSONB DEFAULT '[]'::jsonb,
    dry_run BOOLEAN DEFAULT TRUE,
    dry_run_wallet FLOAT DEFAULT 1000.0,
    stake_amount FLOAT,
    max_open_trades INTEGER DEFAULT 3,
    signal_thresholds JSONB NOT NULL,
    proxy_id INTEGER REFERENCES proxies(id) ON DELETE SET NULL,
    status VARCHAR(20) DEFAULT 'stopped',
    is_active BOOLEAN DEFAULT TRUE,
    port INTEGER,
    process_id INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    started_at TIMESTAMP WITH TIME ZONE,
    stopped_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_strategies_user ON strategies(user_id);
CREATE INDEX idx_strategies_status ON strategies(status);
CREATE INDEX idx_strategies_active ON strategies(is_active);
CREATE INDEX idx_strategies_port ON strategies(port);

-- Signals table (with partitioning support)
CREATE TABLE IF NOT EXISTS signals (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
    pair VARCHAR(20) NOT NULL,
    action VARCHAR(10) NOT NULL,
    signal_strength FLOAT NOT NULL CHECK (signal_strength >= 0 AND signal_strength <= 1),
    strength_level VARCHAR(10) NOT NULL,
    current_rate FLOAT NOT NULL,
    entry_price FLOAT,
    exit_price FLOAT,
    profit_ratio FLOAT,
    profit_abs FLOAT,
    trade_duration INTEGER,
    indicators JSONB,
    metadata JSONB,
    notes TEXT,
    freqtrade_trade_id INTEGER,
    open_date TIMESTAMP WITH TIME ZONE,
    close_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_signals_strategy ON signals(strategy_id);
CREATE INDEX idx_signals_pair ON signals(pair);
CREATE INDEX idx_signals_action ON signals(action);
CREATE INDEX idx_signals_strength_level ON signals(strength_level);
CREATE INDEX idx_signals_created_at ON signals(created_at DESC);
CREATE INDEX idx_signals_strategy_pair_created ON signals(strategy_id, pair, created_at DESC);
CREATE INDEX idx_signals_pair_action_created ON signals(pair, action, created_at DESC);
CREATE INDEX idx_signals_strength_created ON signals(strength_level, created_at DESC);

-- Notifications table
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    signal_id INTEGER NOT NULL REFERENCES signals(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    notification_type VARCHAR(20) NOT NULL,
    priority VARCHAR(10) NOT NULL,
    channel VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    data JSONB,
    recipient VARCHAR(100) NOT NULL,
    sent_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE,
    read_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_notifications_signal ON notifications(signal_id);
CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_status ON notifications(status);
CREATE INDEX idx_notifications_priority ON notifications(priority);
CREATE INDEX idx_notifications_created_at ON notifications(created_at DESC);
CREATE INDEX idx_notifications_status_priority_created ON notifications(status, priority, created_at DESC);
CREATE INDEX idx_notifications_user_created ON notifications(user_id, created_at DESC);

-- Capacity history table (for monitoring)
CREATE TABLE IF NOT EXISTS capacity_history (
    id SERIAL PRIMARY KEY,
    max_strategies INTEGER NOT NULL,
    running_strategies INTEGER NOT NULL,
    available_slots INTEGER NOT NULL,
    utilization_percent FLOAT NOT NULL,
    port_range VARCHAR(20) NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_capacity_history_recorded_at ON capacity_history(recorded_at DESC);

-- System logs table
CREATE TABLE IF NOT EXISTS system_logs (
    id SERIAL PRIMARY KEY,
    level VARCHAR(20) NOT NULL,
    source VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_system_logs_level ON system_logs(level);
CREATE INDEX idx_system_logs_source ON system_logs(source);
CREATE INDEX idx_system_logs_created_at ON system_logs(created_at DESC);

-- Create default admin user (password: admin123)
-- Note: This should be changed in production
INSERT INTO users (username, email, hashed_password, is_superuser)
VALUES (
    'admin',
    'admin@btc-watcher.local',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5/JDpX/0/VmJW',
    TRUE
) ON CONFLICT (username) DO NOTHING;

-- Create update timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_strategies_updated_at BEFORE UPDATE ON strategies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_signals_updated_at BEFORE UPDATE ON signals
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_notifications_updated_at BEFORE UPDATE ON notifications
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_proxies_updated_at BEFORE UPDATE ON proxies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO btc_watcher;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO btc_watcher;

-- Log initialization
INSERT INTO system_logs (level, source, message)
VALUES ('INFO', 'database', 'Database initialization completed successfully');

-- Display summary
SELECT
    'Database initialized successfully' as status,
    COUNT(DISTINCT tablename) as tables_created
FROM pg_tables
WHERE schemaname = 'public' AND tablename IN (
    'users', 'proxies', 'strategies', 'signals',
    'notifications', 'capacity_history', 'system_logs'
);
