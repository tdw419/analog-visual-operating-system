from queue import PriorityQueue, Empty
import itertools
import numpy as np
import threading
import logging
from typing import Callable, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class DMARegion:
    """Represents a region of memory for DMA operations."""
    __slots__ = ("buf", "size", "prio")
    def __init__(self, size: int, prio: int = 50):
        self.buf = np.zeros(size, np.uint8)
        self.size = size
        self.prio = prio

    def scrub(self):
        """Fills the buffer with zeros to clear sensitive data."""
        self.buf.fill(0)

class DMAQueue:
    """A priority queue for scheduling DMA operations."""
    def __init__(self, max_inflight: int = 8):
        self.q = PriorityQueue()
        self.inflight = 0
        self.max = max_inflight
        self._seq = itertools.count()  # Tiebreaker for stable sorting
        self._lock = threading.Lock() # For thread-safe submission

    def submit(self, region: DMARegion, op: Callable[[DMARegion], Any]):
        """Submits an operation to the queue in a thread-safe manner."""
        with self._lock:
            # Priority, sequence, region, operation
            item = (region.prio, next(self._seq), region, op)
            self.q.put(item)
            logging.info(f"DMA op submitted. Priority: {item[0]}, Seq: {item[1]}")

    def run(self):
        """
        Runs operations from the queue.
        This method is designed to be called from a single-threaded dispatcher loop.
        It processes a batch of operations on each call.
        """
        # Process up to a batch size, respecting max_inflight operations
        n = min(self.q.qsize(), max(0, self.max - self.inflight))

        for _ in range(n):
            try:
                _prio, _seq, region, op = self.q.get_nowait()
            except Empty:
                break # Queue is empty, nothing more to do in this run

            self.inflight += 1
            logging.debug(f"Executing DMA op. In-flight: {self.inflight}, Prio: {_prio}")
            try:
                op(region)
            except Exception as e:
                logging.error(f"DMA operation failed for seq {_seq}: {e}", exc_info=True)
            finally:
                region.scrub()
                self.inflight -= 1
                logging.debug(f"DMA op complete. In-flight: {self.inflight}")

    def stats(self) -> dict:
        """Returns statistics about the queue."""
        return {
            "queue_size": self.q.qsize(),
            "inflight": self.inflight,
            "max_inflight": self.max
        }
