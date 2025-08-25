from __future__ import annotations
from typing import Dict, Any, Tuple
from PIL import Image, ImageDraw
from map_contracts import Program, ProgramState, Px, BBox

from control_strip import draw_control, read_control

class HelloScreen(Program):
    id = "hello_screen"
    def draw(self, state: ProgramState, px: Px, local_bbox: BBox) -> None:
        px.clear("#101018")
        px.text(10, 12, "PXOS — Screen (Hello)", 14, "#A0FFA0")
        px.rect(8, 30, local_bbox.x1 - local_bbox.x0 - 16, 2, "#2a2a40")
        px.text(10, 44, f"PC: {state.pc}", 12, "#FFFFFF")
        fields = {"SCREEN_ID": 1, "PC": state.pc, "MAILBOX_OUT": state.mailbox_out}
        draw_control(px._draw, fields)
    def decode(self, img: Image.Image) -> Dict[str, Any]:
        return read_control(img)
    def update(self, decoded: Dict[str, Any], state: ProgramState, inputs: Dict) -> Tuple[ProgramState, str]:
        next_id = "hello_screen"
        if inputs.get("key_next"):
            next_id = "clock_screen"
        return ProgramState(pc=(state.pc + 1) % 4096, mailbox_out=state.mailbox_out), next_id
    def accept(self, decoded: Dict[str, Any]) -> bool:
        return decoded.get("SCREEN_ID") == 1 and decoded.get("CRC16", 0) == 0

class ClockScreen(Program):
    id = "clock_screen"
    def draw(self, state: ProgramState, px: Px, local_bbox: BBox) -> None:
        from datetime import datetime
        px.clear("#000000")
        now = datetime.now()
        px.text(10, 12, "PXOS — Screen (Clock)", 14, "#FFD966")
        px.text(10, 44, now.strftime("%H:%M:%S"), 24, "#FFFFFF")
        fields = {"SCREEN_ID": 2, "PC": state.pc, "MAILBOX_OUT": now.second}
        draw_control(px._draw, fields)
    def decode(self, img: Image.Image) -> Dict[str, Any]:
        return read_control(img)
    def update(self, decoded: Dict[str, Any], state: ProgramState, inputs: Dict) -> Tuple[ProgramState, str]:
        next_id = "clock_screen"
        if inputs.get("key_back"):
            next_id = "hello_screen"
        return ProgramState(pc=(state.pc + 1) % 4096, mailbox_out=state.mailbox_out), next_id
    def accept(self, decoded: Dict[str, Any]) -> bool:
        return decoded.get("SCREEN_ID") == 2 and decoded.get("CRC16", 0) == 0

REGISTRY = {
    HelloScreen.id: HelloScreen(),
    ClockScreen.id: ClockScreen(),
}
