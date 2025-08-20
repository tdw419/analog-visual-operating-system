#!/usr/bin/env python3
# Analog Runtime with TCP: Executes AIR commands
# Produces PPM frames and signal trace

from dataclasses import dataclass
from typing import List, Tuple
import time
import json
import uuid
import re
import socketserver
import threading
from font_5x7 import glyph_for

WIDTH, HEIGHT = 160, 90
Color = Tuple[int, int, int]
BLACK: Color = (0, 0, 0)
GREEN: Color = (0, 255, 0)
BLUE: Color = (100, 100, 255)
WHITE = (255, 255, 255)

@dataclass
class Rect:
    x: int
    y: int
    w: int
    h: int
    color: Color
    correlation_id: str = ""
    def sample(self, px: int, py: int) -> Color | None:
        if self.x <= px < self.x + self.w and self.y <= py < self.y + self.h:
            return self.color
        return None

@dataclass
class Text:
    text: str
    x: int
    y: int
    color: Color
    scale: int = 2
    correlation_id: str = ""
    def sample(self, px: int, py: int) -> Color | None:
        char_w, char_h = 5 * self.scale, 7 * self.scale
        dx, dy = px - self.x, py - self.y
        if dx < 0 or dy < 0 or dy // char_h != 0:
            return None
        col = dx // char_w
        if col >= len(self.text):
            return None
        ch = self.text[col].upper()
        glyph = glyph_for(ch)
        gx = (dx % char_w) // self.scale
        gy = (dy % char_h) // self.scale
        if 0 <= gx < 5 and 0 <= gy < 7 and glyph[gy][gx] == '#':
            return self.color
        return None

@dataclass
class Line:
    x1: int
    y1: int
    x2: int
    y2: int
    color: Color
    correlation_id: str = ""
    def sample(self, px: int, py: int) -> Color | None:
        # Basic line sampling, not perfect but good for demo
        # A proper implementation would use Bresenham's line algorithm checks
        # For simplicity, we just check if the point is on the line segment
        # This is computationally expensive and not how a real analog system would do it
        # but serves for creating a visual representation in the simulator.
        dist_ap = ((px - self.x1)**2 + (py - self.y1)**2)**0.5
        dist_pb = ((self.x2 - px)**2 + (self.y2 - py)**2)**0.5
        dist_ab = ((self.x2 - self.x1)**2 + (self.y2 - self.y1)**2)**0.5
        if abs(dist_ap + dist_pb - dist_ab) < 0.5: # Check if point is on the line
            return self.color
        return None

@dataclass
class Cursor:
    x: int
    y: int
    w: int
    h: int
    color: Color
    blink_hz: int
    correlation_id: str = ""
    def sample(self, px: int, py: int, t: float) -> Color | None:
        if self.blink_hz > 0 and int(t * self.blink_hz * 2) % 2 == 0:
            return None # Blink off
        if self.x <= px < self.x + self.w and self.y <= py < self.y + self.h:
            return self.color
        return None

@dataclass
class Scene:
    objects: List[object]

class Tracer:
    def __init__(self):
        self.logs = []

    def log(self, event_type: str, operation: object = None, signals: list = None):
        self.logs.append({
            'timestamp': time.time(),
            'correlation_id': str(uuid.uuid4())[:8],
            'event_type': event_type,
            'operation': operation.__dict__ if operation else None,
            'signals': signals if signals else []
        })

    def save(self, filename: str):
        with open(filename, 'w') as f:
            json.dump(self.logs, f, indent=2)

def compute_pixel(x: int, y: int, t: float, scene: Scene) -> Color:
    color = BLACK
    # Paint in reverse order (last object is on top)
    for obj in reversed(scene.objects):
        sample = None
        if isinstance(obj, Cursor):
            sample = obj.sample(x, y, t)
        else:
            sample = obj.sample(x, y)

        if sample is not None:
            color = sample
            break # Stop when the top-most object is found
    return color

def scan_out(scene: Scene, t: float) -> List[List[Color]]:
    frame = []
    for py in range(HEIGHT):
        row = []
        for px in range(WIDTH):
            row.append(compute_pixel(px, py, t, scene))
        frame.append(row)
    return frame

