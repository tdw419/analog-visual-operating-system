#!/usr/bin/env python3
"""
Enhanced PXOS Sync Engine - Core round-trip translator with bulletproof data flow
Implements single-truth model, echo guards, validation gates, and splice operations
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Callable, Optional, Tuple, Literal, Protocol, List
import asyncio
import time
import hashlib
import difflib
import json
import logging

# Type definitions
PaneId = Literal["P1", "P2", "P3", "P4", "P5", "P6"]
EditableId = Literal["P1", "P2", "P3", "P5"]

class ValidationError(Exception):
    """Raised when validation fails"""
    pass

class PinnedError(Exception):
    """Raised when attempting to write to a pinned pane"""
    pass

# Enhanced Cache with separate P2/P3 tracking
@dataclass
class Cache:
    """Cache with separate hashes for P2 vs P3 analog content"""
    H_py: Optional[str] = None
    H_analog_p2: Optional[str] = None  # Separate cache for P2
    H_analog_p3: Optional[str] = None  # Separate cache for P3
    H_hlir: Optional[str] = None
    llir: Any = None  # Store actual LLIR object (was H_llir)
    last_good_hlir: Optional[Dict[str, Any]] = None
    last_good_build: Optional[int] = None

@dataclass
class Profile:
    """ECC and encoding profile configuration"""
    ecc: Literal["parity", "hamming16_12"] = "hamming16_12"
    mode: Literal["absolute", "delta"] = "absolute"
    dac_range: Tuple[float, float] = (0.0, 5.0)
    max_channels: int = 8

@dataclass
class Bus:
    """Event bus state tracking"""
    build_id: int = 0
    truth_origin: Optional[EditableId] = None

# Protocol definitions for pane adapters
class Pane(Protocol):
    """Base pane interface with echo guard"""
    id: PaneId
    pinned: bool
    
    def read(self) -> str: ...
    def write(self, text: str, *, origin: PaneId, build_id: int) -> None: ...
    def annotate(self, message: str, *, severity: Literal["info", "warn", "error"] = "error") -> None: ...
    def clear_diagnostics(self) -> None: ...

class TextPaneAdapter(Pane):
    """Enhanced text pane adapter with splice support and echo guard"""
    
    def __init__(self, pane_id: PaneId, get_fn, set_fn, annotate_fn, clear_fn, splice_fn=None):
        self.id = pane_id
        self._get, self._set = get_fn, set_fn
        self._annot, self._clear = annotate_fn, clear_fn
        self._splice = splice_fn
        self.pinned = False
        self._last_build_id = -1  # Echo guard
    
    def read(self) -> str:
        return self._get()
    
    def write(self, text: str, *, origin: PaneId, build_id: int) -> None:
        if build_id == self._last_build_id and origin == self.id:
            return  # Self-echo guard
        self._last_build_id = build_id
        self._set(text, origin, build_id)
    
    def splice(self, i0: int, i1: int, insert_text: str, *, origin: PaneId, build_id: int) -> None:
        """Optional splice operation for minimal edits"""
        if build_id == self._last_build_id and origin == self.id:
            return  # Self-echo guard
        self._last_build_id = build_id
        if self._splice:
            self._splice(i0, i1, insert_text, origin, build_id)
        else:
            # Fallback to full write
            old_text = self.read()
            new_text = old_text[:i0] + insert_text + old_text[i1:]
            self._set(new_text, origin, build_id)
    
    def annotate(self, message: str, *, severity: Literal["info", "warn", "error"] = "error") -> None:
        self._annot(message, severity)
    
    def clear_diagnostics(self) -> None:
        self._clear()

class TilesPane(Pane, Protocol):
    """Tiles pane with echo guard for tile rendering"""
    def render_tiles(self, tiles: Any, ecc_report: Dict[str, int], *, origin: PaneId, build_id: int) -> None: ...

class ReplayPane(Pane, Protocol):
    """Replay pane with echo guard and logging"""
    def replay_from_hlir(self, hlir: Dict[str, Any], *, origin: PaneId, build_id: int) -> None: ...
    def log(self, line: str) -> None: ...

class Transforms:
    """Transform function registry"""
    T_py_to_hlir: Callable[[str], Dict[str, Any]]
    T_analog_to_hlir: Callable[[str], Dict[str, Any]]
    T_hlir_to_analog: Callable[[Dict[str, Any]], str]
    validate_hlir: Callable[[Dict[str, Any]], None]
    lower_hlir_to_llir: Callable[[Dict[str, Any]], Any]
    encode_tiles: Callable[[Any, str], Any]
    ecc_stats: Callable[[Any], Dict[str, int]]

# Utility functions
def _h(blob: Any) -> str:
    """Generate hash for caching"""
    if isinstance(blob, (dict, list)):
        b = json.dumps(blob, sort_keys=True, separators=(",", ":")).encode("utf-8")
    elif isinstance(blob, str):
        b = blob.encode("utf-8")
    else:
        b = repr(blob).encode("utf-8")
    return hashlib.sha256(b).hexdigest()

def minimal_edit(old: str, new: str) -> Tuple[int, int, int, int, str]:
    """Compute minimal edit for splice operations"""
    sm = difflib.SequenceMatcher(a=old, b=new)
    ops = [op for op in sm.get_opcodes() if op[0] != "equal"]
    if not ops:
        return (0, len(old), 0, len(new), new)
    i0 = min(o[1] for o in ops)
    i1 = max(o[2] for o in ops)
    j0 = min(o[3] for o in ops)
    j1 = max(o[4] for o in ops)
    return (i0, i1, j0, j1, new[j0:j1])

class Debouncer:
    """Async debouncer with cancellation safety"""
    
    def __init__(self, ms: int, loop: asyncio.AbstractEventLoop):
        self._delay = ms / 1000.0
        self._loop = loop
        self._task: Optional[asyncio.Task] = None
        self._last_args = None
    
    def call(self, coro_fn: Callable, *args, **kwargs):
        """Debounce a coroutine call"""
        self._last_args = (coro_fn, args, kwargs)
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = self._loop.create_task(self._run())
    
    async def _run(self):
        """Execute debounced call with cancellation safety"""
        try:
            snap = self._last_args
            await asyncio.sleep(self._delay)
            if self._last_args is not snap:
                return  # Arguments changed during wait
            fn, args, kwargs = snap
            await fn(*args, **kwargs)
        except asyncio.CancelledError:
            return

class PXOSEngine:
    """Enhanced PXOS synchronization engine with bulletproof data flow"""
    
    def __init__(self, transforms: Transforms, profile: Profile = Profile(), 
                 loop: Optional[asyncio.AbstractEventLoop] = None):
        self.tr = transforms
        self.profile = profile
        self.loop = loop or asyncio.get_event_loop()
        
        self.bus = Bus()
        self.cache = Cache()
        self.panes: Dict[PaneId, Pane] = {}
        
        # ECC profile hot-swap tracking
        self._last_ecc_key = None
        
        # Debouncer per editable pane
        self._debouncers: Dict[EditableId, Debouncer] = {
            "P1": Debouncer(200, self.loop),
            "P2": Debouncer(200, self.loop),
            "P3": Debouncer(200, self.loop),
            "P5": Debouncer(200, self.loop),
        }
    
    def register(self, pane: Pane) -> None:
        """Register a pane with the engine"""
        self.panes[pane.id] = pane
    
    def on_edit(self, pane_id: EditableId) -> None:
        """Handle edit event with debouncing"""
        self._debouncers[pane_id].call(self._handle_edit, pane_id)
    
    async def _handle_edit(self, pane_id: EditableId):
        """Core edit handling with validation and propagation"""
        self.bus.build_id += 1
        self.bus.truth_origin = pane_id
        build = self.bus.build_id
        
        try:
            # Parse input to HLIR based on origin
            hlir = await self._parse_to_hlir(pane_id, build)
            
            # Validate HLIR
            self.tr.validate_hlir(hlir)
            
            # Sync other source panes
            await self._sync_sources_from_hlir(hlir, origin=pane_id, build_id=build)
            
            # Run common pipeline
            await self._run_common_pipeline(hlir, origin=pane_id, build_id=build)
            
            # Update cache
            self.cache.last_good_hlir = hlir
            self.cache.last_good_build = build
            
            # Clear diagnostics on success
            for pid in ["P1", "P2", "P3", "P5"]:
                if pid in self.panes:
                    self.panes[pid].clear_diagnostics()
                    
        except ValidationError as e:
            self.panes[pane_id].annotate(str(e), severity="error")
            if "P6" in self.panes and isinstance(self.panes["P6"], ReplayPane):
                self.panes["P6"].log(f"[build {build}] Validation failed in {pane_id}: {e}")
        except Exception as e:
            logging.error(f"Unexpected error in build {build}: {e}")
            self.panes[pane_id].annotate(f"Internal error: {e}", severity="error")
    
    async def _parse_to_hlir(self, pane_id: EditableId, build: int) -> Dict[str, Any]:
        """Parse pane content to HLIR with caching"""
        if pane_id == "P1":
            text = self.panes["P1"].read()
            H = _h(text)
            if self.cache.H_py == H and self.cache.last_good_hlir:
                return self.cache.last_good_hlir
            else:
                hlir = self.tr.T_py_to_hlir(text)
                self.cache.H_py = H
                return hlir
                
        elif pane_id == "P2":
            text = self.panes["P2"].read()
            H = _h(text)
            if self.cache.H_analog_p2 == H and self.cache.last_good_hlir:
                return self.cache.last_good_hlir
            else:
                hlir = self.tr.T_analog_to_hlir(text)
                self.cache.H_analog_p2 = H
                return hlir
                
        elif pane_id == "P3":
            text = self.panes["P3"].read()
            H = _h(text)
            if self.cache.H_analog_p3 == H and self.cache.last_good_hlir:
                return self.cache.last_good_hlir
            else:
                hlir = self.tr.T_analog_to_hlir(text)
                self.cache.H_analog_p3 = H
                return hlir
                
        elif pane_id == "P5":
            hlir_text = self.panes["P5"].read()
            return self._parse_hlir_text(hlir_text)
        else:
            raise RuntimeError(f"Unknown origin pane: {pane_id}")
    
    async def _sync_sources_from_hlir(self, hlir: Dict[str, Any], *, origin: EditableId, build_id: int):
        """Sync text panes from HLIR with echo guards"""
        targets: List[Tuple[PaneId, Callable[[Dict[str, Any]], str]]] = [
            ("P5", self._pretty_hlir_text),
            ("P2", self.tr.T_hlir_to_analog),
            ("P3", self.tr.T_hlir_to_analog),
        ]
        
        for pid, fmt in targets:
            if pid == origin:
                continue  # Don't update origin
            if pid not in self.panes:
                continue
                
            pane = self.panes[pid]
            if pane.pinned:
                continue
                
            new_text = fmt(hlir)
            try:
                self._write_normalized(pane, new_text, origin=origin, build_id=build_id)
            except PinnedError:
                pass
    
    async def _run_common_pipeline(self, hlir: Dict[str, Any], *, origin: EditableId, build_id: int):
        """Run lowering and encoding pipeline with error handling"""
        try:
            H_hlir = _h(hlir)
            if self.cache.H_hlir == H_hlir and self.cache.llir:
                llir = self.cache.llir
            else:
                llir = self.tr.lower_hlir_to_llir(hlir)
                self.cache.H_hlir = H_hlir
                self.cache.llir = llir
            
            # ECC profile hot-swap detection
            ecc_key = (self.profile.ecc, _h(llir))
            if self._last_ecc_key != ecc_key:
                tiles = self.tr.encode_tiles(llir, self.profile.ecc)
                self._last_ecc_key = ecc_key
            else:
                tiles = self.tr.encode_tiles(llir, self.profile.ecc)
            
            stats = self.tr.ecc_stats(tiles)
            
            # Update visual panes
            if "P4" in self.panes and isinstance(self.panes["P4"], TilesPane):
                self.panes["P4"].render_tiles(tiles, stats, origin=origin, build_id=build_id)
            
            if "P6" in self.panes and isinstance(self.panes["P6"], ReplayPane):
                self.panes["P6"].replay_from_hlir(hlir, origin=origin, build_id=build_id)
                self.panes["P6"].log(f"[build {build_id}] tiles: ok={stats.get('ok',0)} corrected={stats.get('corrected',0)} bad={stats.get('bad',0)}")
                
        except Exception as e:
            if "P6" in self.panes and isinstance(self.panes["P6"], ReplayPane):
                self.panes["P6"].log(f"[build {build_id}] pipeline error: {e}")
            # Don't clobber P4/P6 - they still show last good state
            raise
    
    def _write_normalized(self, pane: Pane, new_text: str, *, origin: PaneId, build_id: int):
        """Write with minimal diff and echo guard"""
        if pane.pinned:
            raise PinnedError()
        
        old_text = pane.read()
        if new_text == old_text:
            return
        
        i0, i1, _, _, ins = minimal_edit(old_text, new_text)
        
        # Try splice if supported, otherwise fall back to full write
        if hasattr(pane, "splice"):
            pane.splice(i0, i1, ins, origin=origin, build_id=build_id)
        else:
            pane.write(new_text, origin=origin, build_id=build_id)
    
    def _pretty_hlir_text(self, hlir: Dict[str, Any]) -> str:
        """Format HLIR as pretty JSON"""
        return json.dumps(hlir, indent=2, sort_keys=True)
    
    def _parse_hlir_text(self, text: str) -> Dict[str, Any]:
        """Parse HLIR text as JSON"""
        try:
            return json.loads(text)
        except Exception as e:
            raise ValidationError(f"HLIR is not valid JSON: {e}") from e
    
    def get_build_info(self) -> Dict[str, Any]:
        """Get current build information"""
        return {
            'build_id': self.bus.build_id,
            'truth_origin': self.bus.truth_origin,
            'has_errors': any(hasattr(pane, '_last_error') for pane in self.panes.values()),
            'cache_stats': {
                'H_py': bool(self.cache.H_py),
                'H_analog_p2': bool(self.cache.H_analog_p2),
                'H_analog_p3': bool(self.cache.H_analog_p3),
                'H_hlir': bool(self.cache.H_hlir),
                'last_good_build': self.cache.last_good_build
            }
        }
    
    def force_rebuild(self):
        """Force complete rebuild by clearing caches"""
        self.cache = Cache()
        self._last_ecc_key = None
        if self.bus.truth_origin:
            self.on_edit(self.bus.truth_origin)
    
    def reset(self):
        """Reset engine state"""
        self.bus = Bus()
        self.cache = Cache()
        self._last_ecc_key = None
        for pane in self.panes.values():
            pane.clear_diagnostics()