"""Audit service that knows about Users and Orders (feature envy)."""

from datetime import datetime
from pathlib import Path

class AuditService:
    """Logs audit events for user actions."""
    def __init__(self):
        """
        Initialize the AuditService and configure its log file path.
        
        Sets self.log_file to Path("audit.log"), pointing to the audit log file in the current working directory.
        """
        self.log_file = Path("audit.log")

    def record_user_creation(self, user):
        """
        Record an audit entry for a newly created user.
        
        Appends an audit line containing the user's id, email, and the current UTC timestamp in the format:
        `USER_CREATED {user.id} {user.email} at {timestamp}`.
        
        Parameters:
            user: An object with `id` and `email` attributes used to populate the log entry.
        """
        self._write(f"USER_CREATED {user.id} {user.email} at {datetime.utcnow()}")

    def record_order_creation(self, order):
        """
        Log an order creation event to the audit file.
        
        Writes a single audit line with the format:
        `ORDER_CREATED {order.id} {order.user.id} amount={order.amount}`.
        
        Parameters:
            order: An object representing the order. Must have `id`, `amount`, and a `user` with an `id`.
        """
        self._write(f"ORDER_CREATED {order.id} {order.user.id} amount={order.amount}")

    def _write(self, line: str):
        """
        Append a line to the service's configured audit log file.
        
        Appends the provided text as a new line to self.log_file using append mode.
        
        Parameters:
            line (str): Text to append to the log file (a terminating newline will be added).
        """
        with open(self.log_file, "a") as f:
            f.write(line + "\n")

audit = AuditService()