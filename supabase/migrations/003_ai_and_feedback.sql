-- Migration 003: AI Insights & Feedback Rules

-- AI Insights (audit trail for all AI-generated analysis)
create table ai_insights (
  id uuid primary key default gen_random_uuid(),
  insight_type varchar(50) not null,
  signal_id uuid references signals(id) on delete set null,
  strategy_id uuid references strategies(id) on delete set null,
  user_id uuid references auth.users(id) on delete cascade,
  symbol varchar(20),
  model_used varchar(50) not null,
  reasoning text,
  result_json jsonb not null default '{}'::jsonb,
  confidence double precision,
  input_tokens integer,
  output_tokens integer,
  latency_ms integer,
  cost_usd double precision,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index ix_ai_insights_created on ai_insights(created_at);
create index ix_ai_insights_signal_id on ai_insights(signal_id);
create index ix_ai_insights_strategy_id on ai_insights(strategy_id);
create index ix_ai_insights_user_id on ai_insights(user_id);

-- Feedback Rules (learned trading rules from trade history analysis)
create table feedback_rules (
  id uuid primary key default gen_random_uuid(),
  strategy_id uuid references strategies(id) on delete set null,
  user_id uuid not null references auth.users(id) on delete cascade,
  rule_type varchar(50) not null,
  description text not null,
  conditions_json jsonb not null default '{}'::jsonb,
  confidence double precision not null default 0.5,
  is_active boolean not null default true,
  source_trade_ids jsonb,
  expires_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index ix_feedback_rules_strategy_id on feedback_rules(strategy_id);
create index ix_feedback_rules_user_id on feedback_rules(user_id);

create trigger trg_ai_insights_updated_at before update on ai_insights for each row execute function update_updated_at();
create trigger trg_feedback_rules_updated_at before update on feedback_rules for each row execute function update_updated_at();
