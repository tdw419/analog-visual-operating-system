import pytest
from analog_compiler import (
    compile_from_source,
    generate_signals,
    write_bytecode,
    disasm,
    TextOp,
    RectOp,
    LineOp,
    CursorOp,
    MoveOp,
    BlankOp,
)
from air import IROp
import os
import struct

# Fixture for a sample program source
@pytest.fixture
def sample_source():
    return """
# This is a comment
TEXT "HELLO" AT 16,20 COLOR #00FF00 SCALE 2
RECT 10,40,60,14 COLOR #6464FF
MOVE TO 0,0
BLANK ON
"""

def test_compile_from_source(sample_source):
    """Tests that the compiler correctly parses DSL into an IR."""
    ir = compile_from_source(sample_source)

    assert len(ir) == 4

    # Check TextOp
    text_op = ir[0]
    assert isinstance(text_op, TextOp)
    assert text_op.text == "HELLO"
    assert text_op.x == 16
    assert text_op.y == 20
    assert text_op.color == (0, 255, 0)
    assert text_op.scale == 2

    # Check RectOp
    rect_op = ir[1]
    assert isinstance(rect_op, RectOp)
    assert rect_op.x == 10
    assert rect_op.y == 40
    assert rect_op.w == 60
    assert rect_op.h == 14
    assert rect_op.color == (100, 100, 255)

    # Check MoveOp
    move_op = ir[2]
    assert isinstance(move_op, MoveOp)
    assert move_op.x == 0
    assert move_op.y == 0

    # Check BlankOp
    blank_op = ir[3]
    assert isinstance(blank_op, BlankOp)
    assert blank_op.enable is True

def test_generate_signals_and_rle(sample_source):
    """Tests signal generation and that RLE is effective."""
    ir = compile_from_source(sample_source)

    # Manually calculate raw pixel count for "HELLO" (5x7 font, scale 2)
    # H: 15, E: 15, L: 10, L: 10, O: 14 -> Total: 64 pixels
    # Scaled by 2x2 = 4 pixels per glyph pixel -> 64 * 4 = 256
    # Rect: 60 * 14 = 840
    # Total raw drawing signals = 256 + 840 = 1096
    # Plus moves and blanks

    signals = generate_signals(ir)

    assert len(signals) > 0

    # The number of RLE-compressed signals should be less than the raw pixel count
    # This is a heuristic test but should hold true for this sample.
    # The exact number of raw signals is complex to calculate due to beam moves,
    # but the number of runs should be significantly smaller than total pixels.
    total_pixels = (15+15+10+10+14)*4 + (60*14)
    assert len(signals) < total_pixels

    # Check the format of a signal tuple
    signal = signals[0]
    assert len(signal) == 8 # t_us, x, y, r, g, b, op_name, length
    assert isinstance(signal[0], int) # t_us
    assert isinstance(signal[7], int) # length

def test_bytecode_roundtrip(sample_source):
    """Tests that bytecode can be written and then disassembled."""
    ir = compile_from_source(sample_source)

    bytecode_path = "test_program.ab"
    write_bytecode(bytecode_path, ir)

    assert os.path.exists(bytecode_path)

    # Capture stdout from disassembler
    import io
    from contextlib import redirect_stdout

    f = io.StringIO()
    with redirect_stdout(f):
        disasm(bytecode_path)
    output = f.getvalue()

    # Check if disassembly output looks reasonable
    assert "ANLG v1" in output
    assert "TEXT" in output
    assert "RECT" in output
    assert "MOVE" in output
    assert "BLANK" in output
    assert "END" in output

    os.remove(bytecode_path)
