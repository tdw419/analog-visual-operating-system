# px_cartridge_loader.py — PX Cartridge Loader window (pygame demo)  (MIT)
# - Press 'O' to open a BitPack v1 PNG
# - Shows header, checksum, and a text preview
# - Press 'R' to "run": calls on_run(lang, content_bytes) callback (replace with PixelOS routing)
import os, sys, json, hashlib
import pygame
import tkinter as tk
from tkinter import filedialog
from dataclasses import dataclass
from typing import Optional, Callable
from pxos_py.px_bitpack_v1 import decode_from_png

BG = (20,22,24)
FG = (230,230,230)
ACCENT = (90,170,255)
OK = (90,200,120)
ERR = (230,80,80)

@dataclass
class Cartridge:
    path: str
    lang: str
    content: bytes
    digest: str  # hex

class PXCartridgeLoader:
    def __init__(self, on_run: Optional[Callable[[str, bytes], None]] = None, size=(900, 700)):
        pygame.init()
        self.screen = pygame.display.set_mode(size)
        pygame.display.set_caption("PX Cartridge Loader (BitPack v1)")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Consolas,Menlo,Monaco,DejaVu Sans Mono", 16)
        self.small = pygame.font.SysFont("Consolas,Menlo,Monaco,DejaVu Sans Mono", 14)
        self.big = pygame.font.SysFont("Consolas,Menlo,Monaco,DejaVu Sans Mono", 20, bold=True)
        self.on_run = on_run or self._default_runner
        self.cart: Optional[Cartridge] = None
        self.status = "Press O to open a BitPack PNG; R to run."
        self.status_color = FG
        self.scroll = 0

    def _default_runner(self, lang: str, content: bytes):
        # Stub: replace with route to your PixelOS sandbox/tooling
        print(f"[RUN] lang={lang} bytes={len(content)}")
        # Example: if lang in ("pixelpy","python"): exec(content.decode("utf-8"), {})

    def _open_dialog(self) -> Optional[str]:
        root = tk.Tk(); root.withdraw()
        path = filedialog.askopenfilename(title="Open BitPack v1 PNG", filetypes=[("PNG","*.png"),("All","*.*")])
        root.destroy()
        return path or None

    def load_png(self, path: str):
        try:
            pkt = decode_from_png(path)
            lang = pkt["lang"]
            content = pkt["content"]
            digest = hashlib.sha256(content).hexdigest()
            self.cart = Cartridge(path=path, lang=lang, content=content, digest=digest)
            self.status = f"Loaded {os.path.basename(path)}  lang={lang}  size={len(content)} bytes"
            self.status_color = OK
            self.scroll = 0
        except Exception as e:
            self.status = f"Error: {e}"
            self.status_color = ERR
            self.cart = None

    def draw_text(self, surf, text, x, y, color=FG, font=None):
        font = font or self.font
        s = font.render(text, True, color)
        surf.blit(s, (x, y))

    def render(self):
        self.screen.fill(BG)
        W,H = self.screen.get_size()

        # Header
        pygame.draw.rect(self.screen, (36,40,44), (0,0,W,80))
        self.draw_text(self.screen, "PX Cartridge Loader", 20, 16, ACCENT, self.big)
        self.draw_text(self.screen, "BitPack v1 · lossless code-as-pixels", 20, 44, (180,180,180), self.small)

        # Status bar
        pygame.draw.rect(self.screen, (30,32,34), (0,H-30,W,30))
        self.draw_text(self.screen, self.status, 10, H-24, self.status_color, self.small)

        # Info / preview pane
        left = 20; top = 90; right = W - 20; bottom = H - 40
        pygame.draw.rect(self.screen, (28,30,32), (left, top, right-left, bottom-top))
        inner = pygame.Rect(left+12, top+12, right-left-24, bottom-top-24)
        pygame.draw.rect(self.screen, (18,18,18), inner)
        pygame.draw.rect(self.screen, (60,60,60), inner, 1)

        if self.cart:
            # Left column: meta
            x0 = inner.x + 10; y0 = inner.y + 8
            self.draw_text(self.screen, f"File: {os.path.basename(self.cart.path)}", x0, y0)
            y0 += 22; self.draw_text(self.screen, f"Lang: {self.cart.lang}", x0, y0)
            y0 += 22; self.draw_text(self.screen, f"Bytes: {len(self.cart.content)}", x0, y0)
            y0 += 22; self.draw_text(self.screen, f"SHA256: {self.cart.digest[:16]}…", x0, y0, (200,200,200))

            # Divider
            y_div = inner.y + 120
            pygame.draw.line(self.screen, (60,60,60), (inner.x+8, y_div), (inner.right-8, y_div))

            # Preview (scrollable text)
            preview = self.cart.content.decode("utf-8", errors="replace").splitlines()
            x = inner.x + 10; y = y_div + 8 - self.scroll
            line_h = 18
            max_lines = (inner.bottom - y_div - 16)//line_h
            for i in range(max_lines):
                li = i + self.scroll//line_h
                if 0 <= li < len(preview):
                    self.draw_text(self.screen, f"{li+1:4d}: {preview[li]}", x, y + i*line_h, (210,210,210), self.font)
        else:
            self.draw_text(self.screen, "No cartridge loaded.", inner.x+10, inner.y+10, (200,200,200))

        # Foot keys
        keys = "O: Open   R: Run   ↑/↓: Scroll   Esc: Quit"
        self.draw_text(self.screen, keys, W-20 - self.small.size(self.screen, keys)[0] if hasattr(self.small, "size") else W-240, H-24, (160,160,160), self.small)

        pygame.display.flip()

    def run(self):
        running = True
        while running:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    running = False
                elif e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE:
                        running = False
                    elif e.key == pygame.K_o:
                        path = self._open_dialog()
                        if path: self.load_png(path)
                    elif e.key == pygame.K_r:
                        if self.cart:
                            try:
                                self.on_run(self.cart.lang, self.cart.content)
                                self.status = f"Dispatched run: lang={self.cart.lang}"
                                self.status_color = OK
                            except Exception as ex:
                                self.status = f"Run error: {ex}"
                                self.status_color = ERR
                    elif e.key == pygame.K_UP:
                        self.scroll = max(0, self.scroll - 18)
                    elif e.key == pygame.K_DOWN:
                        self.scroll += 18
            self.render()
            self.clock.tick(60)

# Demo: run as script
if __name__ == "__main__":
    def demo_runner(lang, content: bytes):
        print(f"[DEMO] Would run lang={lang} with {len(content)} bytes.")
        if lang.lower() in ("pixelpy","python"):
            src = content.decode("utf-8", errors="replace")
            print("First 5 lines:")
            print("\n".join(src.splitlines()[:5]))

    app = PXCartridgeLoader(on_run=demo_runner)
    app.run()
