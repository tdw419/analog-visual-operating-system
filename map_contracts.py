from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any, Protocol
from PIL import Image, ImageDraw

@dataclass
class Point:
    x: int
    y: int

@dataclass
class BBox:
    x0: int
    y0: int
    x1: int
    y1: int

@dataclass
class ProgramState:
    pc: int = 0
    mailbox_out: int = 0

@dataclass
class StackHeader:
    stack_id: str
    program_id: str
    mount_at: Point
    bbox: BBox
    z: int
    state: ProgramState = field(default_factory=ProgramState)
    frames: List[str] = field(default_factory=list)

class Program(Protocol):
    id: str
    def draw(self, state: ProgramState, px: Px, local_bbox: BBox) -> None:...
    def decode(self, img: Image.Image) -> Dict[str, Any]:...
    def update(self, decoded: Dict[str, Any], state: ProgramState, inputs: Dict[str, Any]) -> Tuple[ProgramState, str]:...
    def accept(self, decoded: Dict[str, Any]) -> bool:...

# Frame/pixel abstraction for rendering
class Px(Protocol):
    width: int
    height: int
    _draw: ImageDraw.Draw
    def rect(self, x:int, y:int, w:int, h:int, color:str) -> None:...
    def line(self, x1:int, y1:int, x2:int, y2:int, width:int, color:str) -> None:...
    def text(self, x:int, y:int, text:str, size:int, color:str) -> None:...
    def clear(self, color:str) -> None:...
    def tick(self) -> None:...
