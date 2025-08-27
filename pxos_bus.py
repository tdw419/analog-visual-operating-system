# pxos_bus.py
"""
PXOS Event Bus - Central data flow orchestrator for the 6-pane workbench
Implements the bulletproof data flow architecture with validation/propagation rules

Key Features:
- Single source of truth with build_id tracking
- Deterministic transform chain per origin
- Validation layers with error isolation
- Conflict and cycle guards
- Incremental rebuilds with caching
"""

import hashlib
import time
import traceback
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass
from enum import Enum

class PaneType(Enum):
    """Pane identifiers for the 6-pane workbench"""
    P1_PYTHON = "P1_PYTHON"           # Python source (editable)
    P2_ANALOG_MIRROR = "P2_ANALOG_MIRROR"  # Analog text mirror (editable)
    P3_ANALOG_EDITOR = "P3_ANALOG_EDITOR"  # Analog source editor (editable)
    P4_TILES = "P4_TILES"             # Tile sheet (view-only)
    P5_HLIR = "P5_HLIR"               # HLIR CSV/JSON (editable)
    P6_REPLAY = "P6_REPLAY"           # Live replay (view-only)

@dataclass
class BuildEvent:
    """Event data for build updates"""
    build_id: int
    origin: PaneType
    timestamp: float
    content: str
    metadata: Dict[str, Any]

@dataclass
class ValidationResult:
    """Result of validation operation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    data: Any = None

class TransformCache:
    """Caching layer for expensive transforms"""
    
    def __init__(self):
        self.cache = {}
        self.hashes = {}
    
    def get_hash(self, content: str) -> str:
        """Generate content hash for caching"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def get(self, key: str, content: str) -> Optional[Any]:
        """Get cached result if content hasn't changed"""
        content_hash = self.get_hash(content)
        if key in self.cache and self.hashes.get(key) == content_hash:
            return self.cache[key]
        return None
    
    def set(self, key: str, content: str, result: Any):
        """Cache result with content hash"""
        content_hash = self.get_hash(content)
        self.cache[key] = result
        self.hashes[key] = content_hash
    
    def invalidate(self, key: str):
        """Invalidate cached result"""
        if key in self.cache:
            del self.cache[key]
        if key in self.hashes:
            del self.hashes[key]

