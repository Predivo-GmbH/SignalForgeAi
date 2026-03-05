-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create hypertable for candles (run after table creation by Alembic)
-- This is idempotent due to if_not_exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'candles') THEN
        PERFORM create_hypertable('candles', 'time', if_not_exists => TRUE);

        -- Enable compression on candles older than 7 days
        ALTER TABLE candles SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'symbol,exchange,timeframe'
        );
        SELECT add_compression_policy('candles', INTERVAL '7 days', if_not_exists => TRUE);
    END IF;
END
$$;
