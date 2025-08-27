# PXOS 6-Pane Workbench: Sync Contract

## Single-Page Synchronization Contract

| **Truth Origin** | **Parse → HLIR** | **Validate** | **Fan-out (text)** | **Common Pipeline** | **Error Surface** | **Echo Guard** |
|------------------|------------------|--------------|---------------------|-------------------|-------------------|----------------|
| **P1 (Python)** | `T_py_to_hlir(code)` | `validate_hlir(hlir)` | P5 = pretty(HLIR), P2/P3 = `T_hlir_to_analog(hlir)` | HLIR → `lower_hlir_to_llir` → `encode_tiles(ecc)` → P4.render, P6.replay | Annotate **P1** with exception; keep last-good P4/P6 | Do **not** write back to P1 for same `build_id` |
| **P2 (Analog Mirror)** | `T_analog_to_hlir(text)` | `validate_hlir(hlir)` | P5 = pretty(HLIR), P3 = `T_hlir_to_analog`, (optionally P1 if reverse supported) | same | Annotate **P2** | Don't write P2 for same build |
| **P3 (Analog Editor)** | `T_analog_to_hlir(text)` | `validate_hlir(hlir)` | P5 = pretty(HLIR), P2 = `T_hlir_to_analog`, (optionally P1) | same | Annotate **P3** | Don't write P3 for same build |
| **P5 (HLIR JSON)** | `parse_hlir_text(text)` | `validate_hlir(hlir)` | P2/P3 = `T_hlir_to_analog` | same | Annotate **P5** | Don't write P5 for same build |

## Global Rules

* **Single Truth**: Every write carries `{build_id, origin}`. Only one pane is truth per build.
* **Pinned Panes**: Pinned panes (📌) are skipped from auto-updates.
* **Validation Gates**: If validation fails: stop propagation; leave P4/P6 showing **last good** build; log to P6.
* **Caches**: `H_py`, `H_analog_p2`, `H_analog_p3`, `H_hlir`, `llir` short-circuit recompute.
* **Normalization**: Apply minimal splice to avoid caret jumps when possible.
* **Debouncing**: 200ms debounce prevents UI lag from rapid edits.

## Implementation Architecture

### Enhanced Cache Structure
```python
@dataclass
class Cache:
    H_py: Optional[str] = None
    H_analog_p2: Optional[str] = None  # Separate cache for P2
    H_analog_p3: Optional[str] = None  # Separate cache for P3  
    H_hlir: Optional[str] = None
    llir: Any = None  # Store actual LLIR object
    last_good_hlir: Optional[Dict[str, Any]] = None
    last_good_build: Optional[int] = None
```

### Echo Guard Pattern
```python
class TextPaneAdapter:
    def __init__(self, pane_id, get_fn, set_fn, annotate_fn, clear_fn):
        self.id = pane_id
        self._last_build_id = -1  # Echo guard
    
    def write(self, text: str, *, origin, build_id) -> None:
        if build_id == self._last_build_id and origin == self.id:
            return  # Self-echo guard
        self._last_build_id = build_id
        self._set(text, origin, build_id)
```

### Splice-Aware Updates
```python
def _write_normalized(self, pane: Pane, new_text: str, *, origin: PaneId, build_id: int):
    if pane.pinned: 
        raise PinnedError()
    old = pane.read()
    if new_text == old: 
        return
    i0, i1, _, _, ins = minimal_edit(old, new_text)
    if hasattr(pane, "splice"):
        pane.splice(i0, i1, ins, origin=origin, build_id=build_id)
    else:
        pane.write(new_text, origin=origin, build_id=build_id)
```

### Error Handling Strategy
```python
try:
    await self._run_common_pipeline(hlir, origin=pane_id, build_id=build)
    self.cache.last_good_hlir = hlir
    self.cache.last_good_build = build
except Exception as e:
    if "P6" in self.panes and isinstance(self.panes["P6"], ReplayPane):
        self.panes["P6"].log(f"[build {build}] pipeline error: {e}")
    # Do not clobber P4/P6 (they still show last good)
```

## Validation Points

1. **Python AST**: P1 syntax validation
2. **Analog DSL**: P2/P3 grammar parsing  
3. **JSON Schema**: P5 pxos-ops/1.0 compliance
4. **ECC**: P4 tile integrity
5. **Semantic**: All panes range/type checking

## Performance Features

- **Incremental Hash Caching**: Avoid redundant transforms
- **Async Debouncing**: Coalesce rapid edits (200ms)
- **Minimal Diffs**: Preserve cursor position with splice operations
- **ECC Hot-Swap**: Detect profile changes and re-encode only when needed

## Testing Invariants

The included pytest harness validates these critical behaviors:

1. **Echo Guards**: Panes never update themselves
2. **Validation Halts**: Invalid content stops propagation
3. **Pinning Works**: Pinned panes skip auto-updates  
4. **Debouncing**: Rapid edits are coalesced
5. **Separate Caches**: P2 and P3 have independent analog caches
6. **Build Tracking**: Truth origin and build IDs are properly managed

## Usage Example

```python
# Initialize engine
transforms = create_transforms()  # Your transform functions
engine = PXOSEngine(transforms, Profile(ecc="hamming16_12"))

# Register pane adapters
engine.register(TextPaneAdapter("P1", get_fn, set_fn, annotate_fn, clear_fn))
engine.register(TilesPaneAdapter("P4"))
engine.register(ReplayPaneAdapter("P6"))

# Handle edit events
def on_text_edit(pane_id):
    engine.on_edit(pane_id)  # Debounced, async processing

# Check status
build_info = engine.get_build_info()
print(f"Build {build_info['build_id']}, Truth: {build_info['truth_origin']}")
```

This contract ensures **bulletproof data flow** with deterministic behavior, no echo loops, and robust error handling for production use.