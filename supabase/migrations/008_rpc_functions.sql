-- Migration 008: RPC Functions

-- Dequeue signal job with advisory lock (replaces Redis locking)
create or replace function dequeue_signal_job(p_worker_id text)
returns table (
  signal_id uuid,
  symbol varchar,
  direction varchar,
  entry_price double precision,
  stop_loss double precision,
  take_profit_1 double precision,
  position_size double precision,
  strategy_id uuid,
  user_id uuid
) language plpgsql as $$
declare
  v_signal_id uuid;
begin
  -- Try to lock and claim a pending signal
  select s.id into v_signal_id
  from signals s
  where s.status = 'pending'
  order by s.created_at asc
  limit 1
  for update skip locked;

  if v_signal_id is null then
    return;
  end if;

  -- Mark as processing
  update signals set status = 'processing', updated_at = now()
  where id = v_signal_id;

  return query
  select s.id, s.symbol, s.direction, s.entry_price, s.stop_loss,
         s.take_profit_1, s.position_size, s.strategy_id, s.user_id
  from signals s
  where s.id = v_signal_id;
end;
$$;

-- Atomic AI usage increment
create or replace function increment_ai_usage(
  p_user_id uuid,
  p_tokens integer,
  p_cost double precision
) returns void language plpgsql as $$
begin
  insert into ai_insights (
    insight_type, user_id, model_used, input_tokens, cost_usd, result_json
  ) values (
    'usage_increment', p_user_id, 'aggregate', p_tokens, p_cost, '{}'::jsonb
  );
end;
$$;

-- Retention cleanup
create or replace function cleanup_old_data(p_days integer default 90)
returns jsonb language plpgsql as $$
declare
  v_pipeline_count integer;
  v_candle_count integer;
  v_cutoff timestamptz;
begin
  v_cutoff := now() - (p_days || ' days')::interval;

  -- Delete old pipeline logs (30 days)
  delete from pipeline_logs where created_at < now() - interval '30 days';
  get diagnostics v_pipeline_count = row_count;

  -- Delete old candles
  delete from candles where time < v_cutoff;
  get diagnostics v_candle_count = row_count;

  return jsonb_build_object(
    'pipeline_logs_deleted', v_pipeline_count,
    'candles_deleted', v_candle_count,
    'cutoff', v_cutoff
  );
end;
$$;

-- Auto-create profile on user signup
create or replace function handle_new_user()
returns trigger language plpgsql security definer as $$
begin
  insert into profiles (user_id) values (new.id);
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function handle_new_user();
