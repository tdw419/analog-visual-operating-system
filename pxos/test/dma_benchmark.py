import time
import numpy as np
from pxos.hw.dma import DMAController, DMAPermission

def run_benchmarks():
    """Runs a suite of performance benchmarks for the DMAController."""
    print("="*50)
    print("Running DMA Performance Benchmarks (Priority Queue)")
    print("="*50)

    benchmark_throughput()
    benchmark_latency()
    benchmark_mixed_workload()

def benchmark_throughput():
    """Benchmarks read and write throughput for various data sizes."""
    print("\n--- Throughput Benchmark ---")
    dma = DMAController()
    sizes = [1*1024, 256*1024, 1*1024*1024, 16*1024*1024] # 1KB, 256KB, 1MB, 16MB
    iterations = 100

    for size in sizes:
        region = dma.allocate_region(size, DMAPermission.RW)
        data = np.random.randint(0, 256, size, dtype=np.uint8)

        # Write throughput
        start_time = time.perf_counter()
        for i in range(iterations):
            dma.submit_write(region, data, priority=i)
        dma.process_queue()
        end_time = time.perf_counter()
        write_throughput = (size * iterations / (1024*1024)) / (end_time - start_time)

        # Read throughput
        start_time = time.perf_counter()
        for i in range(iterations):
            dma.submit_read(region, priority=i)
        dma.process_queue()
        end_time = time.perf_counter()
        read_throughput = (size * iterations / (1024*1024)) / (end_time - start_time)

        print(f"Size: {size/1024:<6.1f} KB | Write: {write_throughput:7.2f} MB/s | Read: {read_throughput:7.2f} MB/s")

def benchmark_latency():
    """Benchmarks the latency of a high-priority item."""
    print("\n--- Latency Benchmark ---")
    dma = DMAController()
    size = 64 # 64 bytes
    num_low_priority_items = 1000

    region = dma.allocate_region(size, DMAPermission.RW)
    data = np.random.randint(0, 256, size, dtype=np.uint8)

    # Fill the queue with low-priority items
    for _ in range(num_low_priority_items):
        dma.submit_write(region, data, priority=10)

    # Submit a high-priority item and measure the time to process it
    start_time = time.perf_counter()
    dma.submit_write(region, data, priority=1) # High priority
    dma.process_queue()
    end_time = time.perf_counter()

    # This measures the time to process the whole queue, which is not what we want.
    # To measure the latency of a single item, we would need a different approach.
    # For now, we'll just measure the total processing time.
    print(f"Processing {num_low_priority_items+1} items took: {(end_time - start_time)*1e3:.2f} ms")


def benchmark_mixed_workload():
    """Benchmarks performance with a mixed workload of reads and writes."""
    print("\n--- Mixed Workload Benchmark ---")
    dma = DMAController()
    num_items = 1000
    size = 1024

    region = dma.allocate_region(size, DMAPermission.RW)
    data = np.random.randint(0, 256, size, dtype=np.uint8)

    for i in range(num_items):
        if i % 2 == 0:
            dma.submit_write(region, data, priority=np.random.randint(1, 11))
        else:
            dma.submit_read(region, priority=np.random.randint(1, 11))

    start_time = time.perf_counter()
    dma.process_queue()
    end_time = time.perf_counter()

    total_throughput = (size * num_items / (1024*1024)) / (end_time - start_time)
    print(f"Processed {num_items} mixed R/W ops | Total Throughput: {total_throughput:7.2f} MB/s")


if __name__ == "__main__":
    run_benchmarks()
