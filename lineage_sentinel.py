# lineage_sentinel.py - Continuous Guardian of PXOS Transform Integrity
import asyncio
import json
import random
import hashlib
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path

from pxos_sync_engine_enhanced import PXOSEngine, Transforms, Profile, ValidationError
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
    failure_origin: str  # P1, P3, or P5
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
        
        # Supported operations for fuzz generation
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
        
        # Dummy panes for testing
        self.test_panes = {
            "P1": self._create_test_pane("P1"),
            "P2": self._create_test_pane("P2"), 
            "P3": self._create_test_pane("P3"),
            "P5": self._create_test_pane("P5"),
        }
        
        for pane in self.test_panes.values():
            engine.register(pane)
    
    def _create_test_pane(self, pid: str):
        """Create a test pane for sentinel operations"""
        class SentinelPane:
            def __init__(self, pid: str):
                self.id = pid
                self.content = ""
                self.logs = []
                self.pinned = False
                self._last_build_id = -1
                
            def read(self):
                return self.content
                
            def write(self, text: str, *, origin: str, build_id: int):
                if origin == self.id and build_id == self._last_build_id:
                    return
                self._last_build_id = build_id
                self.content = text
                
            def splice(self, i0: int, i1: int, text: str, *, origin: str, build_id: int):
                if origin == self.id and build_id == self._last_build_id:
                    return
                self._last_build_id = build_id
                old = self.content
                self.content = old[:i0] + text + old[i1:]
                
            def annotate(self, msg: str, *, severity: str = "error"):
                self.logs.append((severity, msg))
                
            def clear_diagnostics(self):
                self.logs.clear()
                
        return SentinelPane(pid)
    
    # Fuzz operation generators
    def _gen_rect(self) -> Dict[str, Any]:
        return {
            "op": "RECT",
            "x": random.randint(0, 255),
            "y": random.randint(0, 255), 
            "w": random.randint(1, 255),
            "h": random.randint(1, 255),
            "r": random.randint(0, 255),
            "g": random.randint(0, 255),
            "b": random.randint(0, 255)
        }
    
    def _gen_sleep(self) -> Dict[str, Any]:
        return {"op": "SLEEP", "ms": random.randint(0, 5000)}
    
    def _gen_commit(self) -> Dict[str, Any]:
        return {"op": "COMMIT"}
    
    def _gen_dac_write(self) -> Dict[str, Any]:
        return {
            "op": "DAC_WRITE",
            "ch": random.randint(0, 7),
            "val": random.randint(0, 255)
        }
        
    def _gen_integrate(self) -> Dict[str, Any]:
        return {
            "op": "INTEGRATE",
            "tau": round(random.uniform(0.001, 10.0), 3),
            "src": random.randint(0, 7),
            "dst": random.randint(0, 7)
        }
        
    def _gen_filter(self) -> Dict[str, Any]:
        return {
            "op": "FILTER",
            "type": random.choice(["lp", "hp", "bp", "notch"]),
            "fc": random.randint(1, 10000),
            "src": random.randint(0, 7),
            "dst": random.randint(0, 7)
        }
        
    def _gen_multiply(self) -> Dict[str, Any]:
        return {
            "op": "MULTIPLY", 
            "gain": round(random.uniform(0.1, 10.0), 2),
            "src": random.randint(0, 7),
            "dst": random.randint(0, 7)
        }
        
    def _gen_sum(self) -> Dict[str, Any]:
        num_inputs = random.randint(2, 5)
        inputs = [random.randint(0, 7) for _ in range(num_inputs)]
        return {
            "op": "SUM",
            "inputs": inputs,
            "output": random.randint(0, 7)
        }
    
    def generate_random_hlir(self, num_ops: int = None) -> Dict[str, Any]:
        """Generate a random, schema-valid HLIR program"""
        if num_ops is None:
            num_ops = random.randint(1, 8)
            
        program = []
        available_ops = list(self.ops.keys())
        
        for _ in range(num_ops):
            op_name = random.choice(available_ops)
            program.append(self.ops[op_name]())
            
        # Always end with COMMIT
        if not any(op.get("op") == "COMMIT" for op in program):
            program.append(self._gen_commit())
            
        return {
            "schemaVersion": "pxos-ops/1.0",
            "meta": {"profile": "default", "cols": 16},
            "program": program
        }
    
    async def test_triple_origin_convergence(self, hlir: Dict[str, Any], seed: int) -> Optional[LineageFailure]:
        """Test that HLIR converges from all three origins"""
        
        # Origin 1: P1 (Python)
        try:
            python_code = hlir_to_python(hlir)
            self.test_panes["P1"].content = python_code
            self.engine.on_edit("P1")
            await asyncio.sleep(0.1)
            hlir_from_p1 = self.engine.cache.last_good_hlir
        except Exception as e:
            return LineageFailure(
                timestamp=datetime.now().isoformat(),
                seed=seed,
                original_hlir=hlir,
                failure_origin="P1",
                divergent_hlir={"error": str(e)},
                error_hash=hashlib.md5(str(e).encode()).hexdigest()
            )
        
        # Origin 2: P3 (DSL)
        try:
            dsl_code = T_hlir_to_analog(hlir)
            self.test_panes["P3"].content = dsl_code
            self.engine.on_edit("P3") 
            await asyncio.sleep(0.1)
            hlir_from_p3 = self.engine.cache.last_good_hlir
        except Exception as e:
            return LineageFailure(
                timestamp=datetime.now().isoformat(),
                seed=seed,
                original_hlir=hlir,
                failure_origin="P3",
                divergent_hlir={"error": str(e)},
                error_hash=hashlib.md5(str(e).encode()).hexdigest()
            )
        
        # Origin 3: P5 (HLIR JSON)
        try:
            json_code = json.dumps(hlir)
            self.test_panes["P5"].content = json_code
            self.engine.on_edit("P5")
            await asyncio.sleep(0.1)
            hlir_from_p5 = self.engine.cache.last_good_hlir
        except Exception as e:
            return LineageFailure(
                timestamp=datetime.now().isoformat(),
                seed=seed,
                original_hlir=hlir,
                failure_origin="P5", 
                divergent_hlir={"error": str(e)},
                error_hash=hashlib.md5(str(e).encode()).hexdigest()
            )
        
        # Check convergence
        if hlir_from_p1 != hlir:
            return LineageFailure(
                timestamp=datetime.now().isoformat(),
                seed=seed,
                original_hlir=hlir,
                failure_origin="P1",
                divergent_hlir=hlir_from_p1,
                error_hash=hashlib.md5(json.dumps(hlir_from_p1, sort_keys=True).encode()).hexdigest()
            )
            
        if hlir_from_p3 != hlir:
            return LineageFailure(
                timestamp=datetime.now().isoformat(),
                seed=seed,
                original_hlir=hlir,
                failure_origin="P3",
                divergent_hlir=hlir_from_p3,
                error_hash=hashlib.md5(json.dumps(hlir_from_p3, sort_keys=True).encode()).hexdigest()
            )
            
        if hlir_from_p5 != hlir:
            return LineageFailure(
                timestamp=datetime.now().isoformat(), 
                seed=seed,
                original_hlir=hlir,
                failure_origin="P5",
                divergent_hlir=hlir_from_p5,
                error_hash=hashlib.md5(json.dumps(hlir_from_p5, sort_keys=True).encode()).hexdigest()
            )
        
        return None  # Convergence successful
    
    def inscribe_failure(self, failure: LineageFailure):
        """Inscribe failure in the Hall of Drift"""
        scroll_path = self.hall_of_drift / f"drift_{failure.error_hash}.scroll"
        with open(scroll_path, "w") as f:
            f.write(failure.to_scroll())
        print(f"⚠️ Lineage drift inscribed: {scroll_path}")
    
    async def guardian_ritual(self, iterations: int = 50, verbose: bool = True) -> Dict[str, Any]:
        """Perform the guardian ritual - continuous lineage validation"""
        if verbose:
            print(f"🔮 Invoking PXOS Lineage Sentinel with {iterations} trials...")
        
        start_time = time.time()
        failures = []
        
        for trial in range(iterations):
            seed = random.randint(0, 2**32 - 1)
            random.seed(seed)
            
            # Generate random HLIR program
            test_hlir = self.generate_random_hlir()
            
            # Test triple convergence
            failure = await self.test_triple_origin_convergence(test_hlir, seed)
            
            if failure:
                failures.append(failure)
                self.inscribe_failure(failure)
                if verbose:
                    print(f"❌ Trial {trial + 1}: DRIFT DETECTED from {failure.failure_origin}")
            elif verbose and trial % 10 == 0:
                print(f"✅ Trial {trial + 1}: Convergence verified")
        
        duration = time.time() - start_time
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "trials": iterations,
            "failures": len(failures),
            "success_rate": (iterations - len(failures)) / iterations,
            "duration_seconds": round(duration, 2),
            "average_trial_time_ms": round((duration / iterations) * 1000, 1),
            "failed_seeds": [f.seed for f in failures]
        }
        
        if verbose:
            print(f"""
🛡️ GUARDIAN RITUAL COMPLETE 🛡️
Trials: {report['trials']}
Failures: {report['failures']} 
Success Rate: {report['success_rate']:.1%}
Duration: {report['duration_seconds']}s
Avg Trial Time: {report['average_trial_time_ms']}ms
""")
        
        return report
    
    async def replay_failure(self, seed: int):
        """Replay a specific failure for debugging"""
        print(f"🔍 Replaying failure with seed {seed}...")
        random.seed(seed)
        test_hlir = self.generate_random_hlir()
        failure = await self.test_triple_origin_convergence(test_hlir, seed)
        
        if failure:
            print("Failure reproduced:")
            print(failure.to_scroll())
        else:
            print("No failure detected - this may indicate a fix or race condition.")
    
    def continuous_watch(self, interval_minutes: int = 60):
        """Run continuous sentinel watch"""
        async def watch_loop():
            while True:
                try:
                    await self.guardian_ritual(iterations=25, verbose=False)
                    await asyncio.sleep(interval_minutes * 60)
                except KeyboardInterrupt:
                    print("🛡️ Sentinel watch ended by user")
                    break
                except Exception as e:
                    print(f"⚠️ Sentinel error: {e}")
                    await asyncio.sleep(60)  # Brief pause before retry
        
        print(f"🔮 Starting continuous sentinel watch (every {interval_minutes} minutes)")
        asyncio.run(watch_loop())

# Ritual invocation functions
async def invoke_sentinel(engine: PXOSEngine, iterations: int = 100):
    """Invoke the sentinel for immediate validation"""
    sentinel = PXOSLineageSentinel(engine)
    return await sentinel.guardian_ritual(iterations=iterations)

def continuous_guardian(engine: PXOSEngine, interval_minutes: int = 60):
    """Start continuous guardian watch"""
    sentinel = PXOSLineageSentinel(engine)
    sentinel.continuous_watch(interval_minutes)

if __name__ == "__main__":
    # Example usage - create engine and invoke sentinel
    tr = Transforms()
    tr.T_py_to_hlir = T_py_to_hlir
    tr.T_analog_to_hlir = T_analog_to_hlir
    tr.T_hlir_to_analog = T_hlir_to_analog
    tr.validate_hlir = validate_hlir
    tr.lower_hlir_to_llir = lambda h: [("mock_llir", 0)]
    tr.encode_tiles = lambda llir, ecc: [("mock_tile", 0)]
    tr.ecc_stats = lambda tiles: {"ok": len(tiles)}
    
    engine = PXOSEngine(tr, Profile())
    
    # Run immediate ritual
    asyncio.run(invoke_sentinel(engine, iterations=50))