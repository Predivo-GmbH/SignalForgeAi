# SignalForge Operational Runbooks

## Common Issues & Resolution

### Redis Connection Failure
**Symptoms:** API returns 503, signals not processing, health check shows Redis down
**Resolution:**
1. Check Redis container: `docker compose logs redis`
2. Restart Redis: `docker compose restart redis`
3. Verify: `docker compose exec redis redis-cli ping` -- should return PONG
4. If persistent, check memory: Redis may be OOM (check resource limits)

### Database Connection Issues
**Symptoms:** API returns 500, health check shows DB down
**Resolution:**
1. Check DB container: `docker compose logs db`
2. Check connections: `docker compose exec db psql -U signalforge -c "SELECT count(*) FROM pg_stat_activity;"`
3. If too many connections, restart API: `docker compose restart api`
4. If DB crashed, restore from backup: see "Restore from Backup" below

### Celery Worker Not Processing
**Symptoms:** Signals not generated, pipelines not running
**Resolution:**
1. Check worker: `docker compose logs worker`
2. Check beat scheduler: `docker compose logs beat`
3. Restart both: `docker compose restart worker beat`
4. Check Redis queue depth: `docker compose exec redis redis-cli LLEN celery`

### AI API Quota Exceeded
**Symptoms:** AI Advisor returns "Service unavailable", AI usage shows high cost
**Resolution:**
1. Check current usage: `curl -H "Authorization: Bearer TOKEN" http://localhost:8000/api/ai-usage`
2. If over budget, wait for daily reset or increase `SF_AI_PREPAID_CREDIT_USD` in .env
3. AI features gracefully degrade -- trading continues without AI insights

### Database Migration
**Apply new migration:**
```bash
docker compose exec api alembic upgrade head
```
**Rollback last migration:**
```bash
docker compose exec api alembic downgrade -1
```

### Restore from Backup
```bash
# List available backups
ls -la /opt/signalforge/backups/

# Restore latest backup
gunzip < /opt/signalforge/backups/signalforge_YYYYMMDD_HHMMSS.sql.gz | \
  docker compose exec -T db psql -U signalforge -d signalforge
```

### Full System Restart
```bash
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d
# Wait for health checks (30s)
curl http://localhost:8000/health
```
