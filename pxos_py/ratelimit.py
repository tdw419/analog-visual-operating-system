import time
import threading

class Limiter:
    """
    A thread-safe token bucket rate limiter.
    This implementation uses a monotonic clock to be resilient against system time changes.
    """
    def __init__(self, per_min, burst):
        """
        Initializes the rate limiter.

        Args:
            per_min (float): The number of allowed requests per minute.
            burst (float): The maximum number of tokens that can be accumulated.
        """
        self.rate = per_min / 60.0
        self.burst = float(burst)
        self.tokens = float(burst)
        self._last_update_time = time.monotonic()
        self._lock = threading.Lock()

    def allow(self):
        """
        Checks if a request is allowed. Consumes a token if it is.

        Returns:
            bool: True if the request is allowed, False otherwise.
        """
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_update_time
            self._last_update_time = now

            # Add new tokens based on the elapsed time
            self.tokens += elapsed * self.rate
            self.tokens = min(self.burst, self.tokens)

            # Check if there are enough tokens for a request
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return True

            return False

    def stats(self):
        """
        Returns the current state of the rate limiter for monitoring.

        Returns:
            dict: A dictionary containing the current number of tokens and other stats.
        """
        with self._lock:
            return {
                "tokens": self.tokens,
                "last_update_time": self._last_update_time,
                "rate_per_second": self.rate,
                "burst_capacity": self.burst
            }
