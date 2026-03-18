-- Migration 007: pg_cron Schedules
-- Requires pg_cron and pg_net extensions enabled on the Supabase project

create extension if not exists pg_cron;
create extension if not exists pg_net;

-- Every minute: candle ingestion + signal pipeline + execution + position management
select cron.schedule(
  'engine-cron',
  '* * * * *',
  $$
  select net.http_post(
    url := current_setting('app.settings.supabase_url') || '/functions/v1/engine-cron',
    headers := jsonb_build_object(
      'Authorization', 'Bearer ' || current_setting('app.settings.service_role_key'),
      'Content-Type', 'application/json'
    ),
    body := '{}'::jsonb
  );
  $$
);

-- Daily 02:00 UTC: risk tuning + feedback + pattern analysis + cleanup
select cron.schedule(
  'daily-maintenance',
  '0 2 * * *',
  $$
  select net.http_post(
    url := current_setting('app.settings.supabase_url') || '/functions/v1/daily-maintenance',
    headers := jsonb_build_object(
      'Authorization', 'Bearer ' || current_setting('app.settings.service_role_key'),
      'Content-Type', 'application/json'
    ),
    body := '{}'::jsonb
  );
  $$
);

-- Hourly: simulation snapshots
select cron.schedule(
  'simulation-snapshot',
  '0 * * * *',
  $$
  select net.http_post(
    url := current_setting('app.settings.supabase_url') || '/functions/v1/simulation-snapshot',
    headers := jsonb_build_object(
      'Authorization', 'Bearer ' || current_setting('app.settings.service_role_key'),
      'Content-Type', 'application/json'
    ),
    body := '{}'::jsonb
  );
  $$
);

-- Every 6 hours: symbol universe expansion
select cron.schedule(
  'universe-expansion',
  '0 */6 * * *',
  $$
  select net.http_post(
    url := current_setting('app.settings.supabase_url') || '/functions/v1/universe-expansion',
    headers := jsonb_build_object(
      'Authorization', 'Bearer ' || current_setting('app.settings.service_role_key'),
      'Content-Type', 'application/json'
    ),
    body := '{}'::jsonb
  );
  $$
);
