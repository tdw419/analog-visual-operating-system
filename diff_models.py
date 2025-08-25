from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Literal

OpStatus = Literal["same", "changed", "added", "removed"]

@dataclass
class FieldDiff:
    field: str
    left: Any
    right: Any

@dataclass
class OpDiff:
    index: int
    status: OpStatus
    op_left: Optional[Dict[str, Any]] = None
    op_right: Optional[Dict[str, Any]] = None
    field_diffs: List[FieldDiff] = field(default_factory=list)

@dataclass
class JsonDiff:
    ops: List[OpDiff]
    same_count: int
    changed_count: int
    added_count: int
    removed_count: int
