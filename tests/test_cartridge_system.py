import pytest
import numpy as np
from pxos_py.bitpack_v2 import BitPackV2Codec, BitPackSpec
from pxos_py.cartridge_manager import CartridgeManager
from pxos_py.visual_editor import VisualCodeEditor
from pxos_py.sandbox import ExecutionSandbox

class MockPixelOS:
    def log(self, msg):
        print(msg)

@pytest.fixture
def mock_pxos():
    return MockPixelOS()

def test_bitpack_v2_codec():
    codec = BitPackV2Codec(BitPackSpec())
    sample_code = "print('hello')"
    buffer = codec.encode_to_buffer(sample_code)
    decoded = codec.decode_from_buffer(buffer)
    assert decoded["text"] == sample_code

def test_cartridge_manager(mock_pxos):
    manager = CartridgeManager(mock_pxos, 0, 0, 100, 100)
    # This test is incomplete as it requires a file path
    # manager.load_cartridge("examples/demo_cartridge.png")
    # assert len(manager.cartridges) == 1

def test_visual_editor(mock_pxos):
    editor = VisualCodeEditor(mock_pxos, 0, 0, 100, 100)
    assert editor.mode == "code"
    editor.select_tool("block")
    assert editor.mode == "visual"

def test_execution_sandbox(mock_pxos):
    sandbox = ExecutionSandbox(mock_pxos)
    success, message = sandbox.execute("print('hello')", "pixelpy")
    assert success
    assert message == "Execution completed"
