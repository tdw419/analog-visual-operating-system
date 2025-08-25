from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Callable, Optional, Tuple, Literal, Protocol, runtime_checkable
import asyncio, time, hashlib, difflib

PaneId = Literal["P1", "P2", "P3", "P4", "P5", "P6"]
EditableId = Literal["P1", "P2", "P3", "P5"]

# ---------- Pane adapter contracts (UI-agnostic) ----------

@runtime_checkable
class Pane(Protocol):
    id: PaneId
    pinned: bool
    def read(self) -> str: ...
    def write(self, text: str, *, origin: PaneId, build_id: int) -> None: ...
    def annotate(self, message: str, *, severity: Literal["info","warn","error"]="error") -> None: ...
    def clear_diagnostics(self) -> None: ...

@runtime_checkable
class TilesPane(Pane, Protocol):
    def render_tiles(self, tiles: Any, ecc_report: Dict[str,int], *, origin: PaneId, build_id: int) -> None: ...

@runtime_checkable
class ReplayPane(Pane, Protocol):
    def replay_from_hlir(self, hlir: Dict[str, Any], *, origin: PaneId, build_id: int) -> None: ...
    def log(self, line: str) -> None: ...

# ---------- Hashing / caching helpers ----------

def _h(blob: Any) -> str:
    if isinstance(blob, (dict, list)):
        import json
        b = json.dumps(blob, sort_keys=True, separators=(",", ":")).encode("utf-8")
    elif isinstance(blob, str):
        b = blob.encode("utf-8")
    else:
        b = repr(blob).encode("utf-8")
    return hashlib.sha256(b).hexdigest()

# ---------- Normalization / minimal-diff writer ----------

def minimal_edit(old: str, new: str) -> Tuple[int,int,int,int, str]:
    """
    Return a single minimal splice (i0, i1, j0, j1, insert_text) that transforms old -> new.
    Good enough to preserve caret/selection; UI adapter can apply without jumping.
    """
    sm = difflib.SequenceMatcher(a=old, b=new)
    # collapse to one best op if possible; fallback to full replace
    ops = [op for op in sm.get_opcodes() if op[0] != "equal"]
    if not ops:
        return (0, len(old), 0, len(new), new)
    # If multiple, merge to a single encompassing span
    i0 = min(o[1] for o in ops); i1 = max(o[2] for o in ops)
    j0 = min(o[3] for o in ops); j1 = max(o[4] for o in ops)
    return (i0, i1, j0, j1, new[j0:j1])

# ---------- Transform function slots (plug your helpers here) ----------

class Transforms:
    T_py_to_hlir: Callable[[str], Dict[str,Any]]
    T_analog_to_hlir: Callable[[str], Dict[str,Any]]
    T_hlir_to_analog: Callable[[Dict[str,Any]], str]
    T_hlir_to_py: Callable[[Dict[str,Any]], str]
    validate_hlir: Callable[[Dict[str,Any]], None]  # raise ValidationError on failure
    lower_hlir_to_llir: Callable[[Dict[str,Any]], Any]
    encode_tiles: Callable[[Any, str], Any]  # (llir, ecc_mode) -> tiles
    ecc_stats: Callable[[Any], Dict[str,int]]

# ---------- Engine state ----------

@dataclass
class Profile:
    ecc: Literal["parity", "hamming16_12"] = "hamming16_12"

@dataclass
class Cache:
    H_py: Optional[str] = None
    H_analog_p2: Optional[str] = None
    H_analog_p3: Optional[str] = None
    H_hlir: Optional[str] = None
    llir: Any = None
    last_good_hlir: Optional[Dict[str, Any]] = None
    last_good_build: Optional[int] = None

@dataclass
class Bus:
    build_id: int = 0
    truth_origin: Optional[EditableId] = None

# ---------- Debouncer ----------

class Debouncer:
    def __init__(self, ms: int):
        self._delay = ms / 1000.0
        self._task: Optional[asyncio.Task] = None
        self._last_args = None
    def call(self, coro_fn: Callable, *args, **kwargs):
        self._last_args = (coro_fn, args, kwargs)
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = asyncio.create_task(self._run())
    async def _run(self):
        try:
            snap = self._last_args
            await asyncio.sleep(self._delay)
            if self._last_args is not snap:
                return
            fn, args, kwargs = snap
            await fn(*args, **kwargs)
        except asyncio.CancelledError:
            return

# ---------- Exceptions ----------

class ValidationError(Exception): ...
class PinnedError(Exception): ...

# ---------- The Engine ----------

