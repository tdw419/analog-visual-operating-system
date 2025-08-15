class PxosError(Exception):
    """Base exception for PxOS errors."""
    pass

class SimulationHaltError(PxosError):
    """Raised when simulation halts unexpectedly."""
    def __init__(self, message: str, frame: int = None):
        super().__init__(message)
        self.frame = frame

class KernelExecutionError(PxosError):
    """Base class for kernel execution errors."""
    pass

class BufferShapeError(KernelExecutionError):
    """Raised for buffer shape mismatches."""
    pass
