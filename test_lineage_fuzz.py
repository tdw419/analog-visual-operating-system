# test_lineage_fuzz.py - Fuzz-Powered Triple-Origin Convergence Tests
import asyncio
import json
import random
import pytest
import itertools
from hypothesis import given, settings, strategies as st
from pxos_sync_engine_enhanced import PXOSEngine, Transforms, Profile, ValidationError
from transpiler import T_py_to_hlir
from pxos_dsl import T_analog_to_hlir, T_hlir_to_analog
from validate_hlir import validate_hlir
from hlir_to_py import hlir_to_python
from typing import Dict, Any

# --- Dummy pane for testing ---
class DummyPane:
    def __init__(self, pid: str, engine: PXOSEngine):
        self.id = pid
        self.engine = engine
        self._last_build_id = -1
        self.content = ""
        self.annotations = []
        self.pinned = False
    def read(self) -> str:
        return self.content
    def write(self, text: str, *, origin: str, build_id: int) -> None:
        if origin == self.id and build_id == self._last_build_id:
            return
        self._last_build_id = build_id
        self.content = text
    def splice(self, i0: int, i1: int, text: str, *, origin: str, build_id: int) -> None:
        if origin == self.id and build_id == self._last_build_id:
            return
        self._last_build_id = build_id
        old = self.content
        self.content = old[:i0] + text + old[i1:]
    def annotate(self, message: str, *, severity: str="error") -> None:
        self.annotations.append((severity, message))
    def clear_diagnostics(self) -> None:
        self.annotations.clear()

class DummyTiles(DummyPane):
    def render_tiles(self, tiles: Any, ecc_report: Dict[str,int], *, origin: str, build_id: int) -> None:
        if origin == self.id and build_id == self._last_build_id:
            return
        self._last_build_id = build_id
        self.tiles = (tiles, ecc_report)

class DummyReplay(DummyPane):
    def replay_from_hlir(self, hlir: Dict[str, Any], *, origin: str, build_id: int) -> None:
        if origin == self.id and build_id == self._last_build_id:
            return
        self._last_build_id = build_id
        self.h = hlir
    def log(self, line: str) -> None:
        self.logs = getattr(self, 'logs', [])
        self.logs.append(("info", line))

# --- HLIR fuzz generator ---
OPS = ["RECT", "SLEEP", "COMMIT", "DAC_WRITE", "INTEGRATE", "FILTER", "MULTIPLY", "SUM"]
FILTER_TYPES = ["lp", "hp", "bp", "notch"]

def random_hlir_program(num_ops: int, seed: int) -> Dict[str, Any]:
    random.seed(seed)  # Ensure reproducibility
    prog = []
    for _ in range(num_ops):
        op = random.choice(OPS)
        if op == "RECT":
            prog.append({
                "op": "RECT",
                "x": random.randint(0, 255),
                "y": random.randint(0, 255),
                "w": random.randint(1, 255),
                "h": random.randint(1, 255),
                "r": random.randint(0, 255),
                "g": random.randint(0, 255),
                "b": random.randint(0, 255)
            })
        elif op == "SLEEP":
            prog.append({"op": "SLEEP", "ms": random.randint(0, 10000)})
        elif op == "COMMIT":
            prog.append({"op": "COMMIT"})
        elif op == "DAC_WRITE":
            prog.append({"op": "DAC_WRITE", "ch": random.randint(0, 31), "val": random.randint(0, 65535)})
        elif op == "INTEGRATE":
            prog.append({"op": "INTEGRATE", "tau": random.uniform(0.001, 10.0), "src": random.randint(0, 7), "dst": random.randint(0, 7)})
        elif op == "FILTER":
            prog.append({"op": "FILTER", "type": random.choice(FILTER_TYPES), "fc": random.randint(0, 10000), "src": random.randint(0, 7), "dst": random.randint(0, 7)})
        elif op == "MULTIPLY":
            prog.append({"op": "MULTIPLY", "gain": random.uniform(-10.0, 10.0), "src": random.randint(0, 7), "dst": random.randint(0, 7)})
        elif op == "SUM":
            inputs = [random.randint(0, 7) for _ in range(random.randint(1, 4))]
            prog.append({"op": "SUM", "inputs": inputs, "output": random.randint(0, 7)})
    return {
        "schemaVersion": "pxos-ops/1.0",
        "meta": {"profile": "default", "cols": 16},
        "program": prog
    }

