import time
import ast
import csv
import argparse
import sys
import signal
from typing import TypedDict, Protocol, List, Optional, Tuple
import numpy as np
from PIL import Image
import mss

try:
    import pygetwindow as gw
except Exception:
    gw = None

class Op(TypedDict):
    stream: str
    frame: int
    dt: float
    op: str
    x: int | None
    y: int | None
    w: int | None
    h: int | None
    r: int | None
    g: int | None
    b: int | None
    intensity: float | None
    text: str | None
    id: str | None

class Clock:
    def __init__(self, fps: int):
        self.fps = fps
        self.period = 1.0 / fps
        self.frame_count = 0
        self.next_tick = time.perf_counter()

    def wait_next_tick(self):
        self.next_tick += self.period
        sleep_for = self.next_tick - time.perf_counter()
        if sleep_for > 0:
            time.sleep(sleep_for)
        self.frame_count += 1

    @property
    def frame(self) -> int:
        return self.frame_count

class Producer(Protocol):
    def tick(self, frame: int) -> List[Op]:
        ...

class SourceProducer(Producer, ast.NodeVisitor):
    def __init__(self, path: str):
        self.path = path
        self.ops = []
        self.frame = 0
        self._transpile()

    def _transpile(self):
        with open(self.path, 'r') as f:
            code = f.read()
        tree = ast.parse(code)
        self.visit(tree)

    def tick(self, frame: int) -> List[Op]:
        # For now, we return all ops on the first frame.
        # A more advanced implementation would execute the ops over time.
        if frame == 1:
            return self.ops
        return []

    def visit_Assign(self, node):
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            var_name = node.targets[0].id
            if isinstance(node.value, ast.Constant):
                value = node.value.value
            else:
                value = "expr"
            self.ops.append({'op': 'SET_VAR', 'param1': var_name, 'param2': value})
            self.frame += 1
        self.generic_visit(node)

    def visit_Expr(self, node):
        if isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Name) and call.func.id == 'print':
                if len(call.args) == 1 and isinstance(call.args[0], ast.Constant):
                    text = call.args[0].value
                    self.ops.append({'op': 'PRINT', 'param1': text})
                    self.frame += 1
        self.generic_visit(node)

    def visit_For(self, node):
        if (isinstance(node.target, ast.Name) and
                isinstance(node.iter, ast.Call) and
                isinstance(node.iter.func, ast.Name) and
                node.iter.func.id == 'range'):
            loop_var = node.target.id
            if len(node.iter.args) == 1 and isinstance(node.iter.args[0], ast.Constant):
                start = 0
                stop = node.iter.args[0].value
                self.ops.append({'op': 'LOOP_START', 'param1': loop_var, 'param2': start, 'param3': stop})
                self.frame += 1
                for stmt in node.body:
                    self.visit(stmt)
                self.ops.append({'op': 'LOOP_END'})
                self.frame += 1