def write_ppm(filename: str, frame: List[List[Color]]):
    with open(filename, "w") as f:
        f.write(f"P3\n{WIDTH} {HEIGHT}\n255\n")
        for row in frame:
            f.write(" ".join(f"{r} {g} {b}" for r,g,b in row) + "\n")

class AnalogRuntime:
    def __init__(self):
        self.scene = Scene(objects=[])
        self.tracer = Tracer()
        self.time = 0.0
        self.event_handlers = {}
        self.lock = threading.Lock()

    def handle_command(self, command: str):
        with self.lock:
            cid = str(uuid.uuid4())[:8]
            # TEXT "HELLO" AT 16,20 COLOR #00FF00 SCALE 2
            m = re.match(r'^TEXT\s+"([^"]+)"\s+AT\s+(\d+)\s*,\s*(\d+)(?:\s+COLOR\s+(#?[0-9a-fA-F]{6}))?(?:\s+SCALE\s+(\d+))?$', command, re.I)
            if m:
                s,x,y,col,sc = m[0]
                text_obj = Text(text=s, x=int(x), y=int(y), color=hex_rgb(col) if col else GREEN, scale=int(sc) if sc else 2, correlation_id=cid)
                self.scene.objects.append(text_obj)
                self.tracer.log("TEXT", text_obj)
                return

            # RECT 10,40,60,14 COLOR #6464FF
            m = re.match(r'^RECT\s+(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s+COLOR\s+(#?[0-9a-fA-F]{6}))?$', command, re.I)
            if m:
                x,y,w,h,*rest = m[0]
                col = rest[0] if rest else None
                rect_obj = Rect(x=int(x), y=int(y), w=int(w), h=int(h), color=hex_rgb(col) if col else BLUE, correlation_id=cid)
                self.scene.objects.append(rect_obj)
                self.tracer.log("RECT", rect_obj)
                return

            # ON_KEY "X" { TEXT "X" AT 16,70 COLOR #00FF00 }
            m = re.match(r'^ON_KEY\s+"([^"]+)"\s+\{\s*(.*)\s*\}$', command, re.I)
            if m:
                key, body = m[0]
                self.event_handlers[key] = body
                self.tracer.log(f"ON_KEY_{key}", operation={'handler': body})
                return

    def handle_key_press(self, key: str):
        if key in self.event_handlers:
            handler_body = self.event_handlers[key]
            # For this demo, we just re-run the command. A real system would be more complex.
            print(f"Executing handler for key '{key}': {handler_body}")
            self.handle_command(handler_body)

    def run_and_render(self, frame_count=1, base_filename="frame"):
        with self.lock:
            for i in range(frame_count):
                self.time += 0.016 # ~60fps
                frame = scan_out(self.scene, self.time)
                write_ppm(f"{base_filename}{i+1}.ppm", frame)
            self.tracer.save("trace.json")
            print(f"Rendered {frame_count} frame(s) and updated trace.json")

class TCPHandler(socketserver.BaseRequestHandler):
    def handle(self):
        runtime = self.server.runtime
        print(f"Client connected: {self.client_address}")
        for line in self.rfile:
            command = line.strip().decode('utf-8')
            if not command: continue

            print(f"Received command: {command}")
            if command.startswith("KEY "):
                key = command.split(' ', 1)[1]
                runtime.handle_key_press(key)
            else:
                runtime.handle_command(command)

            # After each command, render a new frame
            runtime.run_and_render(1, base_filename=f"frame_{int(time.time())}")
        print(f"Client disconnected: {self.client_address}")

def main():
    runtime = AnalogRuntime()

    HOST, PORT = "localhost", 12345
    server = socketserver.TCPServer((HOST, PORT), TCPHandler)
    server.runtime = runtime # Make runtime accessible to handlers

    print(f"Analog Runtime TCP server listening on {HOST}:{PORT}")

    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    try:
        # Initial render
        runtime.run_and_render(1, "initial_frame")
        print("Initial frame rendered. Waiting for TCP commands. Press Ctrl+C to exit.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down server.")
    finally:
        server.shutdown()
        server.server_close()

if __name__ == "__main__":
    main()
