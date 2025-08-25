import asyncio
from event_bus import EventBus
from data_model import DataModel
from hal_base import ADCInterface, DACInterface

class PXOSController:
    def __init__(self, event_bus: EventBus, data_model: DataModel, adc: ADCInterface, dac: DACInterface):
        self.event_bus = event_bus
        self.data_model = data_model
        self.adc = adc
        self.dac = dac
        self._is_running = False
        self._tasks: list[asyncio.Task] = []

    async def start(self):
        print("PXOS Controller starting...")
        await self.adc.connect()
        await self.dac.connect()
        self._is_running = True

        # Example background task: periodically read from ADC
        sensor_reading_task = asyncio.create_task(self._read_sensors_periodically())
        self._tasks.append(sensor_reading_task)

        print("PXOS Controller started.")

    async def stop(self):
        print("PXOS Controller stopping...")
        self._is_running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)

        await self.adc.disconnect()
        await self.dac.disconnect()
        print("PXOS Controller stopped.")

    async def _read_sensors_periodically(self):
        while self._is_running:
            try:
                # Read from all 8 channels for demonstration
                for i in range(8):
                    voltage = await self.adc.read_voltage(i)
                    await self.data_model.set(f"adc_channel_{i}", voltage, use_cache=True)
                await asyncio.sleep(1)  # Read every second
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error reading sensors: {e}")
                await asyncio.sleep(5) # Wait longer after an error

    # Example of a high-level command
    async def set_output_voltage(self, channel: int, voltage: float):
        print(f"Controller: Setting output voltage for channel {channel} to {voltage}V")
        await self.dac.set_voltage(channel, voltage)
        await self.data_model.set(f"dac_channel_{channel}", voltage)
