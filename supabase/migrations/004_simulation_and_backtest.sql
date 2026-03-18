-- Migration 004: Simulation & Backtest

-- Paper Simulations
create table paper_simulations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  strategy_id uuid references strategies(id) on delete set null,
  status varchar(20) not null default 'running',
  initial_holdings jsonb not null default '[]'::jsonb,
  initial_value_usd double precision not null,
  paper_holdings jsonb not null default '[]'::jsonb,
  usdt_reserve_pct double precision not null default 0.0,
  usdt_reserve_mode varchar(20) not null default 'ai',
  ai_suggested_reserve_pct double precision,
  ai_reserve_reasoning varchar(2000),
  started_at timestamptz not null default now(),
  stopped_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index ix_paper_simulations_user_id on paper_simulations(user_id);

-- Simulation Snapshots
create table simulation_snapshots (
  id uuid primary key default gen_random_uuid(),
  simulation_id uuid not null references paper_simulations(id) on delete cascade,
  timestamp timestamptz not null default now(),
  bh_value_usd double precision not null,
  sf_value_usd double precision not null,
  sf_cash_usd double precision not null default 0.0,
  sf_positions_value double precision not null default 0.0
);
create index ix_simulation_snapshots_sim_time on simulation_snapshots(simulation_id, timestamp);

-- Backtest Results
create table backtest_results (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  strategy_id uuid references strategies(id) on delete set null,
  symbol varchar(20) not null,
  timeframe varchar(5) not null,
  days integer not null,
  metrics jsonb not null,
  equity_curve jsonb,
  trade_count integer not null default 0,
  win_rate double precision,
  sharpe_ratio double precision,
  max_drawdown double precision,
  total_pnl double precision,
  created_at timestamptz not null default now()
);
create index ix_backtest_results_user_id on backtest_results(user_id);
create index ix_backtest_results_strategy_id on backtest_results(strategy_id);

create trigger trg_paper_simulations_updated_at before update on paper_simulations for each row execute function update_updated_at();
