import asyncio
import json
import random
import hashlib
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

from pxos_sync_engine import PXOSEngine, Transforms, Profile, ValidationError
from transpiler import T_py_to_hlir
from validate_hlir import validate_hlir
from hlir_to_py import hlir_to_python
from pxos_dsl import T_analog_to_hlir, T_hlir_to_analog

@dataclass
class LineageFailure:
    """Records a transform integrity failure for the Hall of Drift"""
    timestamp: str
    seed: int
    original_hlir: Dict[str, Any]
    failure_origin: str
    divergent_hlir: Dict[str, Any]
    error_hash: str

    def to_scroll(self) -> str:
        """Format as a ceremonial scroll entry"""
        return f"""
═══ LINEAGE DRIFT DETECTED ═══
Time: {self.timestamp}
Seed: {self.seed} (replay with: random.seed({self.seed}))
Origin: {self.failure_origin}
Error Hash: {self.error_hash}

Original HLIR:
{json.dumps(self.original_hlir, indent=2)}

Divergent HLIR:
{json.dumps(self.divergent_hlir, indent=2)}

═══ END SCROLL ═══
"""

class PXOSLineageSentinel:
    """Continuous guardian of PXOS transform integrity"""

    def __init__(self, engine: PXOSEngine, hall_of_drift_path: Path = Path("hall_of_drift")):
        self.engine = engine
        self.hall_of_drift = hall_of_drift_path
        self.hall_of_drift.mkdir(exist_ok=True)

        self.ops = {
            "RECT": self._gen_rect,
            "SLEEP": self._gen_sleep,
            "COMMIT": self._gen_commit,
            "DAC_WRITE": self._gen_dac_write,
            "INTEGRATE": self._gen_integrate,
            "FILTER": self._gen_filter,
            "MULTIPLY": self._gen_multiply,
            "SUM": self._gen_sum,
        }

        class SentinelPane:
            def __init__(self, pid: str):
                self.id = pid
                self.content = ""
                self.logs = []
                self.pinned = False
                self._last_build_id = -1
            def read(self): return self.content
            def write(self, text: str, *, origin: str, build_id: int):
                if origin == self.id and build_id == self._last_build_id: return
                self._last_build_id = build_id
                self.content = text
            def splice(self, i0: int, i1: int, text: str, *, origin: str, build_id: int):
                if origin == self.id and build_id == self._last_build_id: return
                self._last_build_id = build_id
                old = self.content
                self.content = old[:i0] + text + old[i1:]
            def annotate(self, msg: str, *, severity: str = "error"): self.logs.append((severity, msg))
            def clear_diagnostics(self): self.logs.clear()

        self.test_panes = { pid: SentinelPane(pid) for pid in ["P1", "P2", "P3", "P5"] }
        for pane in self.test_panes.values():
            engine.register(pane)

    def _gen_rect(self) -> Dict[str, Any]:
        return {"op": "RECT", "x": random.randint(0, 255), "y": random.randint(0, 255), "w": random.randint(1, 255), "h": random.randint(1, 255), "r": random.randint(0, 255), "g": random.randint(0, 255), "b": random.randint(0, 255)}
    def _gen_sleep(self) -> Dict[str, Any]: return {"op": "SLEEP", "ms": random.randint(0, 5000)}
    def _gen_commit(self) -> Dict[str, Any]: return {"op": "COMMIT"}
    def _gen_dac_write(self) -> Dict[str, Any]: return {"op": "DAC_WRITE", "ch": random.randint(0, 7), "val": random.randint(0, 255)}
    def _gen_integrate(self) -> Dict[str, Any]: return {"op": "INTEGRATE", "tau": round(random.uniform(0.001, 10.0), 3), "src": random.randint(0, 7), "dst": random.randint(0, 7)}
    def _gen_filter(self) -> Dict[str, Any]: return {"op": "FILTER", "type": random.choice(["lp", "hp", "bp", "notch"]), "fc": random.randint(1, 10000), "src": random.randint(0, 7), "dst": random.randint(0, 7)}
    def _gen_multiply(self) -> Dict[str, Any]: return {"op": "MULTIPLY", "gain": round(random.uniform(0.1, 10.0), 2), "src": random.randint(0, 7), "dst": random.randint(0, 7)}
    def _gen_sum(self) -> Dict[str, Any]:
        num_inputs = random.randint(2, 5)
        inputs = [random.randint(0, 7) for _ in range(num_inputs)]
        return {"op": "SUM", "inputs": inputs, "output": random.randint(0, 7)}

    def generate_random_hlir(self, num_ops: int = None) -> Dict[str, Any]:
        if num_ops is None: num_ops = random.randint(1, 8)
        program = [self.ops[random.choice(list(self.ops.keys()))]() for _ in range(num_ops)]
        if not any(op.get("op") == "COMMIT" for op in program): program.append(self._gen_commit())
        return {"schemaVersion": "pxos-ops/1.0", "meta": {"profile": "default", "cols": 16}, "program": program}

    async def test_pathway(self, start_pane_id: str, pathway: List[str], seed_hlir: Dict) -> Tuple[bool, Dict]:
        # 1. Load seed HLIR into the starting pane
        if start_pane_id == 'P1': self.test_panes['P1'].content = hlir_to_python(seed_hlir)
        elif start_pane_id in ['P2', 'P3']: self.test_panes[start_pane_id].content = T_hlir_to_analog(seed_hlir)
        elif start_pane_id == 'P5': self.test_panes['P5'].content = json.dumps(seed_hlir, indent=2)

        # 2. Propagate through the pathway
        current_pane_id = start_pane_id
        for next_pane_id in pathway:
            self.engine.on_edit(current_pane_id)
            await asyncio.sleep(0.05) # allow debounce
            current_pane_id = next_pane_id

        # 3. Extract final HLIR
        final_pane = self.test_panes[current_pane_id]
        final_hlir = {}
        if current_pane_id == 'P1': final_hlir = T_py_to_hlir(final_pane.content)
        elif current_pane_id in ['P2', 'P3']: final_hlir = T_analog_to_hlir(final_pane.content)
        elif current_pane_id == 'P5': final_hlir = json.loads(final_pane.content)

        # 4. Compare
        return final_hlir == seed_hlir, final_hlir

    def inscribe_failure(self, failure: LineageFailure):
        scroll_path = self.hall_of_drift / f"drift_{failure.error_hash}.scroll"
        with open(scroll_path, "w") as f: f.write(failure.to_scroll())
        print(f"⚠️ Lineage drift inscribed: {scroll_path}")

    async def guardian_ritual(self, iterations: int = 50, verbose: bool = True):
        # ... (user's sketch)
        pass

async def invoke_sentinel(engine: PXOSEngine, iterations: int = 100):
    sentinel = PXOSLineageSentinel(engine)
    return await sentinel.guardian_ritual(iterations=iterations)

if __name__ == "__main__":
    tr = Transforms()
    tr.T_py_to_hlir = T_py_to_hlir
    tr.T_analog_to_hlir = T_analog_to_hlir
    tr.T_hlir_to_analog = T_hlir_to_analog
    tr.validate_hlir = validate_hlir
    tr.lower_hlir_to_llir = lambda h: [("mock_llir", 0)]
    tr.encode_tiles = lambda llir, ecc: [("mock_tile", 0)]
    tr.ecc_stats = lambda tiles: {"ok": len(tiles)}

    engine = PXOSEngine(tr, Profile())

    asyncio.run(invoke_sentinel(engine, iterations=10))
