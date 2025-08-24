# analog_code_workbench.py
"""
Analog Code Workbench — 4-pane UI to turn source → analog pixels → CSV → visual result.
Layout (2x2 grid):
[ Pane 1 ] Original Python source (editable Text)
[ Pane 2 ] Analog view = tile-encoded program sheet (live preview Image)
[ Pane 3 ] Analog code (CSV / IR) (editable Text)
[ Pane 4 ] Result canvas (replays CSV drawing ops, live Canvas)
Updates:
- Embedded viewer_adapter for tracing your Python viewer to CSV ops.
- "Run with Viewer" button: Imports/runs your python_viewer.py, captures ops, updates panes.
How it works
- Pane 1: type simple calls like RECT(20,20,40,20,64), SLEEP(30), SYNC_ROW(1), DAC_WRITE(2,200), COMMIT().
  A tiny regex "transpiler" extracts these → IR ops.
- Pane 3: shows/editable CSV from IR. Edit CSV directly to update.
- Pane 2: tile-encoded sheet from IR (using px_tiles_v2 logic, embedded).
- Pane 4: replays CSV on a canvas (RECT as filled rects; others as text labels).
- Changes in Pane 1 or 3 trigger updates to all downstream panes.
Dependencies: tkinter (built-in), Pillow (pip install pillow)
Run: python analog_code_workbench.py
This is a standalone scaffold. Swap the regex parser for your VisualPython tracer.
Embed px_tiles_v2.py logic here for self-contained.
"""
import tkinter as tk
from tkinter import scrolledtext, Canvas, PhotoImage, Button
from PIL import Image, ImageDraw, ImageTk
import re, math
import importlib.util, traceback, os, inspect, pathlib # For dynamic import

# Embed minimal px_tiles_v2 codec (opcodes, pack/unpack, draw/sample, make_page)
TILE=16; PAYLOAD=12; MARGIN=2; MINICELL=3; BLACK=0; WHITE=255
def u8(n): return n & 0xFF
def to_i8(u): return u-256 if u>127 else u
def split_u8(n): return ((n>>4)&0xF, n&0xF)
def join_u8(hi,lo): return ((hi&0xF)<<4)|(lo&0xF)
def parity_nibble(op, hi, lo): return (op ^ hi ^ lo) & 0xF
def pack_bits(opcode, operand):
    # Data bits: 12 = 4(op) + 8(operand), least-significant bit first per nibble
    def bits_of_nibble(n):
        return [(n >> i) & 1 for i in range(4)]  # LSB→MSB

    data = bits_of_nibble(opcode & 0xF) + \
           bits_of_nibble((operand >> 4) & 0xF) + \
           bits_of_nibble(operand & 0xF)  # total 12 bits

    # Hamming(16,12) layout: positions 1..16; parity at 1,2,4,8
    # Fill data into non-parity positions: 3,5,6,7,9,10,11,12,13,14,15,16
    code = [0]*17  # 1-indexed
    data_positions = [3,5,6,7,9,10,11,12,13,14,15,16]
    for b, pos in zip(data, data_positions):
        code[pos] = b

    # Compute parity bits p1 (pos1), p2 (pos2), p4 (pos4), p8 (pos8)
    def parity_for(mask_bit):
        acc = 0
        for i in range(1,17):
            if i & mask_bit:
                acc ^= code[i]
        return acc

    code[1] = parity_for(0b0001)  # covers positions with bit0=1
    code[2] = parity_for(0b0010)  # covers bit1
    code[4] = parity_for(0b0100)  # covers bit2
    code[8] = parity_for(0b1000)  # covers bit3

    # Return 16 bits (row-major 4×4 payload) as list LSB→MSB per row
    return [code[i] for i in range(1,17)]
def draw_tile(op, operand):
    img=Image.new('L',(TILE,TILE),WHITE); d=ImageDraw.Draw(img)
    bits=pack_bits(op,operand); x0=MARGIN; y0=MARGIN
    for bi,b in enumerate(bits):
        r=bi//4; c=bi%4; px=x0+c*MINICELL; py=y0+r*MINICELL
        d.rectangle([px,py,px+MINICELL-1,py+MINICELL-1], fill=BLACK if b else WHITE)
    d.rectangle([0,0,TILE-1,TILE-1], outline=0)
    return img
def make_page(ops, cols=8):  # Smaller cols for UI fit
    rows=math.ceil(len(ops)/cols) if cols>0 else 1
    W=cols*TILE; H=rows*TILE
    page=Image.new('L',(W,H),WHITE); d=ImageDraw.Draw(page)
    def fid(x,y): d.rectangle([x,y,x+TILE-1,y+TILE-1], fill=BLACK)
    if W>=TILE and H>=TILE: fid(0,0); fid(W-TILE,0); fid(0,H-TILE); fid(W-TILE,H-TILE)
    for i,(op,arg) in enumerate(ops):
        tx=i%cols; ty=i//cols
        page.paste(draw_tile(op,arg),(tx*TILE,ty*TILE))
    return page.resize((300,300), Image.LANCZOS)  # Scale for pane

