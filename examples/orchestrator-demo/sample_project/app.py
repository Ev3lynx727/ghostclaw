"""Sample project with intentional architectural smells to test orchestrator selection."""

from datetime import datetime
import uuid

class User:
    """User model."""
    def __init__(self, name: str, email: str):
        self.id = str(uuid.uuid4())
        self.name = name
        self.email = email
        self.created_at = datetime.utcnow()

class Order:
    """Order model."""
    def __init__(self, user: User, amount: float):
        self.id = str(uuid.uuid4())
        self.user = user
        self.amount = amount
        self.created_at = datetime.utcnow()

class PaymentProcessor:
    """Handles payment processing (single responsibility violation: this also logs and notifies)."""
    def process(self, order: Order):
        # Complex logic
        if order.amount <= 0:
            raise ValueError("Invalid amount")
        # Simulate payment
        print(f"Processing payment ${order.amount} for {order.user.name}")
        # Logging (should be delegated)
        print(f"[LOG] Payment processed for order {order.id}")
        # Notification (should be delegated)
        self._send_receipt(order)

    def _send_receipt(self, order: Order):
        # Simulate sending receipt
        print(f"Sending receipt to {order.user.email}")

class ReportGenerator:
    """Generates reports; tightly coupled to User and Order via direct attribute access."""
    def generate_user_report(self, user: User, orders: list[Order]):
        print(f"User Report: {user.name}")
        total = sum(o.amount for o in orders)
        print(f"Total spent: ${total}")
        # Report format logic here
        return {"user": user.name, "total": total}

class System:
    """God object: knows too much about everything."""
    def __init__(self):
        self.users = []
        self.orders = []
        self.payment = PaymentProcessor()
        self.reporter = ReportGenerator()

    def register_user(self, name, email):
        user = User(name, email)
        self.users.append(user)
        return user

    def create_order(self, user, amount):
        order = Order(user, amount)
        self.orders.append(order)
        return order

    def checkout(self, order):
        self.payment.process(order)

    def report(self, user):
        user_orders = [o for o in self.orders if o.user == user]
        return self.reporter.generate_user_report(user, user_orders)

if __name__ == "__main__":
    sys = System()
    alice = sys.register_user("Alice", "alice@example.com")
    order = sys.create_order(alice, 99.99)
    sys.checkout(order)
    print(sys.report(alice))