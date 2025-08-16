import time
import threading

class Limiter:
    """
    A thread-safe token bucket rate limiter.
    """
    def __init__(self, per_min: float, burst: float):
        """
        Initializes the limiter.
        Args:
            per_min: The number of allowed requests per minute.
            burst: The maximum number of requests that can be handled in a burst.
        """
        self.rate = per_min / 60.0
        self.burst = float(burst)
        self.tokens = float(burst)
        self.last_update = time.monotonic()
        self._lock = threading.Lock()

    def allow(self) -> bool:
        """
        Checks if a request is allowed. Consumes a token if it is.
        Returns:
            True if the request is allowed, False otherwise.
        """
        with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.last_update = now

            # Add new tokens based on elapsed time
            self.tokens += elapsed * self.rate
            self.tokens = min(self.burst, self.tokens)

            # Check if there are enough tokens
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return True
            return False

    def stats(self) -> dict:
        """Returns the current state of the limiter."""
        with self._lock:
            return {
                "tokens": self.tokens,
                "burst": self.burst,
                "rate_per_sec": self.rate,
                "last_update": self.last_update,
            }
