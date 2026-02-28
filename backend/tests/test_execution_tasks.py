"""Tests for execution Celery tasks."""


def test_execute_signals_task_registered():
    from app.tasks.execute_signals import execute_pending_signals

    assert execute_pending_signals.name == "execute_pending_signals"


def test_poll_orders_task_registered():
    from app.tasks.poll_orders import poll_order_status

    assert poll_order_status.name == "poll_order_status"


def test_manage_positions_task_registered():
    from app.tasks.manage_positions import manage_positions

    assert manage_positions.name == "manage_positions"


def test_reconcile_task_registered():
    from app.tasks.reconcile import reconcile_broker_state

    assert reconcile_broker_state.name == "reconcile_broker_state"
