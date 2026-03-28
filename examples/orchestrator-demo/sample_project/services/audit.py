"""Audit service that knows about Users and Orders (feature envy)."""

from datetime import datetime
from pathlib import Path

class AuditService:
    """Logs audit events for user actions."""
    def __init__(self):
        self.log_file = Path("audit.log")

    def record_user_creation(self, user):
        self._write(f"USER_CREATED {user.id} {user.email} at {datetime.utcnow()}")

    def record_order_creation(self, order):
        self._write(f"ORDER_CREATED {order.id} {order.user.id} amount={order.amount}")

    def _write(self, line: str):
        with open(self.log_file, "a") as f:
            f.write(line + "\n")

audit = AuditService()