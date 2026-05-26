-- Migration 007: pg_cron Schedules
-- Requires pg_cron and pg_net extensions enabled on the Supabase project
-- NOTE: Supabase does not allow ALTER DATABASE SET app.settings.*, so URLs
--       and service_role_key are hardcoded. Update these after any project migration.

create extension if not exists pg_cron;
create extension if not exists pg_net;

-- Every minute: candle ingestion + signal pipeline + execution + position management
select cron.schedule(
  'engine-cron',
  '* * * * *',
  $$
  select net.http_post(
    url := 'https://xioqgsybkhjijkciinmu.supabase.co/functions/v1/engine-cron',
    headers := jsonb_build_object(
      'Authorization', 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inhpb3Fnc3lia2hqaWprY2lpbm11Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3OTc4Nzg4MywiZXhwIjoyMDk1MzYzODgzfQ.O4dBjpaOe0O1NTwX1jd4hjLgkeKyGDvDU2uZajwdvI8',
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
    url := 'https://xioqgsybkhjijkciinmu.supabase.co/functions/v1/daily-maintenance',
    headers := jsonb_build_object(
      'Authorization', 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inhpb3Fnc3lia2hqaWprY2lpbm11Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3OTc4Nzg4MywiZXhwIjoyMDk1MzYzODgzfQ.O4dBjpaOe0O1NTwX1jd4hjLgkeKyGDvDU2uZajwdvI8',
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
    url := 'https://xioqgsybkhjijkciinmu.supabase.co/functions/v1/simulation-snapshot',
    headers := jsonb_build_object(
      'Authorization', 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inhpb3Fnc3lia2hqaWprY2lpbm11Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3OTc4Nzg4MywiZXhwIjoyMDk1MzYzODgzfQ.O4dBjpaOe0O1NTwX1jd4hjLgkeKyGDvDU2uZajwdvI8',
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
    url := 'https://xioqgsybkhjijkciinmu.supabase.co/functions/v1/universe-expansion',
    headers := jsonb_build_object(
      'Authorization', 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inhpb3Fnc3lia2hqaWprY2lpbm11Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3OTc4Nzg4MywiZXhwIjoyMDk1MzYzODgzfQ.O4dBjpaOe0O1NTwX1jd4hjLgkeKyGDvDU2uZajwdvI8',
      'Content-Type', 'application/json'
    ),
    body := '{}'::jsonb
  );
  $$
);
