-- Migration 006: Row Level Security

-- Enable RLS on all tables
alter table profiles enable row level security;
alter table strategies enable row level security;
alter table signals enable row level security;
alter table trades enable row level security;
alter table orders enable row level security;
alter table positions enable row level security;
alter table broker_connections enable row level security;
alter table candles enable row level security;
alter table pipeline_logs enable row level security;
alter table ai_insights enable row level security;
alter table feedback_rules enable row level security;
alter table paper_simulations enable row level security;
alter table simulation_snapshots enable row level security;
alter table backtest_results enable row level security;
alter table manual_holdings enable row level security;
alter table cost_basis_overrides enable row level security;

-- Profiles: users can only access their own profile
create policy "profiles_select_own" on profiles for select using (auth.uid() = user_id);
create policy "profiles_insert_own" on profiles for insert with check (auth.uid() = user_id);
create policy "profiles_update_own" on profiles for update using (auth.uid() = user_id);
create policy "profiles_delete_own" on profiles for delete using (auth.uid() = user_id);

-- Strategies
create policy "strategies_select_own" on strategies for select using (auth.uid() = user_id);
create policy "strategies_insert_own" on strategies for insert with check (auth.uid() = user_id);
create policy "strategies_update_own" on strategies for update using (auth.uid() = user_id);
create policy "strategies_delete_own" on strategies for delete using (auth.uid() = user_id);

-- Signals
create policy "signals_select_own" on signals for select using (auth.uid() = user_id);
create policy "signals_insert_own" on signals for insert with check (auth.uid() = user_id);
create policy "signals_update_own" on signals for update using (auth.uid() = user_id);
create policy "signals_delete_own" on signals for delete using (auth.uid() = user_id);

-- Trades
create policy "trades_select_own" on trades for select using (auth.uid() = user_id);
create policy "trades_insert_own" on trades for insert with check (auth.uid() = user_id);
create policy "trades_update_own" on trades for update using (auth.uid() = user_id);
create policy "trades_delete_own" on trades for delete using (auth.uid() = user_id);

-- Orders
create policy "orders_select_own" on orders for select using (auth.uid() = user_id);
create policy "orders_insert_own" on orders for insert with check (auth.uid() = user_id);
create policy "orders_update_own" on orders for update using (auth.uid() = user_id);
create policy "orders_delete_own" on orders for delete using (auth.uid() = user_id);

-- Positions
create policy "positions_select_own" on positions for select using (auth.uid() = user_id);
create policy "positions_insert_own" on positions for insert with check (auth.uid() = user_id);
create policy "positions_update_own" on positions for update using (auth.uid() = user_id);
create policy "positions_delete_own" on positions for delete using (auth.uid() = user_id);

-- Broker Connections
create policy "broker_connections_select_own" on broker_connections for select using (auth.uid() = user_id);
create policy "broker_connections_insert_own" on broker_connections for insert with check (auth.uid() = user_id);
create policy "broker_connections_update_own" on broker_connections for update using (auth.uid() = user_id);
create policy "broker_connections_delete_own" on broker_connections for delete using (auth.uid() = user_id);

-- Candles: publicly readable, insert/update/delete via service role only
create policy "candles_select_public" on candles for select using (true);

-- Pipeline Logs: readable by strategy owner (via strategy join)
create policy "pipeline_logs_select_own" on pipeline_logs for select
  using (exists (
    select 1 from strategies s where s.id = pipeline_logs.strategy_id and s.user_id = auth.uid()
  ));

-- AI Insights
create policy "ai_insights_select_own" on ai_insights for select using (auth.uid() = user_id);
create policy "ai_insights_insert_own" on ai_insights for insert with check (auth.uid() = user_id);

-- Feedback Rules
create policy "feedback_rules_select_own" on feedback_rules for select using (auth.uid() = user_id);
create policy "feedback_rules_insert_own" on feedback_rules for insert with check (auth.uid() = user_id);
create policy "feedback_rules_update_own" on feedback_rules for update using (auth.uid() = user_id);
create policy "feedback_rules_delete_own" on feedback_rules for delete using (auth.uid() = user_id);

-- Paper Simulations
create policy "paper_simulations_select_own" on paper_simulations for select using (auth.uid() = user_id);
create policy "paper_simulations_insert_own" on paper_simulations for insert with check (auth.uid() = user_id);
create policy "paper_simulations_update_own" on paper_simulations for update using (auth.uid() = user_id);
create policy "paper_simulations_delete_own" on paper_simulations for delete using (auth.uid() = user_id);

-- Simulation Snapshots: readable by simulation owner
create policy "simulation_snapshots_select_own" on simulation_snapshots for select
  using (exists (
    select 1 from paper_simulations ps where ps.id = simulation_snapshots.simulation_id and ps.user_id = auth.uid()
  ));

-- Backtest Results
create policy "backtest_results_select_own" on backtest_results for select using (auth.uid() = user_id);
create policy "backtest_results_insert_own" on backtest_results for insert with check (auth.uid() = user_id);
create policy "backtest_results_delete_own" on backtest_results for delete using (auth.uid() = user_id);

-- Manual Holdings
create policy "manual_holdings_select_own" on manual_holdings for select using (auth.uid() = user_id);
create policy "manual_holdings_insert_own" on manual_holdings for insert with check (auth.uid() = user_id);
create policy "manual_holdings_update_own" on manual_holdings for update using (auth.uid() = user_id);
create policy "manual_holdings_delete_own" on manual_holdings for delete using (auth.uid() = user_id);

-- Cost Basis Overrides
create policy "cost_basis_overrides_select_own" on cost_basis_overrides for select using (auth.uid() = user_id);
create policy "cost_basis_overrides_insert_own" on cost_basis_overrides for insert with check (auth.uid() = user_id);
create policy "cost_basis_overrides_update_own" on cost_basis_overrides for update using (auth.uid() = user_id);
create policy "cost_basis_overrides_delete_own" on cost_basis_overrides for delete using (auth.uid() = user_id);
