"""Shared utilities for Celery task execution."""

import logging
from contextlib import contextmanager

import redis

from app.config import settings

logger = logging.getLogger(__name__)


@contextmanager
def task_lock(lock_name: str, timeout: int = 1800, blocking: bool = False):
    """Acquire a Redis lock for a Celery task. Yields True if acquired, False if not.

    Usage:
        with task_lock("my_task", timeout=1800) as acquired:
            if not acquired:
                return
            # do work
    """
    r = None
    lock = None
    acquired = False
    try:
        r = redis.from_url(settings.redis_url)
        lock = r.lock(f"signalforge:lock:{lock_name}", timeout=timeout, blocking=blocking)
        acquired = lock.acquire(blocking=False)
        if not acquired:
            logger.info("%s already running, skipping", lock_name)
            r.close()
    except redis.ConnectionError:
        logger.warning("Redis unavailable for %s lock — proceeding without lock", lock_name)
    except Exception:
        logger.warning("Failed to acquire lock for %s", lock_name, exc_info=True)

    try:
        yield acquired
    finally:
        if lock is not None and acquired:
            try:
                lock.release()
            except redis.exceptions.LockNotOwnedError:
                logger.warning("Lock %s expired before release", lock_name)
            except Exception:
                logger.warning("Failed to release lock %s", lock_name, exc_info=True)
        if r is not None:
            try:
                r.close()
            except Exception:
                logger.warning("Failed to close Redis connection for %s", lock_name, exc_info=True)
