import asyncio
import json
import random
import pytest
import os
import time
from hypothesis import given, settings, strategies as st
from pxos_sync_engine import PXOSEngine, Transforms, Profile, ValidationError
from transpiler import T_py_to_hlir
from pxos_dsl import T_analog_to_hlir, T_hlir_to_analog
from validate_hlir import validate_hlir
from hlir_to_py import hlir_to_python
from hall_of_drift import DriftStorage, HallOfDriftController
from diff_utils import json_diff
from typing import Dict, Any
from pxos_lower_encode import lower_hlir_to_llir, encode_tiles, ecc_stats

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
    random.seed(seed)
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
    num_ops=st.integers(min_value=0, max_value=10),  # Include empty programs
    seed=st.integers(min_value=0, max_value=2**32-1)
)

# --- Test fixture ---
@pytest.fixture
def engine_and_panes():
    tr = Transforms()
    tr.T_py_to_hlir = T_py_to_hlir
    tr.T_analog_to_hlir = T_analog_to_hlir
    tr.T_hlir_to_analog = T_hlir_to_analog
    tr.T_hlir_to_py = hlir_to_python
    tr.T_hlir_to_py = hlir_to_python
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

# --- Fuzz test with permutations and auto-display ---
@pytest.mark.asyncio
@settings(max_examples=50, deadline=None)
@given(hlir=hlir_strategy)
async def test_fuzzed_three_origin_convergence(engine_and_panes, hlir):
    engine, p1, p2, p3, p4, p5, p6 = engine_and_panes
    storage = DriftStorage()
    seed = hlir.get("seed", random.randint(0, 2**32-1))
    canonical_hlir = {k: v for k, v in hlir.items() if k != "seed"}
    paths = [
        ("P1", "P3", "P5"),
        ("P3", "P5", "P1"),
        ("P5", "P1", "P3")
    ]
    for start, mid, end in paths:
        for p in (p1, p2, p3, p5):
            p.content = ""
            p.annotations.clear()
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
        try:
            assert final_hlir == canonical_hlir, f"Path {start}→{mid}→{end} failed with seed {seed}"
            assert p4.tiles[1]["ok"] > 0, f"Tiles not rendered for path {start}→{mid}→{end}"
            assert p6.h == canonical_hlir, f"Replay HLIR mismatch for path {start}→{mid}→{end}"
            assert any(f"[build {engine.bus.build_id} from {start}]" in log[1] for log in p6.logs), f"Origin log missing for {start}"
        except AssertionError as e:
            ts = time.strftime("%Y%m%d-%H%M%S")
            folder = Path(f"hall_of_drift/drift_{ts}")
            folder.mkdir(exist_ok=True)
            with open(folder / "canonical.json", "w") as f:
                json.dump(canonical_hlir, f, indent=2)
            with open(folder / "drifted.json", "w") as f:
                json.dump(final_hlir, f, indent=2)
            with open(folder / "path.txt", "w") as f:
                f.write(f"{start} -> {mid} -> {end}")
            with open(folder / "seed.txt", "w") as f:
                f.write(str(seed))
            with open(folder / "replay.py", "w") as f:
                f.write(f"""from pxos_sync_engine import PXOSEngine, Transforms, Profile
from transpiler import T_py_to_hlir
from pxos_dsl import T_analog_to_hlir, T_hlir_to_analog
from validate_hlir import validate_hlir
from hlir_to_py import hlir_to_python
from diff_utils import json_diff
from main import PXOSWorkbench
import json
import tkinter as tk
tr = Transforms()
tr.T_py_to_hlir = T_py_to_hlir
tr.T_analog_to_hlir = T_analog_to_hlir
tr.T_hlir_to_analog = T_hlir_to_analog
tr.validate_hlir = validate_hlir
tr.lower_hlir_to_llir = lambda h: [("OP", i) for i, op in enumerate(h["program"])]
tr.encode_tiles = lambda llir, ecc: [f"{{ecc}}:{{op}}" for op in llir]
tr.ecc_stats = lambda tiles: {{"ok": len(tiles), "corrected": 0, "bad": 0}}
engine = PXOSEngine(tr, Profile())
app = PXOSWorkbench()
app.hall_controller.current_scroll = {{
    "id": "drift_{ts}",
    "canonical": json.load(open("{folder}/canonical.json")),
    "drifted": json.load(open("{folder}/drifted.json")),
    "path": "{start} -> {mid} -> {end}",
    "seed": {seed},
    "status": "Unreviewed",
    "annotation": ""
}}
app.hall_controller.state = "DETAIL_VIEW"
app.hall_controller.render_detail_view()
app.mainloop()
""")
            raise

# --- Echo guard test ---
@pytest.mark.asyncio
async def test_echo_guard_no_rewrite(engine_and_panes):
    engine, p1, p2, p3, p4, p5, p6 = engine_and_panes
    canonical_hlir = random_hlir_program(num_ops=3, seed=42)
    p1.content = hlir_to_python(canonical_hlir)

    engine.on_edit("P1")
    await asyncio.sleep(0.25)

    initial_p3_content = p3.content
    initial_p5_content = p5.content

    engine.on_edit("P3")
    await asyncio.sleep(0.25)

    assert p3.content == initial_p3_content, "P3 was rewritten unnecessarily"
    assert p5.content == initial_p5_content, "P5 was rewritten unnecessarily"