# --- Hypothesis strategies for property-based testing ---
hlir_strategy = st.builds(
    random_hlir_program,
    num_ops=st.integers(min_value=1, max_value=10),
    seed=st.integers(min_value=0, max_value=2**32-1)
)

# --- Test fixture ---
@pytest.fixture
def engine_and_panes():
    tr = Transforms()
    tr.T_py_to_hlir = T_py_to_hlir
    tr.T_analog_to_hlir = T_analog_to_hlir
    tr.T_hlir_to_analog = T_hlir_to_analog
    tr.validate_hlir = validate_hlir
    tr.lower_hlir_to_llir = lambda h: [("OP", i) for i, op in enumerate(h["program"])]
    tr.encode_tiles = lambda llir, ecc: [f"{ecc}:{op}" for op in llir]
    tr.ecc_stats = lambda tiles: {"ok": len(tiles), "corrected": 0, "bad": 0}
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

# --- Fuzz test with permutations ---
@pytest.mark.asyncio
@settings(max_examples=50, deadline=None)
@given(hlir=hlir_strategy)
async def test_fuzzed_three_origin_convergence(engine_and_panes, hlir):
    engine, p1, p2, p3, p4, p5, p6 = engine_and_panes
    seed = hlir.get("seed", random.randint(0, 2**32-1))  # Extract seed for reproducibility
    canonical_hlir = {k: v for k, v in hlir.items() if k != "seed"}  # Remove seed from comparison

    # Permutation paths: P1→P3→P5, P3→P5→P1, P5→P1→P3
    paths = [
        ("P1", "P3", "P5"),
        ("P3", "P5", "P1"),
        ("P5", "P1", "P3")
    ]

    for start, mid, end in paths:
        # Reset panes
        for p in (p1, p2, p3, p5):
            p.content = ""
            p.annotations.clear()

        # Seed the starting pane
        if start == "P1":
            p1.content = hlir_to_python(canonical_hlir)
        elif start == "P3":
            p3.content = T_hlir_to_analog(canonical_hlir)
        elif start == "P5":
            p5.content = json.dumps(canonical_hlir)

        # Propagate from start
        engine.on_edit(start)
        await asyncio.sleep(0.25)

        # Propagate from mid
        mid_pane = {"P1": p1, "P3": p3, "P5": p5}[mid]
        mid_pane.write(mid_pane.read(), origin=mid, build_id=engine.bus.build_id + 1)
        engine.on_edit(mid)
        await asyncio.sleep(0.25)

        # Extract HLIR from end pane
        end_pane = {"P1": p1, "P3": p3, "P5": p5}[end]
        if end == "P1":
            final_hlir = T_py_to_hlir(end_pane.read())
        elif end == "P3":
            final_hlir = T_analog_to_hlir(end_pane.read())
        elif end == "P5":
            final_hlir = json.loads(end_pane.read())

        # Verify convergence
        try:
            assert final_hlir == canonical_hlir, f"Path {start}→{mid}→{end} failed with seed {seed}"
            assert p4.tiles[1]["ok"] > 0, f"Tiles not rendered for path {start}→{mid}→{end}"
            assert p6.h == canonical_hlir, f"Replay HLIR mismatch for path {start}→{mid}→{end}"
            assert any(f"[build {engine.bus.build_id} from {start}]" in log[1] for log in p6.logs), f"Origin log missing for {start}"
        except AssertionError as e:
            # Log failure details for debugging
            with open(f"hall_of_drift_seed_{seed}.json", "w") as f:
                json.dump({
                    "seed": seed,
                    "canonical_hlir": canonical_hlir,
                    "final_hlir": final_hlir,
                    "path": f"{start}→{mid}→{end}",
                    "error": str(e)
                }, f, indent=2)
            raise

# --- Echo guard test ---
@pytest.mark.asyncio
async def test_echo_guard_no_rewrite(engine_and_panes):
    engine, p1, p2, p3, p4, p5, p6 = engine_and_panes
    canonical_hlir = random_hlir_program(num_ops=3, seed=42)
    p1.content = hlir_to_python(canonical_hlir)
    
    # Initial propagation
    engine.on_edit("P1")
    await asyncio.sleep(0.25)
    
    # Store initial state
    initial_p3_content = p3.content
    initial_p5_content = p5.content
    
    # Try to re-propagate same content
    engine.on_edit("P3")
    await asyncio.sleep(0.25)
    
    # Verify no unnecessary rewrites
    assert p3.content == initial_p3_content, "P3 was rewritten unnecessarily"
    assert p5.content == initial_p5_content, "P5 was rewritten unnecessarily"

