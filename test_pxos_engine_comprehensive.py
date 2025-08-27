#!/usr/bin/env python3
"""
Comprehensive pytest harness for PXOS Enhanced Sync Engine
Tests all invariants: echo guards, validation halts, pinning, debouncing, round-trip
"""

import asyncio
import pytest
import json
from typing import Dict, Any, List, Tuple
from pxos_sync_engine_enhanced import (
    PXOSEngine, Transforms, Profile, ValidationError, 
    TextPaneAdapter, TilesPane, ReplayPane, Pane
)
from py_to_hlir_ast import T_py_to_hlir
from pxos_dsl_parser import T_analog_to_hlir, T_hlir_to_analog
from pxos_schema_validator import validate_hlir
from hlir_to_python import hlir_to_python_compact

class DummyPane:
    """Dummy pane for testing with echo guard simulation"""
    def __init__(self, pane_id: str, initial_text: str = ""):
        self.id = pane_id
        self._text = initial_text
        self.logs: List[Tuple[str, str]] = []
        self.pinned = False
        self.last_writes: List[Tuple[str, int, str]] = []
        self._last_build_id = -1
        
    def read(self) -> str:
        return self._text
        
    def write(self, text: str, *, origin: str, build_id: int) -> None:
        # Echo guard simulation
        if origin == self.id and build_id == self._last_build_id:
            return
        self._last_build_id = build_id
        
        self.last_writes.append((origin, build_id, text))
        self._text = text
        
    def splice(self, i0: int, i1: int, insert_text: str, *, origin: str, build_id: int) -> None:
        # Echo guard simulation
        if origin == self.id and build_id == self._last_build_id:
            return
        self._last_build_id = build_id
        
        old_text = self._text
        new_text = old_text[:i0] + insert_text + old_text[i1:]
        self.last_writes.append((origin, build_id, new_text))
        self._text = new_text
        
    def annotate(self, msg: str, *, severity: str = "error") -> None:
        self.logs.append((severity, msg))
        
    def clear_diagnostics(self) -> None:
        self.logs.clear()

class DummyTilesPane(DummyPane, TilesPane):
    """Dummy tiles pane for testing"""
    def __init__(self, pane_id: str):
        super().__init__(pane_id)
        self.tiles_data = None
        self.ecc_data = None
        
    def render_tiles(self, tiles: Any, ecc_report: Dict[str, int], *, origin: str, build_id: int) -> None:
        if origin == self.id and build_id == self._last_build_id:
            return
        self._last_build_id = build_id
        
        self.last_writes.append(("tiles", build_id, tiles))
        self.tiles_data = tiles
        self.ecc_data = ecc_report

class DummyReplayPane(DummyPane, ReplayPane):
    """Dummy replay pane for testing"""
    def __init__(self, pane_id: str):
        super().__init__(pane_id)
        self.hlir_data = None
        
    def replay_from_hlir(self, hlir: Dict[str, Any], *, origin: str, build_id: int) -> None:
        if origin == self.id and build_id == self._last_build_id:
            return
        self._last_build_id = build_id
        
        self.last_writes.append(("replay", build_id, hlir))
        self.hlir_data = hlir
        
    def log(self, line: str) -> None:
        self.logs.append(("info", line))

class SpliceSpy(DummyPane):
    """Spy pane that tracks splice operations"""
    def __init__(self, pid: str, text: str = ""):
        super().__init__(pid, text)
        self.splices = 0
        
    def splice(self, i0: int, i1: int, text: str, *, origin: str, build_id: int) -> None:
        self.splices += 1
        super().splice(i0, i1, text, origin=origin, build_id=build_id)

@pytest.fixture
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def transforms():
    """Create real transforms for testing"""
    tr = Transforms()
    
    # Use real transforms
    tr.T_py_to_hlir = T_py_to_hlir
    tr.T_analog_to_hlir = T_analog_to_hlir
    tr.T_hlir_to_analog = T_hlir_to_analog
    tr.validate_hlir = validate_hlir
    
    # Minimal stubs for pipeline
    tr.lower_hlir_to_llir = lambda h: [("DRAW_RECT", 0, h)]
    tr.encode_tiles = lambda llir, ecc: [0xC0DE, len(llir)]
    tr.ecc_stats = lambda tiles: {"ok": len(tiles), "corrected": 0, "bad": 0}
    
    return tr

@pytest.fixture
def engine(event_loop, transforms):
    """Create engine for testing"""
    return PXOSEngine(transforms, Profile(), loop=event_loop)

# ======================================================================
# Core Functionality Tests
# ======================================================================