class PXOSEngine:
    def __init__(self, transforms: Transforms, profile: Profile):
        self.tr = transforms
        self.profile = profile
        self.bus = Bus()
        self.cache = Cache()
        self.panes: Dict[PaneId, Pane] = {}
        self._debouncers = {pid: Debouncer(200) for pid in ("P1","P2","P3","P5")}
        self._last_ecc_key = None

    def register(self, pane: Pane) -> None:
        self.panes[pane.id] = pane

    def on_edit(self, pane_id: EditableId) -> None:
        self._debouncers[pane_id].call(self._handle_edit, pane_id)

    async def _handle_edit(self, pane_id: EditableId):
        self.bus.build_id += 1
        build = self.bus.build_id
        self.bus.truth_origin = pane_id
        try:
            # 1) parse → HLIR (with separate caches for P2 vs P3)
            if pane_id == "P1":
                text = self.panes["P1"].read()
                H = _h(text)
                if self.cache.H_py == H and self.cache.last_good_hlir:
                    hlir = self.cache.last_good_hlir
                else:
                    hlir = self.tr.T_py_to_hlir(text)
                    self.cache.H_py = H
            elif pane_id == "P2":
                text = self.panes["P2"].read()
                H = _h(text)
                if self.cache.H_analog_p2 == H and self.cache.last_good_hlir:
                    hlir = self.cache.last_good_hlir
                else:
                    hlir = self.tr.T_analog_to_hlir(text)
                    self.cache.H_analog_p2 = H
            elif pane_id == "P3":
                text = self.panes["P3"].read()
                H = _h(text)
                if self.cache.H_analog_p3 == H and self.cache.last_good_hlir:
                    hlir = self.cache.last_good_hlir
                else:
                    hlir = self.tr.T_analog_to_hlir(text)
                    self.cache.H_analog_p3 = H
            elif pane_id == "P5":
                hlir = self._parse_hlir_text(self.panes["P5"].read())
            else:
                raise RuntimeError(pane_id)

            # 2) validate
            self.tr.validate_hlir(hlir)

            # 3) fan-out text panes
            await self._sync_sources_from_hlir(hlir, origin=pane_id, build_id=build)

            # 4) common pipeline (guarded)
            try:
                await self._run_common_pipeline(hlir, origin=pane_id, build_id=build)
                self.cache.last_good_hlir = hlir
                self.cache.last_good_build = build
                # clear diagnostics everywhere symmetrical
                for pid in ("P1","P2","P3","P5"):
                    if pid in self.panes: self.panes[pid].clear_diagnostics()
            except Exception as e:
                if "P6" in self.panes and isinstance(self.panes["P6"], ReplayPane):
                    self.panes["P6"].log(f"[build {build}] pipeline error: {e}")
                # keep last good P4/P6 (do not clobber)

        except ValidationError as e:
            self.panes[pane_id].annotate(str(e), severity="error")
            if "P6" in self.panes and isinstance(self.panes["P6"], ReplayPane):
                self.panes["P6"].log(f"[build {build}] validation failed in {pane_id}: {e}")

    async def _sync_sources_from_hlir(self, hlir: Dict[str,Any], *, origin: PaneId, build_id: int):
        # The full round-trip: HLIR can be projected back to all editable source panes
        projections = {
            "P1": self.tr.T_hlir_to_py,
            "P2": self.tr.T_hlir_to_analog,
            "P3": self.tr.T_hlir_to_analog,
            "P5": self._pretty_hlir
        }
        for pid, to_text_fn in projections.items():
            if pid == origin or pid not in self.panes or self.panes[pid].pinned:
                continue
            new_text = to_text_fn(hlir)
            self._write_normalized(self.panes[pid], new_text, origin=origin, build_id=build_id)

    async def _run_common_pipeline(self, hlir: Dict[str,Any], *, origin: PaneId, build_id: int):
        Hh = _h(hlir)
        if self.cache.H_hlir != Hh or self.cache.llir is None:
            self.cache.llir = self.tr.lower_hlir_to_llir(hlir)
            self.cache.H_hlir = Hh

        llir = self.cache.llir
        ecc_key = (self.profile.ecc, _h(llir))
        if self._last_ecc_key != ecc_key:
            tiles = self.tr.encode_tiles(llir, self.profile.ecc)
            self._last_ecc_key = ecc_key
        else:
            # This logic is a bit off, if encode_tiles is expensive, we need to cache it
            tiles = self.tr.encode_tiles(llir, self.profile.ecc)

        stats = self.tr.ecc_stats(tiles)

        if "P4" in self.panes and isinstance(self.panes["P4"], TilesPane):
            self.panes["P4"].render_tiles(tiles, stats, origin=origin, build_id=build_id)
        if "P6" in self.panes and isinstance(self.panes["P6"], ReplayPane):
            self.panes["P6"].replay_from_hlir(hlir, origin=origin, build_id=build_id)
            self.panes["P6"].log(
                f"[build {build_id} from {origin}] tiles: ok={stats.get('ok',0)} "
                f"corrected={stats.get('corrected',0)} bad={stats.get('bad',0)}"
            )


    def _write_normalized(self, pane: Pane, new_text: str, *, origin: PaneId, build_id: int):
        if pane.pinned: raise PinnedError()
        old = pane.read()
        if new_text == old: return
        i0,i1,_,_,ins = minimal_edit(old, new_text)
        if hasattr(pane, "splice"):
            pane.splice(i0, i1, ins, origin=origin, build_id=build_id)
        else:
            pane.write(new_text, origin=origin, build_id=build_id)

    def _pretty_hlir(self, hlir: Dict[str,Any]) -> str:
        import json
        return json.dumps(hlir, indent=2, sort_keys=True)

    def _parse_hlir_text(self, text: str) -> Dict[str,Any]:
        import json
        try:
            return json.loads(text)
        except Exception as e:
            raise ValidationError(f"HLIR is not valid JSON: {e}") from e
