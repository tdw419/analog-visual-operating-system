import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from hal_base import ADCInterface, DACInterface
from event_bus import EventBus
from data_model import DataModel
from pxos_controller import PXOSController
from mock_hardware import MockADC, MockDAC

@pytest.fixture
def event_bus():
    return EventBus()

@pytest.fixture
def data_model(event_bus):
    return DataModel(event_bus)

@pytest.fixture
def mock_adc():
    return MockADC()

@pytest.fixture
def mock_dac():
    return MockDAC()

@pytest.fixture
def controller(event_bus, data_model, mock_adc, mock_dac):
    return PXOSController(event_bus, data_model, mock_adc, mock_dac)

@pytest.mark.asyncio
async def test_event_bus_publish_subscribe(event_bus):
    mock_callback = MagicMock()
    event_bus.subscribe("test_event", mock_callback)
    await event_bus.publish("test_event", "test_data")
    mock_callback.assert_called_once_with("test_data")

@pytest.mark.asyncio
async def test_data_model_set_get(data_model):
    await data_model.set("test_key", "test_value")
    assert data_model.get("test_key") == "test_value"

@pytest.mark.asyncio
async def test_data_model_event_on_set(event_bus, data_model):
    mock_callback = MagicMock()
    event_bus.subscribe("data_changed:test_key", mock_callback)
    await data_model.set("test_key", "test_value")
    mock_callback.assert_called_once_with("test_value")

@pytest.mark.asyncio
async def test_controller_start_stop(controller, mock_adc, mock_dac):
    with patch.object(mock_adc, 'connect', new_callable=AsyncMock) as mock_adc_connect, \
         patch.object(mock_adc, 'disconnect', new_callable=AsyncMock) as mock_adc_disconnect, \
         patch.object(mock_dac, 'connect', new_callable=AsyncMock) as mock_dac_connect, \
         patch.object(mock_dac, 'disconnect', new_callable=AsyncMock) as mock_dac_disconnect:

        await controller.start()
        mock_adc_connect.assert_awaited_once()
        mock_dac_connect.assert_awaited_once()
        assert controller._is_running is True

        await controller.stop()
        mock_adc_disconnect.assert_awaited_once()
        mock_dac_disconnect.assert_awaited_once()
        assert controller._is_running is False

@pytest.mark.asyncio
async def test_controller_set_output_voltage(controller, mock_dac, data_model):
    with patch.object(mock_dac, 'set_voltage', new_callable=AsyncMock) as mock_set_voltage:
        await controller.set_output_voltage(channel=1, voltage=3.3)
        mock_set_voltage.assert_awaited_once_with(channel=1, voltage=3.3)
        assert data_model.get("dac_channel_1") == 3.3

@pytest.mark.asyncio
async def test_controller_sensor_reading_loop(controller, mock_adc, data_model):
    # This test checks if the background task runs and updates the data model
    # We can't easily check the loop itself without a long-running test,
    # but we can check the effect after a short period.
    with patch.object(mock_adc, 'read_voltage', new_callable=AsyncMock, return_value=1.23) as mock_read_voltage:
        await controller.start()
        await asyncio.sleep(0.1) # Allow the loop to run at least once

        # In the test, the loop runs faster than 1s, but this is a way to check it's called
        mock_read_voltage.assert_called()
        assert data_model.get("adc_channel_0") == 1.23

        await controller.stop()
