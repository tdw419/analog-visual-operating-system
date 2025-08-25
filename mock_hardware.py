import asyncio
from typing import Any
from hal_base import ADCInterface, DACInterface

class MockADC(ADCInterface):
    def __init__(self, num_channels: int = 8):
        self._num_channels = num_channels
        self._voltages = [0.0] * num_channels

    async def connect(self) -> None:
        print("Mock ADC connected.")
        await asyncio.sleep(0.01)

    async def disconnect(self) -> None:
        print("Mock ADC disconnected.")
        await asyncio.sleep(0.01)

    async def send_command(self, command: str, *args: Any) -> None:
        print(f"Mock ADC received command: {command} with args: {args}")
        await asyncio.sleep(0.01)

    async def read_response(self) -> Any:
        response = "Mock ADC response"
        print(f"Mock ADC sending response: {response}")
        await asyncio.sleep(0.01)
        return response

    async def read_voltage(self, channel: int) -> float:
        if 0 <= channel < self._num_channels:
            # Simulate some changing values
            self._voltages[channel] = (self._voltages[channel] + 0.1) % 5.0
            print(f"Mock ADC reading voltage from channel {channel}: {self._voltages[channel]:.2f}V")
            await asyncio.sleep(0.01)
            return self._voltages[channel]
        else:
            raise ValueError("Invalid ADC channel")

class MockDAC(DACInterface):
    def __init__(self, num_channels: int = 8):
        self._num_channels = num_channels
        self._voltages = [0.0] * num_channels

    async def connect(self) -> None:
        print("Mock DAC connected.")
        await asyncio.sleep(0.01)

    async def disconnect(self) -> None:
        print("Mock DAC disconnected.")
        await asyncio.sleep(0.01)

    async def send_command(self, command: str, *args: Any) -> None:
        print(f"Mock DAC received command: {command} with args: {args}")
        await asyncio.sleep(0.01)

    async def read_response(self) -> Any:
        response = "Mock DAC response"
        print(f"Mock DAC sending response: {response}")
        await asyncio.sleep(0.01)
        return response

    async def set_voltage(self, channel: int, voltage: float) -> None:
        if 0 <= channel < self._num_channels:
            print(f"Mock DAC setting channel {channel} to {voltage:.2f}V")
            self._voltages[channel] = voltage
            await asyncio.sleep(0.01)
        else:
            raise ValueError("Invalid DAC channel")
