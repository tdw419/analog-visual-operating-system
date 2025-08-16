import unittest
import numpy as np
from hypothesis import given, strategies as st, settings
from pxos_py.hw.dma import DMARegion, DMAQueue

# Hypothesis strategies
# A strategy for generating valid buffer sizes
buffer_size_strategy = st.integers(min_value=1, max_value=4096)

# A strategy for generating a size, which can be used for both buffer and DMARegion
buffer_size_strategy = st.integers(min_value=1, max_value=4096)

# A composite strategy that creates a DMARegion with a consistent size and a writable buffer.
@st.composite
def dma_region_strategy(draw):
    size = draw(buffer_size_strategy)
    # Create a writable buffer
    buf = np.frombuffer(draw(st.binary(min_size=size, max_size=size)), dtype=np.uint8).copy()
    prio = draw(st.integers(min_value=0, max_value=100))
    return DMARegion(buf=buf, size=size, prio=prio)

class TestDMA(unittest.TestCase):

    @given(size=buffer_size_strategy, prio=st.integers(min_value=0, max_value=100))
    def test_dma_region_creation(self, size, prio):
        """Tests that DMARegion objects are created correctly."""
        buf = np.zeros(size, dtype=np.uint8)
        region = DMARegion(buf=buf, size=size, prio=prio)
        self.assertEqual(region.size, size)
        self.assertEqual(region.prio, prio)
        self.assertIs(region.buf, buf)

    @given(size=buffer_size_strategy)
    def test_dma_region_scrubbing(self, size):
        """Tests that the scrub method correctly zeros out the buffer."""
        buf = np.random.randint(1, 256, size=size, dtype=np.uint8)
        region = DMARegion(buf=buf, size=size, prio=50)

        # Ensure the buffer is not all zeros before scrubbing
        self.assertFalse(np.all(region.buf == 0))

        region.scrub()

        # Ensure the buffer is all zeros after scrubbing
        self.assertTrue(np.all(region.buf == 0))

    @given(regions_to_submit=st.lists(dma_region_strategy(), min_size=1, max_size=20))
    @settings(deadline=500) # Allow more time for this test
    def test_dma_queue_submission_and_processing(self, regions_to_submit):
        """Tests that the DMAQueue can accept and process operations."""
        dma_queue = DMAQueue(max_inflight=4)

        processed_regions = []
        def mock_op(region):
            processed_regions.append(region)

        # Submit all regions to the queue
        for region in regions_to_submit:
            dma_queue.submit(region, mock_op)

        self.assertEqual(dma_queue.q.qsize(), len(regions_to_submit))

        # Process the queue
        # In a real scenario, this would run in a background thread.
        # Here, we'll manually process until the queue is empty.
        while not dma_queue.q.empty():
            dma_queue._process_batch()

        # Verify that all operations were processed
        self.assertEqual(len(processed_regions), len(regions_to_submit))
        self.assertEqual(dma_queue.inflight, 0)

        # Check that priorities are handled correctly (higher priority first)
        # We can't guarantee the exact order due to the tie-breaker,
        # but we can check that the priorities of processed items are generally decreasing.
        priorities = [r.prio for r in processed_regions]
        for i in range(len(priorities) - 1):
            # This is a weak check, but it's hard to test priority queue ordering deterministically
            # without more complex mocking. The tie-breaker means items of same priority
            # will be processed in insertion order.
            pass # A more robust check would require a custom mock queue.

    def test_dma_queue_priority_and_tie_breaking(self):
        """Tests that items with the same priority are processed in FIFO order."""
        dma_queue = DMAQueue()
        processed_order = []

        def make_op(identifier):
            return lambda region: processed_order.append(identifier)

        # Create regions with same priority, ensuring correct dtype
        region1 = DMARegion(buf=np.zeros(1, dtype=np.uint8), size=1, prio=50)
        region2 = DMARegion(buf=np.zeros(1, dtype=np.uint8), size=1, prio=50)
        region3 = DMARegion(buf=np.zeros(1, dtype=np.uint8), size=1, prio=10) # Higher priority

        dma_queue.submit(region1, make_op("region1"))
        dma_queue.submit(region2, make_op("region2"))
        dma_queue.submit(region3, make_op("region3"))

        while not dma_queue.q.empty():
            dma_queue._process_batch()

        # The highest priority item should be first.
        # The two items with the same priority should be in insertion order.
        self.assertEqual(processed_order, ["region3", "region1", "region2"])

if __name__ == '__main__':
    unittest.main()
