-- Migration 002: Candles & Pipeline Logs

-- Candles (composite PK — standard PostgreSQL, no TimescaleDB)
create table candles (
  time timestamptz not null,
  symbol varchar(20) not null,
  exchange varchar(20) not null,
  timeframe varchar(5) not null,
  open double precision not null,
  high double precision not null,
  low double precision not null,
  close double precision not null,
  volume double precision not null,
  vwap double precision,
  trades integer,
  primary key (time, symbol, exchange, timeframe)
);
create index idx_candles_symbol on candles(symbol, timeframe, time);

-- Pipeline Logs
create table pipeline_logs (
  id uuid primary key default gen_random_uuid(),
  strategy_id uuid not null references strategies(id) on delete cascade,
  symbol varchar(20) not null,
  timeframe varchar(10) not null,
  action varchar(10) not null,
  block_reason varchar(40),
  confluence_score integer,
  regime varchar(20),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index ix_pipeline_logs_strategy_created on pipeline_logs(strategy_id, created_at);
create index ix_pipeline_logs_created_at on pipeline_logs(created_at);

create trigger trg_pipeline_logs_updated_at before update on pipeline_logs for each row execute function update_updated_at();
