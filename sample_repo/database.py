"""Database connection manager for TaskMaster."""

class DatabaseSession:
    def __init__(self, connection_url: str = "sqlite:///taskmaster.db"):
        self.connection_url = connection_url
        self.connected = False

    def connect(self):
        """Initializes database connection pool."""
        self.connected = True
        return f"Connected to {self.connection_url}"

    def disconnect(self):
        """Closes active pool connections."""
        self.connected = False
