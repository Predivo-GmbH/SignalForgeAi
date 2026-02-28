"""Reconcile local DB state with broker positions/orders."""

import logging

from app.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="reconcile_broker_state", bind=True, max_retries=3)
def reconcile_broker_state(self):
    """Sync local DB with broker state — placeholder for real broker sync."""
    logger.info("Reconciliation task running (no-op in paper mode)")
