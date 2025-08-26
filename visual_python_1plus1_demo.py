# visual_python_1plus1_demo.py
# pip install pillow

from PIL import Image, ImageDraw, ImageFont
import ast, operator
import dis

# -------- configurable expression --------
CODE_STR = "2+3"

# -------- safe arithmetic evaluator (numbers and + - * / // % **, parentheses) --------
BIN_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
UN_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}

def safe_eval(expr: str):
    node = ast.parse(expr, mode="eval").body
    def ev(n):
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        if isinstance(n, ast.UnaryOp) and type(n.op) in UN_OPS:
            return UN_OPS[type(n.op)](ev(n.operand))
        if isinstance(n, ast.BinOp) and type(n.op) in BIN_OPS:
            return BIN_OPS[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.Expr):
            return ev(n.value)
        raise ValueError("Unsupported expression")
    return ev(node)

# -------- color palette for machine tiles --------
PALETTE = {
    "0":"#2dd4bf","1":"#22c55e","2":"#84cc16","3":"#eab308","4":"#f59e0b",
    "5":"#f97316","6":"#ef4444","7":"#ec4899","8":"#a855f7","9":"#3b82f6",
    "+":"#fb923c","-":"#f43f5e","*":"#8b5cf6","/":"#06b6d4","(":"#94a3b8",")":"#94a3b8",
    " ":"#0f172a"
}
def char_color(ch: str) -> str:
    return PALETTE.get(ch, "#64748b")  # default slate if unknown

def to_visual_ir(py_src: str):
    code = compile(py_src, "<visual>", "exec")
    instructions = list(dis.get_instructions(code))
    return instructions

BYTECODE_PALETTE = {
    "LOAD_CONST": "#3b82f6",
    "BINARY_ADD": "#ef4444",
    "PRINT_EXPR": "#22c55e",
    "RETURN_VALUE": "#a855f7",
}
def bytecode_color(opname: str) -> str:
    return BYTECODE_PALETTE.get(opname, "#64748b")

# -------- canvas + layout --------
W, H = 1200, 700
M, GAP = 18, 18
CTRL_H = 40
pane_w = (W - M*2 - GAP) // 2
pane_h = (H - M*2 - GAP - CTRL_H) // 2
PANE_BG = "#0b1220"
OUT_PATH = "visual_python_1plus1_demo.png"

img = Image.new("RGB", (W, H), "#0a0f1a")
d = ImageDraw.Draw(img)
try:
    font_mono = ImageFont.truetype("DejaVuSansMono.ttf", 28)
    font_mono_big = ImageFont.truetype("DejaVuSansMono.ttf", 48)
    font_ui = ImageFont.truetype("DejaVuSans.ttf", 18)
except:
    font_mono = ImageFont.load_default()
    font_mono_big = ImageFont.load_default()
    font_ui = ImageFont.load_default()

def pane_box(ix, iy, title):
    x0 = M + (pane_w + GAP) * ix
    y0 = M + CTRL_H + (pane_h + GAP) * iy
    x1, y1 = x0 + pane_w, y0 + pane_h
    d.rounded_rectangle([x0, y0, x1, y1], radius=14, fill=PANE_BG, outline="#1f2a44", width=2)
    d.text((x0+14, y0-26), title, font=font_ui, fill="#a5b4fc")
    return (x0, y0, x1, y1)

# -------- draw grid helper for “pixelized” look --------
def draw_char_grid(x0, y0, cell_w, cell_h, cols, rows, color="#132035"):
    for r in range(rows+1):
        y = y0 + r*cell_h
        d.line([(x0, y), (x0+cols*cell_w, y)], fill=color, width=1)
    for c in range(cols+1):
        x = x0 + c*cell_w
        d.line([(x, y0), (x, y0+rows*cell_h)], fill=color, width=1)

# -------- PANE 1: text source --------
p1 = pane_box(0, 0, "Pane 1 — Text source")
d.text((p1[0]+20, p1[1]+20), CODE_STR, font=font_mono_big, fill="#e2e8f0")

# -------- PANE 2: pixelized (human-readable) from Pane 1 --------
p2 = pane_box(1, 0, "Pane 2 — Pixelized text (from Pane 1)")
# a simple cell grid + monospaced text to suggest pixelization
cell_w, cell_h = 24, 32
cols = max(12, len(CODE_STR) + 4)
rows = 3
gx = p2[0] + 16
gy = p2[1] + 16
draw_char_grid(gx, gy, cell_w, cell_h, cols, rows)
d.text((gx + 2, gy + cell_h//4), CODE_STR, font=font_mono_big, fill="#c7d2fe")

# -------- PANE 3: color-encoded tiles (machine-readable bytecode) --------
p3 = pane_box(0, 1, "Pane 3 — Bytecode Tiles (machine-readable)")
instructions = to_visual_ir(f"print({CODE_STR})")
tile_size = min(100, (pane_w - 40) // max(3, len(instructions)))
tx0 = p3[0] + (pane_w - tile_size*len(instructions))//2
ty0 = p3[1] + (pane_h - tile_size)//2
for i, instr in enumerate(instructions):
    x = tx0 + i*tile_size
    y = ty0
    c = bytecode_color(instr.opname)
    d.rounded_rectangle([x, y, x+tile_size-4, y+tile_size-4], radius=10, fill=c, outline="#0b0f1a", width=3)
    # faint glyph overlay for debugging
    op_text = f"{instr.opname}\n({instr.argval})" if instr.argval is not None else instr.opname
    d.text((x + 10, y + 10), op_text, font=font_mono, fill="#0b122080")

# small legend
lx, ly = p3[0]+16, p3[1]+16
d.text((lx, ly), "Legend:", font=font_ui, fill="#93c5fd")
for i, opname in enumerate(BYTECODE_PALETTE.keys()):
    sw = 18
    d.rectangle([lx, ly+24+20*i, lx+sw, ly+24+20*i+sw], fill=bytecode_color(opname), outline="#0b0f1a")
    d.text((lx+sw+8, ly+24+20*i-2), opname, font=font_ui, fill="#cbd5e1")

# -------- PANE 4: pixel compiler/interpreter/result --------
p4 = pane_box(1, 1, "Pane 4 — Visual VM")
stack = []
output = ""
y_offset = p4[1] + 20
d.text((p4[0]+20, y_offset), "Executing bytecode tiles...", font=font_ui, fill="#94a3b8")
y_offset += 30

for instr in instructions:
    d.text((p4[0]+20, y_offset), f"Op: {instr.opname}, Arg: {instr.argval}", font=font_mono, fill="#e2e8f0")
    y_offset += 30
    if instr.opname == "LOAD_CONST":
        stack.append(instr.argval)
    elif instr.opname == "BINARY_ADD":
        b = stack.pop()
        a = stack.pop()
        stack.append(a + b)
    elif instr.opname == "PRINT_EXPR":
        output = str(stack.pop())

    d.text((p4[0]+20, y_offset), f"Stack: {stack}", font=font_mono, fill="#a5b4fc")
    y_offset += 40

d.text((p4[0]+20, y_offset), f"Final Output: {output}", font=font_mono_big, fill="#facc15")

# -------- top control strip (cosmetic) --------
d.rectangle([M, M, W-M, M+CTRL_H], fill="#0e1726", outline="#1f2a44")
d.text((M+14, M+10), "Visual Python — text → pixelized text → color tiles → result", font=font_ui, fill="#a5b4fc")

img.save(OUT_PATH)
print(f"Saved {OUT_PATH}")