class AppProducer(Producer):
    def __init__(self, window_title_substr: str, tile_px: int = 8, thresh: float = 10.0, max_rects_per_frame: int = 200):
        self.window_title_substr = window_title_substr
        self.tile_px = tile_px
        self.thresh = thresh
        self.max_rects_per_frame = max_rects_per_frame
        self.sct = mss.mss()
        self.prev_small = None
        self.bbox = self._find_window_bbox()
        if not self.bbox:
            raise RuntimeError(f"Window not found or unsupported. Title contains: {self.window_title_substr!r}")

    def _find_window_bbox(self) -> Optional[Tuple[int,int,int,int]]:
        if gw is None:
            return None
        wins = [w for w in gw.getAllTitles() if self.window_title_substr.lower() in w.lower()]
        if not wins:
            return None
        w = gw.getWindowsWithTitle(wins[0])[0]
        if not w or not w.isVisible:
            return None
        return (w.left, w.top, w.left + w.width, w.top + w.height)

    def _tile_average(self, img: np.ndarray, tile: int) -> np.ndarray:
        H, W, C = img.shape
        h = (H // tile) * tile
        w = (W // tile) * tile
        img = img[:h, :w, :3]
        img = img.reshape(h // tile, tile, w // tile, tile, 3).mean(axis=(1,3)).astype(np.uint8)
        return img

    def tick(self, frame: int) -> List[Op]:
        left, top, right, bottom = self.bbox
        width, height = right - left, bottom - top

        frame_data = np.array(self.sct.grab({"left": left, "top": top, "width": width, "height": height}))
        frame_rgb = frame_data[..., :3][:, :, ::-1]

        small = self._tile_average(frame_rgb, self.tile_px)

        changed_tiles = []
        if self.prev_small is None:
            baseline = np.zeros_like(small)
            diff = np.linalg.norm(small.astype(np.float32) - baseline.astype(np.float32), axis=2)
            changed_tiles = np.argwhere(diff > 0.0)
        else:
            diff = np.linalg.norm(small.astype(np.float32) - self.prev_small.astype(np.float32), axis=2)
            changed_tiles = np.argwhere(diff > self.thresh)

        ops = []
        rects_emitted = 0
        for ty, tx in changed_tiles:
            if rects_emitted >= self.max_rects_per_frame:
                break
            r, g, b = map(int, small[ty, tx])
            x = int(tx * self.tile_px)
            y = int(ty * self.tile_px)
            w = self.tile_px
            h = self.tile_px
            ops.append({'op': 'RECT', 'x': x, 'y': y, 'w': w, 'h': h, 'r': r, 'g': g, 'b': b})
            rects_emitted += 1

        ops.append({'op': 'COMMIT'})
        self.prev_small = small
        return ops

class Sink(Protocol):
    def write(self, op: Op):
        ...

class CsvSink(Sink):
    def __init__(self, path: str):
        self.file = open(path, 'w', newline='')
        self.writer = csv.DictWriter(self.file, fieldnames=Op.__annotations__.keys())
        self.writer.writeheader()

    def write(self, op: Op):
        self.writer.writerow(op)

    def close(self):
        self.file.close()

class SimulatorSink(Sink):
    def write(self, op: Op):
        print(f"SimulatorSink: received op from stream '{op['stream']}' for frame {op['frame']}")

class Multiplexer:
    def __init__(self, sinks: List[Sink]):
        self.sinks = sinks

    def push(self, ops: List[Op]):
        for op in ops:
            for sink in self.sinks:
                sink.write(op)

    def close(self):
        for sink in self.sinks:
            if hasattr(sink, 'close'):
                sink.close()

def main():
    parser = argparse.ArgumentParser(description="Orchestrator for the Intelligent Display Stack")
    parser.add_argument('--src', type=str, help='Path to the source code file to be transpiled.')
    parser.add_argument('--export-src', type=str, help='Path to export the CSV for the source stream.')
    parser.add_argument('--app-title', type=str, help='Title of the application window to capture.')
    parser.add_argument('--export-app', type=str, help='Path to export the CSV for the app stream.')
    parser.add_argument('--preview', type=str, choices=['split', 'tabbed'], help='Live preview mode.')
    parser.add_argument('--fps', type=int, default=30, help='Frames per second for the simulation.')
    parser.add_argument('--lockstep', action='store_true', help='Run producers in lockstep.')

    args = parser.parse_args()

    clock = Clock(fps=args.fps)

    producers = []
    if args.src:
        producers.append(SourceProducer(args.src))
    if args.app_title:
        producers.append(AppProducer(args.app_title))

    sinks = []
    if args.export_src:
        sinks.append(CsvSink(args.export_src))
    if args.export_app:
        sinks.append(CsvSink(args.export_app))

    if args.preview:
        sinks.append(SimulatorSink())

    mux = Multiplexer(sinks=sinks)

    try:
        while True:
            clock.wait_next_tick()

            all_ops = []
            for producer in producers:
                ops = producer.tick(clock.frame)
                stream_name = 'src' if isinstance(producer, SourceProducer) else 'app'
                for op in ops:
                    op['stream'] = stream_name
                    op['frame'] = clock.frame
                    op['dt'] = clock.period
                all_ops.extend(ops)

            mux.push(all_ops)

    except KeyboardInterrupt:
        print("\nOrchestrator shutting down.")
    finally:
        mux.close()

if __name__ == "__main__":
    main()
