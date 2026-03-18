-- Migration 001: Core Schema
-- profiles, strategies, signals, trades, positions, orders, broker_connections
-- Note: users table is managed by Supabase Auth (auth.users)

-- Profiles (extends auth.users with app-specific settings)
create table profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  alert_config jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Strategies
create table strategies (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  name varchar(255) not null,
  is_active boolean not null default false,
  config jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index ix_strategies_user_id on strategies(user_id);

-- Signals
create table signals (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade,
  strategy_id uuid references strategies(id) on delete set null,
  symbol varchar(20) not null,
  timeframe varchar(10) not null,
  direction varchar(10) not null,
  entry_price double precision not null,
  stop_loss double precision not null,
  take_profit_1 double precision not null,
  take_profit_2 double precision,
  position_size double precision,
  confluence_score integer not null,
  regime varchar(20) not null,
  triggers jsonb,
  status varchar(20) not null default 'pending',
  ai_quality_score double precision,
  ai_reasoning text,
  ai_recommendation varchar(20),
  mtf_confidence double precision,
  mtf_alignment varchar(20),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index ix_signals_user_id on signals(user_id);
create index ix_signals_strategy_id on signals(strategy_id);
create index ix_signals_status on signals(status);
create index ix_signals_dedup on signals(strategy_id, symbol, timeframe, direction, status);

-- Trades
create table trades (
  id uuid primary key default gen_random_uuid(),
  signal_id uuid references signals(id) on delete set null,
  user_id uuid not null references auth.users(id) on delete cascade,
  symbol varchar(20) not null,
  direction varchar(10) not null,
  entry_price double precision not null,
  exit_price double precision,
  position_size double precision not null,
  stop_loss double precision not null,
  take_profit double precision not null,
  pnl double precision,
  pnl_pct double precision,
  risk_reward double precision,
  confluence_score integer not null,
  entry_time timestamptz,
  exit_time timestamptz,
  exit_reason varchar(50),
  broker_order_id varchar(100),
  metadata_json jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index ix_trades_user_id on trades(user_id);
create index ix_trades_signal_id on trades(signal_id);
create index ix_trades_exit_time on trades(exit_time);
create index ix_trades_symbol on trades(symbol);
create index ix_trades_user_exit on trades(user_id, exit_time);

-- Orders
create table orders (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  signal_id uuid references signals(id) on delete set null,
  symbol varchar(20) not null,
  direction varchar(10) not null,
  order_type varchar(10) not null,
  quantity double precision not null,
  price double precision,
  filled_quantity double precision not null default 0.0,
  average_fill_price double precision,
  stop_loss double precision,
  take_profit double precision,
  status varchar(20) not null default 'pending',
  broker varchar(20) not null,
  broker_order_id varchar(100),
  error_message text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index ix_orders_user_id on orders(user_id);
create index ix_orders_signal_id on orders(signal_id);
create index ix_orders_status on orders(status);

-- Positions
create table positions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  order_id uuid unique references orders(id) on delete set null,
  strategy_id uuid references strategies(id) on delete set null,
  symbol varchar(20) not null,
  direction varchar(10) not null,
  quantity double precision not null,
  entry_price double precision not null,
  current_price double precision,
  stop_loss double precision,
  take_profit double precision,
  original_stop_loss double precision,
  unrealized_pnl double precision not null default 0.0,
  broker varchar(20) not null,
  broker_position_id varchar(100),
  is_open boolean not null default true,
  break_even_applied boolean not null default false,
  trailing_activated boolean not null default false,
  cooldown_until timestamptz,
  opened_at timestamptz not null default now(),
  closed_at timestamptz
);
create index ix_positions_user_id on positions(user_id);
create index ix_positions_strategy_id on positions(strategy_id);
create index ix_positions_symbol on positions(symbol);
create index ix_positions_is_open on positions(is_open);
create index ix_positions_open_user on positions(is_open, user_id);

-- Broker Connections (API keys stored in Supabase Vault, not here)
create table broker_connections (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  broker varchar(50) not null,
  is_paper boolean not null default true,
  purpose varchar(10) not null default 'read',
  vault_key_id uuid,
  vault_secret_id uuid,
  vault_passphrase_id uuid,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index ix_broker_connections_user_id on broker_connections(user_id);

-- Auto-update updated_at trigger
create or replace function update_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger trg_profiles_updated_at before update on profiles for each row execute function update_updated_at();
create trigger trg_strategies_updated_at before update on strategies for each row execute function update_updated_at();
create trigger trg_signals_updated_at before update on signals for each row execute function update_updated_at();
create trigger trg_trades_updated_at before update on trades for each row execute function update_updated_at();
create trigger trg_orders_updated_at before update on orders for each row execute function update_updated_at();
create trigger trg_broker_connections_updated_at before update on broker_connections for each row execute function update_updated_at();