class PXOSBus:
    """
    Central event bus for the 6-pane workbench
    Implements the data flow architecture with validation and conflict resolution
    """
    
    def __init__(self):
        self.build_id = 0
        self.truth_origin = None
        self.last_build_time = 0
        self.debounce_delay = 0.2  # 200ms debounce
        
        # State tracking
        self.current_content = {pane: "" for pane in PaneType}
        self.pinned_panes = set()  # Panes that won't auto-update
        self.validation_errors = {pane: [] for pane in PaneType}
        
        # Transform cache
        self.cache = TransformCache()
        
        # Registered handlers
        self.validators = {}
        self.transformers = {}
        self.update_handlers = {}
        
        # HLIR state (the canonical truth)
        self.hlir_data = None
        self.hlir_hash = None
        
    def register_validator(self, transform_name: str, validator: Callable[[str], ValidationResult]):
        """Register a validation function"""
        self.validators[transform_name] = validator
    
    def register_transformer(self, transform_name: str, transformer: Callable[[str], Any]):
        """Register a transform function"""
        self.transformers[transform_name] = transformer
    
    def register_update_handler(self, pane: PaneType, handler: Callable[[str, int, PaneType], None]):
        """Register a pane update handler"""
        self.update_handlers[pane] = handler
    
    def pin_pane(self, pane: PaneType, pinned: bool = True):
        """Pin/unpin a pane to prevent auto-updates"""
        if pinned:
            self.pinned_panes.add(pane)
        else:
            self.pinned_panes.discard(pane)
    
    def on_edit(self, pane: PaneType, content: str, metadata: Dict[str, Any] = None) -> bool:
        """
        Handle edit event from a pane
        Returns True if the edit was processed, False if debounced
        """
        current_time = time.time()
        
        # Debounce rapid edits
        if current_time - self.last_build_time < self.debounce_delay:
            return False
        
        self.last_build_time = current_time
        self.build_id += 1
        self.truth_origin = pane
        
        # Create build event
        event = BuildEvent(
            build_id=self.build_id,
            origin=pane,
            timestamp=current_time,
            content=content,
            metadata=metadata or {}
        )
        
        # Store current content
        self.current_content[pane] = content
        
        try:
            # Execute transform chain based on origin
            if pane == PaneType.P1_PYTHON:
                return self._handle_python_edit(event)
            elif pane == PaneType.P2_ANALOG_MIRROR:
                return self._handle_analog_mirror_edit(event)
            elif pane == PaneType.P3_ANALOG_EDITOR:
                return self._handle_analog_editor_edit(event)
            elif pane == PaneType.P5_HLIR:
                return self._handle_hlir_edit(event)
            else:
                return False
                
        except Exception as e:
            self._handle_error(pane, f"Transform error: {str(e)}", traceback.format_exc())
            return False
    
    def _handle_python_edit(self, event: BuildEvent) -> bool:
        """Handle edit from P1 (Python source)"""
        # T_py→hlir (trace or compile to HLIR JSON/CSV)
        hlir_result = self._transform_with_validation("T_py_to_hlir", event.content)
        if not hlir_result.is_valid:
            self._handle_error(PaneType.P1_PYTHON, "Python→HLIR failed", hlir_result.errors)
            return False
        
        # Update P5 (HLIR), then run Common Pipeline
        self._update_pane(PaneType.P5_HLIR, hlir_result.data, event.build_id, event.origin)
        return self._run_common_pipeline(hlir_result.data, event.build_id, event.origin)
    
    def _handle_analog_editor_edit(self, event: BuildEvent) -> bool:
        """Handle edit from P3 (Analog editor)"""
        # Parse & validate DSL → T_analog→hlir
        hlir_result = self._transform_with_validation("T_analog_to_hlir", event.content)
        if not hlir_result.is_valid:
            self._handle_error(PaneType.P3_ANALOG_EDITOR, "Analog→HLIR failed", hlir_result.errors)
            return False
        
        # Update P5 (HLIR), update P2 via T_hlir→analog (pretty-print/normalize)
        self._update_pane(PaneType.P5_HLIR, hlir_result.data, event.build_id, event.origin)
        
        # Update P2 (analog mirror)
        analog_result = self._transform_with_validation("T_hlir_to_analog", hlir_result.data)
        if analog_result.is_valid:
            self._update_pane(PaneType.P2_ANALOG_MIRROR, analog_result.data, event.build_id, event.origin)
        
        return self._run_common_pipeline(hlir_result.data, event.build_id, event.origin)
    
    def _handle_analog_mirror_edit(self, event: BuildEvent) -> bool:
        """Handle edit from P2 (Analog text mirror)"""
        # Parse (strict, normalized grammar) → T_analog→hlir
        hlir_result = self._transform_with_validation("T_analog_to_hlir", event.content)
        if not hlir_result.is_valid:
            self._handle_error(PaneType.P2_ANALOG_MIRROR, "Mirror→HLIR failed", hlir_result.errors)
            return False
        
        # Update P5, update P3 (editor view)
        self._update_pane(PaneType.P5_HLIR, hlir_result.data, event.build_id, event.origin)
        self._update_pane(PaneType.P3_ANALOG_EDITOR, event.content, event.build_id, event.origin)
        
        return self._run_common_pipeline(hlir_result.data, event.build_id, event.origin)
    
    def _handle_hlir_edit(self, event: BuildEvent) -> bool:
        """Handle edit from P5 (HLIR CSV/JSON)"""
        # Validate against JSON Schema
        hlir_result = self._transform_with_validation("validate_hlir", event.content)
        if not hlir_result.is_valid:
            self._handle_error(PaneType.P5_HLIR, "HLIR validation failed", hlir_result.errors)
            return False
        
        # Update P2 (analog text) & P3 (editor view)
        analog_result = self._transform_with_validation("T_hlir_to_analog", event.content)
        if analog_result.is_valid:
            self._update_pane(PaneType.P2_ANALOG_MIRROR, analog_result.data, event.build_id, event.origin)
            self._update_pane(PaneType.P3_ANALOG_EDITOR, analog_result.data, event.build_id, event.origin)
        
        return self._run_common_pipeline(event.content, event.build_id, event.origin)
    
    def _run_common_pipeline(self, hlir_data: str, build_id: int, origin: PaneType) -> bool:
        """
        Common Pipeline: runs after any HLIR change
        1. Validate HLIR (schema + range clamps + profile checks)
        2. Lower: T_hlir→llir
        3. Encode tiles: choose ECC=parity|hamming16_12 per profile
        4. Render P4 (tile sheet) and P6 (live replay)
        """
        try:
            # 1. Validate HLIR
            validation = self._transform_with_validation("validate_hlir_complete", hlir_data)
            if not validation.is_valid:
                self._handle_error(origin, "HLIR validation failed", validation.errors)
                return False
            
            # Store canonical HLIR
            self.hlir_data = hlir_data
            self.hlir_hash = self.cache.get_hash(hlir_data)
            
            # 2. Lower to LLIR
            llir_result = self._transform_with_validation("T_hlir_to_llir", hlir_data)
            if not llir_result.is_valid:
                self._handle_error(origin, "HLIR→LLIR failed", llir_result.errors)
                return False
            
            # 3. Encode tiles
            tiles_result = self._transform_with_validation("encode_tiles", llir_result.data)
            if not tiles_result.is_valid:
                self._handle_error(origin, "Tile encoding failed", tiles_result.errors)
                return False
            
            # 4. Render P4 (tiles) and P6 (replay)
            self._update_pane(PaneType.P4_TILES, tiles_result.data, build_id, origin)
            
            replay_result = self._transform_with_validation("T_hlir_to_replay", hlir_data)
            if replay_result.is_valid:
                self._update_pane(PaneType.P6_REPLAY, replay_result.data, build_id, origin)
            
            # Clear errors for successful build
            self.validation_errors[origin] = []
            
            return True
            
        except Exception as e:
            self._handle_error(origin, f"Common pipeline error: {str(e)}", [traceback.format_exc()])
            return False
    
    def _transform_with_validation(self, transform_name: str, content: str) -> ValidationResult:
        """Apply transform with caching and validation"""
        # Check cache first
        cached_result = self.cache.get(transform_name, content)
        if cached_result is not None:
            return cached_result
        
        # Apply validator if available
        if transform_name in self.validators:
            result = self.validators[transform_name](content)
        else:
            # Default: assume transform succeeds
            if transform_name in self.transformers:
                try:
                    data = self.transformers[transform_name](content)
                    result = ValidationResult(True, [], [], data)
                except Exception as e:
                    result = ValidationResult(False, [str(e)], [], None)
            else:
                result = ValidationResult(False, [f"No transformer for {transform_name}"], [], None)
        
        # Cache result
        self.cache.set(transform_name, content, result)
        return result
    
    def _update_pane(self, pane: PaneType, content: str, build_id: int, origin: PaneType):
        """Update a pane if not pinned and not the origin"""
        if pane == origin or pane in self.pinned_panes:
            return
        
        # Apply normalization check to avoid cursor jumps
        current = self.current_content.get(pane, "")
        if self._should_update_content(current, content):
            self.current_content[pane] = content
            
            # Call registered update handler
            if pane in self.update_handlers:
                try:
                    self.update_handlers[pane](content, build_id, origin)
                except Exception as e:
                    self._handle_error(pane, f"Update handler error: {str(e)}", [])
    
    def _should_update_content(self, current: str, new: str) -> bool:
        """Check if content should be updated (normalization check)"""
        # Only update if content actually changed
        return current.strip() != new.strip()
    
    def _handle_error(self, pane: PaneType, message: str, details: List[str]):
        """Handle validation/transform errors"""
        self.validation_errors[pane] = [message] + details
        print(f"PXOS Bus Error [{pane.value}]: {message}")
        for detail in details:
            print(f"  {detail}")
    
    def get_errors(self, pane: PaneType) -> List[str]:
        """Get current errors for a pane"""
        return self.validation_errors.get(pane, [])
    
    def get_build_info(self) -> Dict[str, Any]:
        """Get current build information"""
        return {
            "build_id": self.build_id,
            "truth_origin": self.truth_origin.value if self.truth_origin else None,
            "timestamp": self.last_build_time,
            "hlir_hash": self.hlir_hash,
            "pinned_panes": [p.value for p in self.pinned_panes],
            "has_errors": any(self.validation_errors.values())
        }
    
    def force_rebuild(self):
        """Force a complete rebuild from current truth"""
        if self.truth_origin and self.truth_origin in self.current_content:
            content = self.current_content[self.truth_origin]
            self.on_edit(self.truth_origin, content, {"force_rebuild": True})
    
    def reset(self):
        """Reset bus state"""
        self.build_id = 0
        self.truth_origin = None
        self.last_build_time = 0
        self.current_content = {pane: "" for pane in PaneType}
        self.pinned_panes.clear()
        self.validation_errors = {pane: [] for pane in PaneType}
        self.cache = TransformCache()
        self.hlir_data = None
        self.hlir_hash = None