@pytest.mark.asyncio
async def test_p1_valid_propagates(engine):
    """Test that valid P1 edit propagates to all panes"""
    # Setup panes
    p1 = DummyPane("P1", "import viewer_adapter as VA\nVA.RECT(20, 20, 40, 20, 64)\nVA.COMMIT()")
    p2 = DummyPane("P2")
    p3 = DummyPane("P3")
    p4 = DummyTilesPane("P4")
    p5 = DummyPane("P5")
    p6 = DummyReplayPane("P6")
    
    for pane in [p1, p2, p3, p4, p5, p6]:
        engine.register(pane)
    
    # Trigger edit
    engine.on_edit("P1")
    await asyncio.sleep(0.25)  # Wait for debounce
    
    # Verify propagation
    assert "RECT" in p5.read()  # HLIR should contain RECT
    assert "RECT" in p2.read()  # Analog DSL should contain RECT
    assert "RECT" in p3.read()  # Analog DSL should contain RECT
    assert p4.ecc_data["ok"] >= 1  # Tiles should be encoded
    assert p6.hlir_data["program"][0]["op"] == "RECT"  # Replay should have HLIR
    assert p6.hlir_data["program"][1]["op"] == "COMMIT"

@pytest.mark.asyncio
async def test_validation_halts_propagation(engine):
    """Test that validation failure halts propagation"""
    # Setup with invalid Python code
    p1 = DummyPane("P1", "import viewer_adapter as VA\nVA.RECT(20, 20, 40)")  # Missing args
    p2 = DummyPane("P2")
    p3 = DummyPane("P3")
    p4 = DummyTilesPane("P4")
    p5 = DummyPane("P5")
    p6 = DummyReplayPane("P6")
    
    for pane in [p1, p2, p3, p4, p5, p6]:
        engine.register(pane)
    
    # Trigger edit
    engine.on_edit("P1")
    await asyncio.sleep(0.25)
    
    # Verify failure handling
    assert any("RECT requires" in msg for _, msg in p1.logs)  # P1 should be annotated
    assert p4.tiles_data is None  # No new tiles
    assert p6.hlir_data is None  # No new replay

@pytest.mark.asyncio
async def test_pinned_pane_skips_write(engine):
    """Test that pinned panes are not updated"""
    p1 = DummyPane("P1", "import viewer_adapter as VA\nVA.RECT(20, 20, 40, 20, 64)")
    p2 = DummyPane("P2")
    p3 = DummyPane("P3")
    p4 = DummyTilesPane("P4")
    p5 = DummyPane("P5")
    p6 = DummyReplayPane("P6")
    
    # Pin P2
    p2.pinned = True
    
    for pane in [p1, p2, p3, p4, p5, p6]:
        engine.register(pane)
    
    # Trigger edit
    engine.on_edit("P1")
    await asyncio.sleep(0.25)
    
    # Verify pinning behavior
    assert p2.read() == ""  # P2 should remain unchanged (pinned)
    assert "RECT" in p3.read()  # P3 should be updated (not pinned)

@pytest.mark.asyncio
async def test_echo_guard_prevents_loops(engine):
    """Test that echo guard prevents self-updates"""
    p1 = DummyPane("P1", "import viewer_adapter as VA\nVA.RECT(20, 20, 40, 20, 64)")
    p2 = DummyPane("P2")
    p3 = DummyPane("P3")
    p5 = DummyPane("P5")
    
    for pane in [p1, p2, p3, p5]:
        engine.register(pane)
    
    # Trigger edit from P1
    engine.on_edit("P1")
    await asyncio.sleep(0.25)
    
    # Check that P1 doesn't write to itself
    p1_self_writes = [w for w in p1.last_writes if w[0] == "P1"]
    assert len(p1_self_writes) == 0, "P1 should not write to itself"

@pytest.mark.asyncio
async def test_debounce_coalesces_edits(engine):
    """Test that debouncer coalesces rapid edits"""
    p1 = DummyPane("P1", "import viewer_adapter as VA\nVA.RECT(20, 20, 40, 20, 64)")
    p2 = DummyPane("P2")
    p3 = DummyPane("P3")
    p5 = DummyPane("P5")
    
    for pane in [p1, p2, p3, p5]:
        engine.register(pane)
    
    # Trigger multiple rapid edits
    engine.on_edit("P1")
    engine.on_edit("P1")
    engine.on_edit("P1")
    
    await asyncio.sleep(0.25)  # Wait for debounce
    
    # Only one build should have taken effect
    builds = {w[1] for w in p3.last_writes}
    assert len(builds) == 1, "Debouncer should coalesce rapid edits"

