import asyncio, pytest
from pxos_sync_engine import PXOSEngine, Transforms, ValidationError, Profile
from transpiler import T_py_to_hlir
from pxos_dsl import T_analog_to_hlir, T_hlir_to_analog
from hlir_to_py import hlir_to_python
from validate_hlir import validate_hlir
from typing import Dict, Any

class DummyPane:
    def __init__(self, pid, text=""):
        self.id = pid; self._t = text; self.logs = []; self.pinned=False; self.last=[]
    def read(self): return self._t
    def write(self, text, *, origin, build_id): self.last.append((origin, build_id)); self._t = text
    def annotate(self, msg, *, severity="error"): self.logs.append((severity, msg))
    def clear_diagnostics(self): self.logs.clear()

class DummyTiles(DummyPane):
    def __init__(self, pid, text=""): super().__init__(pid, text); self.tiles=None
    def render_tiles(self, tiles, ecc_report, *, origin, build_id):
        self.last.append(("tiles", build_id)); self.tiles = (tiles, ecc_report)

class DummyReplay(DummyPane):
    def __init__(self, pid, text=""): super().__init__(pid, text); self.h=None
    def replay_from_hlir(self, hlir, *, origin, build_id):
        self.last.append(("replay", build_id)); self.h = hlir
    def log(self, line): self.logs.append(("info", line))

@pytest.fixture
def engine():
    tr = Transforms()
    tr.T_py_to_hlir       = T_py_to_hlir
    tr.T_analog_to_hlir   = T_analog_to_hlir
    tr.T_hlir_to_analog   = T_hlir_to_analog
    tr.T_hlir_to_py       = hlir_to_python
    tr.validate_hlir      = validate_hlir
    tr.lower_hlir_to_llir = lambda h: [("DRAW_RECT", 0)]
    tr.encode_tiles       = lambda llir, ecc: [0xC0DE] if ecc == "hamming16_12" else [0xBEEF]
    tr.ecc_stats          = lambda tiles: {"ok": len(tiles)}
    return PXOSEngine(tr, profile=Profile())

class SpliceSpy(DummyPane):
    def __init__(self, pid, text=""): super().__init__(pid, text); self.splices=0
    def splice(self, i0,i1,text,*,origin,build_id): self.splices+=1; super().write(self.read()[:i0] + text + self.read()[i1:], origin=origin, build_id=build_id)


@pytest.mark.asyncio
async def test_p1_valid_propagates(engine):
    p1, p2, p3 = DummyPane("P1","RECT(1,2,3,4,5)"), DummyPane("P2"), DummyPane("P3")
    p4, p5, p6 = DummyTiles("P4"), DummyPane("P5"), DummyReplay("P6")
    for p in [p1,p2,p3,p4,p5,p6]: engine.register(p)
    engine.on_edit("P1"); await asyncio.sleep(0.25)
    assert "RECT" in p5.read()
    assert "RECT" in p2.read()
    assert p4.tiles[1]["ok"] == 1
    assert p6.h["program"][0]["op"] == "RECT"

@pytest.mark.asyncio
async def test_validation_halts(engine):
    engine.tr.T_py_to_hlir = lambda s: {"bad":True}
    p1, p2, p3 = DummyPane("P1","x"), DummyPane("P2"), DummyPane("P3")
    p4, p5, p6 = DummyTiles("P4"), DummyPane("P5"), DummyReplay("P6")
    for p in [p1,p2,p3,p4,p5,p6]: engine.register(p)
    engine.on_edit("P1"); await asyncio.sleep(0.25)
    assert any("required" in m for _,m in p1.logs)
    assert p4.tiles is None
    assert p6.h is None

@pytest.mark.asyncio
async def test_pinned_skips_write(engine):
    p1, p2, p3 = DummyPane("P1","COMMIT()"), DummyPane("P2"), DummyPane("P3")
    p2.pinned = True
    p4, p5, p6 = DummyTiles("P4"), DummyPane("P5"), DummyReplay("P6")
    for p in [p1,p2,p3,p4,p5,p6]: engine.register(p)
    engine.on_edit("P1"); await asyncio.sleep(0.25)
    assert p2.read() == ""
    assert len(p3.last) > 0 # check that a write was attempted

@pytest.mark.asyncio
async def test_debounce_coalesces(engine):
    p1, p2, p3 = DummyPane("P1","COMMIT()"), DummyPane("P2"), DummyPane("P3")
    p4, p5, p6 = DummyTiles("P4"), DummyPane("P5"), DummyReplay("P6")
    for p in [p1,p2,p3,p4,p5,p6]: engine.register(p)
    engine.on_edit("P1"); engine.on_edit("P1"); engine.on_edit("P1")
    await asyncio.sleep(0.25)
    # Check that any pane was updated, but only once
    all_builds = {b for p in [p2,p3,p5] for _,b in p.last}
    assert len(all_builds) == 1

@pytest.mark.asyncio
async def test_p2_p3_caches_are_distinct(engine):
    p1,p2,p3 = DummyPane("P1",""), DummyPane("P2","SUM([0],1)"), DummyPane("P3","SUM([0,1],2)")
    p4,p5,p6 = DummyTiles("P4"), DummyPane("P5"), DummyReplay("P6")
    for p in [p1,p2,p3,p4,p5,p6]: engine.register(p)

    # Pin other panes to prevent the first edit from overwriting the second one's source
    p1.pinned = True
    p3.pinned = True

    engine.on_edit("P2"); await asyncio.sleep(0.25)
    h_after_p2 = engine.cache.last_good_hlir

    # Unpin p3 so the second edit can be sourced from it
    p3.pinned = False
    p2.pinned = True # Pin p2 to prevent write-back

    engine.on_edit("P3"); await asyncio.sleep(0.25)
    h_after_p3 = engine.cache.last_good_hlir

    assert h_after_p2 != h_after_p3

@pytest.mark.asyncio
async def test_ecc_hot_swap_reencodes(engine):
    p1,p2,p3 = DummyPane("P1","RECT(1,2,3,4,5)"), DummyPane("P2"), DummyPane("P3")
    p4,p5,p6 = DummyTiles("P4"), DummyPane("P5"), DummyReplay("P6")
    for p in [p1,p2,p3,p4,p5,p6]: engine.register(p)

    engine.on_edit("P1"); await asyncio.sleep(0.25)
    first_tiles = p4.tiles

    engine.profile.ecc = "parity"
    engine.on_edit("P1"); await asyncio.sleep(0.25)
    second_tiles = p4.tiles

    assert first_tiles != second_tiles

@pytest.mark.asyncio
async def test_write_uses_splice_when_available(engine):
    p1, p2, p3 = DummyPane("P1","COMMIT()"), SpliceSpy("P2", "initial text"), DummyPane("P3")
    p4,p5,p6 = DummyTiles("P4"), DummyPane("P5"), DummyReplay("P6")
    for p in [p1,p2,p3,p4,p5,p6]: engine.register(p)
    engine.on_edit("P1"); await asyncio.sleep(0.25)
    assert p2.splices >= 1
