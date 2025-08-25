from __future__ import annotations
import json
import os
import time
import uuid
from typing import List, Dict, Tuple, Iterable, Optional, Protocol
from PIL import Image, ImageDraw, ImageStat, ImageFont
from map_contracts import BBox, StackHeader, Program, ProgramState, Px, Point
from toy_programs import REGISTRY

CHUNK_SIZE = 256

def chunk_of(x: int, y: int) -> Tuple[int, int]:
    return x // CHUNK_SIZE, y // CHUNK_SIZE

class Store(Protocol):
    def get(self, key: str) -> Optional[bytes]:...
    def put(self, key: str, value: bytes) -> None:...

class InMemStore(Store):
    """In-memory key-value store for development"""
    def __init__(self):
        self._data: Dict[str, bytes] = {}
    def get(self, key: str) -> Optional[bytes]:
        return self._data.get(key)
    def put(self, key: str, value: bytes) -> None:
        self._data[key] = value

class MapRuntime:
    def __init__(self, store: Store):
        self.store = store
        self._stacks: Dict[str, StackHeader] = {} # In-memory cache for headers

    def stacks_in_view(self, view: BBox) -> List[StackHeader]:
        # Simplified for in-memory store; a real version would use a chunk index
        visible_stacks = []
        for header in self._stacks.values():
            if self._intersects(header.bbox, view):
                visible_stacks.append(header)
        return sorted(visible_stacks, key=lambda h: h.z)

    def _intersects(self, bbox1: BBox, bbox2: BBox) -> bool:
        return not (bbox1.x1 <= bbox2.x0 or bbox1.x0 >= bbox2.x1 or bbox1.y1 <= bbox2.y0 or bbox1.y0 >= bbox2.y1)

    def place_program(self, program_id: str, mount_at: Point, bbox: BBox, z: int) -> StackHeader:
        stack_id = str(uuid.uuid4())
        header = StackHeader(stack_id=stack_id, program_id=program_id, mount_at=mount_at, bbox=bbox, z=z)
        self._stacks[stack_id] = header
        return header

    def step_visible(self, view: BBox, inputs: Dict[str, Any]) -> Image.Image:
        # 1) Create a blank framebuffer for compositing
        framebuffer = Image.new("RGB", (view.x1 - view.x0, view.y1 - view.y0), "#000000")

        # 2) Render and advance each visible stack
        for hdr in self.stacks_in_view(view):
            program = REGISTRY.get(hdr.program_id)
            if not program:
                continue
            # Create a local image for the stack's frame
            img = Image.new("RGB", (hdr.bbox.x1 - hdr.bbox.x0, hdr.bbox.y1 - hdr.bbox.y0), "#000000")
            px_proxy = self._create_px_proxy(img)
            program.draw(hdr.state, px_proxy, hdr.bbox)
            # Decode and update state
            decoded = program.decode(img)
            new_state, next_program_id = program.update(decoded, hdr.state, inputs)
            if new_state!= hdr.state:
                hdr.state = new_state
                self._stacks[hdr.stack_id] = hdr # Persist
            if next_program_id and next_program_id!= hdr.program_id:
                hdr.program_id = next_program_id
                hdr.state = ProgramState() # Reset state on switch
            # Composite the frame into the framebuffer
            ox, oy = hdr.bbox.x0 - view.x0, hdr.bbox.y0 - view.y0
            framebuffer.paste(img, (ox, oy), mask=None)

        # 3) return final framebuffer
        return framebuffer

    def _create_px_proxy(self, img: Image.Image) -> Px:
        """Creates a minimal proxy that implements the Px protocol for drawing"""
        draw = ImageDraw.Draw(img)
        class PxProxy:
            width, height = img.size
            _draw = draw
            def rect(self, x:int, y:int, w:int, h:int, color:str) -> None:
                draw.rectangle([x, y, x+w-1, y+h-1], fill=color)
            def line(self, x1:int, y1:int, x2:int, y2:int, width:int, color:str) -> None:
                draw.line([x1, y1, x2, y2], fill=color, width=width)
            def text(self, x:int, y:int, text:str, size:int, color:str) -> None:
                # Placeholder font logic
                font = ImageFont.load_default()
                draw.text((x,y), text, fill=color, font=font)
            def clear(self, color:str) -> None:
                draw.rectangle([0,0,self.width,self.height], fill=color)
            def tick(self) -> None: pass
        return PxProxy()

def run_map_demo(frames=5, out_dir="out_map"):
    os.makedirs(out_dir, exist_ok=True)
    store = InMemStore()
    runtime = MapRuntime(store=store)

    # Mount a hello screen at (10, 10) on the map
    runtime.place_program(
        program_id="hello_screen",
        mount_at=Point(10, 10),
        bbox=BBox(10, 10, 330, 210),
        z=1
    )

    # Mount a clock screen at (300, 200) on the map
    runtime.place_program(
        program_id="clock_screen",
        mount_at=Point(300, 200),
        bbox=BBox(300, 200, 620, 400),
        z=2
    )

    # Simulate a viewport pan
    view = BBox(0, 0, 320, 200)
    for f in range(frames):
        # Render visible stacks and composite into the framebuffer
        framebuffer = runtime.step_visible(view, inputs={})
        framebuffer.save(os.path.join(out_dir, f"frame_{f:06d}.png"))
        # Pan the view to reveal the clock screen
        view.x0 = int(f * 2)
        view.y0 = int(f * 1.5)
        view.x1 = view.x0 + 320
        view.y1 = view.y0 + 200

if __name__ == "__main__":
    run_map_demo()
