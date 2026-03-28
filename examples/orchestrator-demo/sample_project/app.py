"""Sample project with intentional architectural smells to test orchestrator selection."""

from datetime import datetime
import uuid

class User:
    """User model."""
    def __init__(self, name: str, email: str):
        """
        Create a new User with the given name and email, assigning a unique id and a UTC creation timestamp.
        
        Parameters:
            name (str): The user's display name.
            email (str): The user's email address.
        
        Attributes:
            id (str): A UUID4-based unique identifier as a string.
            name (str): The provided name.
            email (str): The provided email.
            created_at (datetime): UTC timestamp of when the user object was created.
        """
        self.id = str(uuid.uuid4())
        self.name = name
        self.email = email
        self.created_at = datetime.utcnow()

class Order:
    """Order model."""
    def __init__(self, user: User, amount: float):
        """
        Initialize an Order for a given user and amount.
        
        Parameters:
            user (User): The user who placed the order.
            amount (float): The order total as a numeric value.
        
        Attributes:
            id (str): UUID4 string uniquely identifying the order.
            user (User): The provided user object.
            amount (float): The provided order total.
            created_at (datetime): UTC timestamp when the order was created.
        """
        self.id = str(uuid.uuid4())
        self.user = user
        self.amount = amount
        self.created_at = datetime.utcnow()

class PaymentProcessor:
    """Handles payment processing (single responsibility violation: this also logs and notifies)."""
    def process(self, order: Order):
        # Complex logic
        """
        Process payment for the given order and deliver a receipt.
        
        Validates the order amount and, if valid, simulates payment processing by printing a processing message, prints a payment log entry, and sends a receipt to the order's user.
        
        Parameters:
            order (Order): The order to be charged.
        
        Raises:
            ValueError: If `order.amount` is less than or equal to zero.
        """
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
        """
        Send a receipt to the user associated with the order.
        
        This method simulates delivery by printing the recipient email.
        
        Parameters:
            order (Order): The order whose user's email will receive the receipt.
        """
        print(f"Sending receipt to {order.user.email}")

class ReportGenerator:
    """Generates reports; tightly coupled to User and Order via direct attribute access."""
    def generate_user_report(self, user: User, orders: list[Order]):
        """
        Generate a per-user spending report and return a summary dictionary.
        
        Parameters:
            user (User): The user for whom the report is generated.
            orders (list[Order]): Orders to include in the report; each order's `amount` is summed.
        
        Returns:
            dict: A report with keys "user" (the user's name) and "total" (the numeric sum of `amount` across `orders`).
        """
        print(f"User Report: {user.name}")
        total = sum(o.amount for o in orders)
        print(f"Total spent: ${total}")
        # Report format logic here
        return {"user": user.name, "total": total}

class System:
    """God object: knows too much about everything."""
    def __init__(self):
        """
        Initialize the System with in-memory stores and service instances.
        
        Creates empty lists for users and orders and instantiates a PaymentProcessor and a ReportGenerator for handling payments and generating reports.
        """
        self.users = []
        self.orders = []
        self.payment = PaymentProcessor()
        self.reporter = ReportGenerator()

    def register_user(self, name, email):
        """
        Register a new user and add it to the system's user list.
        
        Parameters:
            name (str): The user's full name.
            email (str): The user's email address.
        
        Returns:
            User: The created User instance.
        """
        user = User(name, email)
        self.users.append(user)
        return user

    def create_order(self, user, amount):
        """
        Create a new Order for the given user and append it to the system's in-memory order list.
        
        Parameters:
            user (User): The user who places the order.
            amount (float): The monetary amount for the order.
        
        Returns:
            Order: The newly created Order instance.
        """
        order = Order(user, amount)
        self.orders.append(order)
        return order

    def checkout(self, order):
        """
        Delegate payment processing of the given order to the system's PaymentProcessor.
        
        Parameters:
            order (Order): The order to process payment for.
        """
        self.payment.process(order)

    def report(self, user):
        """
        Generate a spending report for the given user.
        
        Filters the system's stored orders to those belonging to the user and returns a per-user spending summary.
        
        Parameters:
            user (User): The user for whom to generate the report.
        
        Returns:
            dict: A report dictionary with keys "user" (user's name) and "total" (sum of the user's order amounts).
        """
        user_orders = [o for o in self.orders if o.user == user]
        return self.reporter.generate_user_report(user, user_orders)

if __name__ == "__main__":
    sys = System()
    alice = sys.register_user("Alice", "alice@example.com")
    order = sys.create_order(alice, 99.99)
    sys.checkout(order)
    print(sys.report(alice))