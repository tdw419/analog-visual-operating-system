from abc import ABC, abstractmethod
from typing import Any

class HardwareInterface(ABC):
    @abstractmethod
    async def connect(self) -> None:
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        pass

    @abstractmethod
    async def send_command(self, command: str, *args: Any) -> None:
        pass

    @abstractmethod
    async def read_response(self) -> Any:
        pass

class ADCInterface(HardwareInterface):
    @abstractmethod
    async def read_voltage(self, channel: int) -> float:
        pass

class DACInterface(HardwareInterface):
    @abstractmethod
    async def set_voltage(self, channel: int, voltage: float) -> None:
        pass
