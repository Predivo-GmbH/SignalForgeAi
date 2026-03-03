"""Reconcile local DB state with broker positions/orders."""

import logging

from app.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="reconcile_broker_state")
def reconcile_broker_state():
    """Sync local DB with broker state — placeholder for real broker sync."""
    pass  # No-op until live broker reconciliation is implemented
