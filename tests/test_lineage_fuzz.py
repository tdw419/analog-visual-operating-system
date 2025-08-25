import asyncio
import json
import random
import pytest
from hypothesis import given, settings, strategies as st, HealthCheck

from lineage_sentinel import PXOSLineageSentinel
from pxos_sync_engine import PXOSEngine, Transforms, Profile
from transpiler import T_py_to_hlir
from pxos_dsl import T_analog_to_hlir, T_hlir_to_analog
from validate_hlir import validate_hlir
from hlir_to_py import hlir_to_python

# --- Hypothesis strategies for generating valid HLIR ---
op_strategies = [
    st.fixed_dictionaries({"op": st.just("RECT"), "x": st.integers(0,255), "y": st.integers(0,255), "w": st.integers(1,255), "h": st.integers(1,255), "r": st.integers(0,255), "g": st.integers(0,255), "b": st.integers(0,255)}),
    st.fixed_dictionaries({"op": st.just("SLEEP"), "ms": st.integers(0, 1000)}),
    st.fixed_dictionaries({"op": st.just("COMMIT")}),
    st.fixed_dictionaries({"op": st.just("DAC_WRITE"), "ch": st.integers(0,7), "val": st.integers(0,255)}),
    st.fixed_dictionaries({"op": st.just("INTEGRATE"), "tau": st.floats(0.001, 10.0), "src": st.integers(0,7), "dst": st.integers(0,7)}),
    st.fixed_dictionaries({"op": st.just("FILTER"), "type": st.sampled_from(["lp", "hp", "bp"]), "fc": st.integers(1, 20000), "src": st.integers(0,7), "dst": st.integers(0,7)}),
    st.fixed_dictionaries({"op": st.just("MULTIPLY"), "gain": st.floats(-10.0, 10.0), "src": st.integers(0,7), "dst": st.integers(0,7)}),
    st.fixed_dictionaries({"op": st.just("SUM"), "inputs": st.lists(st.integers(0,7), min_size=1, max_size=4), "output": st.integers(0,7)})
]

program_strategy = st.lists(st.one_of(op_strategies), min_size=1, max_size=5).map(
    lambda ops: ops + [{"op": "COMMIT"}] if not any(o['op'] == 'COMMIT' for o in ops) else ops
)

hlir_strategy = st.builds(
    dict,
    schemaVersion=st.just("pxos-ops/1.0"),
    meta=st.builds(dict, profile=st.just("default"), cols=st.just(16)),
    program=program_strategy
)

@pytest.mark.asyncio
@settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(hlir=hlir_strategy)
async def test_fuzzed_convergence(hlir):
    """
    Tests that a randomly generated, schema-valid HLIR program
    converges to the same state regardless of the editing origin.
    """
    tr = Transforms()
    tr.T_py_to_hlir = T_py_to_hlir
    tr.T_analog_to_hlir = T_analog_to_hlir
    tr.T_hlir_to_analog = T_hlir_to_analog
    tr.validate_hlir = validate_hlir
    tr.lower_hlir_to_llir = lambda h: [("mock_llir", 0)]
    tr.encode_tiles = lambda llir, ecc: [("mock_tile", 0)]
    tr.ecc_stats = lambda tiles: {"ok": len(tiles)}
    engine = PXOSEngine(tr, Profile())
    sentinel = PXOSLineageSentinel(engine)
    seed = random.randint(0, 2**32 - 1)

    # Test P1 -> P3 -> P5 pathway
    p1_to_p5_pathway = ['P3', 'P5']
    converged, final_hlir = await sentinel.test_pathway('P1', p1_to_p5_pathway, hlir)
    if not converged:
        failure = sentinel.inscribe_failure(LineageFailure(datetime.now().isoformat(), seed, hlir, 'P1', final_hlir, 'hash'))
        assert converged, f"P1->P3->P5 pathway failed for seed {seed}. See hall_of_drift."

    # Test P3 -> P1 -> P5 pathway
    p3_to_p5_pathway = ['P1', 'P5']
    converged, final_hlir = await sentinel.test_pathway('P3', p3_to_p5_pathway, hlir)
    if not converged:
        failure = sentinel.inscribe_failure(LineageFailure(datetime.now().isoformat(), seed, hlir, 'P3', final_hlir, 'hash'))
        assert converged, f"P3->P1->P5 pathway failed for seed {seed}. See hall_of_drift."
