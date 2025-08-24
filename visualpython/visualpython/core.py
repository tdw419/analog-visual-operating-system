import ast
import time
import csv
import os
from typing import Dict, Any, List
from .renderer import TkRenderer

class VisualPythonEngine:
    """
    Engine for direct visual execution of Python code.
    Parses AST and renders to a visual backend with keyframe support.
    """
    def __init__(self, backend='tkinter', width=800, height=600, signal_file='signals.csv'):
        self.backend = backend
        self.width = width
        self.height = height
        self.variables: Dict[str, Any] = {}
        self.keyframes: List[Dict] = []
        self.signals: List[List] = []
        self.signal_file = signal_file
        self.current_time = 5.0  # Start at keyframe 5 (post-boot)
        self.stepper_mode = False
        self.renderer = TkRenderer(width, height) if backend == 'tkinter' else None
        self.setup_bitmap_font()
        self.setup_boot_sequence()

    def setup_bitmap_font(self):
        """Initialize the 5x7 bitmap font."""
        self.font5x7 = {
            'A': [0x0E, 0x11, 0x1F, 0x11, 0x11], 'B': [0x1E, 0x11, 0x1E, 0x11, 0x1E],
            'C': [0x0E, 0x11, 0x10, 0x11, 0x0E], 'D': [0x1E, 0x11, 0x11, 0x11, 0x1E],
            'E': [0x1F, 0x10, 0x1E, 0x10, 0x1F], 'F': [0x1F, 0x10, 0x1E, 0x10, 0x10],
            'G': [0x0E, 0x11, 0x13, 0x11, 0x0E], 'H': [0x11, 0x11, 0x1F, 0x11, 0x11],
            'I': [0x0E, 0x04, 0x04, 0x04, 0x0E], 'L': [0x10, 0x10, 0x10, 0x10, 0x1F],
            'M': [0x11, 0x1B, 0x15, 0x11, 0x11], 'N': [0x11, 0x19, 0x15, 0x13, 0x11],
            'O': [0x0E, 0x11, 0x11, 0x11, 0x0E], 'P': [0x1E, 0x11, 0x1E, 0x10, 0x10],
            'R': [0x1E, 0x11, 0x1E, 0x14, 0x13], 'S': [0x0F, 0x10, 0x0E, 0x01, 0x1E],
            'T': [0x1F, 0x04, 0x04, 0x04, 0x04], 'U': [0x11, 0x11, 0x11, 0x11, 0x0E],
            'V': [0x11, 0x11, 0x11, 0x0A, 0x04], 'W': [0x11, 0x11, 0x15, 0x1B, 0x11],
            'X': [0x11, 0x0A, 0x04, 0x0A, 0x11], 'Y': [0x11, 0x0A, 0x04, 0x04, 0x04],
            'Z': [0x1F, 0x02, 0x04, 0x08, 0x1F],
            '0': [0x0E, 0x11, 0x11, 0x11, 0x0E], '1': [0x04, 0x0C, 0x04, 0x04, 0x0E],
            '2': [0x0E, 0x11, 0x02, 0x08, 0x1F], '3': [0x1F, 0x02, 0x06, 0x01, 0x1E],
            '4': [0x02, 0x06, 0x0A, 0x1F, 0x02], '5': [0x1F, 0x10, 0x1E, 0x01, 0x1E],
            '6': [0x06, 0x08, 0x1E, 0x11, 0x0E], '7': [0x1F, 0x01, 0x02, 0x04, 0x08],
            '8': [0x0E, 0x11, 0x0E, 0x11, 0x0E], '9': [0x0E, 0x11, 0x0F, 0x02, 0x0C],
            ' ': [0x00, 0x00, 0x00, 0x00, 0x00], ':': [0x00, 0x04, 0x00, 0x04, 0x00],
            '(': [0x02, 0x04, 0x04, 0x04, 0x02], ')': [0x08, 0x04, 0x04, 0x04, 0x08],
            '!': [0x04, 0x04, 0x04, 0x00, 0x04], ',': [0x00, 0x00, 0x00, 0x04, 0x08],
            '.': [0x00, 0x00, 0x00, 0x00, 0x04], '_': [0x00, 0x00, 0x00, 0x00, 0x1F]
        }

    def setup_boot_sequence(self):
        """Initialize Timeline OS boot sequence keyframes."""
        self.keyframes = [
            {'time': 0.0, 'text': 'TIMELINE OS v1.0', 'color': 'cyan', 'x': 20, 'y': 80, 'displayMode': 'text'},
            {'time': 1.0, 'text': 'INITIALIZING ANALOG CORE', 'color': 'yellow', 'x': 20, 'y': 95, 'displayMode': 'text'},
            {'time': 2.0, 'text': 'LOADING SIGNAL DRIVERS', 'color': 'orange', 'x': 20, 'y': 110, 'displayMode': 'text'},
            {'time': 3.0, 'text': 'BOOT SEQUENCE COMPLETE', 'color': 'lime', 'x': 20, 'y': 125, 'displayMode': 'text'},
            {'time': 5.0, 'text': 'FONT SYSTEM LOADED', 'color': 'white', 'x': 20, 'y': 50, 'displayMode': 'fontGrid', 'fontData': self.font5x7}
        ]

    def step_back(self):
        """Step to the previous keyframe."""
        if self.keyframes:
            self.current_time = max(0.0, self.current_time - 0.1)
            self.render_keyframes()

    def step_forward(self):
        """Step to the next keyframe."""
        if self.keyframes:
            self.current_time = min(max(kf['time'] for kf in self.keyframes), self.current_time + 0.1)
            self.render_keyframes()

    def play_keyframes(self):
        """Play keyframes as an animation."""
        if self.keyframes:
            self.current_time = 0.0
            self.render_keyframes()
            self.renderer.root.after(100, self._animate_keyframes)

    def _animate_keyframes(self):
        """Animate through keyframes."""
        if self.current_time < max(kf['time'] for kf in self.keyframes):
            self.current_time += 0.1
            self.render_keyframes()
            self.renderer.root.after(100, self._animate_keyframes)

    def render_node(self, node):
        """Process a single AST node."""
        if isinstance(node, ast.Assign):
            self.render_variable(node)
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            self.render_function_call(node.value)
        elif isinstance(node, ast.For):
            self.render_for_loop(node)

    def render_variable(self, node):
        """Render an assignment as a keyframe."""
        if isinstance(node.targets[0], ast.Name):
            var_name = node.targets[0].id
            value = self.evaluate(node.value)
            self.variables[var_name] = value
            timestamp = int(time.time() * 1000)
            y_pos = (len(self.variables) * 30) + 50
            keyframe = {
                'time': self.current_time,
                'text': f"{var_name} = {value}",
                'color': 'yellow',
                'x': 350,
                'y': y_pos,
                'displayMode': 'text'
            }
            self.keyframes.append(keyframe)
            self.signals.append([timestamp, 'assign', 350, y_pos, 0, 255, 0, var_name, value])
            if isinstance(value, (int, float)):
                bar_width = min(abs(value) * 2, self.width - 500)
                color = 'lime' if value >= 0 else 'red'
                self.keyframes.append({
                    'time': self.current_time + 0.01,
                    'operation': 'rect',
                    'params': {'x': 500, 'y': y_pos - 10, 'width': bar_width, 'height': 10, 'color': color},
                    'displayMode': 'rect'
                })
                self.signals.append([timestamp, 'rect', 500, y_pos - 10, 0, 255, 0, 'bar', value])
            self.current_time += 0.1

    def render_function_call(self, node):
        """Render a print statement as a keyframe."""
        if isinstance(node.func, ast.Name) and node.func.id == 'print':
            arg = self.evaluate(node.args[0]) if node.args else ''
            timestamp = int(time.time() * 1000)
            y_pos = (len(self.variables) + 1) * 30 + 50
            keyframe = {
                'time': self.current_time,
                'text': str(arg),
                'color': 'cyan',
                'x': 20,
                'y': y_pos,
                'displayMode': 'text'
            }
            self.keyframes.append(keyframe)
            self.signals.append([timestamp, 'print', 20, y_pos, 0, 255, 255, 'output', arg])
            self.current_time += 0.1

    def render_for_loop(self, node):
        """Process a for loop and generate keyframes for each iteration."""
        if isinstance(node.target, ast.Name) and isinstance(node.iter, ast.Call):
            if isinstance(node.iter.func, ast.Name) and node.iter.func.id == 'range':
                var_name = node.target.id
                args = [self.evaluate(arg) for arg in node.iter.args]
                start, stop, step = (0, args[0], 1) if len(args) == 1 else (args[0], args[1], 1) if len(args) == 2 else args
                y_pos = (len(self.variables) + 1) * 30 + 50
                for i in range(start, stop, step):
                    self.variables[var_name] = i
                    self.keyframes.append({
                        'time': self.current_time,
                        'text': f"{var_name} = {i}",
                        'color': 'yellow',
                        'x': 350,
                        'y': y_pos,
                        'displayMode': 'text'
                    })
                    self.signals.append([int(time.time() * 1000), 'assign', 350, y_pos, 0, 255, 0, var_name, i])
                    # Render a tick mark for each iteration
                    self.keyframes.append({
                        'time': self.current_time + 0.01,
                        'operation': 'rect',
                        'params': {'x': 20 + i * 10, 'y': y_pos + 20, 'width': 5, 'height': 5, 'color': 'lime'},
                        'displayMode': 'rect'
                    })
                    self.signals.append([int(time.time() * 1000), 'rect', 20 + i * 10, y_pos + 20, 0, 255, 0, 'tick', i])
                    # Process loop body
                    for body_node in node.body:
                        self.render_node(body_node)
                    self.current_time += 0.1

    def evaluate(self, node):
        """Evaluate an AST node."""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            return self.variables.get(node.id, '???')
        elif isinstance(node, ast.BinOp):
            left = self.evaluate(node.left)
            right = self.evaluate(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            elif isinstance(node.op, ast.Mult):
                return left * right
            return '???'
        elif isinstance(node, ast.Str):
            return node.s
        elif isinstance(node, ast.JoinedStr):
            return ''.join(self.evaluate(v) if isinstance(v, ast.FormattedValue) else v.value for v in node.values)
        elif isinstance(node, ast.FormattedValue):
            return str(self.evaluate(node.value))
        return '???'

    def parse_and_execute_direct(self, code):
        """Parse code and generate keyframes."""
        self.renderer.clear()
        self.variables = {}
        self.keyframes = self.keyframes[:5]  # Preserve boot sequence
        self.signals = []
        self.current_time = 5.0  # Start at keyframe 5
        tree = ast.parse(code)
        for node in tree.body:
            self.render_node(node)
        self.render_keyframes()

    def render_keyframes(self):
        """Render keyframes up to the current time."""
        self.renderer.clear()
        for kf in self.keyframes:
            if kf['time'] <= self.current_time:
                if kf['displayMode'] == 'text':
                    self.renderer.render_bitmap_text(kf['text'], kf['x'], kf['y'], scale=2, color=kf['color'])
                elif kf['displayMode'] == 'rect':
                    params = kf.get('params', {})
                    self.renderer.render_rect(
                        params['x'], params['y'],
                        params['width'], params['height'],
                        params['color']
                    )
                elif kf['displayMode'] == 'fontGrid':
                    y = 50
                    for i, (char, bitmap) in enumerate(self.font5x7.items()):
                        x = 20 + (i % 16) * 40
                        if i % 16 == 0 and i > 0:
                            y += 40
                        self.renderer.render_bitmap_text(char, x, y, scale=2, color='white')
                        self.renderer.render_bitmap_text(f"{ord(char):02X}", x, y + 15, scale=1, color='cyan')

    def execute(self, code, live_mode=False):
        """Execute code and return time in ms."""
        start = time.time()
        self.parse_and_execute_direct(code)
        self.renderer.update()
        self.export_signals()
        exec_time = (time.time() - start) * 1000
        return exec_time

    def export_signals(self):
        """Export signals to CSV for analog output."""
        if self.signals:
            with open(self.signal_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'operation', 'x', 'y', 'r', 'g', 'b', 'variable', 'value'])
                writer.writerows(self.signals)

    def cleanup(self):
        """Clean up resources."""
        if self.renderer:
            self.renderer.cleanup()
