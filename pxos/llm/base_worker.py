# pxos/llm/base_worker.py - Unified worker interface with cancellation and reset
from dataclasses import dataclass
from typing import Iterable
import threading

@dataclass
class LlmLimits:
    max_tokens: int
    wall_timeout_s: float = 30.0
    idle_timeout_s: float = 10.0  # no tokens for N seconds → abort

class BaseWorker:
    def __init__(self):
        self._cancel = threading.Event()

    def stream(self, req, limits: LlmLimits) -> Iterable['LlmChunk']:
        raise NotImplementedError("Subclasses must implement stream()")

    def cancel(self):
        self._cancel.set()

    def reset(self):
        self._cancel.clear()

    def close(self):
        pass
