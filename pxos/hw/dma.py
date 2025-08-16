import mmap
import numpy as np
import logging
from enum import IntFlag, auto
from dataclasses import dataclass, field
from typing import Optional, Tuple, Any
from queue import PriorityQueue

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class DMAPermission(IntFlag):
    READ = 1
    WRITE = 2
    RW = READ | WRITE

class DMAOperation:
    WRITE = auto()
    READ = auto()

@dataclass(order=True)
class DMAWorkItem:
    priority: int
    op: DMAOperation = field(compare=False)
    region: Any = field(compare=False)
    data: Any = field(compare=False, default=None)
    shape: Optional[Tuple] = field(compare=False, default=None)

@dataclass
class DMARegion:
    phys_addr: int
    size: int
    permissions: DMAPermission
    _buffer: mmap.mmap

class DMAController:
    def __init__(self, iommu_enabled: bool = False):
        self.regions = []
        self.iommu_enabled = iommu_enabled
        self.queue = PriorityQueue()
        if self.iommu_enabled:
            logging.info("IOMMU enabled (simulated)")

    def allocate_region(self, size: int, perms: DMAPermission) -> Optional[DMARegion]:
        try:
            prot = 0
            if perms & DMAPermission.READ:
                prot |= mmap.PROT_READ
            if perms & DMAPermission.WRITE:
                prot |= mmap.PROT_WRITE

            mm = mmap.mmap(-1, size, mmap.MAP_PRIVATE | mmap.MAP_ANONYMOUS, prot=prot)
            region = DMARegion(
                phys_addr=id(mm),
                size=size,
                permissions=perms,
                _buffer=mm
            )
            self.regions.append(region)
            logging.info(f"Allocated DMA region: size={size}, perms={perms.name}")
            return region
        except Exception as e:
            logging.error(f"DMA allocation failed: {e}")
            return None

    def submit_write(self, region: DMARegion, data: np.ndarray, priority: int):
        if not (region.permissions & DMAPermission.WRITE):
            raise PermissionError("Region is not writable")
        if data.nbytes > region.size:
            raise ValueError(f"Data size {data.nbytes} exceeds region size {region.size}")
        self.queue.put(DMAWorkItem(priority, DMAOperation.WRITE, region, data=data))

    def submit_read(self, region: DMARegion, priority: int, shape: Optional[Tuple] = None):
        if not (region.permissions & DMAPermission.READ):
            raise PermissionError("Region is not readable")
        self.queue.put(DMAWorkItem(priority, DMAOperation.READ, region, shape=shape))

    def _execute_write(self, region: DMARegion, data: np.ndarray):
        region._buffer.seek(0)
        region._buffer.write(data.tobytes())

    def _execute_read(self, region: DMARegion, shape: Optional[Tuple] = None) -> np.ndarray:
        region._buffer.seek(0)
        data_bytes = region._buffer.read(region.size)
        data = np.frombuffer(data_bytes, dtype=np.uint8)
        if shape:
            num_elements = np.prod(shape)
            return data[:num_elements].reshape(shape)
        return data

    def process_queue(self):
        results = []
        while not self.queue.empty():
            item = self.queue.get()
            if item.op == DMAOperation.WRITE:
                self._execute_write(item.region, item.data)
            elif item.op == DMAOperation.READ:
                result = self._execute_read(item.region, item.shape)
                results.append(result)
        return results


    def scrub_region(self, region: DMARegion):
        if region in self.regions:
            if region.permissions & DMAPermission.WRITE:
                region._buffer.seek(0)
                region._buffer.write(b'\x00' * region.size)
                logging.info(f"Scrubbed DMA region: phys_addr={region.phys_addr}")
            else:
                logging.warning(f"Cannot scrub read-only region: phys_addr={region.phys_addr}")
