"""
PXOS 6-Pane Workbench - Complete Integration
Hybrid computing platform with bidirectional digital-analog translation
"""
import tkinter as tk
from tkinter import scrolledtext, Button, messagebox
import json
import asyncio
import threading
from typing import Any, Dict

# Import all the new components
from transpiler import T_py_to_hlir
from hlir_to_py import hlir_to_python
from validate_hlir import validate_hlir
from pxos_ops_schema import SCHEMA

class MockDSLTransforms:
    """Mock DSL transforms for the prototype"""
    @staticmethod
    def T_analog_to_hlir(dsl_text: str) -> Dict[str, Any]:
        """Convert DSL to HLIR (simplified for prototype)"""
        lines = [line.strip() for line in dsl_text.split('\n') if line.strip()]
        program = []
        
        for line in lines:
            if line.startswith('RECT('):
                # Parse RECT(x=20,y=20,w=40,h=20,g=64)
                import re
                match = re.match(r'RECT\(x=(\d+),y=(\d+),w=(\d+),h=(\d+),g=(\d+)\)', line)
                if match:
                    x, y, w, h, g = map(int, match.groups())
                    program.append({"op": "RECT", "x": x, "y": y, "w": w, "h": h, "r": g, "g": g, "b": g})
            elif line == 'COMMIT()':
                program.append({"op": "COMMIT"})
        
        return {
            "schemaVersion": "pxos-ops/1.0",
            "meta": {"profile": "default", "cols": 16},
            "program": program
        }
    
    @staticmethod
    def T_hlir_to_analog(hlir: Dict[str, Any]) -> str:
        """Convert HLIR to DSL (simplified for prototype)"""
        lines = []
        for op in hlir.get("program", []):
            if op["op"] == "RECT":
                lines.append(f"RECT(x={op['x']},y={op['y']},w={op['w']},h={op['h']},g={op['g']})")
            elif op["op"] == "COMMIT":
                lines.append("COMMIT()")
            elif op["op"] == "SLEEP":
                lines.append(f"SLEEP(ms={op['ms']})")
            elif op["op"] == "DAC_WRITE":
                lines.append(f"DAC_WRITE(ch={op['ch']},val={op['val']})")
        return '\n'.join(lines)

class PaneAdapter:
    """Base adapter for text panes with echo guards"""
    def __init__(self, pane_id: str, widget: scrolledtext.ScrolledText, workbench):
        self.id = pane_id
        self.widget = widget
        self.workbench = workbench
        self.pinned = False
        self._last_build_id = -1
        self._updating = False
        
        # Bind edit events
        self.widget.bind("<KeyRelease>", self._on_edit)
        self.widget.bind("<Button-1>", self._on_edit)  # Mouse clicks
    
    def read(self) -> str:
        return self.widget.get("1.0", "end-1c")
    
    def write(self, text: str, *, origin: str, build_id: int) -> None:
        """Write text with echo guard"""
        if origin == self.id and build_id == self._last_build_id:
            return  # Echo guard: don't update if we're the origin
        if self.pinned:
            return  # Don't update pinned panes
        
        self._last_build_id = build_id
        self._updating = True
        
        # Save cursor position
        cursor_pos = self.widget.index(tk.INSERT)
        
        # Update content
        self.widget.delete("1.0", "end")
        self.widget.insert("1.0", text)
        
        # Restore cursor position (if possible)
        try:
            self.widget.mark_set(tk.INSERT, cursor_pos)
        except:
            pass
        
        self._updating = False
    
    def annotate(self, message: str, *, severity: str = "error") -> None:
        """Show error annotation"""
        if severity == "error":
            self.widget.configure(bg="#ffe6e6")  # Light red background
            messagebox.showerror(f"Error in {self.id}", message)
        else:
            self.widget.configure(bg="#fff3cd")  # Light yellow background
    
    def clear_diagnostics(self) -> None:
        """Clear error annotations"""
        self.widget.configure(bg="white")
    
    def _on_edit(self, event) -> None:
        """Handle edit events"""
        if self._updating:
            return  # Don't trigger during programmatic updates
        
        # Debounce: schedule update after brief delay
        if hasattr(self, '_edit_timer'):
            self.widget.after_cancel(self._edit_timer)
        
        self._edit_timer = self.widget.after(200, lambda: self.workbench.on_edit(self.id))

