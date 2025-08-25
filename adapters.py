import tkinter as tk
from tkinter import scrolledtext
from typing import Dict, Any

class TkTextPane:
    def __init__(self, pid, widget: scrolledtext.ScrolledText):
        self.id = pid
        self.widget = widget
        self.pinned = False
        self.widget.bind("<KeyRelease>", self._on_edit)
        self.engine = None # Will be set by engine during registration

    def read(self) -> str:
        return self.widget.get("1.0", "end-1c")

    def write(self, text: str, *, origin: str, build_id: int):
        self.widget.configure(state="normal")
        self.widget.delete("1.0", "end")
        self.widget.insert("1.0", text)
        self.widget.configure(state="disabled")

    def annotate(self, message: str, *, severity: str = "error"):
        # Simple annotation: just prepend to the text
        self.widget.configure(state="normal")
        self.widget.insert("1.0", f"# {severity.upper()}: {message}\n")
        self.widget.configure(state="disabled")

    def clear_diagnostics(self):
        # Simple clear: remove all lines starting with #
        content = self.read()
        cleaned_content = "\n".join([line for line in content.split("\n") if not line.strip().startswith("#")])
        self.widget.configure(state="normal")
        self.widget.delete("1.0", "end")
        self.widget.insert("1.0", cleaned_content)
        self.widget.configure(state="disabled")

    def _on_edit(self, event):
        if self.engine:
            self.engine.on_edit(self.id)

class TkTilesPane(TkTextPane):
    def render_tiles(self, tiles: Any, ecc_report: Dict[str,int], *, origin: str, build_id: int):
        # For now, just display the JSON representation of the tiles
        import json
        text = json.dumps(tiles, indent=2)
        super().write(text, origin=origin, build_id=build_id)

class TkReplayPane(TkTextPane):
    def replay_from_hlir(self, hlir: Dict[str, Any], *, origin: str, build_id: int):
        # For now, just display the JSON representation of the HLIR
        import json
        text = json.dumps(hlir, indent=2)
        super().write(text, origin=origin, build_id=build_id)

    def log(self, line: str):
        self.widget.configure(state="normal")
        self.widget.insert("end", f"\n# LOG: {line}")
        self.widget.configure(state="disabled")