# Example validator and transformer registration
def setup_default_bus() -> PXOSBus:
    """Set up a PXOS bus with default validators and transformers"""
    bus = PXOSBus()
    
    # Register basic validators (these would be implemented in separate modules)
    def validate_python(content: str) -> ValidationResult:
        """Validate Python syntax"""
        try:
            import ast
            ast.parse(content)
            return ValidationResult(True, [], [], content)
        except SyntaxError as e:
            return ValidationResult(False, [f"Python syntax error: {str(e)}"], [], None)
    
    def validate_hlir(content: str) -> ValidationResult:
        """Validate HLIR format"""
        # Placeholder - would integrate with pxos_validator.py
        return ValidationResult(True, [], [], content)
    
    # Register validators
    bus.register_validator("validate_python", validate_python)
    bus.register_validator("validate_hlir", validate_hlir)
    bus.register_validator("validate_hlir_complete", validate_hlir)
    
    # Register basic transformers (placeholders)
    bus.register_transformer("T_py_to_hlir", lambda x: f"# Converted from Python:\n{x}")
    bus.register_transformer("T_analog_to_hlir", lambda x: f"# Converted from Analog:\n{x}")
    bus.register_transformer("T_hlir_to_analog", lambda x: f"# Pretty-printed analog:\n{x}")
    bus.register_transformer("T_hlir_to_llir", lambda x: f"# LLIR from: {x[:50]}...")
    bus.register_transformer("encode_tiles", lambda x: f"# Tiles for: {x[:50]}...")
    bus.register_transformer("T_hlir_to_replay", lambda x: f"# Replay: {x[:50]}...")
    
    return bus


# Test the bus system
if __name__ == "__main__":
    bus = setup_default_bus()
    
    # Test basic flow
    print("Testing PXOS Bus data flow...")
    
    # Register mock update handlers
    for pane in PaneType:
        bus.register_update_handler(pane, lambda content, build_id, origin: 
                                  print(f"  Update {pane.value}: {content[:30]}... (build {build_id})"))
    
    # Test Python edit
    print("\n1. Python edit:")
    result = bus.on_edit(PaneType.P1_PYTHON, "print('hello world')")
    print(f"  Result: {result}")
    
    # Test HLIR edit
    print("\n2. HLIR edit:")
    result = bus.on_edit(PaneType.P5_HLIR, "RECT,20,20,40,20,64,64,64")
    print(f"  Result: {result}")
    
    # Test error handling
    print("\n3. Error handling:")
    result = bus.on_edit(PaneType.P1_PYTHON, "invalid python syntax +++")
    print(f"  Result: {result}")
    print(f"  Errors: {bus.get_errors(PaneType.P1_PYTHON)}")
    
    # Show build info
    print(f"\n4. Build info: {bus.get_build_info()}")