class PXOSWorkbench(tk.Tk):
    """Complete 6-Pane PXOS Workbench"""
    
    def __init__(self):
        super().__init__()
        self.title("PXOS 6-Pane Workbench - Hybrid Computing Platform")
        self.geometry("1400x900")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # State
        self.build_id = 0
        self.transforms = MockDSLTransforms()
        
        # Create UI
        self.create_layout()
        self.create_panes()
        
        # Initial content
        self.p1.widget.insert("end", "import viewer_adapter as VA\nVA.RECT(20, 20, 40, 20, 64)\nVA.COMMIT()")
        
        # Start event loop
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self.thread.start()
        
        # Initial sync
        self.on_edit("P1")
    
    def create_layout(self):
        """Create the 6-pane layout"""
        # Top frame (3 panes)
        top_frame = tk.Frame(self)
        top_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Bottom frame (3 panes)
        bottom_frame = tk.Frame(self)
        bottom_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Configure grid weights
        for i in range(3):
            top_frame.columnconfigure(i, weight=1)
            bottom_frame.columnconfigure(i, weight=1)
        
        top_frame.rowconfigure(1, weight=1)
        bottom_frame.rowconfigure(1, weight=1)
        
        self.top_frame = top_frame
        self.bottom_frame = bottom_frame
    
    def create_panes(self):
        """Create all 6 panes"""
        # P1: Python Source
        tk.Label(self.top_frame, text="P1: Python Source", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", padx=5)
        p1_widget = scrolledtext.ScrolledText(self.top_frame, width=40, height=15, font=("Consolas", 9))
        p1_widget.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        pin_btn1 = Button(self.top_frame, text="📌 Pin", command=lambda: self.toggle_pin("P1"))
        pin_btn1.grid(row=2, column=0, pady=2)
        self.p1 = PaneAdapter("P1", p1_widget, self)
        
        # P2: Analog Text Mirror
        tk.Label(self.top_frame, text="P2: Analog Text Mirror", font=("Arial", 10, "bold")).grid(row=0, column=1, sticky="w", padx=5)
        p2_widget = scrolledtext.ScrolledText(self.top_frame, width=40, height=15, font=("Consolas", 9))
        p2_widget.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")
        pin_btn2 = Button(self.top_frame, text="📌 Pin", command=lambda: self.toggle_pin("P2"))
        pin_btn2.grid(row=2, column=1, pady=2)
        self.p2 = PaneAdapter("P2", p2_widget, self)
        
        # P3: Analog Source Editor
        tk.Label(self.top_frame, text="P3: Analog Source Editor", font=("Arial", 10, "bold")).grid(row=0, column=2, sticky="w", padx=5)
        p3_widget = scrolledtext.ScrolledText(self.top_frame, width=40, height=15, font=("Consolas", 9))
        p3_widget.grid(row=1, column=2, padx=5, pady=5, sticky="nsew")
        pin_btn3 = Button(self.top_frame, text="📌 Pin", command=lambda: self.toggle_pin("P3"))
        pin_btn3.grid(row=2, column=2, pady=2)
        self.p3 = PaneAdapter("P3", p3_widget, self)
        
        # P4: Tile Sheet
        tk.Label(self.bottom_frame, text="P4: Tile Sheet (ECC)", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", padx=5)
        p4_widget = scrolledtext.ScrolledText(self.bottom_frame, width=40, height=10, font=("Consolas", 9), state="disabled")
        p4_widget.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        self.p4 = PaneAdapter("P4", p4_widget, self)
        
        # P5: HLIR JSON
        tk.Label(self.bottom_frame, text="P5: HLIR JSON", font=("Arial", 10, "bold")).grid(row=0, column=1, sticky="w", padx=5)
        p5_widget = scrolledtext.ScrolledText(self.bottom_frame, width=40, height=10, font=("Consolas", 9))
        p5_widget.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")
        pin_btn5 = Button(self.bottom_frame, text="📌 Pin", command=lambda: self.toggle_pin("P5"))
        pin_btn5.grid(row=2, column=1, pady=2)
        self.p5 = PaneAdapter("P5", p5_widget, self)
        
        # P6: Live Replay & Logs
        tk.Label(self.bottom_frame, text="P6: Live Replay & Logs", font=("Arial", 10, "bold")).grid(row=0, column=2, sticky="w", padx=5)
        p6_widget = scrolledtext.ScrolledText(self.bottom_frame, width=40, height=10, font=("Consolas", 9), state="disabled")
        p6_widget.grid(row=1, column=2, padx=5, pady=5, sticky="nsew")
        self.p6 = PaneAdapter("P6", p6_widget, self)
    
    def toggle_pin(self, pane_id: str):
        """Toggle pin state of a pane"""
        pane = getattr(self, pane_id.lower())
        pane.pinned = not pane.pinned
        
        # Visual feedback
        bg_color = "#fffacd" if pane.pinned else "white"  # Light yellow if pinned
        pane.widget.configure(bg=bg_color)
        
        status = "pinned" if pane.pinned else "unpinned"
        self.log(f"P6", f"{pane_id} {status}")
    
    def on_edit(self, pane_id: str):
        """Handle edit events with proper async dispatch"""
        self.loop.call_soon_threadsafe(lambda: asyncio.create_task(self._handle_edit(pane_id)))
    
    async def _handle_edit(self, pane_id: str):
        """Async edit handler"""
        self.build_id += 1
        build_id = self.build_id
        
        try:
            # Clear previous diagnostics
            for pane in [self.p1, self.p2, self.p3, self.p5]:
                pane.clear_diagnostics()
            
            # Transform to HLIR based on origin
            if pane_id == "P1":
                text = self.p1.read()
                hlir = T_py_to_hlir(text)
            elif pane_id in ["P2", "P3"]:
                text = getattr(self, pane_id.lower()).read()
                hlir = self.transforms.T_analog_to_hlir(text)
            elif pane_id == "P5":
                text = self.p5.read()
                try:
                    hlir = json.loads(text)
                except json.JSONDecodeError as e:
                    getattr(self, pane_id.lower()).annotate(f"Invalid JSON: {e}")
                    return
            else:
                return
            
            # Validate HLIR
            validate_hlir(hlir)
            
            # Update all other panes
            await self._sync_all_panes(hlir, origin=pane_id, build_id=build_id)
            
            # Update P4 (tiles) and P6 (logs)
            await self._update_analog_panes(hlir, origin=pane_id, build_id=build_id)
            
            self.log("P6", f"[build {build_id} from {pane_id}] sync complete")
            
        except Exception as e:
            error_msg = str(e)
            getattr(self, pane_id.lower()).annotate(error_msg)
            self.log("P6", f"[build {build_id} from {pane_id}] error: {error_msg}")
    
    async def _sync_all_panes(self, hlir: Dict[str, Any], *, origin: str, build_id: int):
        """Synchronize all panes with new HLIR"""
        # Generate representations
        python_code = hlir_to_python(hlir, alias="VA")
        dsl_code = self.transforms.T_hlir_to_analog(hlir)
        json_code = json.dumps(hlir, indent=2)
        
        # Update panes (skip origin and pinned panes)
        if origin != "P1":
            self.p1.write(python_code, origin=origin, build_id=build_id)
        
        if origin != "P2":
            self.p2.write(dsl_code, origin=origin, build_id=build_id)
        
        if origin != "P3":
            self.p3.write(dsl_code, origin=origin, build_id=build_id)
        
        if origin != "P5":
            self.p5.write(json_code, origin=origin, build_id=build_id)
    
    async def _update_analog_panes(self, hlir: Dict[str, Any], *, origin: str, build_id: int):
        """Update P4 (tiles) and P6 (logs) with analog representations"""
        # P4: Mock tile encoding
        num_ops = len(hlir.get("program", []))
        ecc_stats = {"ok": num_ops, "corrected": 0, "bad": 0}
        tiles_text = f"Tiles Generated: {num_ops} ops\nECC Stats: {ecc_stats}\n"
        
        for i, op in enumerate(hlir.get("program", [])):
            tiles_text += f"Tile {i}: {op['op']}\n"
        
        self.p4.widget.configure(state="normal")
        self.p4.write(tiles_text, origin=origin, build_id=build_id)
        self.p4.widget.configure(state="disabled")
        
        # P6: Mock replay
        replay_text = f"Replay HLIR [{build_id}]:\n"
        for op in hlir.get("program", []):
            replay_text += f"Execute: {op}\n"
        
        self.p6.widget.configure(state="normal")
        self.p6.write(replay_text, origin=origin, build_id=build_id)
        self.p6.widget.configure(state="disabled")
    
    def log(self, pane_id: str, message: str):
        """Add log message to P6"""
        if pane_id == "P6":
            pane = self.p6
            pane.widget.configure(state="normal")
            current = pane.widget.get("1.0", "end-1c")
            new_content = current + f"\n[LOG] {message}" if current else f"[LOG] {message}"
            pane.widget.delete("1.0", "end")
            pane.widget.insert("1.0", new_content)
            pane.widget.see("end")  # Auto-scroll to bottom
            pane.widget.configure(state="disabled")
    
    def _run_event_loop(self):
        """Run the async event loop in a separate thread"""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
    
    def on_closing(self):
        """Handle window closing"""
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.destroy()

if __name__ == "__main__":
    print("🚀 Starting PXOS 6-Pane Workbench...")
    print("✅ All drop-ins integrated:")
    print("   - HLIR → Python pretty-printer")
    print("   - JSON Schema validator") 
    print("   - AST transpiler with clamp helpers")
    print("   - Origin tracking in logs")
    print("\n🎯 Ready for bidirectional editing!")
    
    app = PXOSWorkbench()
    app.mainloop()