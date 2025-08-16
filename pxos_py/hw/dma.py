from queue import PriorityQueue, Empty
import itertools
import numpy as np
import threading
from dataclasses import dataclass

@dataclass
class DMARegion:
    """Represents a region of memory for DMA operations."""
    # Using __slots__ for memory efficiency, as many of these could exist.
    __slots__ = ("buf", "size", "prio")

    buf: np.ndarray
    size: int
    prio: int

    def __post_init__(self):
        if self.buf.nbytes != self.size:
            raise ValueError("Buffer size must match the specified size.")

    def scrub(self):
        """Fills the buffer with zeros to clear sensitive data."""
        self.buf.fill(0)

class DMAQueue:
    """
    A thread-safe, priority-based queue for scheduling DMA operations.
    - Uses a sequence counter as a tie-breaker for stable sorting.
    - Processes operations in batches to avoid starving the queue.
    """
    def __init__(self, max_inflight=8):
        """
        Initializes the DMA queue.

        Args:
            max_inflight (int): The maximum number of operations that can be processed concurrently.
        """
        self.q = PriorityQueue()
        self.inflight = 0
        self.max = max_inflight
        self._seq = itertools.count()  # Tiebreaker for items with the same priority
        self._lock = threading.Lock()
        self.running = True # Flag to control the processing loop

    def submit(self, region: DMARegion, op):
        """
        Submits a DMA operation to the queue.

        Args:
            region (DMARegion): The memory region for the operation.
            op (callable): The operation to perform on the region.
        """
        # The tuple in the queue is (priority, sequence_number, region, operation)
        self.q.put((region.prio, next(self._seq), region, op))

    def _process_batch(self):
        """Processes a batch of items from the queue."""
        with self._lock:
            # Determine how many items to process in this batch
            n = min(self.q.qsize(), max(0, self.max - self.inflight))

        if n == 0:
            return

        for _ in range(n):
            try:
                _, _, region, op = self.q.get_nowait()

                with self._lock:
                    self.inflight += 1

                try:
                    # Execute the operation
                    op(region)
                finally:
                    # Always scrub the region and decrement inflight count
                    region.scrub()
                    with self._lock:
                        self.inflight -= 1
            except Empty:
                break  # Queue is empty, stop processing batch

    def run_in_background(self):
        """Runs the DMA queue processor in a background thread."""
        def worker():
            while self.running:
                self._process_batch()
                # Sleep briefly to prevent busy-waiting
                threading.Event().wait(0.01)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        return thread

    def stop(self):
        """Stops the background processing thread."""
        self.running = False

    def stats(self):
        """Returns statistics about the queue."""
        with self._lock:
            return {
                "queue_size": self.q.qsize(),
                "inflight_operations": self.inflight,
                "max_inflight": self.max
            }
