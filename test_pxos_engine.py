#!/usr/bin/env python3
"""
Pytest harness for PXOS Enhanced Sync Engine
Tests invariants: echo guards, validation halts, pinning, debouncing
"""

import asyncio
import pytest
import json
from pxos_sync_engine_enhanced import (
    PXOSEngine, Transforms, Profile, ValidationError, 
    TextPaneAdapter, TilesPane, ReplayPane, Pane
)

class DummyPane:
    """Dummy pane for testing"""
    def __init__(self, pane_id, initial_text=""):
        self.id = pane_id
        self._text = initial_text
        self.logs = []
        self.pinned = False
        self.last_writes = []
        
    def read(self):
        return self._text
        
    def write(self, text, *, origin, build_id):
        self.last_writes.append((origin, build_id, text))
        self._text = text
        
    def annotate(self, msg, *, severity="error"):
        self.logs.append((severity, msg))
        
    def clear_diagnostics(self):
        self.logs.clear()

class DummyTilesPane(DummyPane, TilesPane):
    """Dummy tiles pane for testing"""
    def __init__(self, pane_id):
        super().__init__(pane_id)
        self.tiles_data = None
        self.ecc_data = None
        
    def render_tiles(self, tiles, ecc_report, *, origin, build_id):
        self.last_writes.append(("tiles", build_id, tiles))
        self.tiles_data = tiles
        self.ecc_data = ecc_report

class DummyReplayPane(DummyPane, ReplayPane):
    """Dummy replay pane for testing"""
    def __init__(self, pane_id):
        super().__init__(pane_id)
        self.hlir_data = None
        
    def replay_from_hlir(self, hlir, *, origin, build_id):
        self.last_writes.append(("replay", build_id, hlir))
        self.hlir_data = hlir
        
    def log(self, line):
        self.logs.append(("info", line))

@pytest.fixture
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def transforms():
    """Create dummy transforms for testing"""
    tr = Transforms()
    
    # Simple transform that creates valid HLIR
    tr.T_py_to_hlir = lambda s: {
        "schemaVersion": "pxos-ops/1.0",
        "meta": {"profile": "default", "cols": 16},
        "program": [{"op": "RECT", "x": 1, "y": 2, "w": 3, "h": 4, "r": 5, "g": 5, "b": 5}]
    }
    
    tr.T_analog_to_hlir = lambda s: {
        "schemaVersion": "pxos-ops/1.0", 
        "meta": {"profile": "default", "cols": 16},
        "program": [{"op": "COMMIT"}]
    }
    
    tr.T_hlir_to_analog = lambda h: "RECT(x=1,y=2,w=3,h=4,g=5)"
    
    # Validation that fails if "bad" is in the HLIR
    def validate_hlir(hlir):
        if "bad" in str(hlir):
            raise ValidationError("Contains 'bad' marker")
    tr.validate_hlir = validate_hlir
    
    tr.lower_hlir_to_llir = lambda h: [("DRAW_RECT", 0)]
    tr.encode_tiles = lambda llir, ecc: [0xC0DE]
    tr.ecc_stats = lambda tiles: {"ok": len(tiles), "corrected": 0, "bad": 0}
    
    return tr

@pytest.fixture
def engine(event_loop, transforms):
    """Create engine for testing"""
    return PXOSEngine(transforms, Profile(), loop=event_loop)

@pytest.mark.asyncio
async def test_p1_valid_propagates(engine):
    """Test that valid P1 edit propagates to all panes"""
    # Setup panes
    p1 = DummyPane("P1", "print('hi')")
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
    assert p4.ecc_data["ok"] == 1  # Tiles should be encoded
    assert p6.hlir_data["program"][0]["op"] == "RECT"  # Replay should have HLIR

@pytest.mark.asyncio
async def test_validation_halts_propagation(engine):
    """Test that validation failure halts propagation"""
    # Setup transforms to fail validation
    engine.tr.T_py_to_hlir = lambda s: {"bad": True}
    
    p1 = DummyPane("P1", "some code")
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
    assert any("bad" in msg for _, msg in p1.logs)  # P1 should be annotated
    assert not hasattr(p4, "tiles_data") or p4.tiles_data is None  # No new tiles
    assert not hasattr(p6, "hlir_data") or p6.hlir_data is None  # No new replay

@pytest.mark.asyncio
async def test_pinned_pane_skips_write(engine):
    """Test that pinned panes are not updated"""
    p1 = DummyPane("P1", "code")
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
    assert p3.read() != ""  # P3 should be updated (not pinned)

@pytest.mark.asyncio
async def test_echo_guard_prevents_loops(engine):
    """Test that echo guard prevents self-updates"""
    p1 = DummyPane("P1", "code")
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
    p1 = DummyPane("P1", "a")
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

@pytest.mark.asyncio
async def test_separate_analog_caches(engine):
    """Test that P2 and P3 have separate caches"""
    p2 = DummyPane("P2", "analog_code_p2")
    p3 = DummyPane("P3", "analog_code_p3")
    p5 = DummyPane("P5")
    
    for pane in [p2, p3, p5]:
        engine.register(pane)
    
    # Edit P2
    engine.on_edit("P2")
    await asyncio.sleep(0.25)
    
    # Check cache state
    assert engine.cache.H_analog_p2 is not None
    assert engine.cache.H_analog_p3 is None  # P3 cache should be separate
    
    # Edit P3
    engine.on_edit("P3")
    await asyncio.sleep(0.25)
    
    # Both caches should now be set
    assert engine.cache.H_analog_p2 is not None
    assert engine.cache.H_analog_p3 is not None
    assert engine.cache.H_analog_p2 != engine.cache.H_analog_p3

@pytest.mark.asyncio
async def test_build_info_tracking(engine):
    """Test build information tracking"""
    p1 = DummyPane("P1", "code")
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
    p1 = DummyPane("P1", "code")
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
    
    p1 = DummyPane("P1", "code")
    p6 = DummyReplayPane("P6")
    
    for pane in [p1, p6]:
        engine.register(pane)
    
    # Trigger edit
    engine.on_edit("P1")
    await asyncio.sleep(0.25)
    
    # Error should be logged in P6
    error_logs = [log for log in p6.logs if "pipeline error" in log[1]]
    assert len(error_logs) > 0, "Pipeline errors should be logged"

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
    def get_fn(): return content
    def set_fn(text, origin, build_id): 
        nonlocal content
        content = text
    def annotate_fn(msg, severity): pass
    def clear_fn(): pass
    
    adapter = TextPaneAdapter("P1", get_fn, set_fn, annotate_fn, clear_fn)
    
    # Write from external source
    adapter.write("external text", origin="P2", build_id=1)
    assert content == "external text"
    
    # Attempt self-write (should be blocked)
    adapter.write("self text", origin="P1", build_id=1)
    assert content == "external text"  # Should remain unchanged

if __name__ == "__main__":
    pytest.main([__file__, "-v"])