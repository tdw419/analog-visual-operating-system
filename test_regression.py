import pytest
import json
from pathlib import Path
from pxos_sync_engine import PXOSEngine, Transforms, Profile
from transpiler import T_py_to_hlir
from pxos_dsl import T_analog_to_hlir, T_hlir_to_analog
from validate_hlir import validate_hlir
from hlir_to_py import hlir_to_python
from pxos_lower_encode import lower_hlir_to_llir, encode_tiles, ecc_stats
from test_lineage_fuzz import DummyPane, DummyTiles, DummyReplay

@pytest.fixture
def engine_and_panes():
    tr = Transforms()
    tr.T_py_to_hlir = T_py_to_hlir
    tr.T_analog_to_hlir = T_analog_to_hlir
    tr.T_hlir_to_analog = T_hlir_to_analog
    tr.validate_hlir = validate_hlir
    tr.lower_hlir_to_llir = lower_hlir_to_llir
    tr.encode_tiles = encode_tiles
    tr.ecc_stats = ecc_stats
    engine = PXOSEngine(tr, Profile(ecc="hamming16_12"))
    p1 = DummyPane("P1", engine)
    p2 = DummyPane("P2", engine)
    p3 = DummyPane("P3", engine)
    p4 = DummyTiles("P4", engine)
    p5 = DummyPane("P5", engine)
    p6 = DummyReplay("P6", engine)
    for p in (p1, p2, p3, p4, p5, p6):
        engine.register(p)
    return engine, p1, p2, p3, p4, p5, p6

def load_regression_tests():
    regression_path = Path("hall_of_drift/regression_tests")
    if not regression_path.exists():
        return []
    tests = []
    for test_file in regression_path.glob("*.json"):
        with open(test_file) as f:
            test_data = json.load(f)
            tests.append((test_data["canonical"], test_data["path"], test_data["seed"]))
    return tests

@pytest.mark.asyncio
@pytest.mark.parametrize("canonical_hlir, path, seed", load_regression_tests())
async def test_regression_cases(engine_and_panes, canonical_hlir, path, seed):
    engine, p1, p2, p3, p4, p5, p6 = engine_and_panes
    path = path.split(" -> ")
    for p in (p1, p2, p3, p5):
        p.content = ""
        p.annotations.clear()
    start, mid, end = path
    if start == "P1":
        p1.content = hlir_to_python(canonical_hlir)
    elif start == "P3":
        p3.content = T_hlir_to_analog(canonical_hlir)
    elif start == "P5":
        p5.content = json.dumps(canonical_hlir)
    engine.on_edit(start)
    await asyncio.sleep(0.25)
    mid_pane = {"P1": p1, "P3": p3, "P5": p5}[mid]
    mid_pane.write(mid_pane.read(), origin=mid, build_id=engine.bus.build_id + 1)
    engine.on_edit(mid)
    await asyncio.sleep(0.25)
    end_pane = {"P1": p1, "P3": p3, "P5": p5}[end]
    if end == "P1":
        final_hlir = T_py_to_hlir(end_pane.read())
    elif end == "P3":
        final_hlir = T_analog_to_hlir(end_pane.read())
    elif end == "P5":
        final_hlir = json.loads(end_pane.read())
    assert final_hlir == canonical_hlir, f"Regression test failed for seed {seed} on path {path}"