# --- Round-trip integrity for specific operations ---
@pytest.mark.asyncio
async def test_rect_round_trip_integrity(engine_and_panes):
    engine, p1, p2, p3, p4, p5, p6 = engine_and_panes
    
    # Test simple RECT
    original_hlir = {
        "schemaVersion": "pxos-ops/1.0",
        "meta": {"profile": "default", "cols": 16},
        "program": [
            {"op": "RECT", "x": 20, "y": 20, "w": 40, "h": 20, "r": 64, "g": 64, "b": 64},
            {"op": "COMMIT"}
        ]
    }
    
    # P1 → P3 → P1 round trip
    p1.content = hlir_to_python(original_hlir)
    engine.on_edit("P1")
    await asyncio.sleep(0.1)
    
    engine.on_edit("P3")  # Trigger P3 transform
    await asyncio.sleep(0.1)
    
    final_hlir = T_py_to_hlir(p1.content)
    assert final_hlir == original_hlir, "RECT round-trip failed"

@pytest.mark.asyncio  
async def test_complex_operation_round_trip(engine_and_panes):
    engine, p1, p2, p3, p4, p5, p6 = engine_and_panes
    
    # Test complex program with multiple operations
    original_hlir = {
        "schemaVersion": "pxos-ops/1.0",
        "meta": {"profile": "default", "cols": 16},
        "program": [
            {"op": "RECT", "x": 10, "y": 10, "w": 30, "h": 30, "r": 128, "g": 128, "b": 128},
            {"op": "SLEEP", "ms": 100},
            {"op": "DAC_WRITE", "ch": 1, "val": 180},
            {"op": "INTEGRATE", "tau": 0.5, "src": 0, "dst": 1},
            {"op": "COMMIT"}
        ]
    }
    
    # Test all permutation paths
    paths = list(itertools.permutations(["P1", "P3", "P5"], 3))
    
    for path in paths:
        # Reset panes
        p1.content = ""
        p3.content = ""
        p5.content = ""
        
        # Seed first origin
        if path[0] == "P1":
            p1.content = hlir_to_python(original_hlir)
        elif path[0] == "P3":
            p3.content = T_hlir_to_analog(original_hlir)
        elif path[0] == "P5":
            p5.content = json.dumps(original_hlir)
        
        # Execute path
        for origin in path:
            engine.on_edit(origin)
            await asyncio.sleep(0.1)
        
        # Verify final HLIR
        final_hlir = engine.cache.last_good_hlir
        assert final_hlir == original_hlir, f"Complex round-trip failed on path {path}"

# --- Schema validation test ---
@pytest.mark.asyncio
async def test_schema_validation_integration(engine_and_panes):
    engine, p1, p2, p3, p4, p5, p6 = engine_and_panes
    
    # Valid HLIR should pass
    valid_hlir = {
        "schemaVersion": "pxos-ops/1.0",
        "meta": {"profile": "default", "cols": 16},
        "program": [{"op": "COMMIT"}]
    }
    
    p5.content = json.dumps(valid_hlir)
    engine.on_edit("P5")
    await asyncio.sleep(0.1)
    
    assert engine.cache.last_good_hlir == valid_hlir
    assert len(p5.annotations) == 0  # No validation errors

@pytest.mark.asyncio
async def test_schema_validation_rejection(engine_and_panes):
    engine, p1, p2, p3, p4, p5, p6 = engine_and_panes
    
    # Invalid HLIR should be rejected
    invalid_hlir = {
        "schemaVersion": "pxos-ops/1.0",
        "program": [{"op": "INVALID_OP"}]  # Missing meta, invalid op
    }
    
    p5.content = json.dumps(invalid_hlir)
    engine.on_edit("P5")
    await asyncio.sleep(0.1)
    
    # Should have validation error
    assert len(p5.annotations) > 0
    assert p5.annotations[0][0] == "error"  # Severity should be error