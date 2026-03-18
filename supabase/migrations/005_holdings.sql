-- Migration 005: Holdings

-- Manual Holdings
create table manual_holdings (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  symbol varchar(20) not null,
  quantity double precision not null,
  purchase_price double precision,
  notes varchar(255),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index ix_manual_holdings_user_id on manual_holdings(user_id);

-- Cost Basis Overrides
create table cost_basis_overrides (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  symbol varchar(20) not null,
  purchase_price double precision not null,
  notes varchar(255),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint uq_cost_basis_user_symbol unique (user_id, symbol)
);
create index ix_cost_basis_overrides_user_id on cost_basis_overrides(user_id);

create trigger trg_manual_holdings_updated_at before update on manual_holdings for each row execute function update_updated_at();
create trigger trg_cost_basis_overrides_updated_at before update on cost_basis_overrides for each row execute function update_updated_at();