# ======================================================================
# Advanced Tests (Your Specific Requests)
# ======================================================================

@pytest.mark.asyncio
async def test_p2_p3_caches_are_distinct(engine):
    """Test that P2 and P3 have separate caches"""
    p1 = DummyPane("P1", "")
    p2 = DummyPane("P2", "RECT(x=20,y=20,w=40,h=20,g=64)\nCOMMIT()")
    p3 = DummyPane("P3", "RECT(x=10,y=10,w=20,h=20,g=128)\nCOMMIT()")
    p4 = DummyTilesPane("P4")
    p5 = DummyPane("P5")
    p6 = DummyReplayPane("P6")
    
    for p in [p1, p2, p3, p4, p5, p6]:
        engine.register(p)

    # Edit P2
    engine.on_edit("P2")
    await asyncio.sleep(0.25)
    h_after_p2 = engine.cache.last_good_hlir

    # Edit P3  
    engine.on_edit("P3")
    await asyncio.sleep(0.25)
    h_after_p3 = engine.cache.last_good_hlir

    # Verify distinct cache hits, no collision
    assert h_after_p2 != h_after_p3, "P2 and P3 should have distinct cache entries"

@pytest.mark.asyncio
async def test_ecc_hot_swap_reencodes(engine):
    """Test that ECC hot-swap triggers re-encode"""
    p1 = DummyPane("P1", "import viewer_adapter as VA\nVA.RECT(20, 20, 40, 20, 64)")
    p2 = DummyPane("P2")
    p3 = DummyPane("P3")
    p4 = DummyTilesPane("P4")
    p5 = DummyPane("P5")
    p6 = DummyReplayPane("P6")
    
    for p in [p1, p2, p3, p4, p5, p6]:
        engine.register(p)

    # First encode with hamming16_12
    engine.on_edit("P1")
    await asyncio.sleep(0.25)
    first_tiles = p4.tiles_data

    # Switch ECC profile
    engine.profile.ecc = "parity"
    engine.on_edit("P1")  # Trigger re-encode
    await asyncio.sleep(0.25)
    second_tiles = p4.tiles_data

    assert first_tiles != second_tiles, "ECC hot-swap should trigger re-encoding"

@pytest.mark.asyncio
async def test_write_uses_splice_when_available(engine):
    """Test that write path uses splice when available"""
    p1 = DummyPane("P1", "import viewer_adapter as VA\nVA.RECT(20, 20, 40, 20, 64)")
    p2 = SpliceSpy("P2")  # Tracks splice calls
    p3 = DummyPane("P3")
    p4 = DummyTilesPane("P4")
    p5 = DummyPane("P5")
    p6 = DummyReplayPane("P6")
    
    for p in [p1, p2, p3, p4, p5, p6]:
        engine.register(p)
    
    engine.on_edit("P1")
    await asyncio.sleep(0.25)
    
    assert p2.splices >= 1, "Should use splice when available"

@pytest.mark.asyncio
async def test_round_trip_fidelity(engine):
    """Test that Python → HLIR → DSL → HLIR preserves semantics"""
    python_code = """
import viewer_adapter as VA
VA.RECT(20, 20, 40, 20, 64)
VA.SLEEP(30)
VA.DAC_WRITE(1, 180)
VA.COMMIT()
"""
    
    p1 = DummyPane("P1", python_code)
    p2 = DummyPane("P2")
    p3 = DummyPane("P3")
    p4 = DummyTilesPane("P4")
    p5 = DummyPane("P5")
    p6 = DummyReplayPane("P6")
    
    for p in [p1, p2, p3, p4, p5, p6]:
        engine.register(p)
    
    # Forward transform: P1 → HLIR → P2/P3
    engine.on_edit("P1")
    await asyncio.sleep(0.25)
    hlir1 = p6.hlir_data
    
    # Reverse transform: P2 → HLIR
    p2._text = p2.read()  # Capture P2 state
    engine.on_edit("P2")
    await asyncio.sleep(0.25)
    hlir2 = p6.hlir_data
    
    # Verify semantic equivalence
    assert hlir1['program'] == hlir2['program'], "Round-trip should preserve semantics"

@pytest.mark.asyncio
async def test_build_info_tracking(engine):
    """Test build information tracking"""
    p1 = DummyPane("P1", "import viewer_adapter as VA\nVA.RECT(20, 20, 40, 20, 64)")
    engine.register(p1)
    
    initial_info = engine.get_build_info()
    assert initial_info['build_id'] == 0
    assert initial_info['truth_origin'] is None
    
    # Trigger edit
    engine.on_edit("P1")
    await asyncio.sleep(0.25)
    
    updated_info = engine.get_build_info()
    assert updated_info['build_id'] == 1
    assert updated_info['truth_origin'] == "P1"