# Opcodes (same as v2)
NOP=0x0; SET_GRAY=0x1; MOVE_X=0x2; MOVE_Y=0x3; SET_W=0x4; SET_H=0x5; DRAW_RECT=0x6; COMMIT=0x7
SLEEP=0x8; SYNC_ROW=0x9; DAC_WRITE=0xA
OP_MAP = {
    'NOP': NOP, 'SET_GRAY': SET_GRAY, 'MOVE_X': MOVE_X, 'MOVE_Y': MOVE_Y,
    'SET_W': SET_W, 'SET_H': SET_H, 'DRAW_RECT': DRAW_RECT, 'COMMIT': COMMIT,
    'SLEEP': SLEEP, 'SYNC_ROW': SYNC_ROW, 'DAC_WRITE': DAC_WRITE,
    'RECT': DRAW_RECT # Add this for CSV parsing
}
def dac_pack(ch, val): return u8((ch&0x7)<<5 | ((val//8)&0x1F))
def dac_unpack(operand): ch=(operand>>5)&0x7; val=(operand&0x1F)*8; return ch,val

# Tiny "transpiler": regex extract ops from Pane 1 source (placeholder for VisualPython)
def source_to_ops(source):
    ops = []
    for line in source.splitlines():
        line = line.strip()
        if not line or line.startswith('#'): continue
        m = re.match(r'(\w+)\((.*)\)', line)
        if m:
            op_name = m.group(1).upper()
            args = [int(a.strip()) for a in m.group(2).split(',') if a.strip()] if m.group(2) else []
            op = OP_MAP.get(op_name)
            if op is not None:
                arg = args[0] if args else 0
                if op == DAC_WRITE and len(args)==2: arg = dac_pack(args[0], args[1])
                elif op == DRAW_RECT and len(args) >= 5:
                    # This is for Pane 1 direct RECT command, simplified
                    ops.append((SET_W, args[2]))
                    ops.append((SET_H, args[3]))
                    ops.append((SET_GRAY, args[4]))
                    ops.append((MOVE_X, args[0]))
                    ops.append((MOVE_Y, args[1]))
                    ops.append((DRAW_RECT, 0))
                    continue
                ops.append((op, arg))
    return ops

# Lower IR ops → CSV lines
def ops_to_csv(ops):
    x=y=w=h=gray=0; csv=[]
    for op,operand in ops:
        if op==NOP: continue
        elif op==SET_GRAY: gray=operand
        elif op==MOVE_X: x = operand
        elif op==MOVE_Y: y = operand
        elif op==SET_W: w=operand
        elif op==SET_H: h=operand
        elif op==DRAW_RECT:
            if w>0 and h>0: csv.append(f"RECT,{x},{y},{w},{h},{gray},{gray},{gray}")
        elif op==COMMIT: csv.append("COMMIT")
        elif op==SLEEP: csv.append(f"SLEEP,{operand}")
        elif op==SYNC_ROW: csv.append(f"SYNC_ROW,{operand}")
        elif op==DAC_WRITE: ch,val=dac_unpack(operand); csv.append(f"DAC_WRITE,{ch},{val}")
    return '\n'.join(csv)

# CSV → ops (for editing Pane 3 → update others)
def csv_to_ops(csv_text):
    ops = []
    for line in csv_text.splitlines():
        if not line.strip(): continue
        fields = line.split(',')
        op_name = fields[0].upper()
        args = [int(f) for f in fields[1:] if f.strip()]
        op = OP_MAP.get(op_name)
        if op is not None:
            if op == DRAW_RECT:
                if len(args) >= 5:
                    ops.append((SET_W, args[2]))
                    ops.append((SET_H, args[3]))
                    ops.append((SET_GRAY, args[4]))
                    ops.append((MOVE_X, args[0]))
                    ops.append((MOVE_Y, args[1]))
                    ops.append((DRAW_RECT, 0))
            else:
                arg = args[0] if args else 0
                if op == DAC_WRITE and len(args)==2: arg = dac_pack(args[0], args[1])
                ops.append((op, arg))
    return ops

# Replay CSV on Canvas (Pane 4)
def replay_csv(canvas, csv_text):
    canvas.delete('all')
    for line in csv_text.splitlines():
        if not line.strip(): continue
        fields = line.split(',')
        op = fields[0].upper()
        args = [int(f) for f in fields[1:]]
        if op == 'RECT':
            if len(args) >= 5:
                x, y, w, h, gray = args[0], args[1], args[2], args[3], args[4]
                canvas.create_rectangle(x, y, x+w, y+h, fill=f'#{gray:02x}{gray:02x}{gray:02x}', outline='black')
        elif op in ['COMMIT', 'SLEEP', 'SYNC_ROW', 'DAC_WRITE']:
            canvas.create_text(10, 10 + len(canvas.find_all())*15, anchor='nw', text=line, fill='blue')

# Viewer Adapter (embedded module for tracing your Python viewer)
class ViewerAdapter:
    ops = []  # Captured ops as CSV lines
    @staticmethod
    def reset():
        ViewerAdapter.ops.clear()
    @staticmethod
    def RECT(x, y, w, h, gray):
        g = int(gray)
        ViewerAdapter.ops.append(f"RECT,{int(x)},{int(y)},{int(w)},{int(h)},{g},{g},{g}")
    @staticmethod
    def TEXT(x, y, s, gray=255):
        pass
    @staticmethod
    def COMMIT():
        ViewerAdapter.ops.append("COMMIT")
    @staticmethod
    def SLEEP(ms):
        ViewerAdapter.ops.append(f"SLEEP,{int(ms)}")
    @staticmethod
    def SYNC_ROW(i):
        ViewerAdapter.ops.append(f"SYNC_ROW,{int(i)}")
    @staticmethod
    def DAC_WRITE(ch, val):
        ViewerAdapter.ops.append(f"DAC_WRITE,{int(ch)},{int(val)}")
    @staticmethod
    def get_captured_csv():
        return '\n'.join(ViewerAdapter.ops)

# UI
class Workbench(tk.Tk):
    def __init__(self):
        super().__init__(); self.title("Analog Code Workbench")
        self.geometry("1200x800")
        # Pane 1: Source (editable)
        tk.Label(self, text="1. Original Python Source", anchor='n').grid(row=0, column=0, padx=5, pady=5)
        self.p1 = scrolledtext.ScrolledText(self, width=40, height=20)
        self.p1.grid(row=1, column=0, padx=5, pady=5)
        self.p1.insert(tk.END, "# Example source\nRECT(20,20,40,20,64)\nRECT(80,20,40,20,160)\nRECT(80,60,40,20,220)\nCOMMIT()\n")
        self.p1.bind("<KeyRelease>", self.update_from_p1)
        # Pane 2: Analog pixels (Image)
        tk.Label(self, text="2. Analog Pixels (Tile Sheet)", anchor='n').grid(row=0, column=1, padx=5, pady=5)
        self.p2 = tk.Label(self)
        self.p2.grid(row=1, column=1, padx=5, pady=5)
        # Pane 3: CSV (editable)
        tk.Label(self, text="3. Analog Code (CSV/IR)", anchor='n').grid(row=0, column=2, padx=5, pady=5)
        self.p3 = scrolledtext.ScrolledText(self, width=40, height=20)
        self.p3.grid(row=1, column=2, padx=5, pady=5)
        self.p3.bind("<KeyRelease>", self.update_from_p3)
        # Pane 4: Result (Canvas)
        tk.Label(self, text="4. Live Results", anchor='n').grid(row=0, column=3, padx=5, pady=5)
        self.p4 = Canvas(self, width=300, height=300, bg='white')
        self.p4.grid(row=1, column=3, padx=5, pady=5)
        # Run with Viewer button
        Button(self, text="Run with my Viewer", command=self.run_viewer).grid(row=2, column=0, padx=5, pady=5, columnspan=4)
        self.update_from_p1()

    def update_from_p1(self, event=None):
        source = self.p1.get('1.0', tk.END)
        ops = source_to_ops(source)
        csv = ops_to_csv(ops)
        self.p3.delete('1.0', tk.END); self.p3.insert(tk.END, csv)
        self.update_panes(ops, csv)

    def update_from_p3(self, event=None):
        csv = self.p3.get('1.0', tk.END)
        ops = csv_to_ops(csv)
        self.update_panes(ops, csv)

    def update_panes(self, ops, csv):
        page = make_page(ops)
        self.photo = ImageTk.PhotoImage(page)
        self.p2.config(image=self.photo)
        replay_csv(self.p4, csv)

    def run_viewer(self):
        VA = ViewerAdapter
        VA.reset()

        module_name = os.getenv("ACW_VIEWER_MODULE", "python_viewer")
        func_name   = os.getenv("ACW_VIEWER_FUNC",   "run_python_viewer")

        try:
            spec = importlib.util.spec_from_file_location(module_name, f"{module_name}.py")
            if not spec or not spec.loader:
                raise ImportError(f"Could not find or load module: {module_name}.py")

            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            func = getattr(mod, func_name)
            func()
        except Exception as e:
            traceback.print_exc()
            err = traceback.format_exc()
            self.p3.delete('1.0', tk.END)
            self.p3.insert(tk.END, "# ERROR: failed to run viewer.\n" + err)
            return

        csv_text = VA.get_captured_csv()
        self.p3.delete('1.0', tk.END)
        self.p3.insert(tk.END, csv_text)

        ops = csv_to_ops(csv_text)
        self.update_panes(ops, csv_text)

        # Mirror source into Pane 1
        try:
            src = inspect.getsource(mod)
        except TypeError:
            try:
                src = pathlib.Path(mod.__file__).read_text(encoding="utf-8")
            except Exception:
                src = f"# Source for {module_name}.py unavailable"
        except Exception:
            src = f"# Source for {module_name}.py unavailable"

        self.p1.delete('1.0', tk.END)
        self.p1.insert(tk.END, src)

if __name__ == "__main__":
    Workbench().mainloop()
