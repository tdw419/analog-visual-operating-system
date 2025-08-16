import unittest
import numpy as np
import hashlib
import time
from pxos.hw.dma import DMAController, DMAPermission

class TestDMAController(unittest.TestCase):
    def setUp(self):
        self.dma = DMAController(iommu_enabled=False)
        self.test_data = np.random.randint(0, 256, (64, 64, 4), dtype=np.uint8)
        self.data_checksum = hashlib.sha256(self.test_data.tobytes()).hexdigest()

    def test_region_allocation_and_permissions(self):
        """Verify DMA region allocation and permission enforcement"""
        region = self.dma.allocate_region(1024, DMAPermission.READ)
        self.assertIsNotNone(region)
        with self.assertRaises(PermissionError):
            self.dma.submit_write(region, self.test_data, priority=1)

    def test_data_integrity(self):
        """End-to-end data transfer validation with checksums"""
        region = self.dma.allocate_region(self.test_data.nbytes, DMAPermission.RW)

        self.dma.submit_write(region, self.test_data, priority=1)
        self.dma.submit_read(region, priority=2, shape=self.test_data.shape)

        results = self.dma.process_queue()
        retrieved_data = results[0]

        self.assertEqual(
            hashlib.sha256(retrieved_data.tobytes()).hexdigest(),
            self.data_checksum
        )

    def test_priority_queue(self):
        """Tests that operations are processed in priority order."""
        region = self.dma.allocate_region(self.test_data.nbytes, DMAPermission.RW)

        # Submit operations with different priorities, in mixed order
        self.dma.submit_write(region, self.test_data, priority=10)
        self.dma.submit_read(region, priority=1, shape=self.test_data.shape) # High priority
        self.dma.submit_write(region, np.zeros_like(self.test_data), priority=5)

        # The read should be processed first. But since reads and writes are not
        # easily distinguishable from the outside after processing, we will
        # check the final state of the region. The last write should be the one
        # with priority 10.
        self.dma.process_queue()

        # To verify order, we need to get data out. Let's do another read.
        self.dma.submit_read(region, priority=0, shape=self.test_data.shape)
        results = self.dma.process_queue()
        final_data = results[0]

        # The write with priority 5 should have overwritten the high-priority read's data,
        # and the write with priority 10 should have happened last.
        # Let's re-think this test.
        # A better way to test priority is to check the order of results.

        self.dma.queue.queue.clear() # Clear the queue for a new test

        read_results = []
        def cb(data):
            read_results.append(data)

        # We can't use callbacks easily without changing the API.
        # Let's check the order of returned values from process_queue.

        self.dma.queue.queue.clear()

        self.dma.submit_read(region, priority=10, shape=(1,1))
        self.dma.submit_read(region, priority=1, shape=(2,2))
        self.dma.submit_read(region, priority=5, shape=(3,3))

        results = self.dma.process_queue()
        self.assertEqual(results[0].shape, (2,2))
        self.assertEqual(results[1].shape, (3,3))
        self.assertEqual(results[2].shape, (1,1))


    def test_scrubbing(self):
        """Verify memory zeroization after scrubbing"""
        region = self.dma.allocate_region(1024, DMAPermission.RW)
        small_test_data = np.random.randint(0, 256, (16, 16, 4), dtype=np.uint8)

        self.dma.submit_write(region, small_test_data, priority=1)
        self.dma.process_queue()

        self.dma.scrub_region(region)

        self.dma.submit_read(region, priority=1, shape=(16, 16, 4))
        results = self.dma.process_queue()
        retrieved_data = results[0]

        self.assertTrue(np.all(retrieved_data == 0))

if __name__ == "__main__":
    unittest.main(verbosity=2)