@pytest.mark.asyncio
async def test_force_rebuild_clears_caches(engine):
    """Test that force rebuild clears all caches"""
    p1 = DummyPane("P1", "import viewer_adapter as VA\nVA.RECT(20, 20, 40, 20, 64)")
    engine.register(p1)
    
    # Build up cache
    engine.on_edit("P1")
    await asyncio.sleep(0.25)
    
    assert engine.cache.H_py is not None
    
    # Force rebuild
    engine.force_rebuild()
    
    # Cache should be cleared
    assert engine.cache.H_py is None
    assert engine.cache.H_analog_p2 is None
    assert engine.cache.H_analog_p3 is None

@pytest.mark.asyncio 
async def test_pipeline_error_handling(engine):
    """Test that pipeline errors are handled gracefully"""
    # Setup transform that fails in pipeline
    def failing_lowering(hlir):
        raise Exception("Lowering failed")
    
    engine.tr.lower_hlir_to_llir = failing_lowering
    
    p1 = DummyPane("P1", "import viewer_adapter as VA\nVA.RECT(20, 20, 40, 20, 64)")
    p6 = DummyReplayPane("P6")
    
    for pane in [p1, p6]:
        engine.register(pane)
    
    # Trigger edit
    engine.on_edit("P1")
    await asyncio.sleep(0.25)
    
    # Error should be logged in P6
    error_logs = [log for log in p6.logs if "pipeline error" in log[1] or "Pipeline error" in log[1]]
    assert len(error_logs) > 0, "Pipeline errors should be logged"

# ======================================================================
# Utility Function Tests
# ======================================================================

def test_minimal_edit_computation():
    """Test minimal edit computation"""
    from pxos_sync_engine_enhanced import minimal_edit
    
    old = "Hello world"
    new = "Hello Python world"
    
    i0, i1, j0, j1, insert = minimal_edit(old, new)
    
    # Should identify that "Python " needs to be inserted at position 6
    assert i0 == 6
    assert i1 == 6
    assert insert == "Python "

def test_text_pane_adapter_echo_guard():
    """Test TextPaneAdapter echo guard functionality"""
    from pxos_sync_engine_enhanced import TextPaneAdapter
    
    content = ""
    def get_fn(): 
        return content
    def set_fn(text, origin, build_id): 
        nonlocal content
        content = text
    def annotate_fn(msg, severity): 
        pass
    def clear_fn(): 
        pass
    
    adapter = TextPaneAdapter("P1", get_fn, set_fn, annotate_fn, clear_fn)
    
    # Write from external source
    adapter.write("external text", origin="P2", build_id=1)
    assert content == "external text"
    
    # Attempt self-write (should be blocked)
    adapter.write("self text", origin="P1", build_id=1)
    assert content == "external text"  # Should remain unchanged

# ======================================================================
# Integration Tests
# ======================================================================

@pytest.mark.asyncio
async def test_full_6pane_integration(engine):
    """Test complete 6-pane integration"""
    python_code = """
import viewer_adapter as VA
width = 40
height = 20
VA.RECT(20, 20, width, height, 64)
VA.SLEEP(30)
VA.DAC_WRITE(1, 180)
VA.COMMIT()
"""
    
    # Setup all 6 panes
    p1 = DummyPane("P1", python_code)
    p2 = DummyPane("P2")
    p3 = DummyPane("P3")
    p4 = DummyTilesPane("P4")
    p5 = DummyPane("P5")
    p6 = DummyReplayPane("P6")
    
    for pane in [p1, p2, p3, p4, p5, p6]:
        engine.register(pane)
    
    # Test forward propagation
    engine.on_edit("P1")
    await asyncio.sleep(0.25)
    
    # Verify all panes updated
    assert p2.read() != ""  # Analog mirror updated
    assert p3.read() != ""  # Analog editor updated
    assert p4.tiles_data is not None  # Tiles rendered
    assert "RECT" in p5.read()  # HLIR contains operations
    assert p6.hlir_data is not None  # Replay updated
    
    # Test reverse propagation from P3
    original_p1 = p1.read()
    p3._text = "RECT(x=10,y=10,w=50,h=30,g=128)\nCOMMIT()"
    engine.on_edit("P3")
    await asyncio.sleep(0.25)
    
    # P1 should be updated with new values
    assert p1.read() != original_p1
    assert "10" in p1.read()  # New coordinates should appear

if __name__ == "__main__":
    pytest.main([__file__, "-v"